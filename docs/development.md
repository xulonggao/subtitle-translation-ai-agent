# 开发指南

## 开发环境设置

### 1. 环境要求

- Python 3.10+
- AWS CLI 配置
- AWS Bedrock 访问权限

### 2. 安装依赖

```bash
cd subtitle-translation-system
pip install -r requirements.txt
```

### 3. 环境变量配置

创建 `.env` 文件：

```bash
# Bedrock配置
BEDROCK_PRIMARY_MODEL_ID=us.anthropic.claude-opus-4-20250514-v1:0
BEDROCK_FALLBACK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
BEDROCK_REGION=us-west-2

# 系统配置
SYSTEM_ENVIRONMENT=local
SYSTEM_DEBUG=true
SYSTEM_MAX_CONCURRENT_TRANSLATIONS=3

# Web配置
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

### 4. AWS 凭证配置

```bash
aws configure
```

## 项目结构说明

```
subtitle-translation-system/
├── agents/                    # Agent实现
│   ├── master_agent.py       # 主控Agent
│   ├── parser_agent.py       # 文件解析Agent
│   ├── context_agent.py      # 上下文管理Agent
│   └── translation_agents/   # 翻译Agent群
├── projects/                  # 项目配置
│   ├── project_template/     # 项目模板
│   └── love_navy_blue/       # 示例项目
├── shared_resources/          # 共享资源
│   ├── global_terminology.json
│   └── cultural_adaptations/
├── config/                    # 配置文件
├── tests/                     # 测试用例
└── docs/                      # 文档
```

## 开发流程

### 1. 创建新功能

1. 在对应模块创建功能代码
2. 编写单元测试
3. 更新文档
4. 提交代码

### 2. 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agents.py

# 生成覆盖率报告
pytest --cov=agents --cov-report=html
```

### 3. 代码质量检查

```bash
# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy .
```

## Agent 开发指南

### 1. 创建新 Agent

```python
from strands import Agent, tool
from config import bedrock_config, get_logger

logger = get_logger("my_agent")

@tool
def my_tool(input_text: str) -> str:
    """工具描述"""
    return f"处理结果: {input_text}"

class MyAgent:
    def __init__(self):
        self.agent = Agent(
            model=self.get_model(),
            tools=[my_tool],
            system_prompt="你是专业的助手..."
        )

    def get_model(self):
        # 使用配置的模型
        pass

    def process(self, input_data):
        return self.agent(input_data)
```

### 2. 错误处理

```python
try:
    result = agent.process(data)
except Exception as e:
    logger.error("处理失败", error=str(e))
    # 错误恢复逻辑
```

## 部署指南

### 本地开发部署

```bash
python main.py
```

### 生产环境部署

参考 [deployment.md](deployment.md)

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request
