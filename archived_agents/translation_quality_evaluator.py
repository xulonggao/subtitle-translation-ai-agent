"""
翻译质量评估器
实现翻译质量的自动评分算法，包括准确性、流畅性、文化适配性等多维度评估
"""
import re
import json
import uuid
import math
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter
import statistics

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationResult

logger = get_logger("translation_quality_evaluator")


class QualityDimension(Enum):
    """质量评估维度"""
    ACCURACY = "accuracy"           # 准确性
    FLUENCY = "fluency"            # 流畅性
    CULTURAL_ADAPTATION = "cultural_adaptation"  # 文化适配性
    CONSISTENCY = "consistency"     # 一致性
    COMPLETENESS = "completeness"   # 完整性
    READABILITY = "readability"     # 可读性
    TIMING_SYNC = "timing_sync"     # 时间同步性


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"    # 优秀 (0.9-1.0)
    GOOD = "good"             # 良好 (0.8-0.9)
    ACCEPTABLE = "acceptable"  # 可接受 (0.7-0.8)
    POOR = "poor"             # 较差 (0.6-0.7)
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
    dimension: QualityDimension
    score: float                    # 0.0-1.0
    weight: float = 1.0            # 权重
    confidence: float = 1.0        # 置信度
    details: Optional[Dict[str, Any]] = None
    method: EvaluationMethod = EvaluationMethod.HYBRID
    
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
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QualityEvaluationRequest:
    """质量评估请求"""
    request_id: str
    original_entries: List[SubtitleEntry]
    translation_results: List[TranslationResult]
    target_language: str
    evaluation_config: Optional[Dict[str, Any]] = None
    context_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.evaluation_config is None:
            self.evaluation_config = {}
        if self.context_info is None:
            self.context_info = {}


@dataclass
class QualityEvaluationResult:
    """质量评估结果"""
    request_id: str
    overall_score: float            # 总体质量分数
    quality_level: QualityLevel     # 质量等级
    dimension_scores: Dict[QualityDimension, QualityMetric]  # 各维度分数
    issues_found: List[QualityIssue]  # 发现的问题
    recommendations: List[str]      # 改进建议
    confidence: float = 1.0         # 整体置信度
    processing_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class TranslationQualityEvaluator:
    """翻译质量评估器
    
    主要功能：
    1. 多维度质量评估
    2. 基于上下文的质量分析
    3. 语言特定的质量检查
    4. 质量问题检测和建议
    """
    
    def __init__(self, evaluator_id: str = None):
        self.evaluator_id = evaluator_id or f"quality_evaluator_{uuid.uuid4().hex[:8]}"
        
        # 评估配置
        self.dimension_weights = {
            QualityDimension.ACCURACY: 0.3,
            QualityDimension.FLUENCY: 0.25,
            QualityDimension.CULTURAL_ADAPTATION: 0.2,
            QualityDimension.CONSISTENCY: 0.15,
            QualityDimension.COMPLETENESS: 0.05,
            QualityDimension.READABILITY: 0.03,
            QualityDimension.TIMING_SYNC: 0.02
        }
        
        # 语言特定配置
        self.language_configs = {
            "en": {
                "max_chars_per_line": 42,
                "max_lines": 2,
                "reading_speed_cps": 17,  # characters per second
                "common_patterns": [r"\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b"],
                "honorific_required": False
            },
            "ja": {
                "max_chars_per_line": 20,
                "max_lines": 2,
                "reading_speed_cps": 8,
                "common_patterns": [r"[です|ます|である|だ]$"],
                "honorific_required": True
            },
            "ko": {
                "max_chars_per_line": 18,
                "max_lines": 2,
                "reading_speed_cps": 9,
                "common_patterns": [r"[습니다|입니다|다|요]$"],
                "honorific_required": True
            },
            "ar": {
                "max_chars_per_line": 35,
                "max_lines": 2,
                "reading_speed_cps": 15,
                "common_patterns": [r"[\u0600-\u06FF]+"],
                "honorific_required": False,
                "rtl_text": True
            }
        }
        
        # 质量阈值
        self.quality_thresholds = {
            QualityLevel.EXCELLENT: 0.9,
            QualityLevel.GOOD: 0.8,
            QualityLevel.ACCEPTABLE: 0.7,
            QualityLevel.POOR: 0.6,
            QualityLevel.UNACCEPTABLE: 0.0
        }
        
        # 统计数据
        self.evaluation_stats = {
            "total_evaluations": 0,
            "average_scores": defaultdict(float),
            "language_stats": defaultdict(lambda: defaultdict(int)),
            "issue_frequency": defaultdict(int),
            "processing_times": []
        }
        
        # 初始化语言检测器和分析器
        self._initialize_analyzers()
        
        logger.info("翻译质量评估器初始化完成", evaluator_id=self.evaluator_id)
    
    def _initialize_analyzers(self):
        """初始化分析器"""
        # 常见错误模式
        self.error_patterns = {
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
                r"[\w][。，！？；：]",  # 标点前多余空格
            ],
            "encoding_issues": [
                r"[��]",  # 乱码字符
                r"\\u[0-9a-fA-F]{4}",  # Unicode转义
                r"&[a-zA-Z]+;",  # HTML实体
            ]
        }
        
        # 文化适配模式
        self.cultural_patterns = {
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
    
    async def evaluate_quality(self, request: QualityEvaluationRequest) -> QualityEvaluationResult:
        """评估翻译质量"""
        start_time = datetime.now()
        
        logger.info("开始质量评估",
                   request_id=request.request_id,
                   target_language=request.target_language,
                   entries_count=len(request.original_entries),
                   results_count=len(request.translation_results))
        
        try:
            # 1. 准确性评估
            accuracy_metric = await self._evaluate_accuracy(request)
            
            # 2. 流畅性评估
            fluency_metric = await self._evaluate_fluency(request)
            
            # 3. 文化适配性评估
            cultural_metric = await self._evaluate_cultural_adaptation(request)
            
            # 4. 一致性评估
            consistency_metric = await self._evaluate_consistency(request)
            
            # 5. 完整性评估
            completeness_metric = await self._evaluate_completeness(request)
            
            # 6. 可读性评估
            readability_metric = await self._evaluate_readability(request)
            
            # 7. 时间同步性评估
            timing_metric = await self._evaluate_timing_sync(request)
            
            # 整合所有维度分数
            dimension_scores = {
                QualityDimension.ACCURACY: accuracy_metric,
                QualityDimension.FLUENCY: fluency_metric,
                QualityDimension.CULTURAL_ADAPTATION: cultural_metric,
                QualityDimension.CONSISTENCY: consistency_metric,
                QualityDimension.COMPLETENESS: completeness_metric,
                QualityDimension.READABILITY: readability_metric,
                QualityDimension.TIMING_SYNC: timing_metric
            }
            
            # 计算总体分数
            overall_score = self._calculate_overall_score(dimension_scores)
            
            # 确定质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 检测质量问题
            issues_found = await self._detect_quality_issues(request, dimension_scores)
            
            # 生成改进建议
            recommendations = self._generate_recommendations(dimension_scores, issues_found)
            
            # 计算置信度
            confidence = self._calculate_confidence(dimension_scores, issues_found)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 创建评估结果
            result = QualityEvaluationResult(
                request_id=request.request_id,
                overall_score=overall_score,
                quality_level=quality_level,
                dimension_scores=dimension_scores,
                issues_found=issues_found,
                recommendations=recommendations,
                confidence=confidence,
                processing_time_ms=int(processing_time),
                metadata={
                    "target_language": request.target_language,
                    "entries_evaluated": len(request.original_entries),
                    "evaluation_method": "hybrid"
                }
            )
            
            # 更新统计
            self._update_evaluation_stats(request, result)
            
            logger.info("质量评估完成",
                       request_id=request.request_id,
                       overall_score=overall_score,
                       quality_level=quality_level.value,
                       issues_count=len(issues_found),
                       processing_time_ms=int(processing_time))
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.error("质量评估失败",
                        request_id=request.request_id,
                        error=str(e),
                        processing_time_ms=int(processing_time))
            
            # 返回失败结果
            return QualityEvaluationResult(
                request_id=request.request_id,
                overall_score=0.0,
                quality_level=QualityLevel.UNACCEPTABLE,
                dimension_scores={},
                issues_found=[
                    QualityIssue(
                        issue_id=f"eval_error_{uuid.uuid4().hex[:8]}",
                        issue_type="evaluation_error",
                        severity="critical",
                        description=f"质量评估过程中发生错误: {str(e)}",
                        confidence=1.0
                    )
                ],
                recommendations=["建议重新进行质量评估"],
                confidence=0.0,
                processing_time_ms=int(processing_time)
            )
    
    async def _evaluate_accuracy(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估翻译准确性"""
        logger.debug("评估翻译准确性", request_id=request.request_id)
        
        accuracy_scores = []
        
        for original, result in zip(request.original_entries, request.translation_results):
            if not result.success:
                accuracy_scores.append(0.0)
                continue
            
            # 简化的准确性评估
            score = 0.8  # 基础分数
            
            # 检查是否为空翻译
            if not result.translated_text.strip():
                accuracy_scores.append(0.0)
                continue
            
            # 检查长度合理性
            length_ratio = len(result.translated_text) / len(original.text) if original.text else 1
            if 0.5 <= length_ratio <= 2.0:
                score += 0.1
            
            # 检查关键词保留
            keywords = ['雷达', '司令', '队长', '海军', '军事']
            for keyword in keywords:
                if keyword in original.text:
                    # 简化检查：看翻译中是否有对应词汇
                    if any(term in result.translated_text.lower() for term in ['radar', 'commander', 'captain', 'navy', 'military']):
                        score += 0.02
            
            accuracy_scores.append(min(score, 1.0))
        
        overall_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.ACCURACY,
            score=overall_accuracy,
            weight=self.dimension_weights[QualityDimension.ACCURACY],
            confidence=0.7,
            method=EvaluationMethod.HYBRID
        )
    
    async def _evaluate_fluency(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估翻译流畅性"""
        logger.debug("评估翻译流畅性", request_id=request.request_id)
        
        fluency_scores = []
        
        for result in request.translation_results:
            if not result.success:
                fluency_scores.append(0.0)
                continue
            
            text = result.translated_text
            score = 0.8  # 基础分数
            
            # 检查基本语法
            if request.target_language == "en":
                # 简单的英语语法检查
                if re.search(r'\b(a|an)\s+[aeiou]', text, re.IGNORECASE):
                    score -= 0.05
                if re.search(r'\b(he|she|it)\s+are\b', text, re.IGNORECASE):
                    score -= 0.1
            
            # 检查重复词汇
            words = re.findall(r'\b\w+\b', text.lower())
            if words:
                unique_ratio = len(set(words)) / len(words)
                if unique_ratio < 0.7:
                    score -= 0.1
            
            # 检查句子长度合理性
            sentences = re.split(r'[.!?。！？]', text)
            if sentences:
                avg_length = statistics.mean([len(s.strip()) for s in sentences if s.strip()])
                if 5 <= avg_length <= 30:
                    score += 0.1
            
            fluency_scores.append(min(score, 1.0))
        
        overall_fluency = statistics.mean(fluency_scores) if fluency_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.FLUENCY,
            score=overall_fluency,
            weight=self.dimension_weights[QualityDimension.FLUENCY],
            confidence=0.6,
            method=EvaluationMethod.RULE_BASED
        )
    
    async def _evaluate_cultural_adaptation(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估文化适配性"""
        logger.debug("评估文化适配性", request_id=request.request_id)
        
        cultural_scores = []
        
        for original, result in zip(request.original_entries, request.translation_results):
            if not result.success:
                cultural_scores.append(0.0)
                continue
            
            score = 0.8  # 基础分数
            
            # 检查敬语使用
            if request.target_language in ["ja", "ko"]:
                honorifics = ['您', '先生', '女士', '司令', '队长']
                has_honorific_context = any(h in original.text for h in honorifics)
                
                if has_honorific_context:
                    if request.target_language == "ja" and re.search(r'(です|ます|さん|様)', result.translated_text):
                        score += 0.1
                    elif request.target_language == "ko" and re.search(r'(습니다|입니다|님|씨)', result.translated_text):
                        score += 0.1
            
            # 检查文化概念翻译
            cultural_terms = {'春节': 'Spring Festival', '中秋节': 'Mid-Autumn Festival'}
            for chinese, english in cultural_terms.items():
                if chinese in original.text and english.lower() in result.translated_text.lower():
                    score += 0.05
            
            cultural_scores.append(min(score, 1.0))
        
        overall_cultural = statistics.mean(cultural_scores) if cultural_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.CULTURAL_ADAPTATION,
            score=overall_cultural,
            weight=self.dimension_weights[QualityDimension.CULTURAL_ADAPTATION],
            confidence=0.5,
            method=EvaluationMethod.CONTEXTUAL
        )
    
    async def _evaluate_consistency(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估一致性"""
        logger.debug("评估一致性", request_id=request.request_id)
        
        # 简化的一致性检查
        score = 0.85
        
        # 检查术语翻译一致性
        term_translations = defaultdict(set)
        key_terms = ['雷达', '司令', '队长']
        
        for original, result in zip(request.original_entries, request.translation_results):
            if not result.success:
                continue
            
            for term in key_terms:
                if term in original.text:
                    # 提取可能的翻译
                    words = re.findall(r'\b\w+\b', result.translated_text.lower())
                    term_translations[term].update(words[:3])  # 只取前3个词
        
        # 计算一致性
        for term, translations in term_translations.items():
            if len(translations) > 2:  # 如果同一术语有多种翻译
                score -= 0.05
        
        return QualityMetric(
            dimension=QualityDimension.CONSISTENCY,
            score=min(score, 1.0),
            weight=self.dimension_weights[QualityDimension.CONSISTENCY],
            confidence=0.6,
            method=EvaluationMethod.STATISTICAL
        )
    
    async def _evaluate_completeness(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估完整性"""
        logger.debug("评估完整性", request_id=request.request_id)
        
        completeness_scores = []
        
        for original, result in zip(request.original_entries, request.translation_results):
            if not result.success:
                completeness_scores.append(0.0)
                continue
            
            # 基于长度的完整性检查
            if not result.translated_text.strip():
                completeness_scores.append(0.0)
                continue
            
            original_length = len(original.text.strip())
            translated_length = len(result.translated_text.strip())
            
            if original_length == 0:
                completeness_scores.append(0.5)
                continue
            
            length_ratio = translated_length / original_length
            
            if 0.7 <= length_ratio <= 1.5:
                completeness_scores.append(1.0)
            elif 0.5 <= length_ratio <= 2.0:
                completeness_scores.append(0.8)
            else:
                completeness_scores.append(0.5)
        
        overall_completeness = statistics.mean(completeness_scores) if completeness_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=overall_completeness,
            weight=self.dimension_weights[QualityDimension.COMPLETENESS],
            confidence=0.8,
            method=EvaluationMethod.STATISTICAL
        )
    
    async def _evaluate_readability(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估可读性"""
        logger.debug("评估可读性", request_id=request.request_id)
        
        readability_scores = []
        lang_config = self.language_configs.get(request.target_language, {})
        max_chars = lang_config.get('max_chars_per_line', 40)
        
        for result in request.translation_results:
            if not result.success:
                readability_scores.append(0.0)
                continue
            
            text = result.translated_text
            score = 0.9  # 基础分数
            
            # 检查行长度
            lines = text.split('\n')
            for line in lines:
                if len(line) > max_chars:
                    score -= 0.1
            
            # 检查行数
            if len(lines) > 2:
                score -= 0.1
            
            readability_scores.append(max(score, 0.0))
        
        overall_readability = statistics.mean(readability_scores) if readability_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.READABILITY,
            score=overall_readability,
            weight=self.dimension_weights[QualityDimension.READABILITY],
            confidence=0.9,
            method=EvaluationMethod.RULE_BASED
        )
    
    async def _evaluate_timing_sync(self, request: QualityEvaluationRequest) -> QualityMetric:
        """评估时间同步性"""
        logger.debug("评估时间同步性", request_id=request.request_id)
        
        timing_scores = []
        lang_config = self.language_configs.get(request.target_language, {})
        reading_speed = lang_config.get('reading_speed_cps', 15)
        
        for original, result in zip(request.original_entries, request.translation_results):
            if not result.success:
                timing_scores.append(0.0)
                continue
            
            text_length = len(result.translated_text)
            required_time = text_length / reading_speed
            available_time = original.duration_seconds
            
            if available_time <= 0:
                timing_scores.append(0.5)
                continue
            
            time_ratio = required_time / available_time
            
            if 0.8 <= time_ratio <= 1.0:
                timing_scores.append(1.0)
            elif 0.6 <= time_ratio <= 1.2:
                timing_scores.append(0.8)
            else:
                timing_scores.append(0.5)
        
        overall_timing = statistics.mean(timing_scores) if timing_scores else 0.0
        
        return QualityMetric(
            dimension=QualityDimension.TIMING_SYNC,
            score=overall_timing,
            weight=self.dimension_weights[QualityDimension.TIMING_SYNC],
            confidence=0.9,
            method=EvaluationMethod.STATISTICAL
        )
    
    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, QualityMetric]) -> float:
        """计算总体质量分数"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, metric in dimension_scores.items():
            weighted_sum += metric.score * metric.weight * metric.confidence
            total_weight += metric.weight * metric.confidence
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """确定质量等级"""
        if overall_score >= self.quality_thresholds[QualityLevel.EXCELLENT]:
            return QualityLevel.EXCELLENT
        elif overall_score >= self.quality_thresholds[QualityLevel.GOOD]:
            return QualityLevel.GOOD
        elif overall_score >= self.quality_thresholds[QualityLevel.ACCEPTABLE]:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= self.quality_thresholds[QualityLevel.POOR]:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    async def _detect_quality_issues(self, request: QualityEvaluationRequest, 
                                   dimension_scores: Dict[QualityDimension, QualityMetric]) -> List[QualityIssue]:
        """检测质量问题"""
        issues = []
        
        # 检查各维度分数，发现低分项
        for dimension, metric in dimension_scores.items():
            if metric.score < 0.6:
                issue = QualityIssue(
                    issue_id=f"low_{dimension.value}_{uuid.uuid4().hex[:8]}",
                    issue_type=f"low_{dimension.value}",
                    severity="high" if metric.score < 0.4 else "medium",
                    description=f"{dimension.value}分数过低: {metric.score:.2f}",
                    suggestion=f"建议改进{dimension.value}相关问题",
                    confidence=metric.confidence
                )
                issues.append(issue)
        
        # 检查具体的翻译问题
        for i, (original, result) in enumerate(zip(request.original_entries, request.translation_results)):
            if not result.success:
                issue = QualityIssue(
                    issue_id=f"failed_translation_{i}_{uuid.uuid4().hex[:8]}",
                    issue_type="translation_failure",
                    severity="critical",
                    description=f"第{i+1}条字幕翻译失败",
                    location=f"subtitle_{i+1}",
                    suggestion="重新进行翻译",
                    confidence=1.0
                )
                issues.append(issue)
                continue
            
            # 检查空翻译
            if not result.translated_text.strip():
                issue = QualityIssue(
                    issue_id=f"empty_translation_{i}_{uuid.uuid4().hex[:8]}",
                    issue_type="empty_translation",
                    severity="high",
                    description=f"第{i+1}条字幕翻译为空",
                    location=f"subtitle_{i+1}",
                    suggestion="提供完整的翻译内容",
                    confidence=1.0
                )
                issues.append(issue)
        
        return issues
    
    def _generate_recommendations(self, dimension_scores: Dict[QualityDimension, QualityMetric], 
                                issues: List[QualityIssue]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于维度分数的建议
        for dimension, metric in dimension_scores.items():
            if metric.score < 0.7:
                if dimension == QualityDimension.ACCURACY:
                    recommendations.append("建议加强术语准确性检查，确保专业词汇翻译正确")
                elif dimension == QualityDimension.FLUENCY:
                    recommendations.append("建议改进语法和表达自然度，使翻译更加流畅")
                elif dimension == QualityDimension.CULTURAL_ADAPTATION:
                    recommendations.append("建议加强文化适配，注意敬语和文化概念的正确翻译")
                elif dimension == QualityDimension.CONSISTENCY:
                    recommendations.append("建议统一术语翻译，保持整体一致性")
                elif dimension == QualityDimension.READABILITY:
                    recommendations.append("建议优化字幕长度和格式，提高可读性")
        
        # 基于问题的建议
        critical_issues = [issue for issue in issues if issue.severity == "critical"]
        if critical_issues:
            recommendations.append(f"发现{len(critical_issues)}个严重问题，建议优先处理")
        
        high_issues = [issue for issue in issues if issue.severity == "high"]
        if high_issues:
            recommendations.append(f"发现{len(high_issues)}个高优先级问题，建议及时修复")
        
        return recommendations
    
    def _calculate_confidence(self, dimension_scores: Dict[QualityDimension, QualityMetric], 
                            issues: List[QualityIssue]) -> float:
        """计算整体置信度"""
        # 基于各维度置信度的加权平均
        total_confidence = 0.0
        total_weight = 0.0
        
        for metric in dimension_scores.values():
            total_confidence += metric.confidence * metric.weight
            total_weight += metric.weight
        
        base_confidence = total_confidence / total_weight if total_weight > 0 else 0.5
        
        # 根据问题数量调整置信度
        critical_issues = len([i for i in issues if i.severity == "critical"])
        if critical_issues > 0:
            base_confidence *= 0.7
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _update_evaluation_stats(self, request: QualityEvaluationRequest, result: QualityEvaluationResult):
        """更新评估统计"""
        self.evaluation_stats["total_evaluations"] += 1
        
        # 更新平均分数
        for dimension, metric in result.dimension_scores.items():
            current_avg = self.evaluation_stats["average_scores"][dimension.value]
            total_evals = self.evaluation_stats["total_evaluations"]
            new_avg = (current_avg * (total_evals - 1) + metric.score) / total_evals
            self.evaluation_stats["average_scores"][dimension.value] = new_avg
        
        # 更新语言统计
        self.evaluation_stats["language_stats"][request.target_language]["evaluations"] += 1
        self.evaluation_stats["language_stats"][request.target_language]["total_score"] += result.overall_score
        
        # 更新问题频率
        for issue in result.issues_found:
            self.evaluation_stats["issue_frequency"][issue.issue_type] += 1
        
        # 更新处理时间
        self.evaluation_stats["processing_times"].append(result.processing_time_ms)
        if len(self.evaluation_stats["processing_times"]) > 1000:
            self.evaluation_stats["processing_times"] = self.evaluation_stats["processing_times"][-1000:]
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """获取评估统计信息"""
        stats = self.evaluation_stats.copy()
        
        # 计算平均处理时间
        if stats["processing_times"]:
            stats["average_processing_time_ms"] = statistics.mean(stats["processing_times"])
            stats["median_processing_time_ms"] = statistics.median(stats["processing_times"])
        
        # 计算语言平均分数
        for lang, lang_stats in stats["language_stats"].items():
            if lang_stats["evaluations"] > 0:
                lang_stats["average_score"] = lang_stats["total_score"] / lang_stats["evaluations"]
        
        return stats


# 导出主要类
__all__ = [
    'QualityDimension', 'QualityLevel', 'EvaluationMethod',
    'QualityMetric', 'QualityIssue', 'QualityEvaluationRequest', 'QualityEvaluationResult',
    'TranslationQualityEvaluator'
]