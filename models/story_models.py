"""
故事和人物关系相关数据模型
"""
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RelationshipType(Enum):
    """关系类型枚举"""
    # 家庭关系
    FAMILY_PARENT = "family_parent"
    FAMILY_CHILD = "family_child"
    FAMILY_SPOUSE = "family_spouse"
    FAMILY_SIBLING = "family_sibling"
    FAMILY_RELATIVE = "family_relative"
    
    # 职业关系
    PROFESSIONAL_SUPERIOR = "professional_superior"
    PROFESSIONAL_SUBORDINATE = "professional_subordinate"
    PROFESSIONAL_COLLEAGUE = "professional_colleague"
    PROFESSIONAL_PARTNER = "professional_partner"
    
    # 军事关系
    MILITARY_COMMANDER = "military_commander"
    MILITARY_SUBORDINATE = "military_subordinate"
    MILITARY_COMRADE = "military_comrade"
    
    # 社交关系
    SOCIAL_FRIEND = "social_friend"
    SOCIAL_LOVER = "social_lover"
    SOCIAL_ENEMY = "social_enemy"
    SOCIAL_STRANGER = "social_stranger"
    
    # 其他关系
    MENTOR_STUDENT = "mentor_student"
    DOCTOR_PATIENT = "doctor_patient"
    TEACHER_STUDENT = "teacher_student"


class FormalityLevel(Enum):
    """正式程度枚举"""
    VERY_LOW = "very_low"      # 非常随意
    LOW = "low"                # 随意
    MEDIUM = "medium"          # 中等
    HIGH = "high"              # 正式
    VERY_HIGH = "very_high"    # 非常正式


class RespectLevel(Enum):
    """尊敬程度枚举"""
    HIGH = "high"              # 高度尊敬
    MEDIUM = "medium"          # 中等尊敬
    EQUAL = "equal"            # 平等
    CARING = "caring"          # 关爱
    NEUTRAL = "neutral"        # 中性


@dataclass
class RelationshipConfig:
    """关系配置类"""
    relationship_type: RelationshipType
    formality_level: FormalityLevel
    respect_level: RespectLevel
    address_style: str  # formal_title, brotherhood, intimate, casual, family等
    
    # 语言特定配置
    language_specific: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_language_config(self, language: str) -> Dict[str, Any]:
        """获取特定语言的配置"""
        return self.language_specific.get(language, {})
    
    def set_language_config(self, language: str, config: Dict[str, Any]):
        """设置特定语言的配置"""
        self.language_specific[language] = config


@dataclass
class CharacterRelation:
    """人物关系类"""
    name: str
    role: str
    profession: str
    
    # 基本信息
    personality_traits: List[str] = field(default_factory=list)
    speaking_style: str = ""
    age_group: Optional[str] = None  # young, middle_aged, elderly
    gender: Optional[str] = None
    
    # 多语言名称翻译
    name_translations: Dict[str, str] = field(default_factory=dict)
    
    # 关系网络
    relationships: Dict[str, RelationshipConfig] = field(default_factory=dict)
    
    # 称谓系统
    titles: List[str] = field(default_factory=list)
    nicknames: List[str] = field(default_factory=list)
    
    # 文化背景
    cultural_background: Optional[str] = None
    social_status: Optional[str] = None
    
    def add_relationship(self, 
                        other_character: str, 
                        relationship_type: RelationshipType,
                        formality: FormalityLevel = FormalityLevel.MEDIUM,
                        respect: RespectLevel = RespectLevel.EQUAL,
                        address_style: str = "casual"):
        """添加关系"""
        config = RelationshipConfig(
            relationship_type=relationship_type,
            formality_level=formality,
            respect_level=respect,
            address_style=address_style
        )
        self.relationships[other_character] = config
    
    def get_relationship(self, other_character: str) -> Optional[RelationshipConfig]:
        """获取与另一个角色的关系"""
        return self.relationships.get(other_character)
    
    def get_name_translation(self, language: str) -> str:
        """获取名称翻译"""
        return self.name_translations.get(language, self.name)
    
    def set_name_translation(self, language: str, translation: str):
        """设置名称翻译"""
        self.name_translations[language] = translation
    
    def get_appropriate_address(self, 
                               other_character: str, 
                               language: str = "zh",
                               context: str = "normal") -> Optional[str]:
        """获取合适的称谓"""
        relationship = self.get_relationship(other_character)
        if not relationship:
            return None
        
        # 根据关系类型、正式程度和语言返回合适的称谓
        # 这里可以扩展为更复杂的称谓选择逻辑
        lang_config = relationship.get_language_config(language)
        if lang_config and "address_terms" in lang_config:
            return lang_config["address_terms"].get(context, lang_config["address_terms"].get("default"))
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "role": self.role,
            "profession": self.profession,
            "personality_traits": self.personality_traits,
            "speaking_style": self.speaking_style,
            "age_group": self.age_group,
            "gender": self.gender,
            "name_translations": self.name_translations,
            "relationships": {
                char: {
                    "relationship_type": rel.relationship_type.value,
                    "formality_level": rel.formality_level.value,
                    "respect_level": rel.respect_level.value,
                    "address_style": rel.address_style,
                    "language_specific": rel.language_specific
                }
                for char, rel in self.relationships.items()
            },
            "titles": self.titles,
            "nicknames": self.nicknames,
            "cultural_background": self.cultural_background,
            "social_status": self.social_status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterRelation':
        """从字典创建实例"""
        character = cls(
            name=data["name"],
            role=data["role"],
            profession=data["profession"],
            personality_traits=data.get("personality_traits", []),
            speaking_style=data.get("speaking_style", ""),
            age_group=data.get("age_group"),
            gender=data.get("gender"),
            name_translations=data.get("name_translations", {}),
            titles=data.get("titles", []),
            nicknames=data.get("nicknames", []),
            cultural_background=data.get("cultural_background"),
            social_status=data.get("social_status"),
        )
        
        # 重建关系
        relationships_data = data.get("relationships", {})
        for char_name, rel_data in relationships_data.items():
            rel_config = RelationshipConfig(
                relationship_type=RelationshipType(rel_data["relationship_type"]),
                formality_level=FormalityLevel(rel_data["formality_level"]),
                respect_level=RespectLevel(rel_data["respect_level"]),
                address_style=rel_data["address_style"],
                language_specific=rel_data.get("language_specific", {})
            )
            character.relationships[char_name] = rel_config
        
        return character


@dataclass
class StoryContext:
    """故事上下文类"""
    title: str
    genre: str
    setting: str
    time_period: str
    
    # 人物信息
    main_characters: Dict[str, CharacterRelation] = field(default_factory=dict)
    
    # 剧情信息
    episode_summary: str = ""
    key_themes: List[str] = field(default_factory=list)
    cultural_notes: List[str] = field(default_factory=list)
    
    # 术语和专业词汇
    key_terms: Dict[str, str] = field(default_factory=dict)
    professional_vocabulary: Dict[str, List[str]] = field(default_factory=dict)
    
    # 社会等级和文化背景
    social_hierarchy: Dict[str, Any] = field(default_factory=dict)
    cultural_context: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_character(self, character: CharacterRelation):
        """添加角色"""
        self.main_characters[character.name] = character
        self.updated_at = datetime.now()
    
    def get_character(self, name: str) -> Optional[CharacterRelation]:
        """获取角色"""
        return self.main_characters.get(name)
    
    def get_character_by_title(self, title: str) -> Optional[CharacterRelation]:
        """通过称谓获取角色"""
        for character in self.main_characters.values():
            if title in character.titles or title in character.nicknames:
                return character
        return None
    
    def get_characters_by_profession(self, profession: str) -> List[CharacterRelation]:
        """获取特定职业的角色"""
        return [char for char in self.main_characters.values() if char.profession == profession]
    
    def get_relationship_between(self, char1: str, char2: str) -> Optional[RelationshipConfig]:
        """获取两个角色间的关系"""
        character1 = self.get_character(char1)
        if character1:
            return character1.get_relationship(char2)
        return None
    
    def analyze_dialogue_context(self, speaker: str, addressee: Optional[str] = None) -> Dict[str, Any]:
        """分析对话上下文"""
        speaker_char = self.get_character(speaker)
        if not speaker_char:
            return {"error": f"未找到说话人: {speaker}"}
        
        context = {
            "speaker": {
                "name": speaker,
                "role": speaker_char.role,
                "profession": speaker_char.profession,
                "personality": speaker_char.personality_traits,
                "speaking_style": speaker_char.speaking_style
            }
        }
        
        if addressee:
            addressee_char = self.get_character(addressee)
            if addressee_char:
                relationship = speaker_char.get_relationship(addressee)
                context["addressee"] = {
                    "name": addressee,
                    "role": addressee_char.role,
                    "profession": addressee_char.profession
                }
                if relationship:
                    context["relationship"] = {
                        "type": relationship.relationship_type.value,
                        "formality": relationship.formality_level.value,
                        "respect": relationship.respect_level.value,
                        "address_style": relationship.address_style
                    }
        
        return context
    
    def get_cultural_adaptation_hints(self, target_language: str) -> Dict[str, Any]:
        """获取文化适配提示"""
        hints = {
            "genre": self.genre,
            "setting": self.setting,
            "time_period": self.time_period,
            "cultural_notes": self.cultural_notes,
            "social_hierarchy": self.social_hierarchy,
            "key_themes": self.key_themes
        }
        
        # 添加语言特定的文化适配信息
        if target_language in self.cultural_context:
            hints["language_specific"] = self.cultural_context[target_language]
        
        return hints
    
    def get_character_personality(self, character_name: str) -> List[str]:
        """获取角色性格特点"""
        character = self.get_character(character_name)
        return character.personality_traits if character else []
    
    def validate_consistency(self) -> List[str]:
        """验证一致性"""
        issues = []
        
        # 检查双向关系一致性
        for char1_name, char1 in self.main_characters.items():
            for char2_name, relationship in char1.relationships.items():
                char2 = self.get_character(char2_name)
                if not char2:
                    issues.append(f"角色 {char1_name} 的关系中引用了不存在的角色: {char2_name}")
                    continue
                
                # 检查反向关系是否存在
                reverse_rel = char2.get_relationship(char1_name)
                if not reverse_rel:
                    issues.append(f"角色 {char1_name} 和 {char2_name} 的关系不对称")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "genre": self.genre,
            "setting": self.setting,
            "time_period": self.time_period,
            "main_characters": {
                name: char.to_dict() 
                for name, char in self.main_characters.items()
            },
            "episode_summary": self.episode_summary,
            "key_themes": self.key_themes,
            "cultural_notes": self.cultural_notes,
            "key_terms": self.key_terms,
            "professional_vocabulary": self.professional_vocabulary,
            "social_hierarchy": self.social_hierarchy,
            "cultural_context": self.cultural_context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryContext':
        """从字典创建实例"""
        context = cls(
            title=data["title"],
            genre=data["genre"],
            setting=data["setting"],
            time_period=data["time_period"],
            episode_summary=data.get("episode_summary", ""),
            key_themes=data.get("key_themes", []),
            cultural_notes=data.get("cultural_notes", []),
            key_terms=data.get("key_terms", {}),
            professional_vocabulary=data.get("professional_vocabulary", {}),
            social_hierarchy=data.get("social_hierarchy", {}),
            cultural_context=data.get("cultural_context", {}),
        )
        
        # 重建角色
        characters_data = data.get("main_characters", {})
        for char_name, char_data in characters_data.items():
            character = CharacterRelation.from_dict(char_data)
            context.main_characters[char_name] = character
        
        # 解析时间
        if "created_at" in data:
            context.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            context.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return context


@dataclass
class DialogueContext:
    """对话上下文类"""
    speaker: str
    addressee: Optional[str]
    previous_speakers: List[str] = field(default_factory=list)
    scene_type: str = "dialogue"  # dialogue, monologue, narration
    emotional_tone: str = "neutral"
    
    # 上下文窗口
    context_window: List[str] = field(default_factory=list)  # 前几句对话
    
    def add_to_context(self, text: str, speaker: str):
        """添加到上下文窗口"""
        self.context_window.append(f"{speaker}: {text}")
        if len(self.context_window) > 10:  # 保持窗口大小
            self.context_window.pop(0)
    
    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        return "\n".join(self.context_window[-5:])  # 最近5句对话