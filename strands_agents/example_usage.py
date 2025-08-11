#!/usr/bin/env python3
"""
Strands Agent字幕翻译系统使用示例
展示完整的翻译工作流程
"""
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strands_agents.subtitle_translation_agent import create_subtitle_translation_agent
from strands_agents.enhanced_tools import (
    parse_srt_file,
    analyze_story_context,
    translate_with_context,
    validate_translation_quality,
    export_translated_srt
)

def example_1_basic_translation():
    """示例1: 基础翻译流程"""
    print("🎬 示例1: 基础字幕翻译")
    print("=" * 50)
    
    # 示例SRT内容
    srt_content = """1
00:00:01,000 --> 00:00:03,000
司令: 参谋长，今天的训练计划如何？

2
00:00:04,000 --> 00:00:06,000
参谋长: 报告司令，所有队员已就位。

3
00:00:07,000 --> 00:00:09,000
队长: 我们准备开始了！

4
00:00:10,000 --> 00:00:12,000
[旁白] 这是一个关于军队训练的故事。"""
    
    # 创建Agent
    agent = create_subtitle_translation_agent()
    
    # 执行翻译
    result = agent.translate_subtitle_file(
        srt_content=srt_content,
        target_language="en",
        additional_context="这是一部军事题材的现代剧，讲述海军训练的故事"
    )
    
    if result["success"]:
        print("✅ 翻译成功完成！")
        print("\n📊 翻译统计:")
        
        # 解析结果并显示统计信息
        try:
            parse_data = json.loads(result["parse_result"])
            if parse_data["success"]:
                stats = parse_data["data"]["statistics"]
                print(f"  - 总条目数: {stats['total_entries']}")
                print(f"  - 检测到说话人: {stats['speakers_detected']}")
                print(f"  - 总时长: {stats['total_duration_ms']/1000:.1f}秒")
        except:
            print("  - 统计信息解析失败")
        
        print("\n📝 导出的SRT文件预览:")
        try:
            export_data = json.loads(result["exported_srt"])
            if export_data["success"]:
                srt_preview = export_data["data"]["srt_content"][:500]
                print(srt_preview + "..." if len(srt_preview) == 500 else srt_preview)
        except:
            print("  - SRT预览失败")
            
    else:
        print(f"❌ 翻译失败: {result['error']}")
    
    print("\n" + "=" * 50 + "\n")

def example_2_step_by_step():
    """示例2: 分步骤使用工具函数"""
    print("🔧 示例2: 分步骤使用工具函数")
    print("=" * 50)
    
    # 示例SRT内容
    srt_content = """1
00:00:01,000 --> 00:00:03,000
小明: 哥，你觉得这个鸡娃现象怎么样？

2
00:00:04,000 --> 00:00:06,000
小华: 现在内卷太严重了，大家都在躺平。

3
00:00:07,000 --> 00:00:09,000
小明: 是啊，压力太大了。"""
    
    print("步骤1: 解析SRT文件")
    parse_result = parse_srt_file(srt_content, detect_speakers=True)
    parse_data = json.loads(parse_result)
    
    if parse_data["success"]:
        print(f"✅ 解析成功，共 {parse_data['data']['statistics']['total_entries']} 个条目")
        entries = parse_data["data"]["entries"]
        for entry in entries[:2]:  # 显示前2个条目
            print(f"  - 条目{entry['sequence']}: {entry['speaker']} - {entry['original_text']}")
    else:
        print(f"❌ 解析失败: {parse_data['error']}")
        return
    
    print("\n步骤2: 分析故事上下文")
    context_result = analyze_story_context(
        entries=parse_result,
        additional_context='{"title": "现代都市剧", "genre": "modern_drama"}',
        analysis_depth="deep"
    )
    context_data = json.loads(context_result)
    
    if context_data["success"]:
        print("✅ 上下文分析成功")
        context = context_data["data"]["context"]
        print(f"  - 剧集类型: {context.get('genre', '未知')}")
        print(f"  - 语调风格: {context.get('tone_style', '未知')}")
        print(f"  - 主要角色: {len(context.get('characters', []))}")
    else:
        print(f"❌ 上下文分析失败: {context_data['error']}")
        return
    
    print("\n步骤3: 执行翻译 (日语)")
    translation_config = {
        "quality_level": "high",
        "cultural_adaptation": True,
        "maintain_speaker_style": True
    }
    
    translate_result = translate_with_context(
        entries=parse_result,
        target_language="ja",
        story_context=context_result,
        translation_config=json.dumps(translation_config)
    )
    translate_data = json.loads(translate_result)
    
    if translate_data["success"]:
        print("✅ 翻译成功")
        summary = translate_data["data"]["translation_summary"]
        print(f"  - 翻译条目数: {summary['total_entries']}")
        print(f"  - 平均置信度: {summary['average_confidence']:.2f}")
        print(f"  - 翻译策略: {summary['translation_strategy']}")
    else:
        print(f"❌ 翻译失败: {translate_data['error']}")
        return
    
    print("\n步骤4: 质量验证")
    quality_result = validate_translation_quality(
        original_entries=parse_result,
        translated_entries=translate_result,
        target_language="ja"
    )
    quality_data = json.loads(quality_result)
    
    if quality_data["success"]:
        print("✅ 质量验证完成")
        metrics = quality_data["data"]["quality_metrics"]
        print(f"  - 总体评分: {metrics['overall_score']:.2f}")
        print(f"  - 准确性: {metrics['accuracy_score']:.2f}")
        print(f"  - 流畅性: {metrics['fluency_score']:.2f}")
        print(f"  - 一致性: {metrics['consistency_score']:.2f}")
        print(f"  - 发现问题: {quality_data['data']['validation_summary']['issues_found']} 个")
    else:
        print(f"❌ 质量验证失败: {quality_data['error']}")
        return
    
    print("\n步骤5: 导出SRT文件")
    export_config = {
        "include_speaker_names": True,
        "speaker_name_format": "{speaker}: {text}",
        "add_metadata": True
    }
    
    export_result = export_translated_srt(
        translated_entries=translate_result,
        export_config=json.dumps(export_config)
    )
    export_data = json.loads(export_result)
    
    if export_data["success"]:
        print("✅ SRT导出成功")
        info = export_data["data"]["export_info"]
        print(f"  - 建议文件名: {info['suggested_filename']}")
        print(f"  - 文件大小: {info['file_size_bytes']} 字节")
        print(f"  - 编码: {info['encoding']}")
        
        print("\n📝 导出内容预览:")
        srt_content = export_data["data"]["srt_content"]
        lines = srt_content.split('\n')[:15]  # 显示前15行
        print('\n'.join(lines))
        if len(srt_content.split('\n')) > 15:
            print("...")
    else:
        print(f"❌ SRT导出失败: {export_data['error']}")
    
    print("\n" + "=" * 50 + "\n")

def example_3_multiple_languages():
    """示例3: 多语言翻译对比"""
    print("🌍 示例3: 多语言翻译对比")
    print("=" * 50)
    
    # 简单的SRT内容
    srt_content = """1
00:00:01,000 --> 00:00:03,000
老板: 你好，欢迎来到我们公司！

2
00:00:04,000 --> 00:00:06,000
员工: 谢谢老板，我会努力工作的。"""
    
    # 目标语言列表
    target_languages = ["en", "ja", "ko", "es"]
    language_names = {
        "en": "英语",
        "ja": "日语", 
        "ko": "韩语",
        "es": "西班牙语"
    }
    
    # 解析SRT
    parse_result = parse_srt_file(srt_content, detect_speakers=True)
    parse_data = json.loads(parse_result)
    
    if not parse_data["success"]:
        print(f"❌ SRT解析失败: {parse_data['error']}")
        return
    
    # 分析上下文
    context_result = analyze_story_context(
        entries=parse_result,
        additional_context='{"title": "职场剧", "genre": "workplace"}',
        analysis_depth="standard"
    )
    
    print("🔄 开始多语言翻译...")
    
    for lang_code in target_languages:
        lang_name = language_names[lang_code]
        print(f"\n📍 翻译到{lang_name} ({lang_code}):")
        
        # 执行翻译
        translate_result = translate_with_context(
            entries=parse_result,
            target_language=lang_code,
            story_context=context_result,
            translation_config='{"quality_level": "high"}'
        )
        translate_data = json.loads(translate_result)
        
        if translate_data["success"]:
            # 显示翻译结果
            entries = translate_data["data"]["translated_entries"]
            for entry in entries:
                speaker = entry.get("speaker", "")
                original = entry.get("original_text", "")
                translated = entry.get("translated_text", "")
                print(f"  原文: {speaker}: {original}")
                print(f"  译文: {speaker}: {translated}")
                print()
        else:
            print(f"  ❌ 翻译失败: {translate_data['error']}")
    
    print("=" * 50 + "\n")

def example_4_quality_analysis():
    """示例4: 翻译质量分析"""
    print("📊 示例4: 翻译质量分析")
    print("=" * 50)
    
    # 创建一个有问题的翻译示例
    original_entries = [
        {
            "sequence": 1,
            "start_time": "00:00:01,000",
            "end_time": "00:00:03,000",
            "original_text": "你好，很高兴见到你！",
            "speaker": "小明"
        },
        {
            "sequence": 2,
            "start_time": "00:00:04,000",
            "end_time": "00:00:06,000",
            "original_text": "我也很高兴见到你。",
            "speaker": "小华"
        }
    ]
    
    # 创建有问题的翻译
    problematic_translation = [
        {
            "sequence": 1,
            "start_time": "00:00:01,000",  # 时间码一致
            "end_time": "00:00:03,000",
            "original_text": "你好，很高兴见到你！",
            "translated_text": "[待翻译] Hello, nice to meet you! This is a very long translation that exceeds the recommended character limit for subtitles",
            "speaker": "小明"
        },
        {
            "sequence": 2,
            "start_time": "00:00:00,000",  # 时间码不一致
            "end_time": "00:00:06,000",
            "original_text": "我也很高兴见到你。",
            "translated_text": "Nice to meet you too",  # 缺少问号
            "speaker": "小华"
        }
    ]
    
    # 执行质量验证
    quality_result = validate_translation_quality(
        original_entries=json.dumps(original_entries),
        translated_entries=json.dumps(problematic_translation),
        target_language="en",
        validation_config='{"detailed_analysis": true}'
    )
    
    quality_data = json.loads(quality_result)
    
    if quality_data["success"]:
        print("✅ 质量分析完成")
        
        # 显示质量指标
        metrics = quality_data["data"]["quality_metrics"]
        print(f"\n📈 质量指标:")
        print(f"  - 总体评分: {metrics['overall_score']:.2f}")
        print(f"  - 准确性: {metrics['accuracy_score']:.2f}")
        print(f"  - 流畅性: {metrics['fluency_score']:.2f}")
        print(f"  - 一致性: {metrics['consistency_score']:.2f}")
        print(f"  - 文化适配: {metrics['cultural_adaptation_score']:.2f}")
        print(f"  - 时间控制: {metrics['timing_score']:.2f}")
        
        # 显示发现的问题
        issues = quality_data["data"]["detailed_issues"]
        print(f"\n🔍 发现的问题 ({len(issues)} 个):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. 条目{issue['sequence']} - {issue['issue_type']}")
            print(f"     描述: {issue['description']}")
            print(f"     严重程度: {issue['severity']}")
            print(f"     建议: {issue['suggestion']}")
            print()
        
        # 显示改进建议
        recommendations = metrics.get("recommendations", [])
        if recommendations:
            print("💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # 显示问题统计
        issue_stats = quality_data["data"]["issue_statistics"]
        print(f"\n📊 问题统计:")
        for issue_type, stats in issue_stats.items():
            print(f"  - {issue_type}: {stats['total']} 个 (高:{stats['high']}, 中:{stats['medium']}, 低:{stats['low']})")
        
    else:
        print(f"❌ 质量分析失败: {quality_data['error']}")
    
    print("\n" + "=" * 50 + "\n")

def main():
    """主函数，运行所有示例"""
    print("🎬 Strands Agent字幕翻译系统使用示例")
    print("=" * 60)
    print("本示例展示了完整的字幕翻译工作流程")
    print("包括解析、分析、翻译、验证和导出等步骤")
    print("=" * 60)
    print()
    
    try:
        # 运行所有示例
        example_1_basic_translation()
        example_2_step_by_step()
        example_3_multiple_languages()
        example_4_quality_analysis()
        
        print("🎉 所有示例运行完成！")
        print("\n📚 更多信息请参考:")
        print("  - README.md: 详细文档")
        print("  - test_enhanced_tools.py: 测试用例")
        print("  - subtitle_translation_agent.py: Agent实现")
        
    except Exception as e:
        print(f"❌ 示例运行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()