#!/usr/bin/env python3
"""
AgentCore部署准备脚本
生成部署配置文件和验证Agent兼容性
"""
import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from agent_config import (
    AgentDeploymentConfig, 
    DeploymentEnvironment,
    PRODUCTION_CONFIG,
    STAGING_CONFIG,
    validate_config,
    get_language_config
)

class DeploymentPreparation:
    """部署准备工具"""
    
    def __init__(self, output_dir: str = "deployment"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_agentcore_manifest(self, config: AgentDeploymentConfig) -> Dict[str, Any]:
        """生成AgentCore部署清单"""
        manifest = {
            "apiVersion": "agentcore.aws.amazon.com/v1",
            "kind": "Agent",
            "metadata": {
                "name": config.agent_name.lower().replace("_", "-"),
                "namespace": "subtitle-translation",
                "labels": {
                    "app": "subtitle-translation-agent",
                    "version": config.agent_version,
                    "environment": config.environment.value
                },
                "annotations": {
                    "agentcore.aws.amazon.com/description": config.agent_description,
                    "agentcore.aws.amazon.com/created": datetime.now().isoformat()
                }
            },
            "spec": {
                "runtime": {
                    "type": "bedrock-strands",
                    "version": "1.0"
                },
                "model": {
                    "primary": {
                        "provider": "bedrock",
                        "modelId": config.primary_model,
                        "region": config.model_region,
                        "parameters": {
                            "maxTokens": config.max_tokens,
                            "temperature": config.temperature,
                            "topP": config.top_p
                        }
                    },
                    "fallback": {
                        "provider": "bedrock",
                        "modelId": config.fallback_model,
                        "region": config.model_region,
                        "parameters": {
                            "maxTokens": config.max_tokens,
                            "temperature": config.temperature + 0.1,
                            "topP": config.top_p
                        }
                    }
                },
                "tools": [
                    {
                        "name": tool_name,
                        "type": "function",
                        "enabled": True,
                        "timeout": "30s"
                    } for tool_name in config.tools
                ],
                "resources": {
                    "requests": {
                        "memory": f"{config.memory_limit_mb}Mi",
                        "cpu": "500m"
                    },
                    "limits": {
                        "memory": f"{config.memory_limit_mb * 2}Mi",
                        "cpu": "1000m"
                    }
                },
                "scaling": {
                    "minReplicas": 1,
                    "maxReplicas": 10,
                    "targetConcurrency": config.max_concurrent_requests
                },
                "networking": {
                    "ports": [
                        {
                            "name": "http",
                            "port": 8080,
                            "protocol": "TCP"
                        },
                        {
                            "name": "metrics",
                            "port": 9090,
                            "protocol": "TCP"
                        }
                    ]
                },
                "monitoring": {
                    "healthCheck": {
                        "path": "/health",
                        "port": 8080,
                        "initialDelaySeconds": 30,
                        "periodSeconds": 10,
                        "timeoutSeconds": 5,
                        "failureThreshold": 3
                    },
                    "metrics": {
                        "enabled": config.enable_performance_metrics,
                        "path": "/metrics",
                        "port": 9090
                    }
                },
                "logging": {
                    "level": config.log_level,
                    "format": "json",
                    "destinations": ["cloudwatch", "s3"],
                    "retention": "30d"
                },
                "security": {
                    "iamRole": "arn:aws:iam::ACCOUNT:role/AgentCoreExecutionRole",
                    "networkPolicy": "default",
                    "podSecurityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 1000,
                        "fsGroup": 2000
                    }
                }
            }
        }
        
        return manifest
    
    def generate_docker_compose(self, config: AgentDeploymentConfig) -> Dict[str, Any]:
        """生成Docker Compose配置（用于本地测试）"""
        compose = {
            "version": "3.8",
            "services": {
                "subtitle-translation-agent": {
                    "image": "bedrock-strands-agent:latest",
                    "container_name": "subtitle-translation-agent",
                    "environment": {
                        "AGENT_NAME": config.agent_name,
                        "AGENT_VERSION": config.agent_version,
                        "MODEL_ID": config.primary_model,
                        "FALLBACK_MODEL_ID": config.fallback_model,
                        "MODEL_REGION": config.model_region,
                        "MAX_TOKENS": str(config.max_tokens),
                        "TEMPERATURE": str(config.temperature),
                        "TOP_P": str(config.top_p),
                        "LOG_LEVEL": config.log_level,
                        "MAX_CONCURRENT_REQUESTS": str(config.max_concurrent_requests),
                        "TIMEOUT_SECONDS": str(config.timeout_seconds),
                        "SUPPORTED_LANGUAGES": ",".join(config.supported_languages)
                    },
                    "ports": [
                        "8080:8080",  # HTTP API
                        "9090:9090"   # Metrics
                    ],
                    "volumes": [
                        "./logs:/app/logs",
                        "./cache:/app/cache"
                    ],
                    "deploy": {
                        "resources": {
                            "limits": {
                                "memory": f"{config.memory_limit_mb}M",
                                "cpus": "1.0"
                            },
                            "reservations": {
                                "memory": f"{config.memory_limit_mb // 2}M",
                                "cpus": "0.5"
                            }
                        }
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "40s"
                    },
                    "restart": "unless-stopped"
                }
            },
            "networks": {
                "agent-network": {
                    "driver": "bridge"
                }
            },
            "volumes": {
                "agent-logs": {},
                "agent-cache": {}
            }
        }
        
        return compose
    
    def generate_terraform_config(self, config: AgentDeploymentConfig) -> str:
        """生成Terraform配置"""
        terraform_config = f'''
# Terraform configuration for Subtitle Translation Agent deployment
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{config.model_region}"
}}

# IAM Role for Agent execution
resource "aws_iam_role" "agent_execution_role" {{
  name = "SubtitleTranslationAgentExecutionRole"
  
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {{
          Service = "agentcore.amazonaws.com"
        }}
      }}
    ]
  }})
}}

# IAM Policy for Bedrock access
resource "aws_iam_role_policy" "bedrock_access" {{
  name = "BedrockAccess"
  role = aws_iam_role.agent_execution_role.id
  
  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:{config.model_region}::foundation-model/{config.primary_model}",
          "arn:aws:bedrock:{config.model_region}::foundation-model/{config.fallback_model}"
        ]
      }}
    ]
  }})
}}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "agent_logs" {{
  name              = "/aws/agentcore/subtitle-translation-agent"
  retention_in_days = 30
}}

# S3 Bucket for artifacts
resource "aws_s3_bucket" "agent_artifacts" {{
  bucket = "subtitle-translation-agent-artifacts-${{random_id.bucket_suffix.hex}}"
}}

resource "random_id" "bucket_suffix" {{
  byte_length = 4
}}

# AgentCore Agent Resource
resource "aws_agentcore_agent" "subtitle_translation_agent" {{
  name        = "{config.agent_name.lower().replace('_', '-')}"
  description = "{config.agent_description}"
  
  runtime {{
    type    = "bedrock-strands"
    version = "1.0"
  }}
  
  model {{
    primary {{
      provider  = "bedrock"
      model_id  = "{config.primary_model}"
      region    = "{config.model_region}"
      
      parameters {{
        max_tokens  = {config.max_tokens}
        temperature = {config.temperature}
        top_p       = {config.top_p}
      }}
    }}
    
    fallback {{
      provider  = "bedrock"
      model_id  = "{config.fallback_model}"
      region    = "{config.model_region}"
      
      parameters {{
        max_tokens  = {config.max_tokens}
        temperature = {config.temperature + 0.1}
        top_p       = {config.top_p}
      }}
    }}
  }}
  
  resources {{
    memory_limit_mb         = {config.memory_limit_mb}
    max_concurrent_requests = {config.max_concurrent_requests}
    timeout_seconds        = {config.timeout_seconds}
  }}
  
  logging {{
    level           = "{config.log_level}"
    cloudwatch_group = aws_cloudwatch_log_group.agent_logs.name
  }}
  
  iam_role = aws_iam_role.agent_execution_role.arn
  
  tags = {{
    Environment = "{config.environment.value}"
    Version     = "{config.agent_version}"
    Application = "subtitle-translation"
  }}
}}

# Outputs
output "agent_endpoint" {{
  description = "Agent API endpoint"
  value       = aws_agentcore_agent.subtitle_translation_agent.endpoint
}}

output "agent_arn" {{
  description = "Agent ARN"
  value       = aws_agentcore_agent.subtitle_translation_agent.arn
}}

output "log_group_name" {{
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.agent_logs.name
}}
'''
        return terraform_config
    
    def generate_deployment_scripts(self, config: AgentDeploymentConfig) -> Dict[str, str]:
        """生成部署脚本"""
        scripts = {}
        
        # 部署脚本
        scripts["deploy.sh"] = f'''#!/bin/bash
set -e

echo "🚀 开始部署字幕翻译Agent到AgentCore..."

# 检查必要的工具
command -v aws >/dev/null 2>&1 || {{ echo "❌ AWS CLI未安装"; exit 1; }}
command -v kubectl >/dev/null 2>&1 || {{ echo "❌ kubectl未安装"; exit 1; }}

# 设置环境变量
export AGENT_NAME="{config.agent_name}"
export AGENT_VERSION="{config.agent_version}"
export ENVIRONMENT="{config.environment.value}"

echo "📋 部署配置:"
echo "  Agent名称: $AGENT_NAME"
echo "  版本: $AGENT_VERSION"
echo "  环境: $ENVIRONMENT"

# 验证AWS凭证
echo "🔐 验证AWS凭证..."
aws sts get-caller-identity > /dev/null || {{ echo "❌ AWS凭证无效"; exit 1; }}

# 应用Kubernetes清单
echo "📦 应用Agent清单..."
kubectl apply -f agentcore-manifest.yaml

# 等待部署完成
echo "⏳ 等待Agent部署完成..."
kubectl wait --for=condition=Ready agent/${{AGENT_NAME,,}} --timeout=300s

# 检查Agent状态
echo "✅ 检查Agent状态..."
kubectl get agent ${{AGENT_NAME,,}} -o wide

echo "🎉 部署完成！"
echo "📊 监控地址: https://console.aws.amazon.com/agentcore/agents/${{AGENT_NAME,,}}"
'''
        
        # 回滚脚本
        scripts["rollback.sh"] = f'''#!/bin/bash
set -e

echo "🔄 开始回滚字幕翻译Agent..."

AGENT_NAME="{config.agent_name.lower().replace('_', '-')}"

# 获取当前版本
CURRENT_VERSION=$(kubectl get agent $AGENT_NAME -o jsonpath='{{.spec.version}}')
echo "当前版本: $CURRENT_VERSION"

# 列出可用版本
echo "可用版本:"
kubectl get agent $AGENT_NAME -o jsonpath='{{.status.availableVersions}}' | tr ',' '\\n'

# 提示用户选择版本
read -p "请输入要回滚到的版本: " TARGET_VERSION

# 执行回滚
echo "回滚到版本: $TARGET_VERSION"
kubectl patch agent $AGENT_NAME --type='merge' -p='{{"spec":{{"version":"'$TARGET_VERSION'"}}}}'

# 等待回滚完成
kubectl wait --for=condition=Ready agent/$AGENT_NAME --timeout=300s

echo "✅ 回滚完成！"
'''
        
        # 健康检查脚本
        scripts["health_check.sh"] = f'''#!/bin/bash

AGENT_NAME="{config.agent_name.lower().replace('_', '-')}"
ENDPOINT=$(kubectl get agent $AGENT_NAME -o jsonpath='{{.status.endpoint}}')

if [ -z "$ENDPOINT" ]; then
    echo "❌ 无法获取Agent端点"
    exit 1
fi

echo "🏥 检查Agent健康状态..."
echo "端点: $ENDPOINT"

# 健康检查
HTTP_CODE=$(curl -s -o /dev/null -w "%{{http_code}}" $ENDPOINT/health)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Agent健康状态正常"
    
    # 获取详细状态
    curl -s $ENDPOINT/health | jq '.'
    
    # 检查指标
    echo "📊 性能指标:"
    curl -s $ENDPOINT/metrics | grep -E "(requests_total|response_time|error_rate)"
    
else
    echo "❌ Agent健康检查失败 (HTTP $HTTP_CODE)"
    exit 1
fi
'''
        
        return scripts
    
    def validate_deployment_readiness(self, config: AgentDeploymentConfig) -> List[str]:
        """验证部署就绪性"""
        issues = []
        
        # 基础配置验证
        config_issues = validate_config(config)
        issues.extend(config_issues)
        
        # AgentCore特定验证
        if config.environment == DeploymentEnvironment.AGENTCORE_PRODUCTION:
            if config.max_concurrent_requests < 10:
                issues.append("生产环境建议max_concurrent_requests >= 10")
            
            if config.memory_limit_mb < 1024:
                issues.append("生产环境建议memory_limit_mb >= 1024")
            
            if config.log_level == "DEBUG":
                issues.append("生产环境不建议使用DEBUG日志级别")
        
        # 模型可用性检查
        supported_models = [
            "us.anthropic.claude-4-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-7-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-haiku-20240307-v1:0"
        ]
        
        if config.primary_model not in supported_models:
            issues.append(f"主要模型 {config.primary_model} 可能不被支持")
        
        if config.fallback_model not in supported_models:
            issues.append(f"备用模型 {config.fallback_model} 可能不被支持")
        
        # 工具验证
        required_tools = [
            "parse_srt_file",
            "analyze_story_context",
            "translate_with_context",
            "validate_translation_quality",
            "export_translated_srt"
        ]
        
        missing_tools = set(required_tools) - set(config.tools)
        if missing_tools:
            issues.append(f"缺少必要工具: {', '.join(missing_tools)}")
        
        return issues
    
    def prepare_deployment(self, environment: DeploymentEnvironment) -> Dict[str, Any]:
        """准备部署文件"""
        # 选择配置
        if environment == DeploymentEnvironment.AGENTCORE_PRODUCTION:
            config = PRODUCTION_CONFIG
        elif environment == DeploymentEnvironment.AGENTCORE_STAGING:
            config = STAGING_CONFIG
        else:
            config = AgentDeploymentConfig(environment=environment)
        
        print(f"🔧 准备 {environment.value} 环境的部署文件...")
        
        # 验证配置
        issues = self.validate_deployment_readiness(config)
        if issues:
            print("⚠️  发现配置问题:")
            for issue in issues:
                print(f"  - {issue}")
            
            if environment == DeploymentEnvironment.AGENTCORE_PRODUCTION:
                print("❌ 生产环境部署被阻止，请修复上述问题")
                return {"success": False, "issues": issues}
        
        # 创建环境特定目录
        env_dir = self.output_dir / environment.value
        env_dir.mkdir(exist_ok=True)
        
        # 生成配置文件
        files_generated = []
        
        # 1. AgentCore清单
        manifest = self.generate_agentcore_manifest(config)
        manifest_file = env_dir / "agentcore-manifest.yaml"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)
        files_generated.append(str(manifest_file))
        
        # 2. Docker Compose（用于本地测试）
        compose = self.generate_docker_compose(config)
        compose_file = env_dir / "docker-compose.yml"
        with open(compose_file, 'w', encoding='utf-8') as f:
            yaml.dump(compose, f, default_flow_style=False)
        files_generated.append(str(compose_file))
        
        # 3. Terraform配置
        terraform_config = self.generate_terraform_config(config)
        terraform_file = env_dir / "main.tf"
        with open(terraform_file, 'w', encoding='utf-8') as f:
            f.write(terraform_config)
        files_generated.append(str(terraform_file))
        
        # 4. 部署脚本
        scripts = self.generate_deployment_scripts(config)
        for script_name, script_content in scripts.items():
            script_file = env_dir / script_name
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
            # 设置执行权限
            os.chmod(script_file, 0o755)
            files_generated.append(str(script_file))
        
        # 5. 配置摘要
        summary = {
            "deployment_info": {
                "environment": environment.value,
                "agent_name": config.agent_name,
                "agent_version": config.agent_version,
                "generated_at": datetime.now().isoformat()
            },
            "configuration": config.to_agentcore_config(),
            "supported_languages": {
                lang: get_language_config(lang) 
                for lang in config.supported_languages
            },
            "validation_issues": issues,
            "files_generated": files_generated
        }
        
        summary_file = env_dir / "deployment-summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        files_generated.append(str(summary_file))
        
        print(f"✅ 部署文件生成完成:")
        for file_path in files_generated:
            print(f"  📄 {file_path}")
        
        return {
            "success": True,
            "environment": environment.value,
            "files_generated": files_generated,
            "config": config,
            "issues": issues
        }

def main():
    """主函数"""
    print("🚀 AgentCore部署准备工具")
    print("=" * 50)
    
    prep = DeploymentPreparation()
    
    # 准备所有环境的部署文件
    environments = [
        DeploymentEnvironment.LOCAL_DEVELOPMENT,
        DeploymentEnvironment.AGENTCORE_STAGING,
        DeploymentEnvironment.AGENTCORE_PRODUCTION
    ]
    
    results = {}
    
    for env in environments:
        print(f"\n📦 准备 {env.value} 环境...")
        result = prep.prepare_deployment(env)
        results[env.value] = result
        
        if not result["success"]:
            print(f"❌ {env.value} 环境准备失败")
        else:
            print(f"✅ {env.value} 环境准备完成")
    
    # 生成总体报告
    print(f"\n📊 部署准备报告:")
    for env_name, result in results.items():
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"  {env_name}: {status}")
        
        if result.get("issues"):
            print(f"    问题数量: {len(result['issues'])}")
    
    print(f"\n📁 所有文件已生成到 deployment/ 目录")
    print(f"🔧 使用方法:")
    print(f"  1. 本地测试: cd deployment/local_development && docker-compose up")
    print(f"  2. 部署到staging: cd deployment/agentcore_staging && ./deploy.sh")
    print(f"  3. 部署到生产: cd deployment/agentcore_production && ./deploy.sh")

if __name__ == "__main__":
    main()