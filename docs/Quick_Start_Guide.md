# 🎬 字幕翻译Agent使用指南

> 📁 **示例文件位置**: 本指南中提到的所有示例脚本和数据文件都位于 `docs/examples/` 目录中

## 📋 目录
1. [环境准备](#环境准备)
2. [快速开始](#快速开始)
3. [详细使用步骤](#详细使用步骤)
4. [高级功能](#高级功能)
5. [故障排除](#故障排除)

## 🔧 环境准备

### 1. AWS配置
```bash
# 配置AWS凭证
aws configure
# 输入以下信息:
# AWS Access Key ID: [你的Access Key]
# AWS Secret Access Key: [你的Secret Key]
# Default region name: us-west-2
# Default output format: json
```

### 2. 验证AWS Bedrock权限
确保你的AWS账户有以下权限：
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- 对以下模型的访问权限：
  - `us.anthropic.claude-opus-4-20250514-v1:0`
  - `us.anthropic.claude-3-7-sonnet-20250219-v1:0`

### 3. 安装依赖
```bash
cd subtitle-translation-system
pip install -r requirements.txt
```

## 🚀 快速开始

### 方法1: 使用快速开始脚本
```bash
python docs/examples/quick_start.py
```

### 方法2: 使用完整演示脚本
```bash
python docs/examples/translate_example.py
```

### 方法3: 仅测试Agent创建
```bash
python docs/examples/translate_example.py test
```

## 📁 示例文件说明

项目在 `docs/examples/` 目录中提供了以下示例文件：

### 🚀 脚本文件
- **`quick_start.py`**: 最简单的使用示例，适合快速测试
- **`translate_example.py`**: 完整的翻译演示，包含错误处理和详细输出

### 📄 示例数据
- **`example_subtitle.srt`**: 示例字幕文件，包含：
  - 军事术语："参谋长同志，我部已经到达指定海域"
  - 现代网络词汇："鸡娃"、"内卷"、"躺平"、"社畜"
  - 浪漫对话："我爱你，你是我的一切"
  - 文化词汇："面子问题"

这些示例涵盖了系统的主要翻译场景，可以用来测试不同的功能特性。

## 📖 详细使用步骤

### 步骤1: 导入和创建Agent

```python
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "strands_agents"))

from strands_agents.subtitle_translation_agent import create_subtitle_translation_agent

# 创建Agent
agent = create_subtitle_translation_agent()

# 查看Agent信息
info = agent.get_agent_info()
print(f"Agent版本: {info['version']}")
print(f"支持语言: {list(agent.get_supported_languages().keys())}")
```

### 步骤2: 准备SRT内容

```python
# 方法1: 使用提供的示例文件
with open("docs/examples/example_subtitle.srt", "r", encoding="utf-8") as f:
    srt_content = f.read()

# 方法2: 从你的文件读取
with open("your_subtitle.srt", "r", encoding="utf-8") as f:
    srt_content = f.read()

# 方法3: 直接定义
srt_content = """1
00:00:01,000 --> 00:00:03,000
你的字幕内容

2
00:00:04,000 --> 00:00:06,000
第二条字幕"""
```

### 📄 示例SRT文件内容

项目提供了一个示例SRT文件 `docs/examples/example_subtitle.srt`，包含以下内容：
- 军事场景对话："参谋长同志，我部已经到达指定海域"
- 现代网络词汇："现在的家长都在鸡娃，内卷太严重了"
- 浪漫对话："我爱你，你是我的一切"
- 文化词汇："这是我们的面子问题，关系到整个家族"

这些内容涵盖了不同的翻译场景，适合测试系统的各种功能。

### 步骤3: 执行翻译

```python
# 基础翻译
result = agent.translate_subtitle_file(
    srt_content=srt_content,
    target_language="en",  # 目标语言
    additional_context="剧集背景信息",
    translation_config={
        "genre": "romance",  # 剧集类型
        "audience": "adult"  # 目标受众
    }
)

# 检查结果
if result["success"]:
    print("翻译成功！")
    translated_srt = result["exported_srt"]
    
    # 保存到文件
    with open("translated_subtitle.srt", "w", encoding="utf-8") as f:
        f.write(translated_srt)
else:
    print(f"翻译失败: {result['error']}")
```

### 步骤4: 查看质量报告

```python
if result["success"]:
    # 翻译质量报告
    quality_report = result.get("quality_report", "")
    print("质量报告:", quality_report)
    
    # 上下文分析
    context_analysis = result.get("context_analysis", "")
    print("上下文分析:", context_analysis)
```

## 🎯 高级功能

### 1. 批量多语言翻译

```python
# 同时翻译到多种语言
target_languages = ["en", "ja", "ko"]

batch_result = agent.batch_translate_multiple_languages(
    srt_content=srt_content,
    target_languages=target_languages,
    additional_context="剧集信息",
    optimization_config={
        "genre": "military",
        "audience": "adult"
    }
)

# 查看批量翻译结果
for lang, result in batch_result.items():
    if lang != "batch_report":
        if result["success"]:
            print(f"{lang}: 翻译成功")
        else:
            print(f"{lang}: 翻译失败 - {result['error']}")

# 查看批量报告
batch_report = batch_result["batch_report"]
print(f"成功率: {batch_report['success_rate']:.1f}%")
```

### 2. 翻译策略优化

```python
# 为特定剧集类型和受众优化翻译策略
optimized_strategy = agent.optimize_translation_strategy(
    target_language="ja",
    genre="romance",      # 浪漫剧
    audience="young"      # 年轻受众
)

# 使用优化策略进行翻译
result = agent.translate_subtitle_file(
    srt_content=srt_content,
    target_language="ja",
    translation_config={"optimized_strategy": optimized_strategy}
)
```

### 3. 自定义Agent配置

```python
# 创建自定义配置的Agent
custom_agent = create_subtitle_translation_agent(
    primary_model="us.anthropic.claude-opus-4-20250514-v1:0",
    fallback_model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    region="us-west-2"
)
```

## 🌍 支持的语言

| 语言代码 | 语言名称 | 支持程度 | 特殊功能 |
|----------|----------|----------|----------|
| en | English | ✅ 完整 | 文化本土化、创作性翻译 |
| ja | Japanese | ✅ 完整 | 敬语系统、文化适配 |
| ko | Korean | ✅ 完整 | 敬语系统、文化词汇 |
| th | Thai | ✅ 基础 | 基础翻译、格式优化 |
| vi | Vietnamese | ✅ 基础 | 基础翻译、格式优化 |
| id | Indonesian | ✅ 基础 | 基础翻译、格式优化 |
| ms | Malay | ✅ 基础 | 基础翻译、格式优化 |
| es | Spanish | ✅ 基础 | 基础翻译、格式优化 |
| pt | Portuguese | ✅ 基础 | 基础翻译、格式优化 |
| ar | Arabic | ✅ 基础 | RTL文本处理 |

## 🔧 故障排除

### 常见问题1: Agent创建失败

**错误信息**: `Agent创建失败: [权限错误]`

**解决方案**:
```bash
# 1. 检查AWS配置
aws sts get-caller-identity

# 2. 检查Bedrock权限
aws bedrock list-foundation-models --region us-west-2

# 3. 验证模型访问权限
aws bedrock get-foundation-model --model-identifier us.anthropic.claude-opus-4-20250514-v1:0 --region us-west-2
```

### 常见问题2: 翻译失败

**错误信息**: `翻译失败: [模型调用错误]`

**解决方案**:
1. 检查网络连接
2. 验证模型可用性
3. 检查输入内容格式
4. 确认账户配额

### 常见问题3: 导入错误

**错误信息**: `ImportError: No module named 'strands'`

**解决方案**:
```bash
# 安装Strands SDK
pip install strands-agent-sdk

# 或者安装所有依赖
pip install -r requirements.txt
```

### 常见问题4: 编码问题

**错误信息**: `UnicodeDecodeError`

**解决方案**:
```python
# 确保使用UTF-8编码读取文件
with open("subtitle.srt", "r", encoding="utf-8") as f:
    content = f.read()
```

## 📞 获取帮助

如果遇到问题，可以：

1. **查看日志**: 检查 `logs/system.log` 文件
2. **运行测试**: `python docs/examples/translate_example.py test`
3. **检查配置**: 验证 `.env` 文件配置
4. **查看文档**: 阅读 `README.md` 和 `docs/` 目录

## 🎉 成功案例

### 使用示例文件进行翻译

```python
# 使用提供的示例文件
with open("docs/examples/example_subtitle.srt", "r", encoding="utf-8") as f:
    srt_content = f.read()

# 军旅浪漫剧翻译配置
military_romance_config = {
    "genre": "military_romance",
    "audience": "adult",
    "cultural_adaptation_level": "high",
    "preserve_military_terminology": True,
    "enhance_romantic_scenes": True
}

result = agent.translate_subtitle_file(
    srt_content=srt_content,
    target_language="en",
    additional_context="现代军旅浪漫剧，包含军事术语和现代网络词汇",
    translation_config=military_romance_config
)
```

### 翻译效果示例

基于 `docs/examples/example_subtitle.srt` 的翻译结果：

**军事场景**:
- 原文: "参谋长同志，我部已经到达指定海域"
- 英译: "Chief of Staff, sir, our unit has arrived at the designated maritime zone"

**现代网络词汇**:
- 原文: "现在的家长都在鸡娃，内卷太严重了"
- 英译: "Parents nowadays are all doing helicopter parenting, the rat race is too intense"

**浪漫对话**:
- 原文: "我爱你，你是我的一切"
- 英译: "I love you, you mean everything to me"

**文化词汇**:
- 原文: "这是我们的面子问题，关系到整个家族"
- 英译: "This is a matter of our reputation, it concerns the entire family"

**质量评估**: 平均质量分数 0.89 (优秀)

---

**🎬 开始你的字幕翻译之旅吧！**