"""
翻译任务调度器
负责翻译任务的分发、调度和协调
"""
import json
import uuid
import asyncio
import threading
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
import heapq

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationTask

logger = get_logger("translation_scheduler")


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"         # 等待中
    QUEUED = "queued"          # 已排队
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    RETRYING = "retrying"      # 重试中


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    MODEL_API = "model_api"
    TRANSLATION_AGENT = "translation_agent"


class SchedulingStrategy(Enum):
    """调度策略"""
    FIFO = "fifo"                    # 先进先出
    PRIORITY = "priority"            # 优先级调度
    ROUND_ROBIN = "round_robin"      # 轮询调度
    LOAD_BALANCED = "load_balanced"  # 负载均衡
    DEADLINE = "deadline"            # 截止时间调度


@dataclass
class ResourceRequirement:
    """资源需求"""
    cpu_cores: float = 1.0
    memory_mb: int = 512
    network_bandwidth_mbps: float = 10.0
    model_api_calls: int = 1
    estimated_duration_seconds: float = 30.0


@dataclass
class TranslationTaskRequest:
    """翻译任务请求"""
    task_id: str
    project_id: str
    subtitle_entries: List[SubtitleEntry]
    target_languages: List[str]
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[datetime] = None
    resource_requirements: Optional[ResourceRequirement] = None
    callback: Optional[Callable] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.resource_requirements is None:
            self.resource_requirements = ResourceRequirement()


@dataclass
class TranslationTaskResult:
    """翻译任务结果"""
    task_id: str
    status: TaskStatus
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: float = 0.0
    resource_usage: Optional[Dict[str, float]] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.completed_at and self.started_at:
            self.processing_time_seconds = (self.completed_at - self.started_at).total_seconds()


@dataclass
class WorkerNode:
    """工作节点"""
    node_id: str
    node_type: str  # 节点类型：translation_agent, optimization_agent等
    available_resources: Dict[ResourceType, float]
    current_load: Dict[ResourceType, float]
    max_concurrent_tasks: int = 5
    current_tasks: Set[str] = None
    last_heartbeat: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.current_tasks is None:
            self.current_tasks = set()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now()
        if not self.current_load:
            self.current_load = {resource: 0.0 for resource in ResourceType}


@dataclass
class SchedulingDecision:
    """调度决策"""
    task_id: str
    assigned_worker: Optional[str] = None
    estimated_start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    resource_allocation: Optional[Dict[ResourceType, float]] = None
    scheduling_reason: str = ""
    confidence: float = 0.0


class TranslationTaskScheduler:
    """翻译任务调度器
    
    主要功能：
    1. 任务队列管理和优先级调度
    2. 多语言并行翻译协调
    3. 资源分配和负载均衡
    4. 任务监控和故障恢复
    """
    
    def __init__(self, scheduler_id: str = None, max_workers: int = 10):
        self.scheduler_id = scheduler_id or f"scheduler_{uuid.uuid4().hex[:8]}"
        self.max_workers = max_workers
        
        # 任务队列和状态管理
        self.task_queue = []  # 优先级队列
        self.running_tasks: Dict[str, TranslationTaskRequest] = {}
        self.completed_tasks: Dict[str, TranslationTaskResult] = {}
        self.task_results: Dict[str, TranslationTaskResult] = {}
        
        # 工作节点管理
        self.worker_nodes: Dict[str, WorkerNode] = {}
        self.worker_assignments: Dict[str, str] = {}  # task_id -> worker_id
        
        # 调度配置
        self.scheduling_strategy = SchedulingStrategy.PRIORITY
        self.max_retries = 3
        self.retry_delay_seconds = 5.0
        self.heartbeat_timeout_seconds = 60.0
        
        # 线程池和异步处理
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.scheduler_thread = None
        self.is_running = False
        self.lock = threading.RLock()
        
        # 性能统计
        self.performance_stats = {
            "total_tasks_submitted": 0,
            "total_tasks_completed": 0,
            "total_tasks_failed": 0,
            "average_queue_time_seconds": 0.0,
            "average_processing_time_seconds": 0.0,
            "current_queue_size": 0,
            "active_workers": 0,
            "resource_utilization": defaultdict(float),
            "language_distribution": defaultdict(int),
            "priority_distribution": defaultdict(int)
        }
        
        # 初始化默认工作节点
        self._initialize_default_workers()
        
        logger.info("翻译任务调度器初始化完成", 
                   scheduler_id=self.scheduler_id, 
                   max_workers=max_workers)
    
    def _initialize_default_workers(self):
        """初始化默认工作节点"""
        # 创建默认的翻译工作节点
        default_workers = [
            {
                "node_id": "english_worker",
                "node_type": "english_translation_agent",
                "available_resources": {
                    ResourceType.CPU: 2.0,
                    ResourceType.MEMORY: 1024.0,
                    ResourceType.NETWORK: 100.0,
                    ResourceType.MODEL_API: 10.0,
                    ResourceType.TRANSLATION_AGENT: 1.0
                },
                "max_concurrent_tasks": 3
            },
            {
                "node_id": "asian_worker",
                "node_type": "asian_translation_agent",
                "available_resources": {
                    ResourceType.CPU: 2.0,
                    ResourceType.MEMORY: 1024.0,
                    ResourceType.NETWORK: 100.0,
                    ResourceType.MODEL_API: 10.0,
                    ResourceType.TRANSLATION_AGENT: 1.0
                },
                "max_concurrent_tasks": 3
            },
            {
                "node_id": "european_worker",
                "node_type": "european_translation_agent",
                "available_resources": {
                    ResourceType.CPU: 2.0,
                    ResourceType.MEMORY: 1024.0,
                    ResourceType.NETWORK: 100.0,
                    ResourceType.MODEL_API: 10.0,
                    ResourceType.TRANSLATION_AGENT: 1.0
                },
                "max_concurrent_tasks": 3
            },
            {
                "node_id": "optimization_worker",
                "node_type": "subtitle_optimization_agent",
                "available_resources": {
                    ResourceType.CPU: 1.0,
                    ResourceType.MEMORY: 512.0,
                    ResourceType.NETWORK: 50.0,
                    ResourceType.MODEL_API: 5.0,
                    ResourceType.TRANSLATION_AGENT: 1.0
                },
                "max_concurrent_tasks": 5
            }
        ]
        
        for worker_config in default_workers:
            worker = WorkerNode(
                node_id=worker_config["node_id"],
                node_type=worker_config["node_type"],
                available_resources=worker_config["available_resources"],
                current_load={resource: 0.0 for resource in ResourceType},
                max_concurrent_tasks=worker_config["max_concurrent_tasks"]
            )
            self.worker_nodes[worker.node_id] = worker
        
        logger.info("默认工作节点初始化完成", worker_count=len(default_workers))
    
    def start(self):
        """启动调度器"""
        with self.lock:
            if self.is_running:
                logger.warning("调度器已在运行中")
                return
            
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("翻译任务调度器已启动", scheduler_id=self.scheduler_id)
    
    def stop(self):
        """停止调度器"""
        with self.lock:
            if not self.is_running:
                return
            
            self.is_running = False
            
            # 等待调度线程结束
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5.0)
            
            # 关闭线程池
            self.executor.shutdown(wait=True)
            
            logger.info("翻译任务调度器已停止", scheduler_id=self.scheduler_id)
    
    def submit_task(self, task_request: TranslationTaskRequest) -> str:
        """提交翻译任务"""
        with self.lock:
            # 验证任务请求
            if not self._validate_task_request(task_request):
                raise ValueError(f"无效的任务请求: {task_request.task_id}")
            
            # 添加到优先级队列
            priority_score = self._calculate_priority_score(task_request)
            heapq.heappush(self.task_queue, (-priority_score, task_request.created_at, task_request))
            
            # 创建任务结果记录
            task_result = TranslationTaskResult(
                task_id=task_request.task_id,
                status=TaskStatus.QUEUED
            )
            self.task_results[task_request.task_id] = task_result
            
            # 更新统计信息
            self._update_submission_stats(task_request)
            
            logger.info("翻译任务已提交", 
                       task_id=task_request.task_id,
                       priority=task_request.priority.value,
                       target_languages=task_request.target_languages,
                       queue_size=len(self.task_queue))
            
            return task_request.task_id
    
    def get_task_status(self, task_id: str) -> Optional[TranslationTaskResult]:
        """获取任务状态"""
        return self.task_results.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            # 检查任务是否在队列中
            for i, (priority, created_at, task) in enumerate(self.task_queue):
                if task.task_id == task_id:
                    # 从队列中移除
                    del self.task_queue[i]
                    heapq.heapify(self.task_queue)
                    
                    # 更新任务状态
                    if task_id in self.task_results:
                        self.task_results[task_id].status = TaskStatus.CANCELLED
                    
                    logger.info("任务已从队列中取消", task_id=task_id)
                    return True
            
            # 检查任务是否正在运行
            if task_id in self.running_tasks:
                # 标记为取消（实际取消需要工作节点配合）
                if task_id in self.task_results:
                    self.task_results[task_id].status = TaskStatus.CANCELLED
                
                logger.info("运行中任务已标记为取消", task_id=task_id)
                return True
            
            logger.warning("未找到要取消的任务", task_id=task_id)
            return False
    
    def register_worker(self, worker: WorkerNode) -> bool:
        """注册工作节点"""
        with self.lock:
            self.worker_nodes[worker.node_id] = worker
            logger.info("工作节点已注册", 
                       node_id=worker.node_id, 
                       node_type=worker.node_type,
                       max_tasks=worker.max_concurrent_tasks)
            return True
    
    def unregister_worker(self, worker_id: str) -> bool:
        """注销工作节点"""
        with self.lock:
            if worker_id in self.worker_nodes:
                # 检查是否有正在运行的任务
                worker = self.worker_nodes[worker_id]
                if worker.current_tasks:
                    logger.warning("工作节点仍有运行中的任务，无法注销", 
                                 worker_id=worker_id, 
                                 running_tasks=list(worker.current_tasks))
                    return False
                
                del self.worker_nodes[worker_id]
                logger.info("工作节点已注销", worker_id=worker_id)
                return True
            
            logger.warning("未找到要注销的工作节点", worker_id=worker_id)
            return False
    
    def update_worker_heartbeat(self, worker_id: str, resource_usage: Optional[Dict[ResourceType, float]] = None):
        """更新工作节点心跳"""
        with self.lock:
            if worker_id in self.worker_nodes:
                worker = self.worker_nodes[worker_id]
                worker.last_heartbeat = datetime.now()
                worker.is_active = True
                
                if resource_usage:
                    worker.current_load.update(resource_usage)
                
                logger.debug("工作节点心跳已更新", worker_id=worker_id)
            else:
                logger.warning("未找到工作节点", worker_id=worker_id)
    
    def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("调度器主循环已启动")
        
        while self.is_running:
            try:
                # 检查工作节点健康状态
                self._check_worker_health()
                
                # 处理队列中的任务
                self._process_task_queue()
                
                # 检查运行中任务的状态
                self._check_running_tasks()
                
                # 更新性能统计
                self._update_performance_stats()
                
                # 短暂休眠
                threading.Event().wait(1.0)
                
            except Exception as e:
                logger.error("调度器循环出错", error=str(e))
                threading.Event().wait(5.0)
        
        logger.info("调度器主循环已结束")
    
    def _process_task_queue(self):
        """处理任务队列"""
        with self.lock:
            while self.task_queue and self._has_available_workers():
                # 获取最高优先级的任务
                priority_score, created_at, task_request = heapq.heappop(self.task_queue)
                
                # 进行调度决策
                decision = self._make_scheduling_decision(task_request)
                
                if decision.assigned_worker:
                    # 分配任务给工作节点
                    self._assign_task_to_worker(task_request, decision.assigned_worker)
                else:
                    # 没有可用工作节点，重新放回队列
                    heapq.heappush(self.task_queue, (priority_score, created_at, task_request))
                    break
    
    def _make_scheduling_decision(self, task_request: TranslationTaskRequest) -> SchedulingDecision:
        """制定调度决策"""
        decision = SchedulingDecision(task_id=task_request.task_id)
        
        # 根据调度策略选择工作节点
        if self.scheduling_strategy == SchedulingStrategy.PRIORITY:
            worker_id = self._select_worker_by_priority(task_request)
        elif self.scheduling_strategy == SchedulingStrategy.LOAD_BALANCED:
            worker_id = self._select_worker_by_load_balance(task_request)
        elif self.scheduling_strategy == SchedulingStrategy.ROUND_ROBIN:
            worker_id = self._select_worker_by_round_robin(task_request)
        else:
            worker_id = self._select_worker_by_fifo(task_request)
        
        if worker_id:
            decision.assigned_worker = worker_id
            decision.estimated_start_time = datetime.now()
            decision.estimated_completion_time = (
                decision.estimated_start_time + 
                timedelta(seconds=task_request.resource_requirements.estimated_duration_seconds)
            )
            decision.scheduling_reason = f"使用{self.scheduling_strategy.value}策略分配给{worker_id}"
            decision.confidence = 0.8
        else:
            decision.scheduling_reason = "没有可用的工作节点"
            decision.confidence = 0.0
        
        return decision
    
    def _select_worker_by_priority(self, task_request: TranslationTaskRequest) -> Optional[str]:
        """基于优先级选择工作节点"""
        suitable_workers = self._find_suitable_workers(task_request)
        
        if not suitable_workers:
            return None
        
        # 选择负载最低的工作节点
        return min(suitable_workers, key=lambda w_id: self._calculate_worker_load(w_id))
    
    def _select_worker_by_load_balance(self, task_request: TranslationTaskRequest) -> Optional[str]:
        """基于负载均衡选择工作节点"""
        suitable_workers = self._find_suitable_workers(task_request)
        
        if not suitable_workers:
            return None
        
        # 计算每个工作节点的负载分数
        load_scores = {}
        for worker_id in suitable_workers:
            load_scores[worker_id] = self._calculate_worker_load(worker_id)
        
        # 选择负载最低的工作节点
        return min(load_scores.keys(), key=lambda w_id: load_scores[w_id])
    
    def _select_worker_by_round_robin(self, task_request: TranslationTaskRequest) -> Optional[str]:
        """基于轮询选择工作节点"""
        suitable_workers = self._find_suitable_workers(task_request)
        
        if not suitable_workers:
            return None
        
        # 简单的轮询实现
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        worker_id = suitable_workers[self._round_robin_index % len(suitable_workers)]
        self._round_robin_index += 1
        
        return worker_id
    
    def _select_worker_by_fifo(self, task_request: TranslationTaskRequest) -> Optional[str]:
        """基于先进先出选择工作节点"""
        suitable_workers = self._find_suitable_workers(task_request)
        
        if not suitable_workers:
            return None
        
        # 返回第一个可用的工作节点
        return suitable_workers[0]
    
    def _find_suitable_workers(self, task_request: TranslationTaskRequest) -> List[str]:
        """查找适合的工作节点"""
        suitable_workers = []
        
        for worker_id, worker in self.worker_nodes.items():
            if not worker.is_active:
                continue
            
            # 检查工作节点是否有空闲容量
            if len(worker.current_tasks) >= worker.max_concurrent_tasks:
                continue
            
            # 检查资源需求是否满足
            if self._check_resource_availability(worker, task_request.resource_requirements):
                suitable_workers.append(worker_id)
        
        return suitable_workers
    
    def _check_resource_availability(self, worker: WorkerNode, requirements: ResourceRequirement) -> bool:
        """检查资源可用性"""
        # 检查CPU
        if worker.current_load.get(ResourceType.CPU, 0) + requirements.cpu_cores > worker.available_resources.get(ResourceType.CPU, 0):
            return False
        
        # 检查内存
        if worker.current_load.get(ResourceType.MEMORY, 0) + requirements.memory_mb > worker.available_resources.get(ResourceType.MEMORY, 0):
            return False
        
        # 检查网络带宽
        if worker.current_load.get(ResourceType.NETWORK, 0) + requirements.network_bandwidth_mbps > worker.available_resources.get(ResourceType.NETWORK, 0):
            return False
        
        return True
    
    def _calculate_worker_load(self, worker_id: str) -> float:
        """计算工作节点负载"""
        worker = self.worker_nodes.get(worker_id)
        if not worker:
            return float('inf')
        
        # 计算各种资源的使用率
        cpu_usage = worker.current_load.get(ResourceType.CPU, 0) / worker.available_resources.get(ResourceType.CPU, 1)
        memory_usage = worker.current_load.get(ResourceType.MEMORY, 0) / worker.available_resources.get(ResourceType.MEMORY, 1)
        network_usage = worker.current_load.get(ResourceType.NETWORK, 0) / worker.available_resources.get(ResourceType.NETWORK, 1)
        task_usage = len(worker.current_tasks) / worker.max_concurrent_tasks
        
        # 加权平均负载
        return (cpu_usage * 0.3 + memory_usage * 0.2 + network_usage * 0.1 + task_usage * 0.4)
    
    def _assign_task_to_worker(self, task_request: TranslationTaskRequest, worker_id: str):
        """分配任务给工作节点"""
        worker = self.worker_nodes[worker_id]
        
        # 更新工作节点状态
        worker.current_tasks.add(task_request.task_id)
        self._update_worker_resource_usage(worker, task_request.resource_requirements, True)
        
        # 更新任务状态
        self.running_tasks[task_request.task_id] = task_request
        self.worker_assignments[task_request.task_id] = worker_id
        
        if task_request.task_id in self.task_results:
            self.task_results[task_request.task_id].status = TaskStatus.RUNNING
            self.task_results[task_request.task_id].started_at = datetime.now()
        
        # 提交任务到线程池执行
        future = self.executor.submit(self._execute_task, task_request, worker_id)
        
        logger.info("任务已分配给工作节点", 
                   task_id=task_request.task_id,
                   worker_id=worker_id,
                   worker_load=self._calculate_worker_load(worker_id))
    
    def _execute_task(self, task_request: TranslationTaskRequest, worker_id: str) -> TranslationTaskResult:
        """执行翻译任务"""
        start_time = datetime.now()
        
        try:
            logger.info("开始执行翻译任务", 
                       task_id=task_request.task_id,
                       worker_id=worker_id)
            
            # 模拟任务执行（实际实现中会调用相应的翻译Agent）
            results = self._simulate_translation_execution(task_request)
            
            # 任务完成
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            task_result = TranslationTaskResult(
                task_id=task_request.task_id,
                status=TaskStatus.COMPLETED,
                results=results,
                started_at=start_time,
                completed_at=end_time,
                processing_time_seconds=processing_time
            )
            
            # 执行回调
            if task_request.callback:
                try:
                    task_request.callback(task_result)
                except Exception as e:
                    logger.error("任务回调执行失败", 
                               task_id=task_request.task_id, 
                               error=str(e))
            
            logger.info("翻译任务执行完成", 
                       task_id=task_request.task_id,
                       processing_time=processing_time)
            
            return task_result
            
        except Exception as e:
            # 任务失败
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            task_result = TranslationTaskResult(
                task_id=task_request.task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                started_at=start_time,
                completed_at=end_time,
                processing_time_seconds=processing_time
            )
            
            logger.error("翻译任务执行失败", 
                        task_id=task_request.task_id,
                        error=str(e))
            
            return task_result
        
        finally:
            # 清理资源
            self._cleanup_task_resources(task_request.task_id, worker_id)
    
    def _simulate_translation_execution(self, task_request: TranslationTaskRequest) -> Dict[str, Any]:
        """模拟翻译执行（实际实现中会调用真实的翻译Agent）"""
        import time
        import random
        
        # 模拟处理时间
        processing_time = random.uniform(1.0, 5.0)
        time.sleep(processing_time)
        
        # 模拟翻译结果
        results = {
            "translated_subtitles": {},
            "quality_scores": {},
            "processing_stats": {
                "subtitle_count": len(task_request.subtitle_entries),
                "target_languages": task_request.target_languages,
                "processing_time": processing_time
            }
        }
        
        for language in task_request.target_languages:
            results["translated_subtitles"][language] = [
                {
                    "index": entry.index,
                    "text": f"[{language}] {entry.text}",
                    "start_time": entry.start_time,
                    "end_time": entry.end_time
                }
                for entry in task_request.subtitle_entries
            ]
            results["quality_scores"][language] = random.uniform(0.7, 0.95)
        
        return results
    
    def _cleanup_task_resources(self, task_id: str, worker_id: str):
        """清理任务资源"""
        with self.lock:
            # 从运行任务中移除
            if task_id in self.running_tasks:
                task_request = self.running_tasks.pop(task_id)
                
                # 更新工作节点状态
                if worker_id in self.worker_nodes:
                    worker = self.worker_nodes[worker_id]
                    worker.current_tasks.discard(task_id)
                    self._update_worker_resource_usage(worker, task_request.resource_requirements, False)
                
                # 移除工作节点分配
                if task_id in self.worker_assignments:
                    del self.worker_assignments[task_id]
                
                logger.debug("任务资源已清理", task_id=task_id, worker_id=worker_id)
    
    def _update_worker_resource_usage(self, worker: WorkerNode, requirements: ResourceRequirement, allocate: bool):
        """更新工作节点资源使用情况"""
        multiplier = 1 if allocate else -1
        
        worker.current_load[ResourceType.CPU] += requirements.cpu_cores * multiplier
        worker.current_load[ResourceType.MEMORY] += requirements.memory_mb * multiplier
        worker.current_load[ResourceType.NETWORK] += requirements.network_bandwidth_mbps * multiplier
        worker.current_load[ResourceType.MODEL_API] += requirements.model_api_calls * multiplier
        
        # 确保不会出现负值
        for resource_type in ResourceType:
            worker.current_load[resource_type] = max(0, worker.current_load[resource_type])
    
    def _check_running_tasks(self):
        """检查运行中任务的状态"""
        with self.lock:
            completed_tasks = []
            
            for task_id, task_result in self.task_results.items():
                if task_result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    if task_id in self.running_tasks:
                        completed_tasks.append(task_id)
            
            # 移动已完成的任务
            for task_id in completed_tasks:
                if task_id in self.running_tasks:
                    self.completed_tasks[task_id] = self.running_tasks.pop(task_id)
    
    def _check_worker_health(self):
        """检查工作节点健康状态"""
        current_time = datetime.now()
        timeout_threshold = timedelta(seconds=self.heartbeat_timeout_seconds)
        
        with self.lock:
            for worker_id, worker in self.worker_nodes.items():
                if worker.is_active and (current_time - worker.last_heartbeat) > timeout_threshold:
                    worker.is_active = False
                    logger.warning("工作节点心跳超时，标记为不活跃", 
                                 worker_id=worker_id,
                                 last_heartbeat=worker.last_heartbeat)
    
    def _has_available_workers(self) -> bool:
        """检查是否有可用的工作节点"""
        for worker in self.worker_nodes.values():
            if worker.is_active and len(worker.current_tasks) < worker.max_concurrent_tasks:
                return True
        return False
    
    def _validate_task_request(self, task_request: TranslationTaskRequest) -> bool:
        """验证任务请求"""
        if not task_request.task_id:
            return False
        
        if not task_request.project_id:
            return False
        
        if not task_request.subtitle_entries:
            return False
        
        if not task_request.target_languages:
            return False
        
        return True
    
    def _calculate_priority_score(self, task_request: TranslationTaskRequest) -> float:
        """计算任务优先级分数"""
        base_score = task_request.priority.value * 100
        
        # 考虑截止时间
        if task_request.deadline:
            time_to_deadline = (task_request.deadline - datetime.now()).total_seconds()
            if time_to_deadline > 0:
                # 截止时间越近，优先级越高
                urgency_bonus = max(0, 100 - time_to_deadline / 3600)  # 基于小时计算
                base_score += urgency_bonus
            else:
                # 已过期的任务获得最高优先级
                base_score += 1000
        
        # 考虑任务大小（较小的任务优先级稍高）
        size_penalty = len(task_request.subtitle_entries) * 0.1
        base_score -= size_penalty
        
        return base_score
    
    def _update_submission_stats(self, task_request: TranslationTaskRequest):
        """更新提交统计信息"""
        self.performance_stats["total_tasks_submitted"] += 1
        self.performance_stats["current_queue_size"] = len(self.task_queue)
        
        # 更新语言分布
        for language in task_request.target_languages:
            self.performance_stats["language_distribution"][language] += 1
        
        # 更新优先级分布
        priority_name = task_request.priority.value
        self.performance_stats["priority_distribution"][priority_name] += 1
    
    def _update_performance_stats(self):
        """更新性能统计信息"""
        with self.lock:
            # 更新当前队列大小
            self.performance_stats["current_queue_size"] = len(self.task_queue)
            
            # 更新活跃工作节点数
            active_workers = sum(1 for worker in self.worker_nodes.values() if worker.is_active)
            self.performance_stats["active_workers"] = active_workers
            
            # 更新资源利用率
            if self.worker_nodes:
                total_resources = defaultdict(float)
                used_resources = defaultdict(float)
                
                for worker in self.worker_nodes.values():
                    if worker.is_active:
                        for resource_type, available in worker.available_resources.items():
                            total_resources[resource_type] += available
                            used_resources[resource_type] += worker.current_load.get(resource_type, 0)
                
                for resource_type in ResourceType:
                    if total_resources[resource_type] > 0:
                        utilization = used_resources[resource_type] / total_resources[resource_type]
                        self.performance_stats["resource_utilization"][resource_type.value] = utilization
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        with self.lock:
            return {
                "scheduler_id": self.scheduler_id,
                "is_running": self.is_running,
                "scheduling_strategy": self.scheduling_strategy.value,
                "max_workers": self.max_workers,
                "worker_nodes": {
                    worker_id: {
                        "node_type": worker.node_type,
                        "is_active": worker.is_active,
                        "current_tasks": len(worker.current_tasks),
                        "max_concurrent_tasks": worker.max_concurrent_tasks,
                        "load_percentage": self._calculate_worker_load(worker_id) * 100
                    }
                    for worker_id, worker in self.worker_nodes.items()
                },
                "performance_stats": dict(self.performance_stats),
                "queue_info": {
                    "pending_tasks": len(self.task_queue),
                    "running_tasks": len(self.running_tasks),
                    "completed_tasks": len(self.completed_tasks)
                }
            }
    
    def get_task_queue_info(self) -> List[Dict[str, Any]]:
        """获取任务队列信息"""
        with self.lock:
            queue_info = []
            for priority_score, created_at, task_request in self.task_queue:
                queue_info.append({
                    "task_id": task_request.task_id,
                    "priority": task_request.priority.value,
                    "priority_score": -priority_score,
                    "created_at": created_at.isoformat(),
                    "target_languages": task_request.target_languages,
                    "subtitle_count": len(task_request.subtitle_entries),
                    "deadline": task_request.deadline.isoformat() if task_request.deadline else None
                })
            return queue_info
    
    def set_scheduling_strategy(self, strategy: SchedulingStrategy):
        """设置调度策略"""
        with self.lock:
            self.scheduling_strategy = strategy
            logger.info("调度策略已更新", strategy=strategy.value)
    
    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            self.performance_stats = {
                "total_tasks_submitted": 0,
                "total_tasks_completed": 0,
                "total_tasks_failed": 0,
                "average_queue_time_seconds": 0.0,
                "average_processing_time_seconds": 0.0,
                "current_queue_size": len(self.task_queue),
                "active_workers": sum(1 for w in self.worker_nodes.values() if w.is_active),
                "resource_utilization": defaultdict(float),
                "language_distribution": defaultdict(int),
                "priority_distribution": defaultdict(int)
            }
            logger.info("性能统计已重置")


# 全局翻译任务调度器实例
translation_scheduler = TranslationTaskScheduler()


def get_translation_scheduler() -> TranslationTaskScheduler:
    """获取翻译任务调度器实例"""
    return translation_scheduler


# 便捷函数
def submit_translation_task(project_id: str, subtitle_entries: List[SubtitleEntry],
                          target_languages: List[str], priority: TaskPriority = TaskPriority.NORMAL,
                          deadline: Optional[datetime] = None) -> str:
    """便捷的翻译任务提交函数"""
    scheduler = get_translation_scheduler()
    
    task_request = TranslationTaskRequest(
        task_id=str(uuid.uuid4()),
        project_id=project_id,
        subtitle_entries=subtitle_entries,
        target_languages=target_languages,
        priority=priority,
        deadline=deadline
    )
    
    return scheduler.submit_task(task_request)


def get_translation_task_status(task_id: str) -> Optional[TranslationTaskResult]:
    """便捷的任务状态查询函数"""
    scheduler = get_translation_scheduler()
    return scheduler.get_task_status(task_id)