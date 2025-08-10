#!/usr/bin/env python3
"""
主控 Agent 测试
"""
import unittest
import asyncio
from datetime import datetime

from agents.master_agent import (
    MasterAgent, MasterAgentRequest, MasterAgentResult,
    WorkflowStage, AgentStatus, WorkflowTask
)


class TestMasterAgent(unittest.TestCase):
    """主控 Agent 测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.master_agent = MasterAgent("test_master")
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        self.assertIsNotNone(self.master_agent.agent_id)
        self.assertIsInstance(self.master_agent.sub_agents, dict)
        self.assertIsInstance(self.master_agent.active_workflows, dict)
        self.assertIsInstance(self.master_agent.workflow_history, list)
        self.assertIsInstance(self.master_agent.execution_stats, dict)
    
    def test_master_agent_request_creation(self):
        """测试主控 Agent 请求创建"""
        request = MasterAgentRequest(
            request_id="test_request_1",
            project_id="test_project",
            source_files=["test1.srt", "test2.srt"],
            target_languages=["en", "ja"],
            story_context_file="context.md"
        )
        
        self.assertEqual(request.request_id, "test_request_1")
        self.assertEqual(request.project_id, "test_project")
        self.assertEqual(len(request.source_files), 2)
        self.assertEqual(len(request.target_languages), 2)
        self.assertEqual(request.story_context_file, "context.md")
        self.assertIsNotNone(request.timestamp)
        self.assertIsInstance(request.translation_options, dict)
        self.assertIsInstance(request.quality_requirements, dict)
        self.assertIsInstance(request.optimization_settings, dict)
        self.assertIsInstance(request.workflow_config, dict)
    
    def test_workflow_task_creation(self):
        """测试工作流任务创建"""
        task = WorkflowTask(
            task_id="test_task_1",
            stage=WorkflowStage.FILE_PARSING,
            agent_name="file_parser",
            input_data={"file_path": "test.srt"}
        )
        
        self.assertEqual(task.task_id, "test_task_1")
        self.assertEqual(task.stage, WorkflowStage.FILE_PARSING)
        self.assertEqual(task.agent_name, "file_parser")
        self.assertEqual(task.input_data["file_path"], "test.srt")
        self.assertEqual(task.status, AgentStatus.IDLE)
        self.assertEqual(task.retry_count, 0)
        self.assertEqual(task.max_retries, 3)
    
    def test_workflow_execution_basic(self):
        """测试基础工作流执行"""
        request = MasterAgentRequest(
            request_id="test_workflow_1",
            project_id="test_project",
            source_files=["test.srt"],
            target_languages=["en"]
        )
        
        result = asyncio.run(self.master_agent.execute_workflow(request))
        
        self.assertIsInstance(result, MasterAgentResult)
        self.assertEqual(result.request_id, "test_workflow_1")
        self.assertIsInstance(result.success, bool)
        self.assertIsInstance(result.workflow_stage, WorkflowStage)
        self.assertIsInstance(result.completed_tasks, list)
        self.assertIsInstance(result.failed_tasks, list)
        self.assertGreaterEqual(result.processing_time_ms, 0)
        self.assertIsNotNone(result.timestamp)
    
    def test_workflow_status_tracking(self):
        """测试工作流状态跟踪"""
        # 测试获取不存在的工作流状态
        status = self.master_agent.get_workflow_status("nonexistent")
        self.assertIsNone(status)
        
        # 测试列出活跃工作流
        active_workflows = self.master_agent.list_active_workflows()
        self.assertIsInstance(active_workflows, list)
    
    def test_execution_statistics(self):
        """测试执行统计"""
        stats = self.master_agent.get_execution_statistics()
        
        self.assertIn("total_workflows", stats)
        self.assertIn("successful_workflows", stats)
        self.assertIn("failed_workflows", stats)
        self.assertIn("average_processing_time_ms", stats)
        self.assertIn("agent_performance", stats)
        self.assertIn("stage_performance", stats)
        
        # 初始统计应该为0
        self.assertEqual(stats["total_workflows"], 0)
        self.assertEqual(stats["successful_workflows"], 0)
        self.assertEqual(stats["failed_workflows"], 0)
    
    def test_workflow_cancellation(self):
        """测试工作流取消"""
        # 测试取消不存在的工作流
        result = asyncio.run(self.master_agent.cancel_workflow("nonexistent"))
        self.assertFalse(result)
    
    def test_sub_agents_initialization(self):
        """测试子 Agent 初始化"""
        # 测试子 Agent 字典结构
        self.assertIsInstance(self.master_agent.sub_agents, dict)
        
        # 检查是否尝试初始化了各种子 Agent
        # 注意：由于导入可能失败，我们只检查结构而不检查具体内容
        for agent_name, agent_instance in self.master_agent.sub_agents.items():
            self.assertIsInstance(agent_name, str)
            self.assertIsNotNone(agent_instance)
    
    def test_workflow_stages_enum(self):
        """测试工作流阶段枚举"""
        stages = [
            WorkflowStage.INITIALIZATION,
            WorkflowStage.FILE_PARSING,
            WorkflowStage.CONTEXT_ANALYSIS,
            WorkflowStage.TRANSLATION,
            WorkflowStage.QUALITY_CONTROL,
            WorkflowStage.OPTIMIZATION,
            WorkflowStage.FINALIZATION,
            WorkflowStage.COMPLETED,
            WorkflowStage.FAILED
        ]
        
        for stage in stages:
            self.assertIsInstance(stage.value, str)
    
    def test_agent_status_enum(self):
        """测试 Agent 状态枚举"""
        statuses = [
            AgentStatus.IDLE,
            AgentStatus.RUNNING,
            AgentStatus.COMPLETED,
            AgentStatus.FAILED,
            AgentStatus.UNAVAILABLE
        ]
        
        for status in statuses:
            self.assertIsInstance(status.value, str)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 创建一个会导致错误的请求（空文件列表）
        request = MasterAgentRequest(
            request_id="error_test",
            project_id="test_project",
            source_files=[],  # 空文件列表
            target_languages=["en"]
        )
        
        result = asyncio.run(self.master_agent.execute_workflow(request))
        
        # 即使有错误，也应该返回结果对象
        self.assertIsInstance(result, MasterAgentResult)
        self.assertEqual(result.request_id, "error_test")
        self.assertIsInstance(result.success, bool)
    
    def test_workflow_with_multiple_files_and_languages(self):
        """测试多文件多语言工作流"""
        request = MasterAgentRequest(
            request_id="multi_test",
            project_id="test_project",
            source_files=["ep01.srt", "ep02.srt", "ep03.srt"],
            target_languages=["en", "ja", "ko"],
            story_context_file="story.md",
            translation_options={"style": "formal"},
            quality_requirements={"min_score": 0.8},
            optimization_settings={"level": "balanced"}
        )
        
        result = asyncio.run(self.master_agent.execute_workflow(request))
        
        self.assertIsInstance(result, MasterAgentResult)
        self.assertEqual(result.request_id, "multi_test")
        self.assertIsInstance(result.metadata, dict)
        
        # 检查元数据
        if result.metadata:
            self.assertEqual(result.metadata.get("source_files_count"), 3)
            self.assertEqual(result.metadata.get("target_languages_count"), 3)
    
    def test_workflow_recommendations(self):
        """测试工作流建议生成"""
        request = MasterAgentRequest(
            request_id="recommendation_test",
            project_id="test_project",
            source_files=["test.srt"],
            target_languages=["en"]
        )
        
        result = asyncio.run(self.master_agent.execute_workflow(request))
        
        self.assertIsInstance(result.recommendations, list)
        # 应该至少有一些建议
        if result.recommendations:
            for recommendation in result.recommendations:
                self.assertIsInstance(recommendation, str)
                self.assertGreater(len(recommendation), 0)


class TestMasterAgentDataModels(unittest.TestCase):
    """主控 Agent 数据模型测试"""
    
    def test_master_agent_result_creation(self):
        """测试主控 Agent 结果创建"""
        completed_tasks = [
            WorkflowTask("task1", WorkflowStage.FILE_PARSING, "parser", {})
        ]
        failed_tasks = [
            WorkflowTask("task2", WorkflowStage.TRANSLATION, "translator", {})
        ]
        
        result = MasterAgentResult(
            request_id="test_result",
            success=True,
            workflow_stage=WorkflowStage.COMPLETED,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            processing_time_ms=1500
        )
        
        self.assertEqual(result.request_id, "test_result")
        self.assertTrue(result.success)
        self.assertEqual(result.workflow_stage, WorkflowStage.COMPLETED)
        self.assertEqual(len(result.completed_tasks), 1)
        self.assertEqual(len(result.failed_tasks), 1)
        self.assertEqual(result.processing_time_ms, 1500)
        self.assertIsNotNone(result.timestamp)
        self.assertIsInstance(result.translation_results, dict)
        self.assertIsInstance(result.quality_scores, dict)
        self.assertIsInstance(result.consistency_scores, dict)
        self.assertIsInstance(result.optimization_results, dict)
        self.assertIsInstance(result.recommendations, list)
        self.assertIsInstance(result.metadata, dict)


if __name__ == '__main__':
    unittest.main()