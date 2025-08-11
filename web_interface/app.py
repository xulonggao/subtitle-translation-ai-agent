#!/usr/bin/env python3
"""
字幕翻译系统 Streamlit Web 应用
"""

import streamlit as st
import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 导入系统组件
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.master_agent import MasterAgent, MasterAgentRequest, WorkflowStage
from agents.progress_monitor import ProgressMonitorAgent
from core.models import SubtitleFile, TranslationProject
from utils.file_utils import FileManager
import structlog

# 配置日志
logger = structlog.get_logger()

# 页面配置
st.set_page_config(
    page_title="字幕翻译系统",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .status-success {
        color: #27ae60;
        font-weight: bold;
    }
    .status-error {
        color: #e74c3c;
        font-weight: bold;
    }
    .status-warning {
        color: #f39c12;
        font-weight: bold;
    }
    .progress-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .file-info {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

class WebInterface:
    """Web界面主类"""
    
    def __init__(self):
        self.master_agent = None
        self.file_manager = FileManager()
        self.temp_dir = tempfile.mkdtemp()
        
        # 初始化会话状态
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'translation_results' not in st.session_state:
            st.session_state.translation_results = {}
        if 'progress_data' not in st.session_state:
            st.session_state.progress_data = {}
    
    def initialize_master_agent(self):
        """初始化主控Agent"""
        if self.master_agent is None:
            try:
                self.master_agent = MasterAgent()
                return True
            except Exception as e:
                st.error(f"初始化主控Agent失败: {str(e)}")
                return False
        return True
    
    def render_header(self):
        """渲染页面头部"""
        st.markdown('<h1 class="main-header">🎬 字幕翻译系统</h1>', unsafe_allow_html=True)
        st.markdown("---")
    
    def render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.markdown("### 🎯 功能导航")
            
            page = st.selectbox(
                "选择功能页面",
                ["项目管理", "文件上传", "翻译任务", "进度监控", "结果预览", "系统状态"],
                key="page_selector"
            )
            
            st.markdown("---")
            
            # 系统状态指示器
            st.markdown("### 📊 系统状态")
            if self.initialize_master_agent():
                st.markdown('<span class="status-success">✅ 系统正常</span>', unsafe_allow_html=True)
                
                # 显示Agent健康状态
                if hasattr(self.master_agent, 'get_all_agent_health'):
                    health_status = self.master_agent.get_all_agent_health()
                    healthy_count = sum(1 for h in health_status.values() if h.get('status') == 'healthy')
                    total_count = len(health_status)
                    st.write(f"Agent状态: {healthy_count}/{total_count} 健康")
            else:
                st.markdown('<span class="status-error">❌ 系统异常</span>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # 快速统计
            st.markdown("### 📈 快速统计")
            st.write(f"活跃项目: {len(st.session_state.projects)}")
            st.write(f"完成翻译: {len(st.session_state.translation_results)}")
            
            return page
    
    def render_project_management(self):
        """渲染项目管理页面"""
        st.markdown('<h2 class="section-header">📁 项目管理</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("创建新项目")
            
            with st.form("create_project_form"):
                project_name = st.text_input("项目名称", placeholder="输入项目名称")
                project_description = st.text_area("项目描述", placeholder="输入项目描述（可选）")
                
                col_lang1, col_lang2 = st.columns(2)
                with col_lang1:
                    source_language = st.selectbox(
                        "源语言",
                        ["zh-CN", "en-US", "ja-JP", "ko-KR", "es-ES", "fr-FR", "de-DE"],
                        index=0
                    )
                
                with col_lang2:
                    target_languages = st.multiselect(
                        "目标语言",
                        ["zh-CN", "en-US", "ja-JP", "ko-KR", "es-ES", "fr-FR", "de-DE"],
                        default=["en-US"]
                    )
                
                submitted = st.form_submit_button("创建项目")
                
                if submitted and project_name:
                    project_id = f"project_{int(time.time())}"
                    project = TranslationProject(
                        project_id=project_id,
                        name=project_name,
                        description=project_description,
                        source_language=source_language,
                        target_languages=target_languages,
                        created_at=datetime.now()
                    )
                    
                    st.session_state.projects[project_id] = project
                    st.session_state.current_project = project_id
                    st.success(f"项目 '{project_name}' 创建成功！")
                    st.rerun()
        
        with col2:
            st.subheader("项目列表")
            
            if st.session_state.projects:
                for project_id, project in st.session_state.projects.items():
                    with st.container():
                        st.markdown(f'<div class="file-info">', unsafe_allow_html=True)
                        st.write(f"**{project.name}**")
                        st.write(f"ID: {project_id}")
                        st.write(f"源语言: {project.source_language}")
                        st.write(f"目标语言: {', '.join(project.target_languages)}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("选择", key=f"select_{project_id}"):
                                st.session_state.current_project = project_id
                                st.success(f"已选择项目: {project.name}")
                                st.rerun()
                        
                        with col_btn2:
                            if st.button("删除", key=f"delete_{project_id}"):
                                del st.session_state.projects[project_id]
                                if st.session_state.current_project == project_id:
                                    st.session_state.current_project = None
                                st.success("项目已删除")
                                st.rerun()
                        
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("暂无项目，请创建新项目")
        
        # 显示当前选中的项目
        if st.session_state.current_project:
            current_project = st.session_state.projects[st.session_state.current_project]
            st.markdown("---")
            st.subheader("当前项目")
            st.info(f"📁 {current_project.name} ({st.session_state.current_project})")
    
    def render_file_upload(self):
        """渲染文件上传页面"""
        st.markdown('<h2 class="section-header">📤 文件上传</h2>', unsafe_allow_html=True)
        
        if not st.session_state.current_project:
            st.warning("请先选择或创建一个项目")
            return
        
        current_project = st.session_state.projects[st.session_state.current_project]
        st.info(f"当前项目: {current_project.name}")
        
        # 文件上传区域
        uploaded_files = st.file_uploader(
            "选择字幕文件",
            type=['srt', 'vtt', 'ass', 'ssa', 'txt'],
            accept_multiple_files=True,
            help="支持的格式: SRT, VTT, ASS, SSA, TXT"
        )
        
        if uploaded_files:
            st.subheader("上传的文件")
            
            for uploaded_file in uploaded_files:
                with st.expander(f"📄 {uploaded_file.name}"):
                    # 显示文件信息
                    st.write(f"**文件名:** {uploaded_file.name}")
                    st.write(f"**文件大小:** {uploaded_file.size} bytes")
                    st.write(f"**文件类型:** {uploaded_file.type}")
                    
                    # 保存文件到临时目录
                    temp_file_path = os.path.join(self.temp_dir, uploaded_file.name)
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 预览文件内容
                    try:
                        with open(temp_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            preview = content[:500] + "..." if len(content) > 500 else content
                            st.text_area("文件预览", preview, height=150, disabled=True)
                    except Exception as e:
                        st.error(f"无法预览文件: {str(e)}")
                    
                    # 添加到项目
                    if st.button(f"添加到项目", key=f"add_{uploaded_file.name}"):
                        try:
                            subtitle_file = SubtitleFile(
                                file_path=temp_file_path,
                                original_filename=uploaded_file.name,
                                file_format=uploaded_file.name.split('.')[-1].lower(),
                                language=current_project.source_language,
                                encoding='utf-8'
                            )
                            
                            if 'files' not in current_project.__dict__:
                                current_project.files = []
                            current_project.files.append(subtitle_file)
                            
                            st.success(f"文件 {uploaded_file.name} 已添加到项目")
                            st.rerun()
                        except Exception as e:
                            st.error(f"添加文件失败: {str(e)}")
        
        # 显示项目中的文件
        if hasattr(current_project, 'files') and current_project.files:
            st.markdown("---")
            st.subheader("项目文件")
            
            for i, file in enumerate(current_project.files):
                with st.container():
                    st.markdown(f'<div class="file-info">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"📄 **{file.original_filename}**")
                        st.write(f"格式: {file.file_format.upper()}")
                        st.write(f"语言: {file.language}")
                    
                    with col2:
                        if st.button("预览", key=f"preview_{i}"):
                            try:
                                with open(file.file_path, 'r', encoding=file.encoding) as f:
                                    content = f.read()
                                    st.text_area("文件内容", content, height=200)
                            except Exception as e:
                                st.error(f"预览失败: {str(e)}")
                    
                    with col3:
                        if st.button("移除", key=f"remove_{i}"):
                            current_project.files.pop(i)
                            st.success("文件已移除")
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    def render_translation_task(self):
        """渲染翻译任务页面"""
        st.markdown('<h2 class="section-header">🔄 翻译任务</h2>', unsafe_allow_html=True)
        
        if not st.session_state.current_project:
            st.warning("请先选择或创建一个项目")
            return
        
        current_project = st.session_state.projects[st.session_state.current_project]
        
        if not hasattr(current_project, 'files') or not current_project.files:
            st.warning("请先上传字幕文件")
            return
        
        st.info(f"当前项目: {current_project.name}")
        
        # 翻译配置
        with st.form("translation_config_form"):
            st.subheader("翻译配置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_files = st.multiselect(
                    "选择要翻译的文件",
                    options=[f.original_filename for f in current_project.files],
                    default=[f.original_filename for f in current_project.files]
                )
                
                target_languages = st.multiselect(
                    "目标语言",
                    options=current_project.target_languages,
                    default=current_project.target_languages
                )
            
            with col2:
                quality_level = st.selectbox(
                    "翻译质量等级",
                    ["standard", "high", "premium"],
                    index=1,
                    help="standard: 快速翻译, high: 高质量翻译, premium: 专业级翻译"
                )
                
                enable_context_analysis = st.checkbox("启用上下文分析", value=True)
                enable_cultural_adaptation = st.checkbox("启用文化适应", value=True)
                enable_terminology_consistency = st.checkbox("启用术语一致性", value=True)
            
            # 高级选项
            with st.expander("高级选项"):
                max_concurrent_tasks = st.slider("最大并发任务数", 1, 10, 3)
                retry_attempts = st.slider("重试次数", 1, 5, 3)
                timeout_minutes = st.slider("任务超时时间(分钟)", 5, 60, 30)
            
            submitted = st.form_submit_button("开始翻译", type="primary")
            
            if submitted and selected_files and target_languages:
                if not self.initialize_master_agent():
                    st.error("无法初始化翻译系统")
                    return
                
                # 创建翻译请求
                try:
                    # 准备源文件
                    source_files = []
                    for file in current_project.files:
                        if file.original_filename in selected_files:
                            source_files.append(file)
                    
                    # 创建翻译请求
                    request = MasterAgentRequest(
                        request_id=f"task_{int(time.time())}",
                        project_id=current_project.project_id,
                        source_files=source_files,
                        target_languages=target_languages,
                        quality_requirements={
                            "level": quality_level,
                            "enable_context_analysis": enable_context_analysis,
                            "enable_cultural_adaptation": enable_cultural_adaptation,
                            "enable_terminology_consistency": enable_terminology_consistency
                        },
                        processing_options={
                            "max_concurrent_tasks": max_concurrent_tasks,
                            "retry_attempts": retry_attempts,
                            "timeout_minutes": timeout_minutes
                        }
                    )
                    
                    # 存储任务信息
                    task_key = f"{current_project.project_id}_{request.request_id}"
                    st.session_state.progress_data[task_key] = {
                        "request": request,
                        "status": "submitted",
                        "start_time": datetime.now()
                    }
                    
                    st.success("翻译任务已提交！请前往进度监控页面查看进度。")
                    
                    # 异步执行翻译任务
                    with st.spinner("正在启动翻译任务..."):
                        try:
                            # 这里应该异步执行，但为了演示，我们先同步执行
                            response = asyncio.run(self.master_agent.execute_workflow(request))
                            
                            # 存储结果
                            st.session_state.translation_results[task_key] = response
                            st.session_state.progress_data[task_key]["status"] = "completed" if response.success else "failed"
                            st.session_state.progress_data[task_key]["end_time"] = datetime.now()
                            
                            if response.success:
                                st.success("翻译任务完成！")
                            else:
                                st.error("翻译任务失败，请查看详细信息。")
                            
                        except Exception as e:
                            st.error(f"翻译任务执行失败: {str(e)}")
                            st.session_state.progress_data[task_key]["status"] = "error"
                            st.session_state.progress_data[task_key]["error"] = str(e)
                
                except Exception as e:
                    st.error(f"创建翻译任务失败: {str(e)}")
        
        # 显示历史任务
        if st.session_state.progress_data:
            st.markdown("---")
            st.subheader("翻译任务历史")
            
            for task_key, task_data in st.session_state.progress_data.items():
                if task_key.startswith(current_project.project_id):
                    with st.expander(f"任务 {task_data['request'].request_id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**状态:** {task_data['status']}")
                            st.write(f"**开始时间:** {task_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                            if 'end_time' in task_data:
                                st.write(f"**结束时间:** {task_data['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        with col2:
                            st.write(f"**源文件数:** {len(task_data['request'].source_files)}")
                            st.write(f"**目标语言:** {', '.join(task_data['request'].target_languages)}")
                            st.write(f"**质量等级:** {task_data['request'].quality_requirements.get('level', 'standard')}")
                        
                        if task_key in st.session_state.translation_results:
                            result = st.session_state.translation_results[task_key]
                            st.write(f"**完成任务:** {len(result.completed_tasks)}")
                            st.write(f"**失败任务:** {len(result.failed_tasks)}")
                            st.write(f"**处理时间:** {result.processing_time_ms}ms")
    
    def render_progress_monitoring(self):
        """渲染进度监控页面"""
        st.markdown('<h2 class="section-header">📊 进度监控</h2>', unsafe_allow_html=True)
        
        if not st.session_state.progress_data:
            st.info("暂无进行中的翻译任务")
            return
        
        # 总体统计
        total_tasks = len(st.session_state.progress_data)
        completed_tasks = len([t for t in st.session_state.progress_data.values() if t['status'] == 'completed'])
        failed_tasks = len([t for t in st.session_state.progress_data.values() if t['status'] == 'failed'])
        running_tasks = len([t for t in st.session_state.progress_data.values() if t['status'] in ['submitted', 'running']])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总任务数", total_tasks)
        with col2:
            st.metric("已完成", completed_tasks)
        with col3:
            st.metric("失败", failed_tasks)
        with col4:
            st.metric("进行中", running_tasks)
        
        # 任务状态饼图
        if total_tasks > 0:
            status_data = {
                'completed': completed_tasks,
                'failed': failed_tasks,
                'running': running_tasks
            }
            
            fig = px.pie(
                values=list(status_data.values()),
                names=list(status_data.keys()),
                title="任务状态分布",
                color_discrete_map={
                    'completed': '#27ae60',
                    'failed': '#e74c3c',
                    'running': '#f39c12'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 详细任务列表
        st.subheader("任务详情")
        
        for task_key, task_data in st.session_state.progress_data.items():
            with st.expander(f"📋 任务 {task_data['request'].request_id} - {task_data['status']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**基本信息**")
                    st.write(f"项目ID: {task_data['request'].project_id}")
                    st.write(f"请求ID: {task_data['request'].request_id}")
                    st.write(f"状态: {task_data['status']}")
                    st.write(f"开始时间: {task_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if 'end_time' in task_data:
                        duration = task_data['end_time'] - task_data['start_time']
                        st.write(f"持续时间: {duration.total_seconds():.1f}秒")
                
                with col2:
                    st.write("**任务配置**")
                    st.write(f"源文件数: {len(task_data['request'].source_files)}")
                    st.write(f"目标语言: {', '.join(task_data['request'].target_languages)}")
                    st.write(f"质量等级: {task_data['request'].quality_requirements.get('level', 'standard')}")
                
                # 如果有结果，显示详细信息
                if task_key in st.session_state.translation_results:
                    result = st.session_state.translation_results[task_key]
                    
                    st.write("**执行结果**")
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        st.write(f"工作流阶段: {result.workflow_stage}")
                        st.write(f"成功: {'是' if result.success else '否'}")
                        st.write(f"完成任务数: {len(result.completed_tasks)}")
                        st.write(f"失败任务数: {len(result.failed_tasks)}")
                    
                    with col4:
                        st.write(f"处理时间: {result.processing_time_ms}ms")
                        st.write(f"输出文件数: {len(result.output_files)}")
                    
                    # 显示任务详情
                    if result.completed_tasks:
                        st.write("**完成的任务:**")
                        for task in result.completed_tasks:
                            st.write(f"- {task.task_name} ({task.agent_name})")
                    
                    if result.failed_tasks:
                        st.write("**失败的任务:**")
                        for task in result.failed_tasks:
                            st.write(f"- {task.task_name} ({task.agent_name}): {task.error_message}")
                
                # 错误信息
                if 'error' in task_data:
                    st.error(f"错误信息: {task_data['error']}")
        
        # 自动刷新选项
        if st.checkbox("自动刷新 (10秒)", key="auto_refresh"):
            time.sleep(10)
            st.rerun()
    
    def render_result_preview(self):
        """渲染结果预览页面"""
        st.markdown('<h2 class="section-header">👁️ 结果预览</h2>', unsafe_allow_html=True)
        
        if not st.session_state.translation_results:
            st.info("暂无翻译结果")
            return
        
        # 选择要预览的结果
        result_keys = list(st.session_state.translation_results.keys())
        selected_result = st.selectbox(
            "选择翻译结果",
            options=result_keys,
            format_func=lambda x: f"任务 {st.session_state.progress_data[x]['request'].request_id}"
        )
        
        if selected_result:
            result = st.session_state.translation_results[selected_result]
            task_data = st.session_state.progress_data[selected_result]
            
            # 结果概览
            st.subheader("结果概览")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("成功", "是" if result.success else "否")
            with col2:
                st.metric("完成任务", len(result.completed_tasks))
            with col3:
                st.metric("失败任务", len(result.failed_tasks))
            with col4:
                st.metric("输出文件", len(result.output_files))
            
            # 输出文件预览
            if result.output_files:
                st.subheader("输出文件")
                
                for file_key, file_path in result.output_files.items():
                    with st.expander(f"📄 {file_key}"):
                        try:
                            if os.path.exists(file_path):
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                # 显示文件内容
                                st.text_area("文件内容", content, height=300)
                                
                                # 下载按钮
                                st.download_button(
                                    label="下载文件",
                                    data=content,
                                    file_name=os.path.basename(file_path),
                                    mime="text/plain"
                                )
                            else:
                                st.error("文件不存在")
                        except Exception as e:
                            st.error(f"读取文件失败: {str(e)}")
            
            # 任务执行详情
            st.subheader("任务执行详情")
            
            if result.completed_tasks:
                st.write("**✅ 完成的任务:**")
                for task in result.completed_tasks:
                    st.write(f"- **{task.task_name}** ({task.agent_name})")
                    if task.start_time and task.end_time:
                        duration = (task.end_time - task.start_time).total_seconds()
                        st.write(f"  执行时间: {duration:.2f}秒")
            
            if result.failed_tasks:
                st.write("**❌ 失败的任务:**")
                for task in result.failed_tasks:
                    st.write(f"- **{task.task_name}** ({task.agent_name})")
                    if task.error_message:
                        st.write(f"  错误: {task.error_message}")
    
    def render_system_status(self):
        """渲染系统状态页面"""
        st.markdown('<h2 class="section-header">⚙️ 系统状态</h2>', unsafe_allow_html=True)
        
        if not self.initialize_master_agent():
            st.error("无法连接到系统")
            return
        
        # Agent健康状态
        st.subheader("Agent 健康状态")
        
        if hasattr(self.master_agent, 'get_all_agent_health'):
            health_status = self.master_agent.get_all_agent_health()
            
            for agent_key, health_info in health_status.items():
                with st.expander(f"🤖 {agent_key} - {health_info.get('status', 'unknown')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**状态:** {health_info.get('status', 'unknown')}")
                        st.write(f"**描述:** {health_info.get('description', 'N/A')}")
                        if 'last_check' in health_info:
                            st.write(f"**最后检查:** {health_info['last_check']}")
                    
                    with col2:
                        if 'error_count' in health_info:
                            st.write(f"**错误次数:** {health_info['error_count']}")
                        if 'last_error' in health_info:
                            st.write(f"**最后错误:** {health_info['last_error']}")
                    
                    # 恢复按钮
                    if health_info.get('status') in ['failed', 'error']:
                        if st.button(f"尝试恢复 {agent_key}", key=f"recover_{agent_key}"):
                            try:
                                success = asyncio.run(self.master_agent.recover_failed_agent(agent_key))
                                if success:
                                    st.success(f"Agent {agent_key} 恢复成功")
                                else:
                                    st.error(f"Agent {agent_key} 恢复失败")
                                st.rerun()
                            except Exception as e:
                                st.error(f"恢复失败: {str(e)}")
        
        # 系统统计
        st.subheader("系统统计")
        
        if hasattr(self.master_agent, 'get_execution_statistics'):
            stats = self.master_agent.get_execution_statistics()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总工作流", stats.get('total_workflows', 0))
            with col2:
                st.metric("成功工作流", stats.get('successful_workflows', 0))
            with col3:
                st.metric("失败工作流", stats.get('failed_workflows', 0))
            with col4:
                avg_time = stats.get('average_processing_time_ms', 0)
                st.metric("平均处理时间", f"{avg_time:.0f}ms")
            
            # Agent性能统计
            if 'agent_performance' in stats:
                st.subheader("Agent 性能统计")
                
                perf_data = []
                for agent_name, perf_stats in stats['agent_performance'].items():
                    perf_data.append({
                        'Agent': agent_name,
                        '总任务': perf_stats.get('total_tasks', 0),
                        '成功任务': perf_stats.get('successful_tasks', 0),
                        '失败任务': perf_stats.get('failed_tasks', 0),
                        '平均时间(ms)': perf_stats.get('average_time_ms', 0)
                    })
                
                if perf_data:
                    df = pd.DataFrame(perf_data)
                    st.dataframe(df, use_container_width=True)
        
        # 系统资源使用情况（模拟）
        st.subheader("系统资源")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CPU使用率（模拟）
            cpu_usage = 45.2
            st.metric("CPU 使用率", f"{cpu_usage}%")
            st.progress(cpu_usage / 100)
        
        with col2:
            # 内存使用率（模拟）
            memory_usage = 62.8
            st.metric("内存使用率", f"{memory_usage}%")
            st.progress(memory_usage / 100)
        
        with col3:
            # 磁盘使用率（模拟）
            disk_usage = 34.1
            st.metric("磁盘使用率", f"{disk_usage}%")
            st.progress(disk_usage / 100)
    
    def run(self):
        """运行Web应用"""
        self.render_header()
        
        # 渲染侧边栏并获取选中的页面
        selected_page = self.render_sidebar()
        
        # 根据选中的页面渲染对应内容
        if selected_page == "项目管理":
            self.render_project_management()
        elif selected_page == "文件上传":
            self.render_file_upload()
        elif selected_page == "翻译任务":
            self.render_translation_task()
        elif selected_page == "进度监控":
            self.render_progress_monitoring()
        elif selected_page == "结果预览":
            self.render_result_preview()
        elif selected_page == "系统状态":
            self.render_system_status()

def main():
    """主函数"""
    app = WebInterface()
    app.run()

if __name__ == "__main__":
    main()