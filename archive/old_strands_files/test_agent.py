#!/usr/bin/env python3
"""
Strands Agent测试脚本
验证字幕翻译Agent的核心功能
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from subtitle_translation_agent import (
    create_subtitle_translation_agent,
    translate_subtitle_file,
    parse_srt_file,
    analyze_story_context,
    translate_with_context,
    validate_translation_quality,
    export_translated_srt
)
from agent_config import DEVELOPMENT_CONFIG, get_language_config

# 测试用的SRT内容
TEST_SRT_CONTENT = """1
00:00:01,000 --> 00:00:03,000
你好，欢迎来到我们的节目

2
00:00:04,000 --> 00:00:06,000
今天我们要聊聊人工智能的发展

3
00:00:07,000 --> 00:00:09,000
这真是一个令人兴奋的话题！

4
00:00:10,000 --> 00:00:12,000
张伟：是的，AI技术正在改变我们的生活

5
00:00:13,000 --> 00:00:15,000
李明：特别是在翻译领域的应用

6
00:00:16,000 --> 00:00:18,000
我们需要保持对新技术的开放态度"""

# 军事题材测试内容
MILITARY_SRT_CONTENT = """1
00:00:01,000 --> 00:00:03,000
参谋长：全体集合！

2
00:00:04,000 --> 00:00:06,000
司令：今天的训练任务很重要

3
00:00:07,000 --> 00:00:09,000
队长：是，长官！我们一定完成任务

4
00:00:10,000 --> 00:00:12,000
战友们，为了祖国的荣誉！

5
00:00:13,000 --> 00:00:15,000
这次演习将检验我们的实战能力"""

# 浪漫题材测试内容
ROMANTIC_SRT_CONTENT = """1
00:00:01,000 --> 00:00:03,000
小雨：你还记得我们第一次见面吗？

2
00:00:04,000 --> 00:00:06,000
大明：当然记得，那是个美丽的春天

3
00:00:07,000 --> 00:00:09,000
小雨：我从那时就知道你是我的真命天子

4
00:00:10,000 --> 00:00:12,000
大明：亲爱的，我也爱你

5
00:00:13,000 --> 00:00:15,000
让我们一起走向幸福的未来吧"""

def test_srt_parsing():
    """测试SRT文件解析功能"""
    print("=== 测试SRT文件解析 ===")
    
    result = parse_srt_file(TEST_SRT_CONTENT)
    
    if result.success:
        entries = result.data["entries"]
        print(f"✅ 成功解析 {len(entries)} 个字幕条目")
        
        # 显示前3个条目
        for i, entry in enumerate(entries[:3]):
            print(f"条目 {i+1}:")
            print(f"  时间: {entry['start_time']} --> {entry['end_time']}")
            print(f"  文本: {entry['original_text']}")
            if entry.get('speaker'):
                print(f"  说话人: {entry['speaker']}")
            print()
    else:
        print(f"❌ 解析失败: {result.error}")
    
    return result

def test_context_analysis():
    """测试上下文分析功能"""
    print("=== 测试上下文分析 ===")
    
    # 先解析SRT
    parse_result = parse_srt_file(MILITARY_SRT_CONTENT)
    if not parse_result.success:
        print("❌ SRT解析失败，无法进行上下文分析")
        return None
    
    entries = parse_result.data["entries"]
    additional_context = json.dumps({
        "title": "军事训练",
        "genre": "military",
        "cultural_background": "现代军事"
    })
    
    result = analyze_story_context(entries, additional_context)
    
    if result.success:
        context = result.data
        print(f"✅ 上下文分析完成")
        print(f"  类型: {context.get('genre', '未知')}")
        print(f"  语调: {context.get('tone_style', '中性')}")
        print(f"  角色数量: {len(context.get('characters', []))}")
        print(f"  文化背景: {context.get('cultural_background', '未指定')}")
        
        if context.get('characters'):
            print("  主要角色:")
            for char in context['characters'][:3]:
                print(f"    - {char['name']}")
    else:
        print(f"❌ 上下文分析失败: {result.error}")
    
    return result

def test_translation_with_context():
    """测试基于上下文的翻译功能"""
    print("=== 测试基于上下文的翻译 ===")
    
    # 解析SRT
    parse_result = parse_srt_file(ROMANTIC_SRT_CONTENT)
    if not parse_result.success:
        print("❌ SRT解析失败")
        return None
    
    entries = parse_result.data["entries"]
    
    # 分析上下文
    context_result = analyze_story_context(entries, json.dumps({
        "title": "浪漫爱情故事",
        "genre": "romance",
        "tone_style": "romantic"
    }))
    
    if not context_result.success:
        print("❌ 上下文分析失败")
        return None
    
    story_context = context_result.data
    
    # 测试多种语言翻译
    test_languages = ["en", "ja", "ko", "es"]
    
    for lang in test_languages:
        print(f"\n--- 翻译到 {get_language_config(lang)['name']} ---")
        
        config = {
            "quality_level": "high",
            "cultural_adaptation": True,
            "preserve_timing": True
        }
        
        result = translate_with_context(entries, lang, story_context, config)
        
        if result.success:
            translated_entries = result.data["translated_entries"]
            print(f"✅ 成功翻译 {len(translated_entries)} 个条目")
            
            # 显示前2个翻译结果
            for i, entry in enumerate(translated_entries[:2]):
                print(f"  原文: {entry['original_text']}")
                print(f"  译文: {entry['translated_text']}")
                print(f"  置信度: {entry['confidence_score']:.2f}")
                print()
        else:
            print(f"❌ 翻译失败: {result.error}")
    
    return result

def test_quality_validation():
    """测试翻译质量验证功能"""
    print("=== 测试翻译质量验证 ===")
    
    # 创建测试数据
    original_entries = [
        {
            "sequence": 1,
            "start_time": "00:00:01,000",
            "end_time": "00:00:03,000",
            "original_text": "你好，欢迎来到我们的节目"
        },
        {
            "sequence": 2,
            "start_time": "00:00:04,000",
            "end_time": "00:00:06,000",
            "original_text": "今天我们要聊聊人工智能的发展"
        }
    ]
    
    # 模拟翻译结果（包含一些质量问题）
    translated_entries = [
        {
            "sequence": 1,
            "start_time": "00:00:01,000",
            "end_time": "00:00:03,000",
            "original_text": "你好，欢迎来到我们的节目",
            "translated_text": "Hello, welcome to our program"
        },
        {
            "sequence": 2,
            "start_time": "00:00:04,000",
            "end_time": "00:00:06,000",
            "original_text": "今天我们要聊聊人工智能的发展",
            "translated_text": "[待翻译] Today we will talk about the development of artificial intelligence which is a very long sentence that exceeds the character limit"
        }
    ]
    
    result = validate_translation_quality(original_entries, translated_entries, "en")
    
    if result.success:
        data = result.data
        print(f"✅ 质量验证完成")
        print(f"  总体评分: {data['overall_quality_score']:.2f}")
        print(f"  问题条目数: {data['problematic_entries']}")
        print(f"  质量分布:")
        for level, count in data['quality_distribution'].items():
            print(f"    {level}: {count}")
        
        if data['quality_issues']:
            print("  发现的问题:")
            for issue in data['quality_issues'][:3]:  # 只显示前3个问题
                print(f"    条目 {issue['sequence']}: {', '.join(issue['issues'])}")
        
        if data['recommendations']:
            print("  改进建议:")
            for rec in data['recommendations']:
                print(f"    - {rec}")
    else:
        print(f"❌ 质量验证失败: {result.error}")
    
    return result

def test_srt_export():
    """测试SRT文件导出功能"""
    print("=== 测试SRT文件导出 ===")
    
    # 创建测试翻译数据
    translated_entries = [
        {
            "sequence": 1,
            "start_time": "00:00:01,000",
            "end_time": "00:00:03,000",
            "translated_text": "Hello, welcome to our program"
        },
        {
            "sequence": 2,
            "start_time": "00:00:04,000",
            "end_time": "00:00:06,000",
            "translated_text": "Today we will talk about AI development"
        },
        {
            "sequence": 3,
            "start_time": "00:00:07,000",
            "end_time": "00:00:09,000",
            "translated_text": "This is truly an exciting topic!"
        }
    ]
    
    result = export_translated_srt(translated_entries, "en")
    
    if result.success:
        data = result.data
        print(f"✅ SRT导出成功")
        print(f"  条目数量: {data['entry_count']}")
        print(f"  文件大小: {data['file_size']} 字节")
        print(f"  建议文件名: {data['suggested_filename']}")
        print("\n  导出内容预览:")
        print(data['srt_content'][:200] + "..." if len(data['srt_content']) > 200 else data['srt_content'])
    else:
        print(f"❌ SRT导出失败: {result.error}")
    
    return result

def test_agent_creation():
    """测试Agent创建和配置"""
    print("=== 测试Agent创建 ===")
    
    try:
        agent = create_subtitle_translation_agent()
        print(f"✅ Agent创建成功")
        print(f"  名称: {agent.name}")
        print(f"  模型: {agent.model.model_id}")
        print(f"  工具数量: {len(agent.tools)}")
        print(f"  系统提示词长度: {len(agent.system_prompt)} 字符")
        
        # 测试配置
        config = DEVELOPMENT_CONFIG
        print(f"\n  开发配置:")
        print(f"    支持语言: {', '.join(config.supported_languages)}")
        print(f"    质量级别: {config.default_quality_level}")
        print(f"    文化适配: {config.enable_cultural_adaptation}")
        print(f"    术语一致性: {config.enable_terminology_consistency}")
        
        return True
    except Exception as e:
        print(f"❌ Agent创建失败: {str(e)}")
        return False

async def test_full_translation_workflow():
    """测试完整的翻译工作流程"""
    print("=== 测试完整翻译工作流程 ===")
    
    try:
        result = await translate_subtitle_file(
            srt_content=TEST_SRT_CONTENT,
            target_language="en",
            additional_context=json.dumps({
                "title": "AI技术讨论",
                "genre": "educational",
                "tone_style": "professional"
            })
        )
        
        if result["success"]:
            print(f"✅ 完整翻译流程成功")
            print(f"  处理时间: {result['timestamp']}")
            print(f"  Agent: {result['agent_name']}")
            print(f"  模型: {result['model_used']}")
            print(f"  响应: {result['response']}")
        else:
            print(f"❌ 完整翻译流程失败: {result['error']}")
        
        return result
    except Exception as e:
        print(f"❌ 完整翻译流程异常: {str(e)}")
        return None

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始Strands Agent功能测试\n")
    
    test_results = {}
    
    # 1. 测试Agent创建
    test_results["agent_creation"] = test_agent_creation()
    print()
    
    # 2. 测试SRT解析
    test_results["srt_parsing"] = test_srt_parsing()
    print()
    
    # 3. 测试上下文分析
    test_results["context_analysis"] = test_context_analysis()
    print()
    
    # 4. 测试翻译功能
    test_results["translation"] = test_translation_with_context()
    print()
    
    # 5. 测试质量验证
    test_results["quality_validation"] = test_quality_validation()
    print()
    
    # 6. 测试SRT导出
    test_results["srt_export"] = test_srt_export()
    print()
    
    # 7. 测试完整工作流程
    print("正在测试完整工作流程...")
    try:
        loop = asyncio.get_event_loop()
        test_results["full_workflow"] = loop.run_until_complete(test_full_translation_workflow())
    except Exception as e:
        print(f"❌ 完整工作流程测试失败: {str(e)}")
        test_results["full_workflow"] = False
    print()
    
    # 汇总测试结果
    print("📊 测试结果汇总:")
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！Strands Agent功能正常")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    return test_results

if __name__ == "__main__":
    # 运行测试
    results = run_all_tests()
    
    # 生成测试报告
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "test_results": results,
        "agent_config": DEVELOPMENT_CONFIG.to_local_config(),
        "supported_languages": DEVELOPMENT_CONFIG.supported_languages
    }
    
    # 保存测试报告
    with open("test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 测试报告已保存到 test_report.json")