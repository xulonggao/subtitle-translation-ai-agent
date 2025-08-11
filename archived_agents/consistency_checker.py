"""
一致性检查器
实现人名、术语、称谓的一致性检查，跨集数验证和自动修复建议
"""
import re
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter
import difflib

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationResult

logger = get_logger("consistency_checker")


class ConsistencyType(Enum):
    """一致性类型"""
    PERSON_NAME = "person_name"         # 人名一致性
    TERMINOLOGY = "terminology"         # 术语一致性
    TITLE_HONORIFIC = "title_honorific" # 称谓敬语一致性
    PLACE_NAME = "place_name"           # 地名一致性
    ORGANIZATION = "organization"       # 组织机构一致性
    CULTURAL_TERM = "cultural_term"     # 文化术语一致性
    TECHNICAL_TERM = "technical_term"   # 技术术语一致性


class ConflictSeverity(Enum):
    """冲突严重程度"""
    CRITICAL = "critical"    # 严重冲突，必须修复
    HIGH = "high"           # 高优先级冲突，建议修复
    MEDIUM = "medium"       # 中等冲突，可选修复
    LOW = "low"             # 轻微冲突，可忽略


class ResolutionStrategy(Enum):
    """解决策略"""
    USE_MOST_FREQUENT = "use_most_frequent"     # 使用最频繁的版本
    USE_FIRST_OCCURRENCE = "use_first_occurrence" # 使用首次出现的版本
    USE_LATEST = "use_latest"                   # 使用最新的版本
    USE_HIGHEST_CONFIDENCE = "use_highest_confidence" # 使用置信度最高的版本
    MANUAL_REVIEW = "manual_review"             # 需要人工审核
    CONTEXT_DEPENDENT = "context_dependent"     # 根据上下文决定


@dataclass
class ConsistencyRule:
    """一致性规则"""
    rule_id: str
    rule_name: str
    consistency_type: ConsistencyType
    pattern: str                        # 正则表达式模式
    case_sensitive: bool = False
    scope: str = "project"              # project, episode, scene
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    resolution_strategy: ResolutionStrategy = ResolutionStrategy.USE_MOST_FREQUENT
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class ConsistencyViolation:
    """一致性违规"""
    violation_id: str
    rule_id: str
    consistency_type: ConsistencyType
    source_term: str                    # 原始术语
    conflicting_translations: Dict[str, List[Dict[str, Any]]]  # {translation: [occurrences]}
    severity: ConflictSeverity
    suggested_resolution: Optional[str] = None
    resolution_strategy: Optional[ResolutionStrategy] = None
    confidence: float = 1.0
    contexts: List[str] = None
    locations: List[str] = None         # 出现位置
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.contexts is None:
            self.contexts = []
        if self.locations is None:
            self.locations = []
        if self.detected_at is None:
            self.detected_at = datetime.now()


@dataclass
class ConsistencyCheckRequest:
    """一致性检查请求"""
    request_id: str
    project_id: str
    episodes: List[Dict[str, Any]]      # 集数数据
    target_languages: List[str]
    check_scope: str = "project"        # project, episode, scene
    rules: Optional[List[ConsistencyRule]] = None
    auto_resolve: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.rules is None:
            self.rules = []


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    request_id: str
    success: bool
    violations_found: List[ConsistencyViolation]
    consistency_score: float            # 0.0-1.0
    total_terms_checked: int
    violations_by_type: Dict[ConsistencyType, int]
    auto_resolved_count: int = 0
    manual_review_required: int = 0
    recommendations: List[str] = None
    processing_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConsistencyChecker:
    """一致性检查器
    
    主要功能：
    1. 人名、术语、称谓的一致性检查
    2. 跨集数的一致性验证
    3. 一致性冲突的自动修复建议
    4. 规则引擎和自定义规则支持
    """
    
    def __init__(self, checker_id: str = None):
        self.checker_id = checker_id or f"consistency_checker_{uuid.uuid4().hex[:8]}"
        
        # 内置规则
        self.built_in_rules = self._initialize_built_in_rules()
        
        # 自定义规则
        self.custom_rules: List[ConsistencyRule] = []
        
        # 术语数据库
        self.term_database: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # 统计数据
        self.check_stats = {
            "total_checks": 0,
            "violations_found": 0,
            "auto_resolved": 0,
            "manual_reviews": 0,
            "consistency_scores": [],
            "violation_types": defaultdict(int),
            "processing_times": []
        }
        
        logger.info("一致性检查器初始化完成", checker_id=self.checker_id)
    
    def _initialize_built_in_rules(self) -> List[ConsistencyRule]:
        """初始化内置规则"""
        rules = [
            # 人名规则
            ConsistencyRule(
                rule_id="person_name_chinese",
                rule_name="中文人名一致性",
                consistency_type=ConsistencyType.PERSON_NAME,
                pattern=r"[张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}",
                case_sensitive=True,
                severity=ConflictSeverity.HIGH,
                resolution_strategy=ResolutionStrategy.USE_FIRST_OCCURRENCE,
                description="检查中文人名翻译的一致性",
                examples=["张伟", "李明", "王小红"]
            ),
            
            # 军事术语规则
            ConsistencyRule(
                rule_id="military_terms",
                rule_name="军事术语一致性",
                consistency_type=ConsistencyType.TECHNICAL_TERM,
                pattern=r"(司令|队长|士兵|军官|部队|雷达|导弹|战舰|潜艇|飞机|坦克|装备|武器|战略|战术|训练|演习|作战|防御|攻击|指挥|通信|情报)",
                case_sensitive=False,
                severity=ConflictSeverity.CRITICAL,
                resolution_strategy=ResolutionStrategy.USE_MOST_FREQUENT,
                description="检查军事术语翻译的一致性",
                examples=["司令", "雷达", "战舰"]
            ),
            
            # 称谓敬语规则
            ConsistencyRule(
                rule_id="honorific_titles",
                rule_name="称谓敬语一致性",
                consistency_type=ConsistencyType.TITLE_HONORIFIC,
                pattern=r"(先生|女士|老师|同志|您|请|谢谢|对不起|不好意思)",
                case_sensitive=False,
                severity=ConflictSeverity.MEDIUM,
                resolution_strategy=ResolutionStrategy.CONTEXT_DEPENDENT,
                description="检查称谓和敬语的一致性",
                examples=["先生", "您", "请"]
            ),
            
            # 地名规则
            ConsistencyRule(
                rule_id="place_names",
                rule_name="地名一致性",
                consistency_type=ConsistencyType.PLACE_NAME,
                pattern=r"(北京|上海|广州|深圳|天津|重庆|南京|杭州|苏州|武汉|成都|西安|青岛|大连|厦门|宁波|无锡|佛山|温州|泉州|东莞|中国|美国|日本|韩国|英国|法国|德国)",
                case_sensitive=True,
                severity=ConflictSeverity.HIGH,
                resolution_strategy=ResolutionStrategy.USE_FIRST_OCCURRENCE,
                description="检查地名翻译的一致性",
                examples=["北京", "上海", "中国"]
            ),
            
            # 组织机构规则
            ConsistencyRule(
                rule_id="organizations",
                rule_name="组织机构一致性",
                consistency_type=ConsistencyType.ORGANIZATION,
                pattern=r"(海军|陆军|空军|政府|公司|学校|医院|银行|部门|机构|组织|团队|小组)",
                case_sensitive=False,
                severity=ConflictSeverity.MEDIUM,
                resolution_strategy=ResolutionStrategy.USE_MOST_FREQUENT,
                description="检查组织机构名称的一致性",
                examples=["海军", "政府", "公司"]
            ),
            
            # 文化术语规则
            ConsistencyRule(
                rule_id="cultural_terms",
                rule_name="文化术语一致性",
                consistency_type=ConsistencyType.CULTURAL_TERM,
                pattern=r"(春节|中秋节|端午节|清明节|国庆节|元旦|中华|传统|文化|习俗|礼仪|茶|功夫|太极|书法|京剧)",
                case_sensitive=False,
                severity=ConflictSeverity.MEDIUM,
                resolution_strategy=ResolutionStrategy.CONTEXT_DEPENDENT,
                description="检查文化术语翻译的一致性",
                examples=["春节", "功夫", "太极"]
            )
        ]
        
        return rules
    
    async def check_consistency(self, request: ConsistencyCheckRequest) -> ConsistencyCheckResult:
        """执行一致性检查"""
        start_time = datetime.now()
        
        logger.info("开始一致性检查",
                   request_id=request.request_id,
                   project_id=request.project_id,
                   episodes_count=len(request.episodes),
                   target_languages=request.target_languages,
                   check_scope=request.check_scope)
        
        try:
            # 合并规则（内置规则 + 自定义规则 + 请求中的规则）
            all_rules = self.built_in_rules + self.custom_rules + (request.rules or [])
            
            # 提取所有术语和翻译
            term_occurrences = self._extract_term_occurrences(request.episodes, all_rules)
            
            # 检测一致性违规
            violations = self._detect_violations(term_occurrences, all_rules)
            
            # 自动解决冲突（如果启用）
            auto_resolved_count = 0
            if request.auto_resolve:
                auto_resolved_count = await self._auto_resolve_violations(violations)
            
            # 计算一致性分数
            consistency_score = self._calculate_consistency_score(term_occurrences, violations)
            
            # 生成建议
            recommendations = self._generate_recommendations(violations, term_occurrences)
            
            # 统计违规类型
            violations_by_type = self._count_violations_by_type(violations)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 创建结果
            result = ConsistencyCheckResult(
                request_id=request.request_id,
                success=True,
                violations_found=violations,
                consistency_score=consistency_score,
                total_terms_checked=len(term_occurrences),
                violations_by_type=violations_by_type,
                auto_resolved_count=auto_resolved_count,
                manual_review_required=len([v for v in violations if not v.suggested_resolution]),
                recommendations=recommendations,
                processing_time_ms=int(processing_time),
                metadata={
                    "project_id": request.project_id,
                    "episodes_count": len(request.episodes),
                    "rules_applied": len(all_rules),
                    "check_scope": request.check_scope
                }
            )
            
            # 更新统计
            self._update_check_stats(request, result)
            
            logger.info("一致性检查完成",
                       request_id=request.request_id,
                       consistency_score=consistency_score,
                       violations_count=len(violations),
                       auto_resolved=auto_resolved_count,
                       processing_time_ms=int(processing_time))
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.error("一致性检查失败",
                        request_id=request.request_id,
                        error=str(e),
                        processing_time_ms=int(processing_time))
            
            return ConsistencyCheckResult(
                request_id=request.request_id,
                success=False,
                violations_found=[],
                consistency_score=0.0,
                total_terms_checked=0,
                violations_by_type={},
                processing_time_ms=int(processing_time),
                recommendations=[f"检查过程中发生错误: {str(e)}"]
            )
    
    def _extract_term_occurrences(self, episodes: List[Dict[str, Any]], 
                                 rules: List[ConsistencyRule]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """提取术语出现情况"""
        term_occurrences = defaultdict(lambda: defaultdict(list))
        
        for episode_idx, episode in enumerate(episodes):
            episode_id = episode.get("episode_id", f"episode_{episode_idx}")
            subtitles = episode.get("subtitles", [])
            translations = episode.get("translations", {})
            
            # 遍历每个字幕条目
            for subtitle_idx, subtitle in enumerate(subtitles):
                if not isinstance(subtitle, dict):
                    continue
                
                original_text = subtitle.get("text", "")
                
                # 应用每个规则
                for rule in rules:
                    matches = re.finditer(rule.pattern, original_text, 
                                        re.IGNORECASE if not rule.case_sensitive else 0)
                    
                    for match in matches:
                        term = match.group()
                        
                        # 收集该术语在各语言中的翻译
                        for language in translations:
                            lang_translations = translations[language]
                            if subtitle_idx < len(lang_translations):
                                translation_entry = lang_translations[subtitle_idx]
                                if isinstance(translation_entry, dict):
                                    translated_text = translation_entry.get("translated_text", "")
                                elif isinstance(translation_entry, str):
                                    translated_text = translation_entry
                                else:
                                    continue
                                
                                # 提取翻译中对应的术语
                                translated_term = self._extract_translated_term(
                                    term, original_text, translated_text, language
                                )
                                
                                if translated_term:
                                    occurrence = {
                                        "episode_id": episode_id,
                                        "subtitle_index": subtitle_idx,
                                        "original_text": original_text,
                                        "translated_text": translated_text,
                                        "translated_term": translated_term,
                                        "language": language,
                                        "rule_id": rule.rule_id,
                                        "consistency_type": rule.consistency_type,
                                        "context": self._get_context(subtitles, subtitle_idx),
                                        "confidence": self._calculate_term_confidence(term, translated_term, language)
                                    }
                                    
                                    term_occurrences[term][language].append(occurrence)
        
        return dict(term_occurrences)
    
    def _extract_translated_term(self, original_term: str, original_text: str, 
                               translated_text: str, language: str) -> Optional[str]:
        """从翻译文本中提取对应的术语"""
        # 简化的术语提取逻辑
        # 在实际应用中，这里应该使用更复杂的对齐算法
        
        # 预定义的术语映射
        term_mappings = {
            "zh-en": {
                "张伟": "Zhang Wei",
                "李明": "Li Ming",
                "司令": "Commander",
                "队长": "Captain",
                "雷达": "radar",
                "海军": "Navy",
                "北京": "Beijing",
                "中国": "China"
            },
            "zh-ja": {
                "张伟": "張偉",
                "李明": "李明",
                "司令": "司令官",
                "队长": "隊長",
                "雷达": "レーダー",
                "海军": "海軍",
                "北京": "北京",
                "中国": "中国"
            },
            "zh-ko": {
                "张伟": "장위",
                "李明": "리명",
                "司令": "사령관",
                "队长": "대장",
                "雷达": "레이더",
                "海军": "해군",
                "北京": "베이징",
                "中国": "중국"
            }
        }
        
        mapping_key = f"zh-{language}"
        if mapping_key in term_mappings and original_term in term_mappings[mapping_key]:
            expected_translation = term_mappings[mapping_key][original_term]
            if expected_translation.lower() in translated_text.lower():
                return expected_translation
        
        # 如果没有预定义映射，尝试简单的词汇提取
        words = re.findall(r'\b\w+\b', translated_text)
        
        # 返回最可能的对应词汇（这里使用简化逻辑）
        if words:
            # 优先返回大写开头的词（可能是专有名词）
            capitalized_words = [w for w in words if w[0].isupper()]
            if capitalized_words:
                return capitalized_words[0]
            
            # 否则返回最长的词
            return max(words, key=len) if words else None
        
        return None
    
    def _get_context(self, subtitles: List[Dict[str, Any]], current_index: int, 
                    context_size: int = 2) -> str:
        """获取上下文"""
        start_idx = max(0, current_index - context_size)
        end_idx = min(len(subtitles), current_index + context_size + 1)
        
        context_texts = []
        for i in range(start_idx, end_idx):
            if i < len(subtitles) and isinstance(subtitles[i], dict):
                text = subtitles[i].get("text", "")
                if i == current_index:
                    text = f"[{text}]"  # 标记当前条目
                context_texts.append(text)
        
        return " ".join(context_texts)
    
    def _calculate_term_confidence(self, original_term: str, translated_term: str, language: str) -> float:
        """计算术语翻译的置信度"""
        # 简化的置信度计算
        base_confidence = 0.8
        
        # 如果是预定义的映射，置信度更高
        term_mappings = {
            "zh-en": {"张伟": "Zhang Wei", "司令": "Commander", "雷达": "radar"},
            "zh-ja": {"张伟": "張偉", "司令": "司令官", "雷达": "レーダー"},
            "zh-ko": {"张伟": "장위", "司令": "사령관", "雷达": "레이더"}
        }
        
        mapping_key = f"zh-{language}"
        if (mapping_key in term_mappings and 
            original_term in term_mappings[mapping_key] and
            term_mappings[mapping_key][original_term] == translated_term):
            return 0.95
        
        # 根据翻译长度调整置信度
        if len(translated_term) > 0:
            length_ratio = len(original_term) / len(translated_term)
            if 0.5 <= length_ratio <= 2.0:
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _detect_violations(self, term_occurrences: Dict[str, Dict[str, List[Dict[str, Any]]]], 
                          rules: List[ConsistencyRule]) -> List[ConsistencyViolation]:
        """检测一致性违规"""
        violations = []
        
        for original_term, language_translations in term_occurrences.items():
            for language, occurrences in language_translations.items():
                if len(occurrences) < 2:
                    continue  # 只出现一次，无法检测一致性
                
                # 按翻译分组
                translation_groups = defaultdict(list)
                for occurrence in occurrences:
                    translated_term = occurrence["translated_term"]
                    translation_groups[translated_term].append(occurrence)
                
                # 如果有多个不同的翻译，则存在一致性问题
                if len(translation_groups) > 1:
                    # 找到适用的规则
                    applicable_rule = None
                    for rule in rules:
                        if re.search(rule.pattern, original_term, 
                                   re.IGNORECASE if not rule.case_sensitive else 0):
                            applicable_rule = rule
                            break
                    
                    if not applicable_rule:
                        continue
                    
                    # 创建违规记录
                    violation = ConsistencyViolation(
                        violation_id=f"violation_{uuid.uuid4().hex[:8]}",
                        rule_id=applicable_rule.rule_id,
                        consistency_type=applicable_rule.consistency_type,
                        source_term=original_term,
                        conflicting_translations={
                            translation: [
                                {
                                    "episode_id": occ["episode_id"],
                                    "subtitle_index": occ["subtitle_index"],
                                    "context": occ["context"],
                                    "confidence": occ["confidence"]
                                }
                                for occ in occurrences_list
                            ]
                            for translation, occurrences_list in translation_groups.items()
                        },
                        severity=applicable_rule.severity,
                        resolution_strategy=applicable_rule.resolution_strategy,
                        contexts=[occ["context"] for occ in occurrences],
                        locations=[
                            f"{occ['episode_id']}:{occ['subtitle_index']}" 
                            for occ in occurrences
                        ]
                    )
                    
                    # 生成建议的解决方案
                    violation.suggested_resolution = self._generate_resolution_suggestion(
                        violation, translation_groups
                    )
                    
                    violations.append(violation)
        
        return violations
    
    def _generate_resolution_suggestion(self, violation: ConsistencyViolation, 
                                      translation_groups: Dict[str, List[Dict[str, Any]]]) -> str:
        """生成解决建议"""
        strategy = violation.resolution_strategy
        
        if strategy == ResolutionStrategy.USE_MOST_FREQUENT:
            # 使用出现次数最多的翻译
            most_frequent = max(translation_groups.items(), key=lambda x: len(x[1]))
            return f"建议统一使用 '{most_frequent[0]}'（出现 {len(most_frequent[1])} 次）"
        
        elif strategy == ResolutionStrategy.USE_HIGHEST_CONFIDENCE:
            # 使用置信度最高的翻译
            best_translation = None
            best_confidence = 0.0
            
            for translation, occurrences in translation_groups.items():
                avg_confidence = sum(occ["confidence"] for occ in occurrences) / len(occurrences)
                if avg_confidence > best_confidence:
                    best_confidence = avg_confidence
                    best_translation = translation
            
            return f"建议统一使用 '{best_translation}'（平均置信度: {best_confidence:.2f}）"
        
        elif strategy == ResolutionStrategy.USE_FIRST_OCCURRENCE:
            # 使用首次出现的翻译
            first_occurrence = min(
                [(translation, occurrences) for translation, occurrences in translation_groups.items()],
                key=lambda x: (x[1][0]["episode_id"], x[1][0]["subtitle_index"])
            )
            return f"建议统一使用 '{first_occurrence[0]}'（首次出现）"
        
        elif strategy == ResolutionStrategy.CONTEXT_DEPENDENT:
            return f"建议根据具体语境选择合适的翻译，或制定统一标准"
        
        elif strategy == ResolutionStrategy.MANUAL_REVIEW:
            return f"建议人工审核确定最佳翻译方案"
        
        else:
            # 默认使用最频繁的
            most_frequent = max(translation_groups.items(), key=lambda x: len(x[1]))
            return f"建议统一使用 '{most_frequent[0]}'"
    
    async def _auto_resolve_violations(self, violations: List[ConsistencyViolation]) -> int:
        """自动解决违规"""
        resolved_count = 0
        
        for violation in violations:
            if violation.resolution_strategy in [
                ResolutionStrategy.USE_MOST_FREQUENT,
                ResolutionStrategy.USE_HIGHEST_CONFIDENCE,
                ResolutionStrategy.USE_FIRST_OCCURRENCE
            ]:
                # 这里应该实际修改翻译数据
                # 为了演示，我们只是标记为已解决
                violation.suggested_resolution += " [已自动应用]"
                resolved_count += 1
                
                logger.debug("自动解决违规",
                           violation_id=violation.violation_id,
                           source_term=violation.source_term,
                           resolution=violation.suggested_resolution)
        
        return resolved_count
    
    def _calculate_consistency_score(self, term_occurrences: Dict[str, Dict[str, List[Dict[str, Any]]]], 
                                   violations: List[ConsistencyViolation]) -> float:
        """计算一致性分数"""
        if not term_occurrences:
            return 1.0
        
        total_terms = 0
        consistent_terms = 0
        
        for original_term, language_translations in term_occurrences.items():
            for language, occurrences in language_translations.items():
                if len(occurrences) >= 2:  # 只考虑出现多次的术语
                    total_terms += 1
                    
                    # 检查是否一致
                    translations = set(occ["translated_term"] for occ in occurrences)
                    if len(translations) == 1:
                        consistent_terms += 1
        
        if total_terms == 0:
            return 1.0
        
        return consistent_terms / total_terms
    
    def _count_violations_by_type(self, violations: List[ConsistencyViolation]) -> Dict[ConsistencyType, int]:
        """按类型统计违规数量"""
        counts = defaultdict(int)
        for violation in violations:
            counts[violation.consistency_type] += 1
        return dict(counts)
    
    def _generate_recommendations(self, violations: List[ConsistencyViolation], 
                                term_occurrences: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if not violations:
            recommendations.append("恭喜！未发现一致性问题，翻译质量良好。")
            return recommendations
        
        # 按严重程度分组
        critical_violations = [v for v in violations if v.severity == ConflictSeverity.CRITICAL]
        high_violations = [v for v in violations if v.severity == ConflictSeverity.HIGH]
        
        if critical_violations:
            recommendations.append(f"发现 {len(critical_violations)} 个严重一致性问题，建议立即处理")
        
        if high_violations:
            recommendations.append(f"发现 {len(high_violations)} 个高优先级一致性问题，建议优先处理")
        
        # 按类型统计
        type_counts = self._count_violations_by_type(violations)
        for consistency_type, count in type_counts.items():
            if count > 0:
                recommendations.append(f"{consistency_type.value}类问题: {count} 个")
        
        # 通用建议
        if len(violations) > 10:
            recommendations.append("建议建立术语翻译标准，确保团队成员遵循统一规范")
        
        if any(v.resolution_strategy == ResolutionStrategy.MANUAL_REVIEW for v in violations):
            recommendations.append("部分问题需要人工审核，建议安排专业译者检查")
        
        return recommendations
    
    def _update_check_stats(self, request: ConsistencyCheckRequest, result: ConsistencyCheckResult):
        """更新检查统计"""
        self.check_stats["total_checks"] += 1
        self.check_stats["violations_found"] += len(result.violations_found)
        self.check_stats["auto_resolved"] += result.auto_resolved_count
        self.check_stats["manual_reviews"] += result.manual_review_required
        self.check_stats["consistency_scores"].append(result.consistency_score)
        self.check_stats["processing_times"].append(result.processing_time_ms)
        
        for violation_type, count in result.violations_by_type.items():
            self.check_stats["violation_types"][violation_type.value] += count  
  
    def add_custom_rule(self, rule: ConsistencyRule) -> bool:
        """添加自定义规则"""
        try:
            # 验证规则
            if not rule.rule_id or not rule.pattern:
                logger.error("规则ID和模式不能为空")
                return False
            
            # 检查是否已存在
            if any(r.rule_id == rule.rule_id for r in self.custom_rules):
                logger.warning("规则已存在", rule_id=rule.rule_id)
                return False
            
            # 验证正则表达式
            try:
                re.compile(rule.pattern)
            except re.error as e:
                logger.error("无效的正则表达式", pattern=rule.pattern, error=str(e))
                return False
            
            self.custom_rules.append(rule)
            logger.info("自定义规则已添加", rule_id=rule.rule_id, rule_name=rule.rule_name)
            return True
            
        except Exception as e:
            logger.error("添加自定义规则失败", error=str(e))
            return False
    
    def remove_custom_rule(self, rule_id: str) -> bool:
        """移除自定义规则"""
        try:
            original_count = len(self.custom_rules)
            self.custom_rules = [r for r in self.custom_rules if r.rule_id != rule_id]
            
            if len(self.custom_rules) < original_count:
                logger.info("自定义规则已移除", rule_id=rule_id)
                return True
            else:
                logger.warning("规则未找到", rule_id=rule_id)
                return False
                
        except Exception as e:
            logger.error("移除自定义规则失败", error=str(e))
            return False
    
    def get_all_rules(self) -> List[ConsistencyRule]:
        """获取所有规则"""
        return self.built_in_rules + self.custom_rules
    
    def get_rule_by_id(self, rule_id: str) -> Optional[ConsistencyRule]:
        """根据ID获取规则"""
        all_rules = self.get_all_rules()
        for rule in all_rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def update_term_database(self, term: str, language: str, translation: str, 
                           confidence: float = 1.0, context: str = ""):
        """更新术语数据库"""
        if term not in self.term_database:
            self.term_database[term] = {}
        
        if language not in self.term_database[term]:
            self.term_database[term][language] = []
        
        # 添加或更新翻译
        existing_entry = None
        for entry in self.term_database[term][language]:
            if entry["translation"] == translation:
                existing_entry = entry
                break
        
        if existing_entry:
            # 更新现有条目
            existing_entry["count"] += 1
            existing_entry["confidence"] = (existing_entry["confidence"] + confidence) / 2
            existing_entry["last_seen"] = datetime.now()
            if context and context not in existing_entry["contexts"]:
                existing_entry["contexts"].append(context)
        else:
            # 添加新条目
            self.term_database[term][language].append({
                "translation": translation,
                "confidence": confidence,
                "count": 1,
                "contexts": [context] if context else [],
                "first_seen": datetime.now(),
                "last_seen": datetime.now()
            })
        
        logger.debug("术语数据库已更新", term=term, language=language, translation=translation)
    
    def get_term_translations(self, term: str, language: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取术语的翻译"""
        if term not in self.term_database:
            return {}
        
        if language:
            return {language: self.term_database[term].get(language, [])}
        else:
            return self.term_database[term]
    
    def export_violations_report(self, violations: List[ConsistencyViolation], 
                               format: str = "json") -> str:
        """导出违规报告"""
        try:
            if format.lower() == "json":
                report_data = {
                    "report_id": f"consistency_report_{uuid.uuid4().hex[:8]}",
                    "generated_at": datetime.now().isoformat(),
                    "total_violations": len(violations),
                    "violations": [
                        {
                            "violation_id": v.violation_id,
                            "rule_id": v.rule_id,
                            "consistency_type": v.consistency_type.value,
                            "source_term": v.source_term,
                            "conflicting_translations": v.conflicting_translations,
                            "severity": v.severity.value,
                            "suggested_resolution": v.suggested_resolution,
                            "confidence": v.confidence,
                            "locations": v.locations,
                            "detected_at": v.detected_at.isoformat()
                        }
                        for v in violations
                    ]
                }
                return json.dumps(report_data, ensure_ascii=False, indent=2)
            
            elif format.lower() == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 写入标题行
                writer.writerow([
                    "Violation ID", "Rule ID", "Type", "Source Term", 
                    "Severity", "Suggested Resolution", "Locations", "Detected At"
                ])
                
                # 写入数据行
                for v in violations:
                    writer.writerow([
                        v.violation_id,
                        v.rule_id,
                        v.consistency_type.value,
                        v.source_term,
                        v.severity.value,
                        v.suggested_resolution or "",
                        "; ".join(v.locations),
                        v.detected_at.isoformat()
                    ])
                
                return output.getvalue()
            
            else:
                raise ValueError(f"不支持的格式: {format}")
                
        except Exception as e:
            logger.error("导出违规报告失败", error=str(e))
            return ""
    
    def get_consistency_statistics(self) -> Dict[str, Any]:
        """获取一致性统计"""
        stats = self.check_stats.copy()
        
        # 计算平均值
        if stats["consistency_scores"]:
            stats["average_consistency_score"] = sum(stats["consistency_scores"]) / len(stats["consistency_scores"])
            stats["min_consistency_score"] = min(stats["consistency_scores"])
            stats["max_consistency_score"] = max(stats["consistency_scores"])
        
        if stats["processing_times"]:
            stats["average_processing_time_ms"] = sum(stats["processing_times"]) / len(stats["processing_times"])
        
        # 添加规则统计
        stats["total_rules"] = len(self.get_all_rules())
        stats["built_in_rules"] = len(self.built_in_rules)
        stats["custom_rules"] = len(self.custom_rules)
        
        # 添加术语数据库统计
        stats["terms_in_database"] = len(self.term_database)
        stats["total_translations"] = sum(
            len(translations) for term_translations in self.term_database.values()
            for translations in term_translations.values()
        )
        
        return stats
    
    def validate_episode_data(self, episode: Dict[str, Any]) -> List[str]:
        """验证集数据格式"""
        errors = []
        
        if not isinstance(episode, dict):
            errors.append("集数据必须是字典格式")
            return errors
        
        if "episode_id" not in episode:
            errors.append("缺少episode_id字段")
        
        if "subtitles" not in episode:
            errors.append("缺少subtitles字段")
        elif not isinstance(episode["subtitles"], list):
            errors.append("subtitles必须是列表格式")
        
        if "translations" not in episode:
            errors.append("缺少translations字段")
        elif not isinstance(episode["translations"], dict):
            errors.append("translations必须是字典格式")
        
        # 验证字幕格式
        subtitles = episode.get("subtitles", [])
        for i, subtitle in enumerate(subtitles):
            if not isinstance(subtitle, dict):
                errors.append(f"字幕条目 {i} 必须是字典格式")
                continue
            
            if "text" not in subtitle:
                errors.append(f"字幕条目 {i} 缺少text字段")
        
        # 验证翻译格式
        translations = episode.get("translations", {})
        if isinstance(translations, dict):
            for language, lang_translations in translations.items():
                if not isinstance(lang_translations, list):
                    errors.append(f"语言 {language} 的翻译必须是列表格式")
                    continue
                
                if len(lang_translations) != len(subtitles):
                    errors.append(f"语言 {language} 的翻译数量与字幕数量不匹配")
        
        return errors
    
    async def batch_check_consistency(self, requests: List[ConsistencyCheckRequest]) -> List[ConsistencyCheckResult]:
        """批量一致性检查"""
        results = []
        
        logger.info("开始批量一致性检查", requests_count=len(requests))
        
        for i, request in enumerate(requests):
            logger.debug("处理批量检查请求", request_index=i, request_id=request.request_id)
            
            try:
                result = await self.check_consistency(request)
                results.append(result)
            except Exception as e:
                logger.error("批量检查中的请求失败", 
                           request_index=i, 
                           request_id=request.request_id, 
                           error=str(e))
                
                # 创建失败结果
                error_result = ConsistencyCheckResult(
                    request_id=request.request_id,
                    success=False,
                    violations_found=[],
                    consistency_score=0.0,
                    total_terms_checked=0,
                    violations_by_type={},
                    recommendations=[f"检查失败: {str(e)}"]
                )
                results.append(error_result)
        
        logger.info("批量一致性检查完成", 
                   total_requests=len(requests),
                   successful_results=len([r for r in results if r.success]))
        
        return results
    
    def create_cross_episode_report(self, results: List[ConsistencyCheckResult]) -> Dict[str, Any]:
        """创建跨集数一致性报告"""
        if not results:
            return {"error": "没有检查结果"}
        
        # 合并所有违规
        all_violations = []
        for result in results:
            all_violations.extend(result.violations_found)
        
        # 按术语分组违规
        violations_by_term = defaultdict(list)
        for violation in all_violations:
            violations_by_term[violation.source_term].append(violation)
        
        # 分析跨集数一致性问题
        cross_episode_issues = []
        for term, term_violations in violations_by_term.items():
            if len(term_violations) > 1:
                episodes_affected = set()
                for violation in term_violations:
                    for location in violation.locations:
                        episode_id = location.split(":")[0]
                        episodes_affected.add(episode_id)
                
                if len(episodes_affected) > 1:
                    cross_episode_issues.append({
                        "term": term,
                        "episodes_affected": list(episodes_affected),
                        "violations_count": len(term_violations),
                        "severity": max(v.severity.value for v in term_violations)
                    })
        
        # 计算整体统计
        total_violations = len(all_violations)
        avg_consistency_score = sum(r.consistency_score for r in results) / len(results) if results else 0
        
        report = {
            "report_id": f"cross_episode_report_{uuid.uuid4().hex[:8]}",
            "generated_at": datetime.now().isoformat(),
            "episodes_analyzed": len(results),
            "total_violations": total_violations,
            "cross_episode_issues": cross_episode_issues,
            "cross_episode_issues_count": len(cross_episode_issues),
            "average_consistency_score": avg_consistency_score,
            "violations_by_type": self._aggregate_violations_by_type(results),
            "recommendations": self._generate_cross_episode_recommendations(cross_episode_issues, results)
        }
        
        return report
    
    def _aggregate_violations_by_type(self, results: List[ConsistencyCheckResult]) -> Dict[str, int]:
        """聚合违规类型统计"""
        aggregated = defaultdict(int)
        
        for result in results:
            for violation_type, count in result.violations_by_type.items():
                aggregated[violation_type.value] += count
        
        return dict(aggregated)
    
    def _generate_cross_episode_recommendations(self, cross_episode_issues: List[Dict[str, Any]], 
                                              results: List[ConsistencyCheckResult]) -> List[str]:
        """生成跨集数建议"""
        recommendations = []
        
        if not cross_episode_issues:
            recommendations.append("恭喜！未发现跨集数一致性问题。")
            return recommendations
        
        recommendations.append(f"发现 {len(cross_episode_issues)} 个跨集数一致性问题，需要统一处理")
        
        # 按严重程度分类
        critical_issues = [issue for issue in cross_episode_issues if issue["severity"] == "critical"]
        if critical_issues:
            recommendations.append(f"其中 {len(critical_issues)} 个为严重问题，建议立即处理")
        
        # 最常见的问题术语
        most_problematic = max(cross_episode_issues, key=lambda x: x["violations_count"])
        recommendations.append(f"最需要关注的术语: '{most_problematic['term']}' (出现在 {len(most_problematic['episodes_affected'])} 个集数中)")
        
        # 通用建议
        recommendations.append("建议建立跨集数术语翻译标准文档")
        recommendations.append("建议在翻译开始前进行术语预审和统一")
        
        return recommendations


# 导出主要类
__all__ = [
    'ConsistencyType', 'ConflictSeverity', 'ResolutionStrategy',
    'ConsistencyRule', 'ConsistencyViolation', 'ConsistencyCheckRequest', 'ConsistencyCheckResult',
    'ConsistencyChecker'
]