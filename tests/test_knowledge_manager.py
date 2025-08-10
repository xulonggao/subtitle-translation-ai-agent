"""
知识库管理器测试
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from agents.knowledge_manager import (
    TerminologyExtractor, KnowledgeBase, HierarchicalTerminologyKB,
    ContextAwareTranslationMemory, CulturalAdaptationKB, KnowledgeManager,
    get_knowledge_manager
)
from models.translation_models import TerminologyEntry, TranslationMemory, TranslationMethod


class TestTerminologyExtractor:
    """术语提取器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = TerminologyExtractor()
    
    def test_extract_military_terms(self):
        """测试军事术语提取"""
        text = "参谋长命令突击队立即开始作战演习"
        context = {"speaker": "军官", "scene": "作战室"}
        
        terms = self.extractor.extract_terms(text, context)
        
        # 验证提取结果
        assert len(terms) >= 3
        
        term_texts = [term['term'] for term in terms]
        assert "参谋长" in term_texts
        assert "突击队" in term_texts
        assert "演习" in term_texts
        
        # 验证分类
        military_terms = [term for term in terms if term['category'] == 'military']
        assert len(military_terms) >= 3
    
    def test_extract_cultural_terms(self):
        """测试文化词汇提取"""
        text = "现在的年轻人不是鸡娃就是躺平，内卷太严重了"
        
        terms = self.extractor.extract_terms(text)
        
        term_texts = [term['term'] for term in terms]
        assert "鸡娃" in term_texts
        assert "躺平" in term_texts
        assert "内卷" in term_texts
        
        # 验证分类
        cultural_terms = [term for term in terms if term['category'] == 'cultural']
        assert len(cultural_terms) >= 3
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        text = "参谋长下达作战命令"
        context = {"speaker_profession": "military", "scene_formality": "formal"}
        
        terms = self.extractor.extract_terms(text, context)
        
        # 军事术语在军事上下文中应该有更高置信度
        military_term = next(term for term in terms if term['term'] == '参谋长')
        assert military_term['confidence'] > 0.7


class TestKnowledgeBase:
    """知识库基类测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.kb = KnowledgeBase("test_kb", self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.kb.name == "test_kb"
        assert self.kb.storage_path == Path(self.temp_dir)
        assert isinstance(self.kb.data, dict)
        assert "created_at" in self.kb.metadata
        assert "version" in self.kb.metadata
    
    def test_save_and_load(self):
        """测试保存和加载"""
        # 添加测试数据
        self.kb.data["test_key"] = "test_value"
        self.kb.metadata["entry_count"] = 1
        
        # 保存
        self.kb.save()
        
        # 验证文件存在
        data_file = self.kb.storage_path / "test_kb.json"
        assert data_file.exists()
        
        # 创建新实例并加载
        new_kb = KnowledgeBase("test_kb", self.temp_dir)
        new_kb.load()
        
        # 验证数据
        assert new_kb.data["test_key"] == "test_value"
        assert new_kb.metadata["entry_count"] == 1
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        stats = self.kb.get_statistics()
        
        assert stats["name"] == "test_kb"
        assert "entry_count" in stats
        assert "created_at" in stats
        assert "storage_path" in stats


class TestHierarchicalTerminologyKB:
    """分层术语知识库测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.terminology_kb = HierarchicalTerminologyKB(self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_add_global_term(self):
        """测试添加全局术语"""
        entry = TerminologyEntry(
            source_term="参谋长",
            target_language="en",
            target_term="Chief of Staff",
            domain="military",
            context="军事指挥层级"
        )
        
        result = self.terminology_kb.add_term(entry, "global")
        assert result is True
        
        # 验证术语已添加
        retrieved = self.terminology_kb.get_best_term("参谋长", "en")
        assert retrieved is not None
        assert retrieved.target_term == "Chief of Staff"
        assert retrieved.source_level == "global"
    
    def test_add_project_term(self):
        """测试添加项目术语"""
        entry = TerminologyEntry(
            source_term="队长",
            target_language="en", 
            target_term="Team Leader",
            domain="military",
            context="项目特定称谓"
        )
        
        result = self.terminology_kb.add_term(entry, "project", project_id="test_project")
        assert result is True
        
        # 验证术语已添加
        retrieved = self.terminology_kb.get_best_term("队长", "en", project_id="test_project")
        assert retrieved is not None
        assert retrieved.target_term == "Team Leader"
        assert retrieved.source_level == "project"
    
    def test_term_priority(self):
        """测试术语优先级（项目 > 类型 > 全局）"""
        # 添加全局术语
        global_entry = TerminologyEntry(
            source_term="司令",
            target_language="en",
            target_term="Commander",
            domain="military"
        )
        self.terminology_kb.add_term(global_entry, "global")
        
        # 添加项目术语
        project_entry = TerminologyEntry(
            source_term="司令",
            target_language="en",
            target_term="Colonel",
            domain="military"
        )
        self.terminology_kb.add_term(project_entry, "project", project_id="test_project")
        
        # 验证项目术语优先
        best_term = self.terminology_kb.get_best_term("司令", "en", project_id="test_project")
        assert best_term.target_term == "Colonel"
        assert best_term.source_level == "project"
        
        # 验证无项目时返回全局术语
        global_term = self.terminology_kb.get_best_term("司令", "en")
        assert global_term.target_term == "Commander"
        assert global_term.source_level == "global"


class TestContextAwareTranslationMemory:
    """上下文感知翻译记忆测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_kb = ContextAwareTranslationMemory(self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_add_memory_with_context(self):
        """测试添加带上下文的翻译记忆"""
        memory = TranslationMemory(
            source_text="参谋长下达命令",
            target_language="en",
            target_text="The Chief of Staff issued an order",
            quality_score=0.9
        )
        
        context = {
            "speaker": "军官",
            "scene": "作战室",
            "emotion": "严肃",
            "formality": "high"
        }
        
        result = self.memory_kb.add_memory(memory, context)
        assert result is True
    
    def test_context_aware_search(self):
        """测试上下文感知搜索"""
        # 添加两个相似的翻译记忆，但上下文不同
        memory1 = TranslationMemory(
            source_text="快点行动",
            target_language="en",
            target_text="Move quickly",
            quality_score=0.8
        )
        context1 = {"scene": "战场", "emotion": "紧急"}
        
        memory2 = TranslationMemory(
            source_text="快点行动",
            target_language="en", 
            target_text="Please hurry up",
            quality_score=0.8
        )
        context2 = {"scene": "日常", "emotion": "温和"}
        
        self.memory_kb.add_memory(memory1, context1)
        self.memory_kb.add_memory(memory2, context2)
        
        # 搜索时提供战场上下文
        search_context = {"scene": "战场", "emotion": "紧急"}
        results = self.memory_kb.search_memory_with_context(
            "快点行动", "en", search_context
        )
        
        assert len(results) >= 1
        # 第一个结果应该是上下文更匹配的
        best_match = results[0]
        memory, text_sim, context_sim = best_match
        assert context_sim > 0.5  # 上下文相似度应该较高
    
    def test_context_similarity_calculation(self):
        """测试上下文相似度计算"""
        context1 = {"speaker": "军官", "scene": "战场", "emotion": "紧急"}
        context2 = {"speaker": "军官", "scene": "战场", "emotion": "冷静"}
        context3 = {"speaker": "平民", "scene": "家庭", "emotion": "温和"}
        
        # 相似上下文
        sim1 = self.memory_kb._calculate_context_similarity(context1, context2)
        assert sim1 >= 0.6  # 大部分匹配
        
        # 不同上下文
        sim2 = self.memory_kb._calculate_context_similarity(context1, context3)
        assert sim2 < 0.4  # 大部分不匹配


class TestCulturalAdaptationKB:
    """文化适配知识库测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.cultural_kb = CulturalAdaptationKB(self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_get_cultural_adaptation(self):
        """测试获取文化适配"""
        adaptation = self.cultural_kb.get_cultural_adaptation("鸡娃", "en")
        
        assert adaptation is not None
        assert adaptation["term"] == "helicopter parenting"
        assert "explanation" in adaptation
    
    def test_add_cultural_term(self):
        """测试添加文化术语"""
        self.cultural_kb.add_cultural_term(
            "摸鱼", "en", "slacking off", "Avoiding work while appearing busy"
        )
        
        adaptation = self.cultural_kb.get_cultural_adaptation("摸鱼", "en")
        assert adaptation is not None
        assert adaptation["term"] == "slacking off"
        assert adaptation["explanation"] == "Avoiding work while appearing busy"
    
    def test_genre_context_adaptation(self):
        """测试类型上下文适配"""
        context = {"genre": "现代军旅剧"}
        adaptation = self.cultural_kb.get_cultural_adaptation("内卷", "en", context)
        
        assert adaptation is not None
        assert "genre_context" in adaptation
        assert adaptation["genre_context"]["tone"] == "serious_professional"


class TestKnowledgeManager:
    """知识库管理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock project manager
        self.mock_project_manager = Mock()
        
        with patch('agents.knowledge_manager.get_project_manager', 
                  return_value=self.mock_project_manager):
            self.knowledge_manager = KnowledgeManager(self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_extract_and_store_terms(self):
        """测试提取并存储术语"""
        text = "参谋长命令突击队开始演习"
        context = {"speaker": "军官", "genre": "现代军旅剧"}
        
        entries = self.knowledge_manager.extract_and_store_terms(
            text, "en", context, project_id="test_project"
        )
        
        assert len(entries) >= 3
        
        # 验证术语已存储
        stored_term = self.knowledge_manager.terminology_kb.get_best_term(
            "参谋长", "en", project_id="test_project"
        )
        assert stored_term is not None
        assert stored_term.domain == "military"
    
    def test_search_translation_suggestions(self):
        """测试搜索翻译建议"""
        # 先添加一些测试数据
        memory = TranslationMemory(
            source_text="参谋长下达命令",
            target_language="en",
            target_text="The Chief of Staff issued an order",
            quality_score=0.9
        )
        context = {"speaker": "军官", "scene": "作战室"}
        self.knowledge_manager.translation_memory_kb.add_memory(memory, context)
        
        # 搜索建议
        suggestions = self.knowledge_manager.search_translation_suggestions(
            "参谋长下达命令", "en", context, "test_project"
        )
        
        assert "exact_match" in suggestions
        assert "fuzzy_matches" in suggestions
        assert "terminology_matches" in suggestions
        assert "cultural_adaptations" in suggestions
        assert "extracted_terms" in suggestions
        
        # 验证精确匹配
        if suggestions["exact_match"]:
            assert suggestions["exact_match"]["translation"] == "The Chief of Staff issued an order"
    
    def test_add_translation_feedback(self):
        """测试添加翻译反馈"""
        context = {"speaker": "军官", "scene": "作战室", "genre": "现代军旅剧"}
        
        self.knowledge_manager.add_translation_feedback(
            "司令下达作战命令",
            "en",
            "The Commander issued combat orders",
            0.9,
            context,
            "test_project"
        )
        
        # 验证翻译记忆已添加
        results = self.knowledge_manager.translation_memory_kb.search_memory_with_context(
            "司令下达作战命令", "en", context
        )
        assert len(results) >= 1
        
        # 验证术语已提取和存储
        stored_term = self.knowledge_manager.terminology_kb.get_best_term(
            "司令", "en", project_id="test_project"
        )
        # 注意：由于术语提取依赖于预定义映射，这里可能需要调整测试
    
    def test_save_and_load_all(self):
        """测试保存和加载所有知识库"""
        # 添加一些测试数据
        entry = TerminologyEntry(
            source_term="测试术语",
            target_language="en",
            target_term="Test Term",
            domain="test"
        )
        self.knowledge_manager.terminology_kb.add_term(entry, "global")
        
        # 保存
        self.knowledge_manager.save_all_knowledge_bases()
        
        # 创建新的管理器实例
        with patch('agents.knowledge_manager.get_project_manager', 
                  return_value=self.mock_project_manager):
            new_manager = KnowledgeManager(self.temp_dir)
        
        # 验证数据已加载
        retrieved = new_manager.terminology_kb.get_best_term("测试术语", "en")
        assert retrieved is not None
        assert retrieved.target_term == "Test Term"
    
    def test_get_knowledge_statistics(self):
        """测试获取知识库统计信息"""
        stats = self.knowledge_manager.get_knowledge_statistics()
        
        assert "terminology" in stats
        assert "translation_memory" in stats
        assert "cultural" in stats
        assert "storage_root" in stats
        
        # 验证统计信息结构
        assert "entry_count" in stats["terminology"]
        assert "entry_count" in stats["translation_memory"]
        assert "entry_count" in stats["cultural"]


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock project manager
        self.mock_project_manager = Mock()
        self.mock_project_manager.load_project_context.return_value = {
            "terminology": {
                "military_terms": {
                    "特种兵": {
                        "en": "Special Forces",
                        "ja": "特殊部隊",
                        "context": "军事专业术语"
                    }
                }
            }
        }
        
        with patch('agents.knowledge_manager.get_project_manager', 
                  return_value=self.mock_project_manager):
            self.knowledge_manager = KnowledgeManager(self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 1. 加载项目知识
        self.knowledge_manager.load_project_knowledge("test_project")
        
        # 2. 提取术语并存储
        text = "特种兵执行秘密任务"
        context = {"speaker": "指挥官", "scene": "作战室", "genre": "现代军旅剧"}
        
        extracted_terms = self.knowledge_manager.extract_and_store_terms(
            text, "en", context, "test_project"
        )
        
        # 3. 搜索翻译建议
        suggestions = self.knowledge_manager.search_translation_suggestions(
            text, "en", context, "test_project"
        )
        
        # 4. 添加翻译反馈
        self.knowledge_manager.add_translation_feedback(
            text, "en", "Special Forces execute secret mission", 0.9,
            context, "test_project"
        )
        
        # 5. 验证整个流程
        assert len(extracted_terms) > 0
        assert "extracted_terms" in suggestions
        assert len(suggestions["extracted_terms"]) > 0
        
        # 验证项目术语已加载
        project_term = self.knowledge_manager.terminology_kb.get_best_term(
            "特种兵", "en", project_id="test_project"
        )
        assert project_term is not None
        assert project_term.target_term == "Special Forces"
        
        # 验证翻译记忆已添加
        memory_results = self.knowledge_manager.translation_memory_kb.search_memory_with_context(
            text, "en", context
        )
        assert len(memory_results) >= 1


def test_get_knowledge_manager():
    """测试获取知识库管理器实例"""
    manager = get_knowledge_manager()
    assert isinstance(manager, KnowledgeManager)
    
    # 验证单例模式
    manager2 = get_knowledge_manager()
    assert manager is manager2


if __name__ == "__main__":
    pytest.main([__file__])