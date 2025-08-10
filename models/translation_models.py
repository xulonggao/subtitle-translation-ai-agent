"""
翻译相关数据模型
"""
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .subtitle_models import SubtitleEntry
from .story_models import StoryContext


class TranslationStatus(Enum):
    """翻译状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


class TranslationMethod(Enum):
    """翻译方法枚举"""
    AGENT = "agent"              # Agent翻译
    MEMORY = "memory"            # 翻译记忆
    MANUAL = "manual"            # 人工翻译
    HYBRID = "hybrid"            # 混合方法


class QualityLevel(Enum):
    """质量等级枚举"""
    EXCELLENT = "excellent"      # 优秀 (0.9-1.0)
    GOOD = "good"               # 良好 (0.8-0.9)
    ACCEPTABLE = "acceptable"    # 可接受 (0.7-0.8)
    POOR = "poor"               # 较差 (0.6-0.7)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (<0.6)


@dataclass
class TerminologyEntry:
    """术语条目类"""
    source_term: str
    target_language: str
    target_term: str
    
    # 上下文信息
    context: str = ""
    domain: str = "general"  # general, military, medical, legal等
    
    # 使用频率和置信度
    usage_count: int = 0
    confidence_score: float = 1.0
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    # 变体和同义词
    variants: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    
    # 文化适配信息
    cultural_notes: str = ""
    formality_level: str = "neutral"  # formal, neutral, informal
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
        self.updated_at = datetime.now()
    
    def update_confidence(self, new_score: float):
        """更新置信度"""
        # 使用加权平均更新置信度
        weight = min(self.usage_count, 10) / 10  # 最多考虑10次使用
        self.confidence_score = (self.confidence_score * weight + new_score * (1 - weight))
        self.updated_at = datetime.now()
    
    def add_variant(self, variant: str):
        """添加变体"""
        if variant not in self.variants:
            self.variants.append(variant)
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_term": self.source_term,
            "target_language": self.target_language,
            "target_term": self.target_term,
            "context": self.context,
            "domain": self.domain,
            "usage_count": self.usage_count,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "variants": self.variants,
            "synonyms": self.synonyms,
            "cultural_notes": self.cultural_notes,
            "formality_level": self.formality_level,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerminologyEntry':
        """从字典创建实例"""
        entry = cls(
            source_term=data["source_term"],
            target_language=data["target_language"],
            target_term=data["target_term"],
            context=data.get("context", ""),
            domain=data.get("domain", "general"),
            usage_count=data.get("usage_count", 0),
            confidence_score=data.get("confidence_score", 1.0),
            created_by=data.get("created_by", "system"),
            variants=data.get("variants", []),
            synonyms=data.get("synonyms", []),
            cultural_notes=data.get("cultural_notes", ""),
            formality_level=data.get("formality_level", "neutral"),
        )
        
        if "created_at" in data:
            entry.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            entry.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return entry


@dataclass
class TranslationMemory:
    """翻译记忆类"""
    source_text: str
    target_language: str
    target_text: str
    
    # 上下文信息
    context_hash: str = ""  # 上下文的哈希值，用于匹配相似上下文
    speaker: Optional[str] = None
    scene_type: str = "dialogue"
    
    # 质量和使用信息
    quality_score: float = 1.0
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    project_id: Optional[str] = None
    episode_id: Optional[str] = None
    
    # 相似度匹配参数
    fuzzy_threshold: float = 0.8  # 模糊匹配阈值
    
    def calculate_similarity(self, other_text: str) -> float:
        """计算与另一个文本的相似度"""
        # 简单的相似度计算，实际应用中可以使用更复杂的算法
        if self.source_text == other_text:
            return 1.0
        
        # 计算字符级别的相似度
        longer = max(len(self.source_text), len(other_text))
        if longer == 0:
            return 1.0
        
        # 使用编辑距离计算相似度
        distance = self._levenshtein_distance(self.source_text, other_text)
        return (longer - distance) / longer
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def is_fuzzy_match(self, text: str) -> bool:
        """判断是否为模糊匹配"""
        return self.calculate_similarity(text) >= self.fuzzy_threshold
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
        self.last_used = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_text": self.source_text,
            "target_language": self.target_language,
            "target_text": self.target_text,
            "context_hash": self.context_hash,
            "speaker": self.speaker,
            "scene_type": self.scene_type,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat(),
            "created_at": self.created_at.isoformat(),
            "project_id": self.project_id,
            "episode_id": self.episode_id,
            "fuzzy_threshold": self.fuzzy_threshold,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationMemory':
        """从字典创建实例"""
        memory = cls(
            source_text=data["source_text"],
            target_language=data["target_language"],
            target_text=data["target_text"],
            context_hash=data.get("context_hash", ""),
            speaker=data.get("speaker"),
            scene_type=data.get("scene_type", "dialogue"),
            quality_score=data.get("quality_score", 1.0),
            usage_count=data.get("usage_count", 0),
            project_id=data.get("project_id"),
            episode_id=data.get("episode_id"),
            fuzzy_threshold=data.get("fuzzy_threshold", 0.8),
        )
        
        if "last_used" in data:
            memory.last_used = datetime.fromisoformat(data["last_used"])
        if "created_at" in data:
            memory.created_at = datetime.fromisoformat(data["created_at"])
        
        return memory


@dataclass
class TranslationTask:
    """翻译任务类"""
    task_id: str
    project_id: str
    source_language: str
    target_languages: List[str]
    
    # 任务内容
    subtitle_entries: List[SubtitleEntry]
    story_context: StoryContext
    
    # 任务配置
    quality_threshold: float = 0.8
    batch_size: int = 10
    use_translation_memory: bool = True
    use_terminology: bool = True
    
    # 任务状态
    status: TranslationStatus = TranslationStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果统计
    total_entries: int = field(init=False)
    completed_entries: int = 0
    failed_entries: int = 0
    
    # 质量统计
    average_quality_score: float = 0.0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 错误信息
    error_messages: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        self.total_entries = len(self.subtitle_entries)
    
    def start_task(self):
        """开始任务"""
        self.status = TranslationStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def complete_task(self):
        """完成任务"""
        self.status = TranslationStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 1.0
    
    def fail_task(self, error_message: str):
        """任务失败"""
        self.status = TranslationStatus.FAILED
        self.error_messages.append(error_message)
    
    def update_progress(self, completed: int, failed: int = 0):
        """更新进度"""
        self.completed_entries = completed
        self.failed_entries = failed
        self.progress = (completed + failed) / self.total_entries if self.total_entries > 0 else 0.0
    
    def add_quality_score(self, score: float):
        """添加质量分数"""
        # 更新平均质量分数
        total_scores = self.completed_entries * self.average_quality_score + score
        self.average_quality_score = total_scores / (self.completed_entries + 1)
        
        # 更新质量分布
        quality_level = self._get_quality_level(score)
        self.quality_distribution[quality_level] = self.quality_distribution.get(quality_level, 0) + 1
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT.value
        elif score >= 0.8:
            return QualityLevel.GOOD.value
        elif score >= 0.7:
            return QualityLevel.ACCEPTABLE.value
        elif score >= 0.6:
            return QualityLevel.POOR.value
        else:
            return QualityLevel.UNACCEPTABLE.value
    
    def get_estimated_completion_time(self) -> Optional[datetime]:
        """估算完成时间"""
        if not self.started_at or self.progress <= 0:
            return None
        
        elapsed = datetime.now() - self.started_at
        estimated_total = elapsed / self.progress
        return self.started_at + estimated_total
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "progress": self.progress,
            "total_entries": self.total_entries,
            "completed_entries": self.completed_entries,
            "failed_entries": self.failed_entries,
            "average_quality_score": self.average_quality_score,
            "quality_distribution": self.quality_distribution,
            "target_languages": self.target_languages,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion": self.get_estimated_completion_time().isoformat() if self.get_estimated_completion_time() else None,
            "error_count": len(self.error_messages),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "source_language": self.source_language,
            "target_languages": self.target_languages,
            "quality_threshold": self.quality_threshold,
            "batch_size": self.batch_size,
            "use_translation_memory": self.use_translation_memory,
            "use_terminology": self.use_terminology,
            "status": self.status.value,
            "progress": self.progress,
            "total_entries": self.total_entries,
            "completed_entries": self.completed_entries,
            "failed_entries": self.failed_entries,
            "average_quality_score": self.average_quality_score,
            "quality_distribution": self.quality_distribution,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_messages": self.error_messages,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], subtitle_entries: List[SubtitleEntry], story_context: StoryContext) -> 'TranslationTask':
        """从字典创建实例"""
        task = cls(
            task_id=data["task_id"],
            project_id=data["project_id"],
            source_language=data["source_language"],
            target_languages=data["target_languages"],
            subtitle_entries=subtitle_entries,
            story_context=story_context,
            quality_threshold=data.get("quality_threshold", 0.8),
            batch_size=data.get("batch_size", 10),
            use_translation_memory=data.get("use_translation_memory", True),
            use_terminology=data.get("use_terminology", True),
            status=TranslationStatus(data.get("status", "pending")),
            progress=data.get("progress", 0.0),
            completed_entries=data.get("completed_entries", 0),
            failed_entries=data.get("failed_entries", 0),
            average_quality_score=data.get("average_quality_score", 0.0),
            quality_distribution=data.get("quality_distribution", {}),
            error_messages=data.get("error_messages", []),
        )
        
        if "created_at" in data:
            task.created_at = datetime.fromisoformat(data["created_at"])
        if "started_at" in data and data["started_at"]:
            task.started_at = datetime.fromisoformat(data["started_at"])
        if "completed_at" in data and data["completed_at"]:
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        return task


@dataclass
class TranslationBatch:
    """翻译批次类"""
    batch_id: str
    task_id: str
    entries: List[SubtitleEntry]
    target_language: str
    
    # 批次状态
    status: TranslationStatus = TranslationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    def start_batch(self):
        """开始批次处理"""
        self.status = TranslationStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def complete_batch(self):
        """完成批次处理"""
        self.status = TranslationStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def add_result(self, entry_index: int, translation: str, quality_score: float, method: TranslationMethod):
        """添加翻译结果"""
        self.results.append({
            "entry_index": entry_index,
            "translation": translation,
            "quality_score": quality_score,
            "method": method.value,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_average_quality(self) -> float:
        """获取平均质量分数"""
        if not self.results:
            return 0.0
        
        total_score = sum(result["quality_score"] for result in self.results)
        return total_score / len(self.results)