#!/usr/bin/env python3
"""
编辑器API端点
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import asyncio
import structlog

from .editor_manager import EditorManager
from .models import (
    EditDocument, SubtitleEntry, EditStatus, ReviewStatus,
    EditChange, ReviewComment, EditSession, CollaborationEvent
)

logger = structlog.get_logger()

# 创建路由器
router = APIRouter(prefix="/editor", tags=["编辑器"])

# 全局编辑器管理器实例
editor_manager = EditorManager()

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.document_subscribers: Dict[str, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # 从文档订阅中移除
        for doc_id, subscribers in self.document_subscribers.items():
            if session_id in subscribers:
                subscribers.remove(session_id)
    
    async def subscribe_to_document(self, session_id: str, document_id: str):
        if document_id not in self.document_subscribers:
            self.document_subscribers[document_id] = []
        
        if session_id not in self.document_subscribers[document_id]:
            self.document_subscribers[document_id].append(session_id)
    
    async def broadcast_to_document(self, document_id: str, message: dict):
        if document_id in self.document_subscribers:
            for session_id in self.document_subscribers[document_id]:
                if session_id in self.active_connections:
                    try:
                        await self.active_connections[session_id].send_text(
                            json.dumps(message)
                        )
                    except Exception as e:
                        logger.error("WebSocket广播失败", 
                                   session_id=session_id, error=str(e))

connection_manager = ConnectionManager()

# API端点定义

@router.post("/documents", response_model=dict)
async def create_document(
    title: str,
    project_id: str,
    source_language: str,
    target_language: str,
    entries_data: List[dict],
    created_by: str
):
    """创建编辑文档"""
    try:
        # 转换条目数据
        entries = []
        for entry_data in entries_data:
            entry = SubtitleEntry(
                sequence=entry_data.get("sequence", 0),
                start_time=entry_data.get("start_time", ""),
                end_time=entry_data.get("end_time", ""),
                original_text=entry_data.get("original_text", ""),
                translated_text=entry_data.get("translated_text", ""),
                confidence_score=entry_data.get("confidence_score", 0.0)
            )
            entries.append(entry)
        
        document = await editor_manager.create_document(
            title=title,
            project_id=project_id,
            source_language=source_language,
            target_language=target_language,
            entries=entries,
            created_by=created_by
        )
        
        return {"success": True, "document": document.to_dict()}
        
    except Exception as e:
        logger.error("创建文档失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=dict)
async def list_documents(
    project_id: Optional[str] = None,
    status: Optional[str] = None
):
    """获取文档列表"""
    try:
        status_enum = EditStatus(status) if status else None
        documents = await editor_manager.list_documents(project_id, status_enum)
        
        return {
            "success": True,
            "documents": [doc.to_dict() for doc in documents]
        }
        
    except Exception as e:
        logger.error("获取文档列表失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", response_model=dict)
async def get_document(document_id: str):
    """获取文档详情"""
    try:
        document = await editor_manager.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return {"success": True, "document": document.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取文档失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions", response_model=dict)
async def start_edit_session(
    document_id: str,
    user_id: str,
    user_name: str
):
    """开始编辑会话"""
    try:
        session = await editor_manager.start_edit_session(
            document_id, user_id, user_name
        )
        
        return {"success": True, "session": session.to_dict()}
        
    except Exception as e:
        logger.error("开始编辑会话失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}", response_model=dict)
async def end_edit_session(session_id: str):
    """结束编辑会话"""
    try:
        await editor_manager.end_edit_session(session_id)
        return {"success": True, "message": "编辑会话已结束"}
        
    except Exception as e:
        logger.error("结束编辑会话失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/lock", response_model=dict)
async def lock_entry(session_id: str, entry_id: str):
    """锁定条目"""
    try:
        success = await editor_manager.lock_entry(session_id, entry_id)
        
        if success:
            # 广播锁定事件
            await connection_manager.broadcast_to_document(
                session_id,  # 这里需要获取document_id
                {
                    "type": "entry_locked",
                    "entry_id": entry_id,
                    "session_id": session_id
                }
            )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("锁定条目失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/unlock", response_model=dict)
async def unlock_entry(session_id: str, entry_id: str):
    """解锁条目"""
    try:
        success = await editor_manager.unlock_entry(session_id, entry_id)
        
        if success:
            # 广播解锁事件
            await connection_manager.broadcast_to_document(
                session_id,  # 这里需要获取document_id
                {
                    "type": "entry_unlocked",
                    "entry_id": entry_id,
                    "session_id": session_id
                }
            )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("解锁条目失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sessions/{session_id}/entries/{entry_id}", response_model=dict)
async def edit_entry(
    session_id: str,
    entry_id: str,
    field_name: str,
    new_value: str,
    comment: str = ""
):
    """编辑条目"""
    try:
        success = await editor_manager.edit_entry(
            session_id, entry_id, field_name, new_value, comment
        )
        
        if success:
            # 广播编辑事件
            await connection_manager.broadcast_to_document(
                session_id,  # 这里需要获取document_id
                {
                    "type": "entry_edited",
                    "entry_id": entry_id,
                    "field_name": field_name,
                    "new_value": new_value,
                    "session_id": session_id
                }
            )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("编辑条目失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/comments", response_model=dict)
async def add_comment(
    document_id: str,
    entry_id: str,
    reviewer_id: str,
    reviewer_name: str,
    comment: str,
    suggestion: str = "",
    severity: str = "info"
):
    """添加审核评论"""
    try:
        review_comment = await editor_manager.add_comment(
            document_id, entry_id, reviewer_id, reviewer_name,
            comment, suggestion, severity
        )
        
        # 广播评论事件
        await connection_manager.broadcast_to_document(
            document_id,
            {
                "type": "comment_added",
                "comment": review_comment.to_dict()
            }
        )
        
        return {"success": True, "comment": review_comment.to_dict()}
        
    except Exception as e:
        logger.error("添加评论失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}/comments/{comment_id}/resolve", response_model=dict)
async def resolve_comment(
    document_id: str,
    comment_id: str,
    resolved_by: str
):
    """解决评论"""
    try:
        success = await editor_manager.resolve_comment(
            document_id, comment_id, resolved_by
        )
        
        if success:
            # 广播评论解决事件
            await connection_manager.broadcast_to_document(
                document_id,
                {
                    "type": "comment_resolved",
                    "comment_id": comment_id,
                    "resolved_by": resolved_by
                }
            )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("解决评论失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/versions", response_model=dict)
async def create_version(
    document_id: str,
    created_by: str,
    description: str = ""
):
    """创建新版本"""
    try:
        version = await editor_manager.create_version(
            document_id, created_by, description
        )
        
        return {"success": True, "version": version.to_dict()}
        
    except Exception as e:
        logger.error("创建版本失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}/status", response_model=dict)
async def update_document_status(
    document_id: str,
    new_status: str
):
    """更新文档状态"""
    try:
        status_enum = EditStatus(new_status)
        success = await editor_manager.update_document_status(
            document_id, status_enum
        )
        
        if success:
            # 广播状态更新事件
            await connection_manager.broadcast_to_document(
                document_id,
                {
                    "type": "status_updated",
                    "new_status": new_status
                }
            )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("更新文档状态失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/export", response_model=dict)
async def export_document(
    document_id: str,
    format_type: str = "srt"
):
    """导出文档"""
    try:
        content = await editor_manager.export_document(document_id, format_type)
        
        return {
            "success": True,
            "content": content,
            "format": format_type
        }
        
    except Exception as e:
        logger.error("导出文档失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/collaboration", response_model=dict)
async def get_collaboration_events(
    document_id: str,
    limit: int = 100
):
    """获取协作事件"""
    try:
        events = await editor_manager.get_collaboration_events(document_id, limit)
        
        return {
            "success": True,
            "events": [event.to_dict() for event in events]
        }
        
    except Exception as e:
        logger.error("获取协作事件失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics", response_model=dict)
async def get_statistics():
    """获取统计信息"""
    try:
        stats = await editor_manager.get_statistics()
        return {"success": True, "statistics": stats}
        
    except Exception as e:
        logger.error("获取统计信息失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket端点
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接端点"""
    await connection_manager.connect(websocket, session_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            if message.get("type") == "subscribe":
                document_id = message.get("document_id")
                if document_id:
                    await connection_manager.subscribe_to_document(session_id, document_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "document_id": document_id
                    }))
            
            elif message.get("type") == "heartbeat":
                # 更新会话活动时间
                await editor_manager.update_session_activity(session_id)
                await websocket.send_text(json.dumps({
                    "type": "heartbeat_ack"
                }))
            
            elif message.get("type") == "cursor_position":
                # 广播光标位置
                document_id = message.get("document_id")
                if document_id:
                    await connection_manager.broadcast_to_document(
                        document_id,
                        {
                            "type": "cursor_update",
                            "session_id": session_id,
                            "entry_id": message.get("entry_id"),
                            "position": message.get("position")
                        }
                    )
            
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        # 结束编辑会话
        await editor_manager.end_edit_session(session_id)
        
    except Exception as e:
        logger.error("WebSocket连接错误", session_id=session_id, error=str(e))
        connection_manager.disconnect(session_id)