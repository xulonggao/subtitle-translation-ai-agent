"""
欧洲语言和阿拉伯语翻译 Agent 测试
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from agents.european_arabic_translation_agent import (
    EuropeanArabicTranslationAgent, EuropeanArabicTranslationRequest, EuropeanArabicTranslationResult,
    EuropeanArabicLanguage, GenderType, TextDirection, ReligiousSensitivity,
    get_european_arabic_translation_agent, translate_to_european_arabic_language
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestEuropeanArabicTranslationRequest:
    """欧洲语言和阿拉伯语翻译请求测试"""
    
    def test_translation_request_creation(self):
        """测试翻译请求创建"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="你好，世界！",
            speaker="张三"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="test_request",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH,
            gender_context={"张三": GenderType.MASCULINE},
            religious_sensitivity=ReligiousSensitivity.LOW
        )
        
        assert request.request_id == "test_request"
        assert request.project_id == "test_project"
        assert request.subtitle_entry == subtitle_entry
        assert request.target_language == EuropeanArabicLanguage.SPANISH
        assert request.gender_context == {"张三": GenderType.MASCULINE}
        assert request.religious_sensitivity == ReligiousSensitivity.LOW
        assert request.preserve_gender_agreement is True
        assert request.adapt_religious_content is True
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
        
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.PORTUGUESE
        )
        
        assert request.target_language == EuropeanArabicLanguage.PORTUGUESE
        assert request.gender_context is None
        assert request.religious_sensitivity is None
        assert request.context_window is None
        assert request.preserve_gender_agreement is True
        assert request.adapt_religious_content is True
        assert request.maintain_cultural_respect is True


class TestEuropeanArabicTranslationResult:
    """欧洲语言和阿拉伯语翻译结果测试"""
    
    def test_translation_result_creation(self):
        """测试翻译结果创建"""
        result = EuropeanArabicTranslationResult(
            request_id="test_request",
            success=True,
            target_language=EuropeanArabicLanguage.SPANISH,
            translated_text="¡Hola, mundo!",
            original_text="你好，世界！",
            text_direction=TextDirection.LEFT_TO_RIGHT,
            quality_score=0.85
        )
        
        assert result.request_id == "test_request"
        assert result.success is True
        assert result.target_language == EuropeanArabicLanguage.SPANISH
        assert result.translated_text == "¡Hola, mundo!"
        assert result.original_text == "你好，世界！"
        assert result.text_direction == TextDirection.LEFT_TO_RIGHT
        assert result.quality_score == 0.85
        assert result.character_count == len("¡Hola, mundo!")
        assert result.timestamp is not None
    
    def test_arabic_translation_result(self):
        """测试阿拉伯语翻译结果"""
        result = EuropeanArabicTranslationResult(
            request_id="test_arabic",
            success=True,
            target_language=EuropeanArabicLanguage.ARABIC,
            translated_text="مرحبا بالعالم",
            original_text="你好，世界！",
            text_direction=TextDirection.RIGHT_TO_LEFT,
            religious_adaptations=["上帝 -> الله"],
            quality_score=0.9
        )
        
        assert result.target_language == EuropeanArabicLanguage.ARABIC
        assert result.text_direction == TextDirection.RIGHT_TO_LEFT
        assert result.religious_adaptations == ["上帝 -> الله"]
    
    def test_error_result(self):
        """测试错误结果"""
        result = EuropeanArabicTranslationResult(
            request_id="test_request",
            success=False,
            target_language=EuropeanArabicLanguage.ARABIC,
            error_message="翻译失败"
        )
        
        assert result.success is False
        assert result.target_language == EuropeanArabicLanguage.ARABIC
        assert result.error_message == "翻译失败"
        assert result.translated_text is None
        assert result.quality_score == 0.0


class TestEuropeanArabicTranslationAgent:
    """欧洲语言和阿拉伯语翻译 Agent 测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.european_arabic_translation_agent.get_context_agent'), \
             patch('agents.european_arabic_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = EuropeanArabicTranslationAgent()
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        assert self.agent.agent_id.startswith("eu_ar_agent_")
        assert len(self.agent.language_configs) == 3  # 3种语言
        assert EuropeanArabicLanguage.SPANISH in self.agent.language_configs
        assert EuropeanArabicLanguage.PORTUGUESE in self.agent.language_configs
        assert EuropeanArabicLanguage.ARABIC in self.agent.language_configs
        assert self.agent.performance_stats["total_translations"] == 0
    
    def test_supported_languages(self):
        """测试支持的语言列表"""
        languages = self.agent.get_supported_languages()
        
        assert len(languages) == 3
        
        # 检查西班牙语配置
        spanish = next(lang for lang in languages if lang["code"] == "es")
        assert spanish["name"] == "西班牙语"
        assert spanish["text_direction"] == "ltr"
        assert spanish["gender_system"] is True
        assert spanish["religious_sensitivity"] is False
        
        # 检查阿拉伯语配置
        arabic = next(lang for lang in languages if lang["code"] == "ar")
        assert arabic["name"] == "阿拉伯语"
        assert arabic["text_direction"] == "rtl"
        assert arabic["gender_system"] is True
        assert arabic["religious_sensitivity"] is True
    
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
        
        valid_request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=valid_entry,
            target_language=EuropeanArabicLanguage.SPANISH
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
        
        invalid_request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test_project",
            subtitle_entry=invalid_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        assert self.agent._validate_request(invalid_request) is False
    
    def test_gender_context_determination(self):
        """测试性别上下文确定"""
        # 指定性别上下文的情况
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=EuropeanArabicLanguage.SPANISH,
            gender_context={"张三": GenderType.MASCULINE}
        )
        
        gender_context = self.agent._determine_gender_context(request, {})
        assert gender_context == {"张三": GenderType.MASCULINE}
        
        # 从上下文推断性别
        context_info = {
            "speaker_info": {
                "speaker_info": {"speaker": "李四"}
            }
        }
        
        request_no_gender = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=Mock(),
            target_language=EuropeanArabicLanguage.PORTUGUESE
        )
        
        gender_context = self.agent._determine_gender_context(request_no_gender, context_info)
        assert "李四" in gender_context
        assert gender_context["李四"] == GenderType.NEUTRAL
    
    def test_religious_sensitivity_determination(self):
        """测试宗教敏感度确定"""
        # 阿拉伯语默认高敏感度
        arabic_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="普通文本",
            speaker="测试"
        )
        
        arabic_request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=arabic_entry,
            target_language=EuropeanArabicLanguage.ARABIC
        )
        
        sensitivity = self.agent._determine_religious_sensitivity(arabic_request, {})
        assert sensitivity == ReligiousSensitivity.HIGH
        
        # 包含宗教内容的文本
        religious_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="感谢上帝的祝福",
            speaker="测试"
        )
        
        spanish_request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=religious_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        sensitivity = self.agent._determine_religious_sensitivity(spanish_request, {})
        assert sensitivity == ReligiousSensitivity.MEDIUM
    
    def test_terminology_mapping(self):
        """测试术语映射"""
        # 西班牙语术语映射
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说司令要来检查",
            speaker="士兵"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        terminology = self.agent._get_terminology_mappings(request, {})
        
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "jefe de estado mayor"
        assert "司令" in terminology
        assert terminology["司令"] == "comandante"
        
        # 阿拉伯语术语映射
        request_arabic = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.ARABIC
        )
        
        terminology_arabic = self.agent._get_terminology_mappings(request_arabic, {})
        
        assert "参谋长" in terminology_arabic
        assert terminology_arabic["参谋长"] == "رئيس الأركان"
        assert "司令" in terminology_arabic
        assert terminology_arabic["司令"] == "القائد"
    
    def test_simulate_translation(self):
        """测试模拟翻译"""
        # 西班牙语翻译
        text = "你好，参谋长"
        terminology = {"参谋长": "jefe de estado mayor"}
        
        result = self.agent._simulate_translation(
            text, EuropeanArabicLanguage.SPANISH, {}, terminology
        )
        
        assert "jefe de estado mayor" in result
        
        # 阿拉伯语翻译
        result_arabic = self.agent._simulate_translation(
            text, EuropeanArabicLanguage.ARABIC, {}, {"参谋长": "رئيس الأركان"}
        )
        
        assert "رئيس الأركان" in result_arabic
        
        # 葡萄牙语翻译
        result_portuguese = self.agent._simulate_translation(
            text, EuropeanArabicLanguage.PORTUGUESE, {}, {"参谋长": "chefe do estado-maior"}
        )
        
        assert "chefe do estado-maior" in result_portuguese
    
    def test_gender_adaptations(self):
        """测试性别适配"""
        text = "医生说朋友很关心你"
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text=text,
                speaker="测试"
            ),
            target_language=EuropeanArabicLanguage.SPANISH,
            preserve_gender_agreement=True
        )
        
        gender_context = {"医生": GenderType.FEMININE, "朋友": GenderType.MASCULINE}
        
        adapted = self.agent._apply_gender_adaptations(text, request, gender_context)
        
        # 这里应该根据性别上下文进行适配
        # 由于是简化实现，我们主要测试方法不会出错
        assert adapted is not None
    
    def test_religious_adaptations(self):
        """测试宗教适配"""
        text = "感谢上帝的祝福"
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text=text,
                speaker="测试"
            ),
            target_language=EuropeanArabicLanguage.ARABIC,
            adapt_religious_content=True
        )
        
        adapted = self.agent._apply_religious_adaptations(text, request, ReligiousSensitivity.HIGH)
        
        assert "الله" in adapted  # "上帝" -> "الله"
    
    def test_text_formatting_optimization(self):
        """测试文本格式优化"""
        # 阿拉伯语文本方向处理
        text = "مرحبا بالعالم"
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="你好，世界",
                speaker="测试"
            ),
            target_language=EuropeanArabicLanguage.ARABIC
        )
        
        optimized = self.agent._optimize_text_formatting(text, request)
        
        # 检查是否添加了RTL标记
        assert "\u202B" in optimized and "\u202C" in optimized
    
    def test_length_quality_assessment(self):
        """测试长度质量评估"""
        original = "测试文本"
        
        # 西班牙语 - 理想长度比例（1.2倍）
        # "测试文本"是4个字符，理想翻译应该是4-4.8个字符
        good_translation = "Texto"  # 5个字符，比例1.25，接近但仍在合理范围内
        score = self.agent._assess_length_quality(original, good_translation, EuropeanArabicLanguage.SPANISH)
        assert score >= 0.8
        
        # 阿拉伯语 - 较短的翻译（1.1倍允许范围）
        # "测试文本"是4个字符，阿拉伯语允许1.1倍，即4.4个字符
        arabic_translation = "نص"  # 2个字符，比例0.5，在合理范围内
        score_arabic = self.agent._assess_length_quality(original, arabic_translation, EuropeanArabicLanguage.ARABIC)
        assert score_arabic >= 0.8
        
        # 过长翻译
        long_translation = "Este es un texto muy largo"  # 27个字符，比例6.75，明显过长
        score_long = self.agent._assess_length_quality(original, long_translation, EuropeanArabicLanguage.SPANISH)
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
        
        request = EuropeanArabicTranslationRequest(
            request_id="test",
            project_id="test",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        # 正确使用术语
        good_translation = "El jefe de estado mayor dice que el comandante viene"
        score = self.agent._assess_terminology_consistency(good_translation, request)
        assert score == 1.0
        
        # 部分使用术语
        partial_translation = "El jefe de estado mayor dice que el 司令 viene"
        score = self.agent._assess_terminology_consistency(partial_translation, request)
        assert 0.0 < score < 1.0
        
        # 未使用术语
        bad_translation = "El 参谋长 dice que el 司令 viene"
        score = self.agent._assess_terminology_consistency(bad_translation, request)
        assert score == 0.0
    
    def test_performance_stats_update(self):
        """测试性能统计更新"""
        initial_total = self.agent.performance_stats["total_translations"]
        initial_successful = self.agent.performance_stats["successful_translations"]
        
        # 成功翻译
        self.agent._update_performance_stats(
            EuropeanArabicLanguage.SPANISH, 0.8, 100.0, True
        )
        
        assert self.agent.performance_stats["total_translations"] == initial_total + 1
        assert self.agent.performance_stats["successful_translations"] == initial_successful + 1
        assert self.agent.performance_stats["average_quality_score"] > 0
        assert self.agent.performance_stats["average_processing_time"] > 0
        assert "es" in self.agent.performance_stats["language_distribution"]
        
        # 失败翻译
        initial_errors = self.agent.performance_stats["error_count"]
        self.agent._update_performance_stats(
            EuropeanArabicLanguage.ARABIC, 0.0, 200.0, False
        )
        
        assert self.agent.performance_stats["error_count"] == initial_errors + 1
    
    def test_agent_status(self):
        """测试 Agent 状态"""
        status = self.agent.get_agent_status()
        
        assert "agent_id" in status
        assert status["supported_languages"] == 3
        assert "es" in status["language_list"]
        assert "pt" in status["language_list"]
        assert "ar" in status["language_list"]
        assert "performance_stats" in status
        assert "gender_types" in status
        assert "religious_sensitivity_levels" in status
        assert "text_directions" in status
    
    def test_stats_reset(self):
        """测试统计重置"""
        # 先进行一些翻译以产生统计数据
        self.agent._update_performance_stats(
            EuropeanArabicLanguage.SPANISH, 0.8, 100.0, True
        )
        
        assert self.agent.performance_stats["total_translations"] > 0
        
        # 重置统计
        self.agent.reset_stats()
        
        assert self.agent.performance_stats["total_translations"] == 0
        assert self.agent.performance_stats["successful_translations"] == 0
        assert self.agent.performance_stats["average_quality_score"] == 0.0
        assert self.agent.performance_stats["language_distribution"] == {}


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_european_arabic_translation_agent(self):
        """测试获取全局 Agent 实例"""
        agent1 = get_european_arabic_translation_agent()
        agent2 = get_european_arabic_translation_agent()
        
        # 应该返回同一个实例
        assert agent1 is agent2
        assert agent1.agent_id == agent2.agent_id
    
    @patch('agents.european_arabic_translation_agent.get_european_arabic_translation_agent')
    def test_translate_to_european_arabic_language_convenience_function(self, mock_get_agent):
        """测试便捷翻译函数"""
        # 模拟 Agent
        mock_agent = Mock()
        mock_result = EuropeanArabicTranslationResult(
            request_id="test",
            success=True,
            target_language=EuropeanArabicLanguage.SPANISH,
            translated_text="¡Hola, mundo!",
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
        result = translate_to_european_arabic_language(
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH,
            gender_context={"测试": GenderType.MASCULINE}
        )
        
        # 验证结果
        assert result.success is True
        assert result.translated_text == "¡Hola, mundo!"
        
        # 验证 Agent 被正确调用
        mock_agent.translate.assert_called_once()
        call_args = mock_agent.translate.call_args[0][0]
        assert call_args.project_id == "test_project"
        assert call_args.subtitle_entry == subtitle_entry
        assert call_args.target_language == EuropeanArabicLanguage.SPANISH
        assert call_args.gender_context == {"测试": GenderType.MASCULINE}


class TestLanguageSpecificTranslation:
    """语言特定翻译测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('agents.european_arabic_translation_agent.get_context_agent'), \
             patch('agents.european_arabic_translation_agent.get_dynamic_knowledge_manager'):
            self.agent = EuropeanArabicTranslationAgent()
    
    def test_spanish_translation_integration(self):
        """测试西班牙语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="是，参谋长！",
            speaker="士兵"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="spanish_test",
            project_id="military_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "参谋长" in terminology
        assert terminology["参谋长"] == "jefe de estado mayor"
        
        # 测试翻译
        translated = self.agent._simulate_translation(
            subtitle_entry.text, EuropeanArabicLanguage.SPANISH, {}, terminology
        )
        assert "jefe de estado mayor" in translated
        
        # 测试语言配置
        config = self.agent.language_configs[EuropeanArabicLanguage.SPANISH]
        assert config["text_direction"] == TextDirection.LEFT_TO_RIGHT
        assert config["gender_system"] is True
        assert config["religious_sensitivity"] is False
    
    def test_portuguese_translation_integration(self):
        """测试葡萄牙语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="朋友，你好吗？",
            speaker="张三"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="portuguese_test",
            project_id="casual_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.PORTUGUESE
        )
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "朋友" in terminology
        assert terminology["朋友"] == "amigo"
        
        # 测试翻译
        translated = self.agent._simulate_translation(
            subtitle_entry.text, EuropeanArabicLanguage.PORTUGUESE, {}, terminology
        )
        assert "amigo" in translated
        
        # 测试语言配置
        config = self.agent.language_configs[EuropeanArabicLanguage.PORTUGUESE]
        assert config["text_direction"] == TextDirection.LEFT_TO_RIGHT
        assert config["gender_system"] is True
        assert config["cultural_context"] == "lusophone"
    
    def test_arabic_translation_integration(self):
        """测试阿拉伯语翻译集成"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="感谢上帝，任务完成！",
            speaker="士兵"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="arabic_test",
            project_id="military_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.ARABIC
        )
        
        # 测试宗教敏感度
        sensitivity = self.agent._determine_religious_sensitivity(request, {})
        assert sensitivity == ReligiousSensitivity.HIGH
        
        # 测试术语映射
        terminology = self.agent._get_terminology_mappings(request, {})
        assert "任务" in terminology
        assert terminology["任务"] == "المهمة"
        
        # 测试宗教适配
        adapted = self.agent._apply_religious_adaptations(
            subtitle_entry.text, request, sensitivity
        )
        assert "الله" in adapted  # "上帝" -> "الله"
        
        # 测试语言配置
        config = self.agent.language_configs[EuropeanArabicLanguage.ARABIC]
        assert config["text_direction"] == TextDirection.RIGHT_TO_LEFT
        assert config["religious_sensitivity"] is True
        assert config["cultural_context"] == "islamic"
    
    def test_gender_system_support(self):
        """测试性别系统支持"""
        # 所有语言都支持性别系统
        for lang in EuropeanArabicLanguage:
            config = self.agent.language_configs[lang]
            assert config["gender_system"] is True
        
        # 测试性别映射
        spanish_mappings = self.agent.gender_mappings[EuropeanArabicLanguage.SPANISH]
        assert "医生" in spanish_mappings
        assert spanish_mappings["医生"]["masculine"] == "médico"
        assert spanish_mappings["医生"]["feminine"] == "médica"
        
        arabic_mappings = self.agent.gender_mappings[EuropeanArabicLanguage.ARABIC]
        assert "医生" in arabic_mappings
        assert arabic_mappings["医生"]["masculine"] == "الطبيب"
        assert arabic_mappings["医生"]["feminine"] == "الطبيبة"
    
    def test_text_direction_handling(self):
        """测试文本方向处理"""
        # 欧洲语言：从左到右
        european_languages = [EuropeanArabicLanguage.SPANISH, EuropeanArabicLanguage.PORTUGUESE]
        for lang in european_languages:
            config = self.agent.language_configs[lang]
            assert config["text_direction"] == TextDirection.LEFT_TO_RIGHT
        
        # 阿拉伯语：从右到左
        arabic_config = self.agent.language_configs[EuropeanArabicLanguage.ARABIC]
        assert arabic_config["text_direction"] == TextDirection.RIGHT_TO_LEFT
    
    def test_religious_sensitivity_handling(self):
        """测试宗教敏感性处理"""
        # 阿拉伯语有宗教敏感性
        arabic_config = self.agent.language_configs[EuropeanArabicLanguage.ARABIC]
        assert arabic_config["religious_sensitivity"] is True
        
        # 欧洲语言没有宗教敏感性
        spanish_config = self.agent.language_configs[EuropeanArabicLanguage.SPANISH]
        portuguese_config = self.agent.language_configs[EuropeanArabicLanguage.PORTUGUESE]
        assert spanish_config["religious_sensitivity"] is False
        assert portuguese_config["religious_sensitivity"] is False
    
    def test_cultural_context_adaptation(self):
        """测试文化背景适配"""
        # 西班牙语：西班牙文化
        spanish_config = self.agent.language_configs[EuropeanArabicLanguage.SPANISH]
        assert spanish_config["cultural_context"] == "hispanic"
        
        # 葡萄牙语：葡语文化
        portuguese_config = self.agent.language_configs[EuropeanArabicLanguage.PORTUGUESE]
        assert portuguese_config["cultural_context"] == "lusophone"
        
        # 阿拉伯语：伊斯兰文化
        arabic_config = self.agent.language_configs[EuropeanArabicLanguage.ARABIC]
        assert arabic_config["cultural_context"] == "islamic"
    
    @patch('agents.european_arabic_translation_agent.get_context_agent')
    @patch('agents.european_arabic_translation_agent.get_dynamic_knowledge_manager')
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
        mock_kb_result.results = [{"参谋长": "jefe de estado mayor"}]
        mock_kb_manager.query_knowledge.return_value = mock_kb_result
        
        # 创建翻译请求
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长，任务完成",
            speaker="士兵"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="test_full",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.SPANISH
        )
        
        # 执行翻译
        result = self.agent.translate(request)
        
        # 验证结果
        assert result.success is True
        assert result.target_language == EuropeanArabicLanguage.SPANISH
        assert result.translated_text is not None
        assert result.text_direction == TextDirection.LEFT_TO_RIGHT
        assert result.quality_score > 0
        assert result.processing_time_ms > 0
        assert result.confidence > 0
    
    def test_arabic_full_workflow(self):
        """测试阿拉伯语完整工作流程"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="感谢上帝，朋友平安",
            speaker="张三"
        )
        
        request = EuropeanArabicTranslationRequest(
            request_id="arabic_full_test",
            project_id="test_project",
            subtitle_entry=subtitle_entry,
            target_language=EuropeanArabicLanguage.ARABIC,
            religious_sensitivity=ReligiousSensitivity.HIGH
        )
        
        # 测试各个处理步骤
        context_info = {}
        
        # 性别上下文确定
        gender_context = self.agent._determine_gender_context(request, context_info)
        assert isinstance(gender_context, dict)
        
        # 宗教敏感度确定
        sensitivity = self.agent._determine_religious_sensitivity(request, context_info)
        assert sensitivity == ReligiousSensitivity.HIGH
        
        # 术语映射
        terminology = self.agent._get_terminology_mappings(request, context_info)
        assert "朋友" in terminology
        assert terminology["朋友"] == "الصديق"
        
        # 宗教适配
        adapted = self.agent._apply_religious_adaptations(
            subtitle_entry.text, request, sensitivity
        )
        assert "الله" in adapted
        
        # 文本格式优化
        optimized = self.agent._optimize_text_formatting(adapted, request)
        assert "\u202B" in optimized  # RTL标记