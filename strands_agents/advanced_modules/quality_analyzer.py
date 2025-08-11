"""
高级质量分析器
处理翻译质量的多维度评估和智能问题检测
从agents/translation_quality_evaluator.py迁移而来，符合需求6
"""
import json
import time
import re
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

from . import AdvancedModule, module_registry

class QualityDimension(Enum):
    """质量评估维度"""
    ACCURACY = "accuracy"                    # 准确性
    FLUENCY = "fluency"                     # 流畅性
    CULTURAL_ADAPTATION = "cultural_adaptation"  # 文化适配性
    CONSISTENCY = "consistency"             # 一致性
    COMPLETENESS = "completeness"           # 完整性
    READABILITY = "readability"             # 可读性
    TIMING_SYNC = "timing_sync"             # 时间同步性

class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"      # 优秀 (0.9-1.0)
    GOOD = "good"               # 良好 (0.8-0.9)
    ACCEPTABLE = "acceptable"    # 可接受 (0.7-0.8)
    POOR = "poor"               # 较差 (0.6-0.7)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (0.0-0.6)

class EvaluationMethod(Enum):
    """评估方法"""
    RULE_BASED = "rule_based"       # 基于规则
    STATISTICAL = "statistical"     # 统计方法
    SEMANTIC = "semantic"           # 语义分析
    CONTEXTUAL = "contextual"       # 上下文分析
    HYBRID = "hybrid"               # 混合方法

@dataclass
class QualityMetric:
    """质量指标"""
    dimension: str
    score: float                    # 0.0-1.0
    weight: float = 1.0            # 权重
    confidence: float = 1.0        # 置信度
    details: Dict[str, Any] = None
    method: str = "hybrid"
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class QualityIssue:
    """质量问题"""
    issue_id: str
    issue_type: str
    severity: str                   # critical, high, medium, low
    description: str
    location: Optional[str] = None  # 问题位置
    suggestion: Optional[str] = None # 改进建议
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class QualityAnalysisResult:
    """质量分析结果"""
    overall_score: float            # 总体质量分数
    quality_level: str              # 质量等级
    dimension_scores: Dict[str, QualityMetric]  # 各维度分数
    issues_found: List[QualityIssue]  # 发现的问题
    recommendations: List[str]      # 改进建议
    confidence: float = 1.0         # 整体置信度
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class QualityAnalyzer(AdvancedModule):
    """高级质量分析器
    
    核心功能：
    1. 7种质量评估维度 (符合需求6: 翻译质量控制)
    2. 智能问题检测算法
    3. 改进建议生成
    4. 多语言质量标准
    """
    
    def __init__(self):
        super().__init__("quality_analyzer", "1.0.0")
        
        # 评估维度权重
        self.dimension_weights = {
            "accuracy": 0.3,
            "fluency": 0.25,
            "cultural_adaptation": 0.2,
            "consistency": 0.15,
            "completeness": 0.05,
            "readability": 0.03,
            "timing_sync": 0.02
        }
        
        # 语言特定配置
        self.language_configs = self._initialize_language_configs()
        
        # 质量阈值
        self.quality_thresholds = {
            "excellent": 0.9,
            "good": 0.8,
            "acceptable": 0.7,
            "poor": 0.6,
            "unacceptable": 0.0
        }
        
        # 错误检测模式
        self.error_patterns = self._initialize_error_patterns()
        
        # 文化适配模式
        self.cultural_patterns = self._initialize_cultural_patterns()
        
        # 性能统计
        self.performance_stats = {
            "total_analyses": 0,
            "average_scores": defaultdict(float),
            "language_stats": defaultdict(lambda: defaultdict(int)),
            "issue_frequency": defaultdict(int),
            "processing_times": []
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理质量分析
        
        Args:
            input_data: {
                "original": "原文JSON字符串",
                "translated": "译文JSON字符串", 
                "target_language": "目标语言代码",
                "analysis_config": "分析配置JSON字符串"
            }
        
        Returns:
            详细质量分析报告
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False,
                error="Invalid input data for quality analysis",
                processing_time=time.time() - start_time
            )
        
        try:
            original = self.from_json(input_data["original"])
            translated = self.from_json(input_data["translated"])
            target_language = input_data["target_language"]
            analysis_config = self.from_json(input_data.get("analysis_config", "{}"))
            
            # 执行多维度质量分析
            dimension_scores = self._analyze_all_dimensions(
                original, translated, target_language, analysis_config
            )
            
            # 计算总体分数
            overall_score = self._calculate_overall_score(dimension_scores)
            
            # 确定质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 检测质量问题
            issues_found = self._detect_quality_issues(
                original, translated, target_language, dimension_scores
            )
            
            # 生成改进建议
            recommendations = self._generate_recommendations(dimension_scores, issues_found)
            
            # 计算置信度
            confidence = self._calculate_confidence(dimension_scores, issues_found)
            
            processing_time = time.time() - start_time
            
            # 创建分析结果
            result = QualityAnalysisResult(
                overall_score=overall_score,
                quality_level=quality_level,
                dimension_scores={k: asdict(v) for k, v in dimension_scores.items()},
                issues_found=[asdict(issue) for issue in issues_found],
                recommendations=recommendations,
                confidence=confidence,
                processing_time_ms=int(processing_time * 1000),
                metadata={
                    "target_language": target_language,
                    "entries_analyzed": len(original) if isinstance(original, list) else 1,
                    "evaluation_method": "hybrid"
                }
            )
            
            # 更新统计信息
            self._update_stats(result, target_language)
            
            return self.create_result(
                True,
                data={
                    "quality_analysis": asdict(result),
                    "analysis_summary": {
                        "overall_score": overall_score,
                        "quality_level": quality_level,
                        "issues_count": len(issues_found),
                        "recommendations_count": len(recommendations)
                    }
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Quality analysis failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["original", "translated", "target_language"]
        return all(field in input_data for field in required_fields)
    
    def _analyze_all_dimensions(self, original: Any, translated: Any, 
                               target_language: str, config: Dict) -> Dict[str, QualityMetric]:
        """分析所有质量维度"""
        dimension_scores = {}
        
        # 1. 准确性评估
        dimension_scores["accuracy"] = self._evaluate_accuracy(original, translated, target_language)
        
        # 2. 流畅性评估
        dimension_scores["fluency"] = self._evaluate_fluency(translated, target_language)
        
        # 3. 文化适配性评估
        dimension_scores["cultural_adaptation"] = self._evaluate_cultural_adaptation(
            original, translated, target_language
        )
        
        # 4. 一致性评估
        dimension_scores["consistency"] = self._evaluate_consistency(translated, target_language)
        
        # 5. 完整性评估
        dimension_scores["completeness"] = self._evaluate_completeness(original, translated)
        
        # 6. 可读性评估
        dimension_scores["readability"] = self._evaluate_readability(translated, target_language)
        
        # 7. 时间同步性评估
        dimension_scores["timing_sync"] = self._evaluate_timing_sync(original, translated)
        
        return dimension_scores
    
    def _evaluate_accuracy(self, original: Any, translated: Any, target_language: str) -> QualityMetric:
        """评估翻译准确性"""
        accuracy_scores = []
        
        # 处理单个条目或条目列表
        if isinstance(original, list) and isinstance(translated, list):
            pairs = zip(original, translated)
        else:
            pairs = [(original, translated)]
        
        for orig, trans in pairs:
            score = 0.8  # 基础分数
            
            # 检查是否为空翻译
            if not str(trans).strip():
                accuracy_scores.append(0.0)
                continue
            
            # 检查长度合理性
            orig_text = str(orig)
            trans_text = str(trans)
            
            if orig_text:
                length_ratio = len(trans_text) / len(orig_text)
                if 0.5 <= length_ratio <= 2.0:
                    score += 0.1
                elif length_ratio < 0.3 or length_ratio > 3.0:
                    score -= 0.2
            
            # 检查关键词保留
            keywords = self._extract_keywords(orig_text, target_language)
            preserved_keywords = self._check_keyword_preservation(keywords, trans_text, target_language)
            if keywords:
                preservation_rate = preserved_keywords / len(keywords)
                score += preservation_rate * 0.1
            
            accuracy_scores.append(min(max(score, 0.0), 1.0))
        
        overall_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        
        return QualityMetric(
            dimension="accuracy",
            score=overall_accuracy,
            weight=self.dimension_weights["accuracy"],
            confidence=0.8,
            method="hybrid",
            details={
                "individual_scores": accuracy_scores,
                "keyword_preservation": preserved_keywords if 'preserved_keywords' in locals() else 0
            }
        )
    
    def _evaluate_fluency(self, translated: Any, target_language: str) -> QualityMetric:
        """评估翻译流畅性"""
        fluency_scores = []
        
        # 处理单个条目或条目列表
        texts = translated if isinstance(translated, list) else [translated]
        
        for text in texts:
            text_str = str(text)
            score = 0.8  # 基础分数
            
            # 检查基本语法
            grammar_score = self._check_grammar(text_str, target_language)
            score += grammar_score * 0.1
            
            # 检查重复词汇
            repetition_penalty = self._check_repetition(text_str)
            score -= repetition_penalty
            
            # 检查句子长度合理性
            length_score = self._check_sentence_length(text_str, target_language)
            score += length_score * 0.1
            
            # 检查连贯性
            coherence_score = self._check_coherence(text_str, target_language)
            score += coherence_score * 0.05
            
            fluency_scores.append(min(max(score, 0.0), 1.0))
        
        overall_fluency = statistics.mean(fluency_scores) if fluency_scores else 0.0
        
        return QualityMetric(
            dimension="fluency",
            score=overall_fluency,
            weight=self.dimension_weights["fluency"],
            confidence=0.7,
            method="rule_based",
            details={
                "individual_scores": fluency_scores,
                "grammar_issues": self._count_grammar_issues(texts, target_language)
            }
        )
    
    def _evaluate_cultural_adaptation(self, original: Any, translated: Any, target_language: str) -> QualityMetric:
        """评估文化适配性"""
        cultural_scores = []
        
        # 处理单个条目或条目列表
        if isinstance(original, list) and isinstance(translated, list):
            pairs = zip(original, translated)
        else:
            pairs = [(original, translated)]
        
        for orig, trans in pairs:
            score = 0.8  # 基础分数
            
            orig_text = str(orig)
            trans_text = str(trans)
            
            # 检查敬语使用
            if self._requires_honorifics(target_language):
                honorific_score = self._check_honorifics(orig_text, trans_text, target_language)
                score += honorific_score * 0.1
            
            # 检查文化词汇适配
            cultural_terms = self._detect_cultural_terms(orig_text)
            if cultural_terms:
                adaptation_score = self._check_cultural_adaptation(cultural_terms, trans_text, target_language)
                score += adaptation_score * 0.1
            
            # 检查语言风格适配
            style_score = self._check_style_adaptation(orig_text, trans_text, target_language)
            score += style_score * 0.05
            
            cultural_scores.append(min(max(score, 0.0), 1.0))
        
        overall_cultural = statistics.mean(cultural_scores) if cultural_scores else 0.0
        
        return QualityMetric(
            dimension="cultural_adaptation",
            score=overall_cultural,
            weight=self.dimension_weights["cultural_adaptation"],
            confidence=0.6,
            method="contextual",
            details={
                "individual_scores": cultural_scores,
                "cultural_terms_detected": len(cultural_terms) if 'cultural_terms' in locals() else 0
            }
        )
    
    def _evaluate_consistency(self, translated: Any, target_language: str) -> QualityMetric:
        """评估翻译一致性"""
        if not isinstance(translated, list) or len(translated) < 2:
            # 单个条目无法评估一致性
            return QualityMetric(
                dimension="consistency",
                score=1.0,
                weight=self.dimension_weights["consistency"],
                confidence=0.5,
                method="statistical"
            )
        
        # 检查术语一致性
        term_consistency = self._check_term_consistency(translated, target_language)
        
        # 检查风格一致性
        style_consistency = self._check_style_consistency(translated, target_language)
        
        # 检查格式一致性
        format_consistency = self._check_format_consistency(translated)
        
        overall_consistency = (term_consistency + style_consistency + format_consistency) / 3
        
        return QualityMetric(
            dimension="consistency",
            score=overall_consistency,
            weight=self.dimension_weights["consistency"],
            confidence=0.7,
            method="statistical",
            details={
                "term_consistency": term_consistency,
                "style_consistency": style_consistency,
                "format_consistency": format_consistency
            }
        )
    
    def _evaluate_completeness(self, original: Any, translated: Any) -> QualityMetric:
        """评估翻译完整性"""
        completeness_scores = []
        
        # 处理单个条目或条目列表
        if isinstance(original, list) and isinstance(translated, list):
            pairs = zip(original, translated)
        else:
            pairs = [(original, translated)]
        
        for orig, trans in pairs:
            orig_text = str(orig)
            trans_text = str(trans)
            
            # 检查是否为空翻译
            if not trans_text.strip():
                completeness_scores.append(0.0)
                continue
            
            # 检查信息完整性
            score = 0.9  # 基础分数
            
            # 简单的完整性检查：检查是否有明显的省略
            if "..." in trans_text or "[...]" in trans_text:
                score -= 0.3
            
            if len(trans_text.strip()) < len(orig_text.strip()) * 0.3:
                score -= 0.2
            
            completeness_scores.append(min(max(score, 0.0), 1.0))
        
        overall_completeness = statistics.mean(completeness_scores) if completeness_scores else 0.0
        
        return QualityMetric(
            dimension="completeness",
            score=overall_completeness,
            weight=self.dimension_weights["completeness"],
            confidence=0.8,
            method="rule_based",
            details={
                "individual_scores": completeness_scores
            }
        )
    
    def _evaluate_readability(self, translated: Any, target_language: str) -> QualityMetric:
        """评估可读性"""
        readability_scores = []
        
        # 处理单个条目或条目列表
        texts = translated if isinstance(translated, list) else [translated]
        
        lang_config = self.language_configs.get(target_language, self.language_configs["en"])
        
        for text in texts:
            text_str = str(text)
            score = 0.8  # 基础分数
            
            # 检查字符数限制
            if len(text_str) <= lang_config["max_chars_per_line"]:
                score += 0.1
            elif len(text_str) > lang_config["max_chars_per_line"] * 1.5:
                score -= 0.2
            
            # 检查行数限制
            lines = text_str.split('\n')
            if len(lines) <= lang_config["max_lines"]:
                score += 0.05
            
            # 检查阅读速度
            reading_time = len(text_str) / lang_config["reading_speed_cps"]
            if reading_time <= 2.0:  # 2秒内可读完
                score += 0.05
            
            readability_scores.append(min(max(score, 0.0), 1.0))
        
        overall_readability = statistics.mean(readability_scores) if readability_scores else 0.0
        
        return QualityMetric(
            dimension="readability",
            score=overall_readability,
            weight=self.dimension_weights["readability"],
            confidence=0.9,
            method="rule_based",
            details={
                "individual_scores": readability_scores,
                "max_chars_per_line": lang_config["max_chars_per_line"]
            }
        )
    
    def _evaluate_timing_sync(self, original: Any, translated: Any) -> QualityMetric:
        """评估时间同步性"""
        # 简化的时间同步评估
        # 在实际应用中，这里会检查字幕的时间码同步
        
        return QualityMetric(
            dimension="timing_sync",
            score=0.95,  # 假设时间同步良好
            weight=self.dimension_weights["timing_sync"],
            confidence=0.5,
            method="rule_based",
            details={
                "sync_status": "assumed_good"
            }
        )
    
    def _calculate_overall_score(self, dimension_scores: Dict[str, QualityMetric]) -> float:
        """计算总体质量分数"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric in dimension_scores.values():
            weighted_sum += metric.score * metric.weight
            total_weight += metric.weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_quality_level(self, overall_score: float) -> str:
        """确定质量等级"""
        for level, threshold in sorted(self.quality_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                return level
        return "unacceptable"
    
    def _detect_quality_issues(self, original: Any, translated: Any, 
                             target_language: str, dimension_scores: Dict) -> List[QualityIssue]:
        """检测质量问题"""
        issues = []
        
        # 基于维度分数检测问题
        for dimension, metric in dimension_scores.items():
            if metric.score < 0.7:
                issues.append(QualityIssue(
                    issue_id=f"low_{dimension}_{int(time.time())}",
                    issue_type=f"low_{dimension}",
                    severity="medium" if metric.score >= 0.5 else "high",
                    description=f"{dimension}质量较低 (分数: {metric.score:.2f})",
                    suggestion=self._get_dimension_suggestion(dimension),
                    confidence=metric.confidence
                ))
        
        # 检测具体问题
        texts = translated if isinstance(translated, list) else [translated]
        for i, text in enumerate(texts):
            text_str = str(text)
            
            # 检查空翻译
            if not text_str.strip():
                issues.append(QualityIssue(
                    issue_id=f"empty_translation_{i}_{int(time.time())}",
                    issue_type="empty_translation",
                    severity="critical",
                    description="翻译为空",
                    location=f"entry_{i}",
                    suggestion="提供完整的翻译内容",
                    confidence=1.0
                ))
            
            # 检查格式问题
            if re.search(r'^\s+|\s+$', text_str):
                issues.append(QualityIssue(
                    issue_id=f"formatting_issue_{i}_{int(time.time())}",
                    issue_type="formatting_issue",
                    severity="low",
                    description="存在多余的空格",
                    location=f"entry_{i}",
                    suggestion="清理首尾空格",
                    confidence=0.9
                ))
        
        return issues
    
    def _generate_recommendations(self, dimension_scores: Dict, issues: List[QualityIssue]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于维度分数的建议
        for dimension, metric in dimension_scores.items():
            if metric.score < 0.8:
                recommendations.append(self._get_dimension_recommendation(dimension, metric.score))
        
        # 基于问题的建议
        issue_types = Counter([issue.issue_type for issue in issues])
        for issue_type, count in issue_types.items():
            if count > 1:
                recommendations.append(f"发现{count}个{issue_type}问题，建议系统性检查和修复")
        
        return recommendations[:5]  # 限制建议数量
    
    def _calculate_confidence(self, dimension_scores: Dict, issues: List[QualityIssue]) -> float:
        """计算整体置信度"""
        confidences = [metric.confidence for metric in dimension_scores.values()]
        avg_confidence = statistics.mean(confidences) if confidences else 0.5
        
        # 根据问题数量调整置信度
        issue_penalty = min(len(issues) * 0.05, 0.3)
        
        return max(avg_confidence - issue_penalty, 0.1)
    
    def _update_stats(self, result: QualityAnalysisResult, target_language: str):
        """更新统计信息"""
        self.performance_stats["total_analyses"] += 1
        self.performance_stats["language_stats"][target_language]["count"] += 1
        self.performance_stats["processing_times"].append(result.processing_time_ms)
        
        # 更新平均分数
        for dimension, metric_dict in result.dimension_scores.items():
            current_avg = self.performance_stats["average_scores"][dimension]
            total = self.performance_stats["total_analyses"]
            new_score = metric_dict["score"]
            self.performance_stats["average_scores"][dimension] = (current_avg * (total - 1) + new_score) / total
        
        # 更新问题频率
        for issue in result.issues_found:
            self.performance_stats["issue_frequency"][issue["issue_type"]] += 1
    
    # 辅助方法
    def _initialize_language_configs(self) -> Dict[str, Dict[str, Any]]:
        """初始化语言配置"""
        return {
            "en": {
                "max_chars_per_line": 42,
                "max_lines": 2,
                "reading_speed_cps": 17,
                "honorific_required": False
            },
            "ja": {
                "max_chars_per_line": 20,
                "max_lines": 2,
                "reading_speed_cps": 8,
                "honorific_required": True
            },
            "ko": {
                "max_chars_per_line": 18,
                "max_lines": 2,
                "reading_speed_cps": 9,
                "honorific_required": True
            },
            "zh": {
                "max_chars_per_line": 15,
                "max_lines": 2,
                "reading_speed_cps": 10,
                "honorific_required": False
            },
            "ar": {
                "max_chars_per_line": 35,
                "max_lines": 2,
                "reading_speed_cps": 15,
                "honorific_required": False,
                "rtl_text": True
            }
        }
    
    def _initialize_error_patterns(self) -> Dict[str, List[str]]:
        """初始化错误检测模式"""
        return {
            "incomplete_translation": [
                r"^\s*$",  # 空翻译
                r"^[.]{3,}$",  # 省略号
                r"^\[.*\]$",  # 方括号内容
                r"^TODO|TBD|FIXME",  # 待办标记
            ],
            "formatting_errors": [
                r"^\s+|\s+$",  # 首尾空格
                r"\s{2,}",  # 多余空格
                r"[。，！？；：][\w]",  # 标点后缺少空格
            ],
            "encoding_issues": [
                r"[��]",  # 乱码字符
                r"\\u[0-9a-fA-F]{4}",  # Unicode转义
                r"&[a-zA-Z]+;",  # HTML实体
            ]
        }
    
    def _initialize_cultural_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """初始化文化适配模式"""
        return {
            "honorifics": {
                "ja": [r"さん|様|君|ちゃん", r"です|ます|である"],
                "ko": [r"님|씨", r"습니다|입니다|요"],
                "zh": [r"先生|女士|老师|同志"]
            },
            "formal_language": {
                "en": [r"\b(please|thank you|excuse me|pardon)\b"],
                "ja": [r"恐れ入ります|申し訳|お疲れ様"],
                "ko": [r"죄송합니다|감사합니다|수고하셨습니다"]
            }
        }
    
    # 简化的辅助检查方法
    def _extract_keywords(self, text: str, target_language: str) -> List[str]:
        """提取关键词"""
        # 简化实现：提取常见的重要词汇
        keywords = []
        important_patterns = [
            r'雷达|司令|队长|海军|军事|作战|指挥|战斗',  # 军事词汇
            r'爱情|恋人|男友|女友|结婚|约会',  # 感情词汇
            r'工作|公司|老板|同事|项目|会议'   # 工作词汇
        ]
        
        for pattern in important_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return keywords
    
    def _check_keyword_preservation(self, keywords: List[str], translated: str, target_language: str) -> int:
        """检查关键词保留情况"""
        # 简化实现：检查是否有对应的英文词汇
        preserved = 0
        keyword_mappings = {
            "雷达": ["radar"],
            "司令": ["commander", "chief"],
            "队长": ["captain", "leader"],
            "海军": ["navy", "naval"],
            "军事": ["military", "defense"]
        }
        
        for keyword in keywords:
            if keyword in keyword_mappings:
                for mapping in keyword_mappings[keyword]:
                    if mapping.lower() in translated.lower():
                        preserved += 1
                        break
        
        return preserved
    
    def _check_grammar(self, text: str, target_language: str) -> float:
        """检查语法"""
        # 简化的语法检查
        score = 0.0
        
        if target_language == "en":
            # 简单的英语语法检查
            if not re.search(r'\b(a|an)\s+[aeiou]', text, re.IGNORECASE):
                score += 0.1
            if not re.search(r'\b(he|she|it)\s+are\b', text, re.IGNORECASE):
                score += 0.1
        
        return min(score, 1.0)
    
    def _check_repetition(self, text: str) -> float:
        """检查重复词汇"""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
        
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.7:
            return 0.1
        return 0.0
    
    def _check_sentence_length(self, text: str, target_language: str) -> float:
        """检查句子长度"""
        sentences = re.split(r'[.!?。！？]', text)
        if not sentences:
            return 0.0
        
        lengths = [len(s.strip()) for s in sentences if s.strip()]
        if not lengths:
            return 0.0
        
        avg_length = statistics.mean(lengths)
        if 5 <= avg_length <= 30:
            return 1.0
        return 0.5
    
    def _check_coherence(self, text: str, target_language: str) -> float:
        """检查连贯性"""
        # 简化实现：检查基本的连贯性指标
        return 0.8  # 假设连贯性良好
    
    def _count_grammar_issues(self, texts: List, target_language: str) -> int:
        """统计语法问题"""
        # 简化实现
        return 0
    
    def _requires_honorifics(self, target_language: str) -> bool:
        """检查是否需要敬语"""
        return self.language_configs.get(target_language, {}).get("honorific_required", False)
    
    def _check_honorifics(self, original: str, translated: str, target_language: str) -> float:
        """检查敬语使用"""
        # 简化实现
        return 0.8
    
    def _detect_cultural_terms(self, text: str) -> List[str]:
        """检测文化词汇"""
        cultural_terms = []
        patterns = [r'面子|关系|鸡娃|内卷|躺平']
        for pattern in patterns:
            matches = re.findall(pattern, text)
            cultural_terms.extend(matches)
        return cultural_terms
    
    def _check_cultural_adaptation(self, terms: List[str], translated: str, target_language: str) -> float:
        """检查文化适配"""
        # 简化实现
        return 0.8
    
    def _check_style_adaptation(self, original: str, translated: str, target_language: str) -> float:
        """检查风格适配"""
        # 简化实现
        return 0.8
    
    def _check_term_consistency(self, texts: List, target_language: str) -> float:
        """检查术语一致性"""
        # 简化实现
        return 0.9
    
    def _check_style_consistency(self, texts: List, target_language: str) -> float:
        """检查风格一致性"""
        # 简化实现
        return 0.9
    
    def _check_format_consistency(self, texts: List) -> float:
        """检查格式一致性"""
        # 简化实现
        return 0.95
    
    def _get_dimension_suggestion(self, dimension: str) -> str:
        """获取维度建议"""
        suggestions = {
            "accuracy": "检查关键词翻译和信息完整性",
            "fluency": "改善语法和句子结构",
            "cultural_adaptation": "加强文化词汇和敬语的适配",
            "consistency": "保持术语和风格的一致性",
            "completeness": "确保翻译内容完整",
            "readability": "优化字幕长度和可读性",
            "timing_sync": "检查时间同步"
        }
        return suggestions.get(dimension, "需要改进")
    
    def _get_dimension_recommendation(self, dimension: str, score: float) -> str:
        """获取维度推荐"""
        recommendations = {
            "accuracy": f"准确性分数较低({score:.2f})，建议重新检查翻译准确性",
            "fluency": f"流畅性分数较低({score:.2f})，建议改善语法和表达",
            "cultural_adaptation": f"文化适配分数较低({score:.2f})，建议加强文化敏感性",
            "consistency": f"一致性分数较低({score:.2f})，建议统一术语和风格",
            "completeness": f"完整性分数较低({score:.2f})，建议补充缺失信息",
            "readability": f"可读性分数较低({score:.2f})，建议优化字幕格式",
            "timing_sync": f"时间同步分数较低({score:.2f})，建议调整时间码"
        }
        return recommendations.get(dimension, f"{dimension}需要改进")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()

# 注册模块
quality_analyzer = QualityAnalyzer()
module_registry.register(quality_analyzer)