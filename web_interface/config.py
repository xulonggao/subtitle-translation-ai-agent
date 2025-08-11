#!/usr/bin/env python3
"""
Web界面配置文件
"""

import os
from pathlib import Path
from typing import Dict, Any

class WebConfig:
    """Web界面配置类"""
    
    # 服务器配置
    SERVER_HOST = os.getenv("STREAMLIT_HOST", "localhost")
    SERVER_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
    
    # 应用配置
    APP_TITLE = "字幕翻译系统"
    APP_ICON = "🎬"
    PAGE_LAYOUT = "wide"
    
    # 文件上传配置
    MAX_FILE_SIZE_MB = 50
    ALLOWED_FILE_TYPES = ['srt', 'vtt', 'ass', 'ssa', 'txt']
    UPLOAD_DIR = Path("uploads")
    
    # 翻译配置
    DEFAULT_QUALITY_LEVEL = "high"
    MAX_CONCURRENT_TASKS = 5
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_TIMEOUT_MINUTES = 30
    
    # 支持的语言
    SUPPORTED_LANGUAGES = {
        "zh-CN": "中文(简体)",
        "zh-TW": "中文(繁体)",
        "en-US": "英语(美国)",
        "en-GB": "英语(英国)",
        "ja-JP": "日语",
        "ko-KR": "韩语",
        "es-ES": "西班牙语",
        "fr-FR": "法语",
        "de-DE": "德语",
        "it-IT": "意大利语",
        "pt-BR": "葡萄牙语(巴西)",
        "ru-RU": "俄语",
        "ar-SA": "阿拉伯语",
        "th-TH": "泰语",
        "vi-VN": "越南语"
    }
    
    # 质量等级配置
    QUALITY_LEVELS = {
        "standard": {
            "name": "标准",
            "description": "快速翻译，适合日常使用",
            "features": ["基础翻译", "简单校对"]
        },
        "high": {
            "name": "高质量",
            "description": "高质量翻译，适合专业内容",
            "features": ["上下文分析", "术语一致性", "文化适应"]
        },
        "premium": {
            "name": "专业级",
            "description": "专业级翻译，适合商业用途",
            "features": ["深度上下文分析", "专业术语管理", "文化本地化", "多轮质量检查"]
        }
    }
    
    # UI主题配置
    THEME_CONFIG = {
        "primary_color": "#1f77b4",
        "background_color": "#ffffff",
        "secondary_background_color": "#f0f2f6",
        "text_color": "#262730",
        "font": "sans serif"
    }
    
    # 监控配置
    MONITORING_CONFIG = {
        "auto_refresh_interval": 10,  # 秒
        "max_history_items": 100,
        "progress_update_interval": 2  # 秒
    }
    
    # 安全配置
    SECURITY_CONFIG = {
        "enable_file_validation": True,
        "max_file_count": 20,
        "allowed_mime_types": [
            "text/plain",
            "application/x-subrip",
            "text/vtt"
        ]
    }
    
    @classmethod
    def get_language_options(cls) -> list:
        """获取语言选项列表"""
        return list(cls.SUPPORTED_LANGUAGES.keys())
    
    @classmethod
    def get_language_name(cls, code: str) -> str:
        """获取语言名称"""
        return cls.SUPPORTED_LANGUAGES.get(code, code)
    
    @classmethod
    def get_quality_level_info(cls, level: str) -> Dict[str, Any]:
        """获取质量等级信息"""
        return cls.QUALITY_LEVELS.get(level, cls.QUALITY_LEVELS["standard"])
    
    @classmethod
    def validate_file_type(cls, filename: str) -> bool:
        """验证文件类型"""
        if not filename:
            return False
        
        extension = filename.split('.')[-1].lower()
        return extension in cls.ALLOWED_FILE_TYPES
    
    @classmethod
    def get_upload_path(cls) -> Path:
        """获取上传目录路径"""
        upload_path = cls.UPLOAD_DIR
        upload_path.mkdir(exist_ok=True)
        return upload_path

# 创建全局配置实例
config = WebConfig()