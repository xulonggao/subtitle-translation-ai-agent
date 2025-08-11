#!/usr/bin/env python3
"""
编辑器数据模型
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

class EditStatus(Enum):
    """编辑状态"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"

class ChangeType(Enum):
    """变更类型"""
    INSERT = "insert"
    DELETE = "delete"
    MODIFY = "modify"
    MOVE = "move"

class ReviewStatus(Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

@dataclass
class SubtitleEntry:
    """字幕条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int = 0
    start_time: str = ""  # 格式: "00:00:01,000"
    end_time: str = ""    # 格式: "00:00:03,000"
    original_text: str = ""
    translated_text: str = ""
    notes: str = ""
    confidence_score: float = 0.0
    is_locked: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    updated_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "sequence": self.sequence,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "notes": self.notes,
            "confidence_score": self.confidence_score,
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "updated_by": self.updated_by
        }

@dataclass
class EditChange:
    """编辑变更记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entry_id: str = ""
    change_type: ChangeType = ChangeType.MODIFY
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str = ""
    user_name: str = ""
    comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "change_type": self.change_type.value,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "comment": self.comment
        }

@dataclass
class DocumentVersion:
    """文档版本"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version_number: str = "1.0.0"
    document_id: str = ""
    entries: List[SubtitleEntry] = field(default_factory=list)
    changes: List[EditChange] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    description: str = ""
    is_current: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "version_number": self.version_number,
            "document_id": self.document_id,
            "entries": [entry.to_dict() for entry in self.entries],
            "changes": [change.to_dict() for change in self.changes],
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "is_current": self.is_current
        }

@dataclass
class ReviewComment:
    """审核评论"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entry_id: str = ""
    reviewer_id: str = ""
    reviewer_name: str = ""
    comment: str = ""
    suggestion: str = ""
    severity: str = "info"  # info, warning, error
    is_resolved: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolved_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "comment": self.comment,
            "suggestion": self.suggestion,
            "severity": self.severity,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by
        }

@dataclass
class EditSession:
    """编辑会话"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    user_id: str = ""
    user_name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    locked_entries: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active,
            "locked_entries": self.locked_entries
        }

@dataclass
class EditDocument:
    """编辑文档"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    project_id: str = ""
    source_language: str = ""
    target_language: str = ""
    status: EditStatus = EditStatus.DRAFT
    current_version: str = "1.0.0"
    versions: List[DocumentVersion] = field(default_factory=list)
    comments: List[ReviewComment] = field(default_factory=list)
    active_sessions: List[EditSession] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    assigned_reviewers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_current_version(self) -> Optional[DocumentVersion]:
        """获取当前版本"""
        for version in self.versions:
            if version.is_current:
                return version
        return None
    
    def get_entries(self) -> List[SubtitleEntry]:
        """获取当前版本的条目"""
        current_version = self.get_current_version()
        return current_version.entries if current_version else []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "project_id": self.project_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "status": self.status.value,
            "current_version": self.current_version,
            "versions": [version.to_dict() for version in self.versions],
            "comments": [comment.to_dict() for comment in self.comments],
            "active_sessions": [session.to_dict() for session in self.active_sessions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "assigned_reviewers": self.assigned_reviewers,
            "metadata": self.metadata
        }

@dataclass
class ReviewTask:
    """审核任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    reviewer_id: str = ""
    reviewer_name: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    review_notes: str = ""
    overall_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "status": self.status.value,
            "assigned_at": self.assigned_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "review_notes": self.review_notes,
            "overall_score": self.overall_score
        }

@dataclass
class CollaborationEvent:
    """协作事件"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    user_id: str = ""
    user_name: str = ""
    event_type: str = ""  # join, leave, edit, comment, review
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "event_type": self.event_type,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }