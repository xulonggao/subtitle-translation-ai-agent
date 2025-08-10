#!/usr/bin/env python3
"""
进度监控系统演示脚本
展示如何使用进度跟踪、性能监控、告警管理和错误跟踪功能
"""
import time
import json
import random
from datetime import datetime
from agents.progress_monitor import (
    MonitoringSystem, ProgressStatus, MetricType, AlertLevel, MonitoringEvent,
    PerformanceMetric, ResourceUsage
)


def simulate_translation_task(monitoring_system: MonitoringSystem, project_id: str, task_id: str, total_items: int):
    """模拟翻译任务执行"""
    print(f"\\n开始模拟翻译任务: {task_id}")
    
    # 开始跟踪任务进度
    monitoring_system.progress_tracker.start_tracking(
        project_id=project_id,
        task_id=task_id,
        total_items=total_items,
        current_stage="初始化"
    )
    
    completed = 0
    failed = 0
    stages = ["解析字幕", "翻译处理", "质量检查", "格式化输出"]
    
    for stage_idx, stage in enumerate(stages):
        print(f"  阶段 {stage_idx + 1}: {stage}")
        
        # 更新当前阶段
        monitoring_system.progress_tracker.update_progress(
            task_id=task_id,
            current_stage=stage,
            stage_progress=0.0
        )
        
        # 模拟阶段内的处理
        stage_items = total_items // len(stages)
        for i in range(stage_items):
            # 模拟处理时间
            time.sleep(0.01)
            
            # 随机模拟成功/失败
            if random.random() < 0.95:  # 95%成功率
                completed += 1
            else:
                failed += 1
                # 记录错误
                monitoring_system.error_tracker.record_error(
                    error_type="TranslationError",
                    error_message=f"翻译失败: 项目{i}",
                    task_id=task_id,
                    context={"stage": stage, "item_index": i}
                )
            
            # 更新进度
            stage_progress = ((i + 1) / stage_items) * 100
            monitoring_system.progress_tracker.update_progress(
                task_id=task_id,
                completed_items=completed,
                failed_items=failed,
                stage_progress=stage_progress,
                quality_score=random.uniform(0.8, 1.0)
            )
            
            # 记录性能指标
            if i % 10 == 0:
                # 翻译速度指标
                translation_speed = PerformanceMetric(
                    metric_name="translation_speed",
                    metric_type=MetricType.RATE,
                    value=random.uniform(5.0, 15.0),
                    unit="items/second",
                    tags={"task_id": task_id, "stage": stage}
                )
                monitoring_system.performance_monitor.record_metric(translation_speed)
                
                # 响应时间指标
                response_time = PerformanceMetric(
                    metric_name="response_time",
                    metric_type=MetricType.TIMER,
                    value=random.uniform(0.1, 2.0),
                    unit="seconds",
                    tags={"task_id": task_id}
                )
                monitoring_system.performance_monitor.record_metric(response_time)
    
    # 完成任务
    success = failed < (total_items * 0.1)  # 如果失败率低于10%则认为成功
    monitoring_system.progress_tracker.complete_task(task_id, success=success)
    
    if success:
        print(f"  任务完成: {completed}成功, {failed}失败")
    else:
        print(f"  任务失败: 失败率过高 ({failed}/{total_items})")
        # 创建任务失败告警
        monitoring_system.alert_manager.create_alert(
            level=AlertLevel.ERROR,
            title=f"任务失败: {task_id}",
            message=f"任务 {task_id} 失败率过高: {failed}/{total_items}",
            source="translation_engine",
            event_type=MonitoringEvent.TASK_FAILED,
            metadata={"task_id": task_id, "failed_count": failed, "total_count": total_items}
        )


def simulate_resource_monitoring(monitoring_system: MonitoringSystem):
    """模拟资源监控"""
    print("\\n模拟资源使用情况...")
    
    for i in range(10):
        # CPU使用率
        cpu_usage = ResourceUsage(
            resource_type="cpu",
            current_usage=random.uniform(20.0, 90.0),
            max_capacity=100.0,
            usage_percentage=random.uniform(20.0, 90.0)
        )
        monitoring_system.performance_monitor.record_resource_usage(cpu_usage)
        
        # 内存使用率
        memory_usage = ResourceUsage(
            resource_type="memory",
            current_usage=random.uniform(1000.0, 8000.0),
            max_capacity=16000.0,
            usage_percentage=random.uniform(10.0, 80.0)
        )
        monitoring_system.performance_monitor.record_resource_usage(memory_usage)
        
        # 如果资源使用率过高，创建告警
        if cpu_usage.usage_percentage > 85:
            monitoring_system.alert_manager.create_alert(
                level=AlertLevel.WARNING,
                title="CPU使用率过高",
                message=f"CPU使用率达到 {cpu_usage.usage_percentage:.1f}%",
                source="resource_monitor",
                event_type=MonitoringEvent.RESOURCE_THRESHOLD_EXCEEDED,
                metadata={"resource_type": "cpu", "usage": cpu_usage.usage_percentage}
            )
        
        time.sleep(0.1)


def demonstrate_alert_handling(monitoring_system: MonitoringSystem):
    """演示告警处理"""
    print("\\n演示告警处理...")
    
    # 创建不同级别的告警
    alerts = [
        (AlertLevel.INFO, "系统启动", "翻译系统已成功启动", MonitoringEvent.TASK_STARTED),
        (AlertLevel.WARNING, "性能下降", "翻译速度低于预期", MonitoringEvent.PERFORMANCE_DEGRADED),
        (AlertLevel.ERROR, "连接失败", "无法连接到翻译服务", MonitoringEvent.ERROR_OCCURRED),
        (AlertLevel.CRITICAL, "系统过载", "系统资源严重不足", MonitoringEvent.RESOURCE_THRESHOLD_EXCEEDED)
    ]
    
    created_alerts = []
    for level, title, message, event_type in alerts:
        alert = monitoring_system.alert_manager.create_alert(
            level=level,
            title=title,
            message=message,
            source="demo_system",
            event_type=event_type
        )
        created_alerts.append(alert)
        print(f"  创建告警: [{level.value.upper()}] {title}")
    
    # 确认一些告警
    for alert in created_alerts[:2]:
        monitoring_system.alert_manager.acknowledge_alert(alert.alert_id, "demo_user")
        print(f"  确认告警: {alert.title}")
    
    # 解决一些告警
    for alert in created_alerts[:1]:
        monitoring_system.alert_manager.resolve_alert(alert.alert_id, "demo_user")
        print(f"  解决告警: {alert.title}")


def demonstrate_error_tracking(monitoring_system: MonitoringSystem):
    """演示错误跟踪"""
    print("\\n演示错误跟踪...")
    
    # 模拟各种错误
    error_scenarios = [
        ("ConnectionError", "网络连接超时", "连接翻译API时超时"),
        ("ValidationError", "输入数据格式错误", "字幕文件格式不正确"),
        ("TranslationError", "翻译服务异常", "翻译引擎返回错误"),
        ("FileNotFoundError", "文件未找到", "指定的字幕文件不存在"),
        ("MemoryError", "内存不足", "处理大文件时内存溢出")
    ]
    
    for i, (error_type, error_message, description) in enumerate(error_scenarios):
        # 模拟同一错误发生多次
        for j in range(random.randint(1, 5)):
            monitoring_system.error_tracker.record_error(
                error_type=error_type,
                error_message=error_message,
                context={
                    "description": description,
                    "occurrence": j + 1,
                    "task_id": f"task_{i}",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        print(f"  记录错误: {error_type} - {error_message}")


def print_monitoring_summary(monitoring_system: MonitoringSystem):
    """打印监控摘要"""
    print("\\n" + "="*60)
    print("监控系统摘要报告")
    print("="*60)
    
    # 系统状态
    status = monitoring_system.get_system_status()
    print(f"\\n系统状态:")
    print(f"  系统ID: {status['system_id']}")
    print(f"  运行状态: {'运行中' if status['is_running'] else '已停止'}")
    print(f"  运行时间: {status['uptime_seconds']:.1f} 秒")
    print(f"  活跃任务: {status['active_tasks']} 个")
    print(f"  活跃告警: {status['active_alerts']} 个")
    print(f"  性能分数: {status['performance_score']:.1f}")
    print(f"  错误率: {status['error_rate']:.2f} 错误/分钟")
    
    # 进度摘要
    progress_summary = monitoring_system._get_progress_summary()
    print(f"\\n进度摘要:")
    print(f"  活跃任务数: {progress_summary['active_tasks_count']}")
    print(f"  平均进度: {progress_summary['average_progress']:.1f}%")
    print(f"  总处理速率: {progress_summary['total_processing_rate']:.2f} 项/秒")
    
    # 告警摘要
    alert_summary = monitoring_system._get_alert_summary()
    print(f"\\n告警摘要:")
    print(f"  活跃告警数: {alert_summary['active_alerts_count']}")
    print(f"  未确认告警: {alert_summary['unacknowledged_count']}")
    if alert_summary['alerts_by_level']:
        print("  按级别分布:")
        for level, count in alert_summary['alerts_by_level'].items():
            print(f"    {level.upper()}: {count}")
    
    # 错误摘要
    error_summary = monitoring_system.error_tracker.get_error_summary(60)
    print(f"\\n错误摘要 (最近60分钟):")
    print(f"  总错误数: {error_summary['total_errors']}")
    print(f"  唯一错误类型: {error_summary['unique_errors']}")
    print(f"  错误率: {error_summary['error_rate']:.2f} 错误/分钟")
    
    if error_summary['top_errors']:
        print("  主要错误:")
        for error in error_summary['top_errors'][:3]:
            print(f"    {error['error_type']}: {error['count']} 次")
    
    # 性能摘要
    perf_summary = monitoring_system.performance_monitor.calculate_performance_summary(60)
    print(f"\\n性能摘要 (最近60分钟):")
    print(f"  性能分数: {perf_summary['performance_score']:.1f}")
    
    if perf_summary['metrics_summary']:
        print("  关键指标:")
        for metric_name, metric_info in perf_summary['metrics_summary'].items():
            print(f"    {metric_name}: 平均 {metric_info['average']:.2f}, 最大 {metric_info['max']:.2f}")
    
    if perf_summary['resource_summary']:
        print("  资源使用:")
        for resource_type, resource_info in perf_summary['resource_summary'].items():
            print(f"    {resource_type}: 平均 {resource_info['average_usage']:.1f}%, 峰值 {resource_info['peak_usage']:.1f}%")


def main():
    """主演示函数"""
    print("字幕翻译系统 - 进度监控演示")
    print("="*60)
    
    # 创建监控系统
    monitoring_system = MonitoringSystem("subtitle_translation_demo")
    
    try:
        # 启动监控系统
        print("启动监控系统...")
        monitoring_system.start()
        time.sleep(1)  # 等待系统启动
        
        # 演示各种功能
        simulate_translation_task(monitoring_system, "project_1", "task_1", 100)
        simulate_translation_task(monitoring_system, "project_1", "task_2", 50)
        simulate_resource_monitoring(monitoring_system)
        demonstrate_alert_handling(monitoring_system)
        demonstrate_error_tracking(monitoring_system)
        
        # 等待一些数据收集
        print("\\n等待数据收集...")
        time.sleep(2)
        
        # 打印摘要报告
        print_monitoring_summary(monitoring_system)
        
        # 生成综合报告
        print("\\n生成综合报告...")
        report = monitoring_system.create_comprehensive_report(1)
        
        # 保存报告到文件
        report_file = f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"报告已保存到: {report_file}")
        
        # 生成仪表板数据
        print("\\n生成仪表板数据...")
        dashboard_data = monitoring_system.create_dashboard_data()
        dashboard_file = f"dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"仪表板数据已保存到: {dashboard_file}")
        
    except KeyboardInterrupt:
        print("\\n用户中断演示")
    except Exception as e:
        print(f"\\n演示过程中发生错误: {e}")
        monitoring_system.error_tracker.record_error(
            error_type=type(e).__name__,
            error_message=str(e),
            context={"source": "demo_script"}
        )
    finally:
        # 停止监控系统
        print("\\n停止监控系统...")
        monitoring_system.stop()
        print("演示完成!")


if __name__ == "__main__":
    main()