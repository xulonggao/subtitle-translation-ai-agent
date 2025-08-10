"""
英语翻译 Agent 测试
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from agents.english_translation_agent import (
    EnglishTranslationAgent, TranslationRequest, TranslationResult,
    TranslationStyle, TranslationQuality, get_english_translation_agent,
    translate_to_english
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestTranslationRequest:
    """翻译请求测试"""
    
    def test_translation_request_creation(self):
        """测试翻译请求创建"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="你好，世界！",
            speaker="张三"
        )
        
        request = TranslationRequest(
            request_id="test_request",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            style_preference=TranslationStyle.FORMAL
        )
        
        assert request.request_id == "test_request"
        assert request.project_id == "test_project"
        assert request.subtitle_entry == subtitle_entry
        assert request.style_preference == TranslationStyle.FORMAL
        assert request.target_language == "en"
        assert request.cultural_adaptation is True
        assert request.preserve_timing is True
        assert request.timestamp is not None
    
    def test_translation_request_defaults(self):
        """测试翻译请求默认值"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="测试文本",
            speaker="测试"
        )
        
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry
        )
        
        assert request.target_language == "en"
        assert request.style_preference is None
        assert request.context_window is None
        assert request.cultural_adaptation is True
        assert request.preserve_timing is True
        assert request.max_length is None


class TestTranslationResult:
    """翻译结果测试"""
    
    def test_translation_result_creation(self):
        """测试翻译结果创建"""
        result = TranslationResult(
            request_id="test_request",
            success=True,
            translated_text="Hello, world!",
            original_text="你好，世界！",
            quality_score=0.85
        )
        
        assert result.request_id == "test_request"
        assert result.success is True
        assert result.translated_text == "Hello, world!"
        assert result.original_text == "你好，世界！"
        assert result.quality_score == 0.85
        assert result.quality_level == TranslationQuality.GOOD
        assert result.character_count == len("Hello, world!")
        assert result.timestamp is not None
    
    def test_quality_level_assignment(self):
        """测试质量等级分配"""
        test_cases = [
            (0.95, TranslationQuality.EXCELLENT),
            (0.85, TranslationQuality.GOOD),
            (0.65, TranslationQuality.ACCEPTABLE),
            (0.45, TranslationQuality.POOR),
            (0.25, TranslationQuality.UNACCEPTABLE)
        ]
        
        for score, expected_level in test_cases:
            result = TranslationResult(
                request_id="test",
                success=True,
                quality_score=score
            )
            assert result.quality_level == expected_level
    
    def test_error_result(self):
        """测试错误结果"""
        result = TranslationResult(
            request_id="test_request",
            success=False,
            error_message="翻译失败"
        )
        
        assert result.success is False
        assert result.error_message == "翻译失败"
        assert result.translated_text is None
        assert result.quality_score == 0.0
        assert result.quality_level == TranslationQuality.UNACCEPTABLE


class TestEnglishTranslationAgent:
    """英语翻译 Agent 测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.english_translation_agent.get_context_agent'), \
             patch('agents.english_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = EnglishTranslationAgent()
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        assert self.agent.agent_id.startswith("english_agent_")
        assert "max_length_ratio" in self.agent.translation_config
        assert TranslationStyle.FORMAL in self.agent.system_prompts
        assert "参谋长" in self.agent.terminology_mappings
        assert "chinese_names" in self.agent.cultural_adaptations
        assert self.agent.performance_stats["total_translations"] == 0
    
    def test_request_validation(self):
        """测试请求验证"""
        # 有效请求
        valid_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="测试文本",
            speaker="测试"
        )
        
        valid_request = TranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=valid_entry
        )
        
        assert self.agent._validate_request(valid_request) is True
        
        # 无效请求 - 缺少文本
        invalid_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="",
            speaker="测试"
        )
        
        invalid_request = TranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=invalid_entry
        )
        
        assert self.agent._validate_request(invalid_request) is False
        
        # 无效请求 - 错误的目标语言
        wrong_lang_request = TranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=valid_entry,
            target_language="fr"
        )
        
        assert self.agent._validate_request(wrong_lang_request) is False
    
    def test_style_determination(self):
        """测试翻译风格确定"""
        # 指定风格的情况
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            style_preference=TranslationStyle.MILITARY
        )
        
        style = self.agent._determine_translation_style(request, {})
        assert style == TranslationStyle.MILITARY
        
        # 基于上下文推断 - 军事背景
        military_context = {
            "speaker_info": {
                "speaker_info": {"profession": "军官"}
            }
        }
        
        request_no_style = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock()
        )
        
        style = self.agent._determine_translation_style(request_no_style, military_context)
        assert style == TranslationStyle.MILITARY
        
        # 基于上下文推断 - 正式场合
        formal_context = {
            "relationship_info": {
                "relationship_summary": {"formality": "very_high"}
            }
        }
        
        style = self.agent._determine_translation_style(request_no_style, formal_context)
        assert style == TranslationStyle.FORMAL
    
    def test_military_context_detection(self):
        """测试军事背景检测"""
        # 基于说话人职业
        speaker_info = {
            "speaker_info": {"profession": "军官"}
        }
        cultural_info = {}
        
        assert self.agent._is_military_context(speaker_info, cultural_info) is True
        
        # 基于文化背景
        speaker_info = {}
        cultural_info = {
            "cultural_context": {"cultural_notes": ["军事题材"]}
        }
        
        assert self.agent._is_military_context(speaker_info, cultural_info) is True
        
        # 非军事背景
        assert self.agent._is_military_context({}, {}) is False
    
    def test_romantic_context_detection(self):
        """测试浪漫场景检测"""
        # 基于关系类型
        relationship_info = {
            "relationship_summary": {"relationship_type": "romantic"}
        }
        
        assert self.agent._is_romantic_context(relationship_info, "普通文本") is True
        
        # 基于文本关键词
        assert self.agent._is_romantic_context({}, "我爱你") is True
        assert self.agent._is_romantic_context({}, "想你了") is True
        assert self.agent._is_romantic_context({}, "普通对话") is False
    
    def test_dramatic_context_detection(self):
        """测试戏剧化场景检测"""
        assert self.agent._is_dramatic_context("什么！！") is True
        assert self.agent._is_dramatic_context("不可能？？") is True
        assert self.agent._is_dramatic_context("天哪！") is True
        assert self.agent._is_dramatic_context("普通对话") is False
    
    def test_terminology_mapping(self):
        """测试术语映射"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说司令要来检查",
            speaker="士兵"
        )
        
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry
        )
        
        terminology = self.agent._get_terminology_mappings(request, {})
        
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "Chief of Staff"
        assert "司令" in terminology
        assert terminology["司令"] == "Commander"
    
    def test_simulate_translation(self):
        """测试模拟翻译"""
        text = "你好，参谋长"
        style = TranslationStyle.MILITARY
        terminology = {"参谋长": "Chief of Staff"}
        
        result = self.agent._simulate_translation(text, style, terminology)
        
        assert "Chief of Staff" in result
        assert "Hello" in result or "Hi" in result
    
    def test_cultural_adaptations(self):
        """测试文化适配"""
        text = "我们去吃饺子庆祝春节"
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            cultural_adaptation=True
        )
        
        adapted = self.agent._apply_cultural_adaptations(text, request, {})
        
        assert "dumplings" in adapted
        assert "Chinese New Year" in adapted
    
    def test_text_compression(self):
        """测试文本压缩"""
        long_text = "This is a very long text that needs to be compressed because it exceeds the maximum length limit"
        max_length = 50
        
        compressed = self.agent._compress_text(long_text, max_length)
        
        assert len(compressed) <= max_length
        assert compressed.endswith("...") or len(compressed) < len(long_text)
    
    def test_readability_optimization(self):
        """测试可读性优化"""
        text = "hello world"
        optimized = self.agent._optimize_readability(text)
        
        assert optimized.startswith("H")  # 首字母大写
        assert optimized.endswith(".")    # 句末标点
    
    def test_timing_preservation_check(self):
        """测试时长保持检查"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="短文本",
            speaker="测试"
        )
        
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            preserve_timing=True
        )
        
        # 合理长度的翻译（比例在1.3以内）
        short_translation = "Short"  # 5个字符，比例约1.67，仍然超过1.3
        # 让我们用更合理的测试
        reasonable_translation = "Text"  # 4个字符，比例约1.33，接近但仍超过1.3
        # 实际上对于中文，英文通常会更长，让我们调整测试
        assert self.agent._check_timing_preservation(request, "Text") is False  # 实际上会失败
        
        # 让我们测试一个真正合理的情况
        # 对于3个中文字符，最多允许3*1.3=3.9个英文字符
        very_short_translation = "Hi"  # 2个字符，比例0.67
        assert self.agent._check_timing_preservation(request, very_short_translation) is True
        
        # 过长的翻译
        long_translation = "This is a very long translation that exceeds the reasonable length ratio"
        assert self.agent._check_timing_preservation(request, long_translation) is False
    
    def test_quality_assessment(self):
        """测试质量评估"""
        original = "你好，参谋长"
        translated = "Hello, Chief of Staff"
        
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text=original,
                speaker="士兵"
            )
        )
        
        score, details = self.agent._assess_translation_quality(original, translated, request)
        
        assert 0.0 <= score <= 1.0
        assert "factors" in details
        assert "weights" in details
        assert "overall_score" in details
        
        # 检查各个质量因子
        factors = details["factors"]
        assert "length_quality" in factors
        assert "terminology_consistency" in factors
        assert "fluency" in factors
        assert "completeness" in factors
        assert "style_consistency" in factors
    
    def test_length_quality_assessment(self):
        """测试长度质量评估"""
        original = "测试文本"
        
        # 理想长度比例（1.0-1.3之间）
        # "测试文本"是4个字符，理想翻译应该是4-5.2个字符
        good_translation = "Test"  # 4个字符，比例1.0
        score = self.agent._assess_length_quality(original, good_translation)
        assert score >= 0.8
        
        # 过长翻译
        long_translation = "This is a very long translation of the test text"
        score = self.agent._assess_length_quality(original, long_translation)
        assert score < 0.8
        
        # 过短翻译
        short_translation = "T"  # 1个字符，比例0.25
        score = self.agent._assess_length_quality(original, short_translation)
        assert score < 1.0
    
    def test_terminology_consistency_assessment(self):
        """测试术语一致性评估"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说司令要来",
            speaker="士兵"
        )
        
        request = TranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry
        )
        
        # 正确使用术语
        good_translation = "Chief of Staff says Commander is coming"
        score = self.agent._assess_terminology_consistency(good_translation, request)
        assert score == 1.0
        
        # 部分使用术语
        partial_translation = "Chief of Staff says 司令 is coming"
        score = self.agent._assess_terminology_consistency(partial_translation, request)
        assert 0.0 < score < 1.0
        
        # 未使用术语
        bad_translation = "参谋长 says 司令 is coming"
        score = self.agent._assess_terminology_consistency(bad_translation, request)
        assert score == 0.0
    
    def test_fluency_assessment(self):
        """测试流畅性评估"""
        # 流畅的翻译
        fluent_text = "Hello, how are you?"
        score = self.agent._assess_fluency(fluent_text)
        assert score >= 0.8
        
        # 有问题的翻译
        problematic_text = "Hello,  how  are you"  # 多余空格，缺少标点
        score = self.agent._assess_fluency(problematic_text)
        assert score < 1.0
        
        # 未翻译的文本
        untranslated_text = "[Translation needed: 你好]"
        score = self.agent._assess_fluency(untranslated_text)
        assert score <= 0.5
        
        # 空文本
        empty_text = ""
        score = self.agent._assess_fluency(empty_text)
        assert score == 0.0
    
    def test_performance_stats_update(self):
        """测试性能统计更新"""
        initial_total = self.agent.performance_stats["total_translations"]
        initial_successful = self.agent.performance_stats["successful_translations"]
        
        # 成功翻译
        self.agent._update_performance_stats(TranslationStyle.FORMAL, 0.8, 100.0, True)
        
        assert self.agent.performance_stats["total_translations"] == initial_total + 1
        assert self.agent.performance_stats["successful_translations"] == initial_successful + 1
        assert self.agent.performance_stats["average_quality_score"] > 0
        assert self.agent.performance_stats["average_processing_time"] > 0
        assert "formal" in self.agent.performance_stats["style_distribution"]
        
        # 失败翻译
        initial_errors = self.agent.performance_stats["error_count"]
        self.agent._update_performance_stats(None, 0.0, 200.0, False)
        
        assert self.agent.performance_stats["error_count"] == initial_errors + 1
    
    def test_agent_status(self):
        """测试 Agent 状态"""
        status = self.agent.get_agent_status()
        
        assert "agent_id" in status
        assert status["target_language"] == "en"
        assert "performance_stats" in status
        assert "supported_styles" in status
        assert "terminology_count" in status
        assert "cultural_adaptations" in status
        
        # 检查支持的风格
        supported_styles = status["supported_styles"]
        assert "formal" in supported_styles
        assert "military" in supported_styles
        assert "casual" in supported_styles
    
    def test_stats_reset(self):
        """测试统计重置"""
        # 先进行一些翻译以产生统计数据
        self.agent._update_performance_stats(TranslationStyle.FORMAL, 0.8, 100.0, True)
        
        assert self.agent.performance_stats["total_translations"] > 0
        
        # 重置统计
        self.agent.reset_stats()
        
        assert self.agent.performance_stats["total_translations"] == 0
        assert self.agent.performance_stats["successful_translations"] == 0
        assert self.agent.performance_stats["average_quality_score"] == 0.0
        assert self.agent.performance_stats["style_distribution"] == {}
    
    @patch('agents.english_translation_agent.get_context_agent')
    @patch('agents.english_translation_agent.get_dynamic_knowledge_manager')
    def test_full_translation_workflow(self, mock_kb, mock_context):
        """测试完整翻译流程"""
        # 模拟上下文 Agent 响应
        mock_context_agent = Mock()
        mock_context.return_value = mock_context_agent
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.result = {
            "speaker_info": {"profession": "军官"},
            "relationship_summary": {"formality": "high"}
        }
        mock_context_agent.process_query.return_value = mock_response
        
        # 模拟知识库响应
        mock_kb_manager = Mock()
        mock_kb.return_value = mock_kb_manager
        
        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = [{"参谋长": "Chief of Staff"}]
        mock_kb_manager.query_knowledge.return_value = mock_kb_result
        
        # 创建翻译请求
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长，任务完成",
            speaker="士兵"
        )
        
        request = TranslationRequest(
            request_id="test_full",
            project_id="test_project",
            subtitle_entry=subtitle_entry
        )
        
        # 执行翻译
        result = self.agent.translate(request)
        
        # 验证结果
        assert result.success is True
        assert result.translated_text is not None
        assert result.quality_score > 0
        assert result.style_applied is not None
        assert result.processing_time_ms > 0
        assert result.confidence > 0


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_english_translation_agent(self):
        """测试获取全局 Agent 实例"""
        agent1 = get_english_translation_agent()
        agent2 = get_english_translation_agent()
        
        # 应该返回同一个实例
        assert agent1 is agent2
        assert agent1.agent_id == agent2.agent_id
    
    @patch('agents.english_translation_agent.get_english_translation_agent')
    def test_translate_to_english_convenience_function(self, mock_get_agent):
        """测试便捷翻译函数"""
        # 模拟 Agent
        mock_agent = Mock()
        mock_result = TranslationResult(
            request_id="test",
            success=True,
            translated_text="Hello, world!",
            quality_score=0.8
        )
        mock_agent.translate.return_value = mock_result
        mock_get_agent.return_value = mock_agent
        
        # 创建测试数据
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="你好，世界！",
            speaker="测试"
        )
        
        # 调用便捷函数
        result = translate_to_english(
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            style=TranslationStyle.FORMAL
        )
        
        # 验证结果
        assert result.success is True
        assert result.translated_text == "Hello, world!"
        
        # 验证 Agent 被正确调用
        mock_agent.translate.assert_called_once()
        call_args = mock_agent.translate.call_args[0][0]
        assert call_args.project_id == "test_project"
        assert call_args.subtitle_entry == subtitle_entry
        assert call_args.style_preference == TranslationStyle.FORMAL


class TestTranslationIntegration:
    """翻译集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.english_translation_agent.get_context_agent'), \
             patch('agents.english_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = EnglishTranslationAgent()
    
    def test_military_translation_integration(self):
        """测试军事翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="是，参谋长！",
            speaker="士兵"
        )
        
        request = TranslationRequest(
            request_id="military_test",
            project_id="military_project",
            subtitle_entry=subtitle_entry,
            style_preference=TranslationStyle.MILITARY
        )
        
        # 模拟上下文分析结果
        context_info = {
            "speaker_info": {
                "speaker_info": {"profession": "士兵"}
            },
            "relationship_info": {
                "relationship_summary": {"formality": "very_high"}
            }
        }
        
        # 测试风格确定
        style = self.agent._determine_translation_style(request, context_info)
        assert style == TranslationStyle.MILITARY
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, context_info)
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "Chief of Staff"
        
        # 测试翻译
        translated = self.agent._simulate_translation(
            subtitle_entry.text, style, terminology
        )
        assert "Chief of Staff" in translated
    
    def test_casual_translation_integration(self):
        """测试随意翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="嗨，朋友！",
            speaker="张三"
        )
        
        request = TranslationRequest(
            request_id="casual_test",
            project_id="casual_project",
            subtitle_entry=subtitle_entry,
            style_preference=TranslationStyle.CASUAL
        )
        
        context_info = {
            "relationship_info": {
                "relationship_summary": {"formality": "low"}
            }
        }
        
        # 测试风格确定
        style = self.agent._determine_translation_style(request, context_info)
        assert style == TranslationStyle.CASUAL
        
        # 测试翻译
        terminology = self.agent._get_terminology_mappings(request, context_info)
        translated = self.agent._simulate_translation(
            subtitle_entry.text, style, terminology
        )
        
        # 随意风格应该使用更口语化的表达
        assert "Hi" in translated or "Hello" in translated
    
    def test_cultural_adaptation_integration(self):
        """测试文化适配集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="我们一起吃饺子庆祝春节吧！",
            speaker="妈妈"
        )
        
        request = TranslationRequest(
            request_id="cultural_test",
            project_id="cultural_project",
            subtitle_entry=subtitle_entry,
            cultural_adaptation=True
        )
        
        # 测试文化适配
        adapted_text = self.agent._apply_cultural_adaptations(
            subtitle_entry.text, request, {}
        )
        
        assert "dumplings" in adapted_text
        assert "Chinese New Year" in adapted_text
    
    def test_quality_assessment_integration(self):
        """测试质量评估集成"""
        original = "参谋长，任务完成！"
        translated = "Chief of Staff, mission accomplished!"
        
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text=original,
            speaker="士兵"
        )
        
        request = TranslationRequest(
            request_id="quality_test",
            project_id="quality_project",
            subtitle_entry=subtitle_entry
        )
        
        score, details = self.agent._assess_translation_quality(
            original, translated, request
        )
        
        # 这应该是一个高质量的翻译
        assert score > 0.7
        assert details["factors"]["terminology_consistency"] == 1.0
        assert details["factors"]["completeness"] == 1.0
        assert details["factors"]["fluency"] >= 0.8