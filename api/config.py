#!/usr/bin/env python3
"""
API配置管理
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field

class APISettings(BaseSettings):
    """API设置"""
    
    # 基础配置
    app_name: str = Field(default="字幕翻译系统 API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    workers: int = Field(default=1, env="API_WORKERS")
    
    # 安全配置
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS配置
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # 数据库配置
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis配置
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # 文件上传配置
    max_file_size: int = Field(default=50*1024*1024, env="MAX_FILE_SIZE")  # 50MB
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    allowed_file_types: List[str] = Field(
        default=["srt", "vtt", "ass", "ssa", "txt"],
        env="ALLOWED_FILE_TYPES"
    )
    
    # 速率限制配置
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    default_rate_limit_per_minute: int = Field(default=60, env="DEFAULT_RATE_LIMIT_PER_MINUTE")
    default_rate_limit_per_hour: int = Field(default=1000, env="DEFAULT_RATE_LIMIT_PER_HOUR")
    default_rate_limit_per_day: int = Field(default=10000, env="DEFAULT_RATE_LIMIT_PER_DAY")
    
    # 翻译配置
    max_concurrent_tasks: int = Field(default=5, env="MAX_CONCURRENT_TASKS")
    default_timeout_minutes: int = Field(default=30, env="DEFAULT_TIMEOUT_MINUTES")
    supported_languages: List[str] = Field(
        default=[
            "zh-CN", "zh-TW", "en-US", "en-GB", "ja-JP", "ko-KR",
            "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "ru-RU",
            "ar-SA", "th-TH", "vi-VN"
        ],
        env="SUPPORTED_LANGUAGES"
    )
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # 监控配置
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # 外部服务配置
    translation_service_url: Optional[str] = Field(default=None, env="TRANSLATION_SERVICE_URL")
    translation_service_timeout: int = Field(default=300, env="TRANSLATION_SERVICE_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 创建全局设置实例
settings = APISettings()

# 环境特定配置
class DevelopmentSettings(APISettings):
    """开发环境配置"""
    debug: bool = True
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

class ProductionSettings(APISettings):
    """生产环境配置"""
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = []  # 应该设置具体的域名
    workers: int = 4

class TestingSettings(APISettings):
    """测试环境配置"""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///./test.db"
    rate_limit_enabled: bool = False

def get_settings() -> APISettings:
    """根据环境获取配置"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

# 配置验证
def validate_settings(settings: APISettings) -> bool:
    """验证配置"""
    errors = []
    
    # 验证必需的配置
    if not settings.secret_key or settings.secret_key == "your-secret-key-here":
        errors.append("SECRET_KEY must be set to a secure value")
    
    if settings.max_file_size <= 0:
        errors.append("MAX_FILE_SIZE must be greater than 0")
    
    if settings.access_token_expire_minutes <= 0:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
    
    if not settings.supported_languages:
        errors.append("SUPPORTED_LANGUAGES cannot be empty")
    
    # 验证端口范围
    if not (1 <= settings.port <= 65535):
        errors.append("API_PORT must be between 1 and 65535")
    
    if not (1 <= settings.metrics_port <= 65535):
        errors.append("METRICS_PORT must be between 1 and 65535")
    
    # 验证日志级别
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.log_level.upper() not in valid_log_levels:
        errors.append(f"LOG_LEVEL must be one of {valid_log_levels}")
    
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True

# 配置信息打印
def print_settings_info(settings: APISettings):
    """打印配置信息"""
    print("⚙️ API配置信息:")
    print(f"  应用名称: {settings.app_name}")
    print(f"  版本: {settings.app_version}")
    print(f"  调试模式: {settings.debug}")
    print(f"  服务地址: {settings.host}:{settings.port}")
    print(f"  工作进程: {settings.workers}")
    print(f"  日志级别: {settings.log_level}")
    print(f"  最大文件大小: {settings.max_file_size // (1024*1024)}MB")
    print(f"  支持的语言: {len(settings.supported_languages)}种")
    print(f"  速率限制: {'启用' if settings.rate_limit_enabled else '禁用'}")
    print(f"  指标监控: {'启用' if settings.enable_metrics else '禁用'}")

# 导出配置
__all__ = [
    "APISettings",
    "DevelopmentSettings", 
    "ProductionSettings",
    "TestingSettings",
    "settings",
    "get_settings",
    "validate_settings",
    "print_settings_info"
]