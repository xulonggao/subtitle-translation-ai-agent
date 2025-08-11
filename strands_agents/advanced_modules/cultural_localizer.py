"""
文化本土化引擎
处理文化特定词汇的翻译和本土化适配
从agents/cultural_localization_agent.py迁移而来，符合需求2和需求3
"""
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

from . import AdvancedModule, module_registry

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
class LocalizationResult:
    """本土化结果"""
    original_text: str
    localized_text: str
    detected_terms: List[str]
    adaptations_applied: List[Dict[str, Any]]
    confidence_score: float
    cultural_notes: List[str]
    alternative_translations: List[str]

class CulturalLocalizer(AdvancedModule):
    """文化本土化引擎
    
    核心功能：
    1. 识别文化特定词汇 (符合需求2: 多语言翻译支持)
    2. 提供多语言文化适配翻译 (符合需求3: 人物关系和称谓处理)
    3. 上下文相关的词汇选择
    4. 文化适配学习和更新
    """
    
    def __init__(self):
        super().__init__("cultural_localizer", "1.0.0")
        
        # 文化词汇数据库
        self.cultural_terms_db: Dict[str, CulturalTerm] = {}
        
        # 语言特定的文化适配规则
        self.language_adaptation_rules = self._initialize_language_rules()
        
        # 初始化核心文化词汇
        self._initialize_core_cultural_terms()
        
        # 性能统计
        self.performance_stats = {
            "total_localizations": 0,
            "successful_localizations": 0,
            "terms_detected": 0,
            "adaptations_applied": 0,
            "average_confidence": 0.0
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文化本土化
        
        Args:
            input_data: {
                "text": "待处理文本",
                "target_language": "目标语言代码",
                "cultural_context": "文化背景配置JSON字符串"
            }
        
        Returns:
            本土化处理结果
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False,
                error="Invalid input data for cultural localization",
                processing_time=time.time() - start_time
            )
        
        try:
            text = input_data["text"]
            target_language = input_data["target_language"]
            cultural_context = self.from_json(input_data.get("cultural_context", "{}"))
            
            # 检测文化词汇
            detected_terms = self._detect_cultural_terms(text)
            
            # 应用本土化适配
            localized_text, adaptations = self._apply_localization(
                text, detected_terms, target_language, cultural_context
            )
            
            # 计算置信度
            confidence_score = self._calculate_confidence(detected_terms, adaptations)
            
            # 生成文化注释
            cultural_notes = self._generate_cultural_notes(detected_terms, target_language)
            
            # 生成替代翻译
            alternatives = self._generate_alternatives(detected_terms, target_language)
            
            # 更新统计信息
            self._update_stats(detected_terms, adaptations, confidence_score)
            
            processing_time = time.time() - start_time
            
            result = LocalizationResult(
                original_text=text,
                localized_text=localized_text,
                detected_terms=[term.term for term in detected_terms],
                adaptations_applied=adaptations,
                confidence_score=confidence_score,
                cultural_notes=cultural_notes,
                alternative_translations=alternatives
            )
            
            return self.create_result(
                True,
                data={
                    "localization_result": asdict(result),
                    "localization_summary": {
                        "terms_detected": len(detected_terms),
                        "adaptations_applied": len(adaptations),
                        "confidence_score": confidence_score,
                        "target_language": target_language
                    }
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Cultural localization failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["text", "target_language"]
        return all(field in input_data for field in required_fields)
    
    def _detect_cultural_terms(self, text: str) -> List[CulturalTerm]:
        """检测文化词汇"""
        detected_terms = []
        text_lower = text.lower()
        
        for term_key, cultural_term in self.cultural_terms_db.items():
            # 检查原词汇
            if cultural_term.term in text:
                detected_terms.append(cultural_term)
                continue
            
            # 检查相关词汇
            for related_term in cultural_term.related_terms:
                if related_term in text_lower:
                    detected_terms.append(cultural_term)
                    break
        
        return detected_terms
    
    def _apply_localization(self, text: str, detected_terms: List[CulturalTerm], 
                          target_language: str, cultural_context: Dict) -> Tuple[str, List[Dict]]:
        """应用本土化适配"""
        localized_text = text
        adaptations = []
        
        # 获取语言特定规则
        lang_rules = self.language_adaptation_rules.get(target_language, {})
        
        for term in detected_terms:
            if target_language in term.target_translations:
                translation_info = term.target_translations[target_language]
                
                # 选择适配策略
                strategy = AdaptationStrategy(translation_info.get("strategy", "direct_translation"))
                translation = translation_info.get("translation", term.term)
                
                # 应用翻译
                localized_text = localized_text.replace(term.term, translation)
                
                # 记录适配信息
                adaptations.append({
                    "original_term": term.term,
                    "translated_term": translation,
                    "strategy": strategy.value,
                    "category": term.category.value,
                    "explanation": translation_info.get("explanation", ""),
                    "confidence": translation_info.get("confidence", 0.8)
                })
        
        return localized_text, adaptations
    
    def _calculate_confidence(self, detected_terms: List[CulturalTerm], 
                            adaptations: List[Dict]) -> float:
        """计算置信度"""
        if not detected_terms:
            return 1.0
        
        total_confidence = 0.0
        for adaptation in adaptations:
            total_confidence += adaptation.get("confidence", 0.5)
        
        return total_confidence / len(adaptations) if adaptations else 0.0
    
    def _generate_cultural_notes(self, detected_terms: List[CulturalTerm], 
                               target_language: str) -> List[str]:
        """生成文化注释"""
        notes = []
        for term in detected_terms:
            if term.cultural_notes:
                notes.extend(term.cultural_notes)
        return notes[:3]  # 限制注释数量
    
    def _generate_alternatives(self, detected_terms: List[CulturalTerm], 
                             target_language: str) -> List[str]:
        """生成替代翻译"""
        alternatives = []
        for term in detected_terms:
            if target_language in term.target_translations:
                alt_list = term.target_translations[target_language].get("alternatives", [])
                alternatives.extend(alt_list)
        return alternatives[:5]  # 限制替代选项数量
    
    def _update_stats(self, detected_terms: List[CulturalTerm], 
                     adaptations: List[Dict], confidence: float):
        """更新统计信息"""
        self.performance_stats["total_localizations"] += 1
        if confidence > 0.5:
            self.performance_stats["successful_localizations"] += 1
        self.performance_stats["terms_detected"] += len(detected_terms)
        self.performance_stats["adaptations_applied"] += len(adaptations)
        
        # 更新平均置信度
        total = self.performance_stats["total_localizations"]
        current_avg = self.performance_stats["average_confidence"]
        self.performance_stats["average_confidence"] = (current_avg * (total - 1) + confidence) / total
    
    def _initialize_language_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化语言特定规则"""
        return {
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
            "es": {
                "family_oriented": True,
                "emotional_expression_important": True,
                "cultural_equivalent_priority": 0.8
            },
            "pt": {
                "family_oriented": True,
                "emotional_expression_important": True,
                "cultural_equivalent_priority": 0.8
            },
            "ar": {
                "islamic_context_aware": True,
                "respect_hierarchy": True,
                "cultural_equivalent_priority": 0.7
            }
        }
    
    def _initialize_core_cultural_terms(self):
        """初始化核心文化词汇 (符合需求2和需求3)"""
        core_terms = [
            # 现代网络词汇 - 符合需求2的文化适配要求
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
                        "strategy": "cultural_equivalent",
                        "explanation": "intensive parenting focused on children's achievement",
                        "alternatives": ["tiger parenting", "pushy parenting"],
                        "confidence": 0.9
                    },
                    "ja": {
                        "translation": "教育熱心",
                        "strategy": "cultural_equivalent",
                        "explanation": "子供の教育に熱心すぎる親",
                        "alternatives": ["教育ママ"],
                        "confidence": 0.8
                    },
                    "ko": {
                        "translation": "교육열",
                        "strategy": "cultural_equivalent",
                        "explanation": "자녀 교육에 과도하게 개입하는 부모",
                        "alternatives": ["헬리콥터 부모"],
                        "confidence": 0.9
                    },
                    "th": {
                        "translation": "การเลี้ยงดูแบบเข้มงวด",
                        "strategy": "explanation_added",
                        "explanation": "การให้ความสำคัญกับการศึกษาของลูกมากเกินไป",
                        "alternatives": ["พ่อแม่เฮลิคอปเตอร์"],
                        "confidence": 0.7
                    },
                    "vi": {
                        "translation": "nuôi dạy con quá mức",
                        "strategy": "explanation_added",
                        "explanation": "cha mẹ quá quan tâm đến việc học của con",
                        "alternatives": ["cha mẹ trực thăng"],
                        "confidence": 0.8
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
                        "strategy": "cultural_equivalent",
                        "explanation": "intense competition that benefits no one",
                        "alternatives": ["cutthroat competition", "zero-sum competition"],
                        "confidence": 0.8
                    },
                    "ja": {
                        "translation": "過当競争",
                        "strategy": "cultural_equivalent",
                        "explanation": "過度な競争による消耗",
                        "alternatives": ["レッドオーシャン"],
                        "confidence": 0.9
                    },
                    "ko": {
                        "translation": "과도한 경쟁",
                        "strategy": "cultural_equivalent",
                        "explanation": "과도한 경쟁으로 인한 소모",
                        "alternatives": ["치킨게임"],
                        "confidence": 0.9
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
                        "strategy": "direct_translation",
                        "explanation": "choosing a minimalist lifestyle, rejecting societal pressure",
                        "alternatives": ["giving up", "opting out"],
                        "confidence": 0.7
                    },
                    "ja": {
                        "translation": "諦め主義",
                        "strategy": "cultural_equivalent",
                        "explanation": "競争社会から降りる若者",
                        "alternatives": ["寝そべり族"],
                        "confidence": 0.8
                    },
                    "ko": {
                        "translation": "포기주의",
                        "strategy": "cultural_equivalent",
                        "explanation": "경쟁을 포기하고 소박하게 사는 것",
                        "alternatives": ["눕기족"],
                        "confidence": 0.8
                    }
                },
                cultural_notes=["反映年轻人对社会压力的反抗", "与佛系文化相关"]
            ),
            
            # 人际关系词汇 - 符合需求3的人物关系和称谓处理
            CulturalTerm(
                term="面子",
                category=CulturalCategory.RELATIONSHIP,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指个人的尊严、声誉和社会地位",
                usage_examples=["给他留点面子", "这样很没面子"],
                emotional_tone="neutral",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "face",
                        "strategy": "cultural_equivalent",
                        "explanation": "dignity, reputation, social standing",
                        "alternatives": ["reputation", "dignity"],
                        "confidence": 0.9
                    },
                    "ja": {
                        "translation": "面子",
                        "strategy": "direct_translation",
                        "explanation": "尊厳や社会的地位",
                        "alternatives": ["メンツ", "体面"],
                        "confidence": 0.9
                    },
                    "ko": {
                        "translation": "체면",
                        "strategy": "cultural_equivalent",
                        "explanation": "개인의 존엄성과 사회적 지위",
                        "alternatives": ["면자"],
                        "confidence": 0.9
                    }
                },
                cultural_notes=["东亚文化中重要的社会概念", "影响人际交往和决策"]
            ),
            
            CulturalTerm(
                term="关系",
                category=CulturalCategory.RELATIONSHIP,
                source_context=CulturalContext.CHINESE_MAINLAND,
                definition="指人际网络和社会连接，在中国文化中具有特殊意义",
                usage_examples=["他有关系", "靠关系办事"],
                emotional_tone="neutral",
                formality_level="informal",
                target_translations={
                    "en": {
                        "translation": "connections",
                        "strategy": "cultural_equivalent",
                        "explanation": "personal networks and social relationships",
                        "alternatives": ["networking", "relationships"],
                        "confidence": 0.8
                    },
                    "ja": {
                        "translation": "人脈",
                        "strategy": "cultural_equivalent",
                        "explanation": "人間関係のネットワーク",
                        "alternatives": ["コネ"],
                        "confidence": 0.9
                    },
                    "ko": {
                        "translation": "인맥",
                        "strategy": "cultural_equivalent",
                        "explanation": "인간관계 네트워크",
                        "alternatives": ["관계"],
                        "confidence": 0.9
                    }
                },
                cultural_notes=["中国社会中重要的社交概念", "影响商业和社会活动"]
            )
        ]
        
        # 将词汇添加到数据库
        for term in core_terms:
            self.cultural_terms_db[term.term] = term
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def add_cultural_term(self, term: CulturalTerm):
        """添加新的文化词汇"""
        self.cultural_terms_db[term.term] = term
    
    def get_cultural_term(self, term: str) -> Optional[CulturalTerm]:
        """获取文化词汇"""
        return self.cultural_terms_db.get(term)

# 注册模块
cultural_localizer = CulturalLocalizer()
module_registry.register(cultural_localizer)