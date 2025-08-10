#!/usr/bin/env python3
"""
翻译质量评估器演示脚本
展示如何使用翻译质量评估器进行多维度质量评估
"""
import asyncio
import json
from datetime import datetime
from agents.translation_quality_evaluator import (
    TranslationQualityEvaluator, QualityEvaluationRequest, 
    QualityDimension, QualityLevel, EvaluationMethod
)
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationResult


async def create_demo_data():
    """创建演示数据"""
    # 原始字幕
    original_entries = [
        SubtitleEntry(
            index=1,
            start_time=0.0,
            end_time=3.0,
            text="欢迎收看《爱上海军蓝》，我是主持人张伟。",
            speaker="张伟",
            scene_description="演播室内，主持人面向镜头"
        ),
        SubtitleEntry(
            index=2,
            start_time=3.0,
            end_time=6.0,
            text="今天我们邀请到了海军司令李明将军。",
            speaker="张伟",
            scene_description="镜头转向嘉宾席"
        ),
        SubtitleEntry(
            index=3,
            start_time=6.0,
            end_time=9.0,
            text="司令，请您介绍一下我们海军的雷达系统。",
            speaker="张伟",
            scene_description="主持人向嘉宾提问"
        ),
        SubtitleEntry(
            index=4,
            start_time=9.0,
            end_time=13.0,
            text="我们的雷达系统采用了最先进的技术，能够探测到200公里外的目标。",
            speaker="李明",
            scene_description="司令认真回答问题"
        ),
        SubtitleEntry(
            index=5,
            start_time=13.0,
            end_time=17.0,
            text="这套系统不仅提高了我们的防御能力，也增强了战术优势。",
            speaker="李明",
            scene_description="司令继续介绍技术细节"
        )
    ]
    
    # 高质量英语翻译
    excellent_translations = [
        TranslationResult(
            original_index=1,
            translated_text="Welcome to 'Love Navy Blue', I'm host Zhang Wei.",
            target_language="en",
            success=True,
            quality_score=0.95,
            confidence=0.9,
            processing_time_ms=150
        ),
        TranslationResult(
            original_index=2,
            translated_text="Today we have invited Navy Commander General Li Ming.",
            target_language="en",
            success=True,
            quality_score=0.92,
            confidence=0.88,
            processing_time_ms=180
        ),
        TranslationResult(
            original_index=3,
            translated_text="Commander, please introduce our navy's radar system.",
            target_language="en",
            success=True,
            quality_score=0.90,
            confidence=0.85,
            processing_time_ms=160
        ),
        TranslationResult(
            original_index=4,
            translated_text="Our radar system uses the most advanced technology and can detect targets 200 kilometers away.",
            target_language="en",
            success=True,
            quality_score=0.88,
            confidence=0.87,
            processing_time_ms=200
        ),
        TranslationResult(
            original_index=5,
            translated_text="This system not only improves our defensive capabilities but also enhances tactical advantages.",
            target_language="en",
            success=True,
            quality_score=0.91,
            confidence=0.89,
            processing_time_ms=190
        )
    ]
    
    # 中等质量翻译（有一些问题）
    average_translations = [
        TranslationResult(
            original_index=1,
            translated_text="Welcome to Love Navy Blue, I am host Zhang Wei.",  # 缺少引号
            target_language="en",
            success=True,
            quality_score=0.75,
            confidence=0.7
        ),
        TranslationResult(
            original_index=2,
            translated_text="Today we have invite Navy Commander General Li Ming.",  # 语法错误
            target_language="en",
            success=True,
            quality_score=0.65,
            confidence=0.6
        ),
        TranslationResult(
            original_index=3,
            translated_text="Commander, please introduce our navy radar system.",  # 缺少所有格
            target_language="en",
            success=True,
            quality_score=0.78,
            confidence=0.72
        ),
        TranslationResult(
            original_index=4,
            translated_text="Our radar system use most advanced technology, can detect target 200 kilometer away.",  # 多个语法错误
            target_language="en",
            success=True,
            quality_score=0.55,
            confidence=0.5
        ),
        TranslationResult(
            original_index=5,
            translated_text="This system not only improve our defense ability, also enhance tactical advantage.",  # 语法和词汇问题
            target_language="en",
            success=True,
            quality_score=0.60,
            confidence=0.55
        )
    ]
    
    # 低质量翻译（严重问题）
    poor_translations = [
        TranslationResult(
            original_index=1,
            translated_text="",  # 空翻译
            target_language="en",
            success=False,
            quality_score=0.0,
            confidence=0.0
        ),
        TranslationResult(
            original_index=2,
            translated_text="Today we have invited Navy Commander General Li Ming Navy Commander General Li Ming.",  # 重复
            target_language="en",
            success=True,
            quality_score=0.3,
            confidence=0.2
        ),
        TranslationResult(
            original_index=3,
            translated_text="Commander, please introduce our navy's radar system radar system radar system.",  # 严重重复
            target_language="en",
            success=True,
            quality_score=0.2,
            confidence=0.1
        ),
        TranslationResult(
            original_index=4,
            translated_text="Our radar system use most advanced technology can detect target 200 kilometer away technology.",  # 混乱的语法
            target_language="en",
            success=True,
            quality_score=0.25,
            confidence=0.15
        ),
        TranslationResult(
            original_index=5,
            translated_text="System improve defense enhance tactical.",  # 不完整翻译
            target_language="en",
            success=True,
            quality_score=0.1,
            confidence=0.05
        )
    ]
    
    # 日语翻译（测试文化适配）
    japanese_translations = [
        TranslationResult(
            original_index=1,
            translated_text="『愛上海軍藍』へようこそ、司会の張偉です。",
            target_language="ja",
            success=True,
            quality_score=0.90,
            confidence=0.85
        ),
        TranslationResult(
            original_index=2,
            translated_text="今日は海軍司令官の李明将軍をお招きしました。",
            target_language="ja",
            success=True,
            quality_score=0.88,
            confidence=0.82
        ),
        TranslationResult(
            original_index=3,
            translated_text="司令官、我々の海軍のレーダーシステムについて紹介してください。",
            target_language="ja",
            success=True,
            quality_score=0.85,
            confidence=0.80
        ),
        TranslationResult(
            original_index=4,
            translated_text="我々のレーダーシステムは最先端の技術を採用し、200キロメートル先の目標を探知できます。",
            target_language="ja",
            success=True,
            quality_score=0.92,
            confidence=0.88
        ),
        TranslationResult(
            original_index=5,
            translated_text="このシステムは防御能力を向上させるだけでなく、戦術的優位性も強化します。",
            target_language="ja",
            success=True,
            quality_score=0.89,
            confidence=0.86
        )
    ]
    
    return original_entries, {
        "excellent": excellent_translations,
        "average": average_translations,
        "poor": poor_translations,
        "japanese": japanese_translations
    }


async def demonstrate_basic_evaluation():
    """演示基础质量评估功能"""
    print("\\n" + "="*60)
    print("演示1: 基础质量评估功能")
    print("="*60)
    
    evaluator = TranslationQualityEvaluator("demo_evaluator")
    original_entries, translations = await create_demo_data()
    
    # 评估高质量翻译
    print("\\n评估高质量翻译:")
    excellent_request = QualityEvaluationRequest(
        request_id="demo_excellent_001",
        original_entries=original_entries,
        translation_results=translations["excellent"],
        target_language="en"
    )
    
    excellent_result = await evaluator.evaluate_quality(excellent_request)
    
    print(f"  总体分数: {excellent_result.overall_score:.3f}")
    print(f"  质量等级: {excellent_result.quality_level.value}")
    print(f"  置信度: {excellent_result.confidence:.3f}")
    print(f"  处理时间: {excellent_result.processing_time_ms}ms")
    print(f"  发现问题数: {len(excellent_result.issues_found)}")
    
    print("\\n  各维度分数:")
    for dimension, metric in excellent_result.dimension_scores.items():
        print(f"    {dimension.value}: {metric.score:.3f} (权重: {metric.weight:.2f}, 置信度: {metric.confidence:.2f})")
    
    if excellent_result.recommendations:
        print("\\n  改进建议:")
        for i, rec in enumerate(excellent_result.recommendations, 1):
            print(f"    {i}. {rec}")
    
    # 评估中等质量翻译
    print("\\n评估中等质量翻译:")
    average_request = QualityEvaluationRequest(
        request_id="demo_average_001",
        original_entries=original_entries,
        translation_results=translations["average"],
        target_language="en"
    )
    
    average_result = await evaluator.evaluate_quality(average_request)
    
    print(f"  总体分数: {average_result.overall_score:.3f}")
    print(f"  质量等级: {average_result.quality_level.value}")
    print(f"  发现问题数: {len(average_result.issues_found)}")
    
    if average_result.issues_found:
        print("\\n  发现的问题:")
        for issue in average_result.issues_found[:3]:  # 只显示前3个问题
            print(f"    - {issue.issue_type} ({issue.severity}): {issue.description}")
            if issue.suggestion:
                print(f"      建议: {issue.suggestion}")
    
    # 评估低质量翻译
    print("\\n评估低质量翻译:")
    poor_request = QualityEvaluationRequest(
        request_id="demo_poor_001",
        original_entries=original_entries,
        translation_results=translations["poor"],
        target_language="en"
    )
    
    poor_result = await evaluator.evaluate_quality(poor_request)
    
    print(f"  总体分数: {poor_result.overall_score:.3f}")
    print(f"  质量等级: {poor_result.quality_level.value}")
    print(f"  发现问题数: {len(poor_result.issues_found)}")
    
    print("\\n  主要问题:")
    critical_issues = [issue for issue in poor_result.issues_found if issue.severity == "critical"]
    for issue in critical_issues[:3]:
        print(f"    - {issue.description}")


async def demonstrate_multilingual_evaluation():
    """演示多语言质量评估"""
    print("\\n" + "="*60)
    print("演示2: 多语言质量评估")
    print("="*60)
    
    evaluator = TranslationQualityEvaluator("demo_multilingual")
    original_entries, translations = await create_demo_data()
    
    # 评估日语翻译
    print("\\n评估日语翻译:")
    japanese_request = QualityEvaluationRequest(
        request_id="demo_japanese_001",
        original_entries=original_entries,
        translation_results=translations["japanese"],
        target_language="ja"
    )
    
    japanese_result = await evaluator.evaluate_quality(japanese_request)
    
    print(f"  总体分数: {japanese_result.overall_score:.3f}")
    print(f"  质量等级: {japanese_result.quality_level.value}")
    
    print("\\n  各维度分数:")
    for dimension, metric in japanese_result.dimension_scores.items():
        print(f"    {dimension.value}: {metric.score:.3f}")
    
    # 特别关注文化适配性
    cultural_metric = japanese_result.dimension_scores[QualityDimension.CULTURAL_ADAPTATION]
    print(f"\\n  文化适配性详情:")
    print(f"    分数: {cultural_metric.score:.3f}")
    print(f"    评估方法: {cultural_metric.method.value}")
    print(f"    置信度: {cultural_metric.confidence:.3f}")
    
    # 比较不同语言的配置
    print("\\n  语言特定配置比较:")
    languages = ["en", "ja", "ko", "ar"]
    for lang in languages:
        config = evaluator.language_configs.get(lang, {})
        print(f"    {lang}:")
        print(f"      最大字符/行: {config.get('max_chars_per_line', 'N/A')}")
        print(f"      阅读速度: {config.get('reading_speed_cps', 'N/A')} 字符/秒")
        print(f"      需要敬语: {config.get('honorific_required', False)}")
        if lang == "ar":
            print(f"      从右到左: {config.get('rtl_text', False)}")


async def demonstrate_dimension_analysis():
    """演示维度分析功能"""
    print("\\n" + "="*60)
    print("演示3: 质量维度详细分析")
    print("="*60)
    
    evaluator = TranslationQualityEvaluator("demo_dimension")
    original_entries, translations = await create_demo_data()
    
    # 使用中等质量翻译进行详细分析
    request = QualityEvaluationRequest(
        request_id="demo_dimension_001",
        original_entries=original_entries,
        translation_results=translations["average"],
        target_language="en"
    )
    
    result = await evaluator.evaluate_quality(request)
    
    print("\\n详细维度分析:")
    
    # 分析每个维度
    for dimension, metric in result.dimension_scores.items():
        print(f"\\n{dimension.value.upper()} (权重: {metric.weight:.2f}):")
        print(f"  分数: {metric.score:.3f}")
        print(f"  置信度: {metric.confidence:.3f}")
        print(f"  评估方法: {metric.method.value}")
        
        # 显示详细信息
        if metric.details:
            print("  详细信息:")
            for key, value in metric.details.items():
                if isinstance(value, float):
                    print(f"    {key}: {value:.3f}")
                else:
                    print(f"    {key}: {value}")
        
        # 根据分数给出具体建议
        if metric.score < 0.6:
            print(f"  ⚠️  {dimension.value}分数较低，需要重点改进")
        elif metric.score < 0.8:
            print(f"  ⚡ {dimension.value}有改进空间")
        else:
            print(f"  ✅ {dimension.value}表现良好")
    
    # 权重分析
    print("\\n权重分布分析:")
    total_weight = sum(metric.weight for metric in result.dimension_scores.values())
    print(f"  总权重: {total_weight:.2f}")
    
    sorted_dimensions = sorted(
        result.dimension_scores.items(),
        key=lambda x: x[1].weight,
        reverse=True
    )
    
    for dimension, metric in sorted_dimensions:
        percentage = (metric.weight / total_weight) * 100
        print(f"  {dimension.value}: {percentage:.1f}% (权重: {metric.weight:.2f})")


async def demonstrate_quality_issues_analysis():
    """演示质量问题分析"""
    print("\\n" + "="*60)
    print("演示4: 质量问题详细分析")
    print("="*60)
    
    evaluator = TranslationQualityEvaluator("demo_issues")
    original_entries, translations = await create_demo_data()
    
    # 使用低质量翻译来展示问题检测
    request = QualityEvaluationRequest(
        request_id="demo_issues_001",
        original_entries=original_entries,
        translation_results=translations["poor"],
        target_language="en"
    )
    
    result = await evaluator.evaluate_quality(request)
    
    print(f"\\n发现 {len(result.issues_found)} 个质量问题:")
    
    # 按严重程度分组
    issues_by_severity = {}
    for issue in result.issues_found:
        if issue.severity not in issues_by_severity:
            issues_by_severity[issue.severity] = []
        issues_by_severity[issue.severity].append(issue)
    
    severity_order = ["critical", "high", "medium", "low"]
    for severity in severity_order:
        if severity in issues_by_severity:
            issues = issues_by_severity[severity]
            print(f"\\n{severity.upper()}级问题 ({len(issues)}个):")
            
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue.description}")
                if issue.location:
                    print(f"     位置: {issue.location}")
                if issue.suggestion:
                    print(f"     建议: {issue.suggestion}")
                print(f"     置信度: {issue.confidence:.2f}")
                if issue.metadata:
                    print(f"     元数据: {issue.metadata}")
    
    # 问题类型统计
    print("\\n问题类型统计:")
    issue_types = {}
    for issue in result.issues_found:
        issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
    
    for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue_type}: {count}个")
    
    # 改进建议
    print("\\n改进建议:")
    for i, recommendation in enumerate(result.recommendations, 1):
        print(f"  {i}. {recommendation}")


async def demonstrate_performance_analysis():
    """演示性能分析功能"""
    print("\\n" + "="*60)
    print("演示5: 性能统计和分析")
    print("="*60)
    
    evaluator = TranslationQualityEvaluator("demo_performance")
    original_entries, translations = await create_demo_data()
    
    # 执行多次评估来收集统计数据
    print("\\n执行多次评估以收集统计数据...")
    
    test_cases = [
        ("excellent", "en"),
        ("average", "en"),
        ("poor", "en"),
        ("japanese", "ja"),
        ("excellent", "en"),  # 重复测试
        ("average", "en")
    ]
    
    for i, (quality_type, language) in enumerate(test_cases):
        request = QualityEvaluationRequest(
            request_id=f"demo_perf_{i:03d}",
            original_entries=original_entries,
            translation_results=translations[quality_type],
            target_language=language
        )
        
        result = await evaluator.evaluate_quality(request)
        print(f"  评估 {i+1}: {quality_type} ({language}) - 分数: {result.overall_score:.3f}, 时间: {result.processing_time_ms}ms")
    
    # 获取统计信息
    stats = evaluator.get_evaluation_statistics()
    
    print("\\n评估统计信息:")
    print(f"  总评估次数: {stats['total_evaluations']}")
    
    if 'average_processing_time_ms' in stats:
        print(f"  平均处理时间: {stats['average_processing_time_ms']:.1f}ms")
    if 'median_processing_time_ms' in stats:
        print(f"  中位处理时间: {stats['median_processing_time_ms']:.1f}ms")
    
    print("\\n各维度平均分数:")
    for dimension, avg_score in stats['average_scores'].items():
        print(f"  {dimension}: {avg_score:.3f}")
    
    print("\\n语言统计:")
    for language, lang_stats in stats['language_stats'].items():
        print(f"  {language}:")
        print(f"    评估次数: {lang_stats['evaluations']}")
        if 'average_score' in lang_stats:
            print(f"    平均分数: {lang_stats['average_score']:.3f}")
    
    print("\\n问题频率统计:")
    for issue_type, frequency in sorted(stats['issue_frequency'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue_type}: {frequency}次")


async def demonstrate_custom_evaluation():
    """演示自定义评估配置"""
    print("\\n" + "="*60)
    print("演示6: 自定义评估配置")
    print("="*60)
    
    # 创建自定义配置的评估器
    evaluator = TranslationQualityEvaluator("demo_custom")
    
    # 修改权重配置
    print("\\n修改评估维度权重:")
    print("原始权重:")
    for dimension, weight in evaluator.dimension_weights.items():
        print(f"  {dimension.value}: {weight:.2f}")
    
    # 调整权重 - 更重视准确性和流畅性
    evaluator.dimension_weights[QualityDimension.ACCURACY] = 0.4
    evaluator.dimension_weights[QualityDimension.FLUENCY] = 0.3
    evaluator.dimension_weights[QualityDimension.CULTURAL_ADAPTATION] = 0.15
    evaluator.dimension_weights[QualityDimension.CONSISTENCY] = 0.1
    evaluator.dimension_weights[QualityDimension.COMPLETENESS] = 0.03
    evaluator.dimension_weights[QualityDimension.READABILITY] = 0.01
    evaluator.dimension_weights[QualityDimension.TIMING_SYNC] = 0.01
    
    print("\\n调整后权重:")
    for dimension, weight in evaluator.dimension_weights.items():
        print(f"  {dimension.value}: {weight:.2f}")
    
    # 使用新权重进行评估
    original_entries, translations = await create_demo_data()
    
    request = QualityEvaluationRequest(
        request_id="demo_custom_001",
        original_entries=original_entries,
        translation_results=translations["average"],
        target_language="en",
        evaluation_config={
            "focus_on_accuracy": True,
            "strict_mode": True
        }
    )
    
    result = await evaluator.evaluate_quality(request)
    
    print(f"\\n自定义权重评估结果:")
    print(f"  总体分数: {result.overall_score:.3f}")
    print(f"  质量等级: {result.quality_level.value}")
    
    print("\\n各维度贡献度:")
    total_weighted_score = 0
    for dimension, metric in result.dimension_scores.items():
        weighted_contribution = metric.score * metric.weight
        total_weighted_score += weighted_contribution
        print(f"  {dimension.value}: {weighted_contribution:.4f} (分数: {metric.score:.3f} × 权重: {metric.weight:.2f})")
    
    print(f"\\n总加权分数: {total_weighted_score:.4f}")


async def main():
    """主演示函数"""
    print("字幕翻译系统 - 翻译质量评估器演示")
    print("="*60)
    print("本演示将展示翻译质量评估器的各种功能")
    
    try:
        # 运行各个演示
        await demonstrate_basic_evaluation()
        await demonstrate_multilingual_evaluation()
        await demonstrate_dimension_analysis()
        await demonstrate_quality_issues_analysis()
        await demonstrate_performance_analysis()
        await demonstrate_custom_evaluation()
        
        print("\\n" + "="*60)
        print("演示完成!")
        print("="*60)
        print("\\n翻译质量评估器主要功能:")
        print("✅ 多维度质量评估 (准确性、流畅性、文化适配性等)")
        print("✅ 语言特定的质量检查")
        print("✅ 智能问题检测和建议生成")
        print("✅ 可配置的评估权重和阈值")
        print("✅ 详细的统计分析和报告")
        print("✅ 支持多种评估方法 (规则、统计、语义、上下文)")
        print("✅ 实时性能监控和优化")
        
    except KeyboardInterrupt:
        print("\\n用户中断演示")
    except Exception as e:
        print(f"\\n演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())