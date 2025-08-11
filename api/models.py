#!/usr/bin/env python3
"""
API数据模型定义
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

# 枚举类型
class TaskStatus(str, Enum):
    """任务状态"""
    SUBMITTED = "submitted"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FileStatus(str, Enum):
    """文件状态"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class QualityLevel(str, Enum):
    """翻译质量等级"""
    STANDARD = "standard"
    HIGH = "high"
    PREMIUM = "premium"

# 认证相关模型
class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user_info: Dict[str, Any] = Field(..., description="用户信息")

class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")

class RefreshTokenResponse(BaseModel):
    """刷新令牌响应"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")

# 项目管理模型
class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., description="项目名称", max_length=100)
    description: Optional[str] = Field(None, description="项目描述", max_length=500)
    source_language: str = Field(..., description="源语言代码")
    target_languages: List[str] = Field(..., description="目标语言代码列表", min_items=1)

class ProjectResponse(BaseModel):
    """项目响应"""
    project_id: str = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    source_language: str = Field(..., description="源语言代码")
    target_languages: List[str] = Field(..., description="目标语言代码列表")
    created_at: datetime = Field(..., description="创建时间")
    created_by: str = Field(..., description="创建者ID")
    status: str = Field(..., description="项目状态")
    file_count: int = Field(..., description="文件数量")

# 文件管理模型
class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型")
    upload_time: datetime = Field(..., description="上传时间")
    file_path: str = Field(..., description="文件路径")

class FileInfo(BaseModel):
    """文件信息"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型")
    upload_time: datetime = Field(..., description="上传时间")
    status: FileStatus = Field(..., description="文件状态")

# 翻译任务模型
class QualityRequirements(BaseModel):
    """质量要求"""
    level: QualityLevel = Field(default=QualityLevel.HIGH, description="质量等级")
    enable_context_analysis: bool = Field(default=True, description="启用上下文分析")
    enable_cultural_adaptation: bool = Field(default=True, description="启用文化适应")
    enable_terminology_consistency: bool = Field(default=True, description="启用术语一致性")

class ProcessingOptions(BaseModel):
    """处理选项"""
    max_concurrent_tasks: int = Field(default=3, description="最大并发任务数", ge=1, le=10)
    retry_attempts: int = Field(default=3, description="重试次数", ge=1, le=5)
    timeout_minutes: int = Field(default=30, description="超时时间（分钟）", ge=5, le=120)

class CreateTaskRequest(BaseModel):
    """创建翻译任务请求"""
    project_id: str = Field(..., description="项目ID")
    file_ids: List[str] = Field(..., description="文件ID列表", min_items=1)
    source_language: str = Field(..., description="源语言代码")
    target_languages: List[str] = Field(..., description="目标语言代码列表", min_items=1)
    quality_requirements: QualityRequirements = Field(default_factory=QualityRequirements, description="质量要求")
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions, description="处理选项")

class TaskResponse(BaseModel):
    """翻译任务响应"""
    task_id: str = Field(..., description="任务ID")
    project_id: str = Field(..., description="项目ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., description="进度百分比", ge=0.0, le=100.0)
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    file_count: int = Field(..., description="文件数量")
    target_language_count: int = Field(..., description="目标语言数量")
    error_message: Optional[str] = Field(None, description="错误信息")

class ProcessingStage(BaseModel):
    """处理阶段"""
    stage_name: str = Field(..., description="阶段名称")
    status: str = Field(..., description="阶段状态")
    progress: float = Field(..., description="阶段进度", ge=0.0, le=100.0)
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    error_message: Optional[str] = Field(None, description="错误信息")

class OutputFile(BaseModel):
    """输出文件"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    language: str = Field(..., description="语言代码")
    file_size: int = Field(..., description="文件大小（字节）")
    download_url: str = Field(..., description="下载链接")
    created_at: Optional[datetime] = Field(None, description="创建时间")

class TaskDetailResponse(BaseModel):
    """翻译任务详情响应"""
    task_id: str = Field(..., description="任务ID")
    project_id: str = Field(..., description="项目ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., description="进度百分比", ge=0.0, le=100.0)
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    file_count: int = Field(..., description="文件数量")
    target_language_count: int = Field(..., description="目标语言数量")
    processing_stages: List[ProcessingStage] = Field(default_factory=list, description="处理阶段列表")
    output_files: List[OutputFile] = Field(default_factory=list, description="输出文件列表")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="质量指标")
    error_message: Optional[str] = Field(None, description="错误信息")

# 进度监控模型
class ProgressResponse(BaseModel):
    """进度响应"""
    task_id: str = Field(..., description="任务ID")
    overall_progress: float = Field(..., description="总体进度", ge=0.0, le=100.0)
    current_stage: str = Field(..., description="当前阶段")
    stage_progress: float = Field(..., description="阶段进度", ge=0.0, le=100.0)
    estimated_completion_time: Optional[datetime] = Field(None, description="预计完成时间")
    processing_rate: Optional[float] = Field(None, description="处理速率（任务/分钟）")
    success_rate: Optional[float] = Field(None, description="成功率")

class SystemStatistics(BaseModel):
    """系统统计"""
    total_projects: int = Field(..., description="总项目数")
    active_tasks: int = Field(..., description="活跃任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    average_processing_time: float = Field(..., description="平均处理时间（毫秒）")
    system_uptime: datetime = Field(..., description="系统启动时间")
    agent_status: Dict[str, Any] = Field(default_factory=dict, description="Agent状态")

# 批量操作模型
class BatchTaskRequest(BaseModel):
    """批量任务请求"""
    project_id: str = Field(..., description="项目ID")
    tasks: List[CreateTaskRequest] = Field(..., description="任务列表", min_items=1, max_items=10)

class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str = Field(..., description="批次ID")
    total_tasks: int = Field(..., description="总任务数")
    submitted_tasks: List[str] = Field(..., description="已提交的任务ID列表")
    failed_tasks: List[Dict[str, str]] = Field(default_factory=list, description="失败的任务列表")

# 配置模型
class SystemConfig(BaseModel):
    """系统配置"""
    max_file_size: int = Field(default=50*1024*1024, description="最大文件大小（字节）")
    supported_formats: List[str] = Field(default=["srt", "vtt", "ass", "ssa", "txt"], description="支持的文件格式")
    supported_languages: List[str] = Field(default=[], description="支持的语言列表")
    default_quality_level: QualityLevel = Field(default=QualityLevel.HIGH, description="默认质量等级")
    max_concurrent_tasks: int = Field(default=5, description="最大并发任务数")

class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    config: SystemConfig = Field(..., description="系统配置")

# 用户管理模型
class UserInfo(BaseModel):
    """用户信息"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field(..., description="角色")
    created_at: datetime = Field(..., description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    is_active: bool = Field(default=True, description="是否激活")

class CreateUserRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6)
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field(default="user", description="角色")

class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: Optional[str] = Field(None, description="邮箱")
    role: Optional[str] = Field(None, description="角色")
    is_active: Optional[bool] = Field(None, description="是否激活")

# 审计日志模型
class AuditLog(BaseModel):
    """审计日志"""
    log_id: str = Field(..., description="日志ID")
    user_id: str = Field(..., description="用户ID")
    action: str = Field(..., description="操作")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    timestamp: datetime = Field(..., description="时间戳")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")

# 通知模型
class Notification(BaseModel):
    """通知"""
    notification_id: str = Field(..., description="通知ID")
    user_id: str = Field(..., description="用户ID")
    title: str = Field(..., description="标题")
    message: str = Field(..., description="消息内容")
    type: str = Field(..., description="通知类型")
    created_at: datetime = Field(..., description="创建时间")
    read_at: Optional[datetime] = Field(None, description="阅读时间")
    is_read: bool = Field(default=False, description="是否已读")

# 错误响应模型
class ErrorResponse(BaseModel):
    """错误响应"""
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(..., description="时间戳")

# 分页模型
class PaginationParams(BaseModel):
    """分页参数"""
    skip: int = Field(default=0, description="跳过的记录数", ge=0)
    limit: int = Field(default=100, description="返回的记录数", ge=1, le=1000)

class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any] = Field(..., description="数据项列表")
    total: int = Field(..., description="总记录数")
    skip: int = Field(..., description="跳过的记录数")
    limit: int = Field(..., description="返回的记录数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")

# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

class ProgressUpdate(BaseModel):
    """进度更新"""
    task_id: str = Field(..., description="任务ID")
    progress: float = Field(..., description="进度百分比")
    stage: str = Field(..., description="当前阶段")
    message: Optional[str] = Field(None, description="状态消息")

class TaskStatusUpdate(BaseModel):
    """任务状态更新"""
    task_id: str = Field(..., description="任务ID")
    old_status: TaskStatus = Field(..., description="旧状态")
    new_status: TaskStatus = Field(..., description="新状态")
    message: Optional[str] = Field(None, description="状态消息")