"""
翻译协调 Agent 测试
"""
import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from agents.translation_coordinator_agent import (
    TranslationCoordinatorAgent, CoordinationRequest, CoordinationResult,
    CoordinationStatus, QualityThreshold
)
from agents.translation_scheduler import TaskPriority
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationResult


class TestTranslationCoordinatorAgent(unittest.TestCase):
    """翻译协调 Agent 测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.coordinator = TranslationCoordinatorAgent("test_coordinator")
        
        # 创建测试字幕数据
        self.test_subtitles = [
            SubtitleEntry(
                index=1,
                start_time=0.0,
                end_time=2.0,
                text="你好，欢迎来到我们的节目。",
                speaker="主持人"
            ),
            SubtitleEntry(
                index=2,
                start_time=2.0,
                end_time=4.0,
                text="今天我们要讨论军事技术的发展。",
                speaker="专家"
            ),
            SubtitleEntry(
                index=3,
                start_time=4.0,
                end_time=6.0,
                text="雷达系统在现代战争中起着重要作用。",
                speaker="专家"
            )
        ]
    
    def tearDown(self):
        """清理测试环境"""
        asyncio.run(self.coordinator.shutdown())
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.coordinator.scheduler)
        self.assertIsNotNone(self.coordinator.terminology_manager)
        self.assertIsNotNone(self.coordinator.monitoring_system)
        self.assertIsNotNone(self.coordinator.translation_agents)
        self.assertEqual(self.coordinator.current_status, CoordinationStatus.IDLE)
    
    def test_create_coordination_request(self):
        """测试创建协调请求"""
        request = CoordinationRequest(
            request_id="test_request_1",
            project_id="test_project",
            subtitle_entries=self.test_subtitles,
            target_languages=["en", "ja", "ko"],
            quality_threshold=0.8,
            priority=TaskPriority.HIGH
        )
        
        self.assertEqual(request.request_id, "test_request_1")
        self.assertEqual(request.project_id, "test_project")
        self.assertEqual(len(request.subtitle_entries), 3)
        self.assertEqual(len(request.target_languages), 3)
        self.assertEqual(request.quality_threshold, 0.8)
        self.assertEqual(request.priority, TaskPriority.HIGH)
    
    def test_analyze_subtitle_content(self):
        """测试字幕内容分析"""
        analysis = self.coordinator._analyze_subtitle_content(self.test_subtitles)
        
        self.assertEqual(analysis["total_entries"], 3)
        self.assertGreater(analysis["total_characters"], 0)
        self.assertGreater(analysis["total_duration"], 0)
        self.assertIn("military", analysis["content_types"])
        self.assertGreater(analysis["complexity_score"], 0)
    
    def test_determine_translation_strategy(self):
        """测试翻译策略确定"""
        target_languages = ["en", "ja", "ko"]
        content_analysis = {
            "total_entries": 3,
            "complexity_score": 0.6,
            "content_types": ["military"]
        }
        
        strategy = self.coordinator._determine_translation_strategy(
            target_languages, content_analysis
        )
        
        self.assertTrue(strategy["parallel_processing"])
        self.assertTrue(strategy["technical_accuracy_required"])
        self.assertIn("agent_assignment", strategy)
        self.assertIn("batch_size", strategy)
    
    def test_assign_agents_to_languages(self):
        """测试 Agent 分配"""
        languages = ["en", "ja", "ko", "es", "ar"]
        assignment = self.coordinator._assign_agents_to_languages(languages)
        
        self.assertEqual(assignment["en"], "english")
        self.assertEqual(assignment["ja"], "asian")
        self.assertEqual(assignment["ko"], "asian")
        self.assertEqual(assignment["es"], "european_arabic")
        self.assertEqual(assignment["ar"], "european_arabic")
    
    def test_create_task_groups(self):
        """测试任务分组创建"""
        target_languages = ["en", "ja"]
        strategy = {
            "batch_size": 2,
            "agent_assignment": {"en": "english", "ja": "asian"},
            "quality_priority": False,
            "cultural_adaptation_required": False,
            "technical_accuracy_required": True
        }
        
        task_groups = self.coordinator._create_task_groups(
            self.test_subtitles, target_languages, strategy
        )
        
        # 应该有4个任务组：2个批次 × 2种语言
        self.assertEqual(len(task_groups), 4)
        
        # 检查任务组结构
        for group in task_groups:
            self.assertIn("group_id", group)
            self.assertIn("subtitle_entries", group)
            self.assertIn("target_language", group)
            self.assertIn("agent_type", group)
            self.assertIn("special_requirements", group)
    
    def test_estimate_resource_requirements(self):
        """测试资源需求估算"""
        task_groups = [
            {"subtitle_entries": self.test_subtitles[:2], "target_language": "en"},
            {"subtitle_entries": self.test_subtitles[2:], "target_language": "ja"}
        ]
        
        requirements = self.coordinator._estimate_resource_requirements(task_groups)
        
        self.assertEqual(requirements["total_tasks"], 2)
        self.assertEqual(requirements["total_entries"], 3)
        self.assertEqual(requirements["total_languages"], 2)
        self.assertGreater(requirements["estimated_time_seconds"], 0)
        self.assertGreater(requirements["estimated_memory_mb"], 0)
    
    def test_calculate_complexity_score(self):
        """测试复杂度分数计算"""
        # 简单内容
        simple_subtitles = [
            SubtitleEntry(1, 0.0, 2.0, "你好", "A"),
            SubtitleEntry(2, 2.0, 4.0, "再见", "B")
        ]
        simple_score = self.coordinator._calculate_complexity_score(simple_subtitles)
        
        # 复杂内容
        complex_subtitles = [
            SubtitleEntry(1, 0.0, 2.0, "这是一个非常复杂的技术系统，需要专业的军事知识来理解", "专家"),
            SubtitleEntry(2, 2.0, 4.0, "传统文化中的礼仪习俗让我感到非常激动和感动", "学者")
        ]
        complex_score = self.coordinator._calculate_complexity_score(complex_subtitles)
        
        self.assertLess(simple_score, complex_score)
        self.assertLessEqual(complex_score, 1.0)
    
    def test_check_honorific_usage(self):
        """测试敬语使用检查"""
        # 包含敬语的结果
        honorific_results = [
            Mock(translated_text="こんにちはです"),
            Mock(translated_text="ありがとうございます"),
            Mock(translated_text="田中さん")
        ]
        
        # 不包含敬语的结果
        casual_results = [
            Mock(translated_text="こんにちは"),
            Mock(translated_text="ありがとう"),
            Mock(translated_text="田中")
        ]
        
        self.assertTrue(self.coordinator._check_honorific_usage(honorific_results))
        self.assertFalse(self.coordinator._check_honorific_usage(casual_results))
    
    def test_check_length_consistency(self):
        """测试长度一致性检查"""
        # 创建模拟翻译结果
        results = [
            Mock(translated_text="Hello, welcome to our program."),  # 长度合适
            Mock(translated_text="Today we discuss military tech."),  # 长度合适
            Mock(translated_text="Radar systems are very important in modern warfare and play a crucial role.")  # 过长
        ]
        
        consistency_score = self.coordinator._check_length_consistency(results, self.test_subtitles)
        
        self.assertGreater(consistency_score, 0)
        self.assertLessEqual(consistency_score, 1.0)
    
    @patch('agents.translation_coordinator_agent.TranslationCoordinatorAgent._execute_translation_plan')
    @patch('agents.translation_coordinator_agent.TranslationCoordinatorAgent._perform_quality_check')
    @patch('agents.translation_coordinator_agent.TranslationCoordinatorAgent._check_terminology_consistency')
    def test_coordinate_translation_success(self, mock_consistency, mock_quality, mock_execute):
        """测试成功的翻译协调"""
        # 设置模拟返回值
        mock_execute.return_value = {
            "en": [Mock(success=True, translated_text="Hello", quality_score=0.9)],
            "ja": [Mock(success=True, translated_text="こんにちは", quality_score=0.85)]
        }
        mock_quality.return_value = {"en": 0.9, "ja": 0.85}
        mock_consistency.return_value = Mock(
            consistency_score=0.8,
            conflicting_terms_count=0,
            success=True
        )
        
        # 创建协调请求
        request = CoordinationRequest(
            request_id="test_success",
            project_id="test_project",
            subtitle_entries=self.test_subtitles[:1],  # 只用一个字幕测试
            target_languages=["en", "ja"],
            quality_threshold=0.8
        )
        
        # 执行协调
        result = asyncio.run(self.coordinator.coordinate_translation(request))
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.translation_results), 2)
        self.assertEqual(len(result.quality_scores), 2)
        self.assertGreater(result.total_processing_time_ms, 0)
    
    def test_get_coordination_status(self):
        """测试获取协调状态"""
        # 测试整体状态
        status = asyncio.run(self.coordinator.get_coordination_status())
        
        self.assertIn("agent_id", status)
        self.assertIn("current_status", status)
        self.assertIn("active_requests_count", status)
        self.assertIn("performance_stats", status)
    
    def test_update_configuration(self):
        """测试配置更新"""
        config_updates = {
            "max_concurrent_tasks": 10,
            "default_quality_threshold": 0.9,
            "consistency_check_enabled": False
        }
        
        result = asyncio.run(self.coordinator.update_configuration(config_updates))
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["updated_fields"]), 3)
        self.assertEqual(self.coordinator.max_concurrent_tasks, 10)
        self.assertEqual(self.coordinator.default_quality_threshold, 0.9)
        self.assertFalse(self.coordinator.consistency_check_enabled)
    
    def test_get_translation_agents_status(self):
        """测试获取翻译 Agent 状态"""
        status = asyncio.run(self.coordinator.get_translation_agents_status())
        
        self.assertIn("total_agents", status)
        self.assertIn("agents", status)
        self.assertEqual(status["total_agents"], len(self.coordinator.translation_agents))
        
        # 检查每个 Agent 的状态
        for agent_type in ["english", "asian", "european_arabic"]:
            self.assertIn(agent_type, status["agents"])
            agent_status = status["agents"][agent_type]
            self.assertIn("agent_type", agent_status)
            self.assertIn("status", agent_status)
    
    def test_performance_stats_update(self):
        """测试性能统计更新"""
        # 创建模拟请求和结果
        request = CoordinationRequest(
            request_id="test_stats",
            project_id="test_project",
            subtitle_entries=self.test_subtitles,
            target_languages=["en", "ja"]
        )
        
        result = CoordinationResult(
            request_id="test_stats",
            success=True,
            translation_results={"en": [], "ja": []},
            quality_scores={"en": 0.9, "ja": 0.85},
            total_processing_time_ms=1000
        )
        
        # 更新统计
        initial_requests = self.coordinator.performance_stats["total_requests"]
        self.coordinator._update_performance_stats(request, result)
        
        # 验证统计更新
        self.assertEqual(
            self.coordinator.performance_stats["total_requests"],
            initial_requests + 1
        )
        self.assertEqual(
            self.coordinator.performance_stats["successful_requests"],
            1
        )
        self.assertIn("en", self.coordinator.performance_stats["languages_processed"])
        self.assertIn("ja", self.coordinator.performance_stats["languages_processed"])


class TestCoordinationDataModels(unittest.TestCase):
    """协调数据模型测试"""
    
    def test_coordination_request_creation(self):
        """测试协调请求创建"""
        subtitles = [SubtitleEntry(1, 0.0, 2.0, "测试", "A")]
        
        request = CoordinationRequest(
            request_id="test_req",
            project_id="test_proj",
            subtitle_entries=subtitles,
            target_languages=["en", "ja"]
        )
        
        self.assertEqual(request.request_id, "test_req")
        self.assertEqual(request.project_id, "test_proj")
        self.assertEqual(len(request.subtitle_entries), 1)
        self.assertEqual(len(request.target_languages), 2)
        self.assertEqual(request.quality_threshold, 0.8)  # 默认值
        self.assertEqual(request.priority, TaskPriority.NORMAL)  # 默认值
        self.assertIsNotNone(request.created_at)
    
    def test_coordination_result_creation(self):
        """测试协调结果创建"""
        result = CoordinationResult(
            request_id="test_result",
            success=True,
            translation_results={"en": [], "ja": []},
            quality_scores={"en": 0.9, "ja": 0.85}
        )
        
        self.assertEqual(result.request_id, "test_result")
        self.assertTrue(result.success)
        self.assertEqual(len(result.translation_results), 2)
        self.assertEqual(len(result.quality_scores), 2)
        self.assertEqual(result.tasks_completed, 0)  # 默认值
        self.assertEqual(result.tasks_failed, 0)  # 默认值
        self.assertIsNotNone(result.completed_at)
        self.assertIsInstance(result.recommendations, list)


if __name__ == '__main__':
    unittest.main()