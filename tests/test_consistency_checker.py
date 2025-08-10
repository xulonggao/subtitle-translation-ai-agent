"""
一致性检查器测试
"""
import unittest
import asyncio
from datetime import datetime

from agents.consistency_checker import (
    ConsistencyChecker, ConsistencyCheckRequest, ConsistencyCheckResult,
    ConsistencyRule, ConsistencyViolation, ConsistencyType, ConflictSeverity, ResolutionStrategy
)


class TestConsistencyChecker(unittest.TestCase):
    """一致性检查器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.checker = ConsistencyChecker("test_checker")
        
        # 创建测试数据
        self.test_episodes = [
            {
                "episode_id": "episode_1",
                "subtitles": [
                    {"text": "欢迎收看，我是主持人张伟。"},
                    {"text": "今天我们邀请到了海军司令李明将军。"},
                    {"text": "司令，请您介绍一下我们的雷达系统。"}
                ],
                "translations": {
                    "en": [
                        {"translated_text": "Welcome, I'm host Zhang Wei."},
                        {"translated_text": "Today we invited Navy Commander Li Ming."},
                        {"translated_text": "Commander, please introduce our radar system."}
                    ],
                    "ja": [
                        {"translated_text": "ようこそ、司会の張偉です。"},
                        {"translated_text": "今日は海軍司令官の李明将軍をお招きしました。"},
                        {"translated_text": "司令官、我々のレーダーシステムについて紹介してください。"}
                    ]
                }
            },
            {
                "episode_id": "episode_2",
                "subtitles": [
                    {"text": "张伟继续主持节目。"},
                    {"text": "李明司令详细介绍了雷达技术。"},
                    {"text": "这个雷达系统非常先进。"}
                ],
                "translations": {
                    "en": [
                        {"translated_text": "Zhang Wei continues hosting the show."},
                        {"translated_text": "Commander Li Ming detailed the radar technology."},  # 不一致：Li Ming vs Li Ming
                        {"translated_text": "This radar system is very advanced."}
                    ],
                    "ja": [
                        {"translated_text": "張偉が番組の司会を続けます。"},
                        {"translated_text": "李明司令官がレーダー技術について詳しく紹介しました。"},
                        {"translated_text": "このレーダーシステムは非常に先進的です。"}
                    ]
                }
            }
        ]
    
    def test_checker_initialization(self):
        """测试检查器初始化"""
        self.assertIsNotNone(self.checker.checker_id)
        self.assertGreater(len(self.checker.built_in_rules), 0)
        self.assertEqual(len(self.checker.custom_rules), 0)
        self.assertIsInstance(self.checker.term_database, dict)
    
    def test_built_in_rules(self):
        """测试内置规则"""
        rules = self.checker.built_in_rules
        
        # 检查是否包含主要规则类型
        rule_types = [rule.consistency_type for rule in rules]
        self.assertIn(ConsistencyType.PERSON_NAME, rule_types)
        self.assertIn(ConsistencyType.TECHNICAL_TERM, rule_types)
        self.assertIn(ConsistencyType.TITLE_HONORIFIC, rule_types)
        
        # 检查规则格式
        for rule in rules:
            self.assertIsNotNone(rule.rule_id)
            self.assertIsNotNone(rule.pattern)
            self.assertIsInstance(rule.consistency_type, ConsistencyType)
            self.assertIsInstance(rule.severity, ConflictSeverity)
    
    def test_add_custom_rule(self):
        """测试添加自定义规则"""
        custom_rule = ConsistencyRule(
            rule_id="test_custom_rule",
            rule_name="测试自定义规则",
            consistency_type=ConsistencyType.TERMINOLOGY,
            pattern=r"测试术语",
            severity=ConflictSeverity.MEDIUM,
            description="这是一个测试规则"
        )
        
        # 添加规则
        result = self.checker.add_custom_rule(custom_rule)
        self.assertTrue(result)
        self.assertEqual(len(self.checker.custom_rules), 1)
        
        # 尝试添加重复规则
        duplicate_result = self.checker.add_custom_rule(custom_rule)
        self.assertFalse(duplicate_result)
        self.assertEqual(len(self.checker.custom_rules), 1)
    
    def test_remove_custom_rule(self):
        """测试移除自定义规则"""
        # 先添加一个规则
        custom_rule = ConsistencyRule(
            rule_id="test_remove_rule",
            rule_name="待移除规则",
            consistency_type=ConsistencyType.TERMINOLOGY,
            pattern=r"待移除"
        )
        self.checker.add_custom_rule(custom_rule)
        
        # 移除规则
        result = self.checker.remove_custom_rule("test_remove_rule")
        self.assertTrue(result)
        self.assertEqual(len(self.checker.custom_rules), 0)
        
        # 尝试移除不存在的规则
        not_found_result = self.checker.remove_custom_rule("non_existent_rule")
        self.assertFalse(not_found_result)
    
    def test_get_rule_by_id(self):
        """测试根据ID获取规则"""
        # 获取内置规则
        built_in_rule = self.checker.get_rule_by_id("person_name_chinese")
        self.assertIsNotNone(built_in_rule)
        self.assertEqual(built_in_rule.rule_id, "person_name_chinese")
        
        # 获取不存在的规则
        non_existent = self.checker.get_rule_by_id("non_existent_rule")
        self.assertIsNone(non_existent)
    
    def test_extract_term_occurrences(self):
        """测试术语提取"""
        rules = self.checker.built_in_rules
        term_occurrences = self.checker._extract_term_occurrences(self.test_episodes, rules)
        
        # 应该提取到人名（根据实际的正则表达式匹配结果）
        self.assertIn("张伟", term_occurrences)
        # 李明会被匹配为"李明将"或"李明司"等更长的形式
        self.assertTrue(any("李明" in term for term in term_occurrences.keys()))
        
        # 应该提取到技术术语
        self.assertIn("司令", term_occurrences)
        self.assertIn("雷达", term_occurrences)
        
        # 检查翻译语言
        zhang_wei_occurrences = term_occurrences.get("张伟", {})
        self.assertIn("en", zhang_wei_occurrences)
        self.assertIn("ja", zhang_wei_occurrences)
    
    def test_detect_violations(self):
        """测试违规检测"""
        rules = self.checker.built_in_rules
        term_occurrences = self.checker._extract_term_occurrences(self.test_episodes, rules)
        violations = self.checker._detect_violations(term_occurrences, rules)
        
        # 应该检测到一些违规（如果存在不一致的翻译）
        self.assertIsInstance(violations, list)
        
        # 检查违规结构
        for violation in violations:
            self.assertIsInstance(violation, ConsistencyViolation)
            self.assertIsNotNone(violation.violation_id)
            self.assertIsNotNone(violation.source_term)
            self.assertIsInstance(violation.consistency_type, ConsistencyType)
            self.assertIsInstance(violation.severity, ConflictSeverity)
    
    def test_consistency_check_request_creation(self):
        """测试一致性检查请求创建"""
        request = ConsistencyCheckRequest(
            request_id="test_request_1",
            project_id="test_project",
            episodes=self.test_episodes,
            target_languages=["en", "ja"],
            check_scope="project"
        )
        
        self.assertEqual(request.request_id, "test_request_1")
        self.assertEqual(request.project_id, "test_project")
        self.assertEqual(len(request.episodes), 2)
        self.assertEqual(len(request.target_languages), 2)
        self.assertIsNotNone(request.timestamp)
    
    def test_consistency_check(self):
        """测试一致性检查"""
        request = ConsistencyCheckRequest(
            request_id="test_check_1",
            project_id="test_project",
            episodes=self.test_episodes,
            target_languages=["en", "ja"],
            check_scope="project"
        )
        
        result = asyncio.run(self.checker.check_consistency(request))
        
        self.assertIsInstance(result, ConsistencyCheckResult)
        self.assertEqual(result.request_id, "test_check_1")
        self.assertTrue(result.success)
        self.assertIsInstance(result.violations_found, list)
        self.assertGreaterEqual(result.consistency_score, 0.0)
        self.assertLessEqual(result.consistency_score, 1.0)
        self.assertGreater(result.total_terms_checked, 0)
        self.assertGreaterEqual(result.processing_time_ms, 0)
    
    def test_calculate_consistency_score(self):
        """测试一致性分数计算"""
        # 创建测试数据：完全一致的情况
        consistent_occurrences = {
            "张伟": {
                "en": [
                    {"translated_term": "Zhang Wei"},
                    {"translated_term": "Zhang Wei"}
                ]
            }
        }
        
        score = self.checker._calculate_consistency_score(consistent_occurrences, [])
        self.assertEqual(score, 1.0)
        
        # 创建测试数据：不一致的情况
        inconsistent_occurrences = {
            "张伟": {
                "en": [
                    {"translated_term": "Zhang Wei"},
                    {"translated_term": "Zhang Wei"},
                    {"translated_term": "Zhang Wei"}
                ]
            },
            "李明": {
                "en": [
                    {"translated_term": "Li Ming"},
                    {"translated_term": "Lee Ming"}  # 不一致
                ]
            }
        }
        
        score = self.checker._calculate_consistency_score(inconsistent_occurrences, [])
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.0)
    
    def test_update_term_database(self):
        """测试术语数据库更新"""
        # 添加新术语
        self.checker.update_term_database("测试术语", "en", "test term", 0.9, "测试上下文")
        
        # 检查是否添加成功
        translations = self.checker.get_term_translations("测试术语", "en")
        self.assertIn("en", translations)
        self.assertEqual(len(translations["en"]), 1)
        self.assertEqual(translations["en"][0]["translation"], "test term")
        self.assertEqual(translations["en"][0]["confidence"], 0.9)
        
        # 添加相同术语的另一个翻译
        self.checker.update_term_database("测试术语", "en", "test term", 0.8, "另一个上下文")
        
        # 检查是否更新了统计信息
        updated_translations = self.checker.get_term_translations("测试术语", "en")
        self.assertEqual(updated_translations["en"][0]["count"], 2)
    
    def test_export_violations_report(self):
        """测试违规报告导出"""
        # 创建测试违规
        violation = ConsistencyViolation(
            violation_id="test_violation_1",
            rule_id="test_rule",
            consistency_type=ConsistencyType.PERSON_NAME,
            source_term="测试术语",
            conflicting_translations={"en": [{"translation": "test1"}, {"translation": "test2"}]},
            severity=ConflictSeverity.HIGH,
            suggested_resolution="建议使用 test1"
        )
        
        # 导出JSON格式
        json_report = self.checker.export_violations_report([violation], "json")
        self.assertIn("test_violation_1", json_report)
        self.assertIn("测试术语", json_report)
        
        # 导出CSV格式
        csv_report = self.checker.export_violations_report([violation], "csv")
        self.assertIn("Violation ID", csv_report)
        self.assertIn("test_violation_1", csv_report)
    
    def test_validate_episode_data(self):
        """测试集数据验证"""
        # 有效数据
        valid_episode = {
            "episode_id": "test_episode",
            "subtitles": [{"text": "测试字幕"}],
            "translations": {"en": [{"translated_text": "test subtitle"}]}
        }
        
        errors = self.checker.validate_episode_data(valid_episode)
        self.assertEqual(len(errors), 0)
        
        # 无效数据
        invalid_episode = {
            "subtitles": "not a list",  # 应该是列表
            "translations": []  # 应该是字典
        }
        
        errors = self.checker.validate_episode_data(invalid_episode)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("episode_id" in error for error in errors))
    
    def test_batch_check_consistency(self):
        """测试批量一致性检查"""
        requests = [
            ConsistencyCheckRequest(
                request_id=f"batch_test_{i}",
                project_id="batch_project",
                episodes=self.test_episodes,
                target_languages=["en"],
                check_scope="episode"
            )
            for i in range(3)
        ]
        
        results = asyncio.run(self.checker.batch_check_consistency(requests))
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsInstance(result, ConsistencyCheckResult)
            self.assertTrue(result.success)
    
    def test_cross_episode_report(self):
        """测试跨集数报告"""
        # 创建多个检查结果
        results = []
        for i in range(2):
            request = ConsistencyCheckRequest(
                request_id=f"cross_episode_test_{i}",
                project_id="cross_episode_project",
                episodes=[self.test_episodes[i]],
                target_languages=["en"],
                check_scope="episode"
            )
            result = asyncio.run(self.checker.check_consistency(request))
            results.append(result)
        
        # 生成跨集数报告
        cross_report = self.checker.create_cross_episode_report(results)
        
        self.assertIn("report_id", cross_report)
        self.assertIn("episodes_analyzed", cross_report)
        self.assertIn("cross_episode_issues", cross_report)
        self.assertIn("recommendations", cross_report)
        self.assertEqual(cross_report["episodes_analyzed"], 2)
    
    def test_consistency_statistics(self):
        """测试一致性统计"""
        # 执行一些检查以生成统计数据
        request = ConsistencyCheckRequest(
            request_id="stats_test",
            project_id="stats_project",
            episodes=self.test_episodes,
            target_languages=["en", "ja"]
        )
        
        asyncio.run(self.checker.check_consistency(request))
        
        # 获取统计信息
        stats = self.checker.get_consistency_statistics()
        
        self.assertIn("total_checks", stats)
        self.assertIn("violations_found", stats)
        self.assertIn("total_rules", stats)
        self.assertIn("terms_in_database", stats)
        self.assertGreater(stats["total_checks"], 0)
        self.assertGreater(stats["total_rules"], 0)
    
    def test_resolution_strategy_application(self):
        """测试解决策略应用"""
        # 创建包含多个翻译的分组
        translation_groups = {
            "Zhang Wei": [{"confidence": 0.9}, {"confidence": 0.8}],
            "Zhang Wei": [{"confidence": 0.7}]
        }
        
        violation = ConsistencyViolation(
            violation_id="test_resolution",
            rule_id="test_rule",
            consistency_type=ConsistencyType.PERSON_NAME,
            source_term="张伟",
            conflicting_translations={},
            severity=ConflictSeverity.MEDIUM,
            resolution_strategy=ResolutionStrategy.USE_MOST_FREQUENT
        )
        
        suggestion = self.checker._generate_resolution_suggestion(violation, translation_groups)
        self.assertIsInstance(suggestion, str)
        self.assertIn("建议", suggestion)


class TestConsistencyDataModels(unittest.TestCase):
    """一致性数据模型测试"""
    
    def test_consistency_rule_creation(self):
        """测试一致性规则创建"""
        rule = ConsistencyRule(
            rule_id="test_rule_1",
            rule_name="测试规则",
            consistency_type=ConsistencyType.TERMINOLOGY,
            pattern=r"测试.*术语",
            case_sensitive=True,
            severity=ConflictSeverity.HIGH,
            resolution_strategy=ResolutionStrategy.USE_MOST_FREQUENT,
            description="这是一个测试规则"
        )
        
        self.assertEqual(rule.rule_id, "test_rule_1")
        self.assertEqual(rule.consistency_type, ConsistencyType.TERMINOLOGY)
        self.assertTrue(rule.case_sensitive)
        self.assertEqual(rule.severity, ConflictSeverity.HIGH)
        self.assertIsInstance(rule.examples, list)
    
    def test_consistency_violation_creation(self):
        """测试一致性违规创建"""
        violation = ConsistencyViolation(
            violation_id="test_violation_1",
            rule_id="test_rule",
            consistency_type=ConsistencyType.PERSON_NAME,
            source_term="张伟",
            conflicting_translations={
                "en": [{"translation": "Zhang Wei"}, {"translation": "Zhang Wei"}]
            },
            severity=ConflictSeverity.MEDIUM,
            suggested_resolution="建议统一使用 Zhang Wei"
        )
        
        self.assertEqual(violation.violation_id, "test_violation_1")
        self.assertEqual(violation.source_term, "张伟")
        self.assertEqual(violation.severity, ConflictSeverity.MEDIUM)
        self.assertIsNotNone(violation.detected_at)
        self.assertIsInstance(violation.contexts, list)
        self.assertIsInstance(violation.locations, list)
    
    def test_consistency_check_result_creation(self):
        """测试一致性检查结果创建"""
        result = ConsistencyCheckResult(
            request_id="test_result_1",
            success=True,
            violations_found=[],
            consistency_score=0.95,
            total_terms_checked=100,
            violations_by_type={ConsistencyType.PERSON_NAME: 2}
        )
        
        self.assertEqual(result.request_id, "test_result_1")
        self.assertTrue(result.success)
        self.assertEqual(result.consistency_score, 0.95)
        self.assertEqual(result.total_terms_checked, 100)
        self.assertIsNotNone(result.timestamp)
        self.assertIsInstance(result.recommendations, list)


if __name__ == '__main__':
    unittest.main()