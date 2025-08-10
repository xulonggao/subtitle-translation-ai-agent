"""
上下文管理 Agent 测试
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from agents.context_agent import (
    ContextAgent, ContextQuery, ContextResponse,
    get_context_agent, create_context_tools, execute_context_tool
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestContextQuery:
    """上下文查询测试"""
    
    def test_context_query_creation(self):
        """测试上下文查询创建"""
        query = ContextQuery(
            query_id="test_query_1",
            project_id="test_project",
            query_type="speaker_inference"
        )
        
        assert query.query_id == "test_query_1"
        assert query.project_id == "test_project"
        assert query.query_type == "speaker_inference"
        assert query.timestamp is not None
    
    def test_context_query_with_subtitle(self):
        """测试包含字幕条目的查询"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="这是测试文本",
            speaker="张三"
        )
        
        query = ContextQuery(
            query_id="test_query_2",
            project_id="test_project",
            query_type="pronoun_resolution",
            subtitle_entry=subtitle_entry
        )
        
        assert query.subtitle_entry == subtitle_entry
        assert query.subtitle_entry.text == "这是测试文本"


class TestContextResponse:
    """上下文响应测试"""
    
    def test_context_response_creation(self):
        """测试上下文响应创建"""
        response = ContextResponse(
            query_id="test_query_1",
            success=True,
            result={"speaker": "张三"},
            confidence=0.8
        )
        
        assert response.query_id == "test_query_1"
        assert response.success is True
        assert response.result["speaker"] == "张三"
        assert response.confidence == 0.8
        assert response.timestamp is not None
    
    def test_error_response(self):
        """测试错误响应"""
        response = ContextResponse(
            query_id="test_query_2",
            success=False,
            error_message="查询失败"
        )
        
        assert response.success is False
        assert response.error_message == "查询失败"
        assert response.result is None


class TestContextAgent:
    """上下文管理 Agent 测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 使用 Mock 对象避免依赖外部组件
        with patch('agents.context_agent.get_context_manager'), \
             patch('agents.context_agent.get_dynamic_knowledge_manager'), \
             patch('agents.context_agent.get_dialogue_tracker'):
            self.agent = ContextAgent("test_agent")
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        assert self.agent.agent_id == "test_agent"
        assert len(self.agent.active_sessions) == 0
        assert len(self.agent.query_history) == 0
        assert "speaker_inference" in self.agent.query_processors
        assert "pronoun_resolution" in self.agent.query_processors
    
    def test_session_management(self):
        """测试会话管理"""
        # Mock 上下文管理器
        self.agent.context_manager.load_project_context = Mock()
        self.agent.context_tracker.start_session = Mock(return_value="session_123")
        self.agent.context_tracker.end_session = Mock()
        
        # 开始会话
        session_id = self.agent.start_session("test_project")
        
        assert session_id in self.agent.active_sessions
        assert self.agent.active_sessions[session_id] == "test_project"
        
        # 结束会话
        self.agent.end_session(session_id)
        
        assert session_id not in self.agent.active_sessions
    
    def test_query_validation(self):
        """测试查询验证"""
        # 有效查询
        valid_query = ContextQuery(
            query_id="test_1",
            project_id="test_project",
            query_type="context_summary"
        )
        assert self.agent._validate_query(valid_query) is True
        
        # 无效查询 - 缺少项目ID
        invalid_query1 = ContextQuery(
            query_id="test_2",
            project_id="",
            query_type="context_summary"
        )
        assert self.agent._validate_query(invalid_query1) is False
        
        # 无效查询 - 需要字幕条目但未提供
        invalid_query2 = ContextQuery(
            query_id="test_3",
            project_id="test_project",
            query_type="speaker_inference"
        )
        assert self.agent._validate_query(invalid_query2) is False
    
    def test_speaker_inference_query(self):
        """测试说话人推断查询"""
        # Mock 依赖
        mock_context = {
            "speaker": "张三",
            "speaker_info": {"name": "张三", "role": "主角"},
            "relationship": {"type": "friend"}
        }
        self.agent.context_manager.get_speaker_context = Mock(return_value=mock_context)
        
        # 创建查询
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="我觉得这个计划很好",
            speaker=None
        )
        
        query = ContextQuery(
            query_id="test_speaker",
            project_id="test_project",
            query_type="speaker_inference",
            subtitle_entry=subtitle_entry
        )
        
        # 处理查询
        response = self.agent.process_query(query)
        
        assert response.success is True
        assert response.result["inferred_speaker"] == "张三"
        assert "speaker_info" in response.result
        assert response.confidence > 0
    
    def test_cultural_adaptation_query(self):
        """测试文化适配查询"""
        # Mock 依赖
        mock_adaptation_context = {
            "genre": "military",
            "cultural_notes": ["军事题材", "现代背景"]
        }
        self.agent.context_manager.get_cultural_adaptation_context = Mock(
            return_value=mock_adaptation_context
        )
        
        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = [{"term": "司令", "translation": "commander"}]
        mock_kb_result.confidence = 0.9
        self.agent.dynamic_kb.query_knowledge = Mock(return_value=mock_kb_result)
        
        # 创建查询
        query = ContextQuery(
            query_id="test_cultural",
            project_id="test_project",
            query_type="cultural_adaptation",
            target_language="en"
        )
        
        # 处理查询
        response = self.agent.process_query(query)
        
        assert response.success is True
        assert response.result["target_language"] == "en"
        assert "adaptation_context" in response.result
        assert "recommendations" in response.result
    
    def test_context_summary_query(self):
        """测试上下文摘要查询"""
        # Mock 依赖
        self.agent.context_manager.get_context_statistics = Mock(return_value={
            "project_id": "test_project",
            "characters_count": 5
        })
        self.agent.context_tracker.get_session_statistics = Mock(return_value={
            "active_sessions": 1
        })
        self.agent.dynamic_kb.get_statistics = Mock(return_value={
            "total_entries": 100
        })
        
        # 创建查询
        query = ContextQuery(
            query_id="test_summary",
            project_id="test_project",
            query_type="context_summary"
        )
        
        # 处理查询
        response = self.agent.process_query(query)
        
        assert response.success is True
        assert "project_context" in response.result
        assert "dialogue_tracking" in response.result
        assert "knowledge_base" in response.result
        assert "agent_performance" in response.result
    
    def test_unsupported_query_type(self):
        """测试不支持的查询类型"""
        query = ContextQuery(
            query_id="test_unsupported",
            project_id="test_project",
            query_type="unsupported_type"
        )
        
        response = self.agent.process_query(query)
        
        assert response.success is False
        assert "不支持的查询类型" in response.error_message
    
    def test_performance_metrics_update(self):
        """测试性能指标更新"""
        initial_total = self.agent.performance_metrics["total_queries"]
        
        # 模拟成功查询
        self.agent._update_performance_metrics("test_type", 100.0, True)
        
        assert self.agent.performance_metrics["total_queries"] == initial_total + 1
        assert self.agent.performance_metrics["successful_queries"] == 1
        assert "test_type" in self.agent.performance_metrics["query_types"]
    
    def test_agent_status(self):
        """测试 Agent 状态获取"""
        status = self.agent.get_agent_status()
        
        assert "agent_id" in status
        assert "active_sessions" in status
        assert "performance_metrics" in status
        assert "supported_query_types" in status
        assert status["agent_id"] == "test_agent"
    
    def test_metrics_reset(self):
        """测试指标重置"""
        # 先更新一些指标
        self.agent._update_performance_metrics("test_type", 100.0, True)
        
        # 重置指标
        self.agent.reset_metrics()
        
        assert self.agent.performance_metrics["total_queries"] == 0
        assert self.agent.performance_metrics["successful_queries"] == 0
        assert len(self.agent.performance_metrics["query_types"]) == 0


class TestContextTools:
    """上下文工具测试"""
    
    def test_create_context_tools(self):
        """测试创建上下文工具"""
        tools = create_context_tools()
        
        assert len(tools) == 5
        
        tool_names = [tool["name"] for tool in tools]
        assert "infer_speaker" in tool_names
        assert "resolve_pronouns" in tool_names
        assert "get_cultural_adaptation" in tool_names
        assert "analyze_relationship" in tool_names
        assert "get_context_summary" in tool_names
        
        # 验证工具结构
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert "properties" in tool["parameters"]
            assert "required" in tool["parameters"]
    
    @patch('agents.context_agent.get_context_agent')
    def test_execute_context_tool_infer_speaker(self, mock_get_agent):
        """测试执行说话人推断工具"""
        # Mock Agent
        mock_agent = Mock()
        mock_response = ContextResponse(
            query_id="test",
            success=True,
            result={"inferred_speaker": "张三"},
            confidence=0.8,
            processing_time_ms=100
        )
        mock_agent.process_query = Mock(return_value=mock_response)
        mock_get_agent.return_value = mock_agent
        
        # 执行工具
        parameters = {
            "project_id": "test_project",
            "subtitle_entry": {
                "text": "测试文本",
                "speaker": None
            }
        }
        
        result = execute_context_tool("infer_speaker", parameters)
        
        assert result["success"] is True
        assert result["result"]["inferred_speaker"] == "张三"
        assert result["confidence"] == 0.8
    
    @patch('agents.context_agent.get_context_agent')
    def test_execute_context_tool_cultural_adaptation(self, mock_get_agent):
        """测试执行文化适配工具"""
        # Mock Agent
        mock_agent = Mock()
        mock_response = ContextResponse(
            query_id="test",
            success=True,
            result={
                "target_language": "en",
                "recommendations": ["使用正式语言"]
            },
            confidence=0.9
        )
        mock_agent.process_query = Mock(return_value=mock_response)
        mock_get_agent.return_value = mock_agent
        
        # 执行工具
        parameters = {
            "project_id": "test_project",
            "target_language": "en"
        }
        
        result = execute_context_tool("get_cultural_adaptation", parameters)
        
        assert result["success"] is True
        assert result["result"]["target_language"] == "en"
        assert "recommendations" in result["result"]
    
    def test_execute_unknown_tool(self):
        """测试执行未知工具"""
        result = execute_context_tool("unknown_tool", {})
        
        assert "error" in result
        assert "未知的工具" in result["error"]


class TestContextAgentIntegration:
    """上下文 Agent 集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.context_agent.get_context_manager'), \
             patch('agents.context_agent.get_dynamic_knowledge_manager'), \
             patch('agents.context_agent.get_dialogue_tracker'):
            self.agent = ContextAgent("integration_test")
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # Mock 所有依赖
        self.agent.context_manager.load_project_context = Mock()
        self.agent.context_manager.get_speaker_context = Mock(return_value={
            "speaker": "张三",
            "speaker_info": {"name": "张三"},
            "relationship": {"type": "friend"}
        })
        self.agent.context_tracker.start_session = Mock(return_value="session_123")
        self.agent.context_tracker.end_session = Mock()
        
        # 1. 开始会话
        session_id = self.agent.start_session("test_project")
        assert session_id in self.agent.active_sessions
        
        # 2. 处理说话人推断查询
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="我觉得这个计划很好",
            speaker=None
        )
        
        query = ContextQuery(
            query_id="workflow_test",
            project_id="test_project",
            query_type="speaker_inference",
            subtitle_entry=subtitle_entry
        )
        
        response = self.agent.process_query(query)
        assert response.success is True
        
        # 3. 检查性能指标
        assert self.agent.performance_metrics["total_queries"] == 1
        assert self.agent.performance_metrics["successful_queries"] == 1
        
        # 4. 结束会话
        self.agent.end_session(session_id)
        assert session_id not in self.agent.active_sessions


def test_global_instance():
    """测试全局实例"""
    agent = get_context_agent()
    assert isinstance(agent, ContextAgent)
    
    # 确保是单例
    agent2 = get_context_agent()
    assert agent is agent2