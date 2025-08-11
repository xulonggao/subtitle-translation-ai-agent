"""
模型容错管理器
"""
import time
import logging
from typing import Optional, Dict, Any
from strands.models import BedrockModel
from config import bedrock_config, get_logger

logger = get_logger("model_manager")


class ModelFallbackManager:
    """模型容错管理器
    
    支持Claude 4 Sonnet主用，Claude 3.7 Sonnet备用的容错机制
    """
    
    def __init__(self):
        self.primary_config = {
            "model_id": bedrock_config.primary_model_id,
            "region": bedrock_config.region,
            "max_tokens": bedrock_config.max_tokens,
            "temperature": bedrock_config.temperature,
            "memory_enabled": bedrock_config.memory_enabled,
            "memory_duration_days": bedrock_config.memory_duration_days,
        }
        
        self.fallback_config = {
            "model_id": bedrock_config.fallback_model_id,
            "region": bedrock_config.region,
            "max_tokens": bedrock_config.max_tokens,
            "temperature": bedrock_config.temperature,
            "memory_enabled": bedrock_config.memory_enabled,
            "memory_duration_days": bedrock_config.memory_duration_days,
        }
        
        self.retry_attempts = bedrock_config.retry_attempts
        self.backoff_delay = bedrock_config.backoff_delay
        
        # 状态跟踪
        self.current_model_type = "primary"  # primary or fallback
        self.primary_failure_count = 0
        self.last_failure_time = None
        self.model_cache: Dict[str, BedrockModel] = {}
        
        logger.info("模型容错管理器初始化完成", 
                   primary_model=self.primary_config["model_id"],
                   fallback_model=self.fallback_config["model_id"])
    
    def get_model_with_fallback(self) -> BedrockModel:
        """获取可用模型，支持自动容错"""
        
        # 首先尝试主模型
        if self.current_model_type == "primary" or self._should_retry_primary():
            try:
                model = self._get_model("primary")
                if self._test_model_availability(model):
                    self.current_model_type = "primary"
                    self.primary_failure_count = 0
                    logger.info("使用主模型", model_id=self.primary_config["model_id"])
                    return model
            except Exception as e:
                logger.warning("主模型不可用", error=str(e), model_id=self.primary_config["model_id"])
                self._handle_primary_failure(e)
        
        # 使用备用模型
        try:
            model = self._get_model("fallback")
            if self._test_model_availability(model):
                self.current_model_type = "fallback"
                logger.info("切换到备用模型", model_id=self.fallback_config["model_id"])
                return model
        except Exception as e:
            logger.error("备用模型也不可用", error=str(e), model_id=self.fallback_config["model_id"])
            raise RuntimeError(f"所有模型都不可用: 主模型和备用模型都失败")
        
        raise RuntimeError("无法获取可用模型")
    
    def _get_model(self, model_type: str) -> BedrockModel:
        """获取指定类型的模型实例"""
        if model_type in self.model_cache:
            return self.model_cache[model_type]
        
        config = self.primary_config if model_type == "primary" else self.fallback_config
        
        try:
            model = BedrockModel(**config)
            self.model_cache[model_type] = model
            return model
        except Exception as e:
            logger.error(f"创建{model_type}模型失败", error=str(e), config=config)
            raise
    
    def _test_model_availability(self, model: BedrockModel) -> bool:
        """测试模型可用性"""
        try:
            # 发送一个简单的测试请求
            test_prompt = "测试"
            # 注意：这里需要根据Strands SDK的实际API调整
            # response = model.generate(test_prompt, max_tokens=10)
            # return response is not None
            return True  # 暂时返回True，实际实现时需要真正测试
        except Exception as e:
            logger.warning("模型可用性测试失败", error=str(e))
            return False
    
    def _handle_primary_failure(self, error: Exception):
        """处理主模型失败"""
        self.primary_failure_count += 1
        self.last_failure_time = time.time()
        
        # 检查是否是限流错误
        error_str = str(error).lower()
        if "429" in error_str or "throttling" in error_str or "rate limit" in error_str:
            logger.warning("检测到限流错误，切换到备用模型", 
                         failure_count=self.primary_failure_count)
        else:
            logger.error("主模型调用失败", 
                        error=str(error), 
                        failure_count=self.primary_failure_count)
    
    def _should_retry_primary(self) -> bool:
        """判断是否应该重试主模型"""
        if self.last_failure_time is None:
            return True
        
        # 如果距离上次失败超过一定时间，尝试重新使用主模型
        time_since_failure = time.time() - self.last_failure_time
        retry_interval = self.backoff_delay * (2 ** min(self.primary_failure_count, 5))  # 指数退避
        
        should_retry = time_since_failure > retry_interval
        if should_retry:
            logger.info("尝试重新使用主模型", 
                       time_since_failure=time_since_failure,
                       retry_interval=retry_interval)
        
        return should_retry
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        config = self.primary_config if self.current_model_type == "primary" else self.fallback_config
        return {
            "model_type": self.current_model_type,
            "model_id": config["model_id"],
            "region": config["region"],
            "primary_failure_count": self.primary_failure_count,
            "last_failure_time": self.last_failure_time,
        }
    
    def reset_failure_state(self):
        """重置失败状态"""
        self.primary_failure_count = 0
        self.last_failure_time = None
        self.current_model_type = "primary"
        logger.info("重置模型失败状态")
    
    def force_fallback(self):
        """强制使用备用模型"""
        self.current_model_type = "fallback"
        logger.info("强制切换到备用模型")
    
    def force_primary(self):
        """强制使用主模型"""
        self.current_model_type = "primary"
        self.primary_failure_count = 0
        self.last_failure_time = None
        logger.info("强制切换到主模型")


# 全局模型管理器实例
model_manager = ModelFallbackManager()


def get_model():
    """获取可用模型的便捷函数"""
    return model_manager.get_model_with_fallback()


def get_model_info():
    """获取当前模型信息的便捷函数"""
    return model_manager.get_current_model_info()