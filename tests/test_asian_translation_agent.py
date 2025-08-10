"""
亚洲语言翻译 Agent 群测试
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from agents.asian_translation_agent import (
    AsianTranslationAgent, AsianTranslationRequest, AsianTranslationResult,
    AsianLanguage, HonorificLevel, CulturalContext, get_asian_translation_agent,
    translate_to_asian_language
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestAsianTranslationRequest:
    """亚洲语言翻译请求测试"""
    
    def test_translation_request_creation(self):
        """测试翻译请求创建"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="你好，世界！",
            speaker="张三"
        )
        
        request = AsianTranslationRequest(
            request_id="test_request",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE,
            honorific_level=HonorificLevel.HIGH
        )
        
        assert request.request_id == "test_request"
        assert request.project_id == "test_project"
        assert request.subtitle_entry == subtitle_entry
        assert request.target_language == AsianLanguage.JAPANESE
        assert request.honorific_level == HonorificLevel.HIGH
        assert request.preserve_honorifics is True
        assert request.adapt_cultural_references is True
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
        
        request = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.KOREAN
        )
        
        assert request.target_language == AsianLanguage.KOREAN
        assert request.honorific_level is None
        assert request.cultural_context is None
        assert request.context_window is None
        assert request.preserve_honorifics is True
        assert request.adapt_cultural_references is True
        assert request.maintain_formality is True


class TestAsianTranslationResult:
    """亚洲语言翻译结果测试"""
    
    def test_translation_result_creation(self):
        """测试翻译结果创建"""
        result = AsianTranslationResult(
            request_id="test_request",
            success=True,
            target_language=AsianLanguage.JAPANESE,
            translated_text="こんにちは、世界！",
            original_text="你好，世界！",
            honorific_level_used=HonorificLevel.HIGH,
            quality_score=0.85
        )
        
        assert result.request_id == "test_request"
        assert result.success is True
        assert result.target_language == AsianLanguage.JAPANESE
        assert result.translated_text == "こんにちは、世界！"
        assert result.original_text == "你好，世界！"
        assert result.honorific_level_used == HonorificLevel.HIGH
        assert result.quality_score == 0.85
        assert result.character_count == len("こんにちは、世界！")
        assert result.timestamp is not None
    
    def test_error_result(self):
        """测试错误结果"""
        result = AsianTranslationResult(
            request_id="test_request",
            success=False,
            target_language=AsianLanguage.THAI,
            error_message="翻译失败"
        )
        
        assert result.success is False
        assert result.target_language == AsianLanguage.THAI
        assert result.error_message == "翻译失败"
        assert result.translated_text is None
        assert result.quality_score == 0.0


class TestAsianTranslationAgent:
    """亚洲语言翻译 Agent 测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.asian_translation_agent.get_context_agent'), \
             patch('agents.asian_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = AsianTranslationAgent()
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        assert self.agent.agent_id.startswith("asian_agent_")
        assert len(self.agent.language_configs) == 6  # 6种亚洲语言
        assert AsianLanguage.JAPANESE in self.agent.language_configs
        assert AsianLanguage.KOREAN in self.agent.language_configs
        assert AsianLanguage.THAI in self.agent.language_configs
        assert AsianLanguage.VIETNAMESE in self.agent.language_configs
        assert AsianLanguage.INDONESIAN in self.agent.language_configs
        assert AsianLanguage.MALAY in self.agent.language_configs
        assert self.agent.performance_stats["total_translations"] == 0
    
    def test_supported_languages(self):
        """测试支持的语言列表"""
        languages = self.agent.get_supported_languages()
        
        assert len(languages) == 6
        
        # 检查日语配置
        japanese = next(lang for lang in languages if lang["code"] == "ja")
        assert japanese["name"] == "日语"
        assert japanese["honorific_system"] is True
        assert japanese["cultural_context"] == "confucian"
        
        # 检查印尼语配置
        indonesian = next(lang for lang in languages if lang["code"] == "id")
        assert indonesian["name"] == "印尼语"
        assert indonesian["honorific_system"] is False
        assert indonesian["cultural_context"] == "islamic"
    
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
        
        valid_request = AsianTranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=valid_entry,
            target_language=AsianLanguage.JAPANESE
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
        
        invalid_request = AsianTranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=invalid_entry,
            target_language=AsianLanguage.JAPANESE
        )
        
        assert self.agent._validate_request(invalid_request) is False
    
    def test_honorific_level_determination(self):
        """测试敬语等级确定"""
        # 指定敬语等级的情况
        request = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=AsianLanguage.JAPANESE,
            honorific_level=HonorificLevel.VERY_HIGH
        )
        
        level = self.agent._determine_honorific_level(request, {})
        assert level == HonorificLevel.VERY_HIGH
        
        # 基于上下文推断 - 军事背景
        military_context = {
            "speaker_info": {
                "speaker_info": {"profession": "军官"}
            }
        }
        
        request_no_level = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=AsianLanguage.KOREAN
        )
        
        level = self.agent._determine_honorific_level(request_no_level, military_context)
        assert level == HonorificLevel.VERY_HIGH
        
        # 不支持敬语系统的语言
        request_indonesian = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=AsianLanguage.INDONESIAN
        )
        
        level = self.agent._determine_honorific_level(request_indonesian, {})
        assert level is None  
  
    def test_terminology_mapping(self):
        """测试术语映射"""
        # 日语术语映射
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说司令要来检查",
            speaker="士兵"
        )
        
        request = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE
        )
        
        terminology = self.agent._get_terminology_mappings(request, {})
        
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "参謀長"
        assert "司令" in terminology
        assert terminology["司令"] == "司令官"
        
        # 韩语术语映射
        request_korean = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.KOREAN
        )
        
        terminology_korean = self.agent._get_terminology_mappings(request_korean, {})
        
        assert "参谋长" in terminology_korean
        assert terminology_korean["参谋长"] == "참모장"
        assert "司令" in terminology_korean
        assert terminology_korean["司令"] == "사령관"
    
    def test_simulate_translation(self):
        """测试模拟翻译"""
        # 日语翻译
        text = "你好，参谋长"
        terminology = {"参谋长": "参謀長"}
        
        result = self.agent._simulate_translation(
            text, AsianLanguage.JAPANESE, HonorificLevel.HIGH, terminology
        )
        
        assert "参謀長" in result
        assert "です" in result  # 敬语标记
        
        # 韩语翻译
        result_korean = self.agent._simulate_translation(
            text, AsianLanguage.KOREAN, HonorificLevel.HIGH, terminology
        )
        
        assert "습니다" in result_korean  # 敬语标记
        
        # 印尼语翻译（无敬语系统）
        result_indonesian = self.agent._simulate_translation(
            text, AsianLanguage.INDONESIAN, None, {}
        )
        
        # 印尼语应该包含术语映射的结果
        assert "kepala staf" in result_indonesian  # "参谋长" -> "kepala staf"
    
    def test_cultural_adaptations(self):
        """测试文化适配"""
        # 儒家文化圈适配（日语）
        text = "父亲说母亲很关心你"
        request = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=AsianLanguage.JAPANESE,
            adapt_cultural_references=True
        )
        
        adapted = self.agent._apply_cultural_adaptations(text, request, {})
        
        assert "お父さん" in adapted
        assert "お母さん" in adapted
        
        # 伊斯兰文化适配（印尼语）
        text_islamic = "上帝保佑，我们去祈祷"
        request_indonesian = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=AsianLanguage.INDONESIAN,
            adapt_cultural_references=True
        )
        
        adapted_indonesian = self.agent._apply_cultural_adaptations(text_islamic, request_indonesian, {})
        
        assert "Allah" in adapted_indonesian
        assert "sholat" in adapted_indonesian
    
    def test_length_quality_assessment(self):
        """测试长度质量评估"""
        original = "测试文本"
        
        # 日语 - 理想长度比例（1.1倍）
        good_translation = "テスト文本"  # 5个字符，比例1.25，在合理范围内
        score = self.agent._assess_length_quality(original, good_translation, AsianLanguage.JAPANESE)
        assert score >= 0.8
        
        # 泰语 - 较长的翻译（1.4倍允许范围）
        # "测试文本"是4个字符，泰语允许1.4倍，即5.6个字符
        thai_translation = "ทดสอบ"  # 4个字符，比例1.0，应该得高分
        score_thai = self.agent._assess_length_quality(original, thai_translation, AsianLanguage.THAI)
        assert score_thai >= 0.8
        
        # 过长翻译
        long_translation = "这是一个非常长的翻译文本，超出了合理的长度范围"
        score_long = self.agent._assess_length_quality(original, long_translation, AsianLanguage.JAPANESE)
        assert score_long < 0.6
    
    def test_terminology_consistency_assessment(self):
        """测试术语一致性评估"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说司令要来",
            speaker="士兵"
        )
        
        request = AsianTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE
        )
        
        # 正确使用术语
        good_translation = "参謀長が司令官が来ると言った"
        score = self.agent._assess_terminology_consistency(good_translation, request)
        assert score == 1.0
        
        # 部分使用术语
        partial_translation = "参謀長が司令が来ると言った"
        score = self.agent._assess_terminology_consistency(partial_translation, request)
        assert 0.0 < score < 1.0
        
        # 未使用术语
        bad_translation = "参谋长が司令が来ると言った"
        score = self.agent._assess_terminology_consistency(bad_translation, request)
        assert score == 0.0
    
    def test_performance_stats_update(self):
        """测试性能统计更新"""
        initial_total = self.agent.performance_stats["total_translations"]
        initial_successful = self.agent.performance_stats["successful_translations"]
        
        # 成功翻译
        self.agent._update_performance_stats(
            AsianLanguage.JAPANESE, HonorificLevel.HIGH, 0.8, 100.0, True
        )
        
        assert self.agent.performance_stats["total_translations"] == initial_total + 1
        assert self.agent.performance_stats["successful_translations"] == initial_successful + 1
        assert self.agent.performance_stats["average_quality_score"] > 0
        assert self.agent.performance_stats["average_processing_time"] > 0
        assert "ja" in self.agent.performance_stats["language_distribution"]
        assert "high" in self.agent.performance_stats["honorific_distribution"]
        
        # 失败翻译
        initial_errors = self.agent.performance_stats["error_count"]
        self.agent._update_performance_stats(
            AsianLanguage.KOREAN, None, 0.0, 200.0, False
        )
        
        assert self.agent.performance_stats["error_count"] == initial_errors + 1
    
    def test_agent_status(self):
        """测试 Agent 状态"""
        status = self.agent.get_agent_status()
        
        assert "agent_id" in status
        assert status["supported_languages"] == 6
        assert "ja" in status["language_list"]
        assert "ko" in status["language_list"]
        assert "th" in status["language_list"]
        assert "vi" in status["language_list"]
        assert "id" in status["language_list"]
        assert "ms" in status["language_list"]
        assert "performance_stats" in status
        assert "honorific_levels" in status
        assert "cultural_contexts" in status
    
    def test_stats_reset(self):
        """测试统计重置"""
        # 先进行一些翻译以产生统计数据
        self.agent._update_performance_stats(
            AsianLanguage.JAPANESE, HonorificLevel.HIGH, 0.8, 100.0, True
        )
        
        assert self.agent.performance_stats["total_translations"] > 0
        
        # 重置统计
        self.agent.reset_stats()
        
        assert self.agent.performance_stats["total_translations"] == 0
        assert self.agent.performance_stats["successful_translations"] == 0
        assert self.agent.performance_stats["average_quality_score"] == 0.0
        assert self.agent.performance_stats["language_distribution"] == {}
        assert self.agent.performance_stats["honorific_distribution"] == {}


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_asian_translation_agent(self):
        """测试获取全局 Agent 实例"""
        agent1 = get_asian_translation_agent()
        agent2 = get_asian_translation_agent()
        
        # 应该返回同一个实例
        assert agent1 is agent2
        assert agent1.agent_id == agent2.agent_id
    
    @patch('agents.asian_translation_agent.get_asian_translation_agent')
    def test_translate_to_asian_language_convenience_function(self, mock_get_agent):
        """测试便捷翻译函数"""
        # 模拟 Agent
        mock_agent = Mock()
        mock_result = AsianTranslationResult(
            request_id="test",
            success=True,
            target_language=AsianLanguage.JAPANESE,
            translated_text="こんにちは、世界！",
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
        result = translate_to_asian_language(
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE,
            honorific_level=HonorificLevel.HIGH
        )
        
        # 验证结果
        assert result.success is True
        assert result.translated_text == "こんにちは、世界！"
        
        # 验证 Agent 被正确调用
        mock_agent.translate.assert_called_once()
        call_args = mock_agent.translate.call_args[0][0]
        assert call_args.project_id == "test_project"
        assert call_args.subtitle_entry == subtitle_entry
        assert call_args.target_language == AsianLanguage.JAPANESE
        assert call_args.honorific_level == HonorificLevel.HIGH


class TestLanguageSpecificTranslation:
    """语言特定翻译测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.asian_translation_agent.get_context_agent'), \
             patch('agents.asian_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = AsianTranslationAgent()
    
    def test_japanese_translation_integration(self):
        """测试日语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="是，参谋长！",
            speaker="士兵"
        )
        
        request = AsianTranslationRequest(
            request_id="japanese_test",
            project_id="military_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE,
            honorific_level=HonorificLevel.VERY_HIGH
        )
        
        # 测试敬语等级确定
        context_info = {
            "speaker_info": {
                "speaker_info": {"profession": "士兵"}
            },
            "relationship_info": {
                "relationship_summary": {"formality": "very_high"}
            }
        }
        
        level = self.agent._determine_honorific_level(request, context_info)
        assert level == HonorificLevel.VERY_HIGH
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, context_info)
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "参謀長"
        
        # 测试翻译
        translated = self.agent._simulate_translation(
            subtitle_entry.text, AsianLanguage.JAPANESE, level, terminology
        )
        assert "参謀長" in translated
        assert "です" in translated  # 敬语标记
    
    def test_korean_translation_integration(self):
        """测试韩语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="哥，你好吗？",
            speaker="妹妹"
        )
        
        request = AsianTranslationRequest(
            request_id="korean_test",
            project_id="family_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.KOREAN,
            honorific_level=HonorificLevel.MEDIUM
        )
        
        context_info = {
            "relationship_info": {
                "relationship_summary": {"relationship_type": "family"}
            }
        }
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, context_info)
        assert "哥" in terminology
        assert terminology["哥"] == "오빠/형"
        
        # 测试翻译
        translated = self.agent._simulate_translation(
            subtitle_entry.text, AsianLanguage.KOREAN, HonorificLevel.MEDIUM, terminology
        )
        assert "오빠/형" in translated
    
    def test_thai_translation_integration(self):
        """测试泰语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="长官，任务完成！",
            speaker="士兵"
        )
        
        request = AsianTranslationRequest(
            request_id="thai_test",
            project_id="military_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.THAI
        )
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "长官" in terminology
        assert terminology["长官"] == "ท่านผู้บังคับบัญชา"
        assert "任务" in terminology
        assert terminology["任务"] == "ภารกิจ"
    
    def test_vietnamese_translation_integration(self):
        """测试越南语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="朋友，你好！",
            speaker="张三"
        )
        
        request = AsianTranslationRequest(
            request_id="vietnamese_test",
            project_id="casual_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.VIETNAMESE
        )
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "朋友" in terminology
        assert terminology["朋友"] == "bạn"
    
    def test_indonesian_translation_integration(self):
        """测试印尼语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="老板，我们开始工作吧",
            speaker="员工"
        )
        
        request = AsianTranslationRequest(
            request_id="indonesian_test",
            project_id="office_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.INDONESIAN
        )
        
        # 印尼语不支持敬语系统
        level = self.agent._determine_honorific_level(request, {})
        assert level is None
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "老板" in terminology
        assert terminology["老板"] == "bos"
    
    def test_malay_translation_integration(self):
        """测试马来语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="同事们，大家好！",
            speaker="经理"
        )
        
        request = AsianTranslationRequest(
            request_id="malay_test",
            project_id="office_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.MALAY
        )
        
        # 马来语不支持敬语系统
        level = self.agent._determine_honorific_level(request, {})
        assert level is None
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "同事" in terminology
        assert terminology["同事"] == "rakan sekerja"
    
    def test_cultural_context_adaptation(self):
        """测试文化背景适配"""
        # 儒家文化圈（日语）
        japanese_config = self.agent.language_configs[AsianLanguage.JAPANESE]
        assert japanese_config["cultural_context"] == CulturalContext.CONFUCIAN
        
        # 伊斯兰文化（印尼语）
        indonesian_config = self.agent.language_configs[AsianLanguage.INDONESIAN]
        assert indonesian_config["cultural_context"] == CulturalContext.ISLAMIC
        
        # 上座部佛教文化（泰语）
        thai_config = self.agent.language_configs[AsianLanguage.THAI]
        assert thai_config["cultural_context"] == CulturalContext.THERAVADA
    
    def test_honorific_system_support(self):
        """测试敬语系统支持"""
        # 支持敬语系统的语言
        honorific_languages = [
            AsianLanguage.JAPANESE,
            AsianLanguage.KOREAN,
            AsianLanguage.THAI,
            AsianLanguage.VIETNAMESE
        ]
        
        for lang in honorific_languages:
            config = self.agent.language_configs[lang]
            assert config["honorific_system"] is True
        
        # 不支持敬语系统的语言
        non_honorific_languages = [
            AsianLanguage.INDONESIAN,
            AsianLanguage.MALAY
        ]
        
        for lang in non_honorific_languages:
            config = self.agent.language_configs[lang]
            assert config["honorific_system"] is False
    
    @patch('agents.asian_translation_agent.get_context_agent')
    @patch('agents.asian_translation_agent.get_dynamic_knowledge_manager')
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
        mock_kb_result.results = [{"参谋长": "参謀長"}]
        mock_kb_manager.query_knowledge.return_value = mock_kb_result
        
        # 创建翻译请求
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长，任务完成",
            speaker="士兵"
        )
        
        request = AsianTranslationRequest(
            request_id="test_full",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=AsianLanguage.JAPANESE
        )
        
        # 执行翻译
        result = self.agent.translate(request)
        
        # 验证结果
        assert result.success is True
        assert result.target_language == AsianLanguage.JAPANESE
        assert result.translated_text is not None
        assert result.quality_score > 0
        assert result.honorific_level_used is not None
        assert result.processing_time_ms > 0
        assert result.confidence > 0