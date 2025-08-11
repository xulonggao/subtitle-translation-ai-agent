#!/usr/bin/env python3
"""
进度跟踪 Agent
负责翻译任务的进度跟踪、实时状态更新和性能监控
"""
import uuid
import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import os

from config import get_logger

logger = get_logger("progress_tracking_agent")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ProgressEventType(Enum):
    """进度事件类型"""
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    PERFORMANCE_ALERT = "performance_alert"


@dataclass
class ProgressEvent:
    """进度事件"""
    event_id: str
    event_type: ProgressEventType
    timestamp: datetime
    workflow_id: str
    task_id: Optional[str] = None
    stage: Optional[str] = None
    agent_name: Optional[str] = None
    progress_percentage: Optional[float] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    workflow_id: str
    task_name: str
    status: TaskStatus
    progress_percentage: float
    start_time: datetime
    end_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    current_stage: Optional[str] = None
    agent_name: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowProgress:
    """工作流进度信息"""
    workflow_id: str
    project_id: str
    status: TaskStatus
    overall_progress: float
    start_time: datetime
    end_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    current_stage: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    tasks: Dict[str, TaskProgress] = None
    stages_progress: Dict[str, float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tasks is None:
            self.tasks = {}
        if self.stages_progress is None:
            self.stages_progress = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime
    workflow_id: str
    cpu_usage: float
    memory_usage: float
    active_agents: int
    tasks_per_second: float
    average_task_duration: float
    error_rate: float
    queue_size: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProgressTrackingAgent:
    """进度跟踪 Agent
    
    负责：
    1. 翻译任务的进度跟踪
    2. 实时状态更新和通知
    3. 性能监控和资源使用统计
    4. 监控数据的可视化和报告
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"progress_agent_{uuid.uuid4().hex[:8]}"
        
        # 进度跟踪数据
        self.workflows: Dict[str, WorkflowProgress] = {}
        self.tasks: Dict[str, TaskProgress] = {}
        self.events: deque = deque(maxlen=10000)  # 保留最近10000个事件
        
        # 性能监控数据
        self.performance_history: deque = deque(maxlen=1000)  # 保留最近1000个性能记录
        self.performance_alerts: List[Dict[str, Any]] = []
        
        # 通知回调
        self.event_callbacks: List[Callable[[ProgressEvent], None]] = []
        self.status_callbacks: List[Callable[[str, TaskStatus], None]] = []
        
        # 监控配置
        self.monitoring_config = {
            "performance_interval": 5.0,  # 性能监控间隔（秒）
            "alert_thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "error_rate": 10.0,
                "task_duration": 300.0  # 5分钟
            },
            "retention_days": 7  # 数据保留天数
        }\n        \n        # 启动监控线程\n        self.monitoring_active = True\n        self.monitoring_thread = threading.Thread(target=self._performance_monitoring_loop, daemon=True)\n        self.monitoring_thread.start()\n        \n        # 数据持久化\n        self.data_dir = \"monitoring_data\"\n        os.makedirs(self.data_dir, exist_ok=True)\n        \n        logger.info(\"进度跟踪 Agent 初始化完成\", agent_id=self.agent_id)\n    \n    def register_event_callback(self, callback: Callable[[ProgressEvent], None]):\n        \"\"\"注册事件回调\"\"\"\n        self.event_callbacks.append(callback)\n        logger.debug(\"事件回调已注册\", callback_count=len(self.event_callbacks))\n    \n    def register_status_callback(self, callback: Callable[[str, TaskStatus], None]):\n        \"\"\"注册状态变更回调\"\"\"\n        self.status_callbacks.append(callback)\n        logger.debug(\"状态回调已注册\", callback_count=len(self.status_callbacks))\n    \n    def start_workflow_tracking(self, workflow_id: str, project_id: str, \n                               total_tasks: int = 0, metadata: Dict[str, Any] = None) -> WorkflowProgress:\n        \"\"\"开始工作流跟踪\"\"\"\n        workflow_progress = WorkflowProgress(\n            workflow_id=workflow_id,\n            project_id=project_id,\n            status=TaskStatus.RUNNING,\n            overall_progress=0.0,\n            start_time=datetime.now(),\n            total_tasks=total_tasks,\n            metadata=metadata or {}\n        )\n        \n        self.workflows[workflow_id] = workflow_progress\n        \n        # 发送事件\n        event = ProgressEvent(\n            event_id=f\"workflow_start_{uuid.uuid4().hex[:8]}\",\n            event_type=ProgressEventType.WORKFLOW_STARTED,\n            timestamp=datetime.now(),\n            workflow_id=workflow_id,\n            message=f\"工作流 {workflow_id} 开始执行\",\n            metadata={\"project_id\": project_id, \"total_tasks\": total_tasks}\n        )\n        \n        self._emit_event(event)\n        \n        logger.info(\"工作流跟踪已开始\", \n                   workflow_id=workflow_id, \n                   project_id=project_id,\n                   total_tasks=total_tasks)\n        \n        return workflow_progress\n    \n    def start_task_tracking(self, task_id: str, workflow_id: str, task_name: str,\n                           agent_name: str = None, metadata: Dict[str, Any] = None) -> TaskProgress:\n        \"\"\"开始任务跟踪\"\"\"\n        task_progress = TaskProgress(\n            task_id=task_id,\n            workflow_id=workflow_id,\n            task_name=task_name,\n            status=TaskStatus.RUNNING,\n            progress_percentage=0.0,\n            start_time=datetime.now(),\n            agent_name=agent_name,\n            metadata=metadata or {}\n        )\n        \n        self.tasks[task_id] = task_progress\n        \n        # 更新工作流信息\n        if workflow_id in self.workflows:\n            workflow = self.workflows[workflow_id]\n            workflow.tasks[task_id] = task_progress\n            if workflow.total_tasks == 0:\n                workflow.total_tasks = len(workflow.tasks)\n        \n        # 发送事件\n        event = ProgressEvent(\n            event_id=f\"task_start_{uuid.uuid4().hex[:8]}\",\n            event_type=ProgressEventType.TASK_STARTED,\n            timestamp=datetime.now(),\n            workflow_id=workflow_id,\n            task_id=task_id,\n            agent_name=agent_name,\n            message=f\"任务 {task_name} 开始执行\",\n            metadata=metadata or {}\n        )\n        \n        self._emit_event(event)\n        \n        logger.info(\"任务跟踪已开始\", \n                   task_id=task_id, \n                   workflow_id=workflow_id,\n                   task_name=task_name,\n                   agent_name=agent_name)\n        \n        return task_progress\n    \n    def update_task_progress(self, task_id: str, progress_percentage: float,\n                           current_stage: str = None, message: str = None,\n                           metadata: Dict[str, Any] = None):\n        \"\"\"更新任务进度\"\"\"\n        if task_id not in self.tasks:\n            logger.warning(\"尝试更新不存在的任务进度\", task_id=task_id)\n            return\n        \n        task = self.tasks[task_id]\n        task.progress_percentage = min(100.0, max(0.0, progress_percentage))\n        \n        if current_stage:\n            task.current_stage = current_stage\n        \n        if metadata:\n            task.metadata.update(metadata)\n        \n        # 估算完成时间\n        if progress_percentage > 0:\n            elapsed = (datetime.now() - task.start_time).total_seconds()\n            estimated_total = elapsed / (progress_percentage / 100.0)\n            task.estimated_completion = task.start_time + timedelta(seconds=estimated_total)\n        \n        # 更新工作流进度\n        self._update_workflow_progress(task.workflow_id)\n        \n        # 发送事件\n        event = ProgressEvent(\n            event_id=f\"task_progress_{uuid.uuid4().hex[:8]}\",\n            event_type=ProgressEventType.TASK_PROGRESS,\n            timestamp=datetime.now(),\n            workflow_id=task.workflow_id,\n            task_id=task_id,\n            stage=current_stage,\n            agent_name=task.agent_name,\n            progress_percentage=progress_percentage,\n            message=message or f\"任务进度: {progress_percentage:.1f}%\",\n            metadata=metadata or {}\n        )\n        \n        self._emit_event(event)\n        \n        logger.debug(\"任务进度已更新\", \n                    task_id=task_id, \n                    progress=progress_percentage,\n                    stage=current_stage)\n    \n    def complete_task(self, task_id: str, success: bool = True, \n                     error_message: str = None, metadata: Dict[str, Any] = None):\n        \"\"\"完成任务\"\"\"\n        if task_id not in self.tasks:\n            logger.warning(\"尝试完成不存在的任务\", task_id=task_id)\n            return\n        \n        task = self.tasks[task_id]\n        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED\n        task.progress_percentage = 100.0 if success else task.progress_percentage\n        task.end_time = datetime.now()\n        \n        if error_message:\n            task.error_message = error_message\n        \n        if metadata:\n            task.metadata.update(metadata)\n        \n        # 更新工作流进度\n        workflow_id = task.workflow_id\n        if workflow_id in self.workflows:\n            workflow = self.workflows[workflow_id]\n            if success:\n                workflow.completed_tasks += 1\n            else:\n                workflow.failed_tasks += 1\n        \n        self._update_workflow_progress(workflow_id)\n        \n        # 发送事件\n        event_type = ProgressEventType.TASK_COMPLETED if success else ProgressEventType.TASK_FAILED\n        event = ProgressEvent(\n            event_id=f\"task_complete_{uuid.uuid4().hex[:8]}\",\n            event_type=event_type,\n            timestamp=datetime.now(),\n            workflow_id=workflow_id,\n            task_id=task_id,\n            agent_name=task.agent_name,\n            progress_percentage=100.0 if success else task.progress_percentage,\n            message=f\"任务{'完成' if success else '失败'}: {task.task_name}\",\n            metadata=metadata or {}\n        )\n        \n        self._emit_event(event)\n        \n        logger.info(\"任务已完成\", \n                   task_id=task_id, \n                   success=success,\n                   duration=(task.end_time - task.start_time).total_seconds())\n    \n    def complete_workflow(self, workflow_id: str, success: bool = True,\n                         metadata: Dict[str, Any] = None):\n        \"\"\"完成工作流\"\"\"\n        if workflow_id not in self.workflows:\n            logger.warning(\"尝试完成不存在的工作流\", workflow_id=workflow_id)\n            return\n        \n        workflow = self.workflows[workflow_id]\n        workflow.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED\n        workflow.end_time = datetime.now()\n        workflow.overall_progress = 100.0\n        \n        if metadata:\n            workflow.metadata.update(metadata)\n        \n        # 发送事件\n        event = ProgressEvent(\n            event_id=f\"workflow_complete_{uuid.uuid4().hex[:8]}\",\n            event_type=ProgressEventType.WORKFLOW_COMPLETED,\n            timestamp=datetime.now(),\n            workflow_id=workflow_id,\n            progress_percentage=100.0,\n            message=f\"工作流{'完成' if success else '失败'}: {workflow_id}\",\n            metadata={\n                \"total_tasks\": workflow.total_tasks,\n                \"completed_tasks\": workflow.completed_tasks,\n                \"failed_tasks\": workflow.failed_tasks,\n                \"duration\": (workflow.end_time - workflow.start_time).total_seconds()\n            }\n        )\n        \n        self._emit_event(event)\n        \n        logger.info(\"工作流已完成\", \n                   workflow_id=workflow_id, \n                   success=success,\n                   total_tasks=workflow.total_tasks,\n                   completed_tasks=workflow.completed_tasks,\n                   failed_tasks=workflow.failed_tasks)\n    \n    def _update_workflow_progress(self, workflow_id: str):\n        \"\"\"更新工作流整体进度\"\"\"\n        if workflow_id not in self.workflows:\n            return\n        \n        workflow = self.workflows[workflow_id]\n        \n        if not workflow.tasks:\n            return\n        \n        # 计算整体进度\n        total_progress = sum(task.progress_percentage for task in workflow.tasks.values())\n        workflow.overall_progress = total_progress / len(workflow.tasks)\n        \n        # 更新阶段进度\n        stage_progress = defaultdict(list)\n        for task in workflow.tasks.values():\n            if task.current_stage:\n                stage_progress[task.current_stage].append(task.progress_percentage)\n        \n        for stage, progresses in stage_progress.items():\n            workflow.stages_progress[stage] = sum(progresses) / len(progresses)\n        \n        # 估算完成时间\n        if workflow.overall_progress > 0:\n            elapsed = (datetime.now() - workflow.start_time).total_seconds()\n            estimated_total = elapsed / (workflow.overall_progress / 100.0)\n            workflow.estimated_completion = workflow.start_time + timedelta(seconds=estimated_total)\n    \n    def _emit_event(self, event: ProgressEvent):\n        \"\"\"发送事件\"\"\"\n        self.events.append(event)\n        \n        # 调用事件回调\n        for callback in self.event_callbacks:\n            try:\n                callback(event)\n            except Exception as e:\n                logger.error(\"事件回调执行失败\", callback=callback, error=str(e))\n        \n        # 调用状态回调\n        if event.event_type in [ProgressEventType.TASK_STARTED, ProgressEventType.TASK_COMPLETED, ProgressEventType.TASK_FAILED]:\n            task_id = event.task_id\n            if task_id in self.tasks:\n                status = self.tasks[task_id].status\n                for callback in self.status_callbacks:\n                    try:\n                        callback(task_id, status)\n                    except Exception as e:\n                        logger.error(\"状态回调执行失败\", callback=callback, error=str(e))\n    \n    def _performance_monitoring_loop(self):\n        \"\"\"性能监控循环\"\"\"\n        while self.monitoring_active:\n            try:\n                self._collect_performance_metrics()\n                time.sleep(self.monitoring_config[\"performance_interval\"])\n            except Exception as e:\n                logger.error(\"性能监控异常\", error=str(e))\n                time.sleep(5.0)  # 错误时等待5秒\n    \n    def _collect_performance_metrics(self):\n        \"\"\"收集性能指标\"\"\"\n        try:\n            import psutil\n            \n            # 收集系统指标\n            cpu_usage = psutil.cpu_percent()\n            memory = psutil.virtual_memory()\n            memory_usage = memory.percent\n            \n            # 收集应用指标\n            active_workflows = len([w for w in self.workflows.values() if w.status == TaskStatus.RUNNING])\n            active_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])\n            \n            # 计算任务处理速率\n            recent_completions = 0\n            recent_duration = 0\n            now = datetime.now()\n            \n            for task in self.tasks.values():\n                if task.end_time and (now - task.end_time).total_seconds() < 60:  # 最近1分钟\n                    recent_completions += 1\n                    if task.start_time:\n                        recent_duration += (task.end_time - task.start_time).total_seconds()\n            \n            tasks_per_second = recent_completions / 60.0 if recent_completions > 0 else 0.0\n            average_task_duration = recent_duration / recent_completions if recent_completions > 0 else 0.0\n            \n            # 计算错误率\n            recent_failures = len([t for t in self.tasks.values() \n                                 if t.status == TaskStatus.FAILED and t.end_time \n                                 and (now - t.end_time).total_seconds() < 300])  # 最近5分钟\n            recent_total = len([t for t in self.tasks.values() \n                              if t.end_time and (now - t.end_time).total_seconds() < 300])\n            error_rate = (recent_failures / recent_total * 100) if recent_total > 0 else 0.0\n            \n            # 创建性能指标\n            metrics = PerformanceMetrics(\n                timestamp=now,\n                workflow_id=\"system\",\n                cpu_usage=cpu_usage,\n                memory_usage=memory_usage,\n                active_agents=active_workflows,\n                tasks_per_second=tasks_per_second,\n                average_task_duration=average_task_duration,\n                error_rate=error_rate,\n                queue_size=active_tasks,\n                metadata={\n                    \"active_workflows\": active_workflows,\n                    \"active_tasks\": active_tasks,\n                    \"recent_completions\": recent_completions,\n                    \"recent_failures\": recent_failures\n                }\n            )\n            \n            self.performance_history.append(metrics)\n            \n            # 检查告警阈值\n            self._check_performance_alerts(metrics)\n            \n        except ImportError:\n            # psutil 不可用，使用简化指标\n            metrics = PerformanceMetrics(\n                timestamp=datetime.now(),\n                workflow_id=\"system\",\n                cpu_usage=0.0,\n                memory_usage=0.0,\n                active_agents=len([w for w in self.workflows.values() if w.status == TaskStatus.RUNNING]),\n                tasks_per_second=0.0,\n                average_task_duration=0.0,\n                error_rate=0.0,\n                queue_size=len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])\n            )\n            \n            self.performance_history.append(metrics)\n            \n        except Exception as e:\n            logger.error(\"性能指标收集失败\", error=str(e))\n    \n    def _check_performance_alerts(self, metrics: PerformanceMetrics):\n        \"\"\"检查性能告警\"\"\"\n        thresholds = self.monitoring_config[\"alert_thresholds\"]\n        alerts = []\n        \n        if metrics.cpu_usage > thresholds[\"cpu_usage\"]:\n            alerts.append({\n                \"type\": \"cpu_high\",\n                \"message\": f\"CPU使用率过高: {metrics.cpu_usage:.1f}%\",\n                \"value\": metrics.cpu_usage,\n                \"threshold\": thresholds[\"cpu_usage\"]\n            })\n        \n        if metrics.memory_usage > thresholds[\"memory_usage\"]:\n            alerts.append({\n                \"type\": \"memory_high\",\n                \"message\": f\"内存使用率过高: {metrics.memory_usage:.1f}%\",\n                \"value\": metrics.memory_usage,\n                \"threshold\": thresholds[\"memory_usage\"]\n            })\n        \n        if metrics.error_rate > thresholds[\"error_rate\"]:\n            alerts.append({\n                \"type\": \"error_rate_high\",\n                \"message\": f\"错误率过高: {metrics.error_rate:.1f}%\",\n                \"value\": metrics.error_rate,\n                \"threshold\": thresholds[\"error_rate\"]\n            })\n        \n        if metrics.average_task_duration > thresholds[\"task_duration\"]:\n            alerts.append({\n                \"type\": \"task_duration_high\",\n                \"message\": f\"任务执行时间过长: {metrics.average_task_duration:.1f}秒\",\n                \"value\": metrics.average_task_duration,\n                \"threshold\": thresholds[\"task_duration\"]\n            })\n        \n        # 发送告警事件\n        for alert in alerts:\n            alert_event = ProgressEvent(\n                event_id=f\"alert_{uuid.uuid4().hex[:8]}\",\n                event_type=ProgressEventType.PERFORMANCE_ALERT,\n                timestamp=datetime.now(),\n                workflow_id=\"system\",\n                message=alert[\"message\"],\n                metadata=alert\n            )\n            \n            self._emit_event(alert_event)\n            self.performance_alerts.append({\n                \"timestamp\": datetime.now(),\n                \"alert\": alert\n            })\n            \n            logger.warning(\"性能告警\", alert_type=alert[\"type\"], message=alert[\"message\"])\n    \n    def get_workflow_progress(self, workflow_id: str) -> Optional[WorkflowProgress]:\n        \"\"\"获取工作流进度\"\"\"\n        return self.workflows.get(workflow_id)\n    \n    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:\n        \"\"\"获取任务进度\"\"\"\n        return self.tasks.get(task_id)\n    \n    def get_active_workflows(self) -> List[WorkflowProgress]:\n        \"\"\"获取活跃工作流\"\"\"\n        return [w for w in self.workflows.values() if w.status == TaskStatus.RUNNING]\n    \n    def get_recent_events(self, limit: int = 100, \n                         event_types: List[ProgressEventType] = None) -> List[ProgressEvent]:\n        \"\"\"获取最近事件\"\"\"\n        events = list(self.events)\n        \n        if event_types:\n            events = [e for e in events if e.event_type in event_types]\n        \n        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]\n    \n    def get_performance_metrics(self, hours: int = 1) -> List[PerformanceMetrics]:\n        \"\"\"获取性能指标\"\"\"\n        cutoff_time = datetime.now() - timedelta(hours=hours)\n        return [m for m in self.performance_history if m.timestamp >= cutoff_time]\n    \n    def get_performance_summary(self) -> Dict[str, Any]:\n        \"\"\"获取性能摘要\"\"\"\n        if not self.performance_history:\n            return {}\n        \n        recent_metrics = list(self.performance_history)[-10:]  # 最近10个指标\n        \n        return {\n            \"timestamp\": datetime.now(),\n            \"avg_cpu_usage\": sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics),\n            \"avg_memory_usage\": sum(m.memory_usage for m in recent_metrics) / len(recent_metrics),\n            \"current_active_agents\": recent_metrics[-1].active_agents if recent_metrics else 0,\n            \"current_queue_size\": recent_metrics[-1].queue_size if recent_metrics else 0,\n            \"avg_tasks_per_second\": sum(m.tasks_per_second for m in recent_metrics) / len(recent_metrics),\n            \"avg_task_duration\": sum(m.average_task_duration for m in recent_metrics) / len(recent_metrics),\n            \"current_error_rate\": recent_metrics[-1].error_rate if recent_metrics else 0,\n            \"total_workflows\": len(self.workflows),\n            \"active_workflows\": len(self.get_active_workflows()),\n            \"total_tasks\": len(self.tasks),\n            \"recent_alerts\": len([a for a in self.performance_alerts \n                                 if (datetime.now() - a[\"timestamp\"]).total_seconds() < 3600])  # 最近1小时\n        }\n    \n    def generate_progress_report(self, workflow_id: str = None) -> Dict[str, Any]:\n        \"\"\"生成进度报告\"\"\"\n        report = {\n            \"timestamp\": datetime.now(),\n            \"agent_id\": self.agent_id,\n            \"summary\": self.get_performance_summary()\n        }\n        \n        if workflow_id:\n            # 单个工作流报告\n            workflow = self.get_workflow_progress(workflow_id)\n            if workflow:\n                report[\"workflow\"] = {\n                    \"workflow_id\": workflow_id,\n                    \"status\": workflow.status.value,\n                    \"progress\": workflow.overall_progress,\n                    \"start_time\": workflow.start_time,\n                    \"end_time\": workflow.end_time,\n                    \"estimated_completion\": workflow.estimated_completion,\n                    \"total_tasks\": workflow.total_tasks,\n                    \"completed_tasks\": workflow.completed_tasks,\n                    \"failed_tasks\": workflow.failed_tasks,\n                    \"stages_progress\": workflow.stages_progress,\n                    \"tasks\": {tid: {\n                        \"task_name\": task.task_name,\n                        \"status\": task.status.value,\n                        \"progress\": task.progress_percentage,\n                        \"agent_name\": task.agent_name,\n                        \"current_stage\": task.current_stage,\n                        \"start_time\": task.start_time,\n                        \"end_time\": task.end_time,\n                        \"error_message\": task.error_message\n                    } for tid, task in workflow.tasks.items()}\n                }\n        else:\n            # 全局报告\n            report[\"workflows\"] = {\n                wid: {\n                    \"status\": workflow.status.value,\n                    \"progress\": workflow.overall_progress,\n                    \"total_tasks\": workflow.total_tasks,\n                    \"completed_tasks\": workflow.completed_tasks,\n                    \"failed_tasks\": workflow.failed_tasks\n                } for wid, workflow in self.workflows.items()\n            }\n        \n        return report\n    \n    def export_monitoring_data(self, filepath: str, format: str = \"json\"):\n        \"\"\"导出监控数据\"\"\"\n        data = {\n            \"export_timestamp\": datetime.now().isoformat(),\n            \"agent_id\": self.agent_id,\n            \"workflows\": {wid: asdict(workflow) for wid, workflow in self.workflows.items()},\n            \"tasks\": {tid: asdict(task) for tid, task in self.tasks.items()},\n            \"events\": [asdict(event) for event in self.events],\n            \"performance_history\": [asdict(metrics) for metrics in self.performance_history],\n            \"performance_alerts\": self.performance_alerts\n        }\n        \n        # 处理datetime序列化\n        def datetime_handler(obj):\n            if isinstance(obj, datetime):\n                return obj.isoformat()\n            raise TypeError(f\"Object of type {type(obj)} is not JSON serializable\")\n        \n        if format.lower() == \"json\":\n            with open(filepath, 'w', encoding='utf-8') as f:\n                json.dump(data, f, ensure_ascii=False, indent=2, default=datetime_handler)\n        else:\n            raise ValueError(f\"不支持的导出格式: {format}\")\n        \n        logger.info(\"监控数据已导出\", filepath=filepath, format=format)\n    \n    def cleanup_old_data(self):\n        \"\"\"清理过期数据\"\"\"\n        cutoff_time = datetime.now() - timedelta(days=self.monitoring_config[\"retention_days\"])\n        \n        # 清理过期工作流\n        expired_workflows = [wid for wid, workflow in self.workflows.items()\n                           if workflow.end_time and workflow.end_time < cutoff_time]\n        \n        for wid in expired_workflows:\n            del self.workflows[wid]\n            logger.debug(\"已清理过期工作流\", workflow_id=wid)\n        \n        # 清理过期任务\n        expired_tasks = [tid for tid, task in self.tasks.items()\n                        if task.end_time and task.end_time < cutoff_time]\n        \n        for tid in expired_tasks:\n            del self.tasks[tid]\n            logger.debug(\"已清理过期任务\", task_id=tid)\n        \n        # 清理过期告警\n        self.performance_alerts = [alert for alert in self.performance_alerts\n                                 if alert[\"timestamp\"] >= cutoff_time]\n        \n        logger.info(\"数据清理完成\", \n                   expired_workflows=len(expired_workflows),\n                   expired_tasks=len(expired_tasks))\n    \n    def stop_monitoring(self):\n        \"\"\"停止监控\"\"\"\n        self.monitoring_active = False\n        if self.monitoring_thread.is_alive():\n            self.monitoring_thread.join(timeout=5.0)\n        \n        logger.info(\"进度跟踪监控已停止\", agent_id=self.agent_id)\n    \n    def __del__(self):\n        \"\"\"析构函数\"\"\"\n        self.stop_monitoring()\n\n\nif __name__ == \"__main__\":\n    # 测试代码\n    import time\n    \n    def test_progress_tracking():\n        # 创建进度跟踪 Agent\n        tracker = ProgressTrackingAgent(\"test_tracker\")\n        \n        # 注册事件回调\n        def event_callback(event: ProgressEvent):\n            print(f\"事件: {event.event_type.value} - {event.message}\")\n        \n        tracker.register_event_callback(event_callback)\n        \n        # 开始工作流跟踪\n        workflow_id = \"test_workflow_001\"\n        tracker.start_workflow_tracking(workflow_id, \"test_project\", total_tasks=3)\n        \n        # 开始任务跟踪\n        task1_id = \"task_001\"\n        tracker.start_task_tracking(task1_id, workflow_id, \"文件解析\", \"file_parser\")\n        \n        # 模拟任务进度更新\n        for progress in [25, 50, 75, 100]:\n            tracker.update_task_progress(task1_id, progress, \"parsing\", f\"解析进度: {progress}%\")\n            time.sleep(0.1)\n        \n        # 完成任务\n        tracker.complete_task(task1_id, success=True)\n        \n        # 开始第二个任务\n        task2_id = \"task_002\"\n        tracker.start_task_tracking(task2_id, workflow_id, \"翻译处理\", \"translator\")\n        tracker.update_task_progress(task2_id, 50, \"translating\")\n        tracker.complete_task(task2_id, success=True)\n        \n        # 完成工作流\n        tracker.complete_workflow(workflow_id, success=True)\n        \n        # 生成报告\n        report = tracker.generate_progress_report(workflow_id)\n        print(\"\\n进度报告:\")\n        print(json.dumps(report, indent=2, default=str, ensure_ascii=False))\n        \n        # 获取性能摘要\n        summary = tracker.get_performance_summary()\n        print(\"\\n性能摘要:\")\n        print(json.dumps(summary, indent=2, default=str, ensure_ascii=False))\n        \n        # 停止监控\n        tracker.stop_monitoring()\n    \n    test_progress_tracking()\n"