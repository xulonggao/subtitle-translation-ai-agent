"""
进度监控系统测试
"""
import unittest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.progress_monitor import (
    ProgressTracker, PerformanceMonitor, AlertManager, ErrorTracker, MonitoringSystem,
    ProgressStatus, MetricType, AlertLevel, MonitoringEvent,
    ProgressSnapshot, PerformanceMetric, ResourceUsage, Alert, ErrorRecord
)


class TestProgressTracker(unittest.TestCase):
    """进度跟踪器测试"""
    
    def setUp(self):
        self.tracker = ProgressTracker("test_tracker")
    
    def test_start_tracking(self):
        """测试开始跟踪"""
        snapshot = self.tracker.start_tracking("project1", "task1", 100, "初始化")
        
        self.assertEqual(snapshot.project_id, "project1")
        self.assertEqual(snapshot.task_id, "task1")
        self.assertEqual(snapshot.total_items, 100)
        self.assertEqual(snapshot.completed_items, 0)
        self.assertEqual(snapshot.status, ProgressStatus.IN_PROGRESS)
        self.assertEqual(snapshot.current_stage, "初始化")
    
    def test_update_progress(self):
        """测试更新进度"""
        # 开始跟踪
        self.tracker.start_tracking("project1", "task1", 100)
        
        # 更新进度
        snapshot = self.tracker.update_progress("task1", completed_items=25, current_stage="处理中")
        
        self.assertEqual(snapshot.completed_items, 25)
        self.assertEqual(snapshot.progress_percentage, 25.0)
        self.assertEqual(snapshot.current_stage, "处理中")
    
    def test_complete_task(self):
        """测试完成任务"""
        # 开始跟踪
        self.tracker.start_tracking("project1", "task1", 100)
        
        # 完成任务
        snapshot = self.tracker.complete_task("task1", success=True)
        
        self.assertEqual(snapshot.status, ProgressStatus.COMPLETED)
        self.assertEqual(snapshot.progress_percentage, 100.0)
    
    def test_processing_rate_calculation(self):
        """测试处理速率计算"""
        # 开始跟踪
        self.tracker.start_tracking("project1", "task1", 100)
        
        # 模拟进度更新
        time.sleep(0.1)
        self.tracker.update_progress("task1", completed_items=10)
        time.sleep(0.1)
        self.tracker.update_progress("task1", completed_items=20)
        
        current = self.tracker.get_current_progress("task1")
        self.assertGreater(current.processing_rate, 0)
    
    def test_get_all_active_tasks(self):
        """测试获取所有活跃任务"""
        # 开始多个任务
        self.tracker.start_tracking("project1", "task1", 100)
        self.tracker.start_tracking("project1", "task2", 50)
        
        active_tasks = self.tracker.get_all_active_tasks()
        self.assertEqual(len(active_tasks), 2)
        
        # 完成一个任务
        self.tracker.complete_task("task1")
        active_tasks = self.tracker.get_all_active_tasks()
        self.assertEqual(len(active_tasks), 1)


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控器测试"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor("test_monitor")
    
    def test_record_metric(self):
        """测试记录指标"""
        metric = PerformanceMetric(
            metric_name="response_time",
            metric_type=MetricType.TIMER,
            value=0.5,
            unit="seconds"
        )
        
        self.monitor.record_metric(metric)
        
        metrics = self.monitor.get_current_metrics("response_time")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].value, 0.5)
    
    def test_record_resource_usage(self):
        """测试记录资源使用"""
        usage = ResourceUsage(
            resource_type="cpu",
            current_usage=50.0,
            max_capacity=100.0,
            usage_percentage=50.0
        )
        
        self.monitor.record_resource_usage(usage)
        
        usage_history = self.monitor.get_resource_usage_history("cpu")
        self.assertEqual(len(usage_history), 1)
        self.assertEqual(usage_history[0].usage_percentage, 50.0)
    
    def test_performance_summary(self):
        """测试性能摘要"""
        # 记录一些指标
        for i in range(5):
            metric = PerformanceMetric(
                metric_name="test_metric",
                metric_type=MetricType.GAUGE,
                value=float(i * 10),
                unit="count"
            )
            self.monitor.record_metric(metric)
        
        summary = self.monitor.calculate_performance_summary(60)
        
        self.assertIn("metrics_summary", summary)
        self.assertIn("test_metric", summary["metrics_summary"])
        self.assertEqual(summary["metrics_summary"]["test_metric"]["count"], 5)
    
    def test_anomaly_threshold(self):
        """测试异常阈值"""
        self.monitor.set_anomaly_threshold("test_metric", 80.0, 95.0)
        
        # 记录正常指标
        normal_metric = PerformanceMetric(
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=70.0,
            unit="percent"
        )
        self.monitor.record_metric(normal_metric)
        
        # 记录异常指标
        warning_metric = PerformanceMetric(
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=85.0,
            unit="percent"
        )
        self.monitor.record_metric(warning_metric)


class TestAlertManager(unittest.TestCase):
    """告警管理器测试"""
    
    def setUp(self):
        self.alert_manager = AlertManager("test_alert_mgr")
    
    def test_create_alert(self):
        """测试创建告警"""
        alert = self.alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="测试告警",
            message="这是一个测试告警",
            source="test_source",
            event_type=MonitoringEvent.PERFORMANCE_DEGRADED
        )
        
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.title, "测试告警")
        self.assertFalse(alert.acknowledged)
        self.assertFalse(alert.resolved)
    
    def test_acknowledge_alert(self):
        """测试确认告警"""
        alert = self.alert_manager.create_alert(
            level=AlertLevel.ERROR,
            title="错误告警",
            message="测试错误",
            source="test_source",
            event_type=MonitoringEvent.ERROR_OCCURRED
        )
        
        success = self.alert_manager.acknowledge_alert(alert.alert_id, "test_user")
        self.assertTrue(success)
        
        # 验证告警已确认
        active_alerts = self.alert_manager.get_active_alerts()
        acknowledged_alert = next(a for a in active_alerts if a.alert_id == alert.alert_id)
        self.assertTrue(acknowledged_alert.acknowledged)
    
    def test_resolve_alert(self):
        """测试解决告警"""
        alert = self.alert_manager.create_alert(
            level=AlertLevel.CRITICAL,
            title="关键告警",
            message="关键问题",
            source="test_source",
            event_type=MonitoringEvent.RESOURCE_THRESHOLD_EXCEEDED
        )
        
        success = self.alert_manager.resolve_alert(alert.alert_id, "test_user")
        self.assertTrue(success)
        
        # 验证告警已从活跃列表中移除
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 0)
    
    def test_duplicate_alert_detection(self):
        """测试重复告警检测"""
        # 创建第一个告警
        alert1 = self.alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="重复告警测试",
            message="第一次",
            source="test_source",
            event_type=MonitoringEvent.PERFORMANCE_DEGRADED
        )
        
        # 创建相同的告警（应该被忽略）
        alert2 = self.alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="重复告警测试",
            message="第二次",
            source="test_source",
            event_type=MonitoringEvent.PERFORMANCE_DEGRADED
        )
        
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
    
    def test_alert_handler_registration(self):
        """测试告警处理器注册"""
        handler_called = False
        
        def test_handler(alert: Alert):
            nonlocal handler_called
            handler_called = True
        
        self.alert_manager.register_alert_handler(AlertLevel.INFO, test_handler)
        
        # 创建INFO级别告警
        self.alert_manager.create_alert(
            level=AlertLevel.INFO,
            title="信息告警",
            message="测试信息",
            source="test_source",
            event_type=MonitoringEvent.TASK_COMPLETED
        )
        
        self.assertTrue(handler_called)


class TestErrorTracker(unittest.TestCase):
    """错误跟踪器测试"""
    
    def setUp(self):
        self.error_tracker = ErrorTracker("test_error_tracker")
    
    def test_record_error(self):
        """测试记录错误"""
        error_record = self.error_tracker.record_error(
            error_type="ValueError",
            error_message="测试错误消息",
            context={"task_id": "task1"},
            severity=AlertLevel.ERROR
        )
        
        self.assertEqual(error_record.error_type, "ValueError")
        self.assertEqual(error_record.error_message, "测试错误消息")
        self.assertEqual(error_record.count, 1)
    
    def test_duplicate_error_handling(self):
        """测试重复错误处理"""
        # 记录相同错误两次
        error1 = self.error_tracker.record_error(
            error_type="RuntimeError",
            error_message="重复错误测试"
        )
        
        error2 = self.error_tracker.record_error(
            error_type="RuntimeError",
            error_message="重复错误测试"
        )
        
        # 应该是同一个错误记录，计数增加
        self.assertEqual(error1.error_id, error2.error_id)
        self.assertEqual(error2.count, 2)
    
    def test_error_summary(self):
        """测试错误摘要"""
        # 记录不同类型的错误
        self.error_tracker.record_error("TypeError", "类型错误1")
        self.error_tracker.record_error("ValueError", "值错误1")
        self.error_tracker.record_error("TypeError", "类型错误2")
        
        summary = self.error_tracker.get_error_summary(60)
        
        self.assertEqual(summary["total_errors"], 3)
        self.assertEqual(summary["unique_errors"], 2)
        self.assertIn("TypeError", summary["error_types"])
        self.assertIn("ValueError", summary["error_types"])
    
    def test_error_trends(self):
        """测试错误趋势"""
        # 记录一些错误
        for i in range(5):
            self.error_tracker.record_error(f"Error{i}", f"错误消息{i}")
        
        trends = self.error_tracker.get_error_trends(hours=1)
        
        self.assertEqual(trends["total_errors"], 5)
        self.assertIsInstance(trends["trend_data"], list)


class TestMonitoringSystem(unittest.TestCase):
    """监控系统测试"""
    
    def setUp(self):
        self.monitoring_system = MonitoringSystem("test_monitoring")
    
    def tearDown(self):
        if self.monitoring_system.is_running:
            self.monitoring_system.stop()
    
    def test_system_initialization(self):
        """测试系统初始化"""
        self.assertIsNotNone(self.monitoring_system.progress_tracker)
        self.assertIsNotNone(self.monitoring_system.performance_monitor)
        self.assertIsNotNone(self.monitoring_system.alert_manager)
        self.assertIsNotNone(self.monitoring_system.error_tracker)
    
    def test_start_stop_system(self):
        """测试启动停止系统"""
        self.assertFalse(self.monitoring_system.is_running)
        
        self.monitoring_system.start()
        self.assertTrue(self.monitoring_system.is_running)
        self.assertIsNotNone(self.monitoring_system.start_time)
        
        self.monitoring_system.stop()
        self.assertFalse(self.monitoring_system.is_running)
    
    def test_system_status(self):
        """测试系统状态"""
        self.monitoring_system.start()
        
        status = self.monitoring_system.get_system_status()
        
        self.assertIn("system_id", status)
        self.assertIn("is_running", status)
        self.assertIn("uptime_seconds", status)
        self.assertIn("active_tasks", status)
        self.assertIn("active_alerts", status)
        self.assertIn("performance_score", status)
        self.assertIn("error_rate", status)
    
    def test_comprehensive_report(self):
        """测试综合报告"""
        # 添加一些测试数据
        self.monitoring_system.progress_tracker.start_tracking("project1", "task1", 100)
        self.monitoring_system.alert_manager.create_alert(
            AlertLevel.INFO, "测试", "测试消息", "test", MonitoringEvent.TASK_STARTED
        )
        self.monitoring_system.error_tracker.record_error("TestError", "测试错误")
        
        report = self.monitoring_system.create_comprehensive_report(1)
        
        self.assertIn("report_id", report)
        self.assertIn("system_status", report)
        self.assertIn("progress_summary", report)
        self.assertIn("performance_summary", report)
        self.assertIn("alert_summary", report)
        self.assertIn("error_summary", report)
    
    def test_dashboard_data(self):
        """测试仪表板数据"""
        # 添加测试数据
        self.monitoring_system.progress_tracker.start_tracking("project1", "task1", 100)
        
        dashboard_data = self.monitoring_system.create_dashboard_data()
        
        self.assertIn("timestamp", dashboard_data)
        self.assertIn("system_status", dashboard_data)
        self.assertIn("active_tasks", dashboard_data)
        self.assertIn("resource_usage", dashboard_data)
        self.assertIn("recent_alerts", dashboard_data)
        self.assertIn("error_summary", dashboard_data)
    
    @patch('builtins.open', create=True)
    def test_export_monitoring_data(self, mock_open):
        """测试导出监控数据"""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        self.monitoring_system.export_monitoring_data("/tmp/test_report.json", 1)
        
        mock_open.assert_called_once()
        mock_file.write.assert_called()


if __name__ == '__main__':
    unittest.main()