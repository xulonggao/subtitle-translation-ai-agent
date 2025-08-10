#!/usr/bin/env python3
"""
主控 Agent 演示脚本
展示如何使用主控 Agent 协调整个字幕翻译工作流
"""
import asyncio
import json
from datetime import datetime
from agents.master_agent import (
    MasterAgent, MasterAgentRequest, WorkflowStage, AgentStatus
)


async def demonstrate_basic_workflow():
    """演示基础工作流"""
    print("\n" + "="*60)
    print("演示1: 基础字幕翻译工作流")
    print("="*60)
    
    # 创建主控 Agent
    master_agent = MasterAgent("demo_master")
    
    print(f"\n主控 Agent 初始化完成:")
    print(f"  Agent ID: {master_agent.agent_id}")
    print(f"  可用子 Agent: {len(master_agent.sub_agents)}")
    
    if master_agent.sub_agents:
        print("  子 Agent 列表:")
        for agent_name in master_agent.sub_agents.keys():
            print(f"    - {agent_name}")
    
    # 创建翻译请求
    request = MasterAgentRequest(
        request_id="demo_basic_001",
        project_id="love_navy_blue",
        source_files=["episode_01.srt", "episode_02.srt"],
        target_languages=["en", "ja"],
        story_context_file="story_context.md",
        translation_options={
            "style": "formal",
            "preserve_timing": True,
            "cultural_adaptation": True
        },
        quality_requirements={
            "min_accuracy_score": 0.85,
            "consistency_check": True,
            "terminology_validation": True
        },
        optimization_settings={
            "level": "balanced",
            "auto_fix_timing": True,
            "character_limit_check": True
        }
    )
    
    print(f"\n创建翻译请求:")
    print(f"  请求ID: {request.request_id}")
    print(f"  项目ID: {request.project_id}")
    print(f"  源文件: {len(request.source_files)} 个")
    print(f"  目标语言: {', '.join(request.target_languages)}")
    print(f"  剧情背景文件: {request.story_context_file}")
    
    # 执行工作流
    print(f"\n开始执行翻译工作流...")
    
    result = await master_agent.execute_workflow(request)
    
    # 显示结果
    print(f"\n工作流执行结果:")
    print(f"  成功: {result.success}")
    print(f"  最终阶段: {result.workflow_stage.value}")
    print(f"  处理时间: {result.processing_time_ms}ms")
    print(f"  完成任务: {len(result.completed_tasks)}")
    print(f"  失败任务: {len(result.failed_tasks)}")
    
    if result.error_message:
        print(f"  错误信息: {result.error_message}")
    
    # 显示任务详情
    if result.completed_tasks or result.failed_tasks:
        print(f"\n任务执行详情:")
        
        for task in result.completed_tasks:
            print(f"  ✅ {task.agent_name} ({task.stage.value})")
            if task.output_data:
                for key, value in task.output_data.items():
                    print(f"     {key}: {value}")
        
        for task in result.failed_tasks:
            print(f"  ❌ {task.agent_name} ({task.stage.value})")
            if task.error_message:
                print(f"     错误: {task.error_message}")
    
    # 显示建议
    if result.recommendations:
        print(f"\n系统建议:")
        for i, recommendation in enumerate(result.recommendations, 1):
            print(f"  {i}. {recommendation}")
    
    # 显示元数据
    if result.metadata:
        print(f"\n处理元数据:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")


async def demonstrate_workflow_monitoring():
    """演示工作流监控功能"""
    print("\n" + "="*60)
    print("演示2: 工作流状态监控")
    print("="*60)
    
    master_agent = MasterAgent("demo_monitor")
    
    # 显示初始统计
    stats = master_agent.get_execution_statistics()
    print(f"\n初始执行统计:")
    print(f"  总工作流数: {stats['total_workflows']}")
    print(f"  成功工作流: {stats['successful_workflows']}")
    print(f"  失败工作流: {stats['failed_workflows']}")
    print(f"  平均处理时间: {stats['average_processing_time_ms']}ms")
    
    # 列出活跃工作流
    active_workflows = master_agent.list_active_workflows()
    print(f"\n当前活跃工作流: {len(active_workflows)}")
    
    # 创建并执行多个工作流
    print(f"\n执行多个工作流进行监控演示...")
    
    requests = [
        MasterAgentRequest(
            request_id=f"monitor_test_{i}",
            project_id="test_project",
            source_files=[f"test_{i}.srt"],
            target_languages=["en"]
        )
        for i in range(3)
    ]
    
    results = []
    for request in requests:
        print(f"  执行工作流: {request.request_id}")
        result = await master_agent.execute_workflow(request)
        results.append(result)
        
        # 显示工作流状态
        status = master_agent.get_workflow_status(request.request_id)
        if status:
            print(f"    状态: {status.get('current_stage', 'unknown')}")
    
    # 显示更新后的统计
    updated_stats = master_agent.get_execution_statistics()
    print(f"\n更新后的执行统计:")
    print(f"  总工作流数: {updated_stats['total_workflows']}")
    print(f"  成功工作流: {updated_stats['successful_workflows']}")
    print(f"  失败工作流: {updated_stats['failed_workflows']}")
    print(f"  平均处理时间: {updated_stats['average_processing_time_ms']:.1f}ms")
    
    # 显示 Agent 性能统计
    if updated_stats['agent_performance']:
        print(f"\nAgent 性能统计:")
        for agent_name, perf in updated_stats['agent_performance'].items():
            print(f"  {agent_name}:")
            print(f"    总任务: {perf['total_tasks']}")
            print(f"    成功任务: {perf['successful_tasks']}")
            print(f"    失败任务: {perf['failed_tasks']}")
            print(f"    平均时间: {perf['average_time_ms']:.1f}ms")


async def demonstrate_error_handling():
    """演示错误处理功能"""
    print("\n" + "="*60)
    print("演示3: 错误处理和恢复")
    print("="*60)
    
    master_agent = MasterAgent("demo_error")
    
    # 测试各种错误情况
    error_cases = [
        {
            "name": "空文件列表",
            "request": MasterAgentRequest(
                request_id="error_empty_files",
                project_id="test",
                source_files=[],  # 空文件列表
                target_languages=["en"]
            )
        },
        {
            "name": "无效语言代码",
            "request": MasterAgentRequest(
                request_id="error_invalid_lang",
                project_id="test",
                source_files=["test.srt"],
                target_languages=["invalid_lang"]  # 无效语言
            )
        },
        {
            "name": "不存在的文件",
            "request": MasterAgentRequest(
                request_id="error_missing_file",
                project_id="test",
                source_files=["nonexistent.srt"],
                target_languages=["en"]
            )
        }
    ]
    
    for case in error_cases:
        print(f"\n测试错误情况: {case['name']}")
        
        try:
            result = await master_agent.execute_workflow(case['request'])
            
            print(f"  结果: {'成功' if result.success else '失败'}")
            print(f"  最终阶段: {result.workflow_stage.value}")
            
            if result.error_message:
                print(f"  错误信息: {result.error_message}")
            
            if result.recommendations:
                print(f"  系统建议:")
                for rec in result.recommendations[:2]:  # 只显示前2个建议
                    print(f"    - {rec}")
            
            # 显示失败任务的详情
            if result.failed_tasks:
                print(f"  失败任务详情:")
                for task in result.failed_tasks[:3]:  # 只显示前3个失败任务
                    print(f"    - {task.agent_name}: {task.error_message}")
        
        except Exception as e:
            print(f"  异常: {str(e)}")


async def demonstrate_workflow_cancellation():
    """演示工作流取消功能"""
    print("\n" + "="*60)
    print("演示4: 工作流取消功能")
    print("="*60)
    
    master_agent = MasterAgent("demo_cancel")
    
    # 测试取消不存在的工作流
    print(f"\n测试取消不存在的工作流:")
    cancel_result = await master_agent.cancel_workflow("nonexistent_workflow")
    print(f"  取消结果: {cancel_result}")
    
    # 创建一个工作流请求
    request = MasterAgentRequest(
        request_id="cancellation_test",
        project_id="test",
        source_files=["test.srt"],
        target_languages=["en", "ja", "ko"]  # 多语言，处理时间较长
    )
    
    print(f"\n创建工作流: {request.request_id}")
    
    # 启动工作流（在实际应用中，这会在后台运行）
    # 这里我们模拟快速执行然后尝试取消
    result = await master_agent.execute_workflow(request)
    
    print(f"  工作流执行完成: {result.success}")
    print(f"  最终阶段: {result.workflow_stage.value}")
    
    # 尝试取消已完成的工作流
    cancel_result = await master_agent.cancel_workflow(request.request_id)
    print(f"  尝试取消已完成的工作流: {cancel_result}")


async def demonstrate_complex_workflow():
    """演示复杂工作流"""
    print("\n" + "="*60)
    print("演示5: 复杂多文件多语言工作流")
    print("="*60)
    
    master_agent = MasterAgent("demo_complex")
    
    # 创建复杂的翻译请求
    request = MasterAgentRequest(
        request_id="complex_workflow_001",
        project_id="love_navy_blue_complete",
        source_files=[
            "ep01_intro.srt",
            "ep01_main.srt", 
            "ep01_ending.srt",
            "ep02_intro.srt",
            "ep02_main.srt"
        ],
        target_languages=["en", "ja", "ko", "th", "vi"],
        story_context_file="complete_story_context.md",
        translation_options={
            "style": "natural",
            "preserve_timing": True,
            "cultural_adaptation": True,
            "character_consistency": True,
            "terminology_consistency": True,
            "emotional_tone_preservation": True
        },
        quality_requirements={
            "min_accuracy_score": 0.90,
            "min_fluency_score": 0.85,
            "min_consistency_score": 0.88,
            "cultural_appropriateness_check": True,
            "terminology_validation": True,
            "character_name_consistency": True
        },
        optimization_settings={
            "level": "aggressive",
            "auto_fix_timing": True,
            "character_limit_check": True,
            "reading_speed_optimization": True,
            "subtitle_splitting": True,
            "format_standardization": True
        }
    )
    
    print(f"\n复杂工作流配置:")
    print(f"  源文件数量: {len(request.source_files)}")
    print(f"  目标语言数量: {len(request.target_languages)}")
    print(f"  翻译选项: {len(request.translation_options)} 项")
    print(f"  质量要求: {len(request.quality_requirements)} 项")
    print(f"  优化设置: {len(request.optimization_settings)} 项")
    
    print(f"\n开始执行复杂工作流...")
    start_time = datetime.now()
    
    result = await master_agent.execute_workflow(request)
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print(f"\n复杂工作流执行结果:")
    print(f"  执行成功: {result.success}")
    print(f"  总执行时间: {total_time:.2f} 秒")
    print(f"  系统报告时间: {result.processing_time_ms}ms")
    print(f"  最终阶段: {result.workflow_stage.value}")
    print(f"  总任务数: {len(result.completed_tasks) + len(result.failed_tasks)}")
    print(f"  成功任务: {len(result.completed_tasks)}")
    print(f"  失败任务: {len(result.failed_tasks)}")
    
    # 按阶段统计任务
    stage_stats = {}
    all_tasks = result.completed_tasks + result.failed_tasks
    for task in all_tasks:
        stage = task.stage.value
        if stage not in stage_stats:
            stage_stats[stage] = {"completed": 0, "failed": 0}
        
        if task.status == AgentStatus.COMPLETED:
            stage_stats[stage]["completed"] += 1
        elif task.status == AgentStatus.FAILED:
            stage_stats[stage]["failed"] += 1
    
    if stage_stats:
        print(f"\n各阶段任务统计:")
        for stage, stats in stage_stats.items():
            total = stats["completed"] + stats["failed"]
            success_rate = (stats["completed"] / total * 100) if total > 0 else 0
            print(f"  {stage}: {stats['completed']}/{total} 成功 ({success_rate:.1f}%)")
    
    # 显示质量分数（如果有）
    if result.quality_scores:
        print(f"\n质量评分:")
        for key, score in result.quality_scores.items():
            print(f"  {key}: {score:.2%}")
    
    if result.consistency_scores:
        print(f"\n一致性评分:")
        for key, score in result.consistency_scores.items():
            print(f"  {key}: {score:.2%}")


async def main():
    """主演示函数"""
    print("字幕翻译系统 - 主控 Agent 演示")
    print("="*60)
    print("本演示将展示主控 Agent 的各种功能")
    
    try:
        # 运行各个演示
        await demonstrate_basic_workflow()
        await demonstrate_workflow_monitoring()
        await demonstrate_error_handling()
        await demonstrate_workflow_cancellation()
        await demonstrate_complex_workflow()
        
        print("\n" + "="*60)
        print("演示完成!")
        print("="*60)
        print("\n主控 Agent 主要功能:")
        print("✅ 完整的工作流编排 (文件解析 → 上下文分析 → 翻译 → 质量控制 → 优化)")
        print("✅ 子 Agent 协调和管理 (动态加载和错误处理)")
        print("✅ 工作流状态跟踪 (实时监控和历史记录)")
        print("✅ 错误处理和恢复 (优雅降级和错误报告)")
        print("✅ 性能统计和监控 (执行时间和成功率统计)")
        print("✅ 工作流取消功能 (支持中途取消)")
        print("✅ 复杂场景支持 (多文件多语言批量处理)")
        print("✅ 可配置的处理选项 (翻译、质量、优化参数)")
        
    except KeyboardInterrupt:
        print("\n用户中断演示")
    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())