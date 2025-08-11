"""
对话历史和上下文跟踪器
实现对话窗口管理、说话人跟踪、代词指代解析和上下文相关性分析
"""
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import math

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.story_models import CharacterRelation, StoryContext, DialogueContext
from agents.dynamic_knowledge_manager import get_dynamic_knowledge_manager, KnowledgeQuery

logger = get_logger("dialogue_context_tracker")


class PronounType(Enum):
    """代词类型枚举"""
    PERSONAL = "personal"      # 人称代词：他、她、它
    POSSESSIVE = "possessive"  # 物主代词：他的、她的
    DEMONSTRATIVE = "demonstrative"  # 指示代词：这、那
    RELATIVE = "relative"      # 关系代词：谁、什么
    REFLEXIVE = "reflexive"    # 反身代词：自己


class ContextRelevance(Enum):
    """上下文相关性等级"""
    CRITICAL = "critical"      # 关键相关
    HIGH = "high"             # 高度相关
    MEDIUM = "medium"         # 中等相关
    LOW = "low"               # 低度相关
    IRRELEVANT = "irrelevant" # 不相关


@dataclass
class PronounReference:
    """代词指代信息"""
    pronoun: str              # 代词文本
    pronoun_type: PronounType # 代词类型
    position: int             # 在文本中的位置
    candidates: List[str]     # 候选指代对象
    resolved_reference: Optional[str] = None  # 解析出的指代对象
    confidence: float = 0.0   # 解析置信度
    context_clues: List[str] = field(default_factory=list)  # 上下文线索


@dataclass
class DialogueEntry:
    """对话条目"""
    subtitle_entry: SubtitleEntry
    speaker: Optional[str]
    timestamp: datetime
    context_score: float = 0.0
    pronouns: List[PronounReference] = field(default_factory=list)
    mentioned_entities: Set[str] = field(default_factory=set)
    emotional_tone: Optional[str] = None
    scene_context: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DialogueHistory:
    """对话历史管理器
    
    维护对话窗口、说话人跟踪和上下文信息
    """
    
    def __init__(self, window_size: int = 10, max_history: int = 1000):
        self.window_size = window_size
        self.max_history = max_history
        
        # 对话历史存储
        self.dialogue_history: deque[DialogueEntry] = deque(maxlen=max_history)
        self.current_window: deque[DialogueEntry] = deque(maxlen=window_size)
        
        # 说话人跟踪
        self.speaker_history: Dict[str, List[DialogueEntry]] = defaultdict(list)
        self.speaker_transitions: List[Tuple[str, str, datetime]] = []
        
        # 实体跟踪
        self.mentioned_entities: Dict[str, List[DialogueEntry]] = defaultdict(list)
        self.entity_cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        
        # 上下文统计
        self.context_stats = {
            "total_entries": 0,
            "unique_speakers": set(),
            "avg_context_score": 0.0,
            "pronoun_resolution_rate": 0.0
        }
        
        logger.info("对话历史管理器初始化完成", window_size=window_size, max_history=max_history)
    
    def add_dialogue_entry(self, subtitle_entry: SubtitleEntry, 
                          speaker: Optional[str] = None,
                          scene_context: Optional[str] = None) -> DialogueEntry:
        """添加对话条目"""
        # 创建对话条目
        dialogue_entry = DialogueEntry(
            subtitle_entry=subtitle_entry,
            speaker=speaker or subtitle_entry.speaker,
            timestamp=datetime.now(),
            scene_context=scene_context
        )
        
        # 分析文本内容
        self._analyze_dialogue_content(dialogue_entry)
        
        # 计算上下文相关性
        dialogue_entry.context_score = self._calculate_context_relevance(dialogue_entry)
        
        # 添加到历史记录
        self.dialogue_history.append(dialogue_entry)
        self.current_window.append(dialogue_entry)
        
        # 更新说话人跟踪
        if dialogue_entry.speaker:
            self._update_speaker_tracking(dialogue_entry)
        
        # 更新实体跟踪
        self._update_entity_tracking(dialogue_entry)
        
        # 更新统计信息
        self._update_statistics()
        
        logger.debug("对话条目已添加", speaker=dialogue_entry.speaker, 
                    text_preview=dialogue_entry.subtitle_entry.text[:30])
        
        return dialogue_entry    
    
    def _analyze_dialogue_content(self, dialogue_entry: DialogueEntry):
        """分析对话内容"""
        text = dialogue_entry.subtitle_entry.text
        
        # 提取代词
        dialogue_entry.pronouns = self._extract_pronouns(text)
        
        # 提取提及的实体
        dialogue_entry.mentioned_entities = self._extract_entities(text)
        
        # 分析情感语调
        dialogue_entry.emotional_tone = self._analyze_emotional_tone(text)
    
    def _extract_pronouns(self, text: str) -> List[PronounReference]:
        """提取文本中的代词"""
        pronouns = []
        
        # 定义代词模式（按长度排序，优先匹配长的）
        pronoun_patterns = {
            PronounType.POSSESSIVE: [
                r'(我们的|你们的|他们的|她们的|它们的|咱们的|我的|你的|您的|他的|她的|它的)',
            ],
            PronounType.PERSONAL: [
                r'(他们|她们|它们|我们|你们|咱们|他|她|它|我|你|您)',
            ],
            PronounType.DEMONSTRATIVE: [
                r'(这个|那个|这些|那些|这里|那里|这儿|那儿|这|那)',
            ],
            PronounType.RELATIVE: [
                r'(哪些|哪个|哪里|哪儿|谁|什么)',
            ],
            PronounType.REFLEXIVE: [
                r'(自己|本人|亲自)',
            ]
        }
        
        # 记录已匹配的位置，避免重复
        matched_positions = set()
        
        for pronoun_type, patterns in pronoun_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    # 检查是否与已匹配的位置重叠
                    start, end = match.span()
                    if not any(pos >= start and pos < end for pos in matched_positions):
                        pronoun_ref = PronounReference(
                            pronoun=match.group(),
                            pronoun_type=pronoun_type,
                            position=match.start(),
                            candidates=[]
                        )
                        pronouns.append(pronoun_ref)
                        # 记录所有匹配的字符位置
                        matched_positions.update(range(start, end))
        
        return pronouns
    
    def _extract_entities(self, text: str) -> Set[str]:
        """提取文本中提及的实体"""
        entities = set()
        
        # 简单的实体提取模式
        # 人名模式（中文姓名）
        name_patterns = [
            r'[王李张刘陈杨黄赵周吴徐孙朱马胡郭林何高梁郑罗宋谢唐韩曹许邓萧冯曾程蔡彭潘袁于董余苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚][一-龯]{1,2}',
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # 英文姓名
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        # 职位/称谓模式
        title_patterns = [
            r'(参谋长|司令|队长|医生|护士|教授|老师|经理|主任|局长|部长|总统|主席)',
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        return entities
    
    def _analyze_emotional_tone(self, text: str) -> Optional[str]:
        """分析情感语调"""
        emotion_patterns = {
            "angry": [r'(生气|愤怒|气死|混蛋|该死|可恶)', r'[！]{2,}'],
            "sad": [r'(难过|伤心|哭|眼泪|痛苦|悲伤)'],
            "happy": [r'(高兴|开心|笑|快乐|兴奋|哈哈)'],
            "surprised": [r'(惊讶|震惊|不敢相信|天哪|我的天)', r'[？]{2,}'],
            "worried": [r'(担心|害怕|恐惧|焦虑|紧张)'],
            "calm": [r'(冷静|平静|淡定|稳重)']
        }
        
        for emotion, patterns in emotion_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return emotion
        
        return "neutral"
    
    def _calculate_context_relevance(self, dialogue_entry: DialogueEntry) -> float:
        """计算上下文相关性分数"""
        if not self.current_window:
            return 1.0  # 第一个条目默认高相关性
        
        score = 0.0
        factors = []
        
        # 说话人连续性
        if self.current_window:
            last_speaker = self.current_window[-1].speaker
            if dialogue_entry.speaker == last_speaker:
                factors.append(("speaker_continuity", 0.3))
            elif self._are_speakers_related(dialogue_entry.speaker, last_speaker):
                factors.append(("speaker_relation", 0.2))
        
        # 实体重叠
        entity_overlap = self._calculate_entity_overlap(dialogue_entry)
        if entity_overlap > 0:
            factors.append(("entity_overlap", entity_overlap * 0.4))
        
        # 时间连续性
        time_continuity = self._calculate_time_continuity(dialogue_entry)
        factors.append(("time_continuity", time_continuity * 0.2))
        
        # 情感一致性
        emotion_consistency = self._calculate_emotion_consistency(dialogue_entry)
        factors.append(("emotion_consistency", emotion_consistency * 0.1))
        
        # 计算总分
        score = sum(factor_score for _, factor_score in factors)
        score = min(score, 1.0)  # 限制在0-1范围内
        
        logger.debug("上下文相关性计算", score=score, factors=factors)
        return score
    
    def _are_speakers_related(self, speaker1: Optional[str], speaker2: Optional[str]) -> bool:
        """判断两个说话人是否有关系"""
        if not speaker1 or not speaker2:
            return False
        
        # 这里可以集成知识库查询人物关系
        # 简化实现：检查是否是同一场景的常见对话者
        return False  # 暂时返回False，后续可以集成人物关系知识
    
    def _calculate_entity_overlap(self, dialogue_entry: DialogueEntry) -> float:
        """计算实体重叠度"""
        if not self.current_window or not dialogue_entry.mentioned_entities:
            return 0.0
        
        # 获取最近几个条目的实体
        recent_entities = set()
        for entry in list(self.current_window)[-3:]:  # 最近3个条目
            recent_entities.update(entry.mentioned_entities)
        
        if not recent_entities:
            return 0.0
        
        # 计算重叠比例
        overlap = len(dialogue_entry.mentioned_entities & recent_entities)
        total = len(dialogue_entry.mentioned_entities | recent_entities)
        
        return overlap / total if total > 0 else 0.0
    
    def _calculate_time_continuity(self, dialogue_entry: DialogueEntry) -> float:
        """计算时间连续性"""
        if not self.current_window:
            return 1.0
        
        last_entry = self.current_window[-1]
        time_diff = (dialogue_entry.timestamp - last_entry.timestamp).total_seconds()
        
        # 时间差越小，连续性越高
        if time_diff <= 5:  # 5秒内
            return 1.0
        elif time_diff <= 30:  # 30秒内
            return 0.8
        elif time_diff <= 120:  # 2分钟内
            return 0.5
        else:
            return 0.2
    
    def _calculate_emotion_consistency(self, dialogue_entry: DialogueEntry) -> float:
        """计算情感一致性"""
        if not self.current_window or not dialogue_entry.emotional_tone:
            return 0.5
        
        # 检查最近条目的情感
        recent_emotions = []
        for entry in list(self.current_window)[-3:]:
            if entry.emotional_tone:
                recent_emotions.append(entry.emotional_tone)
        
        if not recent_emotions:
            return 0.5
        
        # 情感一致性评分
        if dialogue_entry.emotional_tone in recent_emotions:
            return 1.0
        
        # 检查情感兼容性
        compatible_emotions = {
            "happy": ["excited", "calm"],
            "sad": ["worried", "calm"],
            "angry": ["worried", "surprised"],
            "surprised": ["worried", "happy"],
            "worried": ["sad", "angry"],
            "calm": ["happy", "sad"]
        }
        
        current_emotion = dialogue_entry.emotional_tone
        if current_emotion in compatible_emotions:
            for emotion in recent_emotions:
                if emotion in compatible_emotions[current_emotion]:
                    return 0.7
        
        return 0.3
    
    def _update_speaker_tracking(self, dialogue_entry: DialogueEntry):
        """更新说话人跟踪"""
        speaker = dialogue_entry.speaker
        if not speaker:
            return
        
        # 添加到说话人历史
        self.speaker_history[speaker].append(dialogue_entry)
        
        # 记录说话人转换
        if self.current_window and len(self.current_window) > 1:
            prev_speaker = self.current_window[-2].speaker
            if prev_speaker and prev_speaker != speaker:
                self.speaker_transitions.append((prev_speaker, speaker, dialogue_entry.timestamp))
        
        # 限制历史长度
        if len(self.speaker_history[speaker]) > 100:
            self.speaker_history[speaker] = self.speaker_history[speaker][-100:]
    
    def _update_entity_tracking(self, dialogue_entry: DialogueEntry):
        """更新实体跟踪"""
        for entity in dialogue_entry.mentioned_entities:
            self.mentioned_entities[entity].append(dialogue_entry)
            
            # 更新实体共现统计
            for other_entity in dialogue_entry.mentioned_entities:
                if entity != other_entity:
                    pair = tuple(sorted([entity, other_entity]))
                    self.entity_cooccurrence[pair] += 1
        
        # 限制实体历史长度
        for entity in list(self.mentioned_entities.keys()):
            if len(self.mentioned_entities[entity]) > 50:
                self.mentioned_entities[entity] = self.mentioned_entities[entity][-50:]
    
    def _update_statistics(self):
        """更新统计信息"""
        self.context_stats["total_entries"] = len(self.dialogue_history)
        
        # 更新唯一说话人
        for entry in self.dialogue_history:
            if entry.speaker:
                self.context_stats["unique_speakers"].add(entry.speaker)
        
        # 计算平均上下文分数
        if self.dialogue_history:
            total_score = sum(entry.context_score for entry in self.dialogue_history)
            self.context_stats["avg_context_score"] = total_score / len(self.dialogue_history)
        
        # 计算代词解析率
        total_pronouns = sum(len(entry.pronouns) for entry in self.dialogue_history)
        resolved_pronouns = sum(
            len([p for p in entry.pronouns if p.resolved_reference])
            for entry in self.dialogue_history
        )
        
        if total_pronouns > 0:
            self.context_stats["pronoun_resolution_rate"] = resolved_pronouns / total_pronouns   
 
    def get_current_context(self, max_entries: int = None) -> List[DialogueEntry]:
        """获取当前上下文窗口"""
        if max_entries is None:
            return list(self.current_window)
        else:
            return list(self.current_window)[-max_entries:]
    
    def get_speaker_history(self, speaker: str, max_entries: int = 10) -> List[DialogueEntry]:
        """获取特定说话人的历史"""
        if speaker not in self.speaker_history:
            return []
        
        return self.speaker_history[speaker][-max_entries:]
    
    def get_entity_context(self, entity: str, max_entries: int = 5) -> List[DialogueEntry]:
        """获取特定实体的上下文"""
        if entity not in self.mentioned_entities:
            return []
        
        return self.mentioned_entities[entity][-max_entries:]
    
    def get_related_entities(self, entity: str, min_cooccurrence: int = 2) -> List[Tuple[str, int]]:
        """获取与指定实体相关的其他实体"""
        related = []
        
        for (ent1, ent2), count in self.entity_cooccurrence.items():
            if count >= min_cooccurrence:
                if ent1 == entity:
                    related.append((ent2, count))
                elif ent2 == entity:
                    related.append((ent1, count))
        
        # 按共现次数排序
        related.sort(key=lambda x: x[1], reverse=True)
        return related
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        stats = self.context_stats.copy()
        stats["unique_speakers"] = len(stats["unique_speakers"])
        stats["window_size"] = len(self.current_window)
        stats["total_entities"] = len(self.mentioned_entities)
        stats["speaker_transitions"] = len(self.speaker_transitions)
        
        return stats
    
    def compress_context(self, target_size: int = None) -> int:
        """压缩上下文历史"""
        if target_size is None:
            target_size = self.max_history // 2
        
        if len(self.dialogue_history) <= target_size:
            return 0  # 无需压缩
        
        # 保留高相关性的条目
        sorted_entries = sorted(self.dialogue_history, key=lambda x: x.context_score, reverse=True)
        
        # 保留最近的条目和高分条目
        recent_entries = list(self.dialogue_history)[-target_size//2:]
        high_score_entries = sorted_entries[:target_size//2]
        
        # 合并并去重
        kept_entries = []
        seen_entries = set()
        
        for entry in recent_entries + high_score_entries:
            entry_id = id(entry)
            if entry_id not in seen_entries:
                kept_entries.append(entry)
                seen_entries.add(entry_id)
        
        # 按时间排序
        kept_entries.sort(key=lambda x: x.timestamp)
        
        # 更新历史
        removed_count = len(self.dialogue_history) - len(kept_entries)
        self.dialogue_history = deque(kept_entries, maxlen=self.max_history)
        
        # 重建索引
        self._rebuild_indices()
        
        logger.info("上下文已压缩", removed_count=removed_count, remaining_count=len(kept_entries))
        return removed_count
    
    def _rebuild_indices(self):
        """重建索引"""
        # 重建说话人历史
        self.speaker_history.clear()
        self.mentioned_entities.clear()
        self.entity_cooccurrence.clear()
        
        for entry in self.dialogue_history:
            if entry.speaker:
                self.speaker_history[entry.speaker].append(entry)
            
            for entity in entry.mentioned_entities:
                self.mentioned_entities[entity].append(entry)
                
                for other_entity in entry.mentioned_entities:
                    if entity != other_entity:
                        pair = tuple(sorted([entity, other_entity]))
                        self.entity_cooccurrence[pair] += 1


class PronounResolver:
    """代词指代解析器"""
    
    def __init__(self, dialogue_history: DialogueHistory):
        self.dialogue_history = dialogue_history
        self.dynamic_kb = get_dynamic_knowledge_manager()
        
        # 代词解析规则
        self.resolution_rules = {
            PronounType.PERSONAL: self._resolve_personal_pronoun,
            PronounType.POSSESSIVE: self._resolve_possessive_pronoun,
            PronounType.DEMONSTRATIVE: self._resolve_demonstrative_pronoun,
            PronounType.RELATIVE: self._resolve_relative_pronoun,
            PronounType.REFLEXIVE: self._resolve_reflexive_pronoun
        }
        
        logger.info("代词指代解析器初始化完成")
    
    def resolve_pronouns(self, dialogue_entry: DialogueEntry, 
                        story_context: Optional[StoryContext] = None) -> List[PronounReference]:
        """解析对话条目中的代词指代"""
        resolved_pronouns = []
        
        for pronoun_ref in dialogue_entry.pronouns:
            # 获取候选指代对象
            candidates = self._get_reference_candidates(dialogue_entry, pronoun_ref, story_context)
            pronoun_ref.candidates = candidates
            
            # 应用解析规则
            if pronoun_ref.pronoun_type in self.resolution_rules:
                resolver = self.resolution_rules[pronoun_ref.pronoun_type]
                resolved_ref, confidence = resolver(dialogue_entry, pronoun_ref, story_context)
                
                pronoun_ref.resolved_reference = resolved_ref
                pronoun_ref.confidence = confidence
                
                if resolved_ref:
                    logger.debug("代词解析成功", pronoun=pronoun_ref.pronoun, 
                               reference=resolved_ref, confidence=confidence)
            
            resolved_pronouns.append(pronoun_ref)
        
        return resolved_pronouns
    
    def _get_reference_candidates(self, dialogue_entry: DialogueEntry, 
                                 pronoun_ref: PronounReference,
                                 story_context: Optional[StoryContext] = None) -> List[str]:
        """获取代词指代的候选对象"""
        candidates = []
        
        # 从当前上下文窗口获取候选
        context_window = self.dialogue_history.get_current_context(5)
        
        for entry in reversed(context_window):  # 从最近的开始
            if entry == dialogue_entry:
                continue
            
            # 添加说话人作为候选
            if entry.speaker:
                candidates.append(entry.speaker)
            
            # 添加提及的实体作为候选
            candidates.extend(entry.mentioned_entities)
        
        # 从故事上下文获取候选
        if story_context:
            candidates.extend(story_context.main_characters.keys())
        
        # 去重并保持顺序
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                unique_candidates.append(candidate)
                seen.add(candidate)
        
        return unique_candidates[:10]  # 限制候选数量
    
    def _resolve_personal_pronoun(self, dialogue_entry: DialogueEntry, 
                                 pronoun_ref: PronounReference,
                                 story_context: Optional[StoryContext] = None) -> Tuple[Optional[str], float]:
        """解析人称代词"""
        pronoun = pronoun_ref.pronoun
        candidates = pronoun_ref.candidates
        
        if not candidates:
            return None, 0.0
        
        # 性别匹配规则
        gender_mapping = {
            "他": "male",
            "她": "female", 
            "它": "neutral"
        }
        
        if pronoun in gender_mapping:
            target_gender = gender_mapping[pronoun]
            
            # 从故事上下文获取性别信息
            if story_context:
                for candidate in candidates:
                    character = story_context.get_character(candidate)
                    if character and hasattr(character, 'gender'):
                        if character.gender == target_gender:
                            return candidate, 0.9
            
            # 基于名字推断性别（简化实现）
            for candidate in candidates:
                inferred_gender = self._infer_gender_from_name(candidate)
                if inferred_gender == target_gender:
                    return candidate, 0.7
        
        # 距离优先规则：选择最近提及的候选
        if candidates:
            return candidates[0], 0.6
        
        return None, 0.0
    
    def _resolve_possessive_pronoun(self, dialogue_entry: DialogueEntry,
                                   pronoun_ref: PronounReference,
                                   story_context: Optional[StoryContext] = None) -> Tuple[Optional[str], float]:
        """解析物主代词"""
        pronoun = pronoun_ref.pronoun
        
        # 物主代词到人称代词的映射
        possessive_mapping = {
            "我的": "我",
            "你的": "你", 
            "您的": "您",
            "他的": "他",
            "她的": "她",
            "它的": "它"
        }
        
        if pronoun in possessive_mapping:
            personal_pronoun = possessive_mapping[pronoun]
            
            # 创建临时的人称代词引用进行解析
            temp_pronoun_ref = PronounReference(
                pronoun=personal_pronoun,
                pronoun_type=PronounType.PERSONAL,
                position=pronoun_ref.position,
                candidates=pronoun_ref.candidates
            )
            
            return self._resolve_personal_pronoun(dialogue_entry, temp_pronoun_ref, story_context)
        
        return None, 0.0
    
    def _resolve_demonstrative_pronoun(self, dialogue_entry: DialogueEntry,
                                      pronoun_ref: PronounReference,
                                      story_context: Optional[StoryContext] = None) -> Tuple[Optional[str], float]:
        """解析指示代词"""
        # 指示代词通常指向最近提及的对象或概念
        recent_entities = []
        
        # 获取最近的实体
        context_window = self.dialogue_history.get_current_context(3)
        for entry in reversed(context_window):
            if entry == dialogue_entry:
                continue
            recent_entities.extend(entry.mentioned_entities)
        
        if recent_entities:
            return recent_entities[0], 0.5
        
        return None, 0.0
    
    def _resolve_relative_pronoun(self, dialogue_entry: DialogueEntry,
                                 pronoun_ref: PronounReference,
                                 story_context: Optional[StoryContext] = None) -> Tuple[Optional[str], float]:
        """解析关系代词"""
        # 关系代词的解析通常需要更复杂的语法分析
        # 这里提供简化实现
        
        pronoun = pronoun_ref.pronoun
        
        if pronoun == "谁":
            # 寻找人物候选
            person_candidates = []
            for candidate in pronoun_ref.candidates:
                if self._is_person(candidate, story_context):
                    person_candidates.append(candidate)
            
            if person_candidates:
                return person_candidates[0], 0.6
        
        return None, 0.0
    
    def _resolve_reflexive_pronoun(self, dialogue_entry: DialogueEntry,
                                  pronoun_ref: PronounReference,
                                  story_context: Optional[StoryContext] = None) -> Tuple[Optional[str], float]:
        """解析反身代词"""
        # 反身代词通常指向句子的主语（说话人）
        if dialogue_entry.speaker:
            return dialogue_entry.speaker, 0.8
        
        return None, 0.0
    
    def _infer_gender_from_name(self, name: str) -> Optional[str]:
        """从姓名推断性别（简化实现）"""
        # 这里可以集成更复杂的姓名性别推断逻辑
        male_indicators = ["先生", "男", "哥", "弟", "叔", "伯", "舅"]
        female_indicators = ["女士", "小姐", "女", "姐", "妹", "阿姨", "婶"]
        
        for indicator in male_indicators:
            if indicator in name:
                return "male"
        
        for indicator in female_indicators:
            if indicator in name:
                return "female"
        
        return None
    
    def _is_person(self, entity: str, story_context: Optional[StoryContext] = None) -> bool:
        """判断实体是否为人物"""
        if story_context:
            return entity in story_context.main_characters
        
        # 简单的人物判断逻辑
        person_indicators = ["先生", "女士", "小姐", "老师", "医生", "护士", "队长", "司令"]
        return any(indicator in entity for indicator in person_indicators)


class ContextCompressor:
    """上下文压缩器
    
    实现智能的上下文压缩和内存管理
    """
    
    def __init__(self, dialogue_history: DialogueHistory):
        self.dialogue_history = dialogue_history
        
        # 压缩策略配置
        self.compression_config = {
            "relevance_threshold": 0.3,    # 相关性阈值
            "time_decay_factor": 0.1,      # 时间衰减因子
            "speaker_importance_boost": 0.2, # 说话人重要性加成
            "entity_frequency_boost": 0.1   # 实体频率加成
        }
        
        logger.info("上下文压缩器初始化完成")
    
    def compress_context(self, target_size: int, strategy: str = "adaptive") -> Dict[str, Any]:
        """压缩上下文"""
        if strategy == "adaptive":
            return self._adaptive_compression(target_size)
        elif strategy == "relevance_based":
            return self._relevance_based_compression(target_size)
        elif strategy == "time_based":
            return self._time_based_compression(target_size)
        else:
            raise ValueError(f"未知的压缩策略: {strategy}")
    
    def _adaptive_compression(self, target_size: int) -> Dict[str, Any]:
        """自适应压缩策略"""
        entries = list(self.dialogue_history.dialogue_history)
        
        if len(entries) <= target_size:
            return {"compressed_entries": entries, "compression_ratio": 1.0}
        
        # 计算每个条目的综合重要性分数
        scored_entries = []
        
        for i, entry in enumerate(entries):
            score = self._calculate_importance_score(entry, i, len(entries))
            scored_entries.append((entry, score))
        
        # 按分数排序
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        # 选择top entries，但保证时间顺序
        selected_entries = [entry for entry, _ in scored_entries[:target_size]]
        selected_entries.sort(key=lambda x: x.timestamp)
        
        compression_ratio = len(selected_entries) / len(entries)
        
        return {
            "compressed_entries": selected_entries,
            "compression_ratio": compression_ratio,
            "removed_count": len(entries) - len(selected_entries)
        }
    
    def _calculate_importance_score(self, entry: DialogueEntry, position: int, total: int) -> float:
        """计算条目重要性分数"""
        score = 0.0
        
        # 基础相关性分数
        score += entry.context_score * 0.4
        
        # 时间位置分数（越新越重要）
        recency_score = position / total
        score += recency_score * 0.3
        
        # 说话人重要性
        if entry.speaker:
            speaker_frequency = len(self.dialogue_history.speaker_history.get(entry.speaker, []))
            speaker_score = min(speaker_frequency / 10.0, 1.0)  # 归一化
            score += speaker_score * self.compression_config["speaker_importance_boost"]
        
        # 实体重要性
        entity_score = 0.0
        for entity in entry.mentioned_entities:
            entity_frequency = len(self.dialogue_history.mentioned_entities.get(entity, []))
            entity_score += min(entity_frequency / 5.0, 1.0)
        
        if entry.mentioned_entities:
            entity_score /= len(entry.mentioned_entities)
            score += entity_score * self.compression_config["entity_frequency_boost"]
        
        # 代词解析重要性
        if entry.pronouns:
            resolved_count = len([p for p in entry.pronouns if p.resolved_reference])
            if resolved_count > 0:
                score += 0.1
        
        return min(score, 1.0)
    
    def _relevance_based_compression(self, target_size: int) -> Dict[str, Any]:
        """基于相关性的压缩"""
        entries = list(self.dialogue_history.dialogue_history)
        
        # 按相关性分数排序
        sorted_entries = sorted(entries, key=lambda x: x.context_score, reverse=True)
        selected_entries = sorted_entries[:target_size]
        
        # 恢复时间顺序
        selected_entries.sort(key=lambda x: x.timestamp)
        
        return {
            "compressed_entries": selected_entries,
            "compression_ratio": len(selected_entries) / len(entries),
            "removed_count": len(entries) - len(selected_entries)
        }
    
    def _time_based_compression(self, target_size: int) -> Dict[str, Any]:
        """基于时间的压缩（保留最新的）"""
        entries = list(self.dialogue_history.dialogue_history)
        selected_entries = entries[-target_size:] if len(entries) > target_size else entries
        
        return {
            "compressed_entries": selected_entries,
            "compression_ratio": len(selected_entries) / len(entries),
            "removed_count": len(entries) - len(selected_entries)
        }


# 全局实例
dialogue_tracker = DialogueHistory()
pronoun_resolver = PronounResolver(dialogue_tracker)
context_compressor = ContextCompressor(dialogue_tracker)


def get_dialogue_tracker() -> DialogueHistory:
    """获取对话跟踪器实例"""
    return dialogue_tracker


def get_pronoun_resolver() -> PronounResolver:
    """获取代词解析器实例"""
    return pronoun_resolver


def get_context_compressor() -> ContextCompressor:
    """获取上下文压缩器实例"""
    return context_compressor