"""
模型容错管理器测试
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from agents.model_manager import ModelFallbackManager, get_model, get_model_info


class TestModelFallbackManager:
    """模型容错管理器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.manager = ModelFallbackManager()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.manager.current_model_type == "primary"
        assert self.manager.primary_failure_count == 0
        assert self.manager.last_failure_time is None
        assert len(self.manager.model_cache) == 0
    
    def test_primary_config(self):
        """测试主模型配置"""
        config = self.manager.primary_config
        assert "us.anthropic.claude-opus-4-20250514-v1:0" in config["model_id"]
        assert config["region"] == "us-west-2"
        assert config["temperature"] == 0.1
    
    def test_fallback_config(self):
        """测试备用模型配置"""
        config = self.manager.fallback_config
        assert "us.anthropic.claude-3-7-sonnet-20250219-v1:0" in config["model_id"]
        assert config["region"] == "us-west-2"
        assert config["temperature"] == 0.1
    
    @patch('agents.model_manager.BedrockModel')
    def test_get_model_success(self, mock_bedrock_model):
        """测试成功获取模型"""
        mock_model = Mock()
        mock_bedrock_model.return_value = mock_model
        
        with patch.object(self.manager, '_test_model_availability', return_value=True):
            model = self.manager.get_model_with_fallback()
            
            assert model == mock_model
            assert self.manager.current_model_type == "primary"
            assert self.manager.primary_failure_count == 0
    
    @patch('agents.model_manager.BedrockModel')
    def test_fallback_on_primary_failure(self, mock_bedrock_model):
        """测试主模型失败时的备用机制"""
        # 主模型失败
        mock_bedrock_model.side_effect = [Exception("Primary model failed"), Mock()]
        
        with patch.object(self.manager, '_test_model_availability', return_value=True):
            model = self.manager.get_model_with_fallback()
            
            assert model is not None
            assert self.manager.current_model_type == "fallback"
            assert self.manager.primary_failure_count == 1
    
    @patch('agents.model_manager.BedrockModel')
    def test_throttling_error_detection(self, mock_bedrock_model):
        """测试限流错误检测"""
        # 模拟429限流错误
        throttling_error = Exception("429 Too Many Requests")
        mock_bedrock_model.side_effect = [throttling_error, Mock()]
        
        with patch.object(self.manager, '_test_model_availability', return_value=True):
            model = self.manager.get_model_with_fallback()
            
            assert model is not None
            assert self.manager.current_model_type == "fallback"
            assert self.manager.primary_failure_count == 1
    
    def test_handle_primary_failure(self):
        """测试主模型失败处理"""
        initial_count = self.manager.primary_failure_count
        initial_time = self.manager.last_failure_time
        
        error = Exception("Test error")
        self.manager._handle_primary_failure(error)
        
        assert self.manager.primary_failure_count == initial_count + 1
        assert self.manager.last_failure_time > initial_time
    
    def test_should_retry_primary(self):
        """测试主模型重试逻辑"""
        # 初始状态应该重试
        assert self.manager._should_retry_primary() is True
        
        # 设置失败状态
        self.manager.primary_failure_count = 1
        self.manager.last_failure_time = time.time()
        
        # 刚失败不应该重试
        assert self.manager._should_retry_primary() is False
        
        # 模拟时间过去
        self.manager.last_failure_time = time.time() - 100
        assert self.manager._should_retry_primary() is True
    
    def test_get_current_model_info(self):
        """测试获取当前模型信息"""
        info = self.manager.get_current_model_info()
        
        assert "model_type" in info
        assert "model_id" in info
        assert "region" in info
        assert "primary_failure_count" in info
        assert "last_failure_time" in info
        
        assert info["model_type"] == "primary"
        assert info["primary_failure_count"] == 0
    
    def test_reset_failure_state(self):
        """测试重置失败状态"""
        # 设置失败状态
        self.manager.primary_failure_count = 5
        self.manager.last_failure_time = time.time()
        self.manager.current_model_type = "fallback"
        
        # 重置
        self.manager.reset_failure_state()
        
        assert self.manager.primary_failure_count == 0
        assert self.manager.last_failure_time is None
        assert self.manager.current_model_type == "primary"
    
    def test_force_fallback(self):
        """测试强制使用备用模型"""
        self.manager.force_fallback()
        assert self.manager.current_model_type == "fallback"
    
    def test_force_primary(self):
        """测试强制使用主模型"""
        # 先设置为备用模型
        self.manager.current_model_type = "fallback"
        self.manager.primary_failure_count = 3
        self.manager.last_failure_time = time.time()
        
        # 强制切换到主模型
        self.manager.force_primary()
        
        assert self.manager.current_model_type == "primary"
        assert self.manager.primary_failure_count == 0
        assert self.manager.last_failure_time is None
    
    @patch('agents.model_manager.BedrockModel')
    def test_model_caching(self, mock_bedrock_model):
        """测试模型缓存"""
        mock_model = Mock()
        mock_bedrock_model.return_value = mock_model
        
        # 第一次获取
        model1 = self.manager._get_model("primary")
        assert model1 == mock_model
        assert "primary" in self.manager.model_cache
        
        # 第二次获取应该使用缓存
        model2 = self.manager._get_model("primary")
        assert model2 == mock_model
        assert model1 is model2  # 应该是同一个实例
        
        # BedrockModel应该只被调用一次
        assert mock_bedrock_model.call_count == 1
    
    @patch('agents.model_manager.BedrockModel')
    def test_both_models_fail(self, mock_bedrock_model):
        """测试两个模型都失败的情况"""
        mock_bedrock_model.side_effect = Exception("Both models failed")
        
        with pytest.raises(RuntimeError, match="所有模型都不可用"):
            self.manager.get_model_with_fallback()


def test_convenience_functions():
    """测试便捷函数"""
    with patch('agents.model_manager.model_manager') as mock_manager:
        mock_model = Mock()
        mock_info = {"model_type": "primary"}
        
        mock_manager.get_model_with_fallback.return_value = mock_model
        mock_manager.get_current_model_info.return_value = mock_info
        
        # 测试get_model函数
        model = get_model()
        assert model == mock_model
        mock_manager.get_model_with_fallback.assert_called_once()
        
        # 测试get_model_info函数
        info = get_model_info()
        assert info == mock_info
        mock_manager.get_current_model_info.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])