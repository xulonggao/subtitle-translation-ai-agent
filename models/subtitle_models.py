"""
字幕相关数据模型
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SubtitleFormat(Enum):
    """字幕格式枚举"""
    SRT = "srt"
    ASS = "ass"
    VTT = "vtt"
    SSA = "ssa"


class SceneEmotion(Enum):
    """场景情感枚举"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    TENSE = "tense"
    ROMANTIC = "romantic"
    COMEDIC = "comedic"
    DRAMATIC = "dramatic"


class SpeechPace(Enum):
    """语速枚举"""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    VERY_FAST = "very_fast"


@dataclass
class TimeCode:
    """时间码类"""
    hours: int
    minutes: int
    seconds: int
    milliseconds: int
    
    def __post_init__(self):
        """验证时间码有效性"""
        if not (0 <= self.hours <= 23):
            raise ValueError(f"小时必须在0-23之间，得到: {self.hours}")
        if not (0 <= self.minutes <= 59):
            raise ValueError(f"分钟必须在0-59之间，得到: {self.minutes}")
        if not (0 <= self.seconds <= 59):
            raise ValueError(f"秒必须在0-59之间，得到: {self.seconds}")
        if not (0 <= self.milliseconds <= 999):
            raise ValueError(f"毫秒必须在0-999之间，得到: {self.milliseconds}")
    
    @classmethod
    def from_string(cls, time_str: str) -> 'TimeCode':
        """从字符串解析时间码
        
        支持格式: HH:MM:SS,mmm 或 HH:MM:SS.mmm
        """
        # 匹配SRT格式: 00:01:23,456
        srt_pattern = r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})'
        match = re.match(srt_pattern, time_str.strip())
        
        if not match:
            raise ValueError(f"无效的时间码格式: {time_str}")
        
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return cls(hours, minutes, seconds, milliseconds)
    
    def to_string(self, format_type: str = "srt") -> str:
        """转换为字符串格式"""
        if format_type.lower() == "srt":
            return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d},{self.milliseconds:03d}"
        elif format_type.lower() == "vtt":
            return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}.{self.milliseconds:03d}"
        else:
            return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d},{self.milliseconds:03d}"
    
    def to_milliseconds(self) -> int:
        """转换为总毫秒数"""
        return (
            self.hours * 3600000 +
            self.minutes * 60000 +
            self.seconds * 1000 +
            self.milliseconds
        )
    
    @classmethod
    def from_milliseconds(cls, ms: int) -> 'TimeCode':
        """从毫秒数创建时间码"""
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        milliseconds = ms % 1000
        
        return cls(hours, minutes, seconds, milliseconds)
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __lt__(self, other: 'TimeCode') -> bool:
        return self.to_milliseconds() < other.to_milliseconds()
    
    def __le__(self, other: 'TimeCode') -> bool:
        return self.to_milliseconds() <= other.to_milliseconds()
    
    def __gt__(self, other: 'TimeCode') -> bool:
        return self.to_milliseconds() > other.to_milliseconds()
    
    def __ge__(self, other: 'TimeCode') -> bool:
        return self.to_milliseconds() >= other.to_milliseconds()
    
    def __eq__(self, other: 'TimeCode') -> bool:
        return self.to_milliseconds() == other.to_milliseconds()


@dataclass
class SubtitleEntry:
    """字幕条目类"""
    index: int
    start_time: TimeCode
    end_time: TimeCode
    text: str
    
    # 可选属性
    speaker: Optional[str] = None
    context_tags: List[str] = field(default_factory=list)
    translation_cache: Dict[str, str] = field(default_factory=dict)
    
    # 字幕特有属性
    duration_seconds: float = field(init=False)
    character_count: int = field(init=False)
    scene_emotion: SceneEmotion = SceneEmotion.NEUTRAL
    speech_pace: SpeechPace = SpeechPace.NORMAL
    cultural_context: List[str] = field(default_factory=list)
    compression_level: float = 1.0  # 1.0=无压缩，0.5=高度压缩
    
    # 质量控制
    quality_score: Optional[float] = None
    needs_review: bool = False
    review_notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        self.duration_seconds = self.calculate_duration()
        self.character_count = len(self.text)
        
        # 验证时间码顺序
        if self.start_time >= self.end_time:
            raise ValueError(f"开始时间必须早于结束时间: {self.start_time} >= {self.end_time}")
    
    def calculate_duration(self) -> float:
        """计算显示时长（秒）"""
        # 支持float类型的时间（已经是秒）
        if isinstance(self.start_time, (int, float)) and isinstance(self.end_time, (int, float)):
            return float(self.end_time - self.start_time)
        
        # 支持时间码对象
        start_ms = self.start_time.to_milliseconds()
        end_ms = self.end_time.to_milliseconds()
        return (end_ms - start_ms) / 1000.0
    
    def calculate_reading_speed(self) -> float:
        """计算阅读速度（字符/秒）"""
        if self.duration_seconds <= 0:
            return 0.0
        return self.character_count / self.duration_seconds
    
    def is_reading_speed_appropriate(self, max_chars_per_second: float = 7.5) -> bool:
        """检查阅读速度是否合适"""
        return self.calculate_reading_speed() <= max_chars_per_second
    
    def get_translation(self, language: str) -> Optional[str]:
        """获取指定语言的翻译"""
        return self.translation_cache.get(language)
    
    def set_translation(self, language: str, translation: str, quality_score: Optional[float] = None):
        """设置指定语言的翻译"""
        self.translation_cache[language] = translation
        if quality_score is not None:
            self.quality_score = quality_score
    
    def add_context_tag(self, tag: str):
        """添加上下文标签"""
        if tag not in self.context_tags:
            self.context_tags.append(tag)
    
    def add_review_note(self, note: str):
        """添加审核备注"""
        self.review_notes.append(note)
        self.needs_review = True
    
    def to_srt_format(self, language: Optional[str] = None) -> str:
        """转换为SRT格式"""
        text = self.get_translation(language) if language else self.text
        if not text:
            text = self.text
        
        return f"{self.index}\n{self.start_time} --> {self.end_time}\n{text}\n"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "index": self.index,
            "start_time": self.start_time.to_string(),
            "end_time": self.end_time.to_string(),
            "text": self.text,
            "speaker": self.speaker,
            "context_tags": self.context_tags,
            "translation_cache": self.translation_cache,
            "duration_seconds": self.duration_seconds,
            "character_count": self.character_count,
            "scene_emotion": self.scene_emotion.value,
            "speech_pace": self.speech_pace.value,
            "cultural_context": self.cultural_context,
            "compression_level": self.compression_level,
            "quality_score": self.quality_score,
            "needs_review": self.needs_review,
            "review_notes": self.review_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtitleEntry':
        """从字典创建实例"""
        return cls(
            index=data["index"],
            start_time=TimeCode.from_string(data["start_time"]),
            end_time=TimeCode.from_string(data["end_time"]),
            text=data["text"],
            speaker=data.get("speaker"),
            context_tags=data.get("context_tags", []),
            translation_cache=data.get("translation_cache", {}),
            scene_emotion=SceneEmotion(data.get("scene_emotion", "neutral")),
            speech_pace=SpeechPace(data.get("speech_pace", "normal")),
            cultural_context=data.get("cultural_context", []),
            compression_level=data.get("compression_level", 1.0),
            quality_score=data.get("quality_score"),
            needs_review=data.get("needs_review", False),
            review_notes=data.get("review_notes", []),
        )


@dataclass
class SubtitleFile:
    """字幕文件类"""
    filename: str
    format: SubtitleFormat
    entries: List[SubtitleEntry]
    encoding: str = "utf-8"
    
    # 元数据
    title: Optional[str] = None
    language: str = "zh"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # 统计信息
    total_entries: int = field(init=False)
    total_duration: float = field(init=False)
    average_reading_speed: float = field(init=False)
    
    def __post_init__(self):
        """初始化后处理"""
        self.total_entries = len(self.entries)
        self.total_duration = self.calculate_total_duration()
        self.average_reading_speed = self.calculate_average_reading_speed()
        
        # 验证条目顺序
        self.validate_entry_order()
    
    def calculate_total_duration(self) -> float:
        """计算总时长"""
        if not self.entries:
            return 0.0
        
        first_start = self.entries[0].start_time.to_milliseconds()
        last_end = self.entries[-1].end_time.to_milliseconds()
        return (last_end - first_start) / 1000.0
    
    def calculate_average_reading_speed(self) -> float:
        """计算平均阅读速度"""
        if not self.entries:
            return 0.0
        
        total_chars = sum(entry.character_count for entry in self.entries)
        total_duration = sum(entry.duration_seconds for entry in self.entries)
        
        if total_duration <= 0:
            return 0.0
        
        return total_chars / total_duration
    
    def validate_entry_order(self):
        """验证条目时间顺序"""
        for i in range(1, len(self.entries)):
            prev_entry = self.entries[i-1]
            curr_entry = self.entries[i]
            
            if prev_entry.end_time > curr_entry.start_time:
                raise ValueError(f"字幕条目时间重叠: 条目{prev_entry.index}和{curr_entry.index}")
    
    def get_entries_by_timerange(self, start_time: TimeCode, end_time: TimeCode) -> List[SubtitleEntry]:
        """获取指定时间范围内的条目"""
        result = []
        for entry in self.entries:
            if (entry.start_time >= start_time and entry.start_time <= end_time) or \
               (entry.end_time >= start_time and entry.end_time <= end_time) or \
               (entry.start_time <= start_time and entry.end_time >= end_time):
                result.append(entry)
        return result
    
    def get_entries_by_speaker(self, speaker: str) -> List[SubtitleEntry]:
        """获取指定说话人的条目"""
        return [entry for entry in self.entries if entry.speaker == speaker]
    
    def get_problematic_entries(self, max_reading_speed: float = 7.5) -> List[SubtitleEntry]:
        """获取有问题的条目（阅读速度过快等）"""
        problematic = []
        for entry in self.entries:
            if not entry.is_reading_speed_appropriate(max_reading_speed):
                problematic.append(entry)
        return problematic
    
    def to_srt_content(self, language: Optional[str] = None) -> str:
        """转换为SRT文件内容"""
        content_parts = []
        for entry in self.entries:
            content_parts.append(entry.to_srt_format(language))
        return "\n".join(content_parts)
    
    def save_to_file(self, filepath: str, language: Optional[str] = None):
        """保存到文件"""
        content = self.to_srt_content(language)
        with open(filepath, 'w', encoding=self.encoding) as f:
            f.write(content)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        speakers = set(entry.speaker for entry in self.entries if entry.speaker)
        emotions = {}
        for entry in self.entries:
            emotion = entry.scene_emotion.value
            emotions[emotion] = emotions.get(emotion, 0) + 1
        
        return {
            "total_entries": self.total_entries,
            "total_duration": self.total_duration,
            "average_reading_speed": self.average_reading_speed,
            "unique_speakers": len(speakers),
            "speakers": list(speakers),
            "emotion_distribution": emotions,
            "entries_need_review": sum(1 for entry in self.entries if entry.needs_review),
            "available_languages": list(set(
                lang for entry in self.entries 
                for lang in entry.translation_cache.keys()
            )),
        }


@dataclass
class TranslationResult:
    """翻译结果类"""
    original_entry: SubtitleEntry
    target_language: str
    translated_text: str
    quality_score: float
    translation_time: datetime = field(default_factory=datetime.now)
    
    # 翻译元数据
    model_used: Optional[str] = None
    translation_method: str = "agent"  # agent, memory, manual
    confidence_score: Optional[float] = None
    
    # 质量指标
    fluency_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    cultural_adaptation_score: Optional[float] = None
    
    # 审核信息
    reviewed: bool = False
    reviewer: Optional[str] = None
    review_time: Optional[datetime] = None
    review_notes: List[str] = field(default_factory=list)
    
    def mark_as_reviewed(self, reviewer: str, notes: Optional[str] = None):
        """标记为已审核"""
        self.reviewed = True
        self.reviewer = reviewer
        self.review_time = datetime.now()
        if notes:
            self.review_notes.append(notes)
    
    def calculate_overall_quality(self) -> float:
        """计算综合质量分数"""
        scores = [score for score in [
            self.quality_score,
            self.fluency_score,
            self.accuracy_score,
            self.cultural_adaptation_score
        ] if score is not None]
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original_index": self.original_entry.index,
            "target_language": self.target_language,
            "translated_text": self.translated_text,
            "quality_score": self.quality_score,
            "translation_time": self.translation_time.isoformat(),
            "model_used": self.model_used,
            "translation_method": self.translation_method,
            "confidence_score": self.confidence_score,
            "fluency_score": self.fluency_score,
            "accuracy_score": self.accuracy_score,
            "cultural_adaptation_score": self.cultural_adaptation_score,
            "reviewed": self.reviewed,
            "reviewer": self.reviewer,
            "review_time": self.review_time.isoformat() if self.review_time else None,
            "review_notes": self.review_notes,
        }