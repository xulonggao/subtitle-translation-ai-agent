"""
欧洲语言和阿拉伯语翻译 Agent
支持西班牙语、葡萄牙语、阿拉伯语翻译
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

logger = get_logger("european_arabic_translation_agent")


class EuropeanArabicLanguage(Enum):
    """欧洲和阿拉伯语言类型"""
    SPANISH = "es"          # 西班牙语
    PORTUGUESE = "pt"       # 葡萄牙语
    ARABIC = "ar"           # 阿拉伯语


class GenderType(Enum):
    """性别类型（用于欧洲语言的性别一致性）"""
    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTRAL = "neutral"


class TextDirection(Enum):
    """文本方向"""
    LEFT_TO_RIGHT = "ltr"   # 从左到右
    RIGHT_TO_LEFT = "rtl"   # 从右到左


class ReligiousSensitivity(Enum):
    """宗教敏感度等级"""
    HIGH = "high"           # 高敏感度
    MEDIUM = "medium"       # 中等敏感度
    LOW = "low"             # 低敏感度
    NONE = "none"           # 无宗教内容


@dataclass
class EuropeanArabicTranslationRequest:
    """欧洲语言和阿拉伯语翻译请求"""
    request_id: str
    project_id: str
    subtitle_entry: SubtitleEntry
    target_language: EuropeanArabicLanguage
    gender_context: Optional[Dict[str, GenderType]] = None
    religious_sensitivity: Optional[ReligiousSensitivity] = None
    context_window: Optional[List[SubtitleEntry]] = None
    preserve_gender_agreement: bool = True
    adapt_religious_content: bool = True
    maintain_cultural_respect: bool = True
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EuropeanArabicTranslationResult:
    """欧洲语言和阿拉伯语翻译结果"""
    request_id: str
    success: bool
    target_language: EuropeanArabicLanguage
    translated_text: Optional[str] = None
    original_text: Optional[str] = None
    text_direction: Optional[TextDirection] = None
    gender_adaptations: Optional[List[str]] = None
    religious_adaptations: Optional[List[str]] = None
    terminology_used: Optional[Dict[str, str]] = None
    quality_score: float = 0.0
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


class EuropeanArabicTranslationAgent:
    """欧洲语言和阿拉伯语翻译 Agent
    
    主要功能：
    1. 支持西班牙语、葡萄牙语翻译
    2. 支持阿拉伯语翻译，处理从右到左的文本方向
    3. 实现欧洲语言的性别和格变处理
    4. 添加阿拉伯语的文化和宗教敏感词处理
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"eu_ar_agent_{uuid.uuid4().hex[:8]}"
        
        # 集成其他组件
        self.context_agent = get_context_agent()
        self.dynamic_kb = get_dynamic_knowledge_manager()
        
        # 语言特定配置
        self.language_configs = {
            EuropeanArabicLanguage.SPANISH: {
                "name": "西班牙语",
                "script": "latin",
                "text_direction": TextDirection.LEFT_TO_RIGHT,
                "gender_system": True,
                "religious_sensitivity": False,
                "max_length_ratio": 1.2,
                "cultural_context": "hispanic"
            },
            EuropeanArabicLanguage.PORTUGUESE: {
                "name": "葡萄牙语",
                "script": "latin",
                "text_direction": TextDirection.LEFT_TO_RIGHT,
                "gender_system": True,
                "religious_sensitivity": False,
                "max_length_ratio": 1.2,
                "cultural_context": "lusophone"
            },
            EuropeanArabicLanguage.ARABIC: {
                "name": "阿拉伯语",
                "script": "arabic",
                "text_direction": TextDirection.RIGHT_TO_LEFT,
                "gender_system": True,
                "religious_sensitivity": True,
                "max_length_ratio": 1.1,
                "cultural_context": "islamic"
            }
        }
        
        # 系统提示模板
        self.system_prompts = {
            EuropeanArabicLanguage.SPANISH: """
You are a professional Spanish translator specializing in Chinese-to-Spanish translation.
Focus on:
- Maintaining proper gender agreement (masculine/feminine)
- Using appropriate verb conjugations and noun declensions
- Adapting cultural references for Spanish-speaking audiences
- Ensuring natural Spanish flow and expressions
- Using regional variations appropriately (Latin American vs Iberian Spanish)
""",
            EuropeanArabicLanguage.PORTUGUESE: """
You are a professional Portuguese translator specializing in Chinese-to-Portuguese translation.
Focus on:
- Maintaining proper gender agreement (masculine/feminine)
- Using appropriate verb conjugations and noun declensions
- Adapting cultural references for Portuguese-speaking audiences
- Ensuring natural Portuguese flow and expressions
- Using regional variations appropriately (Brazilian vs European Portuguese)
""",
            EuropeanArabicLanguage.ARABIC: """
You are a professional Arabic translator specializing in Chinese-to-Arabic translation.
Focus on:
- Maintaining proper gender agreement and grammatical structures
- Using appropriate religious and cultural terminology
- Respecting Islamic cultural values and sensitivities
- Ensuring natural Arabic flow and expressions
- Using Modern Standard Arabic (MSA) for formal content
- Handling right-to-left text direction properly
"""
        }
        
        # 术语映射表
        self.terminology_mappings = {
            EuropeanArabicLanguage.SPANISH: {
                # 军事术语
                "参谋长": "jefe de estado mayor",
                "司令": "comandante",
                "队长": "capitán",
                "战友": "compañero de armas",
                "同志": "camarada",
                "长官": "oficial",
                "任务": "misión",
                "训练": "entrenamiento",
                "部队": "tropas",
                
                # 现代生活术语
                "鸡娃": "padres helicóptero",
                "内卷": "competencia feroz",
                "躺平": "rendirse",
                "996": "horario 996",
                "打工人": "trabajador",
                
                # 关系称谓
                "哥": "hermano",
                "姐": "hermana",
                "老板": "jefe",
                "同事": "colega",
                "朋友": "amigo",
                "男朋友": "novio",
                "女朋友": "novia"
            },
            EuropeanArabicLanguage.PORTUGUESE: {
                # 军事术语
                "参谋长": "chefe do estado-maior",
                "司令": "comandante",
                "队长": "capitão",
                "战友": "companheiro de armas",
                "同志": "camarada",
                "长官": "oficial",
                "任务": "missão",
                "训练": "treinamento",
                "部队": "tropas",
                
                # 现代生活术语
                "鸡娃": "pais helicóptero",
                "内卷": "competição feroz",
                "躺平": "desistir",
                "996": "horário 996",
                "打工人": "trabalhador",
                
                # 关系称谓
                "哥": "irmão",
                "姐": "irmã",
                "老板": "chefe",
                "同事": "colega",
                "朋友": "amigo",
                "男朋友": "namorado",
                "女朋友": "namorada"
            },
            EuropeanArabicLanguage.ARABIC: {
                # 军事术语
                "参谋长": "رئيس الأركان",
                "司令": "القائد",
                "队长": "النقيب",
                "战友": "رفيق السلاح",
                "同志": "الرفيق",
                "长官": "الضابط",
                "任务": "المهمة",
                "训练": "التدريب",
                "部队": "القوات",
                
                # 现代生活术语
                "鸡娃": "الآباء المروحية",
                "内卷": "المنافسة الشرسة",
                "躺平": "الاستسلام",
                "996": "نظام العمل 996",
                "打工人": "العامل",
                
                # 关系称谓
                "哥": "الأخ",
                "姐": "الأخت",
                "老板": "المدير",
                "同事": "الزميل",
                "朋友": "الصديق",
                "男朋友": "الصديق",
                "女朋友": "الصديقة"
            }
        }
        
        # 性别映射规则（用于欧洲语言）
        self.gender_mappings = {
            EuropeanArabicLanguage.SPANISH: {
                # 职业词汇的性别变化
                "医生": {"masculine": "médico", "feminine": "médica"},
                "老师": {"masculine": "profesor", "feminine": "profesora"},
                "学生": {"masculine": "estudiante", "feminine": "estudiante"},
                "朋友": {"masculine": "amigo", "feminine": "amiga"},
                "同事": {"masculine": "compañero", "feminine": "compañera"}
            },
            EuropeanArabicLanguage.PORTUGUESE: {
                # 职业词汇的性别变化
                "医生": {"masculine": "médico", "feminine": "médica"},
                "老师": {"masculine": "professor", "feminine": "professora"},
                "学生": {"masculine": "estudante", "feminine": "estudante"},
                "朋友": {"masculine": "amigo", "feminine": "amiga"},
                "同事": {"masculine": "colega", "feminine": "colega"}
            },
            EuropeanArabicLanguage.ARABIC: {
                # 阿拉伯语的性别变化
                "医生": {"masculine": "الطبيب", "feminine": "الطبيبة"},
                "老师": {"masculine": "المعلم", "feminine": "المعلمة"},
                "学生": {"masculine": "الطالب", "feminine": "الطالبة"},
                "朋友": {"masculine": "الصديق", "feminine": "الصديقة"},
                "同事": {"masculine": "الزميل", "feminine": "الزميلة"}
            }
        }
        
        # 宗教敏感词处理（阿拉伯语）
        self.religious_adaptations = {
            # 宗教概念
            "上帝": "الله",
            "神": "الله",
            "天": "السماء",
            "祈祷": "الصلاة",
            "祝福": "البركة",
            "平安": "السلام",
            "感谢": "الحمد لله",
            
            # 时间概念
            "明天": "غداً إن شاء الله",  # 如果真主意愿
            "希望": "إن شاء الله",
            
            # 避免的概念
            "猪": "الخنزير",  # 需要谨慎处理
            "酒": "الخمر",    # 需要谨慎处理
        }
        
        # 文化适配规则
        self.cultural_adaptations = {
            "hispanic": {
                "family_values": True,
                "catholic_influence": True,
                "regional_variations": True,
                "formal_address": True
            },
            "lusophone": {
                "family_values": True,
                "catholic_influence": True,
                "regional_variations": True,
                "formal_address": True
            },
            "islamic": {
                "religious_values": True,
                "family_honor": True,
                "gender_sensitivity": True,
                "halal_concepts": True
            }
        }
        
        # 性能统计
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "language_distribution": {},
            "gender_adaptations_count": 0,
            "religious_adaptations_count": 0,
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "error_count": 0
        }
        
        logger.info("欧洲语言和阿拉伯语翻译 Agent 初始化完成", agent_id=self.agent_id)
    
    def translate(self, request: EuropeanArabicTranslationRequest) -> EuropeanArabicTranslationResult:
        """执行欧洲语言和阿拉伯语翻译"""
        start_time = datetime.now()
        
        try:
            # 验证请求
            if not self._validate_request(request):
                return EuropeanArabicTranslationResult(
                    request_id=request.request_id,
                    success=False,
                    target_language=request.target_language,
                    error_message="翻译请求验证失败"
                )
            
            # 分析上下文
            context_info = self._analyze_context(request)
            
            # 确定性别上下文
            gender_context = self._determine_gender_context(request, context_info)
            
            # 确定宗教敏感度
            religious_sensitivity = self._determine_religious_sensitivity(request, context_info)
            
            # 获取术语映射
            terminology = self._get_terminology_mappings(request, context_info)
            
            # 执行翻译
            translated_text = self._perform_translation(request, gender_context, terminology, context_info)
            
            # 应用性别一致性处理
            gender_adapted_text = self._apply_gender_adaptations(translated_text, request, gender_context)
            
            # 应用宗教敏感词处理
            religiously_adapted_text = self._apply_religious_adaptations(gender_adapted_text, request, religious_sensitivity)
            
            # 优化格式和方向
            optimized_text = self._optimize_text_formatting(religiously_adapted_text, request)
            
            # 质量评估
            quality_score = self._assess_translation_quality(
                request.subtitle_entry.text, optimized_text, request
            )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计信息
            self._update_performance_stats(request.target_language, quality_score, processing_time, True)
            
            # 确定文本方向
            text_direction = self.language_configs[request.target_language]["text_direction"]
            
            result = EuropeanArabicTranslationResult(
                request_id=request.request_id,
                success=True,
                target_language=request.target_language,
                translated_text=optimized_text,
                original_text=request.subtitle_entry.text,
                text_direction=text_direction,
                gender_adaptations=context_info.get("gender_adaptations", []),
                religious_adaptations=context_info.get("religious_adaptations", []),
                terminology_used=terminology,
                quality_score=quality_score,
                processing_time_ms=int(processing_time),
                confidence=quality_score,
                metadata={
                    "language_config": self.language_configs[request.target_language],
                    "gender_context": gender_context,
                    "religious_sensitivity": religious_sensitivity.value if religious_sensitivity else None
                }
            )
            
            logger.debug("欧洲语言和阿拉伯语翻译完成", 
                        request_id=request.request_id,
                        target_language=request.target_language.value,
                        text_direction=text_direction.value,
                        quality_score=quality_score,
                        processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_stats(request.target_language, 0.0, processing_time, False)
            
            logger.error("欧洲语言和阿拉伯语翻译失败", 
                        request_id=request.request_id,
                        target_language=request.target_language.value,
                        error=str(e))
            
            return EuropeanArabicTranslationResult(
                request_id=request.request_id,
                success=False,
                target_language=request.target_language,
                original_text=request.subtitle_entry.text,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def _validate_request(self, request: EuropeanArabicTranslationRequest) -> bool:
        """验证翻译请求"""
        if not request.subtitle_entry or not request.subtitle_entry.text:
            return False
        
        if not request.project_id:
            return False
        
        if request.target_language not in self.language_configs:
            return False
        
        return True
    
    def _analyze_context(self, request: EuropeanArabicTranslationRequest) -> Dict[str, Any]:
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
                target_language=request.target_language.value
            )
            
            cultural_response = self.context_agent.process_query(cultural_query)
            if cultural_response.success:
                context_info["cultural_info"] = cultural_response.result
            
        except Exception as e:
            logger.warning("上下文分析失败", error=str(e))
        
        return context_info    

    def _determine_gender_context(self, request: EuropeanArabicTranslationRequest, 
                                context_info: Dict[str, Any]) -> Dict[str, GenderType]:
        """确定性别上下文"""
        gender_context = {}
        
        # 如果请求中指定了性别上下文，优先使用
        if request.gender_context:
            gender_context.update(request.gender_context)
        
        # 从上下文信息推断性别
        speaker_info = context_info.get("speaker_info", {})
        relationship_info = context_info.get("relationship_info", {})
        
        # 获取说话人性别
        speaker_data = speaker_info.get("speaker_info", {})
        speaker = speaker_data.get("speaker")
        if speaker:
            # 从人物关系中获取性别信息
            # 这里可以集成更复杂的性别推断逻辑
            gender_context[speaker] = GenderType.NEUTRAL  # 默认中性
        
        return gender_context
    
    def _determine_religious_sensitivity(self, request: EuropeanArabicTranslationRequest,
                                       context_info: Dict[str, Any]) -> Optional[ReligiousSensitivity]:
        """确定宗教敏感度"""
        # 如果请求中指定了宗教敏感度，优先使用
        if request.religious_sensitivity:
            return request.religious_sensitivity
        
        # 阿拉伯语默认高宗教敏感度
        if request.target_language == EuropeanArabicLanguage.ARABIC:
            return ReligiousSensitivity.HIGH
        
        # 检查文本中是否包含宗教内容
        text = request.subtitle_entry.text
        religious_keywords = ["上帝", "神", "祈祷", "祝福", "天堂", "地狱"]
        
        if any(keyword in text for keyword in religious_keywords):
            return ReligiousSensitivity.MEDIUM
        
        return ReligiousSensitivity.LOW
    
    def _get_terminology_mappings(self, request: EuropeanArabicTranslationRequest, 
                                context_info: Dict[str, Any]) -> Dict[str, str]:
        """获取术语映射"""
        terminology = {}
        
        # 获取语言特定的术语映射
        lang_terminology = self.terminology_mappings.get(request.target_language, {})
        
        # 基础术语映射
        for chinese, target in lang_terminology.items():
            if chinese in request.subtitle_entry.text:
                terminology[chinese] = target
        
        # 从知识库获取项目特定术语
        try:
            kb_query = KnowledgeQuery(
                query_type="terminology",
                source_text=request.subtitle_entry.text,
                target_language=request.target_language.value,
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
    
    def _perform_translation(self, request: EuropeanArabicTranslationRequest,
                           gender_context: Dict[str, GenderType],
                           terminology: Dict[str, str],
                           context_info: Dict[str, Any]) -> str:
        """执行核心翻译"""
        text = request.subtitle_entry.text
        
        # 应用术语替换
        for chinese_term, target_term in terminology.items():
            text = text.replace(chinese_term, f"[{target_term}]")
        
        # 构建翻译提示
        system_prompt = self.system_prompts.get(request.target_language, "")
        
        # 添加上下文信息到提示中
        context_prompt = self._build_context_prompt(context_info, request.target_language)
        
        # 添加性别上下文信息
        gender_prompt = self._build_gender_prompt(gender_context, request.target_language)
        
        # 构建完整的翻译提示
        full_prompt = f"""
{system_prompt}

Context Information:
{context_prompt}

Gender Context:
{gender_prompt}

Terminology to use:
{json.dumps(terminology, ensure_ascii=False, indent=2)}

Please translate the following Chinese text to {self.language_configs[request.target_language]['name']}:
"{text}"

Requirements:
- Maintain the original meaning and tone
- Use the provided terminology consistently
- Apply appropriate gender agreement if applicable
- Respect cultural and religious sensitivities
- Ensure natural and fluent translation
"""
        
        # 这里应该调用实际的翻译模型（如Claude）
        # 为了演示，我们提供一个简化的翻译逻辑
        translated_text = self._simulate_translation(text, request.target_language, gender_context, terminology)
        
        # 清理术语标记
        for chinese_term, target_term in terminology.items():
            translated_text = translated_text.replace(f"[{target_term}]", target_term)
        
        return translated_text
    
    def _build_context_prompt(self, context_info: Dict[str, Any], 
                            target_language: EuropeanArabicLanguage) -> str:
        """构建上下文提示"""
        context_parts = []
        
        # 说话人信息
        speaker_info = context_info.get("speaker_info", {})
        if speaker_info:
            speaker_data = speaker_info.get("speaker_info", {})
            if speaker_data.get("profession"):
                context_parts.append(f"Speaker profession: {speaker_data['profession']}")
        
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
        
        # 语言特定的文化背景
        lang_config = self.language_configs[target_language]
        cultural_context = lang_config.get("cultural_context")
        if cultural_context:
            context_parts.append(f"Cultural context: {cultural_context}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available"
    
    def _build_gender_prompt(self, gender_context: Dict[str, GenderType], 
                           target_language: EuropeanArabicLanguage) -> str:
        """构建性别上下文提示"""
        if not gender_context:
            return "No specific gender context available"
        
        gender_parts = []
        for entity, gender in gender_context.items():
            gender_parts.append(f"{entity}: {gender.value}")
        
        lang_config = self.language_configs[target_language]
        if lang_config.get("gender_system", False):
            gender_parts.append("Note: Apply appropriate gender agreement in translation")
        
        return "\n".join(gender_parts)
    
    def _simulate_translation(self, text: str, target_language: EuropeanArabicLanguage,
                            gender_context: Dict[str, GenderType],
                            terminology: Dict[str, str]) -> str:
        """模拟翻译（实际实现中应该调用真实的翻译模型）"""
        # 这是一个简化的翻译模拟，实际实现中应该调用Claude等模型
        
        # 获取语言特定的术语映射
        lang_terminology = self.terminology_mappings.get(target_language, {})
        
        # 应用基本术语映射
        result = text
        for chinese, target in lang_terminology.items():
            result = result.replace(chinese, target)
        
        # 应用自定义术语映射
        for chinese, target in terminology.items():
            result = result.replace(chinese, target)
        
        # 如果没有找到合适的翻译，返回原文加上标记
        if result == text:
            lang_name = self.language_configs[target_language]["name"]
            result = f"[{lang_name} translation needed: {text}]"
        
        return result
    
    def _apply_gender_adaptations(self, text: str, request: EuropeanArabicTranslationRequest,
                                gender_context: Dict[str, GenderType]) -> str:
        """应用性别一致性处理"""
        if not request.preserve_gender_agreement:
            return text
        
        lang_config = self.language_configs[request.target_language]
        if not lang_config.get("gender_system", False):
            return text
        
        adapted_text = text
        
        # 获取语言特定的性别映射
        gender_mappings = self.gender_mappings.get(request.target_language, {})
        
        # 应用性别适配
        for chinese_word, gender_variants in gender_mappings.items():
            if chinese_word in request.subtitle_entry.text:
                # 根据上下文确定性别
                # 这里可以实现更复杂的性别推断逻辑
                gender = GenderType.MASCULINE  # 默认阳性
                
                if gender in [GenderType.MASCULINE, GenderType.FEMININE]:
                    gender_key = gender.value
                    if gender_key in gender_variants:
                        adapted_text = adapted_text.replace(chinese_word, gender_variants[gender_key])
        
        return adapted_text
    
    def _apply_religious_adaptations(self, text: str, request: EuropeanArabicTranslationRequest,
                                   religious_sensitivity: Optional[ReligiousSensitivity]) -> str:
        """应用宗教敏感词处理"""
        if not request.adapt_religious_content:
            return text
        
        if request.target_language != EuropeanArabicLanguage.ARABIC:
            return text
        
        if not religious_sensitivity or religious_sensitivity == ReligiousSensitivity.NONE:
            return text
        
        adapted_text = text
        
        # 应用宗教适配
        for chinese_term, arabic_term in self.religious_adaptations.items():
            if chinese_term in request.subtitle_entry.text:
                adapted_text = adapted_text.replace(chinese_term, arabic_term)
        
        return adapted_text
    
    def _optimize_text_formatting(self, text: str, request: EuropeanArabicTranslationRequest) -> str:
        """优化文本格式和方向"""
        lang_config = self.language_configs[request.target_language]
        
        # 检查长度限制
        max_length_ratio = lang_config.get("max_length_ratio", 1.2)
        original_length = len(request.subtitle_entry.text)
        max_length = int(original_length * max_length_ratio)
        
        # 如果超长，进行压缩
        if len(text) > max_length:
            text = self._compress_text(text, max_length, request.target_language)
        
        # 应用语言特定的格式化
        text = self._apply_language_specific_formatting(text, request.target_language)
        
        return text
    
    def _compress_text(self, text: str, max_length: int, 
                     target_language: EuropeanArabicLanguage) -> str:
        """压缩文本长度"""
        if len(text) <= max_length:
            return text
        
        # 语言特定的压缩策略
        compressed = text
        
        # 通用压缩策略
        if target_language in [EuropeanArabicLanguage.SPANISH, EuropeanArabicLanguage.PORTUGUESE]:
            # 欧洲语言可以使用缩写
            abbreviations = {
                "señor": "Sr.",
                "señora": "Sra.",
                "doctor": "Dr.",
                "doctora": "Dra."
            }
            
            for full, abbr in abbreviations.items():
                compressed = compressed.replace(full, abbr)
        
        # 如果还是太长，截断并添加省略号
        if len(compressed) > max_length:
            compressed = compressed[:max_length-3] + "..."
        
        return compressed
    
    def _apply_language_specific_formatting(self, text: str, 
                                          target_language: EuropeanArabicLanguage) -> str:
        """应用语言特定的格式化"""
        # 清理多余空格
        text = " ".join(text.split())
        
        # 语言特定的格式化
        if target_language == EuropeanArabicLanguage.ARABIC:
            # 阿拉伯语特殊处理
            # 确保正确的文本方向标记
            text = f"\u202B{text}\u202C"  # 添加RTL标记
        
        return text
    
    def _assess_translation_quality(self, original_text: str, translated_text: str,
                                  request: EuropeanArabicTranslationRequest) -> float:
        """评估翻译质量"""
        quality_factors = {}
        
        # 1. 长度合理性
        length_score = self._assess_length_quality(original_text, translated_text, request.target_language)
        quality_factors["length_quality"] = length_score
        
        # 2. 术语一致性
        terminology_score = self._assess_terminology_consistency(translated_text, request)
        quality_factors["terminology_consistency"] = terminology_score
        
        # 3. 文化适配性
        cultural_score = self._assess_cultural_adaptation(translated_text, request)
        quality_factors["cultural_adaptation"] = cultural_score
        
        # 4. 完整性检查
        completeness_score = self._assess_completeness(original_text, translated_text)
        quality_factors["completeness"] = completeness_score
        
        # 5. 性别一致性（欧洲语言）
        gender_score = self._assess_gender_consistency(translated_text, request)
        quality_factors["gender_consistency"] = gender_score
        
        # 计算综合质量分数
        weights = {
            "length_quality": 0.2,
            "terminology_consistency": 0.25,
            "cultural_adaptation": 0.2,
            "completeness": 0.2,
            "gender_consistency": 0.15
        }
        
        overall_score = sum(
            quality_factors[factor] * weight 
            for factor, weight in weights.items()
        )
        
        return overall_score
    
    def _assess_length_quality(self, original_text: str, translated_text: str,
                             target_language: EuropeanArabicLanguage) -> float:
        """评估长度质量"""
        if not original_text:
            return 0.0
        
        lang_config = self.language_configs[target_language]
        max_ratio = lang_config.get("max_length_ratio", 1.2)
        
        ratio = len(translated_text) / len(original_text)
        
        # 根据语言特定的比例评估
        if ratio <= max_ratio:
            return 1.0
        elif ratio <= max_ratio * 1.2:
            return 0.8
        elif ratio <= max_ratio * 1.5:
            return 0.6
        else:
            return 0.3
    
    def _assess_terminology_consistency(self, translated_text: str,
                                      request: EuropeanArabicTranslationRequest) -> float:
        """评估术语一致性"""
        lang_terminology = self.terminology_mappings.get(request.target_language, {})
        expected_terms = []
        
        for chinese_term in lang_terminology.keys():
            if chinese_term in request.subtitle_entry.text:
                expected_terms.append(lang_terminology[chinese_term])
        
        if not expected_terms:
            return 1.0
        
        # 检查术语是否正确使用
        correct_terms = sum(1 for term in expected_terms if term in translated_text)
        
        return correct_terms / len(expected_terms) if expected_terms else 1.0
    
    def _assess_cultural_adaptation(self, translated_text: str,
                                  request: EuropeanArabicTranslationRequest) -> float:
        """评估文化适配性"""
        # 简化的文化适配评估
        # 实际实现中可能需要更复杂的文化分析
        
        # 检查是否包含不当的文化引用
        if request.target_language == EuropeanArabicLanguage.ARABIC:
            # 阿拉伯语的宗教敏感性检查
            sensitive_words = ["猪", "酒", "赌博"]
            for word in sensitive_words:
                if word in translated_text:
                    return 0.5  # 降低分数
        
        return 0.8
    
    def _assess_completeness(self, original_text: str, translated_text: str) -> float:
        """评估完整性"""
        if not translated_text.strip():
            return 0.0
        
        if "translation needed:" in translated_text.lower():
            return 0.3
        
        return 1.0
    
    def _assess_gender_consistency(self, translated_text: str,
                                 request: EuropeanArabicTranslationRequest) -> float:
        """评估性别一致性"""
        lang_config = self.language_configs[request.target_language]
        
        if not lang_config.get("gender_system", False):
            return 1.0  # 不支持性别系统的语言得满分
        
        # 简化的性别一致性评估
        # 实际实现中需要更复杂的语法分析
        return 0.8
    
    def _update_performance_stats(self, target_language: EuropeanArabicLanguage,
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
        
        # 更新语言分布
        lang_name = target_language.value
        if lang_name not in self.performance_stats["language_distribution"]:
            self.performance_stats["language_distribution"][lang_name] = 0
        self.performance_stats["language_distribution"][lang_name] += 1
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表"""
        return [
            {
                "code": lang.value,
                "name": config["name"],
                "script": config["script"],
                "text_direction": config["text_direction"].value,
                "gender_system": config["gender_system"],
                "religious_sensitivity": config["religious_sensitivity"],
                "cultural_context": config["cultural_context"]
            }
            for lang, config in self.language_configs.items()
        ]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "supported_languages": len(self.language_configs),
            "language_list": [lang.value for lang in self.language_configs.keys()],
            "performance_stats": self.performance_stats,
            "gender_types": [gender.value for gender in GenderType],
            "religious_sensitivity_levels": [level.value for level in ReligiousSensitivity],
            "text_directions": [direction.value for direction in TextDirection]
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "language_distribution": {},
            "gender_adaptations_count": 0,
            "religious_adaptations_count": 0,
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "error_count": 0
        }
        logger.info("性能统计已重置")


# 全局欧洲语言和阿拉伯语翻译 Agent 实例
european_arabic_translation_agent = EuropeanArabicTranslationAgent()


def get_european_arabic_translation_agent() -> EuropeanArabicTranslationAgent:
    """获取欧洲语言和阿拉伯语翻译 Agent 实例"""
    return european_arabic_translation_agent


# 便捷函数
def translate_to_european_arabic_language(project_id: str, subtitle_entry: SubtitleEntry,
                                        target_language: EuropeanArabicLanguage,
                                        gender_context: Optional[Dict[str, GenderType]] = None,
                                        religious_sensitivity: Optional[ReligiousSensitivity] = None,
                                        context_window: Optional[List[SubtitleEntry]] = None) -> EuropeanArabicTranslationResult:
    """便捷的欧洲语言和阿拉伯语翻译函数"""
    agent = get_european_arabic_translation_agent()
    
    request = EuropeanArabicTranslationRequest(
        request_id=str(uuid.uuid4()),
        project_id=project_id,
        subtitle_entry=subtitle_entry,
        target_language=target_language,
        gender_context=gender_context,
        religious_sensitivity=religious_sensitivity,
        context_window=context_window
    )
    
    return agent.translate(request)