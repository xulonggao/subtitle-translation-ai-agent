# 影视剧字幕翻译Agent系统

基于AWS Bedrock和Strands Agent SDK构建的智能影视剧字幕翻译系统。

## 系统特点

- **通用架构**: 支持任何影视剧作品的字幕翻译
- **多Agent协作**: 专业化Agent处理不同翻译任务
- **上下文感知**: 基于剧情和人物关系的智能翻译
- **多语言支持**: 支持10种目标语言翻译
- **企业级部署**: 支持本地开发和云端生产部署

## 支持的语言

- 英语 (English)
- 日语 (Japanese)
- 韩语 (Korean)
- 泰语 (Thai)
- 越南语 (Vietnamese)
- 印尼语 (Indonesian)
- 马来语 (Malay)
- 西班牙语 (Spanish)
- 葡萄牙语 (Portuguese)
- 阿拉伯语 (Arabic)

## 项目结构

```
subtitle-translation-system/
├── agents/                    # 通用Agent代码
│   ├── master_agent.py
│   ├── parser_agent.py
│   ├── context_agent.py
│   └── translation_agents/
├── projects/                  # 项目特定配置
│   ├── love_navy_blue/
│   └── project_template/
├── shared_resources/          # 共享资源
│   ├── global_terminology.json
│   └── cultural_adaptations/
├── config/                    # 配置文件
├── tests/                     # 测试用例
└── docs/                      # 文档
```

## 快速开始

### 环境要求

- Python 3.10+
- AWS账号和Bedrock访问权限
- Claude 4 Sonnet 或 Claude 3.7 Sonnet 模型访问权限

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置AWS凭证

```bash
aws configure
```

### 运行系统

```bash
python main.py
```

## 开发指南

详细的开发指南请参考 [docs/development.md](docs/development.md)

## 许可证

Apache License 2.0