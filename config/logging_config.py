"""
日志配置
"""
import os
import logging
import structlog
from pathlib import Path
from .config import system_config


def setup_logging():
    """设置日志配置"""
    
    # 创建日志目录
    log_dir = Path(system_config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置标准库logging
    logging.basicConfig(
        level=getattr(logging, system_config.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(system_config.log_file),
            logging.StreamHandler(),
        ],
    )
    
    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not system_config.debug 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """获取logger实例"""
    return structlog.get_logger(name)


# 预定义的logger
system_logger = get_logger("system")
agent_logger = get_logger("agent")
translation_logger = get_logger("translation")
api_logger = get_logger("api")