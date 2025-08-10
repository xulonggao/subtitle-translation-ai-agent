"""
系统配置文件
"""
import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field


class BedrockConfig(BaseSettings):
    """Bedrock模型配置"""
    
    # 主要模型配置 - Claude 4 Sonnet
    primary_model_id: str = "us.anthropic.claude-opus-4-20250514-v1:0"
    
    # 备用模型配置 - Claude 3.7 Sonnet
    fallback_model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    # 通用配置
    region: str = "us-west-2"
    max_tokens: int = 4096
    temperature: float = 0.1  # 低温度确保翻译一致性
    memory_enabled: bool = True
    memory_duration_days: int = 30
    
    # 容错配置
    retry_attempts: int = 3
    backoff_delay: int = 2  # 秒
    
    class Config:
        env_prefix = "BEDROCK_"


class SystemConfig(BaseSettings):
    """系统配置"""
    
    # 环境配置
    environment: str = Field(default="local", description="运行环境: local, production")
    debug: bool = Field(default=True, description="调试模式")
    
    # 性能配置
    max_concurrent_translations: int = Field(default=3, description="最大并发翻译数")
    context_window_size: int = Field(default=50, description="上下文窗口大小")
    batch_size: int = Field(default=5, description="批量处理大小")
    memory_limit: str = Field(default="2GB", description="内存限制")
    
    # 缓存配置
    cache_strategy: str = Field(default="disk_based", description="缓存策略")
    cache_dir: str = Field(default="./cache", description="缓存目录")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="./logs/system.log", description="日志文件")
    
    # 数据库配置
    database_url: Optional[str] = Field(default=None, description="数据库连接URL")
    
    class Config:
        env_prefix = "SYSTEM_"


class TranslationConfig(BaseSettings):
    """翻译配置"""
    
    # 支持的语言
    supported_languages: List[str] = [
        "en",  # 英语
        "ja",  # 日语
        "ko",  # 韩语
        "th",  # 泰语
        "vi",  # 越南语
        "id",  # 印尼语
        "ms",  # 马来语
        "es",  # 西班牙语
        "pt",  # 葡萄牙语
        "ar",  # 阿拉伯语
    ]
    
    # 语言名称映射
    language_names: Dict[str, str] = {
        "en": "English",
        "ja": "Japanese",
        "ko": "Korean",
        "th": "Thai",
        "vi": "Vietnamese",
        "id": "Indonesian",
        "ms": "Malay",
        "es": "Spanish",
        "pt": "Portuguese",
        "ar": "Arabic",
    }
    
    # 质量控制
    quality_threshold: float = Field(default=0.8, description="翻译质量阈值")
    consistency_check: bool = Field(default=True, description="启用一致性检查")
    
    # 字幕特定配置
    max_subtitle_length: int = Field(default=15, description="字幕最大字符数")
    reading_speed_standard: float = Field(default=7.5, description="阅读速度标准(字符/秒)")
    
    class Config:
        env_prefix = "TRANSLATION_"


class WebConfig(BaseSettings):
    """Web界面配置"""
    
    host: str = Field(default="0.0.0.0", description="服务器地址")
    port: int = Field(default=8000, description="服务器端口")
    reload: bool = Field(default=True, description="自动重载")
    
    # 文件上传配置
    max_file_size: int = Field(default=100 * 1024 * 1024, description="最大文件大小(字节)")
    upload_dir: str = Field(default="./uploads", description="上传目录")
    
    # 安全配置
    secret_key: str = Field(default="your-secret-key-here", description="密钥")
    cors_origins: List[str] = Field(default=["*"], description="CORS允许的源")
    
    class Config:
        env_prefix = "WEB_"


# 全局配置实例
bedrock_config = BedrockConfig()
system_config = SystemConfig()
translation_config = TranslationConfig()
web_config = WebConfig()


def get_config():
    """获取完整配置"""
    return {
        "bedrock": bedrock_config,
        "system": system_config,
        "translation": translation_config,
        "web": web_config,
    }


def is_production():
    """判断是否为生产环境"""
    return system_config.environment == "production"


def is_local():
    """判断是否为本地环境"""
    return system_config.environment == "local"