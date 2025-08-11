"""
文化本土化引擎
处理文化特定词汇的翻译和本土化适配
"""
import json
import uuid
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.story_models import StoryContext, CharacterRelation

logger = get_logger("cultural_localization_agent")


class CulturalCategory(Enum):
    """文化词汇类别"""
    MODERN_LIFE = "modern_life"           # 现代生活词汇
    INTERNET_SLANG = "internet_slang"     # 网络流行语
    SOCIAL_PHENOMENON = "social_phenomenon" # 社会现象
    FAMILY_EDUCATION = "family_education"  # 家庭教育
    WORK_CULTURE = "work_culture"         # 工作文化
    RELATIONSHIP = "relationship"         # 人际关系
    FOOD_CULTURE = "food_culture"         # 饮食文化
    TRADITIONAL_CULTURE = "traditional_culture" # 传统文化
    REGIONAL_DIALECT = "regional_dialect" # 地方方言
    GENERATIONAL = "generational"        # 代际差异


class CulturalContext(Enum):
    """文化背景"""
    CHINESE_MAINLAND = "chinese_mainland" # 中国大陆
    HONG_KONG = "hong_kong"              # 香港
    TAIWAN = "taiwan"                    # 台湾
    SINGAPORE = "singapore"              # 新加坡
    WESTERN = "western"                  # 西方文化
    JAPANESE = "japanese"                # 日本文化
    KOREAN = "korean"                    # 韩国文化
    SOUTHEAST_ASIAN = "southeast_asian"  # 东南亚文化


class AdaptationStrategy(Enum):
    """适配策略"""
    DIRECT_TRANSLATION = "direct_translation"     # 直接翻译
    CULTURAL_EQUIVALENT = "cultural_equivalent"   # 文化等价物
    EXPLANATION_ADDED = "explanation_added"       # 添加解释
    LOCALIZED_REPLACEMENT = "localized_replacement" # 本土化替换
    CONTEXTUAL_ADAPTATION = "contextual_adaptation" # 上下文适配
    OMIT_IF_UNCLEAR = "omit_if_unclear"          # 不清楚时省略


@dataclass
class CulturalTerm:
    """文化词汇条目"""
    term: str                                    # 原词汇
    category: CulturalCategory                   # 类别
    source_context: CulturalContext              # 源文化背景
    definition: str                              # 定义说明
    usage_examples: List[str]                    # 使用示例
    emotional_tone: str                          # 情感色彩 (positive/negative/neutral)
    formality_level: str                         # 正式程度 (formal/informal/slang)
    target_translations: Dict[str, Dict[str, Any]] = None # 目标语言翻译
    related_terms: List[str] = None              # 相关词汇
    cultural_notes: List[str] = None             # 文化注释
    frequency_score: float = 0.0                 # 使用频率评分
    last_updated: datetime = None                # 最后更新时间
    
    def __post_init__(self):
        if self.target_translations is None:
            self.target_translations = {}
        if self.related_terms is None:
            self.related_terms = []
        if self.cultural_notes is None:
            self.cultural_notes = []
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class LocalizationRequest:
    """本土化请求"""
    request_id: str
    source_text: str
    target_language: str
    target_culture: CulturalContext
    context_info: Optional[Dict[str, Any]] = None
    speaker_info: Optional[Dict[str, Any]] = None
    scene_context: Optional[str] = None
    formality_preference: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class LocalizationResult:
    """本土化结果"""
    request_id: str
    success: bool
    original_text: str
    localized_text: Optional[str] = None
    detected_terms: List[CulturalTerm] = None
    adaptations_applied: List[Dict[str, Any]] = None
    confidence_score: float = 0.0
    cultural_notes: List[str] = None
    alternative_translations: List[str] = None
    processing_time_ms: int = 0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.detected_terms is None:
            self.detected_terms = []
        if self.adaptations_applied is None:
            self.adaptations_applied = []
        if self.cultural_notes is None:
            self.cultural_notes = []
        if self.alternative_translations is None:
            self.alternative_translations = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CulturalLocalizationEngine:
    """文化本土化引擎
    
    主要功能：
    1. 识别文化特定词汇
    2. 提供多语言文化适配翻译
    3. 上下文相关的词汇选择
    4. 文化适配学习和更新
    """
    
    def __init__(self, engine_id: str = None):
        self.engine_id = engine_id or f"cultural_engine_{uuid.uuid4().hex[:8]}"
        
        # 文化词汇数据库
        self.cultural_terms_db: Dict[str, CulturalTerm] = {}
        
        # 初始化核心文化词汇
        self._initialize_core_cultural_terms()
        
        # 语言特定的文化适配规则
        self.language_adaptation_rules = {
            "en": {
                "prefer_explanation": True,
                "cultural_equivalent_priority": 0.8,
                "max_explanation_length": 50
            },
            "ja": {
                "prefer_cultural_equivalent": True,
                "honorific_adaptation": True,
                "cultural_equivalent_priority": 0.9
            },
            "ko": {
                "prefer_cultural_equivalent": True,
                "honorific_adaptation": True,
                "generational_sensitivity": True
            },
            "th": {
                "respect_hierarchy": True,
                "buddhist_context_aware": True,
                "cultural_equivalent_priority": 0.7
            },
            "vi": {
                "confucian_context_aware": True,
                "family_hierarchy_important": True,
                "cultural_equivalent_priority": 0.8
            },
            "id": {
                "islamic_context_aware": True,
                "respect_elders": True,
                "cultural_equivalent_priority": 0.7
            },
            "ms": {
                "islamic_context_aware": True,
                "multicultural_sensitivity": True,
                "cultural_equivalent_priority": 0.7
            },
            "fr": {
                "prefer_explanation": True,
                "formal_tone_preference": True,
                "cultural_equivalent_priority": 0.6
            },
            "de": {
                "direct_translation_preference": True,
                "precision_important": True,
                "cultural_equivalent_priority": 0.5
            },
            "es": {
                "family_oriented": True,
                "emotional_expression_important": True,
                "cultural_equivalent_priority": 0.8
            },
            "ru": {
                "literary_tradition_aware": True,
                "community_values_important": True,
                "cultural_equivalent_priority": 0.7
            }
        }
        
        # 性能统计
        self.performance_stats = {
            "total_localizations": 0,
            "successful_localizations": 0,
            "terms_detected": 0,
            "adaptations_applied": 0,
            "average_confidence": 0.0,
            "language_distribution": defaultdict(int),
            "category_distribution": defaultdict(int),
            "strategy_distribution": defaultdict(int)
        }
        
        logger.info("文化本土化引擎初始化完成", engine_id=self.engine_id)
    
    def _initialize_core_cultural_terms(self):
        """初始化核心文化词汇"""
        core_terms = [
            # 现代生活词汇
            CulturalTerm(
                term="鸡娃",
                category=CulturalCategory.FAMILY_EDUCATION,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指家长对孩子进行高强度教育投入，类似直升机父母",
                usage_examples=["她是个典型的鸡娃妈妈", "现在鸡娃现象很普遍"],
                emotional_tone="neutral",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "helicopter parenting",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "intensive parenting focused on children's achievement",
                        "alternatives": ["tiger parenting", "pushy parenting"]
                    },
                    "ja": {
                        "translation": "教育ママ",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "子供の教育に熱心すぎる親",
                        "alternatives": ["モンスターペアレント"]
                    },
                    "ko": {
                        "translation": "헬리콥터 부모",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "자녀 교육에 과도하게 개입하는 부모",
                        "alternatives": ["교육열 부모"]
                    }
                },
                cultural_notes=["反映中国家长对子女教育的焦虑", "与社会竞争压力相关"]
            ),
            
            CulturalTerm(
                term="内卷",
                category=CulturalCategory.SOCIAL_PHENOMENON,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指同行间竞争激烈，导致整体福利下降的现象",
                usage_examples=["这个行业内卷太严重了", "大家都在内卷"],
                emotional_tone="negative",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "rat race",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "intense competition that benefits no one",
                        "alternatives": ["cutthroat competition", "zero-sum competition"]
                    },
                    "ja": {
                        "translation": "過当競争",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "過度な競争による消耗",
                        "alternatives": ["レッドオーシャン"]
                    },
                    "ko": {
                        "translation": "과당경쟁",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "과도한 경쟁으로 인한 소모",
                        "alternatives": ["치킨게임"]
                    }
                },
                cultural_notes=["反映现代社会竞争压力", "源于学术概念的网络流行语"]
            ),
            
            CulturalTerm(
                term="躺平",
                category=CulturalCategory.SOCIAL_PHENOMENON,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指年轻人选择低欲望生活，不追求传统成功标准",
                usage_examples=["我决定躺平了", "躺平族越来越多"],
                emotional_tone="neutral",
                formality_level="slang",
                target_translations={
                    "en": {
                        "translation": "lying flat",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "choosing a minimalist lifestyle, rejecting societal pressure",
                        "alternatives": ["giving up", "opting out"]
                    },
                    "ja": {
                        "translation": "寝そべり族",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "競争社会から降りる若者",
                        "alternatives": ["ゆとり世代"]
                    },
                    "ko": {
                        "translation": "눕기족",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "경쟁을 포기하고 소박하게 사는 것",
                        "alternatives": ["포기세대"]
                    }
                },
                cultural_notes=["反映年轻人对社会压力的反抗", "与佛系文化相关"]
            ),
            
            CulturalTerm(
                term="996",
                category=CulturalCategory.WORK_CULTURE,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指早9点到晚9点，每周工作6天的工作制度",
                usage_examples=["这家公司是996工作制", "996太累了"],
                emotional_tone="negative",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "996 work schedule",
                        "strategy": AdaptationStrategy.EXPLANATION_ADDED.value,
                        "explanation": "9am-9pm, 6 days a week work schedule",
                        "alternatives": ["overtime culture", "long working hours"]
                    },
                    "ja": {
                        "translation": "996勤務",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "朝9時から夜9時まで週6日勤務",
                        "alternatives": ["長時間労働"]
                    },
                    "ko": {
                        "translation": "996 근무제",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "오전 9시부터 오후 9시까지 주 6일 근무",
                        "alternatives": ["장시간 근무"]
                    }
                },
                cultural_notes=["反映中国互联网行业工作强度", "引发社会讨论的热点话题"]
            ),
            
            CulturalTerm(
                term="打工人",
                category=CulturalCategory.WORK_CULTURE,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指普通上班族，带有自嘲和共鸣的意味",
                usage_examples=["打工人，打工魂", "我们都是打工人"],
                emotional_tone="neutral",
                formality_level="slang",
                target_translations={
                    "en": {
                        "translation": "working person",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "ordinary office worker (with self-deprecating humor)",
                        "alternatives": ["wage slave", "worker"]
                    },
                    "ja": {
                        "translation": "サラリーマン",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "普通の会社員",
                        "alternatives": ["働く人"]
                    },
                    "ko": {
                        "translation": "직장인",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "평범한 회사원",
                        "alternatives": ["샐러리맨"]
                    }
                },
                cultural_notes=["体现打工族的自我认同", "网络流行语转化为日常用语"]
            ),
            
            # 传统文化词汇
            CulturalTerm(
                term="孝顺",
                category=CulturalCategory.TRADITIONAL_CULTURE,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指对父母长辈的尊敬和照顾",
                usage_examples=["他很孝顺父母", "孝顺是传统美德"],
                emotional_tone="positive",
                formality_level="formal",
                target_translations={
                    "en": {
                        "translation": "filial piety",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "respect and care for parents and elders",
                        "alternatives": ["being dutiful to parents"]
                    },
                    "ja": {
                        "translation": "孝行",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "親孝行すること",
                        "alternatives": ["親思い"]
                    },
                    "ko": {
                        "translation": "효도",
                        "strategy": AdaptationStrategy.CULTURAL_EQUIVALENT.value,
                        "explanation": "부모님께 효성을 다하는 것",
                        "alternatives": ["효성"]
                    }
                },
                cultural_notes=["儒家文化核心价值", "东亚文化共同理念"]
            ),
            
            # 饮食文化
            CulturalTerm(
                term="火锅",
                category=CulturalCategory.FOOD_CULTURE,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="中式涮煮料理，多人围桌共享",
                usage_examples=["我们去吃火锅吧", "四川火锅很辣"],
                emotional_tone="positive",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "hot pot",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "Chinese communal cooking style with shared broth",
                        "alternatives": ["Chinese fondue"]
                    },
                    "ja": {
                        "translation": "火鍋",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "中華風の鍋料理",
                        "alternatives": ["中華鍋"]
                    },
                    "ko": {
                        "translation": "훠궈",
                        "strategy": AdaptationStrategy.DIRECT_TRANSLATION.value,
                        "explanation": "중국식 샤브샤브",
                        "alternatives": ["중국 전골"]
                    }
                },
                cultural_notes=["体现中国人聚餐文化", "社交性很强的饮食方式"]
            )
        ]
        
        # 将核心词汇添加到数据库
        for term in core_terms:
            self.cultural_terms_db[term.term] = term
        
        logger.info("核心文化词汇初始化完成", terms_count=len(core_terms))
    
    def localize_text(self, request: LocalizationRequest) -> LocalizationResult:
        """本土化文本"""
        start_time = datetime.now()
        
        try:
            # 检测文化词汇
            detected_terms = self._detect_cultural_terms(request.source_text)
            
            # 应用本土化适配
            localized_text, adaptations = self._apply_localization(
                request.source_text, detected_terms, request
            )
            
            # 计算置信度
            confidence_score = self._calculate_confidence(detected_terms, adaptations)
            
            # 生成文化注释
            cultural_notes = self._generate_cultural_notes(detected_terms, request.target_culture)
            
            # 生成替代翻译
            alternatives = self._generate_alternatives(detected_terms, request)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计信息
            self._update_performance_stats(request, detected_terms, adaptations, True)
            
            result = LocalizationResult(
                request_id=request.request_id,
                success=True,
                original_text=request.source_text,
                localized_text=localized_text,
                detected_terms=detected_terms,
                adaptations_applied=adaptations,
                confidence_score=confidence_score,
                cultural_notes=cultural_notes,
                alternative_translations=alternatives,
                processing_time_ms=int(processing_time),
                metadata={
                    "target_language": request.target_language,
                    "target_culture": request.target_culture.value,
                    "terms_detected_count": len(detected_terms),
                    "adaptations_count": len(adaptations)
                }
            )
            
            logger.debug("文本本土化完成",
                        request_id=request.request_id,
                        terms_detected=len(detected_terms),
                        confidence=confidence_score,
                        processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_stats(request, [], [], False)
            
            logger.error("文本本土化失败",
                        request_id=request.request_id,
                        error=str(e))
            
            return LocalizationResult(
                request_id=request.request_id,
                success=False,
                original_text=request.source_text,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def _detect_cultural_terms(self, text: str) -> List[CulturalTerm]:
        """检测文化词汇"""
        detected_terms = []
        
        # 直接匹配已知词汇
        for term_text, cultural_term in self.cultural_terms_db.items():
            if term_text in text:
                detected_terms.append(cultural_term)
        
        # 模式匹配检测
        pattern_matches = self._pattern_based_detection(text)
        detected_terms.extend(pattern_matches)
        
        # 去重并按出现顺序排序
        seen_terms = set()
        unique_terms = []
        for term in detected_terms:
            if term.term not in seen_terms:
                unique_terms.append(term)
                seen_terms.add(term.term)
        
        return unique_terms
    
    def _pattern_based_detection(self, text: str) -> List[CulturalTerm]:
        """基于模式的文化词汇检测"""
        pattern_terms = []
        
        # 检测网络流行语模式
        internet_slang_patterns = [
            (r'(\w+)人', CulturalCategory.INTERNET_SLANG),  # XX人
            (r'(\w+)族', CulturalCategory.SOCIAL_PHENOMENON),  # XX族
            (r'(\w+)系', CulturalCategory.MODERN_LIFE),  # XX系
        ]
        
        for pattern, category in internet_slang_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                full_term = match + ('人' if '人' in pattern else '族' if '族' in pattern else '系')
                if full_term not in self.cultural_terms_db:
                    # 创建临时文化词汇条目
                    temp_term = CulturalTerm(
                        term=full_term,
                        category=category,
                        source_context=CulturalContext.CHINESE_MAINLAND,
                        definition=f"网络流行语：{full_term}",
                        usage_examples=[f"文本中出现：{full_term}"],
                        emotional_tone="neutral",
                        formality_level="slang",
                        frequency_score=0.5
                    )
                    pattern_terms.append(temp_term)
        
        return pattern_terms
    
    def _apply_localization(self, text: str, detected_terms: List[CulturalTerm],
                          request: LocalizationRequest) -> Tuple[str, List[Dict[str, Any]]]:
        """应用本土化适配"""
        localized_text = text
        adaptations = []
        
        # 获取目标语言的适配规则
        lang_rules = self.language_adaptation_rules.get(
            request.target_language, 
            self.language_adaptation_rules.get("en", {})
        )
        
        for term in detected_terms:
            if request.target_language in term.target_translations:
                translation_info = term.target_translations[request.target_language]
                
                # 选择适配策略
                strategy = self._select_adaptation_strategy(
                    term, request, lang_rules, translation_info
                )
                
                # 应用适配
                adapted_text = self._apply_adaptation_strategy(
                    term.term, translation_info, strategy, request
                )
                
                # 替换文本
                localized_text = localized_text.replace(term.term, adapted_text)
                
                # 记录适配信息
                adaptation_info = {
                    "original_term": term.term,
                    "adapted_text": adapted_text,
                    "strategy": strategy.value,
                    "category": term.category.value,
                    "confidence": self._calculate_term_confidence(term, request)
                }
                adaptations.append(adaptation_info)
        
        return localized_text, adaptations
    
    def _select_adaptation_strategy(self, term: CulturalTerm, request: LocalizationRequest,
                                  lang_rules: Dict[str, Any], 
                                  translation_info: Dict[str, Any]) -> AdaptationStrategy:
        """选择适配策略"""
        # 获取推荐策略
        recommended_strategy = translation_info.get("strategy", AdaptationStrategy.DIRECT_TRANSLATION.value)
        
        # 根据语言规则调整
        if lang_rules.get("prefer_explanation", False) and term.category in [
            CulturalCategory.MODERN_LIFE, CulturalCategory.INTERNET_SLANG
        ]:
            return AdaptationStrategy.EXPLANATION_ADDED
        
        if lang_rules.get("prefer_cultural_equivalent", False) and "alternatives" in translation_info:
            return AdaptationStrategy.CULTURAL_EQUIVALENT
        
        # 根据上下文调整
        if request.context_info:
            formality = request.context_info.get("formality", "neutral")
            if formality == "formal" and term.formality_level == "slang":
                return AdaptationStrategy.LOCALIZED_REPLACEMENT
        
        # 返回推荐策略
        try:
            return AdaptationStrategy(recommended_strategy)
        except ValueError:
            return AdaptationStrategy.DIRECT_TRANSLATION
    
    def _apply_adaptation_strategy(self, original_term: str, translation_info: Dict[str, Any],
                                 strategy: AdaptationStrategy, request: LocalizationRequest) -> str:
        """应用适配策略"""
        base_translation = translation_info.get("translation", original_term)
        
        if strategy == AdaptationStrategy.DIRECT_TRANSLATION:
            return base_translation
        
        elif strategy == AdaptationStrategy.CULTURAL_EQUIVALENT:
            alternatives = translation_info.get("alternatives", [])
            if alternatives:
                return alternatives[0]  # 选择第一个替代词
            return base_translation
        
        elif strategy == AdaptationStrategy.EXPLANATION_ADDED:
            explanation = translation_info.get("explanation", "")
            if explanation:
                return f"{base_translation} ({explanation})"
            return base_translation
        
        elif strategy == AdaptationStrategy.LOCALIZED_REPLACEMENT:
            # 根据目标文化选择最合适的替换
            alternatives = translation_info.get("alternatives", [])
            if alternatives and len(alternatives) > 1:
                return alternatives[1]  # 选择第二个替代词作为本土化版本
            return base_translation
        
        elif strategy == AdaptationStrategy.CONTEXTUAL_ADAPTATION:
            # 根据上下文调整
            if request.context_info:
                scene_context = request.context_info.get("scene_context", "")
                if "formal" in scene_context.lower():
                    alternatives = translation_info.get("alternatives", [])
                    formal_alt = next((alt for alt in alternatives if "formal" in alt.lower()), None)
                    if formal_alt:
                        return formal_alt
            return base_translation
        
        else:
            return base_translation
    
    def _calculate_confidence(self, detected_terms: List[CulturalTerm], 
                            adaptations: List[Dict[str, Any]]) -> float:
        """计算置信度"""
        if not detected_terms:
            return 1.0
        
        total_confidence = 0.0
        for adaptation in adaptations:
            term_confidence = adaptation.get("confidence", 0.5)
            total_confidence += term_confidence
        
        return total_confidence / len(adaptations) if adaptations else 0.5
    
    def _calculate_term_confidence(self, term: CulturalTerm, request: LocalizationRequest) -> float:
        """计算单个词汇的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 根据词汇频率调整
        confidence += term.frequency_score * 0.3
        
        # 根据翻译质量调整
        if request.target_language in term.target_translations:
            translation_info = term.target_translations[request.target_language]
            if "explanation" in translation_info:
                confidence += 0.2
            if "alternatives" in translation_info and translation_info["alternatives"]:
                confidence += 0.1
        
        # 根据文化匹配度调整
        if self._is_culturally_compatible(term, request.target_culture):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _is_culturally_compatible(self, term: CulturalTerm, target_culture: CulturalContext) -> bool:
        """判断文化兼容性"""
        # 东亚文化圈的兼容性
        east_asian_cultures = {
            CulturalContext.CHINESE_MAINLAND, CulturalContext.HONG_KONG,
            CulturalContext.TAIWAN, CulturalContext.JAPANESE, CulturalContext.KOREAN
        }
        
        if term.source_context in east_asian_cultures and target_culture in east_asian_cultures:
            return True
        
        # 儒家文化概念的兼容性
        if term.category == CulturalCategory.TRADITIONAL_CULTURE:
            confucian_cultures = {
                CulturalContext.CHINESE_MAINLAND, CulturalContext.JAPANESE,
                CulturalContext.KOREAN, CulturalContext.SINGAPORE
            }
            if target_culture in confucian_cultures:
                return True
        
        return False
    
    def _generate_cultural_notes(self, detected_terms: List[CulturalTerm], 
                               target_culture: CulturalContext) -> List[str]:
        """生成文化注释"""
        notes = []
        
        for term in detected_terms:
            if term.cultural_notes:
                for note in term.cultural_notes:
                    cultural_note = f"{term.term}: {note}"
                    notes.append(cultural_note)
            
            # 添加跨文化理解注释
            if not self._is_culturally_compatible(term, target_culture):
                cross_cultural_note = f"{term.term}是中国特有的文化概念，可能需要额外解释"
                notes.append(cross_cultural_note)
        
        return notes
    
    def _generate_alternatives(self, detected_terms: List[CulturalTerm],
                             request: LocalizationRequest) -> List[str]:
        """生成替代翻译"""
        alternatives = []
        
        for term in detected_terms:
            if request.target_language in term.target_translations:
                translation_info = term.target_translations[request.target_language]
                term_alternatives = translation_info.get("alternatives", [])
                
                for alt in term_alternatives:
                    alt_text = request.source_text.replace(term.term, alt)
                    alternatives.append(alt_text)
        
        # 去重
        return list(set(alternatives))
    
    def _update_performance_stats(self, request: LocalizationRequest, 
                                detected_terms: List[CulturalTerm],
                                adaptations: List[Dict[str, Any]], success: bool):
        """更新性能统计"""
        self.performance_stats["total_localizations"] += 1
        
        if success:
            self.performance_stats["successful_localizations"] += 1
            self.performance_stats["terms_detected"] += len(detected_terms)
            self.performance_stats["adaptations_applied"] += len(adaptations)
            
            # 更新语言分布
            self.performance_stats["language_distribution"][request.target_language] += 1
            
            # 更新类别分布
            for term in detected_terms:
                self.performance_stats["category_distribution"][term.category.value] += 1
            
            # 更新策略分布
            for adaptation in adaptations:
                strategy = adaptation.get("strategy", "unknown")
                self.performance_stats["strategy_distribution"][strategy] += 1
    
    def add_cultural_term(self, term: CulturalTerm) -> bool:
        """添加文化词汇"""
        try:
            self.cultural_terms_db[term.term] = term
            logger.info("文化词汇已添加", term=term.term, category=term.category.value)
            return True
        except Exception as e:
            logger.error("添加文化词汇失败", term=term.term, error=str(e))
            return False
    
    def update_cultural_term(self, term_text: str, updates: Dict[str, Any]) -> bool:
        """更新文化词汇"""
        try:
            if term_text not in self.cultural_terms_db:
                return False
            
            term = self.cultural_terms_db[term_text]
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(term, field):
                    setattr(term, field, value)
            
            term.last_updated = datetime.now()
            
            logger.info("文化词汇已更新", term=term_text, updates=list(updates.keys()))
            return True
        except Exception as e:
            logger.error("更新文化词汇失败", term=term_text, error=str(e))
            return False
    
    def get_cultural_terms_by_category(self, category: CulturalCategory) -> List[CulturalTerm]:
        """按类别获取文化词汇"""
        return [term for term in self.cultural_terms_db.values() if term.category == category]
    
    def search_cultural_terms(self, query: str, limit: int = 10) -> List[CulturalTerm]:
        """搜索文化词汇"""
        results = []
        query_lower = query.lower()
        
        for term in self.cultural_terms_db.values():
            if (query_lower in term.term.lower() or 
                query_lower in term.definition.lower() or
                any(query_lower in example.lower() for example in term.usage_examples)):
                results.append(term)
        
        # 按频率评分排序
        results.sort(key=lambda x: x.frequency_score, reverse=True)
        
        return results[:limit]
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "engine_id": self.engine_id,
            "cultural_terms_count": len(self.cultural_terms_db),
            "supported_languages": list(self.language_adaptation_rules.keys()),
            "performance_stats": dict(self.performance_stats),
            "categories": [cat.value for cat in CulturalCategory],
            "cultural_contexts": [ctx.value for ctx in CulturalContext],
            "adaptation_strategies": [strategy.value for strategy in AdaptationStrategy]
        }
    
    def export_cultural_terms(self) -> Dict[str, Any]:
        """导出文化词汇数据"""
        exported_data = {
            "export_time": datetime.now().isoformat(),
            "terms_count": len(self.cultural_terms_db),
            "terms": {}
        }
        
        for term_text, term in self.cultural_terms_db.items():
            exported_data["terms"][term_text] = {
                "category": term.category.value,
                "source_context": term.source_context.value,
                "definition": term.definition,
                "usage_examples": term.usage_examples,
                "emotional_tone": term.emotional_tone,
                "formality_level": term.formality_level,
                "target_translations": term.target_translations,
                "related_terms": term.related_terms,
                "cultural_notes": term.cultural_notes,
                "frequency_score": term.frequency_score,
                "last_updated": term.last_updated.isoformat()
            }
        
        return exported_data
    
    def import_cultural_terms(self, data: Dict[str, Any]) -> bool:
        """导入文化词汇数据"""
        try:
            terms_data = data.get("terms", {})
            imported_count = 0
            
            for term_text, term_data in terms_data.items():
                cultural_term = CulturalTerm(
                    term=term_text,
                    category=CulturalCategory(term_data["category"]),
                    source_context=CulturalContext(term_data["source_context"]),
                    definition=term_data["definition"],
                    usage_examples=term_data["usage_examples"],
                    emotional_tone=term_data["emotional_tone"],
                    formality_level=term_data["formality_level"],
                    target_translations=term_data.get("target_translations", {}),
                    related_terms=term_data.get("related_terms", []),
                    cultural_notes=term_data.get("cultural_notes", []),
                    frequency_score=term_data.get("frequency_score", 0.0),
                    last_updated=datetime.fromisoformat(term_data["last_updated"])
                )
                
                self.cultural_terms_db[term_text] = cultural_term
                imported_count += 1
            
            logger.info("文化词汇导入完成", imported_count=imported_count)
            return True
            
        except Exception as e:
            logger.error("文化词汇导入失败", error=str(e))
            return False


# 全局文化本土化引擎实例
cultural_localization_engine = CulturalLocalizationEngine()


def get_cultural_localization_engine() -> CulturalLocalizationEngine:
    """获取文化本土化引擎实例"""
    return cultural_localization_engine


# 便捷函数
def localize_cultural_text(source_text: str, target_language: str, 
                          target_culture: CulturalContext,
                          context_info: Optional[Dict[str, Any]] = None) -> LocalizationResult:
    """便捷的文化本土化函数"""
    engine = get_cultural_localization_engine()
    
    request = LocalizationRequest(
        request_id=str(uuid.uuid4()),
        source_text=source_text,
        target_language=target_language,
        target_culture=target_culture,
        context_info=context_info
    )
    
    return engine.localize_text(request)


def detect_cultural_terms(text: str) -> List[CulturalTerm]:
    """便捷的文化词汇检测函数"""
    engine = get_cultural_localization_engine()
    return engine._detect_cultural_terms(text)