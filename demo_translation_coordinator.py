#!/usr/bin/env python3
"""
翻译协调 Agent 演示脚本
展示如何使用翻译协调 Agent 进行多语言字幕翻译任务的协调和管理
"""
import asyncio
import json
from datetime import datetime
from agents.translation_coordinator_agent import (
    TranslationCoordinatorAgent, CoordinationRequest, QualityThreshold
)
from agents.translation_scheduler import TaskPriority
from models.subtitle_models import SubtitleEntry


async def create_demo_subtitles() -> list[SubtitleEntry]:
    """创建演示字幕数据"""
    return [
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
        ),
        SubtitleEntry(
            index=6,
            start_time=17.0,
            end_time=20.0,
            text="非常感谢司令的详细介绍，让我们对海军技术有了更深的了解。",
            speaker="张伟",
            scene_description="主持人表示感谢"
        ),
        SubtitleEntry(
            index=7,
            start_time=20.0,
            end_time=23.0,
            text="作为一名海军军官，我深感责任重大，使命光荣。",
            speaker="李明",
            scene_description="司令表达军人情怀"
        ),
        SubtitleEntry(
            index=8,
            start_time=23.0,
            end_time=26.0,
            text="我们会继续努力，保卫祖国的海疆安全。",
            speaker="李明",
            scene_description="司令坚定表态"
        )
    ]


async def demonstrate_basic_coordination():
    """演示基础协调功能"""
    print("\\n" + "="*60)
    print("演示1: 基础翻译协调功能")
    print("="*60)
    
    # 创建翻译协调 Agent
    coordinator = TranslationCoordinatorAgent("demo_coordinator")
    
    try:
        # 创建演示字幕
        subtitles = await create_demo_subtitles()
        print(f"创建了 {len(subtitles)} 条演示字幕")
        
        # 创建协调请求
        request = CoordinationRequest(
            request_id="demo_basic_001",
            project_id="love_navy_blue_demo",
            subtitle_entries=subtitles,
            target_languages=["en", "ja", "ko"],
            quality_threshold=0.8,
            priority=TaskPriority.HIGH
        )
        
        print(f"\\n创建协调请求:")
        print(f"  请求ID: {request.request_id}")
        print(f"  项目ID: {request.project_id}")
        print(f"  目标语言: {', '.join(request.target_languages)}")
        print(f"  质量阈值: {request.quality_threshold}")
        print(f"  优先级: {request.priority.value}")
        
        # 获取初始状态
        initial_status = await coordinator.get_coordination_status()
        print(f"\\n初始状态:")
        print(f"  当前状态: {initial_status['current_status']}")
        print(f"  活跃请求数: {initial_status['active_requests_count']}")
        
        # 执行协调（注意：这里会因为缺少实际的翻译 Agent 而失败，但可以看到流程）
        print(f"\\n开始执行翻译协调...")
        try:
            result = await coordinator.coordinate_translation(request)
            
            print(f"\\n协调结果:")
            print(f"  成功: {result.success}")
            print(f"  处理时间: {result.total_processing_time_ms}ms")
            print(f"  完成任务数: {result.tasks_completed}")
            print(f"  失败任务数: {result.tasks_failed}")
            
            if result.quality_scores:
                print(f"  质量分数:")
                for lang, score in result.quality_scores.items():
                    print(f"    {lang}: {score:.2f}")
            
            if result.recommendations:
                print(f"  建议:")
                for i, rec in enumerate(result.recommendations, 1):
                    print(f"    {i}. {rec}")
                    
        except Exception as e:
            print(f"协调执行失败（预期的，因为缺少实际翻译服务）: {str(e)}")
        
        # 获取最终状态
        final_status = await coordinator.get_coordination_status()
        print(f"\\n最终状态:")
        print(f"  当前状态: {final_status['current_status']}")
        print(f"  已完成请求数: {final_status['completed_requests_count']}")
        
    finally:
        await coordinator.shutdown()


async def demonstrate_configuration_management():
    """演示配置管理功能"""
    print("\\n" + "="*60)
    print("演示2: 配置管理功能")
    print("="*60)
    
    coordinator = TranslationCoordinatorAgent("demo_config")
    
    try:
        # 获取当前配置
        status = await coordinator.get_coordination_status()
        print("当前配置:")
        print(f"  最大并发任务数: {coordinator.max_concurrent_tasks}")
        print(f"  默认质量阈值: {coordinator.default_quality_threshold}")
        print(f"  一致性检查启用: {coordinator.consistency_check_enabled}")
        print(f"  自动重试失败任务: {coordinator.auto_retry_failed_tasks}")
        print(f"  最大重试次数: {coordinator.max_retry_attempts}")
        
        # 更新配置
        config_updates = {
            "max_concurrent_tasks": 8,
            "default_quality_threshold": 0.85,
            "consistency_check_enabled": False,
            "auto_retry_failed_tasks": True,
            "max_retry_attempts": 5
        }
        
        print(f"\\n更新配置...")
        update_result = await coordinator.update_configuration(config_updates)
        
        if update_result["success"]:
            print("配置更新成功!")
            print(f"更新的字段: {', '.join(update_result['updated_fields'])}")
            
            print(f"\\n新配置:")
            new_config = update_result["current_config"]
            for key, value in new_config.items():
                print(f"  {key}: {value}")
        else:
            print(f"配置更新失败: {update_result['error']}")
    
    finally:
        await coordinator.shutdown()


async def demonstrate_monitoring_features():
    """演示监控功能"""
    print("\\n" + "="*60)
    print("演示3: 监控和报告功能")
    print("="*60)
    
    coordinator = TranslationCoordinatorAgent("demo_monitor")
    
    try:
        # 获取翻译 Agent 状态
        agents_status = await coordinator.get_translation_agents_status()
        print("翻译 Agent 状态:")
        print(f"  总 Agent 数: {agents_status['total_agents']}")
        
        for agent_type, status in agents_status["agents"].items():
            print(f"  {agent_type}:")
            print(f"    状态: {status['status']}")
            print(f"    Agent ID: {status.get('agent_id', 'unknown')}")
            if 'supported_languages' in status:
                print(f"    支持语言: {', '.join(status['supported_languages'])}")
        
        # 获取性能报告
        print(f"\\n获取性能报告...")
        performance_report = await coordinator.get_performance_report(24)
        
        print("系统状态:")
        system_status = performance_report.get("system_status", {})
        print(f"  系统运行: {system_status.get('is_running', False)}")
        print(f"  运行时间: {system_status.get('uptime_seconds', 0):.1f} 秒")
        print(f"  活跃任务: {system_status.get('active_tasks', 0)}")
        print(f"  活跃告警: {system_status.get('active_alerts', 0)}")
        print(f"  性能分数: {system_status.get('performance_score', 0):.1f}")
        
        print("\\n协调器统计:")
        coord_stats = performance_report.get("coordination_stats", {})
        print(f"  总请求数: {coord_stats.get('total_requests', 0)}")
        print(f"  成功请求数: {coord_stats.get('successful_requests', 0)}")
        print(f"  失败请求数: {coord_stats.get('failed_requests', 0)}")
        print(f"  平均处理时间: {coord_stats.get('average_processing_time', 0):.1f}ms")
        print(f"  平均质量分数: {coord_stats.get('average_quality_score', 0):.2f}")
        print(f"  已处理语言: {len(coord_stats.get('languages_processed', set()))}")
        print(f"  总翻译字幕数: {coord_stats.get('total_subtitles_translated', 0)}")
        
    finally:
        await coordinator.shutdown()


async def demonstrate_error_handling():
    """演示错误处理功能"""
    print("\\n" + "="*60)
    print("演示4: 错误处理和恢复功能")
    print("="*60)
    
    coordinator = TranslationCoordinatorAgent("demo_error")
    
    try:
        # 创建一个会导致错误的请求（空字幕列表）
        error_request = CoordinationRequest(
            request_id="demo_error_001",
            project_id="error_test",
            subtitle_entries=[],  # 空列表会导致错误
            target_languages=["en"],
            quality_threshold=0.8
        )
        
        print("创建错误测试请求（空字幕列表）...")
        
        try:
            result = await coordinator.coordinate_translation(error_request)
            print(f"请求处理结果: {result.success}")
            if not result.success:
                print(f"错误信息: {result.error_message}")
        except Exception as e:
            print(f"捕获到异常: {str(e)}")
        
        # 测试请求取消功能
        print(f"\\n测试请求取消功能...")
        
        # 创建一个正常请求
        normal_request = CoordinationRequest(
            request_id="demo_cancel_001",
            project_id="cancel_test",
            subtitle_entries=await create_demo_subtitles(),
            target_languages=["en"],
            quality_threshold=0.8
        )
        
        # 模拟添加到活跃请求（通常由 coordinate_translation 完成）
        coordinator.active_requests[normal_request.request_id] = normal_request
        
        # 取消请求
        cancel_result = await coordinator.cancel_request(normal_request.request_id)
        print(f"取消结果: {cancel_result['success']}")
        if cancel_result['success']:
            print(f"取消消息: {cancel_result['message']}")
        
        # 尝试取消不存在的请求
        invalid_cancel = await coordinator.cancel_request("non_existent_request")
        print(f"\\n取消不存在请求的结果: {invalid_cancel['success']}")
        print(f"错误信息: {invalid_cancel['error']}")
        
    finally:
        await coordinator.shutdown()


async def demonstrate_quality_analysis():
    """演示质量分析功能"""
    print("\\n" + "="*60)
    print("演示5: 质量分析功能")
    print("="*60)
    
    coordinator = TranslationCoordinatorAgent("demo_quality")
    
    try:
        # 测试内容分析
        subtitles = await create_demo_subtitles()
        analysis = coordinator._analyze_subtitle_content(subtitles)
        
        print("字幕内容分析:")
        print(f"  总条目数: {analysis['total_entries']}")
        print(f"  总字符数: {analysis['total_characters']}")
        print(f"  总时长: {analysis['total_duration']:.1f}秒")
        print(f"  平均条目长度: {analysis['average_entry_length']:.1f}字符")
        print(f"  内容类型: {', '.join(analysis['content_types'])}")
        print(f"  说话人数量: {analysis['speakers_count']}")
        print(f"  复杂度分数: {analysis['complexity_score']:.2f}")
        
        # 测试翻译策略确定
        target_languages = ["en", "ja", "ko", "es", "ar"]
        strategy = coordinator._determine_translation_strategy(target_languages, analysis)
        
        print(f"\\n翻译策略:")
        print(f"  并行处理: {strategy['parallel_processing']}")
        print(f"  质量优先: {strategy['quality_priority']}")
        print(f"  速度优先: {strategy['speed_priority']}")
        print(f"  需要文化适配: {strategy['cultural_adaptation_required']}")
        print(f"  需要技术准确性: {strategy['technical_accuracy_required']}")
        print(f"  批处理大小: {strategy['batch_size']}")
        
        print(f"\\n Agent 分配:")
        for lang, agent in strategy['agent_assignment'].items():
            print(f"  {lang}: {agent}")
        
        # 测试任务分组
        task_groups = coordinator._create_task_groups(subtitles, target_languages, strategy)
        print(f"\\n任务分组:")
        print(f"  总任务组数: {len(task_groups)}")
        
        # 显示前几个任务组的详情
        for i, group in enumerate(task_groups[:3]):
            print(f"  任务组 {i+1}:")
            print(f"    ID: {group['group_id']}")
            print(f"    目标语言: {group['target_language']}")
            print(f"    Agent 类型: {group['agent_type']}")
            print(f"    字幕数量: {len(group['subtitle_entries'])}")
            print(f"    优先级: {group['priority'].value}")
        
        if len(task_groups) > 3:
            print(f"  ... 还有 {len(task_groups) - 3} 个任务组")
        
        # 测试资源需求估算
        requirements = coordinator._estimate_resource_requirements(task_groups)
        print(f"\\n资源需求估算:")
        print(f"  总任务数: {requirements['total_tasks']}")
        print(f"  总条目数: {requirements['total_entries']}")
        print(f"  总语言数: {requirements['total_languages']}")
        print(f"  预估时间: {requirements['estimated_time_seconds']:.1f}秒")
        print(f"  预估内存: {requirements['estimated_memory_mb']:.2f}MB")
        print(f"  建议并发数: {requirements['concurrent_tasks_recommended']}")
        
    finally:
        await coordinator.shutdown()


async def main():
    """主演示函数"""
    print("字幕翻译系统 - 翻译协调 Agent 演示")
    print("="*60)
    print("本演示将展示翻译协调 Agent 的各种功能")
    print("注意：由于缺少实际的翻译服务，某些功能会显示模拟结果")
    
    try:
        # 运行各个演示
        await demonstrate_basic_coordination()
        await demonstrate_configuration_management()
        await demonstrate_monitoring_features()
        await demonstrate_error_handling()
        await demonstrate_quality_analysis()
        
        print("\\n" + "="*60)
        print("演示完成!")
        print("="*60)
        print("\\n翻译协调 Agent 主要功能:")
        print("✅ 多语言翻译任务协调")
        print("✅ 智能任务分组和调度")
        print("✅ 质量检查和一致性验证")
        print("✅ 实时监控和性能统计")
        print("✅ 错误处理和自动重试")
        print("✅ 配置管理和状态查询")
        print("✅ 资源需求估算和优化")
        
    except KeyboardInterrupt:
        print("\\n用户中断演示")
    except Exception as e:
        print(f"\\n演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())