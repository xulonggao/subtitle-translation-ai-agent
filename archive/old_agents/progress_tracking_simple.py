#!/usr/bin/env python3
"""
简化版进度跟踪 Agent
负责翻译任务的进度跟踪、实时状态更新和性能监控
"""
import uuid
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import json

from config import get_logger

logger = get_logger("progress_tracking_simple")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressEventType(Enum):
    """进度事件类型"""
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    PERFORMANCE_ALERT = "performance_alert"


@dataclass
class ProgressEvent:
    """进度事件"""
    event_id: str
    event_type: ProgressEventType
    timestamp: datetime
    workflow_id: str
    task_id: Optional[str] = None
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
    current_stage: Optional[str] = None
    agent_name: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WorkflowProgress:
    """工作流进度信息"""
    workflow_id: str
    project_id: str
    status: TaskStatus
    overall_progress: float
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    tasks: Dict[str, TaskProgress] = None
    
    def __post_init__(self):
        if self.tasks is None:
            self.tasks = {}


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


class ProgressTrackingAgent:
    """简化版进度跟踪 Agent"""
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"progress_agent_{uuid.uuid4().hex[:8]}"
        
        # 进度跟踪数据
        self.workflows: Dict[str, WorkflowProgress] = {}
        self.tasks: Dict[str, TaskProgress] = {}
        self.events: deque = deque(maxlen=1000)
        
        # 性能监控数据
        self.performance_history: deque = deque(maxlen=100)
        
        # 通知回调
        self.event_callbacks: List[Callable[[ProgressEvent], None]] = []
        self.status_callbacks: List[Callable[[str, TaskStatus], None]] = []
        
        # 监控配置
        self.monitoring_config = {
            "performance_interval": 5.0,
            "retention_days": 7
        }
        
        # 启动监控线程
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._performance_monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("进度跟踪 Agent 初始化完成", agent_id=self.agent_id)
    
    def register_event_callback(self, callback: Callable[[ProgressEvent], None]):
        """注册事件回调"""
        self.event_callbacks.append(callback)
        logger.debug("事件回调已注册", callback_count=len(self.event_callbacks))
    
    def register_status_callback(self, callback: Callable[[str, TaskStatus], None]):
        """注册状态变更回调"""
        self.status_callbacks.append(callback)
        logger.debug("状态回调已注册", callback_count=len(self.status_callbacks))
    
    def start_workflow_tracking(self, workflow_id: str, project_id: str, 
                               total_tasks: int = 0, metadata: Dict[str, Any] = None) -> WorkflowProgress:
        """开始工作流跟踪"""
        workflow_progress = WorkflowProgress(
            workflow_id=workflow_id,
            project_id=project_id,
            status=TaskStatus.RUNNING,
            overall_progress=0.0,
            start_time=datetime.now(),
            total_tasks=total_tasks
        )
        
        self.workflows[workflow_id] = workflow_progress
        
        # 发送事件
        event = ProgressEvent(
            event_id=f"workflow_start_{uuid.uuid4().hex[:8]}",
            event_type=ProgressEventType.WORKFLOW_STARTED,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            message=f"工作流 {workflow_id} 开始执行",
            metadata={"project_id": project_id, "total_tasks": total_tasks}
        )
        
        self._emit_event(event)
        
        logger.info("工作流跟踪已开始", 
                   workflow_id=workflow_id, 
                   project_id=project_id,
                   total_tasks=total_tasks)
        
        return workflow_progress
    
    def start_task_tracking(self, task_id: str, workflow_id: str, task_name: str,
                           agent_name: str = None, metadata: Dict[str, Any] = None) -> TaskProgress:
        """开始任务跟踪"""
        task_progress = TaskProgress(
            task_id=task_id,
            workflow_id=workflow_id,
            task_name=task_name,
            status=TaskStatus.RUNNING,
            progress_percentage=0.0,
            start_time=datetime.now(),
            agent_name=agent_name
        )
        
        self.tasks[task_id] = task_progress
        
        # 更新工作流信息
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            workflow.tasks[task_id] = task_progress
            if workflow.total_tasks == 0:
                workflow.total_tasks = len(workflow.tasks)
        
        # 发送事件
        event = ProgressEvent(
            event_id=f"task_start_{uuid.uuid4().hex[:8]}",
            event_type=ProgressEventType.TASK_STARTED,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            task_id=task_id,
            agent_name=agent_name,
            message=f"任务 {task_name} 开始执行",
            metadata=metadata or {}
        )
        
        self._emit_event(event)
        
        logger.info("任务跟踪已开始", 
                   task_id=task_id, 
                   workflow_id=workflow_id,
                   task_name=task_name,
                   agent_name=agent_name)
        
        return task_progress
    
    def update_task_progress(self, task_id: str, progress_percentage: float,
                           current_stage: str = None, message: str = None,
                           metadata: Dict[str, Any] = None):
        """更新任务进度"""
        if task_id not in self.tasks:
            logger.warning("尝试更新不存在的任务进度", task_id=task_id)
            return
        
        task = self.tasks[task_id]
        task.progress_percentage = min(100.0, max(0.0, progress_percentage))
        
        if current_stage:
            task.current_stage = current_stage
        
        # 更新工作流进度
        self._update_workflow_progress(task.workflow_id)
        
        # 发送事件
        event = ProgressEvent(
            event_id=f"task_progress_{uuid.uuid4().hex[:8]}",
            event_type=ProgressEventType.TASK_PROGRESS,
            timestamp=datetime.now(),
            workflow_id=task.workflow_id,
            task_id=task_id,
            agent_name=task.agent_name,
            progress_percentage=progress_percentage,
            message=message or f"任务进度: {progress_percentage:.1f}%",
            metadata=metadata or {}
        )
        
        self._emit_event(event)
        
        logger.debug("任务进度已更新", 
                    task_id=task_id, 
                    progress=progress_percentage,
                    stage=current_stage)
    
    def complete_task(self, task_id: str, success: bool = True, 
                     error_message: str = None, metadata: Dict[str, Any] = None):
        """完成任务"""
        if task_id not in self.tasks:
            logger.warning("尝试完成不存在的任务", task_id=task_id)
            return
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.progress_percentage = 100.0 if success else task.progress_percentage
        task.end_time = datetime.now()
        
        if error_message:
            task.error_message = error_message
        
        # 更新工作流进度
        workflow_id = task.workflow_id
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            if success:
                workflow.completed_tasks += 1
            else:
                workflow.failed_tasks += 1
        
        self._update_workflow_progress(workflow_id)
        
        # 发送事件
        event_type = ProgressEventType.TASK_COMPLETED if success else ProgressEventType.TASK_FAILED
        event = ProgressEvent(
            event_id=f"task_complete_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            task_id=task_id,
            agent_name=task.agent_name,
            progress_percentage=100.0 if success else task.progress_percentage,
            message=f"任务{'完成' if success else '失败'}: {task.task_name}",
            metadata=metadata or {}
        )
        
        self._emit_event(event)
        
        logger.info("任务已完成", 
                   task_id=task_id, 
                   success=success,
                   duration=(task.end_time - task.start_time).total_seconds())
    
    def complete_workflow(self, workflow_id: str, success: bool = True,
                         metadata: Dict[str, Any] = None):
        """完成工作流"""
        if workflow_id not in self.workflows:
            logger.warning("尝试完成不存在的工作流", workflow_id=workflow_id)
            return
        
        workflow = self.workflows[workflow_id]
        workflow.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        workflow.end_time = datetime.now()
        workflow.overall_progress = 100.0
        
        # 发送事件
        event = ProgressEvent(
            event_id=f"workflow_complete_{uuid.uuid4().hex[:8]}",
            event_type=ProgressEventType.WORKFLOW_COMPLETED,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            progress_percentage=100.0,
            message=f"工作流{'完成' if success else '失败'}: {workflow_id}",
            metadata={
                "total_tasks": workflow.total_tasks,
                "completed_tasks": workflow.completed_tasks,
                "failed_tasks": workflow.failed_tasks,
                "duration": (workflow.end_time - workflow.start_time).total_seconds()
            }
        )
        
        self._emit_event(event)
        
        logger.info("工作流已完成", 
                   workflow_id=workflow_id, 
                   success=success,
                   total_tasks=workflow.total_tasks,
                   completed_tasks=workflow.completed_tasks,
                   failed_tasks=workflow.failed_tasks)
    
    def _update_workflow_progress(self, workflow_id: str):
        """更新工作流整体进度"""
        if workflow_id not in self.workflows:
            return
        
        workflow = self.workflows[workflow_id]
        
        if not workflow.tasks:
            return
        
        # 计算整体进度
        total_progress = sum(task.progress_percentage for task in workflow.tasks.values())
        workflow.overall_progress = total_progress / len(workflow.tasks)
    
    def _emit_event(self, event: ProgressEvent):
        """发送事件"""
        self.events.append(event)
        
        # 调用事件回调
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("事件回调执行失败", callback=callback, error=str(e))
        
        # 调用状态回调
        if event.event_type in [ProgressEventType.TASK_STARTED, ProgressEventType.TASK_COMPLETED, ProgressEventType.TASK_FAILED]:
            task_id = event.task_id
            if task_id in self.tasks:
                status = self.tasks[task_id].status
                for callback in self.status_callbacks:
                    try:
                        callback(task_id, status)
                    except Exception as e:
                        logger.error("状态回调执行失败", callback=callback, error=str(e))
    
    def _performance_monitoring_loop(self):
        """性能监控循环"""
        while self.monitoring_active:
            try:
                self._collect_performance_metrics()
                time.sleep(self.monitoring_config["performance_interval"])
            except Exception as e:
                logger.error("性能监控异常", error=str(e))
                time.sleep(5.0)
    
    def _collect_performance_metrics(self):
        """收集性能指标"""
        try:
            # 收集应用指标
            active_workflows = len([w for w in self.workflows.values() if w.status == TaskStatus.RUNNING])
            active_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            
            # 计算任务处理速率
            recent_completions = 0
            recent_duration = 0
            now = datetime.now()
            
            for task in self.tasks.values():
                if task.end_time and (now - task.end_time).total_seconds() < 60:  # 最近1分钟
                    recent_completions += 1
                    if task.start_time:
                        recent_duration += (task.end_time - task.start_time).total_seconds()
            
            tasks_per_second = recent_completions / 60.0 if recent_completions > 0 else 0.0
            average_task_duration = recent_duration / recent_completions if recent_completions > 0 else 0.0
            
            # 计算错误率
            recent_failures = len([t for t in self.tasks.values() 
                                 if t.status == TaskStatus.FAILED and t.end_time 
                                 and (now - t.end_time).total_seconds() < 300])  # 最近5分钟
            recent_total = len([t for t in self.tasks.values() 
                              if t.end_time and (now - t.end_time).total_seconds() < 300])
            error_rate = (recent_failures / recent_total * 100) if recent_total > 0 else 0.0
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                timestamp=now,
                workflow_id="system",
                cpu_usage=0.0,  # 简化版不收集系统指标
                memory_usage=0.0,
                active_agents=active_workflows,
                tasks_per_second=tasks_per_second,
                average_task_duration=average_task_duration,
                error_rate=error_rate,
                queue_size=active_tasks
            )
            
            self.performance_history.append(metrics)
            
        except Exception as e:
            logger.error("性能指标收集失败", error=str(e))
    
    def get_workflow_progress(self, workflow_id: str) -> Optional[WorkflowProgress]:
        """获取工作流进度"""
        return self.workflows.get(workflow_id)
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        return self.tasks.get(task_id)
    
    def get_active_workflows(self) -> List[WorkflowProgress]:
        """获取活跃工作流"""
        return [w for w in self.workflows.values() if w.status == TaskStatus.RUNNING]
    
    def get_performance_metrics(self, hours: int = 1) -> List[PerformanceMetrics]:
        """获取性能指标"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.performance_history if m.timestamp >= cutoff_time]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_history:
            return {
                "timestamp": datetime.now(),
                "total_workflows": len(self.workflows),
                "active_workflows": len(self.get_active_workflows()),
                "total_tasks": len(self.tasks)
            }
        
        recent_metrics = list(self.performance_history)[-10:]  # 最近10个指标
        
        return {
            "timestamp": datetime.now(),
            "current_active_agents": recent_metrics[-1].active_agents if recent_metrics else 0,
            "current_queue_size": recent_metrics[-1].queue_size if recent_metrics else 0,
            "avg_tasks_per_second": sum(m.tasks_per_second for m in recent_metrics) / len(recent_metrics),
            "avg_task_duration": sum(m.average_task_duration for m in recent_metrics) / len(recent_metrics),
            "current_error_rate": recent_metrics[-1].error_rate if recent_metrics else 0,
            "total_workflows": len(self.workflows),
            "active_workflows": len(self.get_active_workflows()),
            "total_tasks": len(self.tasks)
        }
    
    def generate_progress_report(self, workflow_id: str = None) -> Dict[str, Any]:
        """生成进度报告"""
        report = {
            "timestamp": datetime.now(),
            "agent_id": self.agent_id,
            "summary": self.get_performance_summary()
        }
        
        if workflow_id:
            # 单个工作流报告
            workflow = self.get_workflow_progress(workflow_id)
            if workflow:
                report["workflow"] = {
                    "workflow_id": workflow_id,
                    "status": workflow.status.value,
                    "progress": workflow.overall_progress,
                    "start_time": workflow.start_time,
                    "end_time": workflow.end_time,
                    "total_tasks": workflow.total_tasks,
                    "completed_tasks": workflow.completed_tasks,
                    "failed_tasks": workflow.failed_tasks,
                    "tasks": {tid: {
                        "task_name": task.task_name,
                        "status": task.status.value,
                        "progress": task.progress_percentage,
                        "agent_name": task.agent_name,
                        "current_stage": task.current_stage,
                        "start_time": task.start_time,
                        "end_time": task.end_time,
                        "error_message": task.error_message
                    } for tid, task in workflow.tasks.items()}
                }
        else:
            # 全局报告
            report["workflows"] = {
                wid: {
                    "status": workflow.status.value,
                    "progress": workflow.overall_progress,
                    "total_tasks": workflow.total_tasks,
                    "completed_tasks": workflow.completed_tasks,
                    "failed_tasks": workflow.failed_tasks
                } for wid, workflow in self.workflows.items()
            }
        
        return report
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        
        logger.info("进度跟踪监控已停止", agent_id=self.agent_id)
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()


if __name__ == "__main__":
    # 测试代码
    def test_progress_tracking():
        print("🚀 测试进度跟踪 Agent")
        
        # 创建进度跟踪 Agent
        tracker = ProgressTrackingAgent("test_tracker")
        
        # 注册事件回调
        def event_callback(event: ProgressEvent):
            print(f"📢 事件: {event.event_type.value} - {event.message}")
        
        tracker.register_event_callback(event_callback)
        
        # 开始工作流跟踪
        workflow_id = "test_workflow_001"
        tracker.start_workflow_tracking(workflow_id, "test_project", total_tasks=2)
        
        # 开始任务跟踪
        task1_id = "task_001"
        tracker.start_task_tracking(task1_id, workflow_id, "文件解析", "file_parser")
        
        # 模拟任务进度更新
        for progress in [25, 50, 75, 100]:
            tracker.update_task_progress(task1_id, progress, "parsing", f"解析进度: {progress}%")
            time.sleep(0.1)
        
        # 完成任务
        tracker.complete_task(task1_id, success=True)
        
        # 开始第二个任务
        task2_id = "task_002"
        tracker.start_task_tracking(task2_id, workflow_id, "翻译处理", "translator")
        tracker.update_task_progress(task2_id, 50, "translating")
        tracker.complete_task(task2_id, success=True)
        
        # 完成工作流
        tracker.complete_workflow(workflow_id, success=True)
        
        # 生成报告
        report = tracker.generate_progress_report(workflow_id)
        print("\n📊 进度报告:")
        print(f"  工作流ID: {report['workflow']['workflow_id']}")
        print(f"  状态: {report['workflow']['status']}")
        print(f"  进度: {report['workflow']['progress']:.1f}%")
        print(f"  总任务: {report['workflow']['total_tasks']}")
        print(f"  完成任务: {report['workflow']['completed_tasks']}")
        
        # 获取性能摘要
        summary = tracker.get_performance_summary()
        print("\n⚡ 性能摘要:")
        print(f"  总工作流: {summary['total_workflows']}")
        print(f"  活跃工作流: {summary['active_workflows']}")
        print(f"  总任务: {summary['total_tasks']}")
        
        # 停止监控
        tracker.stop_monitoring()
        
        print("\n✅ 测试完成!")
    
    test_progress_tracking()