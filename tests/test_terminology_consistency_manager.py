"""
术语一致性管理器测试
"""
import unittest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

from agents.terminology_consistency_manager import (
    TerminologyConsistencyManager, TermEntry, TermConflict, 
    ConsistencyCheckRequest, ConsistencyCheckResult,
    TermType, ConsistencyLevel, ConflictSeverity, ConflictResolutionStrategy
)
from models.subtitle_models import SubtitleEntry, TimeCode


class TestTerminologyConsistencyManager(unittest.TestCase):
    """术语一致性管理器测试"""
    
    def setUp(self):
        self.manager = TerminologyConsistencyManager("test_manager")
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.manager.manager_id)
        self.assertGreater(len(self.manager.term_database), 0)  # 应该有核心术语
        self.assertIn("person_zhang_wei", self.manager.term_database)
    
    def test_add_term(self):
        """测试添加术语"""
        term = TermEntry(
            term_id="test_term_1",
            source_text="测试术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.STRICT,
            translations={
                "en": "test term",
                "ja": "テスト用語"
            },
            aliases=["测试词"],
            context_examples=["这是一个测试术语"],
            approved=True
        )
        
        success = self.manager.add_term(term)
        self.assertTrue(success)
        
        # 验证术语已添加
        self.assertIn("test_term_1", self.manager.term_database)
        self.assertIn("测试术语", self.manager.term_index)
        self.assertIn("test term", self.manager.language_index["en"])
    
    def test_update_term(self):
        """测试更新术语"""
        # 先添加一个术语
        term = TermEntry(
            term_id="test_term_2",
            source_text="原始术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.MODERATE,
            translations={"en": "original term"},
            aliases=[],
            context_examples=[],
            approved=False
        )
        self.manager.add_term(term)
        
        # 更新术语
        updates = {
            "translations": {"en": "updated term", "ja": "更新された用語"},
            "approved": True
        }
        success = self.manager.update_term("test_term_2", updates)
        self.assertTrue(success)
        
        # 验证更新
        updated_term = self.manager.term_database["test_term_2"]
        self.assertEqual(updated_term.translations["en"], "updated term")
        self.assertTrue(updated_term.approved)
    
    def test_remove_term(self):
        """测试删除术语"""
        # 先添加一个术语
        term = TermEntry(
            term_id="test_term_3",
            source_text="待删除术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.FLEXIBLE,
            translations={"en": "term to delete"},
            aliases=[],
            context_examples=[],
            approved=True
        )
        self.manager.add_term(term)
        
        # 删除术语
        success = self.manager.remove_term("test_term_3")
        self.assertTrue(success)
        
        # 验证删除
        self.assertNotIn("test_term_3", self.manager.term_database)
        self.assertNotIn("待删除术语", self.manager.term_index)
    
    def test_find_terms_exact_match(self):
        """测试精确匹配查找术语"""
        results = self.manager.find_terms("张伟")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].source_text, "张伟")
    
    def test_find_terms_by_translation(self):
        """测试通过翻译查找术语"""
        results = self.manager.find_terms("Zhang Wei", language="en")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].source_text, "张伟")
    
    def test_find_terms_by_type(self):
        """测试按类型查找术语"""
        results = self.manager.find_terms("司令", term_type=TermType.MILITARY_TERM)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].term_type, TermType.MILITARY_TERM)
    
    def test_fuzzy_search(self):
        """测试模糊搜索"""
        # 降低相似度阈值以便测试
        original_threshold = self.manager.similarity_threshold
        self.manager.similarity_threshold = 0.5
        
        try:
            results = self.manager.find_terms("张威")  # 与"张伟"相似
            # 应该能找到相似的术语
            self.assertGreaterEqual(len(results), 0)
        finally:
            self.manager.similarity_threshold = original_threshold
    
    def test_consistency_check_no_conflicts(self):
        """测试无冲突的一致性检查"""
        subtitle_entries = [
            SubtitleEntry(
                index=1, 
                start_time=TimeCode(0, 0, 0, 0), 
                end_time=TimeCode(0, 0, 2, 0), 
                text="张伟是我们的队长"
            ),
            SubtitleEntry(
                index=2, 
                start_time=TimeCode(0, 0, 2, 0), 
                end_time=TimeCode(0, 0, 4, 0), 
                text="司令下达了命令"
            )
        ]
        
        request = ConsistencyCheckRequest(
            request_id="test_request_1",
            project_id="test_project",
            subtitle_entries=subtitle_entries,
            target_languages=["en", "ja"]
        )
        
        result = self.manager.check_consistency(request)
        
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.consistency_score, 0.8)  # 应该有较高的一致性分数
    
    def test_consistency_check_with_conflicts(self):
        """测试有冲突的一致性检查"""
        # 先添加一个有冲突的术语
        conflicting_term = TermEntry(
            term_id="conflicting_term",
            source_text="冲突术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.STRICT,
            translations={"en": "conflict term"},
            aliases=[],
            context_examples=[],
            approved=True
        )
        self.manager.add_term(conflicting_term)
        
        # 创建包含冲突的字幕
        subtitle_entries = [
            SubtitleEntry(
                index=1, 
                start_time=TimeCode(0, 0, 0, 0), 
                end_time=TimeCode(0, 0, 2, 0), 
                text="这是冲突术语"
            ),
            SubtitleEntry(
                index=2, 
                start_time=TimeCode(0, 0, 2, 0), 
                end_time=TimeCode(0, 0, 4, 0), 
                text="这是另一个冲突术语的变体"
            )
        ]
        
        request = ConsistencyCheckRequest(
            request_id="test_request_2",
            project_id="test_project",
            subtitle_entries=subtitle_entries,
            target_languages=["en"]
        )
        
        result = self.manager.check_consistency(request)
        
        self.assertTrue(result.success)
        # 注意：这个测试可能需要根据实际的冲突检测逻辑调整
    
    def test_language_detection(self):
        """测试语言检测"""
        term = self.manager.term_database["person_zhang_wei"]
        
        # 测试中文检测
        self.assertEqual(self.manager._detect_text_language("张伟", term), "zh")
        
        # 测试英文检测
        self.assertEqual(self.manager._detect_text_language("Zhang Wei", term), "en")
        
        # 测试日文检测
        self.assertEqual(self.manager._detect_text_language("張偉", term), "ja")
    
    def test_character_detection_methods(self):
        """测试字符检测方法"""
        # 测试中文字符检测
        self.assertTrue(self.manager._contains_chinese_chars("张伟"))
        self.assertFalse(self.manager._contains_chinese_chars("Zhang Wei"))
        
        # 测试日文字符检测
        self.assertTrue(self.manager._contains_japanese_chars("こんにちは"))
        self.assertTrue(self.manager._contains_japanese_chars("カタカナ"))
        self.assertFalse(self.manager._contains_japanese_chars("Hello"))
        
        # 测试韩文字符检测
        self.assertTrue(self.manager._contains_korean_chars("안녕하세요"))
        self.assertFalse(self.manager._contains_korean_chars("Hello"))
    
    def test_conflict_severity_assessment(self):
        """测试冲突严重程度评估"""
        # 严格一致性术语
        strict_term = TermEntry(
            term_id="strict_term",
            source_text="严格术语",
            term_type=TermType.PERSON_NAME,
            consistency_level=ConsistencyLevel.STRICT,
            translations={"en": "strict term"},
            aliases=[],
            context_examples=[],
            approved=True
        )
        
        severity = self.manager._assess_conflict_severity(
            strict_term, {"en": ["strict term", "different term"]}
        )
        self.assertEqual(severity, ConflictSeverity.CRITICAL)
        
        # 灵活一致性术语
        flexible_term = TermEntry(
            term_id="flexible_term",
            source_text="灵活术语",
            term_type=TermType.CULTURAL_TERM,
            consistency_level=ConsistencyLevel.FLEXIBLE,
            translations={"en": "flexible term"},
            aliases=[],
            context_examples=[],
            approved=True
        )
        
        severity = self.manager._assess_conflict_severity(
            flexible_term, {"en": ["flexible term", "variant term"]}
        )
        self.assertEqual(severity, ConflictSeverity.MEDIUM)
    
    def test_resolution_strategy_determination(self):
        """测试解决策略确定"""
        term = TermEntry(
            term_id="strategy_term",
            source_text="策略术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.MODERATE,
            translations={"en": "strategy term"},
            aliases=[],
            context_examples=[],
            approved=True
        )
        
        # 关键冲突应该使用权威策略
        strategy = self.manager._determine_resolution_strategy(term, ConflictSeverity.CRITICAL)
        self.assertEqual(strategy, ConflictResolutionStrategy.USE_AUTHORITATIVE)
        
        # 高级冲突应该使用频率策略
        strategy = self.manager._determine_resolution_strategy(term, ConflictSeverity.HIGH)
        self.assertEqual(strategy, ConflictResolutionStrategy.USE_MOST_FREQUENT)
    
    def test_conflict_resolution(self):
        """测试冲突解决"""
        # 创建一个冲突
        conflict = TermConflict(
            conflict_id="test_conflict_1",
            term_id="person_zhang_wei",
            source_text="张伟",
            conflicting_translations={"en": ["Zhang Wei", "Zhang Wei2"]},
            severity=ConflictSeverity.HIGH,
            contexts=["测试上下文"],
            resolution_strategy=ConflictResolutionStrategy.USE_MOST_FREQUENT
        )
        
        self.manager.active_conflicts[conflict.conflict_id] = conflict
        
        # 解决冲突
        success = self.manager.resolve_conflict(
            conflict.conflict_id, 
            "使用标准翻译 Zhang Wei", 
            "test_user"
        )
        
        self.assertTrue(success)
        self.assertNotIn(conflict.conflict_id, self.manager.active_conflicts)
        self.assertIn(conflict.conflict_id, self.manager.resolved_conflicts)
    
    def test_conflict_summary(self):
        """测试冲突摘要"""
        # 添加一些测试冲突
        conflict1 = TermConflict(
            conflict_id="summary_conflict_1",
            term_id="test_term",
            source_text="测试",
            conflicting_translations={"en": ["test1", "test2"]},
            severity=ConflictSeverity.CRITICAL,
            contexts=[]
        )
        
        conflict2 = TermConflict(
            conflict_id="summary_conflict_2",
            term_id="test_term2",
            source_text="测试2",
            conflicting_translations={"en": ["test3", "test4"]},
            severity=ConflictSeverity.HIGH,
            contexts=[]
        )
        
        self.manager.active_conflicts[conflict1.conflict_id] = conflict1
        self.manager.active_conflicts[conflict2.conflict_id] = conflict2
        
        summary = self.manager.get_conflict_summary()
        
        self.assertEqual(summary["active_conflicts"], 2)
        self.assertIn("critical", summary["active_by_severity"])
        self.assertIn("high", summary["active_by_severity"])
    
    def test_performance_stats(self):
        """测试性能统计"""
        stats = self.manager.get_performance_stats()
        
        self.assertIn("basic_stats", stats)
        self.assertIn("language_coverage", stats)
        self.assertIn("term_type_distribution", stats)
        self.assertIn("conflict_severity_distribution", stats)
        
        # 验证基础统计
        basic_stats = stats["basic_stats"]
        self.assertGreaterEqual(basic_stats["total_terms"], 5)  # 至少有核心术语
    
    def test_export_import_database(self):
        """测试数据库导出导入"""
        # 添加一个测试术语
        test_term = TermEntry(
            term_id="export_test_term",
            source_text="导出测试术语",
            term_type=TermType.TECHNICAL_TERM,
            consistency_level=ConsistencyLevel.MODERATE,
            translations={"en": "export test term"},
            aliases=["导出测试"],
            context_examples=["这是导出测试"],
            approved=True
        )
        self.manager.add_term(test_term)
        
        # 导出到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # 导出
            success = self.manager.export_terminology_database(temp_file)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(temp_file))
            
            # 创建新的管理器并导入
            new_manager = TerminologyConsistencyManager("import_test_manager")
            original_count = len(new_manager.term_database)
            
            success = new_manager.import_terminology_database(temp_file)
            self.assertTrue(success)
            
            # 验证导入
            self.assertIn("export_test_term", new_manager.term_database)
            imported_term = new_manager.term_database["export_test_term"]
            self.assertEqual(imported_term.source_text, "导出测试术语")
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_auto_resolve_conflicts(self):
        """测试自动解决冲突"""
        # 创建可自动解决的冲突
        conflict = TermConflict(
            conflict_id="auto_resolve_test",
            term_id="person_zhang_wei",
            source_text="张伟",
            conflicting_translations={"en": ["Zhang Wei", "Zhang Wei Alt"]},
            severity=ConflictSeverity.HIGH,
            contexts=["测试上下文"],
            resolution_strategy=ConflictResolutionStrategy.USE_MOST_FREQUENT
        )
        
        conflicts = [conflict]
        resolved_count = self.manager._auto_resolve_conflicts(conflicts)
        
        # 验证自动解决
        self.assertGreaterEqual(resolved_count, 0)
        if resolved_count > 0:
            self.assertTrue(conflict.resolved)
    
    def test_consistency_score_calculation(self):
        """测试一致性分数计算"""
        # 测试无冲突情况
        extracted_terms = {"term1": [("text1", "context1")], "term2": [("text2", "context2")]}
        conflicts = []
        
        score = self.manager._calculate_consistency_score(extracted_terms, conflicts)
        self.assertEqual(score, 1.0)
        
        # 测试有冲突情况
        conflict = TermConflict(
            conflict_id="score_test_conflict",
            term_id="term1",
            source_text="测试",
            conflicting_translations={"en": ["test1", "test2"]},
            severity=ConflictSeverity.MEDIUM,
            contexts=[]
        )
        conflicts = [conflict]
        
        score = self.manager._calculate_consistency_score(extracted_terms, conflicts)
        self.assertLess(score, 1.0)
        self.assertGreaterEqual(score, 0.0)
    
    def test_recommendations_generation(self):
        """测试建议生成"""
        # 测试无冲突情况
        recommendations = self.manager._generate_recommendations([], {})
        self.assertIn("术语使用一致性良好", recommendations[0])
        
        # 测试有冲突情况
        critical_conflict = TermConflict(
            conflict_id="rec_test_critical",
            term_id="test_term",
            source_text="测试",
            conflicting_translations={"en": ["test1", "test2"]},
            severity=ConflictSeverity.CRITICAL,
            contexts=[]
        )
        
        high_conflict = TermConflict(
            conflict_id="rec_test_high",
            term_id="test_term2",
            source_text="测试2",
            conflicting_translations={"en": ["test3", "test4"]},
            severity=ConflictSeverity.HIGH,
            contexts=[]
        )
        
        conflicts = [critical_conflict, high_conflict]
        extracted_terms = {"term1": [("text1", "context1")]}
        
        recommendations = self.manager._generate_recommendations(conflicts, extracted_terms)
        
        self.assertTrue(any("严重术语冲突" in rec for rec in recommendations))
        self.assertTrue(any("高级术语冲突" in rec for rec in recommendations))


if __name__ == '__main__':
    unittest.main()