"""
创作性翻译适配器
根据场景情感和人物性格调整翻译风格
从agents/creative_translation_adapter.py迁移而来
"""
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from . import AdvancedModule, module_registry

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
    SUSPENSEFUL = "suspenseful"     # 悬疑
    INSPIRATIONAL = "inspirational" # 励志

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
    confidence: float
    detected_keywords: List[str]
    contextual_clues: List[str]

@dataclass
class StyleTemplate:
    """风格模板"""
    template_id: str
    name: str
    emotional_tone: EmotionalTone
    translation_style: TranslationStyle
    scene_context: SceneContext
    linguistic_features: Dict[str, Any]
    target_languages: List[str]
    effectiveness_score: float = 0.0

class CreativeTranslationAdapter(AdvancedModule):
    """创作性翻译适配器"""
    
    def __init__(self):
        super().__init__("creative_adapter", "1.0.0")
        self.style_templates = self._initialize_style_templates()
        self.emotional_keywords = self._initialize_emotional_keywords()
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理创作性翻译适配
        
        Args:
            input_data: {
                "entries": "翻译条目JSON字符串",
                "context": "故事上下文JSON字符串",
                "config": "风格配置JSON字符串"
            }
        
        Returns:
            增强后的翻译结果
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False, 
                error="Invalid input data for creative adaptation",
                processing_time=time.time() - start_time
            )
        
        try:
            # 解析输入数据
            entries = self.from_json(input_data["entries"])
            context = self.from_json(input_data["context"])
            config = self.from_json(input_data.get("config", "{}"))
            
            # 分析情感和场景
            emotional_analysis = self._analyze_emotions(entries, context)
            scene_context = self._detect_scene_context(entries, context)
            
            # 选择适配策略
            adaptation_strategy = self._select_adaptation_strategy(
                emotional_analysis, scene_context, config
            )
            
            # 应用创作性适配
            enhanced_entries = self._apply_creative_adaptation(
                entries, adaptation_strategy, config
            )
            
            processing_time = time.time() - start_time
            
            # 转换枚举为字符串以支持JSON序列化
            emotional_analysis_dict = asdict(emotional_analysis)
            emotional_analysis_dict["primary_emotion"] = emotional_analysis.primary_emotion.value
            emotional_analysis_dict["secondary_emotions"] = [e.value for e in emotional_analysis.secondary_emotions]
            
            return self.create_result(
                True,
                data={
                    "enhanced_entries": enhanced_entries,
                    "emotional_analysis": emotional_analysis_dict,
                    "scene_context": scene_context.value,
                    "adaptation_strategy": adaptation_strategy,
                    "enhancement_summary": {
                        "total_entries": len(entries),
                        "enhanced_entries": len(enhanced_entries),
                        "primary_emotion": emotional_analysis.primary_emotion.value,
                        "style_applied": adaptation_strategy.get("style", "casual")
                    }
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Creative adaptation failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["entries", "context"]
        return all(field in input_data for field in required_fields)
    
    def _analyze_emotions(self, entries: List[Dict], context: Dict) -> EmotionalAnalysis:
        """分析情感色调"""
        # 提取文本内容
        texts = [entry.get("original_text", "") for entry in entries]
        combined_text = " ".join(texts).lower()
        
        # 情感关键词检测
        detected_emotions = []
        detected_keywords = []
        
        for emotion, keywords in self.emotional_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    detected_emotions.append(emotion)
                    detected_keywords.append(keyword)
        
        # 确定主要情感
        if detected_emotions:
            primary_emotion = EmotionalTone(max(set(detected_emotions), key=detected_emotions.count))
        else:
            primary_emotion = EmotionalTone.RELAXED
        
        # 次要情感
        secondary_emotions = [EmotionalTone(e) for e in set(detected_emotions) if e != primary_emotion.value][:3]
        
        # 计算强度和置信度
        intensity = min(len(detected_keywords) / 10.0, 1.0)
        confidence = min(len(set(detected_keywords)) / 5.0, 1.0)
        
        return EmotionalAnalysis(
            primary_emotion=primary_emotion,
            secondary_emotions=secondary_emotions,
            intensity=intensity,
            confidence=confidence,
            detected_keywords=detected_keywords,
            contextual_clues=[]
        )
    
    def _detect_scene_context(self, entries: List[Dict], context: Dict) -> SceneContext:
        """检测场景上下文"""
        # 基于故事上下文和对话内容判断场景类型
        genre = context.get("genre", "").lower()
        
        # 简化的场景检测逻辑
        if "action" in genre or "军事" in str(context):
            return SceneContext.ACTION_SEQUENCE
        elif "romance" in genre or "爱情" in str(context):
            return SceneContext.DIALOGUE_SCENE
        elif "comedy" in genre or "喜剧" in str(context):
            return SceneContext.DIALOGUE_SCENE
        else:
            return SceneContext.DIALOGUE_SCENE
    
    def _select_adaptation_strategy(self, emotional_analysis: EmotionalAnalysis, 
                                  scene_context: SceneContext, config: Dict) -> Dict[str, Any]:
        """选择适配策略"""
        # 根据情感和场景选择翻译风格
        style_mapping = {
            EmotionalTone.ROMANTIC: TranslationStyle.POETIC,
            EmotionalTone.DRAMATIC: TranslationStyle.DRAMATIC,
            EmotionalTone.HUMOROUS: TranslationStyle.COLLOQUIAL,
            EmotionalTone.TENSE: TranslationStyle.MINIMALIST
        }
        
        selected_style = style_mapping.get(
            emotional_analysis.primary_emotion, 
            TranslationStyle.CASUAL
        )
        
        return {
            "style": selected_style.value,
            "emotional_tone": emotional_analysis.primary_emotion.value,
            "scene_context": scene_context.value,
            "intensity_level": emotional_analysis.intensity,
            "adaptation_features": self._get_adaptation_features(selected_style, emotional_analysis)
        }
    
    def _get_adaptation_features(self, style: TranslationStyle, emotional_analysis: EmotionalAnalysis) -> Dict[str, Any]:
        """获取适配特征"""
        features = {
            "enhance_emotional_words": emotional_analysis.intensity > 0.5,
            "use_rhythmic_patterns": style in [TranslationStyle.POETIC, TranslationStyle.RHYTHMIC],
            "prefer_shorter_sentences": style == TranslationStyle.MINIMALIST,
            "add_emotional_particles": emotional_analysis.primary_emotion in [EmotionalTone.ROMANTIC, EmotionalTone.SAD],
            "maintain_formality": style == TranslationStyle.FORMAL,
            "enhance_expressiveness": style == TranslationStyle.EXPRESSIVE
        }
        return features
    
    def _apply_creative_adaptation(self, entries: List[Dict], strategy: Dict[str, Any], config: Dict) -> List[Dict]:
        """应用创作性适配"""
        enhanced_entries = []
        
        for entry in entries:
            enhanced_entry = entry.copy()
            
            # 获取翻译文本
            translated_text = entry.get("translated_text", entry.get("original_text", ""))
            
            # 应用风格适配
            enhanced_text = self._enhance_text_style(translated_text, strategy)
            
            # 更新条目
            enhanced_entry["translated_text"] = enhanced_text
            enhanced_entry["creative_enhancement"] = {
                "style_applied": strategy["style"],
                "emotional_tone": strategy["emotional_tone"],
                "enhancement_score": 0.8  # 简化的评分
            }
            
            enhanced_entries.append(enhanced_entry)
        
        return enhanced_entries
    
    def _enhance_text_style(self, text: str, strategy: Dict[str, Any]) -> str:
        """增强文本风格"""
        # 这里是简化的风格增强逻辑
        # 在实际实现中，这里会有更复杂的文本处理算法
        
        enhanced_text = text
        features = strategy.get("adaptation_features", {})
        
        # 根据特征调整文本
        if features.get("prefer_shorter_sentences"):
            # 简化句子结构
            enhanced_text = enhanced_text.replace("，", "。").replace(",", ".")
        
        if features.get("enhance_emotional_words"):
            # 增强情感词汇（简化实现）
            emotional_replacements = {
                "好": "很好",
                "美": "很美",
                "sad": "deeply sad",
                "happy": "truly happy"
            }
            for original, enhanced in emotional_replacements.items():
                enhanced_text = enhanced_text.replace(original, enhanced)
        
        return enhanced_text
    
    def _initialize_style_templates(self) -> Dict[str, StyleTemplate]:
        """初始化风格模板"""
        templates = {}
        
        # 浪漫场景模板
        templates["romantic"] = StyleTemplate(
            template_id="romantic_v1",
            name="浪漫场景",
            emotional_tone=EmotionalTone.ROMANTIC,
            translation_style=TranslationStyle.POETIC,
            scene_context=SceneContext.DIALOGUE_SCENE,
            linguistic_features={
                "use_soft_expressions": True,
                "enhance_emotional_words": True,
                "prefer_longer_sentences": True
            },
            target_languages=["en", "ja", "ko", "es", "pt"]
        )
        
        # 紧张场景模板
        templates["tense"] = StyleTemplate(
            template_id="tense_v1",
            name="紧张场景",
            emotional_tone=EmotionalTone.TENSE,
            translation_style=TranslationStyle.MINIMALIST,
            scene_context=SceneContext.ACTION_SEQUENCE,
            linguistic_features={
                "use_short_sentences": True,
                "enhance_urgency": True,
                "minimize_particles": True
            },
            target_languages=["en", "ja", "ko", "th", "vi"]
        )
        
        return templates
    
    def _initialize_emotional_keywords(self) -> Dict[str, List[str]]:
        """初始化情感关键词"""
        return {
            "romantic": ["爱", "心", "情", "love", "heart", "dear", "darling"],
            "tense": ["快", "急", "危险", "quick", "urgent", "danger", "emergency"],
            "happy": ["高兴", "开心", "笑", "happy", "joy", "smile", "laugh"],
            "sad": ["伤心", "难过", "哭", "sad", "cry", "tears", "sorrow"],
            "angry": ["生气", "愤怒", "怒", "angry", "mad", "furious", "rage"],
            "dramatic": ["戏剧", "重要", "关键", "dramatic", "crucial", "critical"],
            "humorous": ["搞笑", "幽默", "笑话", "funny", "humor", "joke", "comedy"],
            "mysterious": ["神秘", "秘密", "奇怪", "mystery", "secret", "strange", "weird"]
        }

# 注册模块
creative_adapter = CreativeTranslationAdapter()
module_registry.register(creative_adapter)