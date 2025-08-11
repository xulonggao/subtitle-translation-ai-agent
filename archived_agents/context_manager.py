"""
上下文管理器
负责管理剧情上下文、人物关系和对话历史
"""
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from collections import deque

from config import get_logger
from models.story_models import (
    StoryContext, CharacterRelation, RelationshipType,
    FormalityLevel, RespectLevel, DialogueContext
)
from models.subtitle_models import SubtitleEntry
from agents.project_manager import get_project_manager

logger = get_logger("context_manager")


class ContextManager:
    """上下文管理器
    
    负责加载和管理项目特定的故事上下文、人物关系和对话历史
    """
    
    def __init__(self):
        self.project_manager = get_project_manager()
        self.loaded_contexts: Dict[str, StoryContext] = {}
        self.dialogue_histories: Dict[str, DialogueContext] = {}
        
        logger.info("上下文管理器初始化完成")
    
    def load_project_context(self, project_id: str) -> StoryContext:
        """加载项目上下文"""
        if project_id in self.loaded_contexts:
            logger.info("使用缓存的项目上下文", project_id=project_id)
            return self.loaded_contexts[project_id]
        
        try:
            # 从项目管理器加载原始数据
            context_data = self.project_manager.load_project_context(project_id)
            
            # 构建StoryContext对象
            story_context = self._build_story_context(project_id, context_data)
            
            # 缓存上下文
            self.loaded_contexts[project_id] = story_context
            
            logger.info("项目上下文加载完成", 
                       project_id=project_id,
                       characters_count=len(story_context.main_characters))
            
            return story_context
            
        except Exception as e:
            logger.error("加载项目上下文失败", project_id=project_id, error=str(e))
            raise
    
    def _build_story_context(self, project_id: str, context_data: Dict[str, Any]) -> StoryContext:
        """构建故事上下文对象"""
        
        # 解析人物关系数据
        char_relations_data = context_data.get("character_relations", {})
        project_info = char_relations_data.get("project_info", {})
        
        # 创建基础故事上下文
        story_context = StoryContext(
            title=project_info.get("project_title", project_id),
            genre=project_info.get("genre", "未知"),
            setting=project_info.get("description", ""),
            time_period="当代"  # 默认值
        )
        
        # 解析剧情简介
        story_text = context_data.get("story_context", "")
        if story_text:
            story_context.episode_summary = self._extract_summary_from_text(story_text)
            story_context.key_themes = self._extract_themes_from_text(story_text)
            story_context.cultural_notes = self._extract_cultural_notes_from_text(story_text)
        
        # 构建人物关系
        characters_data = char_relations_data.get("characters", {})
        for char_name, char_data in characters_data.items():
            character = self._build_character_relation(char_name, char_data)
            story_context.add_character(character)
        
        # 建立双向关系
        self._establish_bidirectional_relationships(story_context, characters_data)
        
        # 加载术语库
        terminology_data = context_data.get("terminology", {})
        story_context.key_terms = self._extract_key_terms(terminology_data)
        story_context.professional_vocabulary = self._extract_professional_vocabulary(terminology_data)
        
        # 设置文化背景
        cultural_context = char_relations_data.get("cultural_context", {})
        story_context.cultural_context = cultural_context
        
        return story_context
    
    def _build_character_relation(self, char_name: str, char_data: Dict[str, Any]) -> CharacterRelation:
        """构建人物关系对象"""
        character = CharacterRelation(
            name=char_name,
            role=char_data.get("role", ""),
            profession=char_data.get("profession", ""),
            personality_traits=char_data.get("personality_traits", []),
            speaking_style=char_data.get("speaking_style", ""),
            name_translations=char_data.get("name_translations", {}),
            titles=char_data.get("titles", []),
            nicknames=char_data.get("nicknames", []),
            cultural_background=char_data.get("cultural_background"),
            social_status=char_data.get("social_status")
        )
        
        return character
    
    def _establish_bidirectional_relationships(self, story_context: StoryContext, characters_data: Dict[str, Any]):
        """建立双向人物关系"""
        for char_name, char_data in characters_data.items():
            character = story_context.get_character(char_name)
            if not character:
                continue
            
            relationships = char_data.get("relationships", {})
            for other_char_name, relationship_desc in relationships.items():
                if other_char_name not in story_context.main_characters:
                    continue
                
                # 根据关系描述推断关系类型
                relationship_type = self._infer_relationship_type(relationship_desc)
                formality, respect = self._infer_formality_and_respect(
                    char_data.get("profession", ""), 
                    characters_data.get(other_char_name, {}).get("profession", ""),
                    relationship_desc
                )
                
                character.add_relationship(
                    other_char_name,
                    relationship_type,
                    formality,
                    respect,
                    self._get_address_style(relationship_type)
                )
    
    def _infer_relationship_type(self, relationship_desc: str) -> RelationshipType:
        """推断关系类型"""
        relationship_mapping = {
            "恋人": RelationshipType.SOCIAL_LOVER,
            "夫妻": RelationshipType.FAMILY_SPOUSE,
            "妻子": RelationshipType.FAMILY_SPOUSE,
            "丈夫": RelationshipType.FAMILY_SPOUSE,
            "战友": RelationshipType.MILITARY_COMRADE,
            "上级": RelationshipType.MILITARY_COMMANDER,
            "下属": RelationshipType.MILITARY_SUBORDINATE,
            "同事": RelationshipType.PROFESSIONAL_COLLEAGUE,
            "朋友": RelationshipType.SOCIAL_FRIEND,
            "父亲": RelationshipType.FAMILY_PARENT,
            "母亲": RelationshipType.FAMILY_PARENT,
            "儿子": RelationshipType.FAMILY_CHILD,
            "女儿": RelationshipType.FAMILY_CHILD,
        }
        
        for key, rel_type in relationship_mapping.items():
            if key in relationship_desc:
                return rel_type
        
        return RelationshipType.SOCIAL_STRANGER
    
    def _infer_formality_and_respect(self, profession1: str, profession2: str, relationship: str) -> Tuple[FormalityLevel, RespectLevel]:
        """推断正式程度和尊敬程度"""
        
        # 军事关系通常更正式
        if any(keyword in profession1 + profession2 for keyword in ["军", "司令", "参谋", "队长"]):
            if "上级" in relationship or "司令" in profession2:
                return FormalityLevel.VERY_HIGH, RespectLevel.HIGH
            elif "战友" in relationship:
                return FormalityLevel.HIGH, RespectLevel.EQUAL
            elif "下属" in relationship:
                return FormalityLevel.HIGH, RespectLevel.MEDIUM
        
        # 家庭关系
        if any(keyword in relationship for keyword in ["夫妻", "恋人", "父", "母", "子", "女"]):
            return FormalityLevel.LOW, RespectLevel.CARING
        
        # 职业关系
        if any(keyword in relationship for keyword in ["同事", "合作"]):
            return FormalityLevel.MEDIUM, RespectLevel.EQUAL
        
        # 默认
        return FormalityLevel.MEDIUM, RespectLevel.NEUTRAL
    
    def _get_address_style(self, relationship_type: RelationshipType) -> str:
        """获取称谓风格"""
        style_mapping = {
            RelationshipType.MILITARY_COMMANDER: "formal_title",
            RelationshipType.MILITARY_SUBORDINATE: "formal_title",
            RelationshipType.MILITARY_COMRADE: "brotherhood",
            RelationshipType.FAMILY_SPOUSE: "intimate",
            RelationshipType.SOCIAL_LOVER: "intimate",
            RelationshipType.FAMILY_PARENT: "family",
            RelationshipType.FAMILY_CHILD: "family",
            RelationshipType.PROFESSIONAL_COLLEAGUE: "professional",
            RelationshipType.SOCIAL_FRIEND: "casual",
        }
        
        return style_mapping.get(relationship_type, "casual")
    
    def _extract_summary_from_text(self, story_text: str) -> str:
        """从故事文本中提取摘要"""
        lines = story_text.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#') and len(line) > 20:
                return line.strip()[:200]  # 返回前200字符作为摘要
        return ""
    
    def _extract_themes_from_text(self, story_text: str) -> List[str]:
        """从故事文本中提取主题"""
        themes = []
        theme_keywords = {
            "军旅": ["军", "部队", "战友", "演习", "作战"],
            "爱情": ["恋人", "爱情", "相亲", "结婚", "夫妻"],
            "成长": ["成长", "蜕变", "挑战", "困难"],
            "职场": ["职场", "工作", "记者", "医生"],
            "家庭": ["家庭", "父母", "家人"]
        }
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in story_text for keyword in keywords):
                themes.append(theme)
        
        return themes
    
    def _extract_cultural_notes_from_text(self, story_text: str) -> List[str]:
        """从故事文本中提取文化要点"""
        cultural_notes = []
        
        if any(keyword in story_text for keyword in ["军", "海军", "部队"]):
            cultural_notes.append("军事题材")
        
        if any(keyword in story_text for keyword in ["现代", "当代"]):
            cultural_notes.append("现代背景")
        
        if any(keyword in story_text for keyword in ["中国", "海军"]):
            cultural_notes.append("中国军队")
        
        return cultural_notes
    
    def _extract_key_terms(self, terminology_data: Dict[str, Any]) -> Dict[str, str]:
        """提取关键术语"""
        key_terms = {}
        
        for category, terms in terminology_data.items():
            if isinstance(terms, dict):
                for term, translations in terms.items():
                    if isinstance(translations, dict) and "en" in translations:
                        key_terms[term] = translations["en"]
        
        return key_terms
    
    def _extract_professional_vocabulary(self, terminology_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取专业词汇"""
        professional_vocab = {}
        
        category_mapping = {
            "military_terms": "军事",
            "project_specific_terms": "专业",
            "cultural_terms": "文化"
        }
        
        for category, terms in terminology_data.items():
            if category in category_mapping and isinstance(terms, dict):
                vocab_list = list(terms.keys())
                if vocab_list:
                    professional_vocab[category_mapping[category]] = vocab_list
        
        return professional_vocab
    
    def get_speaker_context(self, project_id: str, entry: SubtitleEntry, history: List[SubtitleEntry]) -> Dict[str, Any]:
        """获取说话人上下文"""
        story_context = self.load_project_context(project_id)
        
        # 推断说话人
        speaker = self._infer_speaker(entry, history, story_context)
        entry.speaker = speaker  # 更新条目的说话人信息
        
        # 构建上下文信息
        context = {
            "speaker": speaker,
            "entry_index": entry.index,
            "text": entry.text,
            "scene_emotion": entry.scene_emotion.value,
            "speech_pace": entry.speech_pace.value,
        }
        
        # 获取说话人信息
        if speaker:
            character = story_context.get_character(speaker)
            if character:
                context["speaker_info"] = {
                    "name": character.name,
                    "role": character.role,
                    "profession": character.profession,
                    "personality_traits": character.personality_traits,
                    "speaking_style": character.speaking_style,
                    "titles": character.titles
                }
        
        # 分析对话历史
        dialogue_context = self._analyze_dialogue_history(history, story_context)
        context["dialogue_history"] = dialogue_context
        
        # 推断对话对象
        addressee = self._infer_addressee(entry, history, story_context)
        if addressee:
            context["addressee"] = addressee
            
            # 获取关系信息
            if speaker:
                relationship = story_context.get_relationship_between(speaker, addressee)
                if relationship:
                    context["relationship"] = {
                        "type": relationship.relationship_type.value,
                        "formality": relationship.formality_level.value,
                        "respect": relationship.respect_level.value,
                        "address_style": relationship.address_style
                    }
        
        return context
    
    def _infer_speaker(self, entry: SubtitleEntry, history: List[SubtitleEntry], story_context: StoryContext) -> Optional[str]:
        """推断说话人"""
        
        # 如果已经有说话人信息，直接返回
        if entry.speaker:
            return entry.speaker
        
        # 基于文本内容推断
        text = entry.text
        
        # 检查是否包含特定称谓或术语
        for char_name, character in story_context.main_characters.items():
            # 检查是否使用了该角色的说话风格
            if self._matches_speaking_style(text, character.speaking_style):
                return char_name
            
            # 检查是否包含该角色的专业术语
            if self._contains_professional_terms(text, character.profession):
                return char_name
        
        # 基于对话历史推断
        if history:
            last_speaker = history[-1].speaker
            if last_speaker and len(history) >= 2:
                # 简单的对话轮换推断
                prev_speaker = history[-2].speaker if len(history) >= 2 else None
                if prev_speaker and prev_speaker != last_speaker:
                    # 可能是对话轮换
                    return prev_speaker
        
        return None
    
    def _matches_speaking_style(self, text: str, speaking_style: str) -> bool:
        """检查文本是否匹配说话风格"""
        if not speaking_style:
            return False
        
        style_keywords = {
            "军人": ["是", "报告", "命令", "执行"],
            "正式": ["请", "您", "同志"],
            "专业": ["参数", "数据", "分析", "报告"],
            "温和": ["请", "谢谢", "不好意思"],
            "直接": ["直接", "明确", "立即"]
        }
        
        for style, keywords in style_keywords.items():
            if style in speaking_style:
                if any(keyword in text for keyword in keywords):
                    return True
        
        return False
    
    def _contains_professional_terms(self, text: str, profession: str) -> bool:
        """检查是否包含专业术语"""
        profession_terms = {
            "军人": ["部队", "司令", "参谋", "作战", "演习", "任务"],
            "记者": ["报道", "新闻", "采访", "媒体"],
            "医生": ["病人", "治疗", "诊断", "医院"],
            "学生": ["学习", "考试", "老师", "课程"]
        }
        
        terms = profession_terms.get(profession, [])
        return any(term in text for term in terms)
    
    def _infer_addressee(self, entry: SubtitleEntry, history: List[SubtitleEntry], story_context: StoryContext) -> Optional[str]:
        """推断对话对象"""
        text = entry.text
        
        # 检查是否直接称呼某个角色
        for char_name, character in story_context.main_characters.items():
            # 检查称谓
            for title in character.titles:
                if title in text:
                    return char_name
            
            # 检查昵称
            for nickname in character.nicknames:
                if nickname in text:
                    return char_name
        
        # 基于对话历史推断
        if history and entry.speaker:
            # 查找最近与当前说话人对话的角色
            for prev_entry in reversed(history[-5:]):  # 检查最近5条
                if prev_entry.speaker and prev_entry.speaker != entry.speaker:
                    return prev_entry.speaker
        
        return None
    
    def _analyze_dialogue_history(self, history: List[SubtitleEntry], story_context: StoryContext) -> Dict[str, Any]:
        """分析对话历史"""
        if not history:
            return {"recent_speakers": [], "context_summary": ""}
        
        # 获取最近的说话人
        recent_speakers = []
        for entry in history[-5:]:  # 最近5条
            if entry.speaker and entry.speaker not in recent_speakers:
                recent_speakers.append(entry.speaker)
        
        # 生成上下文摘要
        context_summary = ""
        if len(history) >= 2:
            recent_texts = [entry.text for entry in history[-3:]]
            context_summary = " | ".join(recent_texts)
        
        return {
            "recent_speakers": recent_speakers,
            "context_summary": context_summary,
            "history_length": len(history)
        }
    
    def resolve_pronouns(self, project_id: str, text: str, context: Dict[str, Any]) -> str:
        """解析代词指代"""
        story_context = self.load_project_context(project_id)
        
        # 获取上下文信息
        speaker = context.get("speaker")
        addressee = context.get("addressee")
        recent_speakers = context.get("dialogue_history", {}).get("recent_speakers", [])
        
        # 代词映射
        pronoun_mapping = {}
        
        # 处理"他/她/它"
        if addressee:
            addressee_char = story_context.get_character(addressee)
            if addressee_char:
                gender = addressee_char.gender
                if gender == "male":
                    pronoun_mapping["他"] = addressee
                elif gender == "female":
                    pronoun_mapping["她"] = addressee
        
        # 处理"我"
        if speaker:
            pronoun_mapping["我"] = speaker
        
        # 应用代词替换
        resolved_text = text
        for pronoun, reference in pronoun_mapping.items():
            if pronoun in resolved_text:
                # 这里可以实现更复杂的代词解析逻辑
                logger.debug("代词解析", pronoun=pronoun, reference=reference)
        
        return resolved_text
    
    def get_cultural_adaptation_context(self, project_id: str, target_language: str) -> Dict[str, Any]:
        """获取文化适配上下文"""
        story_context = self.load_project_context(project_id)
        
        adaptation_context = {
            "genre": story_context.genre,
            "setting": story_context.setting,
            "time_period": story_context.time_period,
            "cultural_notes": story_context.cultural_notes,
            "key_themes": story_context.key_themes,
            "target_language": target_language
        }
        
        # 添加语言特定的适配信息
        language_specific = story_context.cultural_context.get(target_language, {})
        if language_specific:
            adaptation_context["language_specific"] = language_specific
        
        return adaptation_context
    
    def update_dialogue_context(self, project_id: str, entry: SubtitleEntry):
        """更新对话上下文"""
        if project_id not in self.dialogue_histories:
            self.dialogue_histories[project_id] = DialogueContext(
                speaker=entry.speaker or "unknown",
                addressee=None
            )
        
        dialogue_context = self.dialogue_histories[project_id]
        
        # 更新说话人历史
        if entry.speaker:
            if entry.speaker not in dialogue_context.previous_speakers:
                dialogue_context.previous_speakers.append(entry.speaker)
            
            # 保持历史长度
            if len(dialogue_context.previous_speakers) > 10:
                dialogue_context.previous_speakers.pop(0)
        
        # 添加到上下文窗口
        dialogue_context.add_to_context(entry.text, entry.speaker or "unknown")
    
    def clear_project_cache(self, project_id: str):
        """清除项目缓存"""
        if project_id in self.loaded_contexts:
            del self.loaded_contexts[project_id]
        
        if project_id in self.dialogue_histories:
            del self.dialogue_histories[project_id]
        
        logger.info("项目缓存已清除", project_id=project_id)
    
    def get_context_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取上下文统计信息"""
        if project_id not in self.loaded_contexts:
            return {"error": "项目上下文未加载"}
        
        story_context = self.loaded_contexts[project_id]
        
        return {
            "project_id": project_id,
            "title": story_context.title,
            "genre": story_context.genre,
            "characters_count": len(story_context.main_characters),
            "characters": list(story_context.main_characters.keys()),
            "key_themes": story_context.key_themes,
            "cultural_notes": story_context.cultural_notes,
            "key_terms_count": len(story_context.key_terms),
            "professional_vocabulary": story_context.professional_vocabulary,
        }


# 全局上下文管理器实例
context_manager = ContextManager()


def get_context_manager() -> ContextManager:
    """获取上下文管理器实例"""
    return context_manager