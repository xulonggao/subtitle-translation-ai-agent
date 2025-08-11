#!/usr/bin/env python3
"""
Strands Agent配置文件
用于本地开发和AgentCore部署
"""
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class DeploymentEnvironment(Enum):
    """部署环境"""
    LOCAL_DEVELOPMENT = "local_development"
    AGENTCORE_STAGING = "agentcore_staging"
    AGENTCORE_PRODUCTION = "agentcore_production"

class ModelTier(Enum):
    """模型层级"""
    PREMIUM = "premium"     # Claude 4 Sonnet
    STANDARD = "standard"   # Claude 3.7 Sonnet
    BASIC = "basic"         # Claude 3 Haiku

@dataclass
class AgentDeploymentConfig:
    """Agent部署配置"""
    # Agent基本信息
    agent_name: str = "SubtitleTranslationAgent"
    agent_version: str = "1.0.0"
    agent_description: str = "专业的字幕翻译Agent，提供高精度、上下文感知的多语言字幕翻译服务"
    
    # 部署环境
    environment: DeploymentEnvironment = DeploymentEnvironment.LOCAL_DEVELOPMENT
    
    # 模型配置
    primary_model: str = "us.anthropic.claude-4-sonnet-20241022-v2:0"
    fallback_model: str = "us.anthropic.claude-3-7-sonnet-20241022-v2:0"
    model_region: str = "us-east-1"
    max_tokens: int = 4000
    temperature: float = 0.3
    top_p: float = 0.9
    
    # 工具配置
    tools: List[str] = None
    
    # 资源限制
    max_concurrent_requests: int = 10
    timeout_seconds: int = 300
    memory_limit_mb: int = 1024
    
    # 日志配置
    log_level: str = "INFO"
    enable_detailed_logging: bool = True
    enable_performance_metrics: bool = True
    
    # 翻译特定配置
    supported_languages: List[str] = None
    default_quality_level: str = "high"
    enable_cultural_adaptation: bool = True
    enable_terminology_consistency: bool = True
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = [
                "parse_srt_file",
                "analyze_story_context", 
                "translate_with_context",
                "validate_translation_quality",
                "export_translated_srt"
            ]
        
        if self.supported_languages is None:
            self.supported_languages = [
                "en",  # 英语
                "ja",  # 日语
                "ko",  # 韩语
                "th",  # 泰语
                "vi",  # 越南语
                "id",  # 印尼语
                "ms",  # 马来语
                "es",  # 西班牙语
                "pt",  # 葡萄牙语
                "ar"   # 阿拉伯语
            ]
    
    def to_agentcore_config(self) -> Dict[str, Any]:
        """转换为AgentCore部署配置格式"""
        return {
            "agent": {
                "name": self.agent_name,
                "version": self.agent_version,
                "description": self.agent_description,
                "runtime": "bedrock-agentcore",
                "environment": self.environment.value,
                "model": {
                    "primary": {
                        "model_id": self.primary_model,
                        "region": self.model_region,
                        "parameters": {
                            "max_tokens": self.max_tokens,
                            "temperature": self.temperature,
                            "top_p": self.top_p
                        }
                    },
                    "fallback": {
                        "model_id": self.fallback_model,
                        "region": self.model_region,
                        "parameters": {
                            "max_tokens": self.max_tokens,
                            "temperature": self.temperature + 0.1,  # 稍微提高fallback的创造性
                            "top_p": self.top_p
                        }
                    }
                },
                "tools": [
                    {
                        "name": tool_name,
                        "enabled": True,
                        "timeout_seconds": 30
                    } for tool_name in self.tools
                ],
                "resources": {
                    "max_concurrent_requests": self.max_concurrent_requests,
                    "timeout_seconds": self.timeout_seconds,
                    "memory_limit_mb": self.memory_limit_mb,
                    "cpu_limit": "1000m",  # 1 CPU core
                    "storage_limit_mb": 512
                },
                "logging": {
                    "level": self.log_level,
                    "detailed": self.enable_detailed_logging,
                    "performance_metrics": self.enable_performance_metrics,
                    "retention_days": 30
                },
                "features": {
                    "supported_languages": self.supported_languages,
                    "default_quality_level": self.default_quality_level,
                    "cultural_adaptation": self.enable_cultural_adaptation,
                    "terminology_consistency": self.enable_terminology_consistency,
                    "auto_scaling": True,
                    "health_check_enabled": True
                }
            }
        }
    
    def to_local_config(self) -> Dict[str, Any]:
        """转换为本地开发配置格式"""
        return {
            "agent_name": self.agent_name,
            "model_config": {
                "model_id": self.primary_model,
                "region": self.model_region,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "fallback_model_id": self.fallback_model
            },
            "tools": self.tools,
            "supported_languages": self.supported_languages,
            "translation_config": {
                "quality_level": self.default_quality_level,
                "cultural_adaptation": self.enable_cultural_adaptation,
                "terminology_consistency": self.enable_terminology_consistency,
                "batch_size": 10,
                "max_retries": 3
            },
            "development": {
                "debug_mode": True,
                "verbose_logging": True,
                "test_mode": False,
                "mock_responses": False
            },
            "performance": {
                "enable_caching": True,
                "cache_ttl_seconds": 3600,
                "enable_metrics": self.enable_performance_metrics
            }
        }
    
    def to_docker_config(self) -> Dict[str, Any]:
        """转换为Docker容器配置"""
        return {
            "image": "bedrock-strands-agent:latest",
            "environment": {
                "AGENT_NAME": self.agent_name,
                "AGENT_VERSION": self.agent_version,
                "MODEL_ID": self.primary_model,
                "MODEL_REGION": self.model_region,
                "LOG_LEVEL": self.log_level,
                "MAX_CONCURRENT_REQUESTS": str(self.max_concurrent_requests),
                "TIMEOUT_SECONDS": str(self.timeout_seconds)
            },
            "resources": {
                "memory": f"{self.memory_limit_mb}Mi",
                "cpu": "1000m"
            },
            "ports": [
                {"containerPort": 8080, "name": "http"},
                {"containerPort": 9090, "name": "metrics"}
            ],
            "health_check": {
                "path": "/health",
                "port": 8080,
                "initial_delay_seconds": 30,
                "period_seconds": 10
            }
        }

# 预定义配置实例
DEFAULT_CONFIG = AgentDeploymentConfig()

DEVELOPMENT_CONFIG = AgentDeploymentConfig(
    environment=DeploymentEnvironment.LOCAL_DEVELOPMENT,
    max_concurrent_requests=5,
    timeout_seconds=120,
    memory_limit_mb=512,
    log_level="DEBUG",
    enable_detailed_logging=True
)

STAGING_CONFIG = AgentDeploymentConfig(
    environment=DeploymentEnvironment.AGENTCORE_STAGING,
    max_concurrent_requests=20,
    timeout_seconds=300,
    memory_limit_mb=1024,
    log_level="INFO",
    enable_detailed_logging=True
)

PRODUCTION_CONFIG = AgentDeploymentConfig(
    environment=DeploymentEnvironment.AGENTCORE_PRODUCTION,
    max_concurrent_requests=50,
    timeout_seconds=600,
    memory_limit_mb=2048,
    log_level="WARN",
    enable_detailed_logging=False,
    enable_performance_metrics=True
)

# 语言特定配置
LANGUAGE_SPECIFIC_CONFIGS = {
    "en": {
        "name": "English",
        "max_chars_per_line": 42,
        "reading_speed_cps": 17,
        "honorific_system": False,
        "cultural_notes": ["Western cultural references", "Idiomatic expressions"]
    },
    "ja": {
        "name": "Japanese",
        "max_chars_per_line": 20,
        "reading_speed_cps": 8,
        "honorific_system": True,
        "cultural_notes": ["Keigo system", "Confucian values", "Seasonal references"]
    },
    "ko": {
        "name": "Korean",
        "max_chars_per_line": 18,
        "reading_speed_cps": 9,
        "honorific_system": True,
        "cultural_notes": ["Honorific levels", "Age hierarchy", "Confucian values"]
    },
    "ar": {
        "name": "Arabic",
        "max_chars_per_line": 35,
        "reading_speed_cps": 15,
        "honorific_system": False,
        "rtl_text": True,
        "cultural_notes": ["Islamic values", "Religious sensitivity", "RTL text direction"]
    },
    "th": {
        "name": "Thai",
        "max_chars_per_line": 25,
        "reading_speed_cps": 12,
        "honorific_system": True,
        "cultural_notes": ["Buddhist culture", "Royal respect", "Theravada Buddhism"]
    },
    "vi": {
        "name": "Vietnamese",
        "max_chars_per_line": 30,
        "reading_speed_cps": 14,
        "honorific_system": True,
        "cultural_notes": ["Confucian influence", "Family hierarchy", "Tone markers"]
    },
    "id": {
        "name": "Indonesian",
        "max_chars_per_line": 35,
        "reading_speed_cps": 16,
        "honorific_system": False,
        "cultural_notes": ["Islamic influence", "Pancasila values", "Diverse cultures"]
    },
    "ms": {
        "name": "Malay",
        "max_chars_per_line": 35,
        "reading_speed_cps": 16,
        "honorific_system": False,
        "cultural_notes": ["Islamic influence", "Malay customs", "Multicultural society"]
    },
    "es": {
        "name": "Spanish",
        "max_chars_per_line": 38,
        "reading_speed_cps": 18,
        "honorific_system": False,
        "cultural_notes": ["Hispanic culture", "Regional variations", "Catholic influence"]
    },
    "pt": {
        "name": "Portuguese",
        "max_chars_per_line": 38,
        "reading_speed_cps": 18,
        "honorific_system": False,
        "cultural_notes": ["Lusophone culture", "Brazilian vs European", "Catholic influence"]
    }
}

def get_config_for_environment(env: DeploymentEnvironment) -> AgentDeploymentConfig:
    """根据环境获取配置"""
    config_map = {
        DeploymentEnvironment.LOCAL_DEVELOPMENT: DEVELOPMENT_CONFIG,
        DeploymentEnvironment.AGENTCORE_STAGING: STAGING_CONFIG,
        DeploymentEnvironment.AGENTCORE_PRODUCTION: PRODUCTION_CONFIG
    }
    return config_map.get(env, DEFAULT_CONFIG)

def get_language_config(language_code: str) -> Dict[str, Any]:
    """获取语言特定配置"""
    return LANGUAGE_SPECIFIC_CONFIGS.get(language_code, LANGUAGE_SPECIFIC_CONFIGS["en"])

def validate_config(config: AgentDeploymentConfig) -> List[str]:
    """验证配置有效性"""
    issues = []
    
    # 检查必要字段
    if not config.agent_name:
        issues.append("Agent名称不能为空")
    
    if not config.primary_model:
        issues.append("主要模型不能为空")
    
    if config.max_tokens <= 0:
        issues.append("max_tokens必须大于0")
    
    if not (0.0 <= config.temperature <= 2.0):
        issues.append("temperature必须在0.0-2.0之间")
    
    if not (0.0 <= config.top_p <= 1.0):
        issues.append("top_p必须在0.0-1.0之间")
    
    # 检查资源限制
    if config.max_concurrent_requests <= 0:
        issues.append("max_concurrent_requests必须大于0")
    
    if config.timeout_seconds <= 0:
        issues.append("timeout_seconds必须大于0")
    
    if config.memory_limit_mb <= 0:
        issues.append("memory_limit_mb必须大于0")
    
    # 检查支持的语言
    if not config.supported_languages:
        issues.append("supported_languages不能为空")
    
    return issues

if __name__ == "__main__":
    # 测试配置生成
    print("=== 开发环境配置 ===")
    dev_config = get_config_for_environment(DeploymentEnvironment.LOCAL_DEVELOPMENT)
    print(f"Agent名称: {dev_config.agent_name}")
    print(f"模型: {dev_config.primary_model}")
    print(f"支持语言: {', '.join(dev_config.supported_languages)}")
    
    print("\n=== 生产环境配置 ===")
    prod_config = get_config_for_environment(DeploymentEnvironment.AGENTCORE_PRODUCTION)
    print(f"并发请求: {prod_config.max_concurrent_requests}")
    print(f"内存限制: {prod_config.memory_limit_mb}MB")
    print(f"日志级别: {prod_config.log_level}")
    
    print("\n=== AgentCore配置示例 ===")
    agentcore_config = prod_config.to_agentcore_config()
    print(json.dumps(agentcore_config, indent=2, ensure_ascii=False))
    
    print("\n=== 配置验证 ===")
    issues = validate_config(dev_config)
    if issues:
        print("发现问题:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("✅ 配置验证通过")