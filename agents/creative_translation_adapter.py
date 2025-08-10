"""
创作性翻译适配器
根据场景情感和人物性格调整翻译风格
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
from models.subtitle_models import SubtitleEntry, SceneEmotion
from models.story_models import StoryContext, CharacterRelation

logger = get_logger("creative_translation_adapter")


class EmotionalTone(Enum):
    """情感色调"""
    TENSE = "tense"                 # 紧张
    RELAXED = "relaxed"             # 轻松
    SAD = "sad"                     # 悲伤
    HAPPY = "happy"                 # 快乐
    ANGRY = "angry"                 # 愤怒
    ROMANTIC = "romantic"           # 浪漫
    MYSTERIOUS = "mysterious"       # 神秘
    DRAMATIC = "dramatic"           # 戏剧化
    HUMOROUS = "humorous"           # 幽默
    MELANCHOLIC = "melancholic"     # 忧郁


class TranslationStyle(Enum):
    """翻译风格"""
    FORMAL = "formal"               # 正式
    CASUAL = "casual"               # 随意
    POETIC = "poetic"               # 诗意
    COLLOQUIAL = "colloquial"       # 口语化
    LITERARY = "literary"           # 文学性
    DRAMATIC = "dramatic"           # 戏剧性
    MINIMALIST = "minimalist"       # 简约
    EXPRESSIVE = "expressive"       # 表现力强
    RHYTHMIC = "rhythmic"           # 有节奏感
    NATURAL = "natural"             # 自然


class CharacterArchetype(Enum):
    """人物原型"""
    HERO = "hero"                   # 英雄
    MENTOR = "mentor"               # 导师
    INNOCENT = "innocent"           # 天真者
    REBEL = "rebel"                 # 反叛者
    LOVER = "lover"                 # 恋人
    JESTER = "jester"               # 小丑
    SAGE = "sage"                   # 智者
    EXPLORER = "explorer"           # 探索者
    RULER = "ruler"                 # 统治者
    CAREGIVER = "caregiver"         # 照顾者
    CREATOR = "creator"             # 创造者
    EVERYMAN = "everyman"           # 普通人


class SceneContext(Enum):
    """场景上下文"""
    ACTION_SEQUENCE = "action_sequence"     # 动作场面
    DIALOGUE_SCENE = "dialogue_scene"       # 对话场景
    MONOLOGUE = "monologue"                 # 独白
    FLASHBACK = "flashback"                 # 回忆
    DREAM_SEQUENCE = "dream_sequence"       # 梦境
    CONFLICT_SCENE = "conflict_scene"       # 冲突场景
    RESOLUTION = "resolution"               # 解决
    EXPOSITION = "exposition"               # 说明
    CLIMAX = "climax"                       # 高潮
    DENOUEMENT = "denouement"               # 结局


@dataclass
class EmotionalAnalysis:
    """情感分析结果"""
    primary_emotion: EmotionalTone
    secondary_emotions: List[EmotionalTone]
    intensity: float  # 0.0-1.0
    emotional_arc: List[Tuple[float, EmotionalTone]]  # 时间点和情感的变化
    confidence: float
    detected_keywords: List[str]
    contextual_clues: List[str]


@dataclass
class CharacterProfile:
    """人物档案"""
    character_name: str
    archetype: CharacterArchetype
    personality_traits: List[str]
    speaking_style: TranslationStyle
    emotional_range: List[EmotionalTone]
    relationship_dynamics: Dict[str, str]  # 与其他角色的关系
    character_arc_stage: str  # 角色发展阶段
    signature_phrases: List[str]  # 标志性用语
    formality_preference: str  # 正式程度偏好


@dataclass
class StyleTemplate:
    """风格模板"""
    template_id: str
    name: str
    emotional_tone: EmotionalTone
    translation_style: TranslationStyle
    scene_context: SceneContext
    linguistic_features: Dict[str, Any]
    example_transformations: List[Dict[str, str]]
    target_languages: List[str]
    effectiveness_score: float = 0.0


@dataclass
class CreativeAdaptationRequest:
    """创作性适配请求"""
    request_id: str
    subtitle_entry: SubtitleEntry
    target_language: str
    scene_context: Optional[SceneContext] = None
    character_info: Optional[CharacterProfile] = None
    emotional_context: Optional[EmotionalAnalysis] = None
    style_preference: Optional[TranslationStyle] = None
    context_window: Optional[List[SubtitleEntry]] = None
    creative_freedom_level: float = 0.5  # 0.0-1.0, 创作自由度
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CreativeAdaptationResult:
    """创作性适配结果"""
    request_id: str
    success: bool
    original_text: str
    adapted_text: Optional[str] = None
    style_applied: Optional[TranslationStyle] = None
    emotional_tone_matched: Optional[EmotionalTone] = None
    character_voice_preserved: bool = False
    creativity_score: float = 0.0
    naturalness_score: float = 0.0
    emotional_impact_score: float = 0.0
    style_consistency_score: float = 0.0
    adaptations_made: List[str] = None
    alternative_versions: List[str] = None
    processing_time_ms: int = 0
    confidence: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.adaptations_made is None:
            self.adaptations_made = []
        if self.alternative_versions is None:
            self.alternative_versions = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

class CreativeTranslationAdapter:
    """创作性翻译适配器
    
    主要功能：
    1. 情感分析和场景识别
    2. 人物性格匹配和语音风格适配
    3. 创作性翻译风格模板应用
    4. 翻译质量和创作性评估
    """
    
    def __init__(self, adapter_id: str = None):
        self.adapter_id = adapter_id or f"creative_adapter_{uuid.uuid4().hex[:8]}"
        
        # 初始化风格模板
        self.style_templates: Dict[str, StyleTemplate] = {}
        self._initialize_style_templates()
        
        # 情感关键词库
        self.emotional_keywords = {
            EmotionalTone.TENSE: [
                "紧张", "焦虑", "担心", "害怕", "恐惧", "不安", "忐忑", "惊慌",
                "危险", "威胁", "急迫", "压力", "紧急", "警告", "小心"
            ],
            EmotionalTone.RELAXED: [
                "轻松", "舒适", "安心", "平静", "悠闲", "自在", "惬意", "放松",
                "没事", "别担心", "慢慢来", "不急", "随意", "简单", "容易"
            ],
            EmotionalTone.SAD: [
                "悲伤", "难过", "痛苦", "伤心", "失望", "绝望", "沮丧", "忧伤",
                "哭", "眼泪", "心痛", "遗憾", "可惜", "不幸", "悲剧"
            ],
            EmotionalTone.HAPPY: [
                "高兴", "开心", "快乐", "兴奋", "激动", "欣喜", "愉快", "满足",
                "笑", "微笑", "幸福", "美好", "棒", "太好了", "成功"
            ],
            EmotionalTone.ANGRY: [
                "愤怒", "生气", "恼火", "暴怒", "愤慨", "不满", "抗议", "反对",
                "混蛋", "该死", "可恶", "讨厌", "烦人", "受够了", "忍无可忍"
            ],
            EmotionalTone.ROMANTIC: [
                "爱", "喜欢", "心动", "浪漫", "甜蜜", "温柔", "亲爱的", "宝贝",
                "美丽", "迷人", "吸引", "心跳", "约会", "拥抱", "亲吻"
            ]
        }
        
        # 人物原型的语言特征
        self.archetype_language_features = {
            CharacterArchetype.HERO: {
                "tone": "confident",
                "vocabulary": "action-oriented",
                "sentence_structure": "direct",
                "emotional_range": [EmotionalTone.TENSE, EmotionalTone.DRAMATIC]
            },
            CharacterArchetype.MENTOR: {
                "tone": "wise",
                "vocabulary": "philosophical",
                "sentence_structure": "complex",
                "emotional_range": [EmotionalTone.RELAXED, EmotionalTone.MYSTERIOUS]
            },
            CharacterArchetype.LOVER: {
                "tone": "passionate",
                "vocabulary": "emotional",
                "sentence_structure": "flowing",
                "emotional_range": [EmotionalTone.ROMANTIC, EmotionalTone.HAPPY]
            }
        }
        
        # 语言特定的创作性规则
        self.language_creative_rules = {
            "en": {
                "rhythm_important": True,
                "metaphor_acceptance": 0.8,
                "emotional_amplification": 1.0
            },
            "ja": {
                "honorific_creativity": True,
                "metaphor_acceptance": 0.9,
                "emotional_amplification": 0.8
            },
            "ko": {
                "honorific_creativity": True,
                "metaphor_acceptance": 0.8,
                "emotional_amplification": 0.9
            }
        }
        
        # 性能统计
        self.performance_stats = {
            "total_adaptations": 0,
            "successful_adaptations": 0,
            "average_creativity_score": 0.0,
            "average_naturalness_score": 0.0,
            "emotional_tone_distribution": defaultdict(int),
            "style_distribution": defaultdict(int)
        }
        
        logger.info("创作性翻译适配器初始化完成", adapter_id=self.adapter_id)
    
    def _initialize_style_templates(self):
        """初始化风格模板"""
        templates = [
            # 紧张场景模板
            StyleTemplate(
                template_id="tense_action",
                name="紧张动作场景",
                emotional_tone=EmotionalTone.TENSE,
                translation_style=TranslationStyle.DRAMATIC,
                scene_context=SceneContext.ACTION_SEQUENCE,
                linguistic_features={
                    "sentence_length": "short",
                    "punctuation": "exclamatory",
                    "word_choice": "urgent",
                    "rhythm": "staccato"
                },
                example_transformations=[
                    {"original": "小心", "adapted": "Watch out!"},
                    {"original": "快跑", "adapted": "Run! Now!"}
                ],
                target_languages=["en", "ja", "ko"],
                effectiveness_score=0.85
            ),
            
            # 轻松场景模板
            StyleTemplate(
                template_id="relaxed_casual",
                name="轻松随意场景",
                emotional_tone=EmotionalTone.RELAXED,
                translation_style=TranslationStyle.CASUAL,
                scene_context=SceneContext.DIALOGUE_SCENE,
                linguistic_features={
                    "sentence_length": "medium",
                    "punctuation": "minimal",
                    "word_choice": "colloquial",
                    "rhythm": "flowing"
                },
                example_transformations=[
                    {"original": "没关系", "adapted": "No worries"},
                    {"original": "随便", "adapted": "Whatever works"}
                ],
                target_languages=["en", "ja", "ko"],
                effectiveness_score=0.80
            ),
            
            # 浪漫场景模板
            StyleTemplate(
                template_id="romantic_poetic",
                name="浪漫诗意场景",
                emotional_tone=EmotionalTone.ROMANTIC,
                translation_style=TranslationStyle.POETIC,
                scene_context=SceneContext.DIALOGUE_SCENE,
                linguistic_features={
                    "sentence_length": "varied",
                    "punctuation": "gentle",
                    "word_choice": "tender",
                    "rhythm": "melodic"
                },
                example_transformations=[
                    {"original": "我爱你", "adapted": "My heart belongs to you"},
                    {"original": "美丽", "adapted": "breathtaking"}
                ],
                target_languages=["en", "ja", "ko"],
                effectiveness_score=0.90
            )
        ]
        
        for template in templates:
            self.style_templates[template.template_id] = template
        
        logger.info("风格模板初始化完成", templates_count=len(templates))
    
    def adapt_translation(self, request: CreativeAdaptationRequest) -> CreativeAdaptationResult:
        """执行创作性翻译适配"""
        start_time = datetime.now()
        
        try:
            # 分析情感和场景
            if not request.emotional_context:
                emotional_analysis = self._analyze_emotion(request.subtitle_entry, request.context_window)
            else:
                emotional_analysis = request.emotional_context
            
            # 选择适配风格
            selected_style = self._select_adaptation_style(request, emotional_analysis)
            
            # 应用创作性适配
            adapted_text = self._apply_creative_adaptation(
                request.subtitle_entry.text, selected_style, request, emotional_analysis
            )
            
            # 评估适配质量
            quality_scores = self._evaluate_adaptation_quality(
                request.subtitle_entry.text, adapted_text, selected_style, emotional_analysis
            )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计信息
            self._update_performance_stats(request, selected_style, emotional_analysis, True)
            
            result = CreativeAdaptationResult(
                request_id=request.request_id,
                success=True,
                original_text=request.subtitle_entry.text,
                adapted_text=adapted_text,
                style_applied=selected_style.translation_style,
                emotional_tone_matched=emotional_analysis.primary_emotion,
                creativity_score=quality_scores["creativity"],
                naturalness_score=quality_scores["naturalness"],
                emotional_impact_score=quality_scores["emotional_impact"],
                style_consistency_score=quality_scores["consistency"],
                processing_time_ms=int(processing_time),
                confidence=quality_scores["overall"]
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_stats(request, None, None, False)
            
            logger.error("创作性翻译适配失败", request_id=request.request_id, error=str(e))
            
            return CreativeAdaptationResult(
                request_id=request.request_id,
                success=False,
                original_text=request.subtitle_entry.text,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )    

    def _analyze_emotion(self, subtitle_entry: SubtitleEntry, 
                        context_window: Optional[List[SubtitleEntry]] = None) -> EmotionalAnalysis:
        """分析情感"""
        text = subtitle_entry.text
        detected_emotions = []
        detected_keywords = []
        
        # 基于关键词的情感检测
        for emotion, keywords in self.emotional_keywords.items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                detected_emotions.append((emotion, len(matches)))
                detected_keywords.extend(matches)
        
        # 基于标点符号的情感强度分析
        intensity = self._analyze_emotional_intensity(text)
        
        # 确定主要情感
        if detected_emotions:
            detected_emotions.sort(key=lambda x: x[1], reverse=True)
            primary_emotion = detected_emotions[0][0]
            secondary_emotions = [e[0] for e in detected_emotions[1:3]]
        else:
            # 默认情感分析
            primary_emotion = self._infer_emotion_from_context(text, subtitle_entry)
            secondary_emotions = []
        
        # 分析上下文情感变化
        emotional_arc = self._analyze_emotional_arc(subtitle_entry, context_window)
        
        # 计算置信度
        confidence = self._calculate_emotion_confidence(detected_keywords, intensity, context_window)
        
        return EmotionalAnalysis(
            primary_emotion=primary_emotion,
            secondary_emotions=secondary_emotions,
            intensity=intensity,
            emotional_arc=emotional_arc,
            confidence=confidence,
            detected_keywords=detected_keywords,
            contextual_clues=self._extract_contextual_clues(text)
        )
    
    def _analyze_emotional_intensity(self, text: str) -> float:
        """分析情感强度"""
        intensity = 0.5  # 基础强度
        
        # 标点符号分析
        exclamation_count = text.count('!')
        question_count = text.count('?')
        ellipsis_count = text.count('...')
        
        intensity += exclamation_count * 0.2
        intensity += question_count * 0.1
        intensity += ellipsis_count * 0.15
        
        # 重复字符分析
        repeated_chars = len(re.findall(r'(.)\1{2,}', text))
        intensity += repeated_chars * 0.1
        
        return min(1.0, intensity)
    
    def _infer_emotion_from_context(self, text: str, subtitle_entry: SubtitleEntry) -> EmotionalTone:
        """从上下文推断情感"""
        # 基于场景情感
        if hasattr(subtitle_entry, 'scene_emotion'):
            scene_emotion_map = {
                SceneEmotion.HAPPY: EmotionalTone.HAPPY,
                SceneEmotion.SAD: EmotionalTone.SAD,
                SceneEmotion.ANGRY: EmotionalTone.ANGRY,
                SceneEmotion.TENSE: EmotionalTone.TENSE,
                SceneEmotion.ROMANTIC: EmotionalTone.ROMANTIC,
                SceneEmotion.NEUTRAL: EmotionalTone.RELAXED
            }
            return scene_emotion_map.get(subtitle_entry.scene_emotion, EmotionalTone.RELAXED)
        
        # 基于文本长度和结构推断
        if len(text) < 10 and ('!' in text or '?' in text):
            return EmotionalTone.TENSE
        elif len(text) > 50:
            return EmotionalTone.DRAMATIC
        else:
            return EmotionalTone.RELAXED
    
    def _analyze_emotional_arc(self, subtitle_entry: SubtitleEntry,
                             context_window: Optional[List[SubtitleEntry]] = None) -> List[Tuple[float, EmotionalTone]]:
        """分析情感弧线"""
        arc = []
        
        if context_window:
            for i, entry in enumerate(context_window):
                time_point = i / len(context_window)
                emotion = self._infer_emotion_from_context(entry.text, entry)
                arc.append((time_point, emotion))
        else:
            # 单个条目的情感弧线
            arc.append((0.0, self._infer_emotion_from_context(subtitle_entry.text, subtitle_entry)))
        
        return arc
    
    def _calculate_emotion_confidence(self, detected_keywords: List[str], 
                                    intensity: float,
                                    context_window: Optional[List[SubtitleEntry]] = None) -> float:
        """计算情感分析置信度"""
        confidence = 0.5  # 基础置信度
        
        # 关键词匹配置信度
        if detected_keywords:
            confidence += min(0.3, len(detected_keywords) * 0.1)
        
        # 强度置信度
        if intensity > 0.7:
            confidence += 0.2
        elif intensity < 0.3:
            confidence += 0.1
        
        # 上下文一致性置信度
        if context_window and len(context_window) > 1:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _extract_contextual_clues(self, text: str) -> List[str]:
        """提取上下文线索"""
        clues = []
        
        # 时间线索
        time_patterns = [r'现在', r'刚才', r'以前', r'将来', r'马上', r'立刻']
        for pattern in time_patterns:
            if re.search(pattern, text):
                clues.append(f"时间线索: {pattern}")
        
        # 地点线索
        location_patterns = [r'这里', r'那里', r'家里', r'外面', r'里面']
        for pattern in location_patterns:
            if re.search(pattern, text):
                clues.append(f"地点线索: {pattern}")
        
        return clues
    
    def _select_adaptation_style(self, request: CreativeAdaptationRequest,
                               emotional_analysis: EmotionalAnalysis) -> StyleTemplate:
        """选择适配风格"""
        # 如果指定了风格偏好，优先考虑
        if request.style_preference:
            matching_templates = [
                template for template in self.style_templates.values()
                if template.translation_style == request.style_preference
            ]
            if matching_templates:
                return max(matching_templates, key=lambda t: t.effectiveness_score)
        
        # 基于情感分析选择
        emotion_matching_templates = [
            template for template in self.style_templates.values()
            if template.emotional_tone == emotional_analysis.primary_emotion
        ]
        
        if emotion_matching_templates:
            return max(emotion_matching_templates, key=lambda t: t.effectiveness_score)
        
        # 默认选择最通用的模板
        return self.style_templates["relaxed_casual"]
    
    def _apply_creative_adaptation(self, original_text: str, style_template: StyleTemplate,
                                 request: CreativeAdaptationRequest,
                                 emotional_analysis: EmotionalAnalysis) -> str:
        """应用创作性适配"""
        adapted_text = original_text
        
        # 获取语言特定的创作规则
        lang_rules = self.language_creative_rules.get(
            request.target_language, 
            self.language_creative_rules.get("en", {})
        )
        
        # 应用风格模板的语言特征
        adapted_text = self._apply_linguistic_features(
            adapted_text, style_template.linguistic_features, lang_rules
        )
        
        # 应用情感强化
        if emotional_analysis.intensity > 0.7:
            adapted_text = self._amplify_emotional_expression(
                adapted_text, emotional_analysis, lang_rules
            )
        
        return adapted_text
    
    def _apply_linguistic_features(self, text: str, features: Dict[str, Any],
                                 lang_rules: Dict[str, Any]) -> str:
        """应用语言特征"""
        adapted_text = text
        
        # 句子长度调整
        if features.get("sentence_length") == "short":
            adapted_text = self._shorten_sentences(adapted_text)
        elif features.get("sentence_length") == "long":
            adapted_text = self._lengthen_sentences(adapted_text)
        
        # 标点符号调整
        if features.get("punctuation") == "exclamatory":
            adapted_text = self._add_exclamatory_punctuation(adapted_text)
        elif features.get("punctuation") == "gentle":
            adapted_text = self._soften_punctuation(adapted_text)
        
        # 词汇选择调整
        word_choice = features.get("word_choice")
        if word_choice:
            adapted_text = self._adjust_word_choice(adapted_text, word_choice, lang_rules)
        
        return adapted_text
    
    def _shorten_sentences(self, text: str) -> str:
        """缩短句子"""
        simplified = text
        
        # 移除一些常见的修饰语
        modifiers_to_remove = ["非常", "特别", "十分", "相当", "比较"]
        for modifier in modifiers_to_remove:
            simplified = simplified.replace(modifier, "")
        
        # 清理多余空格
        simplified = " ".join(simplified.split())
        
        return simplified
    
    def _lengthen_sentences(self, text: str) -> str:
        """延长句子"""
        enhanced = text
        
        # 在适当位置添加修饰语
        if "好" in enhanced and "很好" not in enhanced:
            enhanced = enhanced.replace("好", "很好")
        
        return enhanced
    
    def _add_exclamatory_punctuation(self, text: str) -> str:
        """添加感叹标点"""
        if not text.endswith(('!', '?', '。', '！', '？')):
            return text + "!"
        return text
    
    def _soften_punctuation(self, text: str) -> str:
        """软化标点符号"""
        softened = text.replace('!', '.')
        softened = softened.replace('！', '。')
        return softened
    
    def _adjust_word_choice(self, text: str, word_choice_style: str, lang_rules: Dict[str, Any]) -> str:
        """调整词汇选择"""
        adjusted = text
        
        if word_choice_style == "urgent":
            # 紧急词汇替换
            urgent_replacements = {
                "快": "赶快",
                "去": "赶紧去",
                "来": "快来"
            }
            for original, replacement in urgent_replacements.items():
                adjusted = adjusted.replace(original, replacement)
        
        elif word_choice_style == "tender":
            # 温柔词汇替换
            tender_replacements = {
                "好": "真好",
                "是": "就是"
            }
            for original, replacement in tender_replacements.items():
                adjusted = adjusted.replace(original, replacement)
        
        return adjusted
    
    def _amplify_emotional_expression(self, text: str, emotional_analysis: EmotionalAnalysis,
                                    lang_rules: Dict[str, Any]) -> str:
        """强化情感表达"""
        amplified = text
        
        if emotional_analysis.primary_emotion == EmotionalTone.HAPPY:
            # 强化快乐情感
            happy_amplifiers = {
                "好": "太好了",
                "开心": "非常开心"
            }
            for original, amplified_version in happy_amplifiers.items():
                if original in amplified:
                    amplified = amplified.replace(original, amplified_version)
        
        elif emotional_analysis.primary_emotion == EmotionalTone.TENSE:
            # 强化紧张情感
            tense_amplifiers = {
                "小心": "一定要小心",
                "危险": "非常危险"
            }
            for original, amplified_version in tense_amplifiers.items():
                if original in amplified:
                    amplified = amplified.replace(original, amplified_version)
        
        return amplified  
  
    def _evaluate_adaptation_quality(self, original_text: str, adapted_text: str,
                                   style_template: StyleTemplate,
                                   emotional_analysis: EmotionalAnalysis) -> Dict[str, float]:
        """评估适配质量"""
        scores = {}
        
        # 创作性评分
        scores["creativity"] = self._assess_creativity(original_text, adapted_text, style_template)
        
        # 自然性评分
        scores["naturalness"] = self._assess_naturalness(adapted_text)
        
        # 情感影响力评分
        scores["emotional_impact"] = self._assess_emotional_impact(adapted_text, emotional_analysis)
        
        # 风格一致性评分
        scores["consistency"] = self._assess_style_consistency(adapted_text, style_template)
        
        # 综合评分
        weights = {
            "creativity": 0.3,
            "naturalness": 0.3,
            "emotional_impact": 0.2,
            "consistency": 0.2
        }
        
        scores["overall"] = sum(scores[aspect] * weight for aspect, weight in weights.items())
        
        return scores
    
    def _assess_creativity(self, original_text: str, adapted_text: str,
                         style_template: StyleTemplate) -> float:
        """评估创作性"""
        if original_text == adapted_text:
            return 0.0
        
        creativity_score = 0.5  # 基础分
        
        # 文本变化程度
        change_ratio = 1 - (len(set(original_text) & set(adapted_text)) / len(set(original_text)))
        creativity_score += change_ratio * 0.3
        
        # 风格特征应用程度
        features_applied = len([f for f in style_template.linguistic_features.keys() 
                              if self._feature_applied(adapted_text, f)])
        max_features = len(style_template.linguistic_features)
        if max_features > 0:
            creativity_score += (features_applied / max_features) * 0.2
        
        return min(1.0, creativity_score)
    
    def _assess_naturalness(self, adapted_text: str) -> float:
        """评估自然性"""
        naturalness_score = 0.8  # 基础分
        
        # 检查是否有不自然的重复
        words = adapted_text.split()
        if len(words) != len(set(words)):
            naturalness_score -= 0.1
        
        # 检查句子长度合理性
        if len(adapted_text) > 100:  # 过长
            naturalness_score -= 0.2
        elif len(adapted_text) < 2:  # 过短
            naturalness_score -= 0.3
        
        return max(0.0, naturalness_score)
    
    def _assess_emotional_impact(self, adapted_text: str, emotional_analysis: EmotionalAnalysis) -> float:
        """评估情感影响力"""
        impact_score = 0.5
        
        # 检查情感关键词保留
        emotion_keywords = self.emotional_keywords.get(emotional_analysis.primary_emotion, [])
        preserved_keywords = [kw for kw in emotion_keywords if kw in adapted_text]
        
        if emotion_keywords:
            keyword_preservation = len(preserved_keywords) / len(emotion_keywords)
            impact_score += keyword_preservation * 0.3
        
        # 检查情感强度匹配
        adapted_intensity = self._analyze_emotional_intensity(adapted_text)
        intensity_match = 1 - abs(adapted_intensity - emotional_analysis.intensity)
        impact_score += intensity_match * 0.2
        
        return min(1.0, impact_score)
    
    def _assess_style_consistency(self, adapted_text: str, style_template: StyleTemplate) -> float:
        """评估风格一致性"""
        consistency_score = 0.7  # 基础分
        
        # 检查风格特征一致性
        features = style_template.linguistic_features
        
        if features.get("sentence_length") == "short" and len(adapted_text) > 50:
            consistency_score -= 0.2
        elif features.get("sentence_length") == "long" and len(adapted_text) < 20:
            consistency_score -= 0.2
        
        if features.get("punctuation") == "exclamatory" and "!" not in adapted_text:
            consistency_score -= 0.1
        
        return max(0.0, consistency_score)
    
    def _feature_applied(self, text: str, feature: str) -> bool:
        """检查特征是否已应用"""
        if feature == "punctuation" and ("!" in text or "?" in text):
            return True
        elif feature == "word_choice" and len(text) != len(text.replace("很", "")):
            return True
        return False
    
    def _update_performance_stats(self, request: CreativeAdaptationRequest,
                                style_template: Optional[StyleTemplate],
                                emotional_analysis: Optional[EmotionalAnalysis],
                                success: bool):
        """更新性能统计"""
        self.performance_stats["total_adaptations"] += 1
        
        if success:
            self.performance_stats["successful_adaptations"] += 1
            
            # 更新情感分布
            if emotional_analysis:
                emotion_name = emotional_analysis.primary_emotion.value
                self.performance_stats["emotional_tone_distribution"][emotion_name] += 1
            
            # 更新风格分布
            if style_template:
                style_name = style_template.translation_style.value
                self.performance_stats["style_distribution"][style_name] += 1
    
    def get_adapter_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        return {
            "adapter_id": self.adapter_id,
            "style_templates_count": len(self.style_templates),
            "supported_languages": list(self.language_creative_rules.keys()),
            "emotional_tones": [tone.value for tone in EmotionalTone],
            "translation_styles": [style.value for style in TranslationStyle],
            "character_archetypes": [archetype.value for archetype in CharacterArchetype],
            "scene_contexts": [context.value for context in SceneContext],
            "performance_stats": dict(self.performance_stats)
        }
    
    def add_style_template(self, template: StyleTemplate) -> bool:
        """添加风格模板"""
        try:
            self.style_templates[template.template_id] = template
            logger.info("风格模板已添加", template_id=template.template_id, name=template.name)
            return True
        except Exception as e:
            logger.error("添加风格模板失败", template_id=template.template_id, error=str(e))
            return False
    
    def get_style_templates_by_emotion(self, emotion: EmotionalTone) -> List[StyleTemplate]:
        """按情感获取风格模板"""
        return [template for template in self.style_templates.values() 
                if template.emotional_tone == emotion]
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_adaptations": 0,
            "successful_adaptations": 0,
            "average_creativity_score": 0.0,
            "average_naturalness_score": 0.0,
            "emotional_tone_distribution": defaultdict(int),
            "style_distribution": defaultdict(int)
        }
        logger.info("性能统计已重置")


# 全局创作性翻译适配器实例
creative_translation_adapter = CreativeTranslationAdapter()


def get_creative_translation_adapter() -> CreativeTranslationAdapter:
    """获取创作性翻译适配器实例"""
    return creative_translation_adapter


# 便捷函数
def adapt_creative_translation(subtitle_entry: SubtitleEntry, target_language: str,
                             emotional_tone: Optional[EmotionalTone] = None,
                             translation_style: Optional[TranslationStyle] = None,
                             creative_freedom_level: float = 0.5) -> CreativeAdaptationResult:
    """便捷的创作性翻译适配函数"""
    adapter = get_creative_translation_adapter()
    
    request = CreativeAdaptationRequest(
        request_id=str(uuid.uuid4()),
        subtitle_entry=subtitle_entry,
        target_language=target_language,
        style_preference=translation_style,
        creative_freedom_level=creative_freedom_level
    )
    
    return adapter.adapt_translation(request)


def analyze_subtitle_emotion(subtitle_entry: SubtitleEntry,
                           context_window: Optional[List[SubtitleEntry]] = None) -> EmotionalAnalysis:
    """便捷的字幕情感分析函数"""
    adapter = get_creative_translation_adapter()
    return adapter._analyze_emotion(subtitle_entry, context_window)