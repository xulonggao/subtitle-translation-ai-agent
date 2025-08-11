#!/usr/bin/env python3
"""
在线编辑器管理器
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import structlog

from .models import (
    EditDocument, DocumentVersion, SubtitleEntry, EditChange, 
    ReviewComment, EditSession, ReviewTask, CollaborationEvent,
    EditStatus, ChangeType, ReviewStatus
)

logger = structlog.get_logger()

class EditorManager:
    """编辑器管理器"""
    
    def __init__(self):
        self.documents: Dict[str, EditDocument] = {}
        self.active_sessions: Dict[str, EditSession] = {}
        self.collaboration_events: List[CollaborationEvent] = []
        self.session_timeout = timedelta(minutes=30)
        
        # 启动会话清理任务
        self.cleanup_task = None
        self.start_cleanup_task()
        
        logger.info("编辑器管理器初始化完成")
    
    def start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_sessions():
            while True:
                try:
                    await self.cleanup_inactive_sessions()
                    await asyncio.sleep(300)  # 每5分钟清理一次
                except Exception as e:
                    logger.error("会话清理任务出错", error=str(e))
                    await asyncio.sleep(60)
        
        self.cleanup_task = asyncio.create_task(cleanup_sessions())
    
    async def cleanup_inactive_sessions(self):
        """清理非活跃会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.end_edit_session(session_id)
            logger.info("清理过期会话", session_id=session_id)
    
    async def create_document(self, title: str, project_id: str, 
                            source_language: str, target_language: str,
                            entries: List[SubtitleEntry], created_by: str) -> EditDocument:
        """创建编辑文档"""
        try:
            document = EditDocument(
                title=title,
                project_id=project_id,
                source_language=source_language,
                target_language=target_language,
                created_by=created_by
            )
            
            # 创建初始版本
            initial_version = DocumentVersion(
                version_number="1.0.0",
                document_id=document.id,
                entries=entries,
                created_by=created_by,
                description="初始版本",
                is_current=True
            )
            
            document.versions.append(initial_version)
            self.documents[document.id] = document
            
            # 记录协作事件
            await self.add_collaboration_event(
                document.id, created_by, "create",
                {"title": title, "entries_count": len(entries)}
            )
            
            logger.info("创建编辑文档", 
                       document_id=document.id,
                       title=title,
                       entries_count=len(entries))
            
            return document
            
        except Exception as e:
            logger.error("创建编辑文档失败", error=str(e))
            raise
    
    async def get_document(self, document_id: str) -> Optional[EditDocument]:
        """获取编辑文档"""
        return self.documents.get(document_id)
    
    async def list_documents(self, project_id: str = None, 
                           status: EditStatus = None) -> List[EditDocument]:
        """获取文档列表"""
        documents = list(self.documents.values())
        
        if project_id:
            documents = [doc for doc in documents if doc.project_id == project_id]
        
        if status:
            documents = [doc for doc in documents if doc.status == status]
        
        return documents
    
    async def start_edit_session(self, document_id: str, user_id: str, 
                               user_name: str) -> EditSession:
        """开始编辑会话"""
        try:
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"文档 {document_id} 不存在")
            
            # 检查是否已有活跃会话
            existing_session = None
            for session in document.active_sessions:
                if session.user_id == user_id and session.is_active:
                    existing_session = session
                    break
            
            if existing_session:
                # 更新现有会话
                existing_session.last_activity = datetime.now()
                session = existing_session
            else:
                # 创建新会话
                session = EditSession(
                    document_id=document_id,
                    user_id=user_id,
                    user_name=user_name
                )
                
                document.active_sessions.append(session)
                self.active_sessions[session.id] = session
            
            # 记录协作事件
            await self.add_collaboration_event(
                document_id, user_id, "join",
                {"user_name": user_name}
            )
            
            logger.info("开始编辑会话", 
                       session_id=session.id,
                       document_id=document_id,
                       user_name=user_name)
            
            return session
            
        except Exception as e:
            logger.error("开始编辑会话失败", error=str(e))
            raise
    
    async def end_edit_session(self, session_id: str):
        """结束编辑会话"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return
            
            session.is_active = False
            
            # 解锁所有锁定的条目
            document = await self.get_document(session.document_id)
            if document:
                current_version = document.get_current_version()
                if current_version:
                    for entry in current_version.entries:
                        if entry.id in session.locked_entries:
                            entry.is_locked = False
            
            # 从活跃会话中移除
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # 记录协作事件
            await self.add_collaboration_event(
                session.document_id, session.user_id, "leave",
                {"user_name": session.user_name}
            )
            
            logger.info("结束编辑会话", session_id=session_id)
            
        except Exception as e:
            logger.error("结束编辑会话失败", error=str(e))
    
    async def update_session_activity(self, session_id: str):
        """更新会话活动时间"""
        session = self.active_sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
    
    async def lock_entry(self, session_id: str, entry_id: str) -> bool:
        """锁定条目"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            
            document = await self.get_document(session.document_id)
            if not document:
                return False
            
            current_version = document.get_current_version()
            if not current_version:
                return False
            
            # 查找条目
            entry = None
            for e in current_version.entries:
                if e.id == entry_id:
                    entry = e
                    break
            
            if not entry:
                return False
            
            # 检查是否已被其他用户锁定
            if entry.is_locked and entry_id not in session.locked_entries:
                return False
            
            # 锁定条目
            entry.is_locked = True
            if entry_id not in session.locked_entries:
                session.locked_entries.append(entry_id)
            
            await self.update_session_activity(session_id)
            
            logger.debug("锁定条目", 
                        session_id=session_id,
                        entry_id=entry_id)
            
            return True
            
        except Exception as e:
            logger.error("锁定条目失败", error=str(e))
            return False
    
    async def unlock_entry(self, session_id: str, entry_id: str) -> bool:
        """解锁条目"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            
            document = await self.get_document(session.document_id)
            if not document:
                return False
            
            current_version = document.get_current_version()
            if not current_version:
                return False
            
            # 查找条目
            entry = None
            for e in current_version.entries:
                if e.id == entry_id:
                    entry = e
                    break
            
            if not entry:
                return False
            
            # 只能解锁自己锁定的条目
            if entry_id not in session.locked_entries:
                return False
            
            # 解锁条目
            entry.is_locked = False
            session.locked_entries.remove(entry_id)
            
            await self.update_session_activity(session_id)
            
            logger.debug("解锁条目", 
                        session_id=session_id,
                        entry_id=entry_id)
            
            return True
            
        except Exception as e:
            logger.error("解锁条目失败", error=str(e))
            return False
    
    async def edit_entry(self, session_id: str, entry_id: str, 
                        field_name: str, new_value: str, 
                        comment: str = "") -> bool:
        """编辑条目"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            
            document = await self.get_document(session.document_id)
            if not document:
                return False
            
            current_version = document.get_current_version()
            if not current_version:
                return False
            
            # 查找条目
            entry = None
            for e in current_version.entries:
                if e.id == entry_id:
                    entry = e
                    break
            
            if not entry:
                return False
            
            # 检查是否有编辑权限
            if entry.is_locked and entry_id not in session.locked_entries:
                return False
            
            # 获取旧值
            old_value = getattr(entry, field_name, "")
            
            # 更新条目
            setattr(entry, field_name, new_value)
            entry.updated_at = datetime.now()
            entry.updated_by = session.user_id
            
            # 记录变更
            change = EditChange(
                entry_id=entry_id,
                change_type=ChangeType.MODIFY,
                field_name=field_name,
                old_value=str(old_value),
                new_value=str(new_value),
                user_id=session.user_id,
                user_name=session.user_name,
                comment=comment
            )
            
            current_version.changes.append(change)
            document.updated_at = datetime.now()
            
            # 记录协作事件
            await self.add_collaboration_event(
                document.id, session.user_id, "edit",
                {
                    "entry_id": entry_id,
                    "field_name": field_name,
                    "user_name": session.user_name
                }
            )
            
            await self.update_session_activity(session_id)
            
            logger.info("编辑条目", 
                       session_id=session_id,
                       entry_id=entry_id,
                       field_name=field_name)
            
            return True
            
        except Exception as e:
            logger.error("编辑条目失败", error=str(e))
            return False
    
    async def add_comment(self, document_id: str, entry_id: str,
                         reviewer_id: str, reviewer_name: str,
                         comment: str, suggestion: str = "",
                         severity: str = "info") -> ReviewComment:
        """添加审核评论"""
        try:
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"文档 {document_id} 不存在")
            
            review_comment = ReviewComment(
                entry_id=entry_id,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                comment=comment,
                suggestion=suggestion,
                severity=severity
            )
            
            document.comments.append(review_comment)
            
            # 记录协作事件
            await self.add_collaboration_event(
                document_id, reviewer_id, "comment",
                {
                    "entry_id": entry_id,
                    "reviewer_name": reviewer_name,
                    "severity": severity
                }
            )
            
            logger.info("添加审核评论", 
                       document_id=document_id,
                       entry_id=entry_id,
                       reviewer_name=reviewer_name)
            
            return review_comment
            
        except Exception as e:
            logger.error("添加审核评论失败", error=str(e))
            raise
    
    async def resolve_comment(self, document_id: str, comment_id: str,
                            resolved_by: str) -> bool:
        """解决评论"""
        try:
            document = await self.get_document(document_id)
            if not document:
                return False
            
            # 查找评论
            comment = None
            for c in document.comments:
                if c.id == comment_id:
                    comment = c
                    break
            
            if not comment:
                return False
            
            comment.is_resolved = True
            comment.resolved_at = datetime.now()
            comment.resolved_by = resolved_by
            
            logger.info("解决评论", 
                       document_id=document_id,
                       comment_id=comment_id,
                       resolved_by=resolved_by)
            
            return True
            
        except Exception as e:
            logger.error("解决评论失败", error=str(e))
            return False
    
    async def create_version(self, document_id: str, created_by: str,
                           description: str = "") -> DocumentVersion:
        """创建新版本"""
        try:
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"文档 {document_id} 不存在")
            
            current_version = document.get_current_version()
            if not current_version:
                raise ValueError("没有当前版本")
            
            # 生成新版本号
            version_parts = current_version.version_number.split('.')
            major, minor, patch = int(version_parts[0]), int(version_parts[1]), int(version_parts[2])
            new_version_number = f"{major}.{minor}.{patch + 1}"
            
            # 创建新版本（深拷贝条目）
            new_entries = []
            for entry in current_version.entries:
                new_entry = SubtitleEntry(
                    sequence=entry.sequence,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    original_text=entry.original_text,
                    translated_text=entry.translated_text,
                    notes=entry.notes,
                    confidence_score=entry.confidence_score,
                    updated_by=entry.updated_by
                )
                new_entries.append(new_entry)
            
            new_version = DocumentVersion(
                version_number=new_version_number,
                document_id=document_id,
                entries=new_entries,
                created_by=created_by,
                description=description,
                is_current=True
            )
            
            # 设置旧版本为非当前版本
            current_version.is_current = False
            
            document.versions.append(new_version)
            document.current_version = new_version_number
            document.updated_at = datetime.now()
            
            logger.info("创建新版本", 
                       document_id=document_id,
                       version_number=new_version_number,
                       created_by=created_by)
            
            return new_version
            
        except Exception as e:
            logger.error("创建新版本失败", error=str(e))
            raise
    
    async def assign_reviewer(self, document_id: str, reviewer_id: str,
                            reviewer_name: str, due_date: datetime = None) -> ReviewTask:
        """分配审核员"""
        try:
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"文档 {document_id} 不存在")
            
            # 添加到分配的审核员列表
            if reviewer_id not in document.assigned_reviewers:
                document.assigned_reviewers.append(reviewer_id)
            
            # 创建审核任务
            review_task = ReviewTask(
                document_id=document_id,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                due_date=due_date
            )
            
            logger.info("分配审核员", 
                       document_id=document_id,
                       reviewer_name=reviewer_name)
            
            return review_task
            
        except Exception as e:
            logger.error("分配审核员失败", error=str(e))
            raise
    
    async def update_document_status(self, document_id: str, 
                                   new_status: EditStatus) -> bool:
        """更新文档状态"""
        try:
            document = await self.get_document(document_id)
            if not document:
                return False
            
            old_status = document.status
            document.status = new_status
            document.updated_at = datetime.now()
            
            logger.info("更新文档状态", 
                       document_id=document_id,
                       old_status=old_status.value,
                       new_status=new_status.value)
            
            return True
            
        except Exception as e:
            logger.error("更新文档状态失败", error=str(e))
            return False
    
    async def add_collaboration_event(self, document_id: str, user_id: str,
                                    event_type: str, details: Dict[str, Any]):
        """添加协作事件"""
        try:
            event = CollaborationEvent(
                document_id=document_id,
                user_id=user_id,
                user_name=details.get("user_name", ""),
                event_type=event_type,
                details=details
            )
            
            self.collaboration_events.append(event)
            
            # 限制事件数量
            if len(self.collaboration_events) > 1000:
                self.collaboration_events = self.collaboration_events[-1000:]
            
        except Exception as e:
            logger.error("添加协作事件失败", error=str(e))
    
    async def get_collaboration_events(self, document_id: str,
                                     limit: int = 100) -> List[CollaborationEvent]:
        """获取协作事件"""
        events = [event for event in self.collaboration_events 
                 if event.document_id == document_id]
        
        # 按时间倒序排列
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return events[:limit]
    
    async def export_document(self, document_id: str, 
                            format_type: str = "srt") -> str:
        """导出文档"""
        try:
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"文档 {document_id} 不存在")
            
            entries = document.get_entries()
            if not entries:
                return ""
            
            if format_type.lower() == "srt":
                return self._export_to_srt(entries)
            elif format_type.lower() == "vtt":
                return self._export_to_vtt(entries)
            elif format_type.lower() == "json":
                return self._export_to_json(entries)
            else:
                raise ValueError(f"不支持的格式: {format_type}")
            
        except Exception as e:
            logger.error("导出文档失败", error=str(e))
            raise
    
    def _export_to_srt(self, entries: List[SubtitleEntry]) -> str:
        """导出为SRT格式"""
        lines = []
        for entry in sorted(entries, key=lambda x: x.sequence):
            lines.append(str(entry.sequence))
            lines.append(f"{entry.start_time} --> {entry.end_time}")
            lines.append(entry.translated_text)
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_to_vtt(self, entries: List[SubtitleEntry]) -> str:
        """导出为VTT格式"""
        lines = ["WEBVTT", ""]
        
        for entry in sorted(entries, key=lambda x: x.sequence):
            # 转换时间格式
            start_time = entry.start_time.replace(',', '.')
            end_time = entry.end_time.replace(',', '.')
            
            lines.append(f"{start_time} --> {end_time}")
            lines.append(entry.translated_text)
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_to_json(self, entries: List[SubtitleEntry]) -> str:
        """导出为JSON格式"""
        data = [entry.to_dict() for entry in sorted(entries, key=lambda x: x.sequence)]
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            total_documents = len(self.documents)
            active_sessions = len(self.active_sessions)
            
            # 按状态统计文档
            status_counts = {}
            for doc in self.documents.values():
                status = doc.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # 统计评论
            total_comments = sum(len(doc.comments) for doc in self.documents.values())
            unresolved_comments = sum(
                len([c for c in doc.comments if not c.is_resolved])
                for doc in self.documents.values()
            )
            
            return {
                "total_documents": total_documents,
                "active_sessions": active_sessions,
                "status_distribution": status_counts,
                "total_comments": total_comments,
                "unresolved_comments": unresolved_comments,
                "collaboration_events": len(self.collaboration_events)
            }
            
        except Exception as e:
            logger.error("获取统计信息失败", error=str(e))
            return {}
    
    def __del__(self):
        """析构函数"""
        if self.cleanup_task:
            self.cleanup_task.cancel()