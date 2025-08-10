"""
配置模块
"""
from .config import (
    bedrock_config,
    system_config,
    translation_config,
    web_config,
    get_config,
    is_production,
    is_local,
)
from .logging_config import setup_logging, get_logger

__all__ = [
    "bedrock_config",
    "system_config", 
    "translation_config",
    "web_config",
    "get_config",
    "is_production",
    "is_local",
    "setup_logging",
    "get_logger",
]