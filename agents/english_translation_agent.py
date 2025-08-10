"""
英语翻译 Agent
专门处理中英翻译，优化军事、现代剧等术语翻译
"""
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationTask
from models.story_models import StoryContext, CharacterRelation
from agents.context_agent import get_context_agent, ContextQuery
from agents.dynamic_knowledge_manager import get_dynamic_knowledge_manager, KnowledgeQuery

logger = get_logger("english_translation_agent")


class TranslationStyle(Enum):
    """翻译风格"""
    FORMAL = "formal"           # 正式
    CASUAL = "casual"           # 随意
    MILITARY = "military"       # 军事
    ROMANTIC = "romantic"       # 浪漫
    DRAMATIC = "dramatic"       # 戏剧化
    TECHNICAL = "technical"     # 技术性


class TranslationQuality(Enum):
    """翻译质量等级"""
    EXCELLENT = "excellent"     # 优秀 (0.9-1.0)
    GOOD = "good"              # 良好 (0.7-0.89)
    ACCEPTABLE = "acceptable"   # 可接受 (0.5-0.69)
    POOR = "poor"              # 较差 (0.3-0.49)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (0.0-0.29)


@dataclass
class TranslationRequest:
    """翻译请求"""
    request_id: str
    project_id: str
    subtitle_entry: SubtitleEntry
    target_language: str = "en"
    style_preference: Optional[TranslationStyle] = None
    context_window: Optional[List[SubtitleEntry]] = None
    cultural_adaptation: bool = True
    preserve_timing: bool = True
    max_length: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TranslationResult:
    """翻译结果"""
    request_id: str
    success: bool
    translated_text: Optional[str] = None
    original_text: Optional[str] = None
    quality_score: float = 0.0
    quality_level: Optional[TranslationQuality] = None
    style_applied: Optional[TranslationStyle] = None
    cultural_adaptations: Optional[List[str]] = None
    terminology_used: Optional[Dict[str, str]] = None
    timing_preserved: bool = True
    character_count: int = 0
    processing_time_ms: int = 0
    confidence: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        if self.translated_text:
            self.character_count = len(self.translated_text)
        
        # 根据质量分数确定质量等级
        if self.quality_score >= 0.9:
            self.quality_level = TranslationQuality.EXCELLENT
        elif self.quality_score >= 0.7:
            self.quality_level = TranslationQuality.GOOD
        elif self.quality_score >= 0.5:
            self.quality_level = TranslationQuality.ACCEPTABLE
        elif self.quality_score >= 0.3:
            self.quality_level = TranslationQuality.POOR
        else:
            self.quality_level = TranslationQuality.UNACCEPTABLE


class EnglishTranslationAgent:
    """英语翻译 Agent
    
    主要功能：
    1. 专门的中英翻译处理
    2. 军事、现代剧等术语优化
    3. 英语文化适配和本土化
    4. 翻译质量评估和优化
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"english_agent_{uuid.uuid4().hex[:8]}"
        
        # 集成其他组件
        self.context_agent = get_context_agent()
        self.dynamic_kb = get_dynamic_knowledge_manager()
        
        # 翻译配置
        self.translation_config = {
            "max_length_ratio": 1.3,  # 英文通常比中文长30%
            "preserve_punctuation": True,
            "adapt_cultural_references": True,
            "maintain_formality": True,
            "optimize_readability": True
        }
        
        # 英语特定的系统提示模板
        self.system_prompts = {
            TranslationStyle.FORMAL: """
You are a professional English translator specializing in formal Chinese-to-English translation.
Focus on:
- Maintaining formal tone and proper grammar
- Using appropriate business/official terminology
- Preserving the original meaning precisely
- Ensuring natural English flow
""",
            TranslationStyle.MILITARY: """
You are a military English translator specializing in Chinese military drama translation.
Focus on:
- Using accurate military terminology and ranks
- Maintaining command structure respect levels
- Preserving military protocol language
- Ensuring authenticity in military contexts
""",
            TranslationStyle.CASUAL: """
You are an English translator specializing in casual, conversational Chinese-to-English translation.
Focus on:
- Using natural, everyday English expressions
- Maintaining conversational flow
- Adapting colloquialisms appropriately
- Ensuring relatability for English speakers
""",
            TranslationStyle.ROMANTIC: """
You are an English translator specializing in romantic Chinese drama translation.
Focus on:
- Capturing emotional nuances and romantic expressions
- Using appropriate intimate language levels
- Maintaining romantic atmosphere
- Ensuring emotional authenticity
""",
            TranslationStyle.DRAMATIC: """
You are an English translator specializing in dramatic Chinese content translation.
Focus on:
- Enhancing dramatic impact and emotional intensity
- Using powerful, expressive language
- Maintaining tension and atmosphere
- Ensuring dramatic authenticity
"""
        }
        
        # 术语映射表
        self.terminology_mappings = {
            # 军事术语
            "参谋长": "Chief of Staff",
            "司令": "Commander",
            "队长": "Captain",
            "中队长": "Squadron Leader",
            "班长": "Squad Leader",
            "战友": "comrade",
            "同志": "comrade",
            "长官": "sir/officer",
            "报告": "reporting",
            "是": "yes sir",
            "收到": "roger/copy that",
            "执行": "execute",
            "任务": "mission",
            "作战": "combat operation",
            "训练": "training",
            "演习": "exercise",
            "部队": "troops/unit",
            
            # 现代生活术语
            "鸡娃": "helicopter parenting",
            "内卷": "rat race/intense competition",
            "躺平": "lying flat/giving up",
            "996": "996 work schedule",
            "打工人": "office worker",
            "社畜": "corporate slave",
            "佛系": "zen-like/laid-back",
            "凡尔赛": "humble bragging",
            
            # 关系称谓
            "哥": "bro/brother",
            "姐": "sis/sister", 
            "老板": "boss",
            "同事": "colleague",
            "朋友": "friend",
            "闺蜜": "bestie/best friend",
            "男朋友": "boyfriend",
            "女朋友": "girlfriend",
            "老公": "husband/hubby",
            "老婆": "wife/honey"
        }
        
        # 文化适配规则
        self.cultural_adaptations = {
            "chinese_names": "preserve_with_explanation",
            "cultural_concepts": "adapt_with_context",
            "food_references": "translate_with_description",
            "historical_references": "explain_if_necessary",
            "idioms": "find_english_equivalent_or_explain"
        }
        
        # 性能统计
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "style_distribution": {},
            "error_count": 0
        }
        
        logger.info("英语翻译 Agent 初始化完成", agent_id=self.agent_id)
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        """执行翻译"""
        start_time = datetime.now()
        
        try:
            # 验证请求
            if not self._validate_request(request):
                return TranslationResult(
                    request_id=request.request_id,
                    success=False,
                    error_message="翻译请求验证失败"
                )
            
            # 分析上下文
            context_info = self._analyze_context(request)
            
            # 确定翻译风格
            style = self._determine_translation_style(request, context_info)
            
            # 获取术语映射
            terminology = self._get_terminology_mappings(request, context_info)
            
            # 执行翻译
            translated_text = self._perform_translation(request, style, terminology, context_info)
            
            # 应用文化适配
            adapted_text = self._apply_cultural_adaptations(translated_text, request, context_info)
            
            # 优化时长和可读性
            optimized_text = self._optimize_for_subtitles(adapted_text, request)
            
            # 质量评估
            quality_score, quality_details = self._assess_translation_quality(
                request.subtitle_entry.text, optimized_text, request
            )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计信息
            self._update_performance_stats(style, quality_score, processing_time, True)
            
            result = TranslationResult(
                request_id=request.request_id,
                success=True,
                translated_text=optimized_text,
                original_text=request.subtitle_entry.text,
                quality_score=quality_score,
                style_applied=style,
                cultural_adaptations=context_info.get("cultural_adaptations", []),
                terminology_used=terminology,
                timing_preserved=self._check_timing_preservation(request, optimized_text),
                processing_time_ms=int(processing_time),
                confidence=quality_score,
                metadata=quality_details
            )
            
            logger.debug("翻译完成", 
                        request_id=request.request_id,
                        quality_score=quality_score,
                        style=style.value,
                        processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_stats(None, 0.0, processing_time, False)
            
            logger.error("翻译失败", 
                        request_id=request.request_id,
                        error=str(e))
            
            return TranslationResult(
                request_id=request.request_id,
                success=False,
                original_text=request.subtitle_entry.text,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def _validate_request(self, request: TranslationRequest) -> bool:
        """验证翻译请求"""
        if not request.subtitle_entry or not request.subtitle_entry.text:
            return False
        
        if not request.project_id:
            return False
        
        if request.target_language != "en":
            return False
        
        return True
    
    def _analyze_context(self, request: TranslationRequest) -> Dict[str, Any]:
        """分析翻译上下文"""
        context_info = {}
        
        try:
            # 获取说话人信息
            speaker_query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=request.project_id,
                query_type="speaker_inference",
                subtitle_entry=request.subtitle_entry,
                dialogue_history=request.context_window or []
            )
            
            speaker_response = self.context_agent.process_query(speaker_query)
            if speaker_response.success:
                context_info["speaker_info"] = speaker_response.result
            
            # 获取人物关系分析
            relationship_query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=request.project_id,
                query_type="relationship_analysis",
                subtitle_entry=request.subtitle_entry,
                dialogue_history=request.context_window or []
            )
            
            relationship_response = self.context_agent.process_query(relationship_query)
            if relationship_response.success:
                context_info["relationship_info"] = relationship_response.result
            
            # 获取文化适配信息
            cultural_query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=request.project_id,
                query_type="cultural_adaptation",
                subtitle_entry=request.subtitle_entry,
                target_language="en"
            )
            
            cultural_response = self.context_agent.process_query(cultural_query)
            if cultural_response.success:
                context_info["cultural_info"] = cultural_response.result
            
        except Exception as e:
            logger.warning("上下文分析失败", error=str(e))
        
        return context_info
    
    def _determine_translation_style(self, request: TranslationRequest, 
                                   context_info: Dict[str, Any]) -> TranslationStyle:
        """确定翻译风格"""
        # 如果请求中指定了风格，优先使用
        if request.style_preference:
            return request.style_preference
        
        # 基于上下文信息推断风格
        speaker_info = context_info.get("speaker_info", {})
        relationship_info = context_info.get("relationship_info", {})
        cultural_info = context_info.get("cultural_info", {})
        
        # 检查是否是军事背景
        if self._is_military_context(speaker_info, cultural_info):
            return TranslationStyle.MILITARY
        
        # 检查正式程度
        formality = relationship_info.get("relationship_summary", {}).get("formality", "medium")
        if formality in ["very_high", "high"]:
            return TranslationStyle.FORMAL
        elif formality == "low":
            return TranslationStyle.CASUAL
        
        # 检查是否是浪漫场景
        if self._is_romantic_context(relationship_info, request.subtitle_entry.text):
            return TranslationStyle.ROMANTIC
        
        # 检查是否是戏剧化场景
        if self._is_dramatic_context(request.subtitle_entry.text):
            return TranslationStyle.DRAMATIC
        
        # 默认使用随意风格
        return TranslationStyle.CASUAL
    
    def _is_military_context(self, speaker_info: Dict[str, Any], 
                           cultural_info: Dict[str, Any]) -> bool:
        """判断是否是军事背景"""
        # 检查说话人职业
        speaker_data = speaker_info.get("speaker_info", {})
        if speaker_data.get("profession") in ["军官", "士兵", "参谋", "司令"]:
            return True
        
        # 检查文化背景
        cultural_notes = cultural_info.get("cultural_context", {}).get("cultural_notes", [])
        if "军事题材" in cultural_notes:
            return True
        
        return False
    
    def _is_romantic_context(self, relationship_info: Dict[str, Any], text: str) -> bool:
        """判断是否是浪漫场景"""
        relationship_data = relationship_info.get("relationship_summary", {})
        if relationship_data.get("relationship_type") in ["romantic", "intimate"]:
            return True
        
        # 检查文本中的浪漫关键词
        romantic_keywords = ["爱", "喜欢", "想你", "亲爱的", "宝贝", "心", "感情"]
        if any(keyword in text for keyword in romantic_keywords):
            return True
        
        return False
    
    def _is_dramatic_context(self, text: str) -> bool:
        """判断是否是戏剧化场景"""
        dramatic_keywords = ["！！", "什么", "不可能", "天哪", "怎么会", "太", "非常"]
        dramatic_punctuation = text.count("！") + text.count("？")
        
        return (any(keyword in text for keyword in dramatic_keywords) or 
                dramatic_punctuation >= 2)
    
    def _get_terminology_mappings(self, request: TranslationRequest, 
                                context_info: Dict[str, Any]) -> Dict[str, str]:
        """获取术语映射"""
        terminology = {}
        
        # 基础术语映射
        for chinese, english in self.terminology_mappings.items():
            if chinese in request.subtitle_entry.text:
                terminology[chinese] = english
        
        # 从知识库获取项目特定术语
        try:
            kb_query = KnowledgeQuery(
                query_type="terminology",
                source_text=request.subtitle_entry.text,
                target_language="en",
                project_id=request.project_id
            )
            
            kb_result = self.dynamic_kb.query_knowledge(kb_query)
            if kb_result.success and kb_result.results:
                for term_mapping in kb_result.results:
                    if isinstance(term_mapping, dict):
                        terminology.update(term_mapping)
        
        except Exception as e:
            logger.warning("术语查询失败", error=str(e))
        
        return terminology
    
    def _perform_translation(self, request: TranslationRequest, 
                           style: TranslationStyle,
                           terminology: Dict[str, str],
                           context_info: Dict[str, Any]) -> str:
        """执行核心翻译"""
        text = request.subtitle_entry.text
        
        # 应用术语替换
        for chinese_term, english_term in terminology.items():
            text = text.replace(chinese_term, f"[{english_term}]")
        
        # 构建翻译提示
        system_prompt = self.system_prompts.get(style, self.system_prompts[TranslationStyle.CASUAL])
        
        # 添加上下文信息到提示中
        context_prompt = self._build_context_prompt(context_info)
        
        # 构建完整的翻译提示
        full_prompt = f"""
{system_prompt}

Context Information:
{context_prompt}

Terminology to use:
{json.dumps(terminology, ensure_ascii=False, indent=2)}

Please translate the following Chinese text to English:
"{text}"

Requirements:
- Maintain the original meaning and tone
- Use the provided terminology consistently
- Keep the translation natural and fluent
- Preserve emotional nuances
- Ensure subtitle-appropriate length
"""
        
        # 这里应该调用实际的翻译模型（如Claude）
        # 为了演示，我们提供一个简化的翻译逻辑
        translated_text = self._simulate_translation(text, style, terminology)
        
        # 清理术语标记
        for chinese_term, english_term in terminology.items():
            translated_text = translated_text.replace(f"[{english_term}]", english_term)
        
        return translated_text
    
    def _simulate_translation(self, text: str, style: TranslationStyle, 
                            terminology: Dict[str, str]) -> str:
        """模拟翻译（实际实现中应该调用真实的翻译模型）"""
        # 这是一个简化的翻译模拟，实际实现中应该调用Claude等模型
        
        # 基本的词汇替换
        basic_mappings = {
            "你好": "Hello",
            "嗨": "Hi",
            "谢谢": "Thank you",
            "对不起": "Sorry",
            "是的": "Yes",
            "不是": "No",
            "我": "I",
            "你": "you",
            "他": "he",
            "她": "she",
            "我们": "we",
            "他们": "they",
            "什么": "what",
            "怎么": "how",
            "为什么": "why",
            "哪里": "where",
            "什么时候": "when",
            "很": "very",
            "非常": "very",
            "太": "too",
            "真的": "really",
            "可能": "maybe",
            "应该": "should",
            "必须": "must",
            "可以": "can",
            "会": "will",
            "要": "want to",
            "喜欢": "like",
            "爱": "love",
            "讨厌": "hate",
            "高兴": "happy",
            "难过": "sad",
            "生气": "angry",
            "担心": "worried",
            "害怕": "afraid",
            "好": "good",
            "坏": "bad",
            "大": "big",
            "小": "small",
            "多": "many",
            "少": "few",
            "快": "fast",
            "慢": "slow",
            "新": "new",
            "旧": "old",
            "朋友": "friend"
        }
        
        # 应用基本映射
        result = text
        for chinese, english in basic_mappings.items():
            result = result.replace(chinese, english)
        
        # 应用术语映射
        for chinese, english in terminology.items():
            result = result.replace(chinese, english)
        
        # 根据风格调整
        if style == TranslationStyle.FORMAL:
            result = result.replace("you", "you")  # 保持正式
        elif style == TranslationStyle.MILITARY:
            result = result.replace("Yes", "Yes, sir")
        elif style == TranslationStyle.CASUAL:
            result = result.replace("Hello", "Hi")
        
        # 如果没有找到合适的翻译，返回原文加上标记
        if result == text:
            result = f"[Translation needed: {text}]"
        
        return result
    
    def _build_context_prompt(self, context_info: Dict[str, Any]) -> str:
        """构建上下文提示"""
        context_parts = []
        
        # 说话人信息
        speaker_info = context_info.get("speaker_info", {})
        if speaker_info:
            speaker_data = speaker_info.get("speaker_info", {})
            if speaker_data.get("profession"):
                context_parts.append(f"Speaker profession: {speaker_data['profession']}")
            if speaker_data.get("speaking_style"):
                context_parts.append(f"Speaking style: {speaker_data['speaking_style']}")
        
        # 关系信息
        relationship_info = context_info.get("relationship_info", {})
        if relationship_info:
            rel_summary = relationship_info.get("relationship_summary", {})
            if rel_summary.get("relationship_type"):
                context_parts.append(f"Relationship: {rel_summary['relationship_type']}")
            if rel_summary.get("formality"):
                context_parts.append(f"Formality level: {rel_summary['formality']}")
        
        # 文化信息
        cultural_info = context_info.get("cultural_info", {})
        if cultural_info:
            recommendations = cultural_info.get("recommendations", [])
            if recommendations:
                context_parts.append(f"Cultural notes: {', '.join(recommendations)}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available"
    
    def _apply_cultural_adaptations(self, text: str, request: TranslationRequest, 
                                  context_info: Dict[str, Any]) -> str:
        """应用文化适配"""
        if not request.cultural_adaptation:
            return text
        
        adapted_text = text
        
        # 处理中文姓名
        adapted_text = self._adapt_chinese_names(adapted_text)
        
        # 处理文化概念
        adapted_text = self._adapt_cultural_concepts(adapted_text)
        
        # 处理食物引用
        adapted_text = self._adapt_food_references(adapted_text)
        
        # 处理成语和俗语
        adapted_text = self._adapt_idioms(adapted_text)
        
        return adapted_text
    
    def _adapt_chinese_names(self, text: str) -> str:
        """适配中文姓名"""
        # 简化实现：保持中文姓名不变，但可以添加解释
        # 实际实现中可能需要更复杂的姓名识别和处理
        return text
    
    def _adapt_cultural_concepts(self, text: str) -> str:
        """适配文化概念"""
        cultural_mappings = {
            "春节": "Chinese New Year",
            "中秋节": "Mid-Autumn Festival",
            "端午节": "Dragon Boat Festival",
            "清明节": "Tomb Sweeping Day",
            "国庆节": "National Day",
            "元宵节": "Lantern Festival"
        }
        
        for chinese, english in cultural_mappings.items():
            text = text.replace(chinese, english)
        
        return text
    
    def _adapt_food_references(self, text: str) -> str:
        """适配食物引用"""
        food_mappings = {
            "饺子": "dumplings",
            "包子": "steamed buns",
            "面条": "noodles",
            "米饭": "rice",
            "粥": "congee",
            "豆腐": "tofu",
            "火锅": "hot pot",
            "烤鸭": "Peking duck"
        }
        
        for chinese, english in food_mappings.items():
            text = text.replace(chinese, english)
        
        return text
    
    def _adapt_idioms(self, text: str) -> str:
        """适配成语和俗语"""
        idiom_mappings = {
            "一石二鸟": "kill two birds with one stone",
            "画蛇添足": "gild the lily",
            "亡羊补牢": "better late than never",
            "守株待兔": "wait for windfalls",
            "刻舟求剑": "be rigid and inflexible"
        }
        
        for chinese, english in idiom_mappings.items():
            text = text.replace(chinese, english)
        
        return text
    
    def _optimize_for_subtitles(self, text: str, request: TranslationRequest) -> str:
        """优化字幕显示"""
        if not request.preserve_timing:
            return text
        
        # 检查长度限制
        max_length = request.max_length
        if not max_length:
            # 基于原文长度估算英文最大长度
            original_length = len(request.subtitle_entry.text)
            max_length = int(original_length * self.translation_config["max_length_ratio"])
        
        # 如果超长，进行压缩
        if len(text) > max_length:
            text = self._compress_text(text, max_length)
        
        # 优化可读性
        text = self._optimize_readability(text)
        
        return text
    
    def _compress_text(self, text: str, max_length: int) -> str:
        """压缩文本长度"""
        if len(text) <= max_length:
            return text
        
        # 简单的压缩策略
        # 1. 移除多余的空格
        compressed = " ".join(text.split())
        
        # 2. 使用缩写
        abbreviations = {
            "and": "&",
            "you": "u",
            "are": "r",
            "to": "2",
            "for": "4",
            "because": "cuz",
            "something": "sth",
            "someone": "sb"
        }
        
        for full, abbr in abbreviations.items():
            if len(compressed) > max_length:
                compressed = compressed.replace(f" {full} ", f" {abbr} ")
        
        # 3. 如果还是太长，截断并添加省略号
        if len(compressed) > max_length:
            compressed = compressed[:max_length-3] + "..."
        
        return compressed
    
    def _optimize_readability(self, text: str) -> str:
        """优化可读性"""
        # 确保首字母大写
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        
        # 确保句末标点
        if text and text[-1] not in ".!?":
            text += "."
        
        # 清理多余空格
        text = " ".join(text.split())
        
        return text
    
    def _check_timing_preservation(self, request: TranslationRequest, 
                                 translated_text: str) -> bool:
        """检查时长保持"""
        if not request.preserve_timing:
            return True
        
        original_length = len(request.subtitle_entry.text)
        translated_length = len(translated_text)
        
        # 检查长度比例是否在合理范围内
        ratio = translated_length / original_length if original_length > 0 else 1.0
        
        return ratio <= self.translation_config["max_length_ratio"]
    
    def _assess_translation_quality(self, original_text: str, translated_text: str, 
                                  request: TranslationRequest) -> Tuple[float, Dict[str, Any]]:
        """评估翻译质量"""
        quality_factors = {}
        
        # 1. 长度合理性 (0-1)
        length_score = self._assess_length_quality(original_text, translated_text)
        quality_factors["length_quality"] = length_score
        
        # 2. 术语一致性 (0-1)
        terminology_score = self._assess_terminology_consistency(translated_text, request)
        quality_factors["terminology_consistency"] = terminology_score
        
        # 3. 流畅性评估 (0-1)
        fluency_score = self._assess_fluency(translated_text)
        quality_factors["fluency"] = fluency_score
        
        # 4. 完整性检查 (0-1)
        completeness_score = self._assess_completeness(original_text, translated_text)
        quality_factors["completeness"] = completeness_score
        
        # 5. 风格一致性 (0-1)
        style_score = self._assess_style_consistency(translated_text, request)
        quality_factors["style_consistency"] = style_score
        
        # 计算综合质量分数
        weights = {
            "length_quality": 0.15,
            "terminology_consistency": 0.25,
            "fluency": 0.25,
            "completeness": 0.20,
            "style_consistency": 0.15
        }
        
        overall_score = sum(
            quality_factors[factor] * weight 
            for factor, weight in weights.items()
        )
        
        quality_details = {
            "factors": quality_factors,
            "weights": weights,
            "overall_score": overall_score
        }
        
        return overall_score, quality_details
    
    def _assess_length_quality(self, original_text: str, translated_text: str) -> float:
        """评估长度质量"""
        if not original_text:
            return 0.0
        
        ratio = len(translated_text) / len(original_text)
        
        # 理想比例是1.0-1.3，超出范围扣分
        if 1.0 <= ratio <= 1.3:
            return 1.0
        elif 0.8 <= ratio < 1.0:
            return 0.9
        elif 1.3 < ratio <= 1.5:
            return 0.8
        elif 0.6 <= ratio < 0.8:
            return 0.7
        elif 1.5 < ratio <= 2.0:
            return 0.6
        else:
            return 0.3
    
    def _assess_terminology_consistency(self, translated_text: str, 
                                      request: TranslationRequest) -> float:
        """评估术语一致性"""
        # 检查是否包含应该翻译的术语
        expected_terms = []
        for chinese_term in self.terminology_mappings.keys():
            if chinese_term in request.subtitle_entry.text:
                expected_terms.append(self.terminology_mappings[chinese_term])
        
        if not expected_terms:
            return 1.0
        
        # 检查术语是否正确使用
        correct_terms = sum(1 for term in expected_terms if term.lower() in translated_text.lower())
        
        return correct_terms / len(expected_terms) if expected_terms else 1.0
    
    def _assess_fluency(self, translated_text: str) -> float:
        """评估流畅性"""
        # 简化的流畅性评估
        score = 1.0
        
        # 检查基本语法问题
        if translated_text.count("  ") > 0:  # 多余空格
            score -= 0.1
        
        if not translated_text.strip():  # 空文本
            return 0.0
        
        # 检查是否有未翻译的标记
        if "[Translation needed:" in translated_text:
            score -= 0.5
        
        # 检查标点符号
        if translated_text and translated_text[-1] not in ".!?":
            score -= 0.1
        
        return max(score, 0.0)
    
    def _assess_completeness(self, original_text: str, translated_text: str) -> float:
        """评估完整性"""
        if not translated_text.strip():
            return 0.0
        
        if "[Translation needed:" in translated_text:
            return 0.3
        
        # 简化的完整性检查
        return 1.0
    
    def _assess_style_consistency(self, translated_text: str, 
                                request: TranslationRequest) -> float:
        """评估风格一致性"""
        # 简化的风格一致性评估
        # 实际实现中可能需要更复杂的风格分析
        return 0.8
    
    def _update_performance_stats(self, style: Optional[TranslationStyle], 
                                quality_score: float, processing_time: float, 
                                success: bool):
        """更新性能统计"""
        self.performance_stats["total_translations"] += 1
        
        if success:
            self.performance_stats["successful_translations"] += 1
            
            # 更新平均质量分数
            total = self.performance_stats["total_translations"]
            current_avg = self.performance_stats["average_quality_score"]
            new_avg = (current_avg * (total - 1) + quality_score) / total
            self.performance_stats["average_quality_score"] = new_avg
        else:
            self.performance_stats["error_count"] += 1
        
        # 更新平均处理时间
        total = self.performance_stats["total_translations"]
        current_avg = self.performance_stats["average_processing_time"]
        new_avg = (current_avg * (total - 1) + processing_time) / total
        self.performance_stats["average_processing_time"] = new_avg
        
        # 更新风格分布
        if style:
            style_name = style.value
            if style_name not in self.performance_stats["style_distribution"]:
                self.performance_stats["style_distribution"][style_name] = 0
            self.performance_stats["style_distribution"][style_name] += 1
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "target_language": "en",
            "performance_stats": self.performance_stats,
            "supported_styles": [style.value for style in TranslationStyle],
            "terminology_count": len(self.terminology_mappings),
            "cultural_adaptations": list(self.cultural_adaptations.keys())
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "style_distribution": {},
            "error_count": 0
        }
        logger.info("性能统计已重置")


# 全局英语翻译 Agent 实例
english_translation_agent = EnglishTranslationAgent()


def get_english_translation_agent() -> EnglishTranslationAgent:
    """获取英语翻译 Agent 实例"""
    return english_translation_agent


# 便捷函数
def translate_to_english(project_id: str, subtitle_entry: SubtitleEntry,
                        style: Optional[TranslationStyle] = None,
                        context_window: Optional[List[SubtitleEntry]] = None) -> TranslationResult:
    """便捷的英语翻译函数"""
    agent = get_english_translation_agent()
    
    request = TranslationRequest(
        request_id=str(uuid.uuid4()),
        project_id=project_id,
        subtitle_entry=subtitle_entry,
        style_preference=style,
        context_window=context_window
    )
    
    return agent.translate(request)