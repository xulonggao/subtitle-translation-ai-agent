#!/usr/bin/env python3
"""
基于Strands SDK的字幕翻译Agent
整合所有翻译精确度优化和工具集
"""
import json
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime

# Strands Agent SDK imports
from strands import Agent
from strands.models import BedrockModel

# 导入工具集
from enhanced_tools import (
    parse_srt_file,
    analyze_story_context,
    translate_with_context,
    validate_translation_quality,
    export_translated_srt,
    # 高级功能工具
    enhance_creative_translation,
    localize_cultural_terms,
    analyze_translation_quality_advanced,
    check_translation_consistency,
    optimize_subtitle_timing,
    manage_terminology
)

logger = structlog.get_logger()

class SubtitleTranslationAgent:
    """
    基于Strands SDK的字幕翻译Agent
    整合所有翻译精确度优化功能
    """
    
    def __init__(self, 
                 primary_model_id: str = "us.anthropic.claude-opus-4-20250514-v1:0",
                 fallback_model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                 region: str = "us-west-2"):
        """
        初始化字幕翻译Agent
        
        Args:
            primary_model_id: 主要模型ID (Claude 4 Sonnet)
            fallback_model_id: 备用模型ID (Claude 3.7 Sonnet)
            region: AWS区域
        """
        self.primary_model_id = primary_model_id
        self.fallback_model_id = fallback_model_id
        self.region = region
        
        # 创建模型实例
        self.primary_model = BedrockModel()
        self.primary_model.update_config(model_id=primary_model_id)
        
        self.fallback_model = BedrockModel()
        self.fallback_model.update_config(model_id=fallback_model_id)
        
        # 系统提示符
        self.system_prompt = self._create_system_prompt()
        
        # 语言特定配置
        self.language_configs = self._initialize_language_configs()
        
        # 翻译策略配置
        self.translation_strategies = self._initialize_translation_strategies()
        
        # 文化适配词典
        self.cultural_adaptations = self._initialize_cultural_adaptations()
        
        # 创建Strands Agent
        self.agent = Agent(
            model=self.primary_model,
            tools=[
                # 基础工具
                parse_srt_file,
                analyze_story_context,
                translate_with_context,
                validate_translation_quality,
                export_translated_srt,
                # 高级功能工具
                enhance_creative_translation,
                localize_cultural_terms,
                analyze_translation_quality_advanced,
                check_translation_consistency,
                optimize_subtitle_timing,
                manage_terminology
            ],
            system_prompt=self.system_prompt,
            name="SubtitleTranslationAgent"
        )
        
        logger.info("字幕翻译Agent初始化完成", 
                   primary_model=self.primary_model.get_config(),
                   fallback_model=self.fallback_model.get_config())
    
    def _create_system_prompt(self) -> str:
        """创建专业的系统提示符"""
        return """# 专业字幕翻译Agent - 多语言文化适配专家

你是一个世界级的字幕翻译专家，专门处理影视剧字幕的跨文化翻译，具备深度的语言学知识和文化敏感性。

## 🎯 核心身份与专长

### 专业定位
- **字幕翻译专家**：精通中文与10种目标语言的专业转换
- **文化桥梁建设者**：深度理解东西方文化差异，擅长文化概念本土化
- **影视剧语言专家**：熟悉军事、现代都市、浪漫爱情、悬疑推理等各类剧集的语言特点
- **敬语系统专家**：精通日韩泰越等语言的复杂敬语体系

### 核心能力矩阵
- **语言转换精度**：99%+ 准确率的专业术语和文化概念翻译
- **上下文理解**：基于人物关系、故事背景的深度语境分析
- **文化适配引擎**：处理"鸡娃"、"内卷"、"躺平"等现代网络词汇的跨文化转换
- **创作性翻译**：根据场景情感调整翻译风格，保持艺术性和观赏性

## 🌍 多语言翻译策略矩阵

### 🇺🇸 英语翻译策略 (English)
**文化背景**: 西方个人主义文化，直接表达习惯
**翻译重点**:
- 避免中式英语表达，使用地道的英语习语
- 处理中西方思维差异：集体主义 → 个人主义表达
- 军事术语使用NATO标准，职场术语符合美式商业文化
- 情感表达更加直接，减少含蓄表达
**敬语处理**: 使用正式/非正式语域区分，避免过度礼貌
**文化适配**: "面子"→"reputation/dignity", "关系"→"connections/networking"

### 🇯🇵 日语翻译策略 (Japanese)
**文化背景**: 等级社会，敬语文化，含蓄表达
**翻译重点**:
- **敬语系统精确应用**：
  - 尊敬语（そんけいご）：对上级、长辈、客户
  - 谦让语（けんじょうご）：谦逊表达自己的行为
  - 丁宁语（ていねいご）：礼貌的基本形式
- 汉字文化圈术语保持一致性：军官→軍官、医生→医師
- 情感表达更加含蓄，使用"ちょっと"等缓和表达
**年龄/地位判断**:
- 上司对部下：命令形、敬语省略
- 部下对上司：完全敬语形式
- 同辈：丁宁语或普通语
**文化适配**: "加班"→"残業", "内卷"→"過当競争", "躺平"→"諦め主義"

### 🇰🇷 韩语翻译策略 (Korean)
**文化背景**: 儒家文化，严格的年龄等级制度
**翻译重点**:
- **敬语等级系统**：
  - 아주높임 (最高敬语)：对长辈、上司
  - 높임 (敬语)：对年长者、客户
  - 보통 (普通语)：对同辈
  - 낮춤 (下称)：对晚辈
- 年龄关系判断：형/누나/오빠/언니 系统
- 职场等级：선배/후배 关系体现
**文化适配**: "鸡娃"→"교육열", "内卷"→"과도한 경쟁", "关系户"→"인맥"

### 🇹🇭 泰语翻译策略 (Thai)
**文化背景**: 佛教文化，王室敬语，社会等级
**翻译重点**:
- **敬语系统**：
  - ราชาศัพท์ (王室敬语)：极度正式场合
  - ภาษาสุภาพ (礼貌语)：正式交流
  - ภาษาพูด (口语)：日常对话
- 佛教概念融入：业力、功德等概念
- 社会地位体现：พี่/น้อง (兄姐/弟妹) 系统
**文化适配**: "面子"→"หน้า", "关系"→"ความสัมพันธ์"

### 🇻🇳 越南语翻译策略 (Vietnamese)
**文化背景**: 儒家文化+法式影响，家族等级制度
**翻译重点**:
- **称谓系统**：anh/chị/em 复杂关系网络
- 法式礼貌用语融合
- 家族关系重视：bác/chú/cô/dì 系统
**文化适配**: 中越文化相似性高，保持儒家文化概念

### 🇮🇩 印尼语翻译策略 (Indonesian)
**文化背景**: 伊斯兰文化主导，多元宗教社会
**翻译重点**:
- 伊斯兰文化敏感性：避免猪肉、酒精等敏感内容
- 宗教礼貌用语：Assalamualaikum 等
- 多元文化包容性体现
**文化适配**: "命运"→"takdir", "缘分"→"jodoh"

### 🇲🇾 马来语翻译策略 (Malay)
**文化背景**: 伊斯兰文化+马来传统文化
**翻译重点**:
- 伊斯兰价值观体现
- 马来传统礼仪：budi/balas budi 概念
- 多元种族和谐表达
**文化适配**: 类似印尼语但更保守

### 🇪🇸 西班牙语翻译策略 (Spanish)
**文化背景**: 天主教文化，拉丁热情文化
**翻译重点**:
- **地区差异处理**：
  - 欧洲西班牙语：更正式，使用vosotros
  - 拉美西班牙语：更亲近，使用ustedes
- 性别语法一致性：形容词、冠词变位
- 天主教文化概念：圣人、节日等
**文化适配**: "面子"→"dignidad", "关系"→"conexiones"

### 🇵🇹 葡萄牙语翻译策略 (Portuguese)
**文化背景**: 天主教文化，巴西vs葡萄牙差异
**翻译重点**:
- **地区差异**：
  - 巴西葡语：更开放，使用você
  - 欧洲葡语：更正式，保持tu/você区分
- 性别语法处理
**文化适配**: 类似西班牙语策略

### 🇸🇦 阿拉伯语翻译策略 (Arabic)
**文化背景**: 伊斯兰文化，从右到左书写
**翻译重点**:
- **宗教敏感性最高**：
  - 避免酒精、猪肉、赌博等内容
  - 男女关系描述需谨慎
  - 宗教节日和习俗尊重
- 从右到左文本方向处理
- 阿拉伯语方言vs标准阿拉伯语选择
**文化适配**: "命运"→"قدر", "缘分"→"نصيب"

## 🎨 创作性翻译适配引擎

### 场景情感分析
- **紧张/悬疑场景**：使用短句，增强节奏感
- **浪漫/温馨场景**：使用柔和表达，增加情感色彩
- **军事/动作场景**：使用专业术语，体现权威性
- **喜剧/轻松场景**：适当使用俏皮话，保持幽默感

### 人物性格适配
- **权威角色**：使用正式语言，体现威严
- **年轻角色**：使用现代表达，贴近年轻人语言
- **知识分子**：使用文雅表达，体现教养
- **普通民众**：使用朴实语言，贴近生活

## 📊 五维质量评估体系

### 1. 翻译准确性 (30%) - 核心指标
- **专业术语准确率**：军事、医学、法律术语零错误
- **文化概念转换**：现代网络词汇本土化成功率
- **语义完整性**：原文信息无遗漏、无曲解

### 2. 语言流畅性 (25%) - 观感指标  
- **目标语言地道性**：符合母语者表达习惯
- **语法正确性**：零语法错误，语序自然
- **阅读流畅度**：无卡顿感，一气呵成

### 3. 一致性维护 (20%) - 连贯指标
- **术语统一性**：人名、地名、职位翻译前后一致
- **人物性格一致性**：说话风格贯穿始终
- **敬语等级一致性**：人物关系体现准确

### 4. 文化适配性 (15%) - 本土化指标
- **文化概念本土化**：避免文化冲突和误解
- **价值观适配**：符合目标文化价值观
- **受众接受度**：目标受众理解无障碍

### 5. 时间节奏控制 (10%) - 技术指标
- **字符密度控制**：2秒内10-15字标准
- **阅读速度适配**：不同语言字符密度调整
- **显示时长优化**：确保充足阅读时间

## 🛠️ 专业工作流程

### 阶段一：深度解析 (Context Analysis)
1. **SRT文件解析**：时间码、说话人、文本结构分析
2. **故事上下文提取**：人物关系网络、文化背景、剧集类型
3. **语言特征识别**：专业术语、文化词汇、情感色彩

### 阶段二：智能翻译 (Contextual Translation)
1. **目标语言策略选择**：根据语言特点选择翻译策略
2. **敬语系统应用**：基于人物关系确定敬语等级
3. **文化适配处理**：现代词汇本土化转换
4. **创作性优化**：根据场景调整翻译风格

### 阶段三：质量保证 (Quality Assurance)
1. **五维质量评估**：全面质量指标检查
2. **一致性验证**：术语、人物、风格一致性检查
3. **文化敏感性审查**：避免文化冲突和误解
4. **时间节奏优化**：字符密度和显示时长调整

### 阶段四：标准化输出 (Standardized Export)
1. **格式规范化**：标准SRT格式输出
2. **编码统一**：UTF-8编码确保兼容性
3. **元数据添加**：说话人、翻译注释等信息
4. **质量报告生成**：详细的翻译质量分析报告

## 🚨 关键注意事项

### 文化敏感性原则
- **宗教敏感性**：伊斯兰、佛教、基督教文化禁忌
- **政治敏感性**：避免政治立场和争议话题
- **性别敏感性**：尊重不同文化的性别观念
- **年龄敏感性**：体现不同文化的年龄等级制度

### 专业标准坚持
- **零容忍错误**：专业术语、人名地名绝对准确
- **一致性要求**：整部剧集翻译风格统一
- **时效性保证**：在质量前提下提高翻译效率
- **反馈响应**：积极响应用户反馈，持续优化

现在，我已准备好为您提供世界级的专业字幕翻译服务。请告诉我您的翻译需求，我将运用最适合的语言策略和文化适配方案为您服务。"""
    
    def _initialize_language_configs(self) -> Dict[str, Dict[str, Any]]:
        """初始化语言特定配置"""
        return {
            "en": {
                "name": "English",
                "family": "Germanic",
                "writing_direction": "ltr",
                "character_density": 1.0,
                "honorific_system": False,
                "cultural_context": "Western individualism",
                "formal_register": "formal/informal distinction",
                "religious_sensitivity": "low",
                "gender_grammar": False
            },
            "ja": {
                "name": "Japanese",
                "family": "Japonic",
                "writing_direction": "ltr",
                "character_density": 0.7,
                "honorific_system": True,
                "honorific_levels": ["sonkeigo", "kenjougo", "teineigo"],
                "cultural_context": "Hierarchical society",
                "formal_register": "complex honorific system",
                "religious_sensitivity": "medium",
                "gender_grammar": False
            },
            "ko": {
                "name": "Korean",
                "family": "Koreanic", 
                "writing_direction": "ltr",
                "character_density": 0.8,
                "honorific_system": True,
                "honorific_levels": ["아주높임", "높임", "보통", "낮춤"],
                "cultural_context": "Confucian hierarchy",
                "formal_register": "age-based honorifics",
                "religious_sensitivity": "medium",
                "gender_grammar": False
            },
            "th": {
                "name": "Thai",
                "family": "Tai-Kadai",
                "writing_direction": "ltr",
                "character_density": 0.6,
                "honorific_system": True,
                "honorific_levels": ["ราชาศัพท์", "ภาษาสุภาพ", "ภาษาพูด"],
                "cultural_context": "Buddhist monarchy",
                "formal_register": "royal/polite/casual",
                "religious_sensitivity": "high",
                "gender_grammar": False
            },
            "vi": {
                "name": "Vietnamese",
                "family": "Austroasiatic",
                "writing_direction": "ltr", 
                "character_density": 0.9,
                "honorific_system": True,
                "honorific_levels": ["anh/chị/em system"],
                "cultural_context": "Confucian + French influence",
                "formal_register": "kinship-based",
                "religious_sensitivity": "medium",
                "gender_grammar": False
            },
            "id": {
                "name": "Indonesian",
                "family": "Austronesian",
                "writing_direction": "ltr",
                "character_density": 1.1,
                "honorific_system": False,
                "cultural_context": "Islamic majority",
                "formal_register": "formal/informal",
                "religious_sensitivity": "high",
                "gender_grammar": False
            },
            "ms": {
                "name": "Malay",
                "family": "Austronesian",
                "writing_direction": "ltr",
                "character_density": 1.1,
                "honorific_system": False,
                "cultural_context": "Islamic + Malay tradition",
                "formal_register": "formal/informal",
                "religious_sensitivity": "high",
                "gender_grammar": False
            },
            "es": {
                "name": "Spanish",
                "family": "Romance",
                "writing_direction": "ltr",
                "character_density": 1.2,
                "honorific_system": False,
                "cultural_context": "Catholic Latin culture",
                "formal_register": "tú/usted distinction",
                "religious_sensitivity": "medium",
                "gender_grammar": True,
                "regional_variants": ["European", "Latin American"]
            },
            "pt": {
                "name": "Portuguese", 
                "family": "Romance",
                "writing_direction": "ltr",
                "character_density": 1.2,
                "honorific_system": False,
                "cultural_context": "Catholic Lusophone",
                "formal_register": "tu/você distinction",
                "religious_sensitivity": "medium",
                "gender_grammar": True,
                "regional_variants": ["European", "Brazilian"]
            },
            "ar": {
                "name": "Arabic",
                "family": "Semitic",
                "writing_direction": "rtl",
                "character_density": 0.8,
                "honorific_system": False,
                "cultural_context": "Islamic culture",
                "formal_register": "formal/informal",
                "religious_sensitivity": "very_high",
                "gender_grammar": True,
                "special_considerations": ["right_to_left", "religious_content"]
            }
        }
    
    def _initialize_translation_strategies(self) -> Dict[str, Dict[str, Any]]:
        """初始化翻译策略配置"""
        return {
            "accuracy_optimization": {
                "terminology_consistency": True,
                "context_awareness": True,
                "cultural_adaptation": True,
                "professional_terms": True
            },
            "fluency_optimization": {
                "natural_expression": True,
                "grammar_correction": True,
                "idiomatic_usage": True,
                "reading_flow": True
            },
            "cultural_adaptation": {
                "modern_slang_localization": True,
                "religious_sensitivity": True,
                "social_hierarchy_respect": True,
                "value_system_alignment": True
            },
            "timing_optimization": {
                "character_density_control": True,
                "reading_speed_adaptation": True,
                "display_duration_optimization": True,
                "rhythm_preservation": True
            },
            "creative_adaptation": {
                "scene_emotion_matching": True,
                "character_personality_consistency": True,
                "genre_style_adaptation": True,
                "artistic_expression_preservation": True
            }
        }
    
    def _initialize_cultural_adaptations(self) -> Dict[str, Dict[str, str]]:
        """初始化文化适配词典"""
        return {
            "modern_chinese_slang": {
                "鸡娃": {
                    "en": "helicopter parenting",
                    "ja": "教育熱心",
                    "ko": "교육열",
                    "th": "การเลี้ยงดูแบบเข้มงวด",
                    "vi": "nuôi dạy con quá mức",
                    "id": "mendidik anak secara berlebihan",
                    "ms": "mendidik anak terlalu ketat",
                    "es": "crianza intensiva",
                    "pt": "educação intensiva",
                    "ar": "التربية المفرطة"
                },
                "内卷": {
                    "en": "rat race / cutthroat competition",
                    "ja": "過当競争",
                    "ko": "과도한 경쟁",
                    "th": "การแข่งขันที่รุนแรง",
                    "vi": "cạnh tranh khốc liệt",
                    "id": "persaingan yang tidak sehat",
                    "ms": "persaingan yang tidak sihat",
                    "es": "competencia despiadada",
                    "pt": "competição acirrada",
                    "ar": "المنافسة الشرسة"
                },
                "躺平": {
                    "en": "giving up / lying flat",
                    "ja": "諦め主義",
                    "ko": "포기주의",
                    "th": "การยอมแพ้",
                    "vi": "thái độ bỏ cuộc",
                    "id": "sikap menyerah",
                    "ms": "sikap mengalah",
                    "es": "rendirse ante la vida",
                    "pt": "desistir da luta",
                    "ar": "الاستسلام للواقع"
                },
                "社畜": {
                    "en": "corporate slave",
                    "ja": "社畜",
                    "ko": "회사 노예",
                    "th": "ทาสบริษัท",
                    "vi": "nô lệ công ty",
                    "id": "budak korporat",
                    "ms": "hamba syarikat",
                    "es": "esclavo corporativo",
                    "pt": "escravo corporativo",
                    "ar": "عبد الشركة"
                }
            },
            "relationship_terms": {
                "面子": {
                    "en": "face / reputation",
                    "ja": "面子",
                    "ko": "체면",
                    "th": "หน้า",
                    "vi": "thể diện",
                    "id": "muka / harga diri",
                    "ms": "muka / maruah",
                    "es": "dignidad",
                    "pt": "dignidade",
                    "ar": "ماء الوجه"
                },
                "关系": {
                    "en": "connections / networking",
                    "ja": "人脈",
                    "ko": "인맥",
                    "th": "ความสัมพันธ์",
                    "vi": "mối quan hệ",
                    "id": "hubungan",
                    "ms": "hubungan",
                    "es": "conexiones",
                    "pt": "conexões",
                    "ar": "العلاقات"
                }
            }
        }
    
    def get_language_strategy(self, target_language: str) -> Dict[str, Any]:
        """获取特定语言的翻译策略"""
        config = self.language_configs.get(target_language, {})
        strategy = {
            "language_config": config,
            "translation_approach": self._get_translation_approach(target_language),
            "cultural_adaptations": self._get_cultural_adaptations(target_language),
            "quality_weights": self._get_quality_weights(target_language)
        }
        return strategy
    
    def _get_translation_approach(self, target_language: str) -> Dict[str, str]:
        """获取语言特定的翻译方法"""
        approaches = {
            "en": "Direct and natural expression, avoid Chinglish",
            "ja": "Honorific system precision, cultural nuance preservation",
            "ko": "Age-hierarchy respect, Confucian value alignment",
            "th": "Buddhist cultural sensitivity, royal language awareness",
            "vi": "Kinship-based honorifics, French influence integration",
            "id": "Islamic cultural sensitivity, multi-religious tolerance",
            "ms": "Islamic values, Malay traditional respect",
            "es": "Regional variant consideration, Catholic cultural context",
            "pt": "European vs Brazilian distinction, gender agreement",
            "ar": "Islamic sensitivity, right-to-left formatting, religious respect"
        }
        return {"approach": approaches.get(target_language, "Standard translation approach")}
    
    def _get_cultural_adaptations(self, target_language: str) -> List[str]:
        """获取文化适配建议"""
        adaptations = {
            "en": ["Individualism emphasis", "Direct communication", "Western values"],
            "ja": ["Hierarchy respect", "Indirect communication", "Group harmony"],
            "ko": ["Age-based respect", "Confucian values", "Social hierarchy"],
            "th": ["Buddhist concepts", "Royal respect", "Social harmony"],
            "vi": ["Family values", "Confucian influence", "French cultural elements"],
            "id": ["Islamic values", "Religious sensitivity", "Multi-cultural tolerance"],
            "ms": ["Islamic principles", "Malay traditions", "Respect for elders"],
            "es": ["Catholic influence", "Family importance", "Regional variations"],
            "pt": ["Catholic culture", "Brazilian warmth vs European formality"],
            "ar": ["Islamic principles", "Religious sensitivity", "Traditional values"]
        }
        return adaptations.get(target_language, ["Standard cultural considerations"])
    
    def _get_quality_weights(self, target_language: str) -> Dict[str, float]:
        """获取语言特定的质量权重"""
        # 根据语言特点调整质量评估权重
        if target_language in ["ja", "ko", "th", "vi"]:
            # 敬语系统语言更重视一致性
            return {
                "accuracy": 0.25,
                "fluency": 0.20,
                "consistency": 0.30,  # 提高一致性权重
                "cultural_adaptation": 0.20,
                "timing": 0.05
            }
        elif target_language in ["id", "ms", "ar"]:
            # 宗教敏感语言更重视文化适配
            return {
                "accuracy": 0.25,
                "fluency": 0.20,
                "consistency": 0.15,
                "cultural_adaptation": 0.30,  # 提高文化适配权重
                "timing": 0.10
            }
        else:
            # 标准权重
            return {
                "accuracy": 0.30,
                "fluency": 0.25,
                "consistency": 0.20,
                "cultural_adaptation": 0.15,
                "timing": 0.10
            }
    
    def translate_subtitle_file(self, 
                               srt_content: str, 
                               target_language: str,
                               additional_context: str = "",
                               translation_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        完整的字幕文件翻译流程
        
        Args:
            srt_content: SRT文件内容
            target_language: 目标语言代码
            additional_context: 额外的上下文信息
            translation_config: 翻译配置
            
        Returns:
            包含翻译结果和质量报告的字典
        """
        try:
            logger.info("开始字幕翻译流程", target_language=target_language)
            
            # 第一步：解析SRT文件
            logger.info("步骤1: 解析SRT文件")
            parse_result = self.agent(f"""
请使用parse_srt_file工具解析以下SRT内容，启用说话人检测：

{srt_content}
""")
            
            # 第二步：分析故事上下文
            logger.info("步骤2: 分析故事上下文")
            context_result = self.agent(f"""
请使用analyze_story_context工具分析故事上下文，分析深度设为"deep"：

解析结果：{parse_result.message}
额外上下文：{additional_context}
""")
            
            # 第三步：获取语言策略并执行翻译
            logger.info("步骤3: 获取语言策略", target_language=target_language)
            language_strategy = self.get_language_strategy(target_language)
            
            # 合并翻译配置
            enhanced_config = {
                **(translation_config or {}),
                "language_strategy": language_strategy,
                "cultural_adaptations": self.cultural_adaptations,
                "translation_strategies": self.translation_strategies
            }
            
            logger.info("步骤3: 执行翻译", target_language=target_language)
            config_json = json.dumps(enhanced_config)
            translate_result = self.agent(f"""
请使用translate_with_context工具进行翻译：

目标语言：{target_language}
解析结果：{parse_result.message}
故事上下文：{context_result.message}
增强翻译配置：{config_json}

请特别注意以下语言特定策略：
- 翻译方法：{language_strategy['translation_approach']['approach']}
- 文化适配：{', '.join(language_strategy['cultural_adaptations'])}
- 质量权重：{language_strategy['quality_weights']}
""")
            
            # 第四步：质量验证
            logger.info("步骤4: 质量验证")
            quality_weights = language_strategy['quality_weights']
            quality_result = self.agent(f"""
请使用validate_translation_quality工具验证翻译质量：

原始条目：{parse_result.message}
翻译结果：{translate_result.message}
目标语言：{target_language}
语言特定质量权重：{json.dumps(quality_weights)}
文化适配要求：{', '.join(language_strategy['cultural_adaptations'])}

请特别关注以下评估重点：
- 敬语系统准确性（如适用）
- 文化敏感词处理
- 专业术语一致性
- 目标语言地道性
""")
            
            # 第五步：导出SRT
            logger.info("步骤5: 导出SRT文件")
            export_config = {
                "include_speaker_names": True,
                "add_metadata": True,
                "validate_timing": True
            }
            export_result = self.agent(f"""
请使用export_translated_srt工具导出SRT文件：

翻译结果：{translate_result.message}
导出配置：{json.dumps(export_config)}
""")
            
            logger.info("字幕翻译流程完成")
            
            return {
                "success": True,
                "parse_result": parse_result.message,
                "context_analysis": context_result.message,
                "translation_result": translate_result.message,
                "quality_report": quality_result.message,
                "exported_srt": export_result.message,
                "target_language": target_language
            }
            
        except Exception as e:
            logger.error("字幕翻译流程失败", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def optimize_translation_strategy(self, 
                                    target_language: str,
                                    genre: str = "modern_drama",
                                    audience: str = "general") -> Dict[str, Any]:
        """
        根据剧集类型和目标受众优化翻译策略
        
        Args:
            target_language: 目标语言
            genre: 剧集类型 (military, romance, comedy, thriller, etc.)
            audience: 目标受众 (young, adult, family, etc.)
            
        Returns:
            优化后的翻译策略配置
        """
        base_strategy = self.get_language_strategy(target_language)
        
        # 根据剧集类型调整策略
        genre_adjustments = {
            "military": {
                "terminology_precision": "high",
                "formality_level": "formal",
                "cultural_sensitivity": "medium"
            },
            "romance": {
                "emotional_expression": "enhanced",
                "cultural_adaptation": "high",
                "formality_level": "casual"
            },
            "comedy": {
                "humor_preservation": "high",
                "cultural_localization": "high",
                "creative_freedom": "high"
            },
            "thriller": {
                "tension_preservation": "high",
                "pacing_control": "strict",
                "clarity_priority": "high"
            }
        }
        
        # 根据受众调整策略
        audience_adjustments = {
            "young": {
                "modern_slang_usage": "high",
                "cultural_references": "contemporary",
                "language_register": "casual"
            },
            "adult": {
                "professional_terminology": "standard",
                "cultural_depth": "full",
                "language_register": "balanced"
            },
            "family": {
                "content_sensitivity": "high",
                "language_simplicity": "medium",
                "cultural_universality": "high"
            }
        }
        
        optimized_strategy = {
            **base_strategy,
            "genre_optimization": genre_adjustments.get(genre, {}),
            "audience_optimization": audience_adjustments.get(audience, {}),
            "optimization_timestamp": datetime.now().isoformat()
        }
        
        logger.info("翻译策略优化完成", 
                   target_language=target_language,
                   genre=genre,
                   audience=audience)
        
        return optimized_strategy
    
    def batch_translate_multiple_languages(self,
                                         srt_content: str,
                                         target_languages: List[str],
                                         additional_context: str = "",
                                         optimization_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        批量多语言翻译
        
        Args:
            srt_content: SRT文件内容
            target_languages: 目标语言列表
            additional_context: 额外上下文
            optimization_config: 优化配置
            
        Returns:
            包含所有语言翻译结果的字典
        """
        results = {}
        
        logger.info("开始批量多语言翻译", target_languages=target_languages)
        
        for lang in target_languages:
            try:
                logger.info(f"翻译语言: {lang}")
                
                # 获取优化策略
                if optimization_config:
                    strategy = self.optimize_translation_strategy(
                        lang,
                        optimization_config.get("genre", "modern_drama"),
                        optimization_config.get("audience", "general")
                    )
                    translation_config = {"optimized_strategy": strategy}
                else:
                    translation_config = None
                
                # 执行翻译
                result = self.translate_subtitle_file(
                    srt_content=srt_content,
                    target_language=lang,
                    additional_context=additional_context,
                    translation_config=translation_config
                )
                
                results[lang] = result
                
                if result["success"]:
                    logger.info(f"语言 {lang} 翻译成功")
                else:
                    logger.error(f"语言 {lang} 翻译失败", error=result.get("error"))
                    
            except Exception as e:
                logger.error(f"语言 {lang} 翻译异常", error=str(e))
                results[lang] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # 生成批量翻译报告
        successful_langs = [lang for lang, result in results.items() if result.get("success")]
        failed_langs = [lang for lang, result in results.items() if not result.get("success")]
        
        batch_report = {
            "total_languages": len(target_languages),
            "successful_languages": len(successful_langs),
            "failed_languages": len(failed_langs),
            "success_rate": len(successful_langs) / len(target_languages) * 100,
            "successful_langs": successful_langs,
            "failed_langs": failed_langs,
            "batch_timestamp": datetime.now().isoformat()
        }
        
        results["batch_report"] = batch_report
        
        logger.info("批量多语言翻译完成", 
                   success_rate=f"{batch_report['success_rate']:.1f}%",
                   successful=len(successful_langs),
                   failed=len(failed_langs))
        
        return results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return {lang: config["name"] for lang, config in self.language_configs.items()}
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "name": self.agent.name,
            "version": "2.0.0",
            "description": "专业字幕翻译Agent - 多语言文化适配专家",
            "primary_model": self.primary_model.get_config(),
            "fallback_model": self.fallback_model.get_config(),
            "supported_languages": self.get_supported_languages(),
            "language_families": list(set(config.get("family") for config in self.language_configs.values())),
            "tools": [
                "parse_srt_file", "analyze_story_context", "translate_with_context", 
                "validate_translation_quality", "export_translated_srt",
                "enhance_creative_translation", "localize_cultural_terms", 
                "analyze_translation_quality_advanced", "check_translation_consistency",
                "optimize_subtitle_timing", "manage_terminology"
            ],
            "core_capabilities": [
                "SRT文件解析与说话人识别",
                "深度故事上下文分析",
                "10种语言专业翻译",
                "敬语系统精确处理",
                "文化适配与本土化",
                "五维质量评估体系",
                "创作性翻译适配",
                "批量多语言处理",
                "标准化SRT导出"
            ],
            "advanced_features": [
                "语言特定翻译策略",
                "文化敏感词智能处理",
                "现代网络词汇本土化",
                "剧集类型优化适配",
                "目标受众策略调整",
                "质量权重动态调整",
                "术语一致性管理",
                "时间节奏智能控制"
            ],
            "cultural_adaptations": {
                "modern_slang_terms": len(self.cultural_adaptations.get("modern_chinese_slang", {})),
                "relationship_terms": len(self.cultural_adaptations.get("relationship_terms", {})),
                "supported_cultural_contexts": [
                    "Western individualism", "Confucian hierarchy", "Buddhist culture",
                    "Islamic values", "Catholic culture", "Malay traditions"
                ]
            },
            "quality_standards": {
                "accuracy_target": "99%+",
                "fluency_standard": "Native-level",
                "consistency_requirement": "100%",
                "cultural_sensitivity": "High",
                "timing_compliance": "2s/10-15chars"
            },
            "honorific_systems": [
                lang for lang, config in self.language_configs.items() 
                if config.get("honorific_system", False)
            ],
            "religious_sensitive_languages": [
                lang for lang, config in self.language_configs.items()
                if config.get("religious_sensitivity") in ["high", "very_high"]
            ]
        }

def create_subtitle_translation_agent(**kwargs) -> SubtitleTranslationAgent:
    """
    创建字幕翻译Agent的工厂函数
    
    Args:
        **kwargs: Agent初始化参数
        
    Returns:
        SubtitleTranslationAgent实例
    """
    return SubtitleTranslationAgent(**kwargs)

if __name__ == "__main__":
    # 示例使用
    print("🎬 字幕翻译Agent初始化中...")
    
    agent = create_subtitle_translation_agent()
    
    print("✅ Agent初始化完成")
    print(f"📊 Agent信息:")
    info = agent.get_agent_info()
    for key, value in info.items():
        if isinstance(value, list):
            print(f"  {key}: {', '.join(value)}")
        elif isinstance(value, dict):
            print(f"  {key}: {len(value)} 种语言")
        else:
            print(f"  {key}: {value}")
    
    print("\n🚀 Agent已准备就绪，可以开始字幕翻译任务！")