"""
配置模块测试
"""
import pytest
from config import (
    bedrock_config,
    system_config,
    translation_config,
    web_config,
    get_config,
    is_production,
    is_local,
)


def test_bedrock_config():
    """测试Bedrock配置"""
    assert bedrock_config.primary_model_id == "us.anthropic.claude-opus-4-20250514-v1:0"
    assert bedrock_config.fallback_model_id == "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    assert bedrock_config.region == "us-west-2"
    assert bedrock_config.temperature == 0.1
    assert bedrock_config.memory_enabled is True


def test_system_config():
    """测试系统配置"""
    assert system_config.environment in ["local", "production"]
    assert system_config.max_concurrent_translations > 0
    assert system_config.context_window_size > 0
    assert system_config.batch_size > 0


def test_translation_config():
    """测试翻译配置"""
    expected_languages = [
        "en", "ja", "ko", "th", "vi", 
        "id", "ms", "es", "pt", "ar"
    ]
    assert translation_config.supported_languages == expected_languages
    assert len(translation_config.language_names) == len(expected_languages)
    assert translation_config.quality_threshold > 0
    assert translation_config.quality_threshold <= 1.0


def test_web_config():
    """测试Web配置"""
    assert web_config.port > 0
    assert web_config.port < 65536
    assert web_config.max_file_size > 0


def test_get_config():
    """测试获取完整配置"""
    config = get_config()
    assert "bedrock" in config
    assert "system" in config
    assert "translation" in config
    assert "web" in config


def test_environment_detection():
    """测试环境检测"""
    # 默认应该是本地环境
    assert is_local() is True
    assert is_production() is False


if __name__ == "__main__":
    pytest.main([__file__])