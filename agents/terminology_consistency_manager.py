"""
术语一致性管理器
负责术语库管理、一致性检查和跨语言术语映射
"""
import json
import uuid
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import difflib

from config import get_logger
from models.subtitle_models import SubtitleEntry

logger = get_logger("terminology_consistency_manager")


class TermType(Enum):
    """术语类型"""
    PERSON_NAME = "person_name"         # 人名
    PLACE_NAME = "place_name"           # 地名
    ORGANIZATION = "organization"       # 组织机构
    TECHNICAL_TERM = "technical_term"   # 技术术语
    MILITARY_TERM = "military_term"     # 军事术语
    MEDICAL_TERM = "medical_term"       # 医学术语
    LEGAL_TERM = "legal_term"           # 法律术语
    BRAND_NAME = "brand_name"           # 品牌名称
    TITLE = "title"                     # 称谓/头衔
    CULTURAL_TERM = "cultural_term"     # 文化术语


class ConsistencyLevel(Enum):
    """一致性级别"""
    STRICT = "strict"           # 严格一致（必须完全相同）
    MODERATE = "moderate"       # 适度一致（允许轻微变化）
    FLEXIBLE = "flexible"       # 灵活一致（允许合理变化）
    CONTEXTUAL = "contextual"   # 上下文相关（根据语境调整）


class ConflictSeverity(Enum):
    """冲突严重程度"""
    CRITICAL = "critical"       # 严重冲突（必须解决）
    HIGH = "high"              # 高级冲突（建议解决）
    MEDIUM = "medium"          # 中级冲突（可选解决）
    LOW = "low"                # 低级冲突（可忽略）


class ConflictResolutionStrategy(Enum):
    """冲突解决策略"""
    USE_MOST_FREQUENT = "use_most_frequent"     # 使用最频繁的版本
    USE_LATEST = "use_latest"                   # 使用最新的版本
    USE_AUTHORITATIVE = "use_authoritative"     # 使用权威版本
    MANUAL_REVIEW = "manual_review"             # 人工审核
    CONTEXT_DEPENDENT = "context_dependent"     # 根据上下文决定


@dataclass
class TermEntry:
    """术语条目"""
    term_id: str
    source_text: str                    # 源语言术语
    term_type: TermType                 # 术语类型
    consistency_level: ConsistencyLevel # 一致性要求
    translations: Dict[str, str]        # 各语言翻译 {language: translation}
    aliases: List[str]                  # 别名/变体
    context_examples: List[str]         # 上下文示例
    usage_frequency: int = 0            # 使用频率
    last_updated: datetime = None       # 最后更新时间
    created_by: str = "system"          # 创建者
    approved: bool = False              # 是否已审核
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TermConflict:
    """术语冲突"""
    conflict_id: str
    term_id: str
    source_text: str
    conflicting_translations: Dict[str, List[str]]  # {language: [conflicting_versions]}
    severity: ConflictSeverity
    contexts: List[str]                 # 冲突出现的上下文
    suggested_resolution: Optional[str] = None
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    detected_at: datetime = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


@dataclass
class ConsistencyCheckRequest:
    """一致性检查请求"""
    request_id: str
    project_id: str
    subtitle_entries: List[SubtitleEntry]
    target_languages: List[str]
    check_scope: str = "project"        # project, episode, scene
    strict_mode: bool = False
    auto_resolve: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    request_id: str
    success: bool
    conflicts_found: List[TermConflict]
    consistency_score: float            # 0.0-1.0
    total_terms_checked: int
    conflicting_terms_count: int
    auto_resolved_count: int = 0
    manual_review_required: int = 0
    processing_time_ms: int = 0
    recommendations: List[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TerminologyConsistencyManager:
    """术语一致性管理器
    
    主要功能：
    1. 术语库管理和查询
    2. 跨语言术语映射和同步
    3. 术语一致性检查和冲突检测
    4. 冲突解决策略和建议
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"term_manager_{uuid.uuid4().hex[:8]}"
        
        # 术语数据库
        self.term_database: Dict[str, TermEntry] = {}
        self.term_index: Dict[str, Set[str]] = defaultdict(set)  # source_text -> term_ids
        self.language_index: Dict[str, Dict[str, str]] = defaultdict(dict)  # lang -> {translation: term_id}
        
        # 冲突管理
        self.active_conflicts: Dict[str, TermConflict] = {}
        self.resolved_conflicts: Dict[str, TermConflict] = {}
        
        # 配置参数
        self.similarity_threshold = 0.8    # 相似度阈值
        self.frequency_weight = 0.3        # 频率权重
        self.recency_weight = 0.2          # 时效性权重
        self.authority_weight = 0.5        # 权威性权重
        
        # 性能统计
        self.performance_stats = {
            "total_terms": 0,
            "total_checks": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "average_consistency_score": 0.0,
            "language_coverage": defaultdict(int),
            "term_type_distribution": defaultdict(int),
            "conflict_severity_distribution": defaultdict(int)
        }
        
        # 初始化核心术语
        self._initialize_core_terms()
        
        logger.info("术语一致性管理器初始化完成", manager_id=self.manager_id)
    
    def _initialize_core_terms(self):
        """初始化核心术语"""
        core_terms = [
            # 人名术语
            TermEntry(
                term_id="person_zhang_wei",
                source_text="张伟",
                term_type=TermType.PERSON_NAME,
                consistency_level=ConsistencyLevel.STRICT,
                translations={
                    "en": "Zhang Wei",
                    "ja": "張偉",
                    "ko": "장위",
                    "fr": "Zhang Wei",
                    "de": "Zhang Wei"
                },
                aliases=["小张", "张队长"],
                context_examples=["张伟是我们的队长", "张伟同志"],
                approved=True
            ),
            
            # 军事术语
            TermEntry(
                term_id="military_commander",
                source_text="司令",
                term_type=TermType.MILITARY_TERM,
                consistency_level=ConsistencyLevel.MODERATE,
                translations={
                    "en": "Commander",
                    "ja": "司令官",
                    "ko": "사령관",
                    "fr": "Commandant",
                    "de": "Kommandant"
                },
                aliases=["司令员", "指挥官"],
                context_examples=["司令下达了命令", "海军司令"],
                approved=True
            ),
            
            # 技术术语
            TermEntry(
                term_id="tech_radar",
                source_text="雷达",
                term_type=TermType.TECHNICAL_TERM,
                consistency_level=ConsistencyLevel.STRICT,
                translations={
                    "en": "radar",
                    "ja": "レーダー",
                    "ko": "레이더",
                    "fr": "radar",
                    "de": "Radar"
                },
                aliases=["雷达系统"],
                context_examples=["雷达显示有目标", "雷达探测"],
                approved=True
            ),
            
            # 称谓术语
            TermEntry(
                term_id="title_captain",
                source_text="队长",
                term_type=TermType.TITLE,
                consistency_level=ConsistencyLevel.CONTEXTUAL,
                translations={
                    "en": "Captain",
                    "ja": "隊長",
                    "ko": "대장",
                    "fr": "Capitaine",
                    "de": "Hauptmann"
                },
                aliases=["队长同志", "小队长"],
                context_examples=["队长，有情况", "我们的队长"],
                approved=True
            ),
            
            # 地名术语
            TermEntry(
                term_id="place_beijing",
                source_text="北京",
                term_type=TermType.PLACE_NAME,
                consistency_level=ConsistencyLevel.STRICT,
                translations={
                    "en": "Beijing",
                    "ja": "北京",
                    "ko": "베이징",
                    "fr": "Pékin",
                    "de": "Peking"
                },
                aliases=["首都", "京城"],
                context_examples=["我来自北京", "北京的天气"],
                approved=True
            )
        ]
        
        # 添加到数据库
        for term in core_terms:
            self.add_term(term)
        
        logger.info("核心术语初始化完成", terms_count=len(core_terms))
    
    def add_term(self, term: TermEntry) -> bool:
        """添加术语"""
        try:
            # 添加到主数据库
            self.term_database[term.term_id] = term
            
            # 更新索引
            self.term_index[term.source_text].add(term.term_id)
            
            # 更新语言索引
            for language, translation in term.translations.items():
                self.language_index[language][translation] = term.term_id
            
            # 更新统计
            self.performance_stats["total_terms"] += 1
            self.performance_stats["term_type_distribution"][term.term_type.value] += 1
            
            for language in term.translations.keys():
                self.performance_stats["language_coverage"][language] += 1
            
            logger.debug("术语已添加", term_id=term.term_id, source_text=term.source_text)
            return True
            
        except Exception as e:
            logger.error("添加术语失败", term_id=term.term_id, error=str(e))
            return False
    
    def update_term(self, term_id: str, updates: Dict[str, Any]) -> bool:
        """更新术语"""
        try:
            if term_id not in self.term_database:
                logger.warning("术语不存在", term_id=term_id)
                return False
            
            term = self.term_database[term_id]
            old_translations = term.translations.copy()
            
            # 应用更新
            for field, value in updates.items():
                if hasattr(term, field):
                    setattr(term, field, value)
            
            term.last_updated = datetime.now()
            
            # 更新语言索引
            if "translations" in updates:
                # 移除旧的索引
                for language, translation in old_translations.items():
                    if translation in self.language_index[language]:
                        del self.language_index[language][translation]
                
                # 添加新的索引
                for language, translation in term.translations.items():
                    self.language_index[language][translation] = term_id
            
            logger.debug("术语已更新", term_id=term_id, updates=list(updates.keys()))
            return True
            
        except Exception as e:
            logger.error("更新术语失败", term_id=term_id, error=str(e))
            return False
    
    def remove_term(self, term_id: str) -> bool:
        """删除术语"""
        try:
            if term_id not in self.term_database:
                logger.warning("术语不存在", term_id=term_id)
                return False
            
            term = self.term_database[term_id]
            
            # 从索引中移除
            self.term_index[term.source_text].discard(term_id)
            if not self.term_index[term.source_text]:
                del self.term_index[term.source_text]
            
            # 从语言索引中移除
            for language, translation in term.translations.items():
                if translation in self.language_index[language]:
                    del self.language_index[language][translation]
            
            # 从主数据库中移除
            del self.term_database[term_id]
            
            # 更新统计
            self.performance_stats["total_terms"] -= 1
            
            logger.debug("术语已删除", term_id=term_id)
            return True
            
        except Exception as e:
            logger.error("删除术语失败", term_id=term_id, error=str(e))
            return False
    
    def find_terms(self, query: str, language: str = "zh", 
                  term_type: Optional[TermType] = None,
                  limit: int = 10) -> List[TermEntry]:
        """查找术语"""
        results = []
        
        # 精确匹配
        if query in self.term_index:
            for term_id in self.term_index[query]:
                term = self.term_database[term_id]
                if term_type is None or term.term_type == term_type:
                    results.append(term)
        
        # 语言索引匹配
        if language in self.language_index and query in self.language_index[language]:
            term_id = self.language_index[language][query]
            term = self.term_database[term_id]
            if term not in results and (term_type is None or term.term_type == term_type):
                results.append(term)
        
        # 模糊匹配
        if len(results) < limit:
            fuzzy_results = self._fuzzy_search(query, language, term_type, limit - len(results))
            for term in fuzzy_results:
                if term not in results:
                    results.append(term)
        
        return results[:limit]
    
    def _fuzzy_search(self, query: str, language: str, 
                     term_type: Optional[TermType], limit: int) -> List[TermEntry]:
        """模糊搜索"""
        candidates = []
        
        for term in self.term_database.values():
            if term_type and term.term_type != term_type:
                continue
            
            # 计算相似度
            similarity = 0.0
            
            # 与源文本的相似度
            source_similarity = difflib.SequenceMatcher(None, query, term.source_text).ratio()
            similarity = max(similarity, source_similarity)
            
            # 与翻译的相似度
            if language in term.translations:
                translation_similarity = difflib.SequenceMatcher(
                    None, query, term.translations[language]
                ).ratio()
                similarity = max(similarity, translation_similarity)
            
            # 与别名的相似度
            for alias in term.aliases:
                alias_similarity = difflib.SequenceMatcher(None, query, alias).ratio()
                similarity = max(similarity, alias_similarity)
            
            if similarity >= self.similarity_threshold:
                candidates.append((similarity, term))
        
        # 按相似度排序
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        return [term for _, term in candidates[:limit]]
    
    def check_consistency(self, request: ConsistencyCheckRequest) -> ConsistencyCheckResult:
        """检查术语一致性"""
        start_time = datetime.now()
        
        try:
            # 提取文本中的术语
            extracted_terms = self._extract_terms_from_subtitles(
                request.subtitle_entries, request.target_languages
            )
            
            # 检测冲突
            conflicts = self._detect_conflicts(extracted_terms, request)
            
            # 自动解决冲突（如果启用）
            auto_resolved_count = 0
            if request.auto_resolve:
                auto_resolved_count = self._auto_resolve_conflicts(conflicts)
            
            # 计算一致性分数
            consistency_score = self._calculate_consistency_score(extracted_terms, conflicts)
            
            # 生成建议
            recommendations = self._generate_recommendations(conflicts, extracted_terms)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计
            self._update_consistency_stats(extracted_terms, conflicts, consistency_score)
            
            result = ConsistencyCheckResult(
                request_id=request.request_id,
                success=True,
                conflicts_found=conflicts,
                consistency_score=consistency_score,
                total_terms_checked=len(extracted_terms),
                conflicting_terms_count=len(conflicts),
                auto_resolved_count=auto_resolved_count,
                manual_review_required=len([c for c in conflicts if not c.resolved]),
                processing_time_ms=int(processing_time),
                recommendations=recommendations
            )
            
            logger.info("术语一致性检查完成",
                       request_id=request.request_id,
                       terms_checked=len(extracted_terms),
                       conflicts_found=len(conflicts),
                       consistency_score=consistency_score)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.error("术语一致性检查失败",
                        request_id=request.request_id,
                        error=str(e))
            
            return ConsistencyCheckResult(
                request_id=request.request_id,
                success=False,
                conflicts_found=[],
                consistency_score=0.0,
                total_terms_checked=0,
                conflicting_terms_count=0,
                processing_time_ms=int(processing_time),
                error_message=str(e)
            )
    
    def _extract_terms_from_subtitles(self, subtitle_entries: List[SubtitleEntry],
                                    target_languages: List[str]) -> Dict[str, List[Tuple[str, str]]]:
        """从字幕中提取术语"""
        extracted_terms = defaultdict(list)  # {term_id: [(text, context)]}
        
        for entry in subtitle_entries:
            text = entry.text
            
            # 查找已知术语
            for source_text, term_ids in self.term_index.items():
                if source_text in text:
                    for term_id in term_ids:
                        context = f"字幕 {entry.index}: {text}"
                        extracted_terms[term_id].append((source_text, context))
            
            # 查找翻译术语
            for language in target_languages:
                if language in self.language_index:
                    for translation, term_id in self.language_index[language].items():
                        if translation in text:
                            context = f"字幕 {entry.index} ({language}): {text}"
                            extracted_terms[term_id].append((translation, context))
        
        return dict(extracted_terms)
    
    def _detect_conflicts(self, extracted_terms: Dict[str, List[Tuple[str, str]]],
                         request: ConsistencyCheckRequest) -> List[TermConflict]:
        """检测术语冲突"""
        conflicts = []
        
        for term_id, occurrences in extracted_terms.items():
            if term_id not in self.term_database:
                continue
            
            term = self.term_database[term_id]
            
            # 按语言分组检查
            language_variations = defaultdict(set)
            contexts = []
            
            for text, context in occurrences:
                contexts.append(context)
                
                # 确定这个文本属于哪种语言
                detected_language = self._detect_text_language(text, term)
                if detected_language:
                    language_variations[detected_language].add(text)
            
            # 检查每种语言的一致性
            conflicting_translations = {}
            for language, variations in language_variations.items():
                if len(variations) > 1:
                    # 有多个变体，可能存在冲突
                    conflicting_translations[language] = list(variations)
            
            # 如果发现冲突，创建冲突记录
            if conflicting_translations:
                severity = self._assess_conflict_severity(term, conflicting_translations)
                
                conflict = TermConflict(
                    conflict_id=str(uuid.uuid4()),
                    term_id=term_id,
                    source_text=term.source_text,
                    conflicting_translations=conflicting_translations,
                    severity=severity,
                    contexts=contexts[:5],  # 限制上下文数量
                    suggested_resolution=self._suggest_resolution(term, conflicting_translations),
                    resolution_strategy=self._determine_resolution_strategy(term, severity)
                )
                
                conflicts.append(conflict)
                self.active_conflicts[conflict.conflict_id] = conflict
        
        return conflicts
    
    def _detect_text_language(self, text: str, term: TermEntry) -> Optional[str]:
        """检测文本语言"""
        # 检查是否是源语言
        if text == term.source_text or text in term.aliases:
            return "zh"  # 假设源语言是中文
        
        # 检查是否是已知翻译
        for language, translation in term.translations.items():
            if text == translation:
                return language
        
        # 简单的语言检测（基于字符特征）
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"
        elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return "ja"
        elif re.search(r'[\uac00-\ud7af]', text):
            return "ko"
        elif re.search(r'[a-zA-Z]', text):
            return "en"  # 简化处理，实际需要更复杂的检测
        
        return None  
  
    def _assess_conflict_severity(self, term: TermEntry, 
                                conflicting_translations: Dict[str, List[str]]) -> ConflictSeverity:
        """评估冲突严重程度"""
        # 基于术语类型评估
        if term.term_type in [TermType.PERSON_NAME, TermType.PLACE_NAME]:
            return ConflictSeverity.CRITICAL
        elif term.term_type in [TermType.TECHNICAL_TERM, TermType.MILITARY_TERM]:
            return ConflictSeverity.HIGH
        elif term.term_type in [TermType.TITLE, TermType.ORGANIZATION]:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW
    
    def _suggest_resolution(self, term: TermEntry, 
                          conflicting_translations: Dict[str, List[str]]) -> str:
        """建议冲突解决方案"""
        suggestions = []
        
        for language, variations in conflicting_translations.items():
            if language in term.translations:
                # 推荐使用标准翻译
                standard_translation = term.translations[language]
                suggestions.append(f"{language}: 建议统一使用 '{standard_translation}'")
            else:
                # 推荐最常见的变体
                most_common = max(variations, key=lambda x: term.usage_frequency)
                suggestions.append(f"{language}: 建议统一使用 '{most_common}'")
        
        return "; ".join(suggestions)
    
    def _determine_resolution_strategy(self, term: TermEntry, 
                                     severity: ConflictSeverity) -> ConflictResolutionStrategy:
        """确定解决策略"""
        if severity == ConflictSeverity.CRITICAL:
            return ConflictResolutionStrategy.USE_AUTHORITATIVE
        elif severity == ConflictSeverity.HIGH:
            return ConflictResolutionStrategy.USE_MOST_FREQUENT
        elif term.consistency_level == ConsistencyLevel.CONTEXTUAL:
            return ConflictResolutionStrategy.CONTEXT_DEPENDENT
        else:
            return ConflictResolutionStrategy.USE_LATEST
    
    def _auto_resolve_conflicts(self, conflicts: List[TermConflict]) -> int:
        """自动解决冲突"""
        resolved_count = 0
        
        for conflict in conflicts:
            if conflict.resolution_strategy in [
                ConflictResolutionStrategy.USE_MOST_FREQUENT,
                ConflictResolutionStrategy.USE_LATEST,
                ConflictResolutionStrategy.USE_AUTHORITATIVE
            ]:
                # 尝试自动解决
                if self._apply_resolution_strategy(conflict):
                    conflict.resolved = True
                    conflict.resolution_notes = f"自动解决：{conflict.resolution_strategy.value}"
                    resolved_count += 1
                    
                    # 移动到已解决冲突
                    self.resolved_conflicts[conflict.conflict_id] = conflict
                    if conflict.conflict_id in self.active_conflicts:
                        del self.active_conflicts[conflict.conflict_id]
        
        return resolved_count
    
    def _apply_resolution_strategy(self, conflict: TermConflict) -> bool:
        """应用解决策略"""
        try:
            term = self.term_database.get(conflict.term_id)
            if not term:
                return False
            
            if conflict.resolution_strategy == ConflictResolutionStrategy.USE_AUTHORITATIVE:
                # 使用权威版本（已批准的翻译）
                for language, variations in conflict.conflicting_translations.items():
                    if language in term.translations:
                        # 更新术语使用频率
                        term.usage_frequency += len(variations)
                        return True
            
            elif conflict.resolution_strategy == ConflictResolutionStrategy.USE_MOST_FREQUENT:
                # 使用最频繁的版本
                for language, variations in conflict.conflicting_translations.items():
                    # 简化实现：选择第一个变体作为最频繁的
                    most_frequent = variations[0]
                    term.translations[language] = most_frequent
                    self.language_index[language][most_frequent] = term.term_id
                    return True
            
            elif conflict.resolution_strategy == ConflictResolutionStrategy.USE_LATEST:
                # 使用最新的版本
                term.last_updated = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            logger.error("应用解决策略失败", conflict_id=conflict.conflict_id, error=str(e))
            return False
    
    def _calculate_consistency_score(self, extracted_terms: Dict[str, List[Tuple[str, str]]],
                                   conflicts: List[TermConflict]) -> float:
        """计算一致性分数"""
        if not extracted_terms:
            return 1.0
        
        total_terms = len(extracted_terms)
        conflicting_terms = len(conflicts)
        
        # 基础一致性分数
        base_score = (total_terms - conflicting_terms) / total_terms
        
        # 根据冲突严重程度调整
        severity_penalty = 0.0
        for conflict in conflicts:
            if conflict.severity == ConflictSeverity.CRITICAL:
                severity_penalty += 0.2
            elif conflict.severity == ConflictSeverity.HIGH:
                severity_penalty += 0.1
            elif conflict.severity == ConflictSeverity.MEDIUM:
                severity_penalty += 0.05
            else:
                severity_penalty += 0.02
        
        # 应用惩罚
        adjusted_score = base_score - (severity_penalty / total_terms)
        
        return max(0.0, min(1.0, adjusted_score))
    
    def _generate_recommendations(self, conflicts: List[TermConflict],
                                extracted_terms: Dict[str, List[Tuple[str, str]]]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if not conflicts:
            recommendations.append("术语使用一致性良好，无需特别处理")
            return recommendations
        
        # 按严重程度分组
        critical_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
        high_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
        
        if critical_conflicts:
            recommendations.append(f"发现 {len(critical_conflicts)} 个严重术语冲突，需要立即处理")
        
        if high_conflicts:
            recommendations.append(f"发现 {len(high_conflicts)} 个高级术语冲突，建议优先处理")
        
        # 术语类型建议
        person_conflicts = [c for c in conflicts if self.term_database.get(c.term_id, {}).term_type == TermType.PERSON_NAME]
        if person_conflicts:
            recommendations.append("人名翻译存在不一致，建议建立人名翻译标准")
        
        # 自动化建议
        auto_resolvable = [c for c in conflicts if c.resolution_strategy != ConflictResolutionStrategy.MANUAL_REVIEW]
        if auto_resolvable:
            recommendations.append(f"{len(auto_resolvable)} 个冲突可以自动解决，建议启用自动解决功能")
        
        return recommendations
    
    def _update_consistency_stats(self, extracted_terms: Dict[str, List[Tuple[str, str]]],
                                conflicts: List[TermConflict], consistency_score: float):
        """更新一致性统计"""
        self.performance_stats["total_checks"] += 1
        self.performance_stats["conflicts_detected"] += len(conflicts)
        
        # 更新平均一致性分数
        total_checks = self.performance_stats["total_checks"]
        current_avg = self.performance_stats["average_consistency_score"]
        new_avg = (current_avg * (total_checks - 1) + consistency_score) / total_checks
        self.performance_stats["average_consistency_score"] = new_avg
        
        # 更新冲突严重程度分布
        for conflict in conflicts:
            self.performance_stats["conflict_severity_distribution"][conflict.severity.value] += 1
    
    def resolve_conflict(self, conflict_id: str, resolution: str, 
                        strategy: ConflictResolutionStrategy) -> bool:
        """手动解决冲突"""
        try:
            if conflict_id not in self.active_conflicts:
                logger.warning("冲突不存在或已解决", conflict_id=conflict_id)
                return False
            
            conflict = self.active_conflicts[conflict_id]
            
            # 应用解决方案
            if strategy == ConflictResolutionStrategy.MANUAL_REVIEW:
                # 手动解决，更新术语
                term = self.term_database.get(conflict.term_id)
                if term:
                    # 解析解决方案并更新术语
                    self._apply_manual_resolution(term, resolution)
            
            # 标记为已解决
            conflict.resolved = True
            conflict.resolution_notes = resolution
            conflict.resolution_strategy = strategy
            
            # 移动到已解决冲突
            self.resolved_conflicts[conflict_id] = conflict
            del self.active_conflicts[conflict_id]
            
            # 更新统计
            self.performance_stats["conflicts_resolved"] += 1
            
            logger.info("冲突已解决", conflict_id=conflict_id, strategy=strategy.value)
            return True
            
        except Exception as e:
            logger.error("解决冲突失败", conflict_id=conflict_id, error=str(e))
            return False
    
    def _apply_manual_resolution(self, term: TermEntry, resolution: str):
        """应用手动解决方案"""
        # 简化实现：假设resolution是JSON格式的翻译更新
        try:
            updates = json.loads(resolution)
            if "translations" in updates:
                term.translations.update(updates["translations"])
                term.last_updated = datetime.now()
                
                # 更新语言索引
                for language, translation in updates["translations"].items():
                    self.language_index[language][translation] = term.term_id
        except json.JSONDecodeError:
            # 如果不是JSON，作为注释处理
            if not term.metadata:
                term.metadata = {}
            term.metadata["manual_resolution"] = resolution
    
    def get_term_statistics(self) -> Dict[str, Any]:
        """获取术语统计信息"""
        return {
            "total_terms": len(self.term_database),
            "approved_terms": len([t for t in self.term_database.values() if t.approved]),
            "term_types": dict(self.performance_stats["term_type_distribution"]),
            "language_coverage": dict(self.performance_stats["language_coverage"]),
            "active_conflicts": len(self.active_conflicts),
            "resolved_conflicts": len(self.resolved_conflicts),
            "average_consistency_score": self.performance_stats["average_consistency_score"]
        }
    
    def export_terms(self, term_type: Optional[TermType] = None,
                    language: Optional[str] = None) -> Dict[str, Any]:
        """导出术语"""
        exported_terms = {}
        
        for term_id, term in self.term_database.items():
            if term_type and term.term_type != term_type:
                continue
            
            term_data = asdict(term)
            
            # 如果指定了语言，只导出该语言的翻译
            if language and language in term.translations:
                term_data["translations"] = {language: term.translations[language]}
            
            exported_terms[term_id] = term_data
        
        return {
            "export_time": datetime.now().isoformat(),
            "term_count": len(exported_terms),
            "filter_type": term_type.value if term_type else None,
            "filter_language": language,
            "terms": exported_terms
        }
    
    def import_terms(self, data: Dict[str, Any], merge_strategy: str = "update") -> bool:
        """导入术语"""
        try:
            terms_data = data.get("terms", {})
            imported_count = 0
            updated_count = 0
            
            for term_id, term_data in terms_data.items():
                # 重构TermEntry
                term = TermEntry(
                    term_id=term_id,
                    source_text=term_data["source_text"],
                    term_type=TermType(term_data["term_type"]),
                    consistency_level=ConsistencyLevel(term_data["consistency_level"]),
                    translations=term_data.get("translations", {}),
                    aliases=term_data.get("aliases", []),
                    context_examples=term_data.get("context_examples", []),
                    usage_frequency=term_data.get("usage_frequency", 0),
                    last_updated=datetime.fromisoformat(term_data["last_updated"]),
                    created_by=term_data.get("created_by", "import"),
                    approved=term_data.get("approved", False),
                    metadata=term_data.get("metadata", {})
                )
                
                if term_id in self.term_database:
                    if merge_strategy == "update":
                        # 更新现有术语
                        self.update_term(term_id, asdict(term))
                        updated_count += 1
                    # skip策略：跳过已存在的术语
                else:
                    # 添加新术语
                    self.add_term(term)
                    imported_count += 1
            
            logger.info("术语导入完成", 
                       imported=imported_count, 
                       updated=updated_count)
            return True
            
        except Exception as e:
            logger.error("术语导入失败", error=str(e))
            return False
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        return {
            "manager_id": self.manager_id,
            "term_database_size": len(self.term_database),
            "active_conflicts": len(self.active_conflicts),
            "resolved_conflicts": len(self.resolved_conflicts),
            "performance_stats": dict(self.performance_stats),
            "configuration": {
                "similarity_threshold": self.similarity_threshold,
                "frequency_weight": self.frequency_weight,
                "recency_weight": self.recency_weight,
                "authority_weight": self.authority_weight
            }
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_terms": len(self.term_database),
            "total_checks": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "average_consistency_score": 0.0,
            "language_coverage": defaultdict(int),
            "term_type_distribution": defaultdict(int),
            "conflict_severity_distribution": defaultdict(int)
        }
        
        # 重新计算语言覆盖和术语类型分布
        for term in self.term_database.values():
            self.performance_stats["term_type_distribution"][term.term_type.value] += 1
            for language in term.translations.keys():
                self.performance_stats["language_coverage"][language] += 1
        
        logger.info("统计信息已重置")
    
    def resolve_conflict(self, conflict_id: str, resolution: str, 
                        resolved_by: str = "system") -> bool:
        """手动解决冲突"""
        try:
            if conflict_id not in self.active_conflicts:
                logger.warning("冲突不存在", conflict_id=conflict_id)
                return False
            
            conflict = self.active_conflicts[conflict_id]
            conflict.resolved = True
            conflict.resolution_notes = f"手动解决 by {resolved_by}: {resolution}"
            
            # 移动到已解决冲突
            self.resolved_conflicts[conflict_id] = conflict
            del self.active_conflicts[conflict_id]
            
            # 更新统计
            self.performance_stats["conflicts_resolved"] += 1
            
            logger.info("冲突已解决", conflict_id=conflict_id, resolved_by=resolved_by)
            return True
            
        except Exception as e:
            logger.error("解决冲突失败", conflict_id=conflict_id, error=str(e))
            return False
    
    def get_conflict_summary(self) -> Dict[str, Any]:
        """获取冲突摘要"""
        active_by_severity = defaultdict(int)
        for conflict in self.active_conflicts.values():
            active_by_severity[conflict.severity.value] += 1
        
        return {
            "active_conflicts": len(self.active_conflicts),
            "resolved_conflicts": len(self.resolved_conflicts),
            "active_by_severity": dict(active_by_severity),
            "total_conflicts_detected": self.performance_stats["conflicts_detected"],
            "total_conflicts_resolved": self.performance_stats["conflicts_resolved"],
            "resolution_rate": (
                self.performance_stats["conflicts_resolved"] / 
                max(1, self.performance_stats["conflicts_detected"])
            ) * 100
        }


# 全局术语一致性管理器实例
terminology_consistency_manager = TerminologyConsistencyManager()


def get_terminology_consistency_manager() -> TerminologyConsistencyManager:
    """获取术语一致性管理器实例"""
    return terminology_consistency_manager


# 便捷函数
def check_terminology_consistency(project_id: str, subtitle_entries: List[SubtitleEntry],
                                target_languages: List[str], strict_mode: bool = False,
                                auto_resolve: bool = False) -> ConsistencyCheckResult:
    """便捷的术语一致性检查函数"""
    manager = get_terminology_consistency_manager()
    
    request = ConsistencyCheckRequest(
        request_id=str(uuid.uuid4()),
        project_id=project_id,
        subtitle_entries=subtitle_entries,
        target_languages=target_languages,
        strict_mode=strict_mode,
        auto_resolve=auto_resolve
    )
    
    return manager.check_consistency(request)


    
    def _assess_conflict_severity(self, term: TermEntry, 
                                conflicting_translations: Dict[str, List[str]]) -> ConflictSeverity:
        """评估冲突严重程度"""
        # 根据术语类型和一致性级别评估
        if term.consistency_level == ConsistencyLevel.STRICT:
            return ConflictSeverity.CRITICAL
        elif term.consistency_level == ConsistencyLevel.MODERATE:
            return ConflictSeverity.HIGH
        elif term.consistency_level == ConsistencyLevel.FLEXIBLE:
            return ConflictSeverity.MEDIUM
        else:  # CONTEXTUAL
            return ConflictSeverity.LOW
    
    def _suggest_resolution(self, term: TermEntry, 
                          conflicting_translations: Dict[str, List[str]]) -> str:
        """建议冲突解决方案"""
        suggestions = []
        
        for language, variations in conflicting_translations.items():
            if language in term.translations:
                # 推荐使用标准翻译
                standard_translation = term.translations[language]
                suggestions.append(f"建议在{language}中统一使用: {standard_translation}")
            else:
                # 推荐使用最频繁的变体
                most_frequent = max(variations, key=lambda x: term.usage_frequency)
                suggestions.append(f"建议在{language}中统一使用: {most_frequent}")
        
        return "; ".join(suggestions)
    
    def _determine_resolution_strategy(self, term: TermEntry, 
                                     severity: ConflictSeverity) -> ConflictResolutionStrategy:
        """确定解决策略"""
        if severity == ConflictSeverity.CRITICAL:
            return ConflictResolutionStrategy.USE_AUTHORITATIVE
        elif severity == ConflictSeverity.HIGH:
            return ConflictResolutionStrategy.USE_MOST_FREQUENT
        elif severity == ConflictSeverity.MEDIUM:
            return ConflictResolutionStrategy.USE_LATEST
        else:
            return ConflictResolutionStrategy.CONTEXT_DEPENDENT
    
    def _auto_resolve_conflicts(self, conflicts: List[TermConflict]) -> int:
        """自动解决冲突"""
        resolved_count = 0
        
        for conflict in conflicts:
            if conflict.resolution_strategy in [
                ConflictResolutionStrategy.USE_MOST_FREQUENT,
                ConflictResolutionStrategy.USE_LATEST,
                ConflictResolutionStrategy.USE_AUTHORITATIVE
            ]:
                if self._apply_resolution_strategy(conflict):
                    conflict.resolved = True
                    conflict.resolution_notes = f"自动解决: {conflict.resolution_strategy.value}"
                    resolved_count += 1
        
        return resolved_count
    
    def _apply_resolution_strategy(self, conflict: TermConflict) -> bool:
        """应用解决策略"""
        try:
            term = self.term_database.get(conflict.term_id)
            if not term:
                return False
            
            if conflict.resolution_strategy == ConflictResolutionStrategy.USE_AUTHORITATIVE:
                # 使用权威版本（已在术语库中的标准翻译）
                return True  # 标准翻译已存在，无需更改
            
            elif conflict.resolution_strategy == ConflictResolutionStrategy.USE_MOST_FREQUENT:
                # 使用最频繁的版本
                for language, variations in conflict.conflicting_translations.items():
                    # 简化处理：选择第一个变体作为标准
                    if variations:
                        term.translations[language] = variations[0]
                        self.update_term(conflict.term_id, {"translations": term.translations})
                return True
            
            elif conflict.resolution_strategy == ConflictResolutionStrategy.USE_LATEST:
                # 使用最新的版本（简化处理）
                return True
            
            return False
            
        except Exception as e:
            logger.error("应用解决策略失败", conflict_id=conflict.conflict_id, error=str(e))
            return False
    
    def _calculate_consistency_score(self, extracted_terms: Dict[str, List[Tuple[str, str]]],
                                   conflicts: List[TermConflict]) -> float:
        """计算一致性分数"""
        if not extracted_terms:
            return 1.0
        
        total_terms = len(extracted_terms)
        conflicting_terms = len(conflicts)
        
        # 基础分数
        base_score = (total_terms - conflicting_terms) / total_terms
        
        # 根据冲突严重程度调整
        severity_penalty = 0.0
        for conflict in conflicts:
            if conflict.severity == ConflictSeverity.CRITICAL:
                severity_penalty += 0.3
            elif conflict.severity == ConflictSeverity.HIGH:
                severity_penalty += 0.2
            elif conflict.severity == ConflictSeverity.MEDIUM:
                severity_penalty += 0.1
            else:
                severity_penalty += 0.05
        
        # 归一化惩罚
        if total_terms > 0:
            severity_penalty = severity_penalty / total_terms
        
        final_score = max(0.0, base_score - severity_penalty)
        return min(1.0, final_score)
    
    def _generate_recommendations(self, conflicts: List[TermConflict],
                                extracted_terms: Dict[str, List[Tuple[str, str]]]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if not conflicts:
            recommendations.append("术语使用一致性良好，无需特别调整")
            return recommendations
        
        # 按严重程度分组
        critical_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
        high_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
        
        if critical_conflicts:
            recommendations.append(f"发现{len(critical_conflicts)}个严重术语冲突，需要立即处理")
        
        if high_conflicts:
            recommendations.append(f"发现{len(high_conflicts)}个高级术语冲突，建议优先处理")
        
        # 术语覆盖建议
        uncovered_terms = []
        for term_id, occurrences in extracted_terms.items():
            if term_id not in self.term_database:
                uncovered_terms.append(term_id)
        
        if uncovered_terms:
            recommendations.append(f"发现{len(uncovered_terms)}个未收录术语，建议添加到术语库")
        
        # 一致性改进建议
        if len(conflicts) > len(extracted_terms) * 0.2:
            recommendations.append("术语冲突率较高，建议加强术语管理和培训")
        
        return recommendations
    
    def _update_consistency_stats(self, extracted_terms: Dict[str, List[Tuple[str, str]]],
                                conflicts: List[TermConflict], consistency_score: float):
        """更新一致性统计"""
        self.performance_stats["total_checks"] += 1
        self.performance_stats["conflicts_detected"] += len(conflicts)
        
        # 更新平均一致性分数
        current_avg = self.performance_stats["average_consistency_score"]
        total_checks = self.performance_stats["total_checks"]
        new_avg = ((current_avg * (total_checks - 1)) + consistency_score) / total_checks
        self.performance_stats["average_consistency_score"] = new_avg
        
        # 更新冲突严重程度分布
        for conflict in conflicts:
            self.performance_stats["conflict_severity_distribution"][conflict.severity.value] += 1
    
    def resolve_conflict(self, conflict_id: str, resolution: str, 
                        resolved_by: str = "system") -> bool:
        """手动解决冲突"""
        try:
            if conflict_id not in self.active_conflicts:
                logger.warning("冲突不存在", conflict_id=conflict_id)
                return False
            
            conflict = self.active_conflicts[conflict_id]
            conflict.resolved = True
            conflict.resolution_notes = f"手动解决 by {resolved_by}: {resolution}"
            
            # 移动到已解决冲突
            self.resolved_conflicts[conflict_id] = conflict
            del self.active_conflicts[conflict_id]
            
            # 更新统计
            self.performance_stats["conflicts_resolved"] += 1
            
            logger.info("冲突已解决", conflict_id=conflict_id, resolved_by=resolved_by)
            return True
            
        except Exception as e:
            logger.error("解决冲突失败", conflict_id=conflict_id, error=str(e))
            return False
    
    def get_conflict_summary(self) -> Dict[str, Any]:
        """获取冲突摘要"""
        active_by_severity = defaultdict(int)
        for conflict in self.active_conflicts.values():
            active_by_severity[conflict.severity.value] += 1
        
        return {
            "active_conflicts": len(self.active_conflicts),
            "resolved_conflicts": len(self.resolved_conflicts),
            "active_by_severity": dict(active_by_severity),
            "total_conflicts_detected": self.performance_stats["conflicts_detected"],
            "total_conflicts_resolved": self.performance_stats["conflicts_resolved"],
            "resolution_rate": (
                self.performance_stats["conflicts_resolved"] / 
                max(1, self.performance_stats["conflicts_detected"])
            ) * 100
        }
    
    def export_terminology_database(self, filepath: str) -> bool:
        """导出术语数据库"""
        try:
            export_data = {
                "metadata": {
                    "manager_id": self.manager_id,
                    "export_time": datetime.now().isoformat(),
                    "total_terms": len(self.term_database),
                    "version": "1.0"
                },
                "terms": [asdict(term) for term in self.term_database.values()],
                "performance_stats": self.performance_stats
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info("术语数据库已导出", filepath=filepath, terms_count=len(self.term_database))
            return True
            
        except Exception as e:
            logger.error("导出术语数据库失败", filepath=filepath, error=str(e))
            return False
    
    def import_terminology_database(self, filepath: str) -> bool:
        """导入术语数据库"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入术语
            imported_count = 0
            for term_data in import_data.get("terms", []):
                # 转换日期字符串
                if "last_updated" in term_data:
                    term_data["last_updated"] = datetime.fromisoformat(term_data["last_updated"])
                
                # 转换枚举
                term_data["term_type"] = TermType(term_data["term_type"])
                term_data["consistency_level"] = ConsistencyLevel(term_data["consistency_level"])
                
                term = TermEntry(**term_data)
                if self.add_term(term):
                    imported_count += 1
            
            logger.info("术语数据库已导入", filepath=filepath, imported_count=imported_count)
            return True
            
        except Exception as e:
            logger.error("导入术语数据库失败", filepath=filepath, error=str(e))
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            "basic_stats": {
                "total_terms": self.performance_stats["total_terms"],
                "total_checks": self.performance_stats["total_checks"],
                "conflicts_detected": self.performance_stats["conflicts_detected"],
                "conflicts_resolved": self.performance_stats["conflicts_resolved"],
                "average_consistency_score": self.performance_stats["average_consistency_score"]
            },
            "language_coverage": dict(self.performance_stats["language_coverage"]),
            "term_type_distribution": dict(self.performance_stats["term_type_distribution"]),
            "conflict_severity_distribution": dict(self.performance_stats["conflict_severity_distribution"]),
            "active_conflicts_count": len(self.active_conflicts),
            "resolved_conflicts_count": len(self.resolved_conflicts)
        }


# 导出主要类和枚举
__all__ = [
    'TermType', 'ConsistencyLevel', 'ConflictSeverity', 'ConflictResolutionStrategy',
    'TermEntry', 'TermConflict', 'ConsistencyCheckRequest', 'ConsistencyCheckResult',
    'TerminologyConsistencyManager'
]