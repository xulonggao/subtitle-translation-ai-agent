"""
进度跟踪和监控系统
实时跟踪翻译进度、性能监控和异常处理
"""
import json
import uuid
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationTask

logger = get_logger("progress_monitor")


class ProgressStatus(Enum):
    """进度状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"         # 计数器
    GAUGE = "gauge"             # 仪表盘
    HISTOGRAM = "histogram"     # 直方图
    TIMER = "timer"             # 计时器
    RATE = "rate"               # 速率


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitoringEvent(Enum):
    """监控事件类型"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKER_REGISTERED = "worker_registered"
    WORKER_DISCONNECTED = "worker_disconnected"
    RESOURCE_THRESHOLD_EXCEEDED = "resource_threshold_exceeded"
    PERFORMANCE_DEGRADED = "performance_degraded"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class ProgressSnapshot:
    """进度快照"""
    project_id: str
    task_id: str
    status: ProgressStatus
    total_items: int
    completed_items: int
    failed_items: int
    progress_percentage: float
    estimated_completion_time: Optional[datetime] = None
    current_stage: str = ""
    stage_progress: float = 0.0
    processing_rate: float = 0.0  # items per second
    error_rate: float = 0.0
    quality_score: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 计算进度百分比
        if self.total_items > 0:
            self.progress_percentage = (self.completed_items / self.total_items) * 100
        else:
            self.progress_percentage = 0.0


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_name: str
    metric_type: MetricType
    value: float
    unit: str
    tags: Dict[str, str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ResourceUsage:
    """资源使用情况"""
    resource_type: str
    current_usage: float
    max_capacity: float
    usage_percentage: float
    trend: str = "stable"  # increasing, decreasing, stable
    threshold_warning: float = 80.0
    threshold_critical: float = 95.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 计算使用百分比
        if self.max_capacity > 0:
            self.usage_percentage = (self.current_usage / self.max_capacity) * 100
        else:
            self.usage_percentage = 0.0


@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    event_type: MonitoringEvent
    metadata: Dict[str, Any] = None
    acknowledged: bool = False
    resolved: bool = False
    created_at: datetime = None
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = None
    task_id: Optional[str] = None
    worker_id: Optional[str] = None
    severity: AlertLevel = AlertLevel.ERROR
    count: int = 1
    first_occurrence: datetime = None
    last_occurrence: datetime = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.first_occurrence is None:
            self.first_occurrence = datetime.now()
        if self.last_occurrence is None:
            self.last_occurrence = datetime.now()


class ProgressTracker:
    """进度跟踪器
    
    主要功能：
    1. 实时跟踪任务进度
    2. 计算完成时间预估
    3. 监控处理速率和质量
    4. 生成进度报告
    """
    
    def __init__(self, tracker_id: str = None):
        self.tracker_id = tracker_id or f"tracker_{uuid.uuid4().hex[:8]}"
        
        # 进度数据存储
        self.progress_snapshots: Dict[str, List[ProgressSnapshot]] = defaultdict(list)
        self.current_progress: Dict[str, ProgressSnapshot] = {}
        
        # 历史数据保留设置
        self.max_snapshots_per_task = 1000
        self.snapshot_retention_days = 7
        
        # 线程安全锁
        self.lock = threading.RLock()
        
        logger.info("进度跟踪器初始化完成", tracker_id=self.tracker_id)
    
    def start_tracking(self, project_id: str, task_id: str, total_items: int, 
                      current_stage: str = "初始化") -> ProgressSnapshot:
        """开始跟踪任务进度"""
        with self.lock:
            snapshot = ProgressSnapshot(
                project_id=project_id,
                task_id=task_id,
                status=ProgressStatus.IN_PROGRESS,
                total_items=total_items,
                completed_items=0,
                failed_items=0,
                progress_percentage=0.0,
                current_stage=current_stage
            )
            
            self.current_progress[task_id] = snapshot
            self._add_snapshot(task_id, snapshot)
            
            logger.info("开始跟踪任务进度", 
                       task_id=task_id, 
                       total_items=total_items,
                       current_stage=current_stage)
            
            return snapshot
    
    def update_progress(self, task_id: str, completed_items: int = None, 
                       failed_items: int = None, current_stage: str = None,
                       stage_progress: float = None, quality_score: float = None) -> Optional[ProgressSnapshot]:
        """更新任务进度"""
        with self.lock:
            if task_id not in self.current_progress:
                logger.warning("任务未找到，无法更新进度", task_id=task_id)
                return None
            
            current = self.current_progress[task_id]
            
            # 更新数据
            if completed_items is not None:
                current.completed_items = completed_items
            if failed_items is not None:
                current.failed_items = failed_items
            if current_stage is not None:
                current.current_stage = current_stage
            if stage_progress is not None:
                current.stage_progress = stage_progress
            if quality_score is not None:
                current.quality_score = quality_score
            
            # 重新计算进度百分比
            if current.total_items > 0:
                current.progress_percentage = (current.completed_items / current.total_items) * 100
            
            # 计算处理速率
            current.processing_rate = self._calculate_processing_rate(task_id)
            
            # 计算错误率
            total_processed = current.completed_items + current.failed_items
            if total_processed > 0:
                current.error_rate = (current.failed_items / total_processed) * 100
            
            # 预估完成时间
            current.estimated_completion_time = self._estimate_completion_time(task_id)
            
            # 更新时间戳
            current.timestamp = datetime.now()
            
            # 添加快照
            self._add_snapshot(task_id, current)
            
            logger.debug("任务进度已更新", 
                        task_id=task_id,
                        progress=f"{current.progress_percentage:.1f}%",
                        stage=current.current_stage)
            
            return current
    
    def complete_task(self, task_id: str, success: bool = True) -> Optional[ProgressSnapshot]:
        """完成任务跟踪"""
        with self.lock:
            if task_id not in self.current_progress:
                logger.warning("任务未找到，无法完成跟踪", task_id=task_id)
                return None
            
            current = self.current_progress[task_id]
            current.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
            current.progress_percentage = 100.0 if success else current.progress_percentage
            current.timestamp = datetime.now()
            
            # 添加最终快照
            self._add_snapshot(task_id, current)
            
            logger.info("任务跟踪已完成", 
                       task_id=task_id,
                       status=current.status.value,
                       final_progress=f"{current.progress_percentage:.1f}%")
            
            return current
    
    def get_current_progress(self, task_id: str) -> Optional[ProgressSnapshot]:
        """获取当前进度"""
        return self.current_progress.get(task_id)
    
    def get_progress_history(self, task_id: str, limit: int = 100) -> List[ProgressSnapshot]:
        """获取进度历史"""
        with self.lock:
            snapshots = self.progress_snapshots.get(task_id, [])
            return snapshots[-limit:] if limit > 0 else snapshots
    
    def get_all_active_tasks(self) -> List[ProgressSnapshot]:
        """获取所有活跃任务的进度"""
        with self.lock:
            return [
                snapshot for snapshot in self.current_progress.values()
                if snapshot.status == ProgressStatus.IN_PROGRESS
            ]
    
    def _add_snapshot(self, task_id: str, snapshot: ProgressSnapshot):
        """添加进度快照"""
        snapshots = self.progress_snapshots[task_id]
        snapshots.append(snapshot)
        
        # 限制快照数量
        if len(snapshots) > self.max_snapshots_per_task:
            snapshots.pop(0)
    
    def _calculate_processing_rate(self, task_id: str) -> float:
        """计算处理速率"""
        snapshots = self.progress_snapshots.get(task_id, [])
        if len(snapshots) < 2:
            return 0.0
        
        # 使用最近的快照计算速率
        recent_snapshots = snapshots[-10:]  # 最近10个快照
        if len(recent_snapshots) < 2:
            return 0.0
        
        first_snapshot = recent_snapshots[0]
        last_snapshot = recent_snapshots[-1]
        
        time_diff = (last_snapshot.timestamp - first_snapshot.timestamp).total_seconds()
        if time_diff <= 0:
            return 0.0
        
        items_diff = last_snapshot.completed_items - first_snapshot.completed_items
        return items_diff / time_diff
    
    def _estimate_completion_time(self, task_id: str) -> Optional[datetime]:
        """预估完成时间"""
        current = self.current_progress.get(task_id)
        if not current or current.processing_rate <= 0:
            return None
        
        remaining_items = current.total_items - current.completed_items
        if remaining_items <= 0:
            return datetime.now()
        
        estimated_seconds = remaining_items / current.processing_rate
        return datetime.now() + timedelta(seconds=estimated_seconds)
    
    def cleanup_old_data(self):
        """清理过期数据"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=self.snapshot_retention_days)
            
            for task_id, snapshots in self.progress_snapshots.items():
                # 保留最近的快照
                filtered_snapshots = [
                    snapshot for snapshot in snapshots
                    if snapshot.timestamp > cutoff_time
                ]
                self.progress_snapshots[task_id] = filtered_snapshots
            
            logger.info("过期进度数据已清理", cutoff_time=cutoff_time.isoformat())


class PerformanceMonitor:
    """性能监控器
    
    主要功能：
    1. 收集和存储性能指标
    2. 监控资源使用情况
    3. 检测性能异常
    4. 生成性能报告
    """
    
    def __init__(self, monitor_id: str = None):
        self.monitor_id = monitor_id or f"monitor_{uuid.uuid4().hex[:8]}"
        
        # 性能指标存储
        self.metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.resource_usage: Dict[str, List[ResourceUsage]] = defaultdict(list)
        
        # 监控配置
        self.metric_retention_hours = 24
        self.max_metrics_per_type = 10000
        self.collection_interval_seconds = 10
        
        # 性能基线
        self.performance_baselines: Dict[str, float] = {}
        self.anomaly_thresholds: Dict[str, Tuple[float, float]] = {}  # (warning, critical)
        
        # 线程安全锁
        self.lock = threading.RLock()
        
        # 监控线程
        self.monitoring_thread = None
        self.is_monitoring = False
        
        logger.info("性能监控器初始化完成", monitor_id=self.monitor_id)
    
    def start_monitoring(self):
        """启动性能监控"""
        with self.lock:
            if self.is_monitoring:
                logger.warning("性能监控已在运行中")
                return
            
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("性能监控已启动", monitor_id=self.monitor_id)
    
    def stop_monitoring(self):
        """停止性能监控"""
        with self.lock:
            if not self.is_monitoring:
                return
            
            self.is_monitoring = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            logger.info("性能监控已停止", monitor_id=self.monitor_id)
    
    def record_metric(self, metric: PerformanceMetric):
        """记录性能指标"""
        with self.lock:
            metrics_list = self.metrics[metric.metric_name]
            metrics_list.append(metric)
            
            # 限制指标数量
            if len(metrics_list) > self.max_metrics_per_type:
                metrics_list.pop(0)
            
            # 检查异常
            self._check_metric_anomaly(metric)
            
            logger.debug("性能指标已记录", 
                        metric_name=metric.metric_name,
                        value=metric.value,
                        unit=metric.unit)
    
    def record_resource_usage(self, usage: ResourceUsage):
        """记录资源使用情况"""
        with self.lock:
            usage_list = self.resource_usage[usage.resource_type]
            usage_list.append(usage)
            
            # 限制数据量
            if len(usage_list) > self.max_metrics_per_type:
                usage_list.pop(0)
            
            # 计算趋势
            usage.trend = self._calculate_usage_trend(usage.resource_type)
            
            # 检查阈值
            self._check_resource_threshold(usage)
            
            logger.debug("资源使用情况已记录", 
                        resource_type=usage.resource_type,
                        usage_percentage=f"{usage.usage_percentage:.1f}%",
                        trend=usage.trend)
    
    def get_current_metrics(self, metric_name: str, limit: int = 100) -> List[PerformanceMetric]:
        """获取当前指标"""
        with self.lock:
            metrics_list = self.metrics.get(metric_name, [])
            return metrics_list[-limit:] if limit > 0 else metrics_list
    
    def get_resource_usage_history(self, resource_type: str, limit: int = 100) -> List[ResourceUsage]:
        """获取资源使用历史"""
        with self.lock:
            usage_list = self.resource_usage.get(resource_type, [])
            return usage_list[-limit:] if limit > 0 else usage_list
    
    def calculate_performance_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """计算性能摘要"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            summary = {
                "time_window_minutes": time_window_minutes,
                "metrics_summary": {},
                "resource_summary": {},
                "performance_score": 0.0,
                "anomalies_detected": 0
            }
            
            # 计算指标摘要
            for metric_name, metrics_list in self.metrics.items():
                recent_metrics = [
                    m for m in metrics_list
                    if m.timestamp > cutoff_time
                ]
                
                if recent_metrics:
                    values = [m.value for m in recent_metrics]
                    summary["metrics_summary"][metric_name] = {
                        "count": len(values),
                        "average": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
                    }
            
            # 计算资源摘要
            for resource_type, usage_list in self.resource_usage.items():
                recent_usage = [
                    u for u in usage_list
                    if u.timestamp > cutoff_time
                ]
                
                if recent_usage:
                    usage_percentages = [u.usage_percentage for u in recent_usage]
                    summary["resource_summary"][resource_type] = {
                        "count": len(usage_percentages),
                        "average_usage": statistics.mean(usage_percentages),
                        "peak_usage": max(usage_percentages),
                        "current_trend": recent_usage[-1].trend if recent_usage else "unknown"
                    }
            
            # 计算整体性能分数
            summary["performance_score"] = self._calculate_performance_score(summary)
            
            return summary
    
    def set_performance_baseline(self, metric_name: str, baseline_value: float):
        """设置性能基线"""
        with self.lock:
            self.performance_baselines[metric_name] = baseline_value
            logger.info("性能基线已设置", metric_name=metric_name, baseline=baseline_value)
    
    def set_anomaly_threshold(self, metric_name: str, warning_threshold: float, critical_threshold: float):
        """设置异常阈值"""
        with self.lock:
            self.anomaly_thresholds[metric_name] = (warning_threshold, critical_threshold)
            logger.info("异常阈值已设置", 
                       metric_name=metric_name,
                       warning=warning_threshold,
                       critical=critical_threshold)
    
    def _monitoring_loop(self):
        """监控主循环"""
        logger.info("性能监控循环已启动")
        
        while self.is_monitoring:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 清理过期数据
                self._cleanup_old_metrics()
                
                # 休眠
                time.sleep(self.collection_interval_seconds)
                
            except Exception as e:
                logger.error("监控循环出错", error=str(e))
                time.sleep(5.0)
        
        logger.info("性能监控循环已结束")
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            import psutil
            
            # CPU使用率
            cpu_usage = ResourceUsage(
                resource_type="cpu",
                current_usage=psutil.cpu_percent(),
                max_capacity=100.0,
                usage_percentage=psutil.cpu_percent()
            )
            self.record_resource_usage(cpu_usage)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = ResourceUsage(
                resource_type="memory",
                current_usage=memory.used / (1024 * 1024),  # MB
                max_capacity=memory.total / (1024 * 1024),  # MB
                usage_percentage=memory.percent
            )
            self.record_resource_usage(memory_usage)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = ResourceUsage(
                resource_type="disk",
                current_usage=disk.used / (1024 * 1024 * 1024),  # GB
                max_capacity=disk.total / (1024 * 1024 * 1024),  # GB
                usage_percentage=(disk.used / disk.total) * 100
            )
            self.record_resource_usage(disk_usage)
            
        except ImportError:
            # psutil不可用时的简化监控
            logger.debug("psutil不可用，跳过系统指标收集")
        except Exception as e:
            logger.error("系统指标收集失败", error=str(e))
    
    def _calculate_usage_trend(self, resource_type: str) -> str:
        """计算资源使用趋势"""
        usage_list = self.resource_usage.get(resource_type, [])
        if len(usage_list) < 3:
            return "stable"
        
        # 使用最近的数据点计算趋势
        recent_usage = usage_list[-5:]
        values = [u.usage_percentage for u in recent_usage]
        
        # 简单的趋势计算
        if len(values) >= 2:
            first_half = statistics.mean(values[:len(values)//2])
            second_half = statistics.mean(values[len(values)//2:])
            
            diff_percentage = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
            
            if diff_percentage > 5:
                return "increasing"
            elif diff_percentage < -5:
                return "decreasing"
            else:
                return "stable"
        
        return "stable"
    
    def _check_metric_anomaly(self, metric: PerformanceMetric):
        """检查指标异常"""
        if metric.metric_name not in self.anomaly_thresholds:
            return
        
        warning_threshold, critical_threshold = self.anomaly_thresholds[metric.metric_name]
        
        if metric.value >= critical_threshold:
            logger.error("检测到关键性能异常", 
                        metric_name=metric.metric_name,
                        value=metric.value,
                        threshold=critical_threshold)
        elif metric.value >= warning_threshold:
            logger.warning("检测到性能警告", 
                          metric_name=metric.metric_name,
                          value=metric.value,
                          threshold=warning_threshold)
    
    def _check_resource_threshold(self, usage: ResourceUsage):
        """检查资源阈值"""
        if usage.usage_percentage >= usage.threshold_critical:
            logger.error("资源使用率达到关键阈值", 
                        resource_type=usage.resource_type,
                        usage_percentage=f"{usage.usage_percentage:.1f}%",
                        threshold=f"{usage.threshold_critical:.1f}%")
        elif usage.usage_percentage >= usage.threshold_warning:
            logger.warning("资源使用率达到警告阈值", 
                          resource_type=usage.resource_type,
                          usage_percentage=f"{usage.usage_percentage:.1f}%",
                          threshold=f"{usage.threshold_warning:.1f}%")
    
    def _calculate_performance_score(self, summary: Dict[str, Any]) -> float:
        """计算性能分数"""
        # 基础分数从100开始
        score = 100.0
        
        # 根据资源使用情况扣分
        for resource_type, resource_info in summary.get("resource_summary", {}).items():
            avg_usage = resource_info.get("average_usage", 0)
            if avg_usage > 90:
                score -= 20
            elif avg_usage > 80:
                score -= 10
            elif avg_usage > 70:
                score -= 5
        
        # 根据性能指标扣分
        for metric_name, metric_info in summary.get("metrics_summary", {}).items():
            if "error" in metric_name.lower():
                avg_value = metric_info.get("average", 0)
                if avg_value > 10:  # 错误率超过10%
                    score -= 30
                elif avg_value > 5:  # 错误率超过5%
                    score -= 15
        
        return max(0.0, min(100.0, score))
    
    def _cleanup_old_metrics(self):
        """清理过期指标"""
        cutoff_time = datetime.now() - timedelta(hours=self.metric_retention_hours)
        
        # 清理性能指标
        for metric_name, metrics_list in self.metrics.items():
            filtered_metrics = [
                m for m in metrics_list
                if m.timestamp > cutoff_time
            ]
            self.metrics[metric_name] = filtered_metrics
        
        # 清理资源使用数据
        for resource_type, usage_list in self.resource_usage.items():
            filtered_usage = [
                u for u in usage_list
                if u.timestamp > cutoff_time
            ]
            self.resource_usage[resource_type] = filtered_usage


class AlertManager:
    """告警管理器
    
    主要功能：
    1. 管理系统告警
    2. 告警去重和聚合
    3. 告警通知和升级
    4. 告警历史记录
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"alert_mgr_{uuid.uuid4().hex[:8]}"
        
        # 告警存储
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # 告警配置
        self.max_history_size = 10000
        self.alert_retention_days = 30
        self.duplicate_alert_window_minutes = 5
        
        # 告警处理器
        self.alert_handlers: Dict[AlertLevel, List[Callable]] = defaultdict(list)
        
        # 线程安全锁
        self.lock = threading.RLock()
        
        logger.info("告警管理器初始化完成", manager_id=self.manager_id)
    
    def create_alert(self, level: AlertLevel, title: str, message: str, 
                    source: str, event_type: MonitoringEvent, 
                    metadata: Dict[str, Any] = None) -> Alert:
        """创建告警"""
        with self.lock:
            alert = Alert(
                alert_id=f"alert_{uuid.uuid4().hex[:8]}",
                level=level,
                title=title,
                message=message,
                source=source,
                event_type=event_type,
                metadata=metadata or {}
            )
            
            # 检查重复告警
            if not self._is_duplicate_alert(alert):
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
                
                # 触发告警处理器
                self._trigger_alert_handlers(alert)
                
                logger.info("新告警已创建", 
                           alert_id=alert.alert_id,
                           level=level.value,
                           title=title)
            else:
                logger.debug("重复告警已忽略", title=title, source=source)
            
            return alert
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """确认告警"""
        with self.lock:
            if alert_id not in self.active_alerts:
                logger.warning("告警未找到", alert_id=alert_id)
                return False
            
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.metadata["acknowledged_by"] = acknowledged_by
            alert.metadata["acknowledged_at"] = datetime.now().isoformat()
            
            logger.info("告警已确认", alert_id=alert_id, acknowledged_by=acknowledged_by)
            return True
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """解决告警"""
        with self.lock:
            if alert_id not in self.active_alerts:
                logger.warning("告警未找到", alert_id=alert_id)
                return False
            
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            alert.metadata["resolved_by"] = resolved_by
            
            # 从活跃告警中移除
            del self.active_alerts[alert_id]
            
            logger.info("告警已解决", alert_id=alert_id, resolved_by=resolved_by)
            return True
    
    def get_active_alerts(self, level: AlertLevel = None) -> List[Alert]:
        """获取活跃告警"""
        with self.lock:
            alerts = list(self.active_alerts.values())
            if level:
                alerts = [alert for alert in alerts if alert.level == level]
            return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_alert_history(self, limit: int = 100, level: AlertLevel = None) -> List[Alert]:
        """获取告警历史"""
        with self.lock:
            history = self.alert_history
            if level:
                history = [alert for alert in history if alert.level == level]
            return history[-limit:] if limit > 0 else history
    
    def register_alert_handler(self, level: AlertLevel, handler: Callable[[Alert], None]):
        """注册告警处理器"""
        with self.lock:
            self.alert_handlers[level].append(handler)
            logger.info("告警处理器已注册", level=level.value)
    
    def _is_duplicate_alert(self, new_alert: Alert) -> bool:
        """检查是否为重复告警"""
        cutoff_time = datetime.now() - timedelta(minutes=self.duplicate_alert_window_minutes)
        
        for alert in self.active_alerts.values():
            if (alert.title == new_alert.title and 
                alert.source == new_alert.source and
                alert.event_type == new_alert.event_type and
                alert.created_at > cutoff_time):
                return True
        
        return False
    
    def _trigger_alert_handlers(self, alert: Alert):
        """触发告警处理器"""
        handlers = self.alert_handlers.get(alert.level, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error("告警处理器执行失败", 
                           handler=str(handler), 
                           error=str(e))
    
    def cleanup_old_alerts(self):
        """清理过期告警"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=self.alert_retention_days)
            
            # 清理历史告警
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.created_at > cutoff_time
            ]
            
            # 限制历史大小
            if len(self.alert_history) > self.max_history_size:
                self.alert_history = self.alert_history[-self.max_history_size:]
            
            logger.info("过期告警已清理", cutoff_time=cutoff_time.isoformat())


class ErrorTracker:
    """错误跟踪器
    
    主要功能：
    1. 收集和分类错误
    2. 错误统计和分析
    3. 错误趋势监控
    4. 错误报告生成
    """
    
    def __init__(self, tracker_id: str = None):
        self.tracker_id = tracker_id or f"error_tracker_{uuid.uuid4().hex[:8]}"
        
        # 错误存储
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_history: List[ErrorRecord] = []
        
        # 错误统计
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 配置
        self.max_history_size = 10000
        self.error_retention_days = 7
        self.rate_calculation_window_minutes = 60
        
        # 线程安全锁
        self.lock = threading.RLock()
        
        logger.info("错误跟踪器初始化完成", tracker_id=self.tracker_id)
    
    def record_error(self, error_type: str, error_message: str, 
                    stack_trace: str = None, context: Dict[str, Any] = None,
                    task_id: str = None, worker_id: str = None,
                    severity: AlertLevel = AlertLevel.ERROR) -> ErrorRecord:
        """记录错误"""
        with self.lock:
            # 生成错误键（用于去重）
            error_key = f"{error_type}:{hash(error_message)}"
            
            if error_key in self.error_records:
                # 更新现有错误记录
                error_record = self.error_records[error_key]
                error_record.count += 1
                error_record.last_occurrence = datetime.now()
                if context:
                    error_record.context.update(context)
            else:
                # 创建新错误记录
                error_record = ErrorRecord(
                    error_id=f"error_{uuid.uuid4().hex[:8]}",
                    error_type=error_type,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    context=context or {},
                    task_id=task_id,
                    worker_id=worker_id,
                    severity=severity
                )
                self.error_records[error_key] = error_record
                self.error_history.append(error_record)
            
            # 更新统计
            self.error_counts[error_type] += 1
            self.error_rates[error_type].append(datetime.now())
            
            logger.error("错误已记录", 
                        error_type=error_type,
                        error_message=error_message,
                        task_id=task_id,
                        count=error_record.count)
            
            return error_record
    
    def get_error_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """获取错误摘要"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            
            # 统计时间窗口内的错误
            recent_errors = [
                error for error in self.error_history
                if error.last_occurrence > cutoff_time
            ]
            
            # 按类型分组
            error_by_type = defaultdict(list)
            for error in recent_errors:
                error_by_type[error.error_type].append(error)
            
            # 生成摘要
            summary = {
                "time_window_minutes": time_window_minutes,
                "total_errors": len(recent_errors),
                "unique_errors": len(error_by_type),
                "error_types": {},
                "top_errors": [],
                "error_rate": self._calculate_error_rate(time_window_minutes)
            }
            
            # 按类型统计
            for error_type, errors in error_by_type.items():
                total_count = sum(error.count for error in errors)
                summary["error_types"][error_type] = {
                    "count": total_count,
                    "unique_instances": len(errors),
                    "severity_distribution": self._get_severity_distribution(errors)
                }
            
            # 获取最频繁的错误
            all_errors_with_count = [
                (error, error.count) for error in recent_errors
            ]
            all_errors_with_count.sort(key=lambda x: x[1], reverse=True)
            
            summary["top_errors"] = [
                {
                    "error_type": error.error_type,
                    "error_message": error.error_message[:100],
                    "count": count,
                    "severity": error.severity.value
                }
                for error, count in all_errors_with_count[:10]
            ]
            
            return summary
    
    def get_error_trends(self, error_type: str = None, hours: int = 24) -> Dict[str, Any]:
        """获取错误趋势"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 按小时分组错误
            hourly_errors = defaultdict(int)
            
            for error in self.error_history:
                if error.last_occurrence > cutoff_time:
                    if error_type is None or error.error_type == error_type:
                        hour_key = error.last_occurrence.strftime("%Y-%m-%d %H:00")
                        hourly_errors[hour_key] += error.count
            
            # 生成趋势数据
            trend_data = []
            current_time = cutoff_time.replace(minute=0, second=0, microsecond=0)
            end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            
            while current_time <= end_time:
                hour_key = current_time.strftime("%Y-%m-%d %H:00")
                error_count = hourly_errors.get(hour_key, 0)
                trend_data.append({
                    "timestamp": hour_key,
                    "error_count": error_count
                })
                current_time += timedelta(hours=1)
            
            return {
                "error_type": error_type or "all",
                "time_range_hours": hours,
                "trend_data": trend_data,
                "total_errors": sum(hourly_errors.values())
            }
    
    def _calculate_error_rate(self, time_window_minutes: int) -> float:
        """计算错误率"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        total_errors = 0
        for error_times in self.error_rates.values():
            recent_errors = [
                timestamp for timestamp in error_times
                if timestamp > cutoff_time
            ]
            total_errors += len(recent_errors)
        
        # 计算每分钟错误率
        return total_errors / time_window_minutes if time_window_minutes > 0 else 0.0
    
    def _get_severity_distribution(self, errors: List[ErrorRecord]) -> Dict[str, int]:
        """获取严重程度分布"""
        distribution = defaultdict(int)
        for error in errors:
            distribution[error.severity.value] += error.count
        return dict(distribution)
    
    def cleanup_old_errors(self):
        """清理过期错误"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=self.error_retention_days)
            
            # 清理历史错误
            self.error_history = [
                error for error in self.error_history
                if error.last_occurrence > cutoff_time
            ]
            
            # 清理错误记录
            expired_keys = []
            for key, error in self.error_records.items():
                if error.last_occurrence < cutoff_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.error_records[key]
            
            # 限制历史大小
            if len(self.error_history) > self.max_history_size:
                self.error_history = self.error_history[-self.max_history_size:]
            
            logger.info("过期错误记录已清理", 
                       cutoff_time=cutoff_time.isoformat(),
                       cleaned_count=len(expired_keys))


class MonitoringSystem:
    """综合监控系统
    
    整合进度跟踪、性能监控、告警管理和错误跟踪
    """
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"monitoring_{uuid.uuid4().hex[:8]}"
        
        # 初始化各个组件
        self.progress_tracker = ProgressTracker(f"{self.system_id}_progress")
        self.performance_monitor = PerformanceMonitor(f"{self.system_id}_perf")
        self.alert_manager = AlertManager(f"{self.system_id}_alert")
        self.error_tracker = ErrorTracker(f"{self.system_id}_error")
        
        # 系统状态
        self.is_running = False
        self.start_time = None
        
        # 定期任务
        self.cleanup_thread = None
        self.cleanup_interval_hours = 6
        
        # 注册默认告警处理器
        self._register_default_alert_handlers()
        
        logger.info("监控系统初始化完成", system_id=self.system_id)
    
    def start(self):
        """启动监控系统"""
        if self.is_running:
            logger.warning("监控系统已在运行中")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # 启动性能监控
        self.performance_monitor.start_monitoring()
        
        # 启动清理任务
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("监控系统已启动", system_id=self.system_id)
    
    def stop(self):
        """停止监控系统"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止性能监控
        self.performance_monitor.stop_monitoring()
        
        # 等待清理线程结束
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        
        logger.info("监控系统已停止", system_id=self.system_id)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        return {
            "system_id": self.system_id,
            "is_running": self.is_running,
            "uptime_seconds": uptime.total_seconds(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "active_tasks": len(self.progress_tracker.get_all_active_tasks()),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "performance_score": self.performance_monitor.calculate_performance_summary().get("performance_score", 0),
            "error_rate": self.error_tracker._calculate_error_rate(60)
        }
    
    def create_comprehensive_report(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """创建综合报告"""
        report = {
            "report_id": f"report_{uuid.uuid4().hex[:8]}",
            "generated_at": datetime.now().isoformat(),
            "time_window_hours": time_window_hours,
            "system_status": self.get_system_status(),
            "progress_summary": self._get_progress_summary(),
            "performance_summary": self.performance_monitor.calculate_performance_summary(time_window_hours * 60),
            "alert_summary": self._get_alert_summary(),
            "error_summary": self.error_tracker.get_error_summary(time_window_hours * 60)
        }
        
        logger.info("综合报告已生成", 
                   report_id=report["report_id"],
                   time_window_hours=time_window_hours)
        
        return report
    
    def create_dashboard_data(self) -> Dict[str, Any]:
        """创建仪表板数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": self.get_system_status(),
            "active_tasks": [
                {
                    "task_id": task.task_id,
                    "project_id": task.project_id,
                    "progress": task.progress_percentage,
                    "stage": task.current_stage,
                    "processing_rate": task.processing_rate,
                    "error_rate": task.error_rate,
                    "estimated_completion": task.estimated_completion_time.isoformat() if task.estimated_completion_time else None
                }
                for task in self.progress_tracker.get_all_active_tasks()
            ],
            "resource_usage": {
                resource_type: [
                    {
                        "timestamp": usage.timestamp.isoformat(),
                        "usage_percentage": usage.usage_percentage,
                        "trend": usage.trend
                    }
                    for usage in self.performance_monitor.get_resource_usage_history(resource_type, 20)
                ]
                for resource_type in ["cpu", "memory", "disk"]
            },
            "recent_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "source": alert.source,
                    "created_at": alert.created_at.isoformat(),
                    "acknowledged": alert.acknowledged
                }
                for alert in self.alert_manager.get_active_alerts()[:10]
            ],
            "error_summary": self.error_tracker.get_error_summary(60)
        }
    
    def export_monitoring_data(self, filepath: str, time_window_hours: int = 24):
        """导出监控数据"""
        try:
            report = self.create_comprehensive_report(time_window_hours)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info("监控数据已导出", filepath=filepath)
            
        except Exception as e:
            logger.error("监控数据导出失败", filepath=filepath, error=str(e))
            raise
    
    def _register_default_alert_handlers(self):
        """注册默认告警处理器"""
        def log_alert(alert: Alert):
            log_level = {
                AlertLevel.INFO: "info",
                AlertLevel.WARNING: "warning", 
                AlertLevel.ERROR: "error",
                AlertLevel.CRITICAL: "error"
            }.get(alert.level, "info")
            
            getattr(logger, log_level)(
                f"告警: {alert.title}",
                alert_id=alert.alert_id,
                source=alert.source,
                event_type=alert.event_type.value,
                message=alert.message
            )
        
        # 为所有级别注册日志处理器
        for level in AlertLevel:
            self.alert_manager.register_alert_handler(level, log_alert)
    
    def _get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        active_tasks = self.progress_tracker.get_all_active_tasks()
        
        if not active_tasks:
            return {
                "active_tasks_count": 0,
                "average_progress": 0.0,
                "total_processing_rate": 0.0
            }
        
        total_progress = sum(task.progress_percentage for task in active_tasks)
        total_rate = sum(task.processing_rate for task in active_tasks)
        
        return {
            "active_tasks_count": len(active_tasks),
            "average_progress": total_progress / len(active_tasks),
            "total_processing_rate": total_rate,
            "tasks_by_stage": self._group_tasks_by_stage(active_tasks)
        }
    
    def _group_tasks_by_stage(self, tasks: List[ProgressSnapshot]) -> Dict[str, int]:
        """按阶段分组任务"""
        stage_counts = defaultdict(int)
        for task in tasks:
            stage_counts[task.current_stage] += 1
        return dict(stage_counts)
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        # 按级别分组
        alerts_by_level = defaultdict(int)
        for alert in active_alerts:
            alerts_by_level[alert.level.value] += 1
        
        return {
            "active_alerts_count": len(active_alerts),
            "alerts_by_level": dict(alerts_by_level),
            "unacknowledged_count": len([a for a in active_alerts if not a.acknowledged])
        }
    
    def _cleanup_loop(self):
        """清理循环"""
        logger.info("监控系统清理循环已启动")
        
        while self.is_running:
            try:
                # 执行清理任务
                self.progress_tracker.cleanup_old_data()
                self.alert_manager.cleanup_old_alerts()
                self.error_tracker.cleanup_old_errors()
                
                # 休眠
                for _ in range(self.cleanup_interval_hours * 3600):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error("清理循环出错", error=str(e))
                time.sleep(60)  # 出错后等待1分钟再继续
        
        logger.info("监控系统清理循环已结束")


# 导出主要类
__all__ = [
    'ProgressStatus', 'MetricType', 'AlertLevel', 'MonitoringEvent',
    'ProgressSnapshot', 'PerformanceMetric', 'ResourceUsage', 'Alert', 'ErrorRecord',
    'ProgressTracker', 'PerformanceMonitor', 'AlertManager', 'ErrorTracker',
    'MonitoringSystem'
]