#!/usr/bin/env python3
"""
Web界面辅助工具模块
"""

import os
import tempfile
import hashlib
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import pandas as pd

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: float) -> str:
    """格式化持续时间"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"

def format_timestamp(timestamp: datetime) -> str:
    """格式化时间戳"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return timestamp.strftime("%Y-%m-%d %H:%M")
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

def validate_file_content(file_content: bytes, filename: str) -> Tuple[bool, str]:
    """验证文件内容"""
    try:
        # 检查文件大小
        if len(file_content) == 0:
            return False, "文件为空"
        
        if len(file_content) > 50 * 1024 * 1024:  # 50MB
            return False, "文件过大（超过50MB）"
        
        # 检查文件扩展名
        extension = filename.split('.')[-1].lower()
        allowed_extensions = ['srt', 'vtt', 'ass', 'ssa', 'txt']
        
        if extension not in allowed_extensions:
            return False, f"不支持的文件格式: {extension}"
        
        # 尝试解码文件内容
        try:
            content_str = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content_str = file_content.decode('gbk')
            except UnicodeDecodeError:
                return False, "文件编码不支持（请使用UTF-8或GBK编码）"
        
        # 基本内容验证
        if len(content_str.strip()) == 0:
            return False, "文件内容为空"
        
        # 字幕文件格式验证
        if extension == 'srt':
            if not _validate_srt_format(content_str):
                return False, "SRT文件格式不正确"
        elif extension == 'vtt':
            if not _validate_vtt_format(content_str):
                return False, "VTT文件格式不正确"
        
        return True, "文件验证通过"
        
    except Exception as e:
        return False, f"文件验证失败: {str(e)}"

def _validate_srt_format(content: str) -> bool:
    """验证SRT文件格式"""
    lines = content.strip().split('\n')
    if len(lines) < 3:
        return False
    
    # 检查第一个字幕块
    try:
        # 第一行应该是数字
        int(lines[0].strip())
        
        # 第二行应该是时间码
        time_line = lines[1].strip()
        if '-->' not in time_line:
            return False
        
        return True
    except (ValueError, IndexError):
        return False

def _validate_vtt_format(content: str) -> bool:
    """验证VTT文件格式"""
    lines = content.strip().split('\n')
    if len(lines) < 1:
        return False
    
    # VTT文件应该以WEBVTT开头
    return lines[0].strip().startswith('WEBVTT')

def generate_file_hash(file_content: bytes) -> str:
    """生成文件哈希值"""
    return hashlib.md5(file_content).hexdigest()

def save_uploaded_file(uploaded_file, upload_dir: Path) -> Tuple[bool, str, str]:
    """保存上传的文件"""
    try:
        # 创建上传目录
        upload_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = generate_file_hash(uploaded_file.getbuffer())[:8]
        filename = f"{timestamp}_{file_hash}_{uploaded_file.name}"
        file_path = upload_dir / filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True, str(file_path), "文件保存成功"
        
    except Exception as e:
        return False, "", f"文件保存失败: {str(e)}"

def create_progress_bar(current: int, total: int, label: str = "") -> None:
    """创建进度条"""
    if total > 0:
        progress = current / total
        st.progress(progress)
        if label:
            st.write(f"{label}: {current}/{total} ({progress:.1%})")

def create_status_badge(status: str) -> str:
    """创建状态徽章HTML"""
    status_colors = {
        'completed': '#27ae60',
        'success': '#27ae60',
        'failed': '#e74c3c',
        'error': '#e74c3c',
        'running': '#f39c12',
        'in_progress': '#f39c12',
        'pending': '#95a5a6',
        'waiting': '#95a5a6'
    }
    
    color = status_colors.get(status.lower(), '#95a5a6')
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{status}</span>'

def create_metric_card(title: str, value: str, delta: str = None, delta_color: str = "normal") -> None:
    """创建指标卡片"""
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color
    )

def export_results_to_csv(results_data: List[Dict[str, Any]]) -> str:
    """导出结果为CSV"""
    try:
        df = pd.DataFrame(results_data)
        return df.to_csv(index=False)
    except Exception as e:
        st.error(f"导出CSV失败: {str(e)}")
        return ""

def export_results_to_json(results_data: List[Dict[str, Any]]) -> str:
    """导出结果为JSON"""
    try:
        import json
        return json.dumps(results_data, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"导出JSON失败: {str(e)}")
        return ""

def create_download_link(data: str, filename: str, mime_type: str = "text/plain") -> None:
    """创建下载链接"""
    st.download_button(
        label=f"下载 {filename}",
        data=data,
        file_name=filename,
        mime=mime_type
    )

def display_error_message(error: str, details: str = None) -> None:
    """显示错误消息"""
    st.error(f"❌ {error}")
    if details:
        with st.expander("错误详情"):
            st.code(details)

def display_success_message(message: str, details: str = None) -> None:
    """显示成功消息"""
    st.success(f"✅ {message}")
    if details:
        with st.expander("详细信息"):
            st.info(details)

def display_warning_message(message: str, details: str = None) -> None:
    """显示警告消息"""
    st.warning(f"⚠️ {message}")
    if details:
        with st.expander("详细信息"):
            st.info(details)

def create_collapsible_section(title: str, content_func, expanded: bool = False):
    """创建可折叠的部分"""
    with st.expander(title, expanded=expanded):
        content_func()

def format_language_list(languages: List[str], language_names: Dict[str, str]) -> str:
    """格式化语言列表"""
    return ", ".join([language_names.get(lang, lang) for lang in languages])

def calculate_translation_cost(file_count: int, target_languages: int, quality_level: str) -> Dict[str, Any]:
    """计算翻译成本（模拟）"""
    base_cost_per_file = 10  # 基础成本
    language_multiplier = target_languages
    
    quality_multipliers = {
        'standard': 1.0,
        'high': 1.5,
        'premium': 2.0
    }
    
    quality_multiplier = quality_multipliers.get(quality_level, 1.0)
    
    total_cost = base_cost_per_file * file_count * language_multiplier * quality_multiplier
    estimated_time = file_count * target_languages * 5  # 5分钟每个文件每种语言
    
    return {
        'total_cost': total_cost,
        'cost_per_file': base_cost_per_file * quality_multiplier,
        'estimated_time_minutes': estimated_time,
        'quality_multiplier': quality_multiplier
    }

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform
    import psutil
    
    try:
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent
        }
    except ImportError:
        return {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'note': 'psutil not available for detailed system info'
        }

class SessionStateManager:
    """会话状态管理器"""
    
    @staticmethod
    def initialize_state(key: str, default_value: Any) -> Any:
        """初始化会话状态"""
        if key not in st.session_state:
            st.session_state[key] = default_value
        return st.session_state[key]
    
    @staticmethod
    def update_state(key: str, value: Any) -> None:
        """更新会话状态"""
        st.session_state[key] = value
    
    @staticmethod
    def get_state(key: str, default: Any = None) -> Any:
        """获取会话状态"""
        return st.session_state.get(key, default)
    
    @staticmethod
    def clear_state(key: str) -> None:
        """清除会话状态"""
        if key in st.session_state:
            del st.session_state[key]
    
    @staticmethod
    def clear_all_state() -> None:
        """清除所有会话状态"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]