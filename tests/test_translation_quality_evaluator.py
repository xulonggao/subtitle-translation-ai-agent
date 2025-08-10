"""
翻译质量评估器测试
"""
import unittest
import asyncio
from datetime import datetime

from agents.translation_quality_evaluator import (
    TranslationQualityEvaluator, QualityEvaluationRequest, QualityEvaluationResult,
    QualityDimension, QualityLevel, EvaluationMethod, QualityMetric, QualityIssue
)
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationResult


class TestTranslationQualityEvaluator(unittest.TestCase):
    """翻译质量评估器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.evaluator = TranslationQualityEvaluator("test_evaluator")
        
        # 创建测试数据
        self.original_entries = [
            SubtitleEntry(
                index=1,
                start_time=0.0,
                end_time=3.0,
                text="欢迎收看《爱上海军蓝》，我是主持人张伟。",
                speaker="张伟"
            ),
            SubtitleEntry(
                index=2,
                start_time=3.0,
                end_time=6.0,
                text="今天我们邀请到了海军司令李明将军。",
                speaker="张伟"
            ),
            SubtitleEntry(
                index=3,
                start_time=6.0,
                end_time=9.0,
                text="司令，请您介绍一下我们海军的雷达系统。",
                speaker="张伟"
            )
        ]
        
        # 创建高质量翻译结果
        self.good_translation_results = [
            TranslationResult(
                original_index=1,
                translated_text="Welcome to 'Love Navy Blue', I'm host Zhang Wei.",
                target_language="en",
                success=True,
                quality_score=0.9,
                confidence=0.95
            ),
            TranslationResult(
                original_index=2,
                translated_text="Today we have invited Navy Commander General Li Ming.",
                target_language="en",
                success=True,
                quality_score=0.85,
                confidence=0.9
            ),
            TranslationResult(
                original_index=3,
                translated_text="Commander, please introduce our navy's radar system.",
                target_language="en",
                success=True,
                quality_score=0.88,
                confidence=0.92
            )
        ]
        
        # 创建低质量翻译结果
        self.poor_translation_results = [
            TranslationResult(
                original_index=1,
                translated_text="",  # 空翻译
                target_language="en",
                success=False,
                quality_score=0.0,
                confidence=0.0
            ),
            TranslationResult(
                original_index=2,
                translated_text="Today we have invite Navy Commander General Li Ming.",  # 语法错误
                target_language="en",
                success=True,
                quality_score=0.6,
                confidence=0.7
            ),
            TranslationResult(
                original_index=3,
                translated_text="Commander, please introduce our navy radar system radar system.",  # 重复
                target_language="en",
                success=True,
                quality_score=0.5,
                confidence=0.6
            )
        ]
    
    def test_evaluator_initialization(self):
        """测试评估器初始化"""
        self.assertIsNotNone(self.evaluator.evaluator_id)
        self.assertIn(QualityDimension.ACCURACY, self.evaluator.dimension_weights)
        self.assertIn(QualityDimension.FLUENCY, self.evaluator.dimension_weights)
        self.assertIn("en", self.evaluator.language_configs)
        self.assertIn("ja", self.evaluator.language_configs)
    
    def test_quality_evaluation_request_creation(self):
        """测试质量评估请求创建"""
        request = QualityEvaluationRequest(
            request_id="test_request_1",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        self.assertEqual(request.request_id, "test_request_1")
        self.assertEqual(len(request.original_entries), 3)
        self.assertEqual(len(request.translation_results), 3)
        self.assertEqual(request.target_language, "en")
        self.assertIsNotNone(request.timestamp)
    
    def test_good_quality_evaluation(self):
        """测试高质量翻译的评估"""
        request = QualityEvaluationRequest(
            request_id="test_good_quality",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        result = asyncio.run(self.evaluator.evaluate_quality(request))
        
        self.assertTrue(result.overall_score > 0.7)
        self.assertIn(result.quality_level, [QualityLevel.GOOD, QualityLevel.EXCELLENT, QualityLevel.ACCEPTABLE])
        self.assertEqual(len(result.dimension_scores), 7)  # 7个评估维度
        self.assertGreater(result.confidence, 0.5)
        self.assertGreaterEqual(result.processing_time_ms, 0)
    
    def test_poor_quality_evaluation(self):
        """测试低质量翻译的评估"""
        request = QualityEvaluationRequest(
            request_id="test_poor_quality",
            original_entries=self.original_entries,
            translation_results=self.poor_translation_results,
            target_language="en"
        )
        
        result = asyncio.run(self.evaluator.evaluate_quality(request))
        
        self.assertTrue(result.overall_score < 0.7)
        self.assertIn(result.quality_level, [QualityLevel.POOR, QualityLevel.UNACCEPTABLE])
        self.assertGreater(len(result.issues_found), 0)  # 应该发现问题
        self.assertGreater(len(result.recommendations), 0)  # 应该有建议
    
    def test_accuracy_evaluation(self):
        """测试准确性评估"""
        request = QualityEvaluationRequest(
            request_id="test_accuracy",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        accuracy_metric = asyncio.run(self.evaluator._evaluate_accuracy(request))
        
        self.assertEqual(accuracy_metric.dimension, QualityDimension.ACCURACY)
        self.assertGreater(accuracy_metric.score, 0.0)
        self.assertLessEqual(accuracy_metric.score, 1.0)
        self.assertGreater(accuracy_metric.confidence, 0.0)
    
    def test_fluency_evaluation(self):
        """测试流畅性评估"""
        request = QualityEvaluationRequest(
            request_id="test_fluency",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        fluency_metric = asyncio.run(self.evaluator._evaluate_fluency(request))
        
        self.assertEqual(fluency_metric.dimension, QualityDimension.FLUENCY)
        self.assertGreater(fluency_metric.score, 0.0)
        self.assertLessEqual(fluency_metric.score, 1.0)
    
    def test_cultural_adaptation_evaluation(self):
        """测试文化适配性评估"""
        # 创建包含敬语的测试数据
        cultural_entries = [
            SubtitleEntry(
                index=1,
                start_time=0.0,
                end_time=3.0,
                text="司令，您好！",
                speaker="士兵"
            )
        ]
        
        # 日语翻译结果
        japanese_results = [
            TranslationResult(
                original_index=1,
                translated_text="司令官、こんにちは！",
                target_language="ja",
                success=True,
                quality_score=0.9
            )
        ]
        
        request = QualityEvaluationRequest(
            request_id="test_cultural",
            original_entries=cultural_entries,
            translation_results=japanese_results,
            target_language="ja"
        )
        
        cultural_metric = asyncio.run(self.evaluator._evaluate_cultural_adaptation(request))
        
        self.assertEqual(cultural_metric.dimension, QualityDimension.CULTURAL_ADAPTATION)
        self.assertGreater(cultural_metric.score, 0.0)
    
    def test_consistency_evaluation(self):
        """测试一致性评估"""
        request = QualityEvaluationRequest(
            request_id="test_consistency",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        consistency_metric = asyncio.run(self.evaluator._evaluate_consistency(request))
        
        self.assertEqual(consistency_metric.dimension, QualityDimension.CONSISTENCY)
        self.assertGreater(consistency_metric.score, 0.0)
    
    def test_completeness_evaluation(self):
        """测试完整性评估"""
        request = QualityEvaluationRequest(
            request_id="test_completeness",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        completeness_metric = asyncio.run(self.evaluator._evaluate_completeness(request))
        
        self.assertEqual(completeness_metric.dimension, QualityDimension.COMPLETENESS)
        self.assertGreater(completeness_metric.score, 0.0)
    
    def test_readability_evaluation(self):
        """测试可读性评估"""
        request = QualityEvaluationRequest(
            request_id="test_readability",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        readability_metric = asyncio.run(self.evaluator._evaluate_readability(request))
        
        self.assertEqual(readability_metric.dimension, QualityDimension.READABILITY)
        self.assertGreater(readability_metric.score, 0.0)
    
    def test_timing_sync_evaluation(self):
        """测试时间同步性评估"""
        request = QualityEvaluationRequest(
            request_id="test_timing",
            original_entries=self.original_entries,
            translation_results=self.good_translation_results,
            target_language="en"
        )
        
        timing_metric = asyncio.run(self.evaluator._evaluate_timing_sync(request))
        
        self.assertEqual(timing_metric.dimension, QualityDimension.TIMING_SYNC)
        self.assertGreater(timing_metric.score, 0.0)
    
    def test_overall_score_calculation(self):
        """测试总体分数计算"""
        dimension_scores = {
            QualityDimension.ACCURACY: QualityMetric(
                dimension=QualityDimension.ACCURACY,
                score=0.9,
                weight=0.3,
                confidence=0.8
            ),
            QualityDimension.FLUENCY: QualityMetric(
                dimension=QualityDimension.FLUENCY,
                score=0.8,
                weight=0.25,
                confidence=0.7
            )
        }
        
        overall_score = self.evaluator._calculate_overall_score(dimension_scores)
        
        self.assertGreater(overall_score, 0.0)
        self.assertLessEqual(overall_score, 1.0)
    
    def test_quality_level_determination(self):
        """测试质量等级确定"""
        self.assertEqual(self.evaluator._determine_quality_level(0.95), QualityLevel.EXCELLENT)
        self.assertEqual(self.evaluator._determine_quality_level(0.85), QualityLevel.GOOD)
        self.assertEqual(self.evaluator._determine_quality_level(0.75), QualityLevel.ACCEPTABLE)
        self.assertEqual(self.evaluator._determine_quality_level(0.65), QualityLevel.POOR)
        self.assertEqual(self.evaluator._determine_quality_level(0.5), QualityLevel.UNACCEPTABLE)
    
    def test_quality_issues_detection(self):
        """测试质量问题检测"""
        # 创建低分数的维度分数
        low_dimension_scores = {
            QualityDimension.ACCURACY: QualityMetric(
                dimension=QualityDimension.ACCURACY,
                score=0.5,  # 低分
                weight=0.3,
                confidence=0.8
            )
        }
        
        request = QualityEvaluationRequest(
            request_id="test_issues",
            original_entries=self.original_entries,
            translation_results=self.poor_translation_results,
            target_language="en"
        )
        
        issues = asyncio.run(self.evaluator._detect_quality_issues(request, low_dimension_scores))
        
        self.assertGreater(len(issues), 0)
        
        # 检查问题类型
        issue_types = [issue.issue_type for issue in issues]
        self.assertIn("low_accuracy", issue_types)
    
    def test_recommendations_generation(self):
        """测试建议生成"""
        low_dimension_scores = {
            QualityDimension.ACCURACY: QualityMetric(
                dimension=QualityDimension.ACCURACY,
                score=0.6,
                weight=0.3,
                confidence=0.8
            ),
            QualityDimension.FLUENCY: QualityMetric(
                dimension=QualityDimension.FLUENCY,
                score=0.5,
                weight=0.25,
                confidence=0.7
            )
        }
        
        issues = [
            QualityIssue(
                issue_id="test_issue",
                issue_type="translation_failure",
                severity="critical",
                description="测试问题"
            )
        ]
        
        recommendations = self.evaluator._generate_recommendations(low_dimension_scores, issues)
        
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any("准确性" in rec for rec in recommendations))
        self.assertTrue(any("流畅" in rec for rec in recommendations))
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        dimension_scores = {
            QualityDimension.ACCURACY: QualityMetric(
                dimension=QualityDimension.ACCURACY,
                score=0.9,
                weight=0.3,
                confidence=0.8
            ),
            QualityDimension.FLUENCY: QualityMetric(
                dimension=QualityDimension.FLUENCY,
                score=0.8,
                weight=0.25,
                confidence=0.7
            )
        }
        
        issues = []
        confidence = self.evaluator._calculate_confidence(dimension_scores, issues)
        
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # 测试有严重问题时的置信度
        critical_issues = [
            QualityIssue(
                issue_id="critical_issue",
                issue_type="translation_failure",
                severity="critical",
                description="严重问题"
            )
        ]
        
        confidence_with_issues = self.evaluator._calculate_confidence(dimension_scores, critical_issues)
        self.assertLess(confidence_with_issues, confidence)
    
    def test_evaluation_statistics(self):
        """测试评估统计"""
        # 执行几次评估
        for i in range(3):
            request = QualityEvaluationRequest(
                request_id=f"test_stats_{i}",
                original_entries=self.original_entries,
                translation_results=self.good_translation_results,
                target_language="en"
            )
            asyncio.run(self.evaluator.evaluate_quality(request))
        
        stats = self.evaluator.get_evaluation_statistics()
        
        self.assertEqual(stats["total_evaluations"], 3)
        self.assertIn("average_scores", stats)
        self.assertIn("language_stats", stats)
        self.assertIn("en", stats["language_stats"])
        self.assertGreater(len(stats["processing_times"]), 0)
    
    def test_language_specific_configs(self):
        """测试语言特定配置"""
        # 测试英语配置
        en_config = self.evaluator.language_configs["en"]
        self.assertIn("max_chars_per_line", en_config)
        self.assertIn("reading_speed_cps", en_config)
        self.assertFalse(en_config["honorific_required"])
        
        # 测试日语配置
        ja_config = self.evaluator.language_configs["ja"]
        self.assertTrue(ja_config["honorific_required"])
        self.assertLess(ja_config["reading_speed_cps"], en_config["reading_speed_cps"])
        
        # 测试韩语配置
        ko_config = self.evaluator.language_configs["ko"]
        self.assertTrue(ko_config["honorific_required"])
        
        # 测试阿拉伯语配置
        ar_config = self.evaluator.language_configs["ar"]
        self.assertTrue(ar_config.get("rtl_text", False))
    
    def test_error_handling(self):
        """测试错误处理"""
        # 创建会导致错误的请求（空数据）
        empty_request = QualityEvaluationRequest(
            request_id="test_error",
            original_entries=[],
            translation_results=[],
            target_language="en"
        )
        
        result = asyncio.run(self.evaluator.evaluate_quality(empty_request))
        
        # 应该返回有效的结果，即使是错误情况
        self.assertIsNotNone(result)
        self.assertEqual(result.request_id, "test_error")
        self.assertGreaterEqual(result.overall_score, 0.0)


class TestQualityDataModels(unittest.TestCase):
    """质量评估数据模型测试"""
    
    def test_quality_metric_creation(self):
        """测试质量指标创建"""
        metric = QualityMetric(
            dimension=QualityDimension.ACCURACY,
            score=0.85,
            weight=0.3,
            confidence=0.9
        )
        
        self.assertEqual(metric.dimension, QualityDimension.ACCURACY)
        self.assertEqual(metric.score, 0.85)
        self.assertEqual(metric.weight, 0.3)
        self.assertEqual(metric.confidence, 0.9)
        self.assertIsInstance(metric.details, dict)
    
    def test_quality_issue_creation(self):
        """测试质量问题创建"""
        issue = QualityIssue(
            issue_id="test_issue_1",
            issue_type="grammar_error",
            severity="medium",
            description="语法错误",
            location="subtitle_1",
            suggestion="修正语法"
        )
        
        self.assertEqual(issue.issue_id, "test_issue_1")
        self.assertEqual(issue.issue_type, "grammar_error")
        self.assertEqual(issue.severity, "medium")
        self.assertEqual(issue.description, "语法错误")
        self.assertEqual(issue.location, "subtitle_1")
        self.assertEqual(issue.suggestion, "修正语法")
    
    def test_quality_evaluation_result_creation(self):
        """测试质量评估结果创建"""
        result = QualityEvaluationResult(
            request_id="test_result_1",
            overall_score=0.85,
            quality_level=QualityLevel.GOOD,
            dimension_scores={},
            issues_found=[],
            recommendations=["建议1", "建议2"]
        )
        
        self.assertEqual(result.request_id, "test_result_1")
        self.assertEqual(result.overall_score, 0.85)
        self.assertEqual(result.quality_level, QualityLevel.GOOD)
        self.assertEqual(len(result.recommendations), 2)
        self.assertIsNotNone(result.timestamp)


if __name__ == '__main__':
    unittest.main()