#!/usr/bin/env python3
"""
术语一致性管理器演示脚本
展示术语库管理、一致性检查和冲突解决功能
"""
import json
from datetime import datetime
from agents.terminology_consistency_manager import (
    TerminologyConsistencyManager, TermEntry, ConsistencyCheckRequest,
    TermType, ConsistencyLevel, ConflictSeverity
)
from models.subtitle_models import SubtitleEntry, TimeCode


def demonstrate_term_management(manager: TerminologyConsistencyManager):
    """演示术语管理功能"""
    print("\n" + "="*60)
    print("术语管理功能演示")
    print("="*60)
    
    # 添加新术语
    print("\n1. 添加新术语")
    new_terms = [
        TermEntry(
            term_id="demo_submarine",
            source_text="潜艇",
            term_type=TermType.MILITARY_TERM,
            consistency_level=ConsistencyLevel.STRICT,
            translations={
                "en": "submarine",
                "ja": "潜水艦",
                "ko": "잠수함",
                "fr": "sous-marin",
                "de": "U-Boot"
            },
            aliases=["潜水艇", "潜艇部队"],
            context_examples=["潜艇正在下潜", "我们的潜艇"],
            approved=True
        ),
        TermEntry(
            term_id="demo_sonar",
            source_text="声纳",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.MODERATE,
            translations={
                "en": "sonar",
                "ja": "ソナー",
                "ko": "소나",
                "fr": "sonar",
                "de": "Sonar"
            },
            aliases=["声纳系统", "声波探测"],
            context_examples=["声纳检测到目标", "声纳操作员"],
            approved=True
        ),
        TermEntry(
            term_id="demo_admiral",
            source_text="海军上将",
            term_type=TermType.TITLE,
            consistency_level=ConsistencyLevel.CONTEXTUAL,
            translations={
                "en": "Admiral",
                "ja": "海軍大将",
                "ko": "해군대장",
                "fr": "Amiral",
                "de": "Admiral"
            },
            aliases=["上将", "海军将领"],
            context_examples=["海军上将下达命令", "尊敬的上将"],
            approved=True
        )
    ]
    
    for term in new_terms:
        success = manager.add_term(term)
        print(f"  添加术语 '{term.source_text}': {'成功' if success else '失败'}")
    
    # 查找术语
    print("\n2. 术语查找演示")
    search_queries = [
        ("潜艇", "zh", None),
        ("submarine", "en", None),
        ("声纳", "zh", TermType.TECHNICAL_TERM),
        ("Admiral", "en", TermType.TITLE)
    ]
    
    for query, language, term_type in search_queries:
        results = manager.find_terms(query, language, term_type, limit=3)
        print(f"  查找 '{query}' ({language}): 找到 {len(results)} 个结果")
        for result in results:
            print(f"    - {result.source_text} ({result.term_type.value})")
    
    # 更新术语
    print("\n3. 术语更新演示")
    updates = {
        "translations": {
            "en": "submarine",
            "ja": "潜水艦",
            "ko": "잠수함",
            "fr": "sous-marin",
            "de": "U-Boot",
            "es": "submarino"  # 添加西班牙语翻译
        },
        "aliases": ["潜水艇", "潜艇部队", "水下舰艇"]  # 添加新别名
    }
    
    success = manager.update_term("demo_submarine", updates)
    print(f"  更新术语 '潜艇': {'成功' if success else '失败'}")
    
    if success:
        updated_term = manager.term_database["demo_submarine"]
        print(f"    新增语言: {list(updated_term.translations.keys())}")
        print(f"    别名数量: {len(updated_term.aliases)}")


def demonstrate_consistency_check(manager: TerminologyConsistencyManager):
    """演示一致性检查功能"""
    print("\n" + "="*60)
    print("一致性检查功能演示")
    print("="*60)
    
    # 创建测试字幕数据
    print("\n1. 创建测试字幕数据")
    subtitle_entries = [
        SubtitleEntry(
            index=1, 
            start_time=TimeCode(0, 0, 0, 0), 
            end_time=TimeCode(0, 0, 3, 0), 
            text="张伟队长，我们的潜艇已经准备就绪"
        ),
        SubtitleEntry(
            index=2, 
            start_time=TimeCode(0, 0, 3, 0), 
            end_time=TimeCode(0, 0, 6, 0), 
            text="声纳显示前方有目标"
        ),
        SubtitleEntry(
            index=3, 
            start_time=TimeCode(0, 0, 6, 0), 
            end_time=TimeCode(0, 0, 9, 0), 
            text="海军上将下达了新的命令"
        ),
        SubtitleEntry(
            index=4, 
            start_time=TimeCode(0, 0, 9, 0), 
            end_time=TimeCode(0, 0, 12, 0), 
            text="雷达和声纳系统都在正常工作"
        ),
        SubtitleEntry(
            index=5, 
            start_time=TimeCode(0, 0, 12, 0), 
            end_time=TimeCode(0, 0, 15, 0), 
            text="司令，潜水艇正在下潜"
        ),  # 使用了别名"潜水艇"
        SubtitleEntry(
            index=6, 
            start_time=TimeCode(0, 0, 15, 0), 
            end_time=TimeCode(0, 0, 18, 0), 
            text="张队长，声波探测发现异常"
        )  # 使用了别名"声波探测"
    ]
    
    print(f"  创建了 {len(subtitle_entries)} 条字幕")
    for entry in subtitle_entries:
        print(f"    {entry.index}: {entry.text}")
    
    # 执行一致性检查
    print("\n2. 执行一致性检查")
    request = ConsistencyCheckRequest(
        request_id=f"demo_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        project_id="demo_project",
        subtitle_entries=subtitle_entries,
        target_languages=["en", "ja", "ko"],
        check_scope="project",
        strict_mode=False,
        auto_resolve=True
    )
    
    result = manager.check_consistency(request)
    
    print(f"  检查结果: {'成功' if result.success else '失败'}")
    print(f"  一致性分数: {result.consistency_score:.2f}")
    print(f"  检查术语总数: {result.total_terms_checked}")
    print(f"  发现冲突数: {result.conflicting_terms_count}")
    print(f"  自动解决数: {result.auto_resolved_count}")
    print(f"  需人工审核: {result.manual_review_required}")
    print(f"  处理时间: {result.processing_time_ms} ms")
    
    # 显示发现的冲突
    if result.conflicts_found:
        print("\n3. 发现的冲突详情")
        for i, conflict in enumerate(result.conflicts_found, 1):
            print(f"  冲突 {i}:")
            print(f"    术语: {conflict.source_text}")
            print(f"    严重程度: {conflict.severity.value}")
            print(f"    冲突翻译: {conflict.conflicting_translations}")
            print(f"    建议解决方案: {conflict.suggested_resolution}")
            print(f"    解决策略: {conflict.resolution_strategy.value if conflict.resolution_strategy else 'N/A'}")
            print(f"    已解决: {'是' if conflict.resolved else '否'}")
    else:
        print("\n3. 未发现术语冲突")
    
    # 显示改进建议
    if result.recommendations:
        print("\n4. 改进建议")
        for i, recommendation in enumerate(result.recommendations, 1):
            print(f"  {i}. {recommendation}")


def demonstrate_conflict_resolution(manager: TerminologyConsistencyManager):
    """演示冲突解决功能"""
    print("\n" + "="*60)
    print("冲突解决功能演示")
    print("="*60)
    
    # 人为创建一个冲突场景
    print("\n1. 创建冲突场景")
    
    # 添加一个有歧义的术语
    conflicting_term = TermEntry(
        term_id="demo_conflicting_term",
        source_text="导弹",
        term_type=TermType.MILITARY_TERM,
        consistency_level=ConsistencyLevel.STRICT,
        translations={
            "en": "missile",
            "ja": "ミサイル"
        },
        aliases=["导弹武器"],
        context_examples=["导弹发射", "导弹系统"],
        approved=True
    )
    
    manager.add_term(conflicting_term)
    print("  添加了术语 '导弹'")
    
    # 创建包含不同变体的字幕
    conflicting_subtitles = [
        SubtitleEntry(
            index=1, 
            start_time=TimeCode(0, 0, 0, 0), 
            end_time=TimeCode(0, 0, 3, 0), 
            text="导弹已经准备发射"
        ),
        SubtitleEntry(
            index=2, 
            start_time=TimeCode(0, 0, 3, 0), 
            end_time=TimeCode(0, 0, 6, 0), 
            text="missile is ready to launch"
        ),
        SubtitleEntry(
            index=3, 
            start_time=TimeCode(0, 0, 6, 0), 
            end_time=TimeCode(0, 0, 9, 0), 
            text="导弹武器系统激活"
        ),
        SubtitleEntry(
            index=4, 
            start_time=TimeCode(0, 0, 9, 0), 
            end_time=TimeCode(0, 0, 12, 0), 
            text="rocket launcher activated"
        )  # 使用了不同的英文术语
    ]
    
    # 执行检查以产生冲突
    conflict_request = ConsistencyCheckRequest(
        request_id="conflict_demo",
        project_id="conflict_project",
        subtitle_entries=conflicting_subtitles,
        target_languages=["en", "ja"],
        strict_mode=True,
        auto_resolve=False
    )
    
    conflict_result = manager.check_consistency(conflict_request)
    
    print(f"\n2. 冲突检查结果")
    print(f"  发现冲突: {len(conflict_result.conflicts_found)} 个")
    
    # 显示活跃冲突
    active_conflicts = list(manager.active_conflicts.values())
    if active_conflicts:
        print(f"\n3. 活跃冲突列表")
        for i, conflict in enumerate(active_conflicts, 1):
            print(f"  冲突 {i} (ID: {conflict.conflict_id[:8]}...):")
            print(f"    术语: {conflict.source_text}")
            print(f"    严重程度: {conflict.severity.value}")
            print(f"    建议解决: {conflict.suggested_resolution}")
            
            # 演示手动解决冲突
            if i == 1:  # 只解决第一个冲突作为演示
                print(f"\n4. 手动解决冲突 {conflict.conflict_id[:8]}...")
                resolution_note = f"统一使用标准翻译: {conflict.suggested_resolution}"
                success = manager.resolve_conflict(
                    conflict.conflict_id, 
                    resolution_note, 
                    "demo_user"
                )
                print(f"    解决结果: {'成功' if success else '失败'}")
    
    # 显示冲突摘要
    print(f"\n5. 冲突管理摘要")
    conflict_summary = manager.get_conflict_summary()
    print(f"  活跃冲突: {conflict_summary['active_conflicts']} 个")
    print(f"  已解决冲突: {conflict_summary['resolved_conflicts']} 个")
    print(f"  解决率: {conflict_summary['resolution_rate']:.1f}%")
    
    if conflict_summary['active_by_severity']:
        print("  按严重程度分布:")
        for severity, count in conflict_summary['active_by_severity'].items():
            print(f"    {severity}: {count} 个")


def demonstrate_performance_stats(manager: TerminologyConsistencyManager):
    """演示性能统计功能"""
    print("\n" + "="*60)
    print("性能统计功能演示")
    print("="*60)
    
    stats = manager.get_performance_stats()
    
    print("\n1. 基础统计")
    basic_stats = stats["basic_stats"]
    print(f"  术语总数: {basic_stats['total_terms']}")
    print(f"  检查总次数: {basic_stats['total_checks']}")
    print(f"  检测到的冲突: {basic_stats['conflicts_detected']}")
    print(f"  已解决冲突: {basic_stats['conflicts_resolved']}")
    print(f"  平均一致性分数: {basic_stats['average_consistency_score']:.3f}")
    
    print("\n2. 语言覆盖情况")
    language_coverage = stats["language_coverage"]
    for language, count in sorted(language_coverage.items()):
        print(f"  {language}: {count} 个术语")
    
    print("\n3. 术语类型分布")
    term_type_dist = stats["term_type_distribution"]
    for term_type, count in sorted(term_type_dist.items()):
        print(f"  {term_type}: {count} 个")
    
    print("\n4. 冲突严重程度分布")
    conflict_severity_dist = stats["conflict_severity_distribution"]
    if conflict_severity_dist:
        for severity, count in sorted(conflict_severity_dist.items()):
            print(f"  {severity}: {count} 个")
    else:
        print("  暂无冲突记录")
    
    print(f"\n5. 当前状态")
    print(f"  活跃冲突: {stats['active_conflicts_count']} 个")
    print(f"  已解决冲突: {stats['resolved_conflicts_count']} 个")


def demonstrate_database_operations(manager: TerminologyConsistencyManager):
    """演示数据库操作功能"""
    print("\n" + "="*60)
    print("数据库操作功能演示")
    print("="*60)
    
    # 导出数据库
    print("\n1. 导出术语数据库")
    export_file = f"terminology_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    success = manager.export_terminology_database(export_file)
    print(f"  导出结果: {'成功' if success else '失败'}")
    if success:
        print(f"  导出文件: {export_file}")
        
        # 显示导出文件的部分内容
        try:
            with open(export_file, 'r', encoding='utf-8') as f:
                export_data = json.load(f)
            
            print(f"  导出的术语数量: {len(export_data.get('terms', []))}")
            print(f"  导出时间: {export_data.get('metadata', {}).get('export_time', 'N/A')}")
            
            # 显示前几个术语的信息
            terms = export_data.get('terms', [])[:3]
            if terms:
                print("  示例术语:")
                for term in terms:
                    print(f"    - {term.get('source_text', 'N/A')} ({term.get('term_type', 'N/A')})")
        
        except Exception as e:
            print(f"  读取导出文件时出错: {e}")
    
    # 演示导入功能（创建新的管理器实例）
    print("\n2. 导入术语数据库演示")
    if success:
        print("  创建新的管理器实例...")
        new_manager = TerminologyConsistencyManager("import_demo_manager")
        original_count = len(new_manager.term_database)
        print(f"  新管理器初始术语数: {original_count}")
        
        print("  执行导入...")
        import_success = new_manager.import_terminology_database(export_file)
        print(f"  导入结果: {'成功' if import_success else '失败'}")
        
        if import_success:
            new_count = len(new_manager.term_database)
            print(f"  导入后术语数: {new_count}")
            print(f"  新增术语数: {new_count - original_count}")
        
        # 清理导出文件
        try:
            import os
            os.remove(export_file)
            print(f"  已清理临时文件: {export_file}")
        except:
            print(f"  注意: 请手动删除临时文件 {export_file}")


def main():
    """主演示函数"""
    print("字幕翻译系统 - 术语一致性管理器演示")
    print("="*60)
    
    # 创建术语一致性管理器
    print("初始化术语一致性管理器...")
    manager = TerminologyConsistencyManager("demo_manager")
    print(f"管理器ID: {manager.manager_id}")
    print(f"初始术语数量: {len(manager.term_database)}")
    
    try:
        # 演示各种功能
        demonstrate_term_management(manager)
        demonstrate_consistency_check(manager)
        demonstrate_conflict_resolution(manager)
        demonstrate_performance_stats(manager)
        demonstrate_database_operations(manager)
        
        print("\n" + "="*60)
        print("演示完成!")
        print("="*60)
        
        # 最终统计
        final_stats = manager.get_performance_stats()
        print(f"\n最终统计:")
        print(f"  术语总数: {final_stats['basic_stats']['total_terms']}")
        print(f"  执行检查: {final_stats['basic_stats']['total_checks']} 次")
        print(f"  检测冲突: {final_stats['basic_stats']['conflicts_detected']} 个")
        print(f"  解决冲突: {final_stats['basic_stats']['conflicts_resolved']} 个")
        print(f"  平均一致性分数: {final_stats['basic_stats']['average_consistency_score']:.3f}")
        
    except KeyboardInterrupt:
        print("\n\n用户中断演示")
    except Exception as e:
        print(f"\n\n演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n感谢使用术语一致性管理器演示!")


if __name__ == "__main__":
    main()