#!/usr/bin/env python3
"""
基于Streamlit的在线编辑器界面
"""

import streamlit as st
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

# 导入编辑器组件
from .editor_manager import EditorManager
from .models import (
    EditDocument, SubtitleEntry, EditStatus, ReviewStatus,
    ChangeType, ReviewComment
)

# 页面配置
st.set_page_config(
    page_title="字幕翻译在线编辑器",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .editor-header {
        font-size: 2rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle-entry {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f9f9f9;
    }
    .subtitle-entry.locked {
        border-color: #e74c3c;
        background-color: #fdf2f2;
    }
    .subtitle-entry.editing {
        border-color: #3498db;
        background-color: #f0f8ff;
    }
    .time-code {
        font-family: monospace;
        font-size: 0.9rem;
        color: #7f8c8d;
    }
    .original-text {
        background-color: #ecf0f1;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .translated-text {
        background-color: #e8f5e8;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .comment-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
    .comment-resolved {
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
    .user-indicator {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .user-online {
        background-color: #27ae60;
        color: white;
    }
    .user-editing {
        background-color: #3498db;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

class WebEditor:
    """Web编辑器界面"""
    
    def __init__(self):
        # 初始化编辑器管理器
        if 'editor_manager' not in st.session_state:
            st.session_state.editor_manager = EditorManager()
        
        self.editor_manager = st.session_state.editor_manager
        
        # 初始化会话状态
        if 'current_document_id' not in st.session_state:
            st.session_state.current_document_id = None
        if 'current_session_id' not in st.session_state:
            st.session_state.current_session_id = None
        if 'user_info' not in st.session_state:
            st.session_state.user_info = {
                "user_id": "demo_user",
                "user_name": "演示用户"
            }
        if 'editing_entry_id' not in st.session_state:
            st.session_state.editing_entry_id = None
    
    def render_header(self):
        """渲染页面头部"""
        st.markdown('<h1 class="editor-header">✏️ 字幕翻译在线编辑器</h1>', unsafe_allow_html=True)
        
        # 用户信息和状态
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"👤 当前用户: {st.session_state.user_info['user_name']}")
        
        with col2:
            if st.session_state.current_document_id:
                st.write(f"📄 文档: {st.session_state.current_document_id[:8]}...")
        
        with col3:
            if st.session_state.current_session_id:
                st.write("🟢 在线编辑中")
            else:
                st.write("⚪ 未连接")
        
        st.markdown("---")
    
    def render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.markdown("### 📋 编辑器功能")
            
            page = st.selectbox(
                "选择功能",
                ["文档管理", "在线编辑", "审核管理", "版本控制", "协作历史", "统计信息"],
                key="editor_page_selector"
            )
            
            st.markdown("---")
            
            # 文档快速信息
            if st.session_state.current_document_id:
                document = asyncio.run(
                    self.editor_manager.get_document(st.session_state.current_document_id)
                )
                if document:
                    st.markdown("### 📄 当前文档")
                    st.write(f"**标题:** {document.title}")
                    st.write(f"**状态:** {document.status.value}")
                    st.write(f"**版本:** {document.current_version}")
                    
                    entries = document.get_entries()
                    st.write(f"**条目数:** {len(entries)}")
                    
                    # 活跃用户
                    if document.active_sessions:
                        st.markdown("### 👥 在线用户")
                        for session in document.active_sessions:
                            if session.is_active:
                                st.markdown(
                                    f'<span class="user-indicator user-online">{session.user_name}</span>',
                                    unsafe_allow_html=True
                                )
            
            st.markdown("---")
            
            # 快速操作
            st.markdown("### ⚡ 快速操作")
            
            if st.button("🔄 刷新页面"):
                st.rerun()
            
            if st.session_state.current_session_id:
                if st.button("🚪 退出编辑"):
                    asyncio.run(
                        self.editor_manager.end_edit_session(st.session_state.current_session_id)
                    )
                    st.session_state.current_session_id = None
                    st.success("已退出编辑会话")
                    st.rerun()
            
            return page
    
    def render_document_management(self):
        """渲染文档管理页面"""
        st.markdown("## 📁 文档管理")
        
        # 创建新文档
        with st.expander("➕ 创建新文档", expanded=False):
            with st.form("create_document_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("文档标题", placeholder="输入文档标题")
                    project_id = st.text_input("项目ID", placeholder="输入项目ID")
                
                with col2:
                    source_lang = st.selectbox("源语言", ["zh-CN", "en-US", "ja-JP", "ko-KR"])
                    target_lang = st.selectbox("目标语言", ["en-US", "zh-CN", "ja-JP", "ko-KR"])
                
                # 示例字幕条目
                st.markdown("**示例字幕条目:**")
                sample_entries_text = st.text_area(
                    "字幕内容 (SRT格式)",
                    value="""1
00:00:01,000 --> 00:00:03,000
这是第一条字幕

2
00:00:04,000 --> 00:00:06,000
这是第二条字幕""",
                    height=150
                )
                
                if st.form_submit_button("创建文档", type="primary"):
                    if title and project_id:
                        try:
                            # 解析示例条目
                            entries = self.parse_srt_content(sample_entries_text)
                            
                            # 创建文档
                            document = asyncio.run(
                                self.editor_manager.create_document(
                                    title=title,
                                    project_id=project_id,
                                    source_language=source_lang,
                                    target_language=target_lang,
                                    entries=entries,
                                    created_by=st.session_state.user_info["user_id"]
                                )
                            )
                            
                            st.success(f"文档 '{title}' 创建成功！")
                            st.session_state.current_document_id = document.id
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"创建文档失败: {str(e)}")
                    else:
                        st.error("请填写文档标题和项目ID")
        
        # 文档列表
        st.markdown("### 📋 文档列表")
        
        documents = asyncio.run(self.editor_manager.list_documents())
        
        if documents:
            for doc in documents:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**📄 {doc.title}**")
                        st.write(f"项目: {doc.project_id}")
                        st.write(f"{doc.source_language} → {doc.target_language}")
                    
                    with col2:
                        status_color = {
                            "draft": "🟡",
                            "in_review": "🔵", 
                            "approved": "🟢",
                            "rejected": "🔴",
                            "published": "✅"
                        }
                        st.write(f"{status_color.get(doc.status.value, '⚪')} {doc.status.value}")
                        st.write(f"版本: {doc.current_version}")
                    
                    with col3:
                        entries_count = len(doc.get_entries())
                        comments_count = len(doc.comments)
                        st.write(f"条目: {entries_count}")
                        st.write(f"评论: {comments_count}")
                    
                    with col4:
                        if st.button("打开", key=f"open_{doc.id}"):
                            st.session_state.current_document_id = doc.id
                            st.success(f"已打开文档: {doc.title}")
                            st.rerun()
                        
                        if st.button("删除", key=f"delete_{doc.id}"):
                            # 这里应该添加删除确认
                            st.warning("删除功能待实现")
                    
                    st.markdown("---")
        else:
            st.info("暂无文档，请创建新文档")
    
    def render_online_editor(self):
        """渲染在线编辑页面"""
        st.markdown("## ✏️ 在线编辑")
        
        if not st.session_state.current_document_id:
            st.warning("请先选择一个文档进行编辑")
            return
        
        document = asyncio.run(
            self.editor_manager.get_document(st.session_state.current_document_id)
        )
        
        if not document:
            st.error("文档不存在")
            return
        
        # 文档信息
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**文档:** {document.title}")
            st.write(f"**状态:** {document.status.value}")
        
        with col2:
            st.write(f"**版本:** {document.current_version}")
            st.write(f"**语言:** {document.source_language} → {document.target_language}")
        
        with col3:
            # 开始/结束编辑会话
            if not st.session_state.current_session_id:
                if st.button("🚀 开始编辑", type="primary"):
                    try:
                        session = asyncio.run(
                            self.editor_manager.start_edit_session(
                                document.id,
                                st.session_state.user_info["user_id"],
                                st.session_state.user_info["user_name"]
                            )
                        )
                        st.session_state.current_session_id = session.id
                        st.success("编辑会话已开始")
                        st.rerun()
                    except Exception as e:
                        st.error(f"开始编辑失败: {str(e)}")
            else:
                st.write("🟢 编辑中...")
                if st.button("🛑 结束编辑"):
                    asyncio.run(
                        self.editor_manager.end_edit_session(st.session_state.current_session_id)
                    )
                    st.session_state.current_session_id = None
                    st.success("编辑会话已结束")
                    st.rerun()
        
        st.markdown("---")
        
        # 字幕条目编辑
        if st.session_state.current_session_id:
            self.render_subtitle_entries(document)
        else:
            st.info("请开始编辑会话以编辑字幕条目")
    
    def render_subtitle_entries(self, document: EditDocument):
        """渲染字幕条目编辑界面"""
        entries = document.get_entries()
        
        if not entries:
            st.info("文档中没有字幕条目")
            return
        
        st.markdown("### 📝 字幕条目")
        
        # 搜索和过滤
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_text = st.text_input("🔍 搜索字幕内容", key="search_entries")
        
        with col2:
            show_only_comments = st.checkbox("仅显示有评论的条目")
        
        with col3:
            entries_per_page = st.selectbox("每页显示", [10, 20, 50], index=1)
        
        # 过滤条目
        filtered_entries = entries
        
        if search_text:
            filtered_entries = [
                entry for entry in filtered_entries
                if search_text.lower() in entry.original_text.lower() or
                   search_text.lower() in entry.translated_text.lower()
            ]
        
        if show_only_comments:
            entry_ids_with_comments = {comment.entry_id for comment in document.comments}
            filtered_entries = [
                entry for entry in filtered_entries
                if entry.id in entry_ids_with_comments
            ]
        
        # 分页
        total_entries = len(filtered_entries)
        total_pages = (total_entries - 1) // entries_per_page + 1 if total_entries > 0 else 1
        
        if total_pages > 1:
            page = st.selectbox(f"页面 (共 {total_pages} 页)", range(1, total_pages + 1))
            start_idx = (page - 1) * entries_per_page
            end_idx = start_idx + entries_per_page
            page_entries = filtered_entries[start_idx:end_idx]
        else:
            page_entries = filtered_entries
        
        # 渲染条目
        for entry in page_entries:
            self.render_single_entry(entry, document)
    
    def render_single_entry(self, entry: SubtitleEntry, document: EditDocument):
        """渲染单个字幕条目"""
        # 确定条目状态
        is_locked = entry.is_locked
        is_editing = st.session_state.editing_entry_id == entry.id
        
        # 获取条目的评论
        entry_comments = [c for c in document.comments if c.entry_id == entry.id]
        
        # 条目容器
        container_class = "subtitle-entry"
        if is_locked:
            container_class += " locked"
        elif is_editing:
            container_class += " editing"
        
        with st.container():
            st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
            
            # 条目头部
            col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
            
            with col1:
                st.write(f"**#{entry.sequence}**")
            
            with col2:
                st.markdown(f'<span class="time-code">{entry.start_time} → {entry.end_time}</span>', 
                           unsafe_allow_html=True)
            
            with col3:
                if entry_comments:
                    unresolved_count = len([c for c in entry_comments if not c.is_resolved])
                    st.write(f"💬 {len(entry_comments)} ({unresolved_count} 未解决)")
            
            with col4:
                if is_locked and entry.id not in st.session_state.get('locked_entries', []):
                    st.write("🔒 已锁定")
                elif is_editing:
                    if st.button("💾 保存", key=f"save_{entry.id}"):
                        st.session_state.editing_entry_id = None
                        st.rerun()
                else:
                    if st.button("✏️ 编辑", key=f"edit_{entry.id}"):
                        # 尝试锁定条目
                        success = asyncio.run(
                            self.editor_manager.lock_entry(
                                st.session_state.current_session_id, entry.id
                            )
                        )
                        if success:
                            st.session_state.editing_entry_id = entry.id
                            st.rerun()
                        else:
                            st.error("无法锁定条目，可能被其他用户占用")
            
            # 原文
            st.markdown("**原文:**")
            st.markdown(f'<div class="original-text">{entry.original_text}</div>', 
                       unsafe_allow_html=True)
            
            # 译文
            st.markdown("**译文:**")
            if is_editing:
                new_translation = st.text_area(
                    "编辑译文",
                    value=entry.translated_text,
                    key=f"translation_{entry.id}",
                    height=100
                )
                
                col_edit1, col_edit2 = st.columns(2)
                
                with col_edit1:
                    if st.button("💾 保存修改", key=f"save_changes_{entry.id}"):
                        success = asyncio.run(
                            self.editor_manager.edit_entry(
                                st.session_state.current_session_id,
                                entry.id,
                                "translated_text",
                                new_translation,
                                "Web编辑器修改"
                            )
                        )
                        if success:
                            # 解锁条目
                            asyncio.run(
                                self.editor_manager.unlock_entry(
                                    st.session_state.current_session_id, entry.id
                                )
                            )
                            st.session_state.editing_entry_id = None
                            st.success("修改已保存")
                            st.rerun()
                        else:
                            st.error("保存失败")
                
                with col_edit2:
                    if st.button("❌ 取消", key=f"cancel_{entry.id}"):
                        # 解锁条目
                        asyncio.run(
                            self.editor_manager.unlock_entry(
                                st.session_state.current_session_id, entry.id
                            )
                        )
                        st.session_state.editing_entry_id = None
                        st.rerun()
            else:
                st.markdown(f'<div class="translated-text">{entry.translated_text}</div>', 
                           unsafe_allow_html=True)
            
            # 备注
            if entry.notes:
                st.markdown(f"**备注:** {entry.notes}")
            
            # 置信度分数
            if entry.confidence_score > 0:
                st.progress(entry.confidence_score)
                st.write(f"置信度: {entry.confidence_score:.1%}")
            
            # 评论区域
            if entry_comments:
                st.markdown("**评论:**")
                for comment in entry_comments:
                    comment_class = "comment-box"
                    if comment.is_resolved:
                        comment_class += " comment-resolved"
                    
                    st.markdown(f'<div class="{comment_class}">', unsafe_allow_html=True)
                    st.write(f"**{comment.reviewer_name}** ({comment.severity})")
                    st.write(comment.comment)
                    if comment.suggestion:
                        st.write(f"**建议:** {comment.suggestion}")
                    
                    if not comment.is_resolved:
                        if st.button("✅ 标记为已解决", key=f"resolve_{comment.id}"):
                            asyncio.run(
                                self.editor_manager.resolve_comment(
                                    document.id, comment.id,
                                    st.session_state.user_info["user_id"]
                                )
                            )
                            st.success("评论已标记为已解决")
                            st.rerun()
                    else:
                        st.write(f"✅ 已解决 (by {comment.resolved_by})")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 添加评论
            with st.expander("💬 添加评论"):
                comment_text = st.text_area("评论内容", key=f"comment_{entry.id}")
                suggestion_text = st.text_input("建议修改", key=f"suggestion_{entry.id}")
                severity = st.selectbox("严重程度", ["info", "warning", "error"], key=f"severity_{entry.id}")
                
                if st.button("发表评论", key=f"add_comment_{entry.id}"):
                    if comment_text:
                        asyncio.run(
                            self.editor_manager.add_comment(
                                document.id, entry.id,
                                st.session_state.user_info["user_id"],
                                st.session_state.user_info["user_name"],
                                comment_text, suggestion_text, severity
                            )
                        )
                        st.success("评论已添加")
                        st.rerun()
                    else:
                        st.error("请输入评论内容")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
    
    def render_review_management(self):
        """渲染审核管理页面"""
        st.markdown("## 🔍 审核管理")
        
        if not st.session_state.current_document_id:
            st.warning("请先选择一个文档")
            return
        
        document = asyncio.run(
            self.editor_manager.get_document(st.session_state.current_document_id)
        )
        
        if not document:
            st.error("文档不存在")
            return
        
        # 文档状态管理
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 文档状态")
            current_status = document.status.value
            new_status = st.selectbox(
                "更改状态",
                ["draft", "in_review", "approved", "rejected", "published"],
                index=["draft", "in_review", "approved", "rejected", "published"].index(current_status)
            )
            
            if new_status != current_status:
                if st.button("更新状态"):
                    asyncio.run(
                        self.editor_manager.update_document_status(
                            document.id, EditStatus(new_status)
                        )
                    )
                    st.success(f"状态已更新为: {new_status}")
                    st.rerun()
        
        with col2:
            st.markdown("### 👥 分配审核员")
            reviewer_name = st.text_input("审核员姓名")
            reviewer_id = st.text_input("审核员ID")
            due_date = st.date_input("截止日期")
            
            if st.button("分配审核员"):
                if reviewer_name and reviewer_id:
                    try:
                        due_datetime = datetime.combine(due_date, datetime.min.time())
                        asyncio.run(
                            self.editor_manager.assign_reviewer(
                                document.id, reviewer_id, reviewer_name, due_datetime
                            )
                        )
                        st.success(f"已分配审核员: {reviewer_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"分配失败: {str(e)}")
                else:
                    st.error("请填写审核员信息")
        
        # 评论统计
        st.markdown("### 💬 评论统计")
        
        if document.comments:
            total_comments = len(document.comments)
            resolved_comments = len([c for c in document.comments if c.is_resolved])
            unresolved_comments = total_comments - resolved_comments
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总评论数", total_comments)
            with col2:
                st.metric("已解决", resolved_comments)
            with col3:
                st.metric("未解决", unresolved_comments)
            
            # 按严重程度统计
            severity_counts = {}
            for comment in document.comments:
                severity = comment.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if severity_counts:
                st.markdown("**按严重程度分布:**")
                severity_df = pd.DataFrame(
                    list(severity_counts.items()),
                    columns=["严重程度", "数量"]
                )
                st.bar_chart(severity_df.set_index("严重程度"))
        else:
            st.info("暂无评论")
    
    def render_version_control(self):
        """渲染版本控制页面"""
        st.markdown("## 📚 版本控制")
        
        if not st.session_state.current_document_id:
            st.warning("请先选择一个文档")
            return
        
        document = asyncio.run(
            self.editor_manager.get_document(st.session_state.current_document_id)
        )
        
        if not document:
            st.error("文档不存在")
            return
        
        # 创建新版本
        with st.expander("➕ 创建新版本"):
            version_description = st.text_area("版本描述", placeholder="描述此版本的主要变更...")
            
            if st.button("创建版本", type="primary"):
                if version_description:
                    try:
                        new_version = asyncio.run(
                            self.editor_manager.create_version(
                                document.id,
                                st.session_state.user_info["user_id"],
                                version_description
                            )
                        )
                        st.success(f"新版本 {new_version.version_number} 创建成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"创建版本失败: {str(e)}")
                else:
                    st.error("请输入版本描述")
        
        # 版本列表
        st.markdown("### 📋 版本历史")
        
        if document.versions:
            for version in sorted(document.versions, key=lambda v: v.created_at, reverse=True):
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    
                    with col1:
                        current_indicator = "🟢 " if version.is_current else ""
                        st.write(f"**{current_indicator}版本 {version.version_number}**")
                        st.write(f"创建者: {version.created_by}")
                    
                    with col2:
                        st.write(f"创建时间: {version.created_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"条目数: {len(version.entries)}")
                    
                    with col3:
                        st.write(f"变更数: {len(version.changes)}")
                        if version.description:
                            st.write(f"描述: {version.description}")
                    
                    with col4:
                        if not version.is_current:
                            if st.button("恢复", key=f"restore_{version.id}"):
                                st.warning("版本恢复功能待实现")
                        
                        if st.button("详情", key=f"details_{version.id}"):
                            st.session_state.selected_version_id = version.id
                    
                    st.markdown("---")
        else:
            st.info("暂无版本历史")
    
    def render_collaboration_history(self):
        """渲染协作历史页面"""
        st.markdown("## 👥 协作历史")
        
        if not st.session_state.current_document_id:
            st.warning("请先选择一个文档")
            return
        
        # 获取协作事件
        events = asyncio.run(
            self.editor_manager.get_collaboration_events(st.session_state.current_document_id)
        )
        
        if events:
            st.markdown(f"### 📋 最近 {len(events)} 个事件")
            
            for event in events:
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        event_icons = {
                            "create": "📄",
                            "join": "🚪",
                            "leave": "🚶",
                            "edit": "✏️",
                            "comment": "💬",
                            "review": "🔍"
                        }
                        icon = event_icons.get(event.event_type, "📝")
                        st.write(f"{icon} **{event.event_type}**")
                    
                    with col2:
                        st.write(f"**{event.user_name}** {self.get_event_description(event)}")
                        if event.details:
                            details_text = ", ".join([f"{k}: {v}" for k, v in event.details.items() if k != "user_name"])
                            if details_text:
                                st.write(f"_{details_text}_")
                    
                    with col3:
                        st.write(event.timestamp.strftime("%H:%M:%S"))
                        st.write(event.timestamp.strftime("%Y-%m-%d"))
                    
                    st.markdown("---")
        else:
            st.info("暂无协作历史")
    
    def render_statistics(self):
        """渲染统计信息页面"""
        st.markdown("## 📊 统计信息")
        
        # 获取统计数据
        stats = asyncio.run(self.editor_manager.get_statistics())
        
        # 总体统计
        st.markdown("### 📈 总体统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总文档数", stats.get("total_documents", 0))
        with col2:
            st.metric("活跃会话", stats.get("active_sessions", 0))
        with col3:
            st.metric("总评论数", stats.get("total_comments", 0))
        with col4:
            st.metric("未解决评论", stats.get("unresolved_comments", 0))
        
        # 状态分布
        if stats.get("status_distribution"):
            st.markdown("### 📋 文档状态分布")
            status_df = pd.DataFrame(
                list(stats["status_distribution"].items()),
                columns=["状态", "数量"]
            )
            st.bar_chart(status_df.set_index("状态"))
        
        # 协作活动
        st.markdown("### 👥 协作活动")
        st.write(f"协作事件总数: {stats.get('collaboration_events', 0)}")
        
        # 当前文档统计
        if st.session_state.current_document_id:
            document = asyncio.run(
                self.editor_manager.get_document(st.session_state.current_document_id)
            )
            if document:
                st.markdown("### 📄 当前文档统计")
                
                entries = document.get_entries()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("字幕条目", len(entries))
                with col2:
                    st.metric("版本数", len(document.versions))
                with col3:
                    st.metric("活跃用户", len(document.active_sessions))
    
    def parse_srt_content(self, content: str) -> List[SubtitleEntry]:
        """解析SRT内容为字幕条目"""
        entries = []
        lines = content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():
                sequence = int(lines[i].strip())
                
                if i + 1 < len(lines) and '-->' in lines[i + 1]:
                    time_line = lines[i + 1].strip()
                    start_time, end_time = time_line.split(' --> ')
                    
                    # 收集字幕文本
                    text_lines = []
                    i += 2
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = '\n'.join(text_lines)
                    
                    entry = SubtitleEntry(
                        sequence=sequence,
                        start_time=start_time,
                        end_time=end_time,
                        original_text=text,
                        translated_text=text  # 初始时译文等于原文
                    )
                    entries.append(entry)
            
            i += 1
        
        return entries
    
    def get_event_description(self, event: CollaborationEvent) -> str:
        """获取事件描述"""
        descriptions = {
            "create": "创建了文档",
            "join": "加入了编辑",
            "leave": "离开了编辑",
            "edit": "编辑了条目",
            "comment": "添加了评论",
            "review": "进行了审核"
        }
        return descriptions.get(event.event_type, "执行了操作")
    
    def run(self):
        """运行Web编辑器"""
        self.render_header()
        
        # 渲染侧边栏并获取选中的页面
        selected_page = self.render_sidebar()
        
        # 根据选中的页面渲染对应内容
        if selected_page == "文档管理":
            self.render_document_management()
        elif selected_page == "在线编辑":
            self.render_online_editor()
        elif selected_page == "审核管理":
            self.render_review_management()
        elif selected_page == "版本控制":
            self.render_version_control()
        elif selected_page == "协作历史":
            self.render_collaboration_history()
        elif selected_page == "统计信息":
            self.render_statistics()

def main():
    """主函数"""
    editor = WebEditor()
    editor.run()

if __name__ == "__main__":
    main()