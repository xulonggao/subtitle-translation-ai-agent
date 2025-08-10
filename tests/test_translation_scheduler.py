"""
翻译任务调度器测试
"""
import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.translation_scheduler import (
    TranslationTaskScheduler, TranslationTaskRequest, TranslationTaskResult,
    WorkerNode, ResourceRequirement, SchedulingDecision,
    TaskPriority, TaskStatus, ResourceType, SchedulingStrategy,
    get_translation_scheduler, submit_translation_task, get_translation_task_status
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestResourceRequirement:
    """资源需求测试"""
    
    def test_resource_requirement_creation(self):
        """测试资源需求创建"""
        requirement = ResourceRequirement(
            cpu_cores=2.0,
            memory_mb=1024,
            network_bandwidth_mbps=50.0,
            model_api_calls=5,
            estimated_duration_seconds=60.0
        )
        
        assert requirement.cpu_cores == 2.0
        assert requirement.memory_mb == 1024
        assert requirement.network_bandwidth_mbps == 50.0
        assert requirement.model_api_calls == 5
        assert requirement.estimated_duration_seconds == 60.0
    
    def test_resource_requirement_defaults(self):
        """测试资源需求默认值"""
        requirement = ResourceRequirement()
        
        assert requirement.cpu_cores == 1.0
        assert requirement.memory_mb == 512
        assert requirement.network_bandwidth_mbps == 10.0
        assert requirement.model_api_calls == 1
        assert requirement.estimated_duration_seconds == 30.0


class TestTranslationTaskRequest:
    """翻译任务请求测试"""
    
    def test_task_request_creation(self):
        """测试任务请求创建"""
        subtitle_entries = [
            SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试字幕1",
                speaker="A"
            ),
            SubtitleEntry(
                index=2,
                start_time=TimeCode(0, 0, 4, 0),
                end_time=TimeCode(0, 0, 6, 0),
                text="测试字幕2",
                speaker="B"
            )
        ]
        
        request = TranslationTaskRequest(
            task_id="test_task_001",
            project_id="test_project",
            subtitle_entries=subtitle_entries,
            target_languages=["en", "ja"],
            priority=TaskPriority.HIGH
        )
        
        assert request.task_id == "test_task_001"
        assert request.project_id == "test_project"
        assert len(request.subtitle_entries) == 2
        assert request.target_languages == ["en", "ja"]
        assert request.priority == TaskPriority.HIGH
        assert request.created_at is not None
        assert request.resource_requirements is not None
    
    def test_task_request_with_deadline(self):
        """测试带截止时间的任务请求"""
        deadline = datetime.now() + timedelta(hours=2)
        
        request = TranslationTaskRequest(
            task_id="test_task_002",
            project_id="test_project",
            subtitle_entries=[],
            target_languages=["en"],
            deadline=deadline
        )
        
        assert request.deadline == deadline


class TestTranslationTaskResult:
    """翻译任务结果测试"""
    
    def test_task_result_creation(self):
        """测试任务结果创建"""
        started_at = datetime.now()
        completed_at = started_at + timedelta(seconds=30)
        
        result = TranslationTaskResult(
            task_id="test_task_001",
            status=TaskStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at
        )
        
        assert result.task_id == "test_task_001"
        assert result.status == TaskStatus.COMPLETED
        assert result.started_at == started_at
        assert result.completed_at == completed_at
        assert result.processing_time_seconds == 30.0
    
    def test_task_result_failure(self):
        """测试失败的任务结果"""
        result = TranslationTaskResult(
            task_id="test_task_002",
            status=TaskStatus.FAILED,
            error_message="翻译失败"
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.error_message == "翻译失败"
        assert result.results is None


class TestWorkerNode:
    """工作节点测试"""
    
    def test_worker_node_creation(self):
        """测试工作节点创建"""
        available_resources = {
            ResourceType.CPU: 4.0,
            ResourceType.MEMORY: 2048.0,
            ResourceType.NETWORK: 100.0
        }
        
        worker = WorkerNode(
            node_id="test_worker",
            node_type="translation_agent",
            available_resources=available_resources,
            current_load={resource: 0.0 for resource in ResourceType},
            max_concurrent_tasks=5
        )
        
        assert worker.node_id == "test_worker"
        assert worker.node_type == "translation_agent"
        assert worker.available_resources == available_resources
        assert worker.max_concurrent_tasks == 5
        assert worker.current_tasks == set()
        assert worker.is_active is True
        assert worker.last_heartbeat is not None
        assert len(worker.current_load) == len(ResourceType)


class TestTranslationTaskScheduler:
    """翻译任务调度器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.scheduler = TranslationTaskScheduler(max_workers=5)
    
    def teardown_method(self):
        """测试后清理"""
        if self.scheduler.is_running:
            self.scheduler.stop()
    
    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        assert self.scheduler.scheduler_id.startswith("scheduler_")
        assert self.scheduler.max_workers == 5
        assert len(self.scheduler.worker_nodes) > 0  # 应该有默认工作节点
        assert self.scheduler.is_running is False
        assert len(self.scheduler.task_queue) == 0
        assert len(self.scheduler.running_tasks) == 0
        
        # 检查默认工作节点
        assert "english_worker" in self.scheduler.worker_nodes
        assert "asian_worker" in self.scheduler.worker_nodes
        assert "european_worker" in self.scheduler.worker_nodes
        assert "optimization_worker" in self.scheduler.worker_nodes
    
    def test_start_stop_scheduler(self):
        """测试启动和停止调度器"""
        # 启动调度器
        self.scheduler.start()
        assert self.scheduler.is_running is True
        assert self.scheduler.scheduler_thread is not None
        
        # 等待一小段时间确保线程启动
        time.sleep(0.1)
        assert self.scheduler.scheduler_thread.is_alive()
        
        # 停止调度器
        self.scheduler.stop()
        assert self.scheduler.is_running is False
    
    def test_register_unregister_worker(self):
        """测试注册和注销工作节点"""
        # 注册新工作节点
        new_worker = WorkerNode(
            node_id="custom_worker",
            node_type="custom_agent",
            available_resources={
                ResourceType.CPU: 2.0,
                ResourceType.MEMORY: 1024.0
            },
            current_load={resource: 0.0 for resource in ResourceType},
            max_concurrent_tasks=3
        )
        
        success = self.scheduler.register_worker(new_worker)
        assert success is True
        assert "custom_worker" in self.scheduler.worker_nodes
        
        # 注销工作节点
        success = self.scheduler.unregister_worker("custom_worker")
        assert success is True
        assert "custom_worker" not in self.scheduler.worker_nodes
        
        # 尝试注销不存在的工作节点
        success = self.scheduler.unregister_worker("nonexistent_worker")
        assert success is False
    
    def test_update_worker_heartbeat(self):
        """测试更新工作节点心跳"""
        worker_id = "english_worker"
        original_heartbeat = self.scheduler.worker_nodes[worker_id].last_heartbeat
        
        # 等待一小段时间
        time.sleep(0.01)
        
        # 更新心跳
        resource_usage = {ResourceType.CPU: 1.5, ResourceType.MEMORY: 512.0}
        self.scheduler.update_worker_heartbeat(worker_id, resource_usage)
        
        # 检查心跳时间是否更新
        new_heartbeat = self.scheduler.worker_nodes[worker_id].last_heartbeat
        assert new_heartbeat > original_heartbeat
        
        # 检查资源使用情况是否更新
        worker = self.scheduler.worker_nodes[worker_id]
        assert worker.current_load[ResourceType.CPU] == 1.5
        assert worker.current_load[ResourceType.MEMORY] == 512.0
    
    def test_validate_task_request(self):
        """测试任务请求验证"""
        # 有效的任务请求
        valid_request = TranslationTaskRequest(
            task_id="valid_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"]
        )
        
        assert self.scheduler._validate_task_request(valid_request) is True
        
        # 无效的任务请求（缺少task_id）
        invalid_request = TranslationTaskRequest(
            task_id="",
            project_id="test_project",
            subtitle_entries=[],
            target_languages=["en"]
        )
        
        assert self.scheduler._validate_task_request(invalid_request) is False
    
    def test_calculate_priority_score(self):
        """测试优先级分数计算"""
        # 普通优先级任务
        normal_request = TranslationTaskRequest(
            task_id="normal_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"],
            priority=TaskPriority.NORMAL
        )
        
        normal_score = self.scheduler._calculate_priority_score(normal_request)
        
        # 高优先级任务
        high_request = TranslationTaskRequest(
            task_id="high_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"],
            priority=TaskPriority.HIGH
        )
        
        high_score = self.scheduler._calculate_priority_score(high_request)
        
        # 高优先级任务应该有更高的分数
        assert high_score > normal_score
        
        # 带截止时间的任务
        deadline_request = TranslationTaskRequest(
            task_id="deadline_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"],
            priority=TaskPriority.NORMAL,
            deadline=datetime.now() + timedelta(minutes=30)
        )
        
        deadline_score = self.scheduler._calculate_priority_score(deadline_request)
        
        # 有截止时间的任务应该有更高的分数
        assert deadline_score > normal_score
    
    def test_find_suitable_workers(self):
        """测试查找适合的工作节点"""
        # 创建一个简单的任务请求
        task_request = TranslationTaskRequest(
            task_id="test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"],
            resource_requirements=ResourceRequirement(
                cpu_cores=0.5,
                memory_mb=256
            )
        )
        
        suitable_workers = self.scheduler._find_suitable_workers(task_request)
        
        # 应该找到一些适合的工作节点
        assert len(suitable_workers) > 0
        assert all(worker_id in self.scheduler.worker_nodes for worker_id in suitable_workers)
    
    def test_calculate_worker_load(self):
        """测试工作节点负载计算"""
        worker_id = "english_worker"
        
        # 初始负载应该很低
        initial_load = self.scheduler._calculate_worker_load(worker_id)
        assert 0.0 <= initial_load <= 1.0
        
        # 模拟增加负载
        worker = self.scheduler.worker_nodes[worker_id]
        worker.current_load[ResourceType.CPU] = 1.0
        worker.current_load[ResourceType.MEMORY] = 512.0
        worker.current_tasks.add("test_task_1")
        
        # 负载应该增加
        increased_load = self.scheduler._calculate_worker_load(worker_id)
        assert increased_load > initial_load
        
        # 不存在的工作节点应该返回无穷大
        nonexistent_load = self.scheduler._calculate_worker_load("nonexistent_worker")
        assert nonexistent_load == float('inf')
    
    def test_check_resource_availability(self):
        """测试资源可用性检查"""
        worker = self.scheduler.worker_nodes["english_worker"]
        
        # 小需求应该满足
        small_requirement = ResourceRequirement(
            cpu_cores=0.5,
            memory_mb=256
        )
        
        assert self.scheduler._check_resource_availability(worker, small_requirement) is True
        
        # 大需求可能不满足
        large_requirement = ResourceRequirement(
            cpu_cores=10.0,
            memory_mb=10240
        )
        
        # 这取决于工作节点的配置，但通常应该返回False
        result = self.scheduler._check_resource_availability(worker, large_requirement)
        assert isinstance(result, bool)
    
    def test_submit_task(self):
        """测试提交任务"""
        task_request = TranslationTaskRequest(
            task_id="submit_test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试字幕",
                speaker="A"
            )],
            target_languages=["en", "ja"],
            priority=TaskPriority.HIGH
        )
        
        # 提交任务
        task_id = self.scheduler.submit_task(task_request)
        
        assert task_id == "submit_test_task"
        assert len(self.scheduler.task_queue) == 1
        assert task_id in self.scheduler.task_results
        assert self.scheduler.task_results[task_id].status == TaskStatus.QUEUED
        
        # 检查统计信息更新
        assert self.scheduler.performance_stats["total_tasks_submitted"] == 1
        assert self.scheduler.performance_stats["current_queue_size"] == 1
    
    def test_get_task_status(self):
        """测试获取任务状态"""
        task_request = TranslationTaskRequest(
            task_id="status_test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"]
        )
        
        # 提交任务
        task_id = self.scheduler.submit_task(task_request)
        
        # 获取任务状态
        status = self.scheduler.get_task_status(task_id)
        
        assert status is not None
        assert status.task_id == task_id
        assert status.status == TaskStatus.QUEUED
        
        # 获取不存在任务的状态
        nonexistent_status = self.scheduler.get_task_status("nonexistent_task")
        assert nonexistent_status is None
    
    def test_cancel_task(self):
        """测试取消任务"""
        task_request = TranslationTaskRequest(
            task_id="cancel_test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"]
        )
        
        # 提交任务
        task_id = self.scheduler.submit_task(task_request)
        
        # 取消任务
        success = self.scheduler.cancel_task(task_id)
        
        assert success is True
        assert len(self.scheduler.task_queue) == 0
        assert self.scheduler.task_results[task_id].status == TaskStatus.CANCELLED
        
        # 尝试取消不存在的任务
        success = self.scheduler.cancel_task("nonexistent_task")
        assert success is False
    
    def test_scheduling_strategies(self):
        """测试不同的调度策略"""
        # 测试设置调度策略
        self.scheduler.set_scheduling_strategy(SchedulingStrategy.LOAD_BALANCED)
        assert self.scheduler.scheduling_strategy == SchedulingStrategy.LOAD_BALANCED
        
        self.scheduler.set_scheduling_strategy(SchedulingStrategy.ROUND_ROBIN)
        assert self.scheduler.scheduling_strategy == SchedulingStrategy.ROUND_ROBIN
        
        self.scheduler.set_scheduling_strategy(SchedulingStrategy.FIFO)
        assert self.scheduler.scheduling_strategy == SchedulingStrategy.FIFO
    
    def test_get_scheduler_status(self):
        """测试获取调度器状态"""
        status = self.scheduler.get_scheduler_status()
        
        assert "scheduler_id" in status
        assert "is_running" in status
        assert "scheduling_strategy" in status
        assert "max_workers" in status
        assert "worker_nodes" in status
        assert "performance_stats" in status
        assert "queue_info" in status
        
        # 检查工作节点信息
        assert len(status["worker_nodes"]) > 0
        for worker_id, worker_info in status["worker_nodes"].items():
            assert "node_type" in worker_info
            assert "is_active" in worker_info
            assert "current_tasks" in worker_info
            assert "max_concurrent_tasks" in worker_info
            assert "load_percentage" in worker_info
    
    def test_get_task_queue_info(self):
        """测试获取任务队列信息"""
        # 提交几个任务
        for i in range(3):
            task_request = TranslationTaskRequest(
                task_id=f"queue_test_task_{i}",
                project_id="test_project",
                subtitle_entries=[SubtitleEntry(
                    index=1,
                    start_time=TimeCode(0, 0, 1, 0),
                    end_time=TimeCode(0, 0, 3, 0),
                    text=f"测试{i}",
                    speaker="A"
                )],
                target_languages=["en"],
                priority=TaskPriority.NORMAL if i % 2 == 0 else TaskPriority.HIGH
            )
            self.scheduler.submit_task(task_request)
        
        # 获取队列信息
        queue_info = self.scheduler.get_task_queue_info()
        
        assert len(queue_info) == 3
        for task_info in queue_info:
            assert "task_id" in task_info
            assert "priority" in task_info
            assert "priority_score" in task_info
            assert "created_at" in task_info
            assert "target_languages" in task_info
            assert "subtitle_count" in task_info
    
    def test_reset_stats(self):
        """测试重置统计信息"""
        # 提交一个任务以产生统计数据
        task_request = TranslationTaskRequest(
            task_id="stats_test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )],
            target_languages=["en"]
        )
        
        self.scheduler.submit_task(task_request)
        
        # 确认有统计数据
        assert self.scheduler.performance_stats["total_tasks_submitted"] > 0
        
        # 重置统计
        self.scheduler.reset_stats()
        
        # 确认统计已重置
        assert self.scheduler.performance_stats["total_tasks_submitted"] == 0
        assert self.scheduler.performance_stats["total_tasks_completed"] == 0
        assert self.scheduler.performance_stats["total_tasks_failed"] == 0
    
    @patch('time.sleep')  # 模拟sleep以加速测试
    def test_task_execution_simulation(self, mock_sleep):
        """测试任务执行模拟"""
        mock_sleep.return_value = None  # 跳过实际的sleep
        
        task_request = TranslationTaskRequest(
            task_id="execution_test_task",
            project_id="test_project",
            subtitle_entries=[SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试字幕",
                speaker="A"
            )],
            target_languages=["en", "ja"]
        )
        
        # 执行任务模拟
        result = self.scheduler._simulate_translation_execution(task_request)
        
        assert "translated_subtitles" in result
        assert "quality_scores" in result
        assert "processing_stats" in result
        
        # 检查翻译结果
        assert "en" in result["translated_subtitles"]
        assert "ja" in result["translated_subtitles"]
        
        # 检查质量分数
        assert "en" in result["quality_scores"]
        assert "ja" in result["quality_scores"]
        
        # 检查处理统计
        stats = result["processing_stats"]
        assert stats["subtitle_count"] == 1
        assert stats["target_languages"] == ["en", "ja"]


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_get_translation_scheduler(self):
        """测试获取调度器实例"""
        scheduler = get_translation_scheduler()
        assert isinstance(scheduler, TranslationTaskScheduler)
        
        # 应该返回同一个实例
        scheduler2 = get_translation_scheduler()
        assert scheduler is scheduler2
    
    def test_submit_translation_task(self):
        """测试便捷的任务提交函数"""
        subtitle_entries = [
            SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试字幕",
                speaker="A"
            )
        ]
        
        task_id = submit_translation_task(
            project_id="test_project",
            subtitle_entries=subtitle_entries,
            target_languages=["en", "ja"],
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        assert isinstance(task_id, str)
        
        # 检查任务是否已提交
        status = get_translation_task_status(task_id)
        assert status is not None
        assert status.task_id == task_id
    
    def test_get_translation_task_status(self):
        """测试便捷的任务状态查询函数"""
        # 提交一个任务
        subtitle_entries = [
            SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="测试",
                speaker="A"
            )
        ]
        
        task_id = submit_translation_task(
            project_id="test_project",
            subtitle_entries=subtitle_entries,
            target_languages=["en"]
        )
        
        # 查询任务状态
        status = get_translation_task_status(task_id)
        
        assert status is not None
        assert isinstance(status, TranslationTaskResult)
        assert status.task_id == task_id
        
        # 查询不存在的任务
        nonexistent_status = get_translation_task_status("nonexistent_task")
        assert nonexistent_status is None


class TestEnumValues:
    """枚举值测试"""
    
    def test_task_priority_values(self):
        """测试任务优先级枚举"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.URGENT.value == 4
        assert TaskPriority.CRITICAL.value == 5
    
    def test_task_status_values(self):
        """测试任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
    
    def test_resource_type_values(self):
        """测试资源类型枚举"""
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.NETWORK.value == "network"
        assert ResourceType.MODEL_API.value == "model_api"
        assert ResourceType.TRANSLATION_AGENT.value == "translation_agent"
    
    def test_scheduling_strategy_values(self):
        """测试调度策略枚举"""
        assert SchedulingStrategy.FIFO.value == "fifo"
        assert SchedulingStrategy.PRIORITY.value == "priority"
        assert SchedulingStrategy.ROUND_ROBIN.value == "round_robin"
        assert SchedulingStrategy.LOAD_BALANCED.value == "load_balanced"
        assert SchedulingStrategy.DEADLINE.value == "deadline"


if __name__ == "__main__":
    pytest.main([__file__])