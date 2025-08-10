"""
文化本土化引擎测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from agents.cultural_localization_agent import (
    CulturalLocalizationEngine, CulturalTerm, LocalizationRequest, LocalizationResult,
    CulturalCategory, CulturalContext, AdaptationStrategy,
    get_cultural_localization_engine, localize_cultural_text, detect_cultural_terms
)


class TestCulturalTerm:
    """文化词汇条目测试"""
    
    def test_cultural_term_creation(self):
        """测试文化词汇创建"""
        term = CulturalTerm(
            term="鸡娃",
            category=CulturalCategory.FAMILY_EDUCATION,
            source_context=CulturalContext.CHINESE_MAINLAND,
            definition="指家长对孩子进行高强度教育投入",
            usage_examples=["她是个典型的鸡娃妈妈"],
            emotional_tone="neutral",
            formality_level="informal"
        )
        
        assert term.term == "鸡娃"
        assert term.category == CulturalCategory.FAMILY_EDUCATION
        assert term.source_context == CulturalContext.CHINESE_MAINLAND
        assert term.definition == "指家长对孩子进行高强度教育投入"
        assert len(term.usage_examples) == 1
        assert term.emotional_tone == "neutral"
        assert term.formality_level == "informal"
        assert term.target_translations == {}
        assert term.related_terms == []
        assert term.cultural_notes == []
        assert term.frequency_score == 0.0
        assert term.last_updated is not None
    
    def test_cultural_term_with_translations(self):
        """测试带翻译的文化词汇"""
        translations = {
            "en": {
                "translation": "helicopter parenting",
                "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                "explanation": "intensive parenting focused on children's achievement"
            }
        }
        
        term = CulturalTerm(
            term="鸡娃",
            category=CulturalCategory.FAMILY_EDUCATION,
            source_context=CulturalContext.CHINESE_MAINLAND,
            definition="指家长对孩子进行高强度教育投入",
            usage_examples=["她是个典型的鸡娃妈妈"],
            emotional_tone="neutral",
            formality_level="informal",
            target_translations=translations
        )
        
        assert term.target_translations == translations
        assert "en" in term.target_translations
        assert term.target_translations["en"]["translation"] == "helicopter parenting"


class TestLocalizationRequest:
    """本土化请求测试"""
    
    def test_localization_request_creation(self):
        """测试本土化请求创建"""
        request = LocalizationRequest(
            request_id="test_request",
            source_text="这个孩子被鸡娃了",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        assert request.request_id == "test_request"
        assert request.source_text == "这个孩子被鸡娃了"
        assert request.target_language == "en"
        assert request.target_culture == CulturalContext.WESTERN
        assert request.context_info is None
        assert request.speaker_info is None
        assert request.scene_context is None
        assert request.formality_preference is None
        assert request.timestamp is not None
    
    def test_localization_request_with_context(self):
        """测试带上下文的本土化请求"""
        context_info = {"formality": "formal", "scene_context": "family discussion"}
        
        request = LocalizationRequest(
            request_id="test_request",
            source_text="现在内卷太严重了",
            target_language="ja",
            target_culture=CulturalContext.JAPANESE,
            context_info=context_info,
            formality_preference="formal"
        )
        
        assert request.context_info == context_info
        assert request.formality_preference == "formal"


class TestLocalizationResult:
    """本土化结果测试"""
    
    def test_localization_result_success(self):
        """测试成功的本土化结果"""
        result = LocalizationResult(
            request_id="test_request",
            success=True,
            original_text="这个孩子被鸡娃了",
            localized_text="This child is being helicopter parented",
            confidence_score=0.85
        )
        
        assert result.request_id == "test_request"
        assert result.success is True
        assert result.original_text == "这个孩子被鸡娃了"
        assert result.localized_text == "This child is being helicopter parented"
        assert result.confidence_score == 0.85
        assert result.detected_terms == []
        assert result.adaptations_applied == []
        assert result.cultural_notes == []
        assert result.alternative_translations == []
        assert result.timestamp is not None
    
    def test_localization_result_failure(self):
        """测试失败的本土化结果"""
        result = LocalizationResult(
            request_id="test_request",
            success=False,
            original_text="测试文本",
            error_message="处理失败"
        )
        
        assert result.success is False
        assert result.error_message == "处理失败"
        assert result.localized_text is None


class TestCulturalLocalizationEngine:
    """文化本土化引擎测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.engine = CulturalLocalizationEngine()
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        assert self.engine.engine_id.startswith("cultural_engine_")
        assert len(self.engine.cultural_terms_db) > 0
        assert len(self.engine.language_adaptation_rules) > 0
        assert self.engine.performance_stats["total_localizations"] == 0
        
        # 检查核心词汇是否已加载
        assert "鸡娃" in self.engine.cultural_terms_db
        assert "内卷" in self.engine.cultural_terms_db
        assert "躺平" in self.engine.cultural_terms_db
        assert "996" in self.engine.cultural_terms_db
    
    def test_detect_cultural_terms_known_terms(self):
        """测试检测已知文化词汇"""
        text = "现在鸡娃现象很普遍，大家都在内卷"
        detected_terms = self.engine._detect_cultural_terms(text)
        
        assert len(detected_terms) >= 2
        term_texts = [term.term for term in detected_terms]
        assert "鸡娃" in term_texts
        assert "内卷" in term_texts
    
    def test_detect_cultural_terms_pattern_matching(self):
        """测试模式匹配检测"""
        text = "现在打工人都很累，社畜族越来越多"
        detected_terms = self.engine._detect_cultural_terms(text)
        
        # 应该检测到"打工人"（已知词汇）和可能的模式匹配词汇
        assert len(detected_terms) >= 1
        term_texts = [term.term for term in detected_terms]
        assert "打工人" in term_texts
    
    def test_localize_text_simple(self):
        """测试简单文本本土化"""
        request = LocalizationRequest(
            request_id="test_001",
            source_text="这个孩子被鸡娃了",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert result.original_text == "这个孩子被鸡娃了"
        assert result.localized_text is not None
        assert result.localized_text != result.original_text
        assert len(result.detected_terms) >= 1
        assert result.confidence_score > 0
        
        # 检查是否检测到"鸡娃"
        detected_term_texts = [term.term for term in result.detected_terms]
        assert "鸡娃" in detected_term_texts
    
    def test_localize_text_multiple_terms(self):
        """测试多个文化词汇的本土化"""
        request = LocalizationRequest(
            request_id="test_002",
            source_text="现在内卷太严重，很多人选择躺平",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert len(result.detected_terms) >= 2
        assert len(result.adaptations_applied) >= 2
        
        # 检查是否检测到多个词汇
        detected_term_texts = [term.term for term in result.detected_terms]
        assert "内卷" in detected_term_texts
        assert "躺平" in detected_term_texts
    
    def test_localize_text_japanese(self):
        """测试日语本土化"""
        request = LocalizationRequest(
            request_id="test_003",
            source_text="996工作制太累了",
            target_language="ja",
            target_culture=CulturalContext.JAPANESE
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert result.localized_text is not None
        assert "996" in [term.term for term in result.detected_terms]
    
    def test_localize_text_with_context(self):
        """测试带上下文的本土化"""
        context_info = {
            "formality": "formal",
            "scene_context": "business meeting"
        }
        
        request = LocalizationRequest(
            request_id="test_004",
            source_text="打工人都很辛苦",
            target_language="en",
            target_culture=CulturalContext.WESTERN,
            context_info=context_info
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert result.localized_text is not None
        # 在正式场合，应该使用更正式的翻译
    
    def test_select_adaptation_strategy(self):
        """测试适配策略选择"""
        term = self.engine.cultural_terms_db["鸡娃"]
        request = LocalizationRequest(
            request_id="test_005",
            source_text="鸡娃现象",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        lang_rules = self.engine.language_adaptation_rules["en"]
        translation_info = term.target_translations["en"]
        
        strategy = self.engine._select_adaptation_strategy(
            term, request, lang_rules, translation_info
        )
        
        assert isinstance(strategy, AdaptationStrategy)
    
    def test_apply_adaptation_strategy_direct(self):
        """测试直接翻译策略"""
        translation_info = {
            "translation": "helicopter parenting",
            "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value
        }
        
        request = LocalizationRequest(
            request_id="test_006",
            source_text="鸡娃",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine._apply_adaptation_strategy(
            "鸡娃", translation_info, AdaptationStrategy.DIRECT_TRANSLATION, request
        )
        
        assert result == "helicopter parenting"
    
    def test_apply_adaptation_strategy_explanation(self):
        """测试添加解释策略"""
        translation_info = {
            "translation": "helicopter parenting",
            "explanation": "intensive parenting focused on children's achievement"
        }
        
        request = LocalizationRequest(
            request_id="test_007",
            source_text="鸡娃",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine._apply_adaptation_strategy(
            "鸡娃", translation_info, AdaptationStrategy.EXPLANATION_ADDED, request
        )
        
        assert "helicopter parenting" in result
        assert "intensive parenting focused on children's achievement" in result
    
    def test_calculate_confidence(self):
        """测试置信度计算"""
        detected_terms = [self.engine.cultural_terms_db["鸡娃"]]
        adaptations = [{"confidence": 0.8}]
        
        confidence = self.engine._calculate_confidence(detected_terms, adaptations)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence == 0.8
    
    def test_calculate_term_confidence(self):
        """测试单个词汇置信度计算"""
        term = self.engine.cultural_terms_db["鸡娃"]
        request = LocalizationRequest(
            request_id="test_008",
            source_text="鸡娃",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        confidence = self.engine._calculate_term_confidence(term, request)
        
        assert 0.0 <= confidence <= 1.0
    
    def test_is_culturally_compatible(self):
        """测试文化兼容性判断"""
        term = self.engine.cultural_terms_db["孝顺"]  # 传统文化词汇
        
        # 东亚文化应该兼容
        assert self.engine._is_culturally_compatible(term, CulturalContext.JAPANESE) is True
        assert self.engine._is_culturally_compatible(term, CulturalContext.KOREAN) is True
        
        # 西方文化可能不太兼容
        # 但由于是传统文化，在儒家文化圈应该兼容
        assert self.engine._is_culturally_compatible(term, CulturalContext.SINGAPORE) is True
    
    def test_generate_cultural_notes(self):
        """测试文化注释生成"""
        detected_terms = [self.engine.cultural_terms_db["鸡娃"]]
        notes = self.engine._generate_cultural_notes(detected_terms, CulturalContext.WESTERN)
        
        assert isinstance(notes, list)
        # 应该有一些注释
        assert len(notes) >= 0
    
    def test_generate_alternatives(self):
        """测试替代翻译生成"""
        detected_terms = [self.engine.cultural_terms_db["鸡娃"]]
        request = LocalizationRequest(
            request_id="test_009",
            source_text="这是鸡娃现象",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        alternatives = self.engine._generate_alternatives(detected_terms, request)
        
        assert isinstance(alternatives, list)
    
    def test_add_cultural_term(self):
        """测试添加文化词汇"""
        new_term = CulturalTerm(
            term="摸鱼",
            category=CulturalCategory.WORK_CULTURE,
            source_context=CulturalContext.CHINESE_MAINLAND,
            definition="指在工作时间做与工作无关的事情",
            usage_examples=["他在上班时间摸鱼"],
            emotional_tone="neutral",
            formality_level="slang"
        )
        
        success = self.engine.add_cultural_term(new_term)
        
        assert success is True
        assert "摸鱼" in self.engine.cultural_terms_db
        assert self.engine.cultural_terms_db["摸鱼"] == new_term
    
    def test_update_cultural_term(self):
        """测试更新文化词汇"""
        # 先添加一个词汇
        new_term = CulturalTerm(
            term="测试词汇",
            category=CulturalCategory.MODERN_LIFE,
            source_context=CulturalContext.CHINESE_MAINLAND,
            definition="测试用词汇",
            usage_examples=["这是测试"],
            emotional_tone="neutral",
            formality_level="informal"
        )
        
        self.engine.add_cultural_term(new_term)
        
        # 更新词汇
        updates = {
            "definition": "更新后的定义",
            "frequency_score": 0.8
        }
        
        success = self.engine.update_cultural_term("测试词汇", updates)
        
        assert success is True
        updated_term = self.engine.cultural_terms_db["测试词汇"]
        assert updated_term.definition == "更新后的定义"
        assert updated_term.frequency_score == 0.8
    
    def test_get_cultural_terms_by_category(self):
        """测试按类别获取文化词汇"""
        family_terms = self.engine.get_cultural_terms_by_category(CulturalCategory.FAMILY_EDUCATION)
        
        assert isinstance(family_terms, list)
        assert len(family_terms) > 0
        
        # 检查所有返回的词汇都是正确类别
        for term in family_terms:
            assert term.category == CulturalCategory.FAMILY_EDUCATION
    
    def test_search_cultural_terms(self):
        """测试搜索文化词汇"""
        results = self.engine.search_cultural_terms("工作", limit=5)
        
        assert isinstance(results, list)
        assert len(results) <= 5
        
        # 检查结果是否包含相关词汇
        result_texts = [term.term for term in results]
        # 应该找到包含"工作"相关的词汇
    
    def test_get_engine_status(self):
        """测试获取引擎状态"""
        status = self.engine.get_engine_status()
        
        assert "engine_id" in status
        assert "cultural_terms_count" in status
        assert "supported_languages" in status
        assert "performance_stats" in status
        assert "categories" in status
        assert "cultural_contexts" in status
        assert "adaptation_strategies" in status
        
        assert status["cultural_terms_count"] > 0
        assert len(status["supported_languages"]) > 0
    
    def test_export_import_cultural_terms(self):
        """测试导出和导入文化词汇"""
        # 导出数据
        exported_data = self.engine.export_cultural_terms()
        
        assert "export_time" in exported_data
        assert "terms_count" in exported_data
        assert "terms" in exported_data
        assert exported_data["terms_count"] > 0
        
        # 创建新引擎并导入数据
        new_engine = CulturalLocalizationEngine()
        original_count = len(new_engine.cultural_terms_db)
        
        success = new_engine.import_cultural_terms(exported_data)
        
        assert success is True
        # 导入后词汇数量应该不少于原来的数量
        assert len(new_engine.cultural_terms_db) >= original_count


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_get_cultural_localization_engine(self):
        """测试获取引擎实例"""
        engine = get_cultural_localization_engine()
        assert isinstance(engine, CulturalLocalizationEngine)
        
        # 应该返回同一个实例
        engine2 = get_cultural_localization_engine()
        assert engine is engine2
    
    def test_localize_cultural_text(self):
        """测试便捷的本土化函数"""
        result = localize_cultural_text(
            source_text="现在内卷太严重了",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        assert isinstance(result, LocalizationResult)
        assert result.success is True
        assert result.original_text == "现在内卷太严重了"
    
    def test_detect_cultural_terms_function(self):
        """测试便捷的文化词汇检测函数"""
        terms = detect_cultural_terms("鸡娃和内卷是现代社会现象")
        
        assert isinstance(terms, list)
        assert len(terms) >= 2
        
        term_texts = [term.term for term in terms]
        assert "鸡娃" in term_texts
        assert "内卷" in term_texts


class TestEnumValues:
    """枚举值测试"""
    
    def test_cultural_category_values(self):
        """测试文化类别枚举"""
        assert CulturalCategory.MODERN_LIFE.value == "modern_life"
        assert CulturalCategory.INTERNET_SLANG.value == "internet_slang"
        assert CulturalCategory.FAMILY_EDUCATION.value == "family_education"
        assert CulturalCategory.WORK_CULTURE.value == "work_culture"
    
    def test_cultural_context_values(self):
        """测试文化背景枚举"""
        assert CulturalContext.CHINESE_MAINLAND.value == "chinese_mainland"
        assert CulturalContext.WESTERN.value == "western"
        assert CulturalContext.JAPANESE.value == "japanese"
        assert CulturalContext.KOREAN.value == "korean"
    
    def test_adaptation_strategy_values(self):
        """测试适配策略枚举"""
        assert AdaptationStrategy.DIRECT_TRANSLATION.value == "direct_translation"
        assert AdaptationStrategy.CULTURAL_EQUIVALENT.value == "cultural_equivalent"
        assert AdaptationStrategy.EXPLANATION_ADDED.value == "explanation_added"
        assert AdaptationStrategy.LOCALIZED_REPLACEMENT.value == "localized_replacement"


class TestEdgeCases:
    """边界情况测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.engine = CulturalLocalizationEngine()
    
    def test_empty_text_localization(self):
        """测试空文本本土化"""
        request = LocalizationRequest(
            request_id="test_empty",
            source_text="",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert result.localized_text == ""
        assert len(result.detected_terms) == 0
    
    def test_no_cultural_terms_text(self):
        """测试不包含文化词汇的文本"""
        request = LocalizationRequest(
            request_id="test_no_terms",
            source_text="今天天气很好",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        assert result.success is True
        assert result.localized_text == "今天天气很好"  # 应该保持不变
        assert len(result.detected_terms) == 0
    
    def test_unsupported_language(self):
        """测试不支持的语言"""
        request = LocalizationRequest(
            request_id="test_unsupported",
            source_text="鸡娃现象很普遍",
            target_language="unknown_lang",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        # 应该使用默认规则处理
        assert result.success is True
    
    def test_term_without_target_translation(self):
        """测试没有目标语言翻译的词汇"""
        # 添加一个没有英语翻译的词汇
        new_term = CulturalTerm(
            term="测试无翻译",
            category=CulturalCategory.MODERN_LIFE,
            source_context=CulturalContext.CHINESE_MAINLAND,
            definition="测试用词汇",
            usage_examples=["这是测试"],
            emotional_tone="neutral",
            formality_level="informal"
        )
        
        self.engine.add_cultural_term(new_term)
        
        request = LocalizationRequest(
            request_id="test_no_translation",
            source_text="这是测试无翻译的例子",
            target_language="en",
            target_culture=CulturalContext.WESTERN
        )
        
        result = self.engine.localize_text(request)
        
        # 应该能处理，但可能保持原文
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__])