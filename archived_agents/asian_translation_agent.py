"""
亚洲语言翻译 Agent 群
支持日语、韩语、泰语、越南语、印尼语、马来语等亚洲语言翻译
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

logger = get_logger("asian_translation_agent")


class AsianLanguage(Enum):
    """亚洲语言类型"""
    JAPANESE = "ja"         # 日语
    KOREAN = "ko"          # 韩语
    THAI = "th"            # 泰语
    VIETNAMESE = "vi"      # 越南语
    INDONESIAN = "id"      # 印尼语
    MALAY = "ms"           # 马来语


class HonorificLevel(Enum):
    """敬语等级"""
    VERY_HIGH = "very_high"     # 极高敬语（日语：尊敬语，韩语：아주높임）
    HIGH = "high"               # 高敬语（日语：丁宁语，韩语：높임）
    MEDIUM = "medium"           # 中等敬语（日语：普通语，韩语：보통）
    LOW = "low"                 # 低敬语（日语：친구말，韩语：반말）
    INTIMATE = "intimate"       # 亲密语（家人朋友间）


class CulturalContext(Enum):
    """文化背景"""
    CONFUCIAN = "confucian"         # 儒家文化圈（中日韩）
    BUDDHIST = "buddhist"           # 佛教文化
    ISLAMIC = "islamic"             # 伊斯兰文化（印尼、马来）
    THERAVADA = "theravada"         # 上座部佛教（泰国）
    MODERN_URBAN = "modern_urban"   # 现代都市文化


@dataclass
class AsianTranslationRequest:
    """亚洲语言翻译请求"""
    request_id: str
    project_id: str
    subtitle_entry: SubtitleEntry
    target_language: AsianLanguage
    honorific_level: Optional[HonorificLevel] = None
    cultural_context: Optional[CulturalContext] = None
    context_window: Optional[List[SubtitleEntry]] = None
    preserve_honorifics: bool = True
    adapt_cultural_references: bool = True
    maintain_formality: bool = True
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AsianTranslationResult:
    """亚洲语言翻译结果"""
    request_id: str
    success: bool
    target_language: AsianLanguage
    translated_text: Optional[str] = None
    original_text: Optional[str] = None
    honorific_level_used: Optional[HonorificLevel] = None
    cultural_adaptations: Optional[List[str]] = None
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


class AsianTranslationAgent:
    """亚洲语言翻译 Agent 群
    
    主要功能：
    1. 支持多种亚洲语言翻译
    2. 实现敬语系统和文化适配
    3. 处理汉字文化圈的术语一致性
    4. 亚洲语言特有的格式和排版处理
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"asian_agent_{uuid.uuid4().hex[:8]}"
        
        # 集成其他组件
        self.context_agent = get_context_agent()
        self.dynamic_kb = get_dynamic_knowledge_manager()
        
        # 语言特定配置
        self.language_configs = {
            AsianLanguage.JAPANESE: {
                "name": "日语",
                "script": "hiragana_katakana_kanji",
                "honorific_system": True,
                "cultural_context": CulturalContext.CONFUCIAN,
                "max_length_ratio": 1.1,  # 日语通常比中文稍长
                "writing_direction": "horizontal"
            },
            AsianLanguage.KOREAN: {
                "name": "韩语",
                "script": "hangul_hanja",
                "honorific_system": True,
                "cultural_context": CulturalContext.CONFUCIAN,
                "max_length_ratio": 1.2,
                "writing_direction": "horizontal"
            },
            AsianLanguage.THAI: {
                "name": "泰语",
                "script": "thai",
                "honorific_system": True,
                "cultural_context": CulturalContext.THERAVADA,
                "max_length_ratio": 1.4,
                "writing_direction": "horizontal"
            },
            AsianLanguage.VIETNAMESE: {
                "name": "越南语",
                "script": "latin_vietnamese",
                "honorific_system": True,
                "cultural_context": CulturalContext.CONFUCIAN,
                "max_length_ratio": 1.3,
                "writing_direction": "horizontal"
            },
            AsianLanguage.INDONESIAN: {
                "name": "印尼语",
                "script": "latin",
                "honorific_system": False,
                "cultural_context": CulturalContext.ISLAMIC,
                "max_length_ratio": 1.3,
                "writing_direction": "horizontal"
            },
            AsianLanguage.MALAY: {
                "name": "马来语",
                "script": "latin",
                "honorific_system": False,
                "cultural_context": CulturalContext.ISLAMIC,
                "max_length_ratio": 1.3,
                "writing_direction": "horizontal"
            }
        }
        
        # 敬语系统提示模板
        self.honorific_prompts = {
            AsianLanguage.JAPANESE: {
                HonorificLevel.VERY_HIGH: """
You are a professional Japanese translator specializing in formal keigo (honorific language).
Focus on:
- Using 尊敬語 (sonkeigo) and 謙譲語 (kenjougo) appropriately
- Maintaining proper formality levels for business/official contexts
- Using です/ます forms consistently
- Ensuring cultural appropriateness for Japanese audiences
""",
                HonorificLevel.HIGH: """
You are a Japanese translator specializing in polite language.
Focus on:
- Using です/ます (desu/masu) forms
- Maintaining polite but not overly formal tone
- Using appropriate honorific expressions
- Ensuring natural Japanese flow
""",
                HonorificLevel.MEDIUM: """
You are a Japanese translator for casual but polite conversation.
Focus on:
- Using だ/である (da/de aru) forms when appropriate
- Balancing politeness with naturalness
- Using common Japanese expressions
- Maintaining conversational flow
""",
                HonorificLevel.LOW: """
You are a Japanese translator for casual conversation.
Focus on:
- Using casual forms and expressions
- Maintaining friendly, informal tone
- Using colloquial Japanese when appropriate
- Ensuring natural casual conversation flow
"""
            },
            AsianLanguage.KOREAN: {
                HonorificLevel.VERY_HIGH: """
You are a professional Korean translator specializing in formal honorific language.
Focus on:
- Using 아주높임 (aju nopim) - very high honorific forms
- Using 하십시오체 (hasipsio-che) formal endings
- Maintaining proper respect levels for seniors/superiors
- Ensuring cultural appropriateness for Korean audiences
""",
                HonorificLevel.HIGH: """
You are a Korean translator specializing in polite language.
Focus on:
- Using 높임말 (nopimmal) - honorific language
- Using 해요체 (haeyo-che) polite endings
- Maintaining respectful but approachable tone
- Using appropriate honorific vocabulary
""",
                HonorificLevel.MEDIUM: """
You are a Korean translator for standard polite conversation.
Focus on:
- Using 해요체 (haeyo-che) for general politeness
- Balancing formality with naturalness
- Using common Korean expressions
- Maintaining conversational appropriateness
""",
                HonorificLevel.LOW: """
You are a Korean translator for casual conversation.
Focus on:
- Using 반말 (banmal) - casual speech
- Using 해체 (hae-che) casual endings
- Maintaining friendly, informal tone
- Using colloquial Korean expressions
"""
            }
        }
        
        # 术语映射表（按语言分类）
        self.terminology_mappings = {
            AsianLanguage.JAPANESE: {
                # 军事术语
                "参谋长": "参謀長",
                "司令": "司令官",
                "队长": "隊長",
                "战友": "戦友",
                "同志": "同志",
                "长官": "長官",
                "任务": "任務",
                "训练": "訓練",
                "部队": "部隊",
                
                # 现代生活术语
                "鸡娃": "教育ママ",
                "内卷": "過当競争",
                "躺平": "寝そべり族",
                "996": "996勤務",
                "打工人": "サラリーマン",
                
                # 关系称谓
                "哥": "お兄さん",
                "姐": "お姉さん",
                "老板": "社長",
                "同事": "同僚",
                "朋友": "友達",
                "男朋友": "彼氏",
                "女朋友": "彼女"
            },
            AsianLanguage.KOREAN: {
                # 军事术语
                "参谋长": "참모장",
                "司令": "사령관",
                "队长": "대장",
                "战友": "전우",
                "同志": "동지",
                "长官": "장관",
                "任务": "임무",
                "训练": "훈련",
                "部队": "부대",
                
                # 现代生活术语
                "鸡娃": "헬리콥터 부모",
                "内卷": "과도한 경쟁",
                "躺平": "눕기족",
                "996": "996 근무제",
                "打工人": "직장인",
                
                # 关系称谓
                "哥": "오빠/형",
                "姐": "언니/누나",
                "老板": "사장님",
                "同事": "동료",
                "朋友": "친구",
                "男朋友": "남자친구",
                "女朋友": "여자친구"
            },
            AsianLanguage.THAI: {
                # 军事术语
                "参谋长": "หัวหน้าเสนาธิการ",
                "司令": "ผู้บัญชาการ",
                "队长": "หัวหน้าหน่วย",
                "战友": "เพื่อนร่วมรบ",
                "长官": "ท่านผู้บังคับบัญชา",
                "任务": "ภารกิจ",
                "训练": "การฝึก",
                "部队": "หน่วยทหาร",
                
                # 现代生活术语
                "鸡娃": "พ่อแม่เฮลิคอปเตอร์",
                "内卷": "การแข่งขันที่รุนแรง",
                "躺平": "การยอมแพ้",
                "打工人": "คนทำงาน",
                
                # 关系称谓
                "哥": "พี่ชาย",
                "姐": "พี่สาว",
                "老板": "เจ้านาย",
                "同事": "เพื่อนร่วมงาน",
                "朋友": "เพื่อน",
                "男朋友": "แฟน",
                "女朋友": "แฟน"
            },
            AsianLanguage.VIETNAMESE: {
                # 军事术语
                "参谋长": "tham mưu trưởng",
                "司令": "tư lệnh",
                "队长": "đội trưởng",
                "战友": "đồng đội",
                "长官": "sĩ quan",
                "任务": "nhiệm vụ",
                "训练": "huấn luyện",
                "部队": "bộ đội",
                
                # 现代生活术语
                "鸡娃": "cha mẹ trực thăng",
                "内卷": "cạnh tranh khốc liệt",
                "躺平": "nằm xuống",
                "打工人": "người lao động",
                
                # 关系称谓
                "哥": "anh",
                "姐": "chị",
                "老板": "sếp",
                "同事": "đồng nghiệp",
                "朋友": "bạn",
                "男朋友": "bạn trai",
                "女朋友": "bạn gái"
            },
            AsianLanguage.INDONESIAN: {
                # 军事术语
                "参谋长": "kepala staf",
                "司令": "komandan",
                "队长": "kapten",
                "战友": "rekan seperjuangan",
                "长官": "perwira",
                "任务": "misi",
                "训练": "latihan",
                "部队": "pasukan",
                
                # 现代生活术语
                "鸡娃": "orang tua helikopter",
                "内卷": "persaingan ketat",
                "躺平": "menyerah",
                "打工人": "pekerja",
                
                # 关系称谓
                "哥": "kakak laki-laki",
                "姐": "kakak perempuan",
                "老板": "bos",
                "同事": "rekan kerja",
                "朋友": "teman",
                "男朋友": "pacar",
                "女朋友": "pacar"
            },
            AsianLanguage.MALAY: {
                # 军事术语
                "参谋长": "ketua staf",
                "司令": "komander",
                "队长": "kapten",
                "战友": "rakan seperjuangan",
                "长官": "pegawai",
                "任务": "misi",
                "训练": "latihan",
                "部队": "pasukan",
                
                # 现代生活术语
                "鸡娃": "ibu bapa helikopter",
                "内卷": "persaingan sengit",
                "躺平": "menyerah",
                "打工人": "pekerja",
                
                # 关系称谓
                "哥": "abang",
                "姐": "kakak",
                "老板": "bos",
                "同事": "rakan sekerja",
                "朋友": "kawan",
                "男朋友": "teman lelaki",
                "女朋友": "teman wanita"
            }
        }
        
        # 文化适配规则
        self.cultural_adaptations = {
            CulturalContext.CONFUCIAN: {
                "hierarchy_emphasis": True,
                "age_respect": True,
                "family_values": True,
                "education_importance": True
            },
            CulturalContext.BUDDHIST: {
                "karma_concepts": True,
                "meditation_references": True,
                "temple_culture": True,
                "merit_making": True
            },
            CulturalContext.ISLAMIC: {
                "halal_concepts": True,
                "prayer_references": True,
                "mosque_culture": True,
                "religious_greetings": True
            },
            CulturalContext.THERAVADA: {
                "monk_respect": True,
                "temple_traditions": True,
                "royal_respect": True,
                "buddhist_calendar": True
            }
        }
        
        # 性能统计
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "language_distribution": {},
            "honorific_distribution": {},
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "error_count": 0
        }
        
        logger.info("亚洲语言翻译 Agent 群初始化完成", agent_id=self.agent_id)
    
    def translate(self, request: AsianTranslationRequest) -> AsianTranslationResult:
        """执行亚洲语言翻译"""
        start_time = datetime.now()
        
        try:
            # 验证请求
            if not self._validate_request(request):
                return AsianTranslationResult(
                    request_id=request.request_id,
                    success=False,
                    target_language=request.target_language,
                    error_message="翻译请求验证失败"
                )
            
            # 分析上下文
            context_info = self._analyze_context(request)
            
            # 确定敬语等级
            honorific_level = self._determine_honorific_level(request, context_info)
            
            # 获取术语映射
            terminology = self._get_terminology_mappings(request, context_info)
            
            # 执行翻译
            translated_text = self._perform_translation(request, honorific_level, terminology, context_info)
            
            # 应用文化适配
            adapted_text = self._apply_cultural_adaptations(translated_text, request, context_info)
            
            # 优化格式和排版
            optimized_text = self._optimize_formatting(adapted_text, request)
            
            # 质量评估
            quality_score = self._assess_translation_quality(
                request.subtitle_entry.text, optimized_text, request
            )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计信息
            self._update_performance_stats(request.target_language, honorific_level, quality_score, processing_time, True)
            
            result = AsianTranslationResult(
                request_id=request.request_id,
                success=True,
                target_language=request.target_language,
                translated_text=optimized_text,
                original_text=request.subtitle_entry.text,
                honorific_level_used=honorific_level,
                cultural_adaptations=context_info.get("cultural_adaptations", []),
                terminology_used=terminology,
                quality_score=quality_score,
                processing_time_ms=int(processing_time),
                confidence=quality_score,
                metadata={
                    "language_config": self.language_configs[request.target_language],
                    "context_analysis": context_info
                }
            )
            
            logger.debug("亚洲语言翻译完成", 
                        request_id=request.request_id,
                        target_language=request.target_language.value,
                        honorific_level=honorific_level.value if honorific_level else None,
                        quality_score=quality_score,
                        processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_stats(request.target_language, None, 0.0, processing_time, False)
            
            logger.error("亚洲语言翻译失败", 
                        request_id=request.request_id,
                        target_language=request.target_language.value,
                        error=str(e))
            
            return AsianTranslationResult(
                request_id=request.request_id,
                success=False,
                target_language=request.target_language,
                original_text=request.subtitle_entry.text,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def _validate_request(self, request: AsianTranslationRequest) -> bool:
        """验证翻译请求"""
        if not request.subtitle_entry or not request.subtitle_entry.text:
            return False
        
        if not request.project_id:
            return False
        
        if request.target_language not in self.language_configs:
            return False
        
        return True
    
    def _analyze_context(self, request: AsianTranslationRequest) -> Dict[str, Any]:
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
    
    def _determine_honorific_level(self, request: AsianTranslationRequest, 
                                 context_info: Dict[str, Any]) -> Optional[HonorificLevel]:
        """确定敬语等级"""
        # 如果请求中指定了敬语等级，优先使用
        if request.honorific_level:
            return request.honorific_level
        
        # 检查目标语言是否支持敬语系统
        lang_config = self.language_configs[request.target_language]
        if not lang_config.get("honorific_system", False):
            return None
        
        # 基于上下文信息推断敬语等级
        relationship_info = context_info.get("relationship_info", {})
        speaker_info = context_info.get("speaker_info", {})
        
        # 获取关系信息
        relationship_summary = relationship_info.get("relationship_summary", {})
        formality = relationship_summary.get("formality", "medium")
        relationship_type = relationship_summary.get("relationship_type", "neutral")
        
        # 获取说话人信息
        speaker_data = speaker_info.get("speaker_info", {})
        profession = speaker_data.get("profession", "")
        
        # 基于职业确定敬语等级
        if profession in ["军官", "司令", "参谋长"]:
            return HonorificLevel.VERY_HIGH
        
        # 基于关系类型确定敬语等级
        if relationship_type in ["superior_subordinate", "elder_younger"]:
            return HonorificLevel.HIGH
        elif relationship_type in ["romantic", "family", "close_friend"]:
            return HonorificLevel.LOW
        
        # 基于正式程度确定敬语等级
        if formality == "very_high":
            return HonorificLevel.VERY_HIGH
        elif formality == "high":
            return HonorificLevel.HIGH
        elif formality == "low":
            return HonorificLevel.LOW
        else:
            return HonorificLevel.MEDIUM
    
    def _get_terminology_mappings(self, request: AsianTranslationRequest, 
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
    
    def _perform_translation(self, request: AsianTranslationRequest, 
                           honorific_level: Optional[HonorificLevel],
                           terminology: Dict[str, str],
                           context_info: Dict[str, Any]) -> str:
        """执行核心翻译"""
        text = request.subtitle_entry.text
        
        # 应用术语替换
        for chinese_term, target_term in terminology.items():
            text = text.replace(chinese_term, f"[{target_term}]")
        
        # 构建翻译提示
        system_prompt = self._build_translation_prompt(request.target_language, honorific_level)
        
        # 添加上下文信息到提示中
        context_prompt = self._build_context_prompt(context_info, request.target_language)
        
        # 构建完整的翻译提示
        full_prompt = f"""
{system_prompt}

Context Information:
{context_prompt}

Terminology to use:
{json.dumps(terminology, ensure_ascii=False, indent=2)}

Please translate the following Chinese text to {self.language_configs[request.target_language]['name']}:
"{text}"

Requirements:
- Maintain the original meaning and tone
- Use the provided terminology consistently
- Apply appropriate honorific level if applicable
- Ensure cultural appropriateness
- Keep the translation natural and fluent
"""
        
        # 这里应该调用实际的翻译模型（如Claude）
        # 为了演示，我们提供一个简化的翻译逻辑
        translated_text = self._simulate_translation(text, request.target_language, honorific_level, terminology)
        
        # 清理术语标记
        for chinese_term, target_term in terminology.items():
            translated_text = translated_text.replace(f"[{target_term}]", target_term)
        
        return translated_text
    
    def _build_translation_prompt(self, target_language: AsianLanguage, 
                                honorific_level: Optional[HonorificLevel]) -> str:
        """构建翻译提示"""
        lang_name = self.language_configs[target_language]["name"]
        
        base_prompt = f"""
You are a professional {lang_name} translator specializing in Chinese-to-{lang_name} translation.
Focus on:
- Maintaining accurate meaning and cultural nuances
- Using natural {lang_name} expressions
- Ensuring appropriate formality levels
- Adapting cultural references when necessary
"""
        
        # 添加敬语系统提示
        if honorific_level and target_language in self.honorific_prompts:
            honorific_prompt = self.honorific_prompts[target_language].get(honorific_level, "")
            if honorific_prompt:
                base_prompt += f"\n\nHonorific Language Guidelines:\n{honorific_prompt}"
        
        return base_prompt
    
    def _build_context_prompt(self, context_info: Dict[str, Any], 
                            target_language: AsianLanguage) -> str:
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
            context_parts.append(f"Cultural context: {cultural_context.value}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available"
    
    def _simulate_translation(self, text: str, target_language: AsianLanguage,
                            honorific_level: Optional[HonorificLevel],
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
        
        # 根据敬语等级调整（简化实现）
        if honorific_level and target_language == AsianLanguage.JAPANESE:
            if honorific_level in [HonorificLevel.HIGH, HonorificLevel.VERY_HIGH]:
                # 添加敬语标记
                result = result + "です"
        elif honorific_level and target_language == AsianLanguage.KOREAN:
            if honorific_level in [HonorificLevel.HIGH, HonorificLevel.VERY_HIGH]:
                # 添加敬语标记
                result = result + "습니다"
        
        # 如果没有找到合适的翻译，返回原文加上标记
        if result == text:
            lang_name = self.language_configs[target_language]["name"]
            result = f"[{lang_name} translation needed: {text}]"
        
        return result
    
    def _apply_cultural_adaptations(self, text: str, request: AsianTranslationRequest, 
                                  context_info: Dict[str, Any]) -> str:
        """应用文化适配"""
        if not request.adapt_cultural_references:
            return text
        
        adapted_text = text
        
        # 获取文化背景
        lang_config = self.language_configs[request.target_language]
        cultural_context = lang_config.get("cultural_context")
        
        if cultural_context:
            # 应用文化特定的适配
            adaptations = self.cultural_adaptations.get(cultural_context, {})
            
            if cultural_context == CulturalContext.CONFUCIAN:
                # 儒家文化圈的适配
                adapted_text = self._adapt_confucian_culture(adapted_text, request.target_language)
            elif cultural_context == CulturalContext.ISLAMIC:
                # 伊斯兰文化的适配
                adapted_text = self._adapt_islamic_culture(adapted_text, request.target_language)
            elif cultural_context == CulturalContext.THERAVADA:
                # 上座部佛教文化的适配
                adapted_text = self._adapt_theravada_culture(adapted_text, request.target_language)
        
        return adapted_text
    
    def _adapt_confucian_culture(self, text: str, target_language: AsianLanguage) -> str:
        """适配儒家文化"""
        # 处理家庭关系和等级制度
        if target_language == AsianLanguage.JAPANESE:
            # 日语特定的文化适配
            text = text.replace("父亲", "お父さん")
            text = text.replace("母亲", "お母さん")
        elif target_language == AsianLanguage.KOREAN:
            # 韩语特定的文化适配
            text = text.replace("父亲", "아버지")
            text = text.replace("母亲", "어머니")
        
        return text
    
    def _adapt_islamic_culture(self, text: str, target_language: AsianLanguage) -> str:
        """适配伊斯兰文化"""
        # 处理宗教相关的概念
        if target_language in [AsianLanguage.INDONESIAN, AsianLanguage.MALAY]:
            text = text.replace("上帝", "Allah")
            text = text.replace("祈祷", "sholat" if target_language == AsianLanguage.INDONESIAN else "solat")
        
        return text
    
    def _adapt_theravada_culture(self, text: str, target_language: AsianLanguage) -> str:
        """适配上座部佛教文化"""
        # 处理佛教相关的概念
        if target_language == AsianLanguage.THAI:
            text = text.replace("和尚", "พระ")
            text = text.replace("寺庙", "วัด")
        
        return text
    
    def _optimize_formatting(self, text: str, request: AsianTranslationRequest) -> str:
        """优化格式和排版"""
        lang_config = self.language_configs[request.target_language]
        
        # 检查长度限制
        max_length_ratio = lang_config.get("max_length_ratio", 1.3)
        original_length = len(request.subtitle_entry.text)
        max_length = int(original_length * max_length_ratio)
        
        # 如果超长，进行压缩
        if len(text) > max_length:
            text = self._compress_text(text, max_length, request.target_language)
        
        # 语言特定的格式优化
        text = self._apply_language_specific_formatting(text, request.target_language)
        
        return text
    
    def _compress_text(self, text: str, max_length: int, target_language: AsianLanguage) -> str:
        """压缩文本长度"""
        if len(text) <= max_length:
            return text
        
        # 语言特定的压缩策略
        if target_language in [AsianLanguage.JAPANESE, AsianLanguage.KOREAN]:
            # 对于汉字文化圈，可以使用更简洁的表达
            compressed = text
        else:
            # 对于其他语言，使用通用压缩策略
            compressed = text
        
        # 如果还是太长，截断并添加省略号
        if len(compressed) > max_length:
            compressed = compressed[:max_length-3] + "..."
        
        return compressed
    
    def _apply_language_specific_formatting(self, text: str, target_language: AsianLanguage) -> str:
        """应用语言特定的格式化"""
        # 清理多余空格
        text = " ".join(text.split())
        
        # 语言特定的格式化
        if target_language == AsianLanguage.THAI:
            # 泰语不使用空格分词，但保留标点符号前后的空格
            pass
        elif target_language in [AsianLanguage.JAPANESE, AsianLanguage.KOREAN]:
            # 日语和韩语的特殊格式化
            pass
        
        return text
    
    def _assess_translation_quality(self, original_text: str, translated_text: str, 
                                  request: AsianTranslationRequest) -> float:
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
        
        # 计算综合质量分数
        weights = {
            "length_quality": 0.2,
            "terminology_consistency": 0.3,
            "cultural_adaptation": 0.2,
            "completeness": 0.3
        }
        
        overall_score = sum(
            quality_factors[factor] * weight 
            for factor, weight in weights.items()
        )
        
        return overall_score
    
    def _assess_length_quality(self, original_text: str, translated_text: str, 
                             target_language: AsianLanguage) -> float:
        """评估长度质量"""
        if not original_text:
            return 0.0
        
        lang_config = self.language_configs[target_language]
        max_ratio = lang_config.get("max_length_ratio", 1.3)
        
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
                                      request: AsianTranslationRequest) -> float:
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
                                  request: AsianTranslationRequest) -> float:
        """评估文化适配性"""
        # 简化的文化适配评估
        # 实际实现中可能需要更复杂的文化分析
        return 0.8
    
    def _assess_completeness(self, original_text: str, translated_text: str) -> float:
        """评估完整性"""
        if not translated_text.strip():
            return 0.0
        
        if "translation needed:" in translated_text.lower():
            return 0.3
        
        return 1.0
    
    def _update_performance_stats(self, target_language: AsianLanguage, 
                                honorific_level: Optional[HonorificLevel],
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
        
        # 更新敬语分布
        if honorific_level:
            honorific_name = honorific_level.value
            if honorific_name not in self.performance_stats["honorific_distribution"]:
                self.performance_stats["honorific_distribution"][honorific_name] = 0
            self.performance_stats["honorific_distribution"][honorific_name] += 1
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表"""
        return [
            {
                "code": lang.value,
                "name": config["name"],
                "script": config["script"],
                "honorific_system": config["honorific_system"],
                "cultural_context": config["cultural_context"].value
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
            "honorific_levels": [level.value for level in HonorificLevel],
            "cultural_contexts": [context.value for context in CulturalContext]
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "language_distribution": {},
            "honorific_distribution": {},
            "average_quality_score": 0.0,
            "average_processing_time": 0.0,
            "error_count": 0
        }
        logger.info("性能统计已重置")


# 全局亚洲语言翻译 Agent 实例
asian_translation_agent = AsianTranslationAgent()


def get_asian_translation_agent() -> AsianTranslationAgent:
    """获取亚洲语言翻译 Agent 实例"""
    return asian_translation_agent


# 便捷函数
def translate_to_asian_language(project_id: str, subtitle_entry: SubtitleEntry,
                              target_language: AsianLanguage,
                              honorific_level: Optional[HonorificLevel] = None,
                              context_window: Optional[List[SubtitleEntry]] = None) -> AsianTranslationResult:
    """便捷的亚洲语言翻译函数"""
    agent = get_asian_translation_agent()
    
    request = AsianTranslationRequest(
        request_id=str(uuid.uuid4()),
        project_id=project_id,
        subtitle_entry=subtitle_entry,
        target_language=target_language,
        honorific_level=honorific_level,
        context_window=context_window
    )
    
    return agent.translate(request)