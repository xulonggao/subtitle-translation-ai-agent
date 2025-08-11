#!/usr/bin/env python3
"""
字幕翻译系统 FastAPI 主应用
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel, Field
import structlog

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.master_agent import MasterAgent, MasterAgentRequest, WorkflowStage
from core.models import SubtitleFile, TranslationProject
from utils.file_utils import FileManager
from api.models import *
from api.auth import AuthManager
from api.rate_limiter import RateLimiter
from api.exceptions import APIException, ErrorCode

# 配置日志
logger = structlog.get_logger()

# 全局变量
master_agent: Optional[MasterAgent] = None
auth_manager: AuthManager = None
rate_limiter: RateLimiter = None
file_manager: FileManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    global master_agent, auth_manager, rate_limiter, file_manager
    
    logger.info("初始化字幕翻译系统API...")
    
    try:
        # 初始化组件
        master_agent = MasterAgent()
        auth_manager = AuthManager()
        rate_limiter = RateLimiter()
        file_manager = FileManager()
        
        logger.info("API系统初始化完成")
        
    except Exception as e:
        logger.error("API系统初始化失败", error=str(e))
        raise
    
    yield
    
    # 关闭时清理
    logger.info("关闭字幕翻译系统API...")

# 创建FastAPI应用
app = FastAPI(
    title="字幕翻译系统 API",
    description="基于AI的多语言字幕翻译系统RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# 安全配置
security = HTTPBearer()

# 依赖注入
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    if not auth_manager:
        raise HTTPException(status_code=500, detail="认证系统未初始化")
    
    user = await auth_manager.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    return user

async def check_rate_limit(user: dict = Depends(get_current_user)):
    """检查速率限制"""
    if not rate_limiter:
        return True
    
    user_id = user.get("user_id", "anonymous")
    if not await rate_limiter.check_limit(user_id):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    
    return True

# 根路径
@app.get("/", tags=["系统"])
async def root():
    """API根路径"""
    return {
        "message": "字幕翻译系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "timestamp": datetime.now().isoformat()
    }

# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    try:
        # 检查主控Agent状态
        agent_status = "healthy" if master_agent else "unavailable"
        
        # 检查各个组件
        components = {
            "master_agent": agent_status,
            "auth_manager": "healthy" if auth_manager else "unavailable",
            "rate_limiter": "healthy" if rate_limiter else "unavailable",
            "file_manager": "healthy" if file_manager else "unavailable"
        }
        
        # 获取系统统计
        stats = {}
        if master_agent:
            try:
                stats = master_agent.get_execution_statistics()
            except Exception as e:
                logger.warning("获取系统统计失败", error=str(e))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": components,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error("健康检查失败", error=str(e))
        raise HTTPException(status_code=500, detail="系统健康检查失败")

# 认证相关API
@app.post("/auth/login", response_model=LoginResponse, tags=["认证"])
async def login(request: LoginRequest):
    """用户登录"""
    try:
        if not auth_manager:
            raise HTTPException(status_code=500, detail="认证系统未初始化")
        
        result = await auth_manager.authenticate(request.username, request.password)
        if not result:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        return LoginResponse(
            access_token=result["access_token"],
            token_type="bearer",
            expires_in=result["expires_in"],
            user_info=result["user_info"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("登录失败", error=str(e))
        raise HTTPException(status_code=500, detail="登录过程中发生错误")

@app.post("/auth/refresh", response_model=RefreshTokenResponse, tags=["认证"])
async def refresh_token(request: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        if not auth_manager:
            raise HTTPException(status_code=500, detail="认证系统未初始化")
        
        result = await auth_manager.refresh_token(request.refresh_token)
        if not result:
            raise HTTPException(status_code=401, detail="无效的刷新令牌")
        
        return RefreshTokenResponse(
            access_token=result["access_token"],
            token_type="bearer",
            expires_in=result["expires_in"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("令牌刷新失败", error=str(e))
        raise HTTPException(status_code=500, detail="令牌刷新过程中发生错误")

# 项目管理API
@app.post("/projects", response_model=ProjectResponse, tags=["项目管理"])
async def create_project(
    request: CreateProjectRequest,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """创建新项目"""
    try:
        project = TranslationProject(
            project_id=f"project_{int(datetime.now().timestamp())}",
            name=request.name,
            description=request.description,
            source_language=request.source_language,
            target_languages=request.target_languages,
            created_at=datetime.now(),
            created_by=user["user_id"]
        )
        
        # 这里应该保存到数据库，现在先返回创建的项目信息
        return ProjectResponse(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            source_language=project.source_language,
            target_languages=project.target_languages,
            created_at=project.created_at,
            created_by=project.created_by,
            status="active",
            file_count=0
        )
        
    except Exception as e:
        logger.error("创建项目失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建项目失败")

@app.get("/projects", response_model=List[ProjectResponse], tags=["项目管理"])
async def list_projects(
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit),
    skip: int = 0,
    limit: int = 100
):
    """获取项目列表"""
    try:
        # 这里应该从数据库获取项目列表，现在返回示例数据
        projects = [
            ProjectResponse(
                project_id="project_001",
                name="示例项目1",
                description="这是一个示例项目",
                source_language="zh-CN",
                target_languages=["en-US", "ja-JP"],
                created_at=datetime.now(),
                created_by=user["user_id"],
                status="active",
                file_count=3
            )
        ]
        
        return projects[skip:skip + limit]
        
    except Exception as e:
        logger.error("获取项目列表失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取项目列表失败")

@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["项目管理"])
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """获取项目详情"""
    try:
        # 这里应该从数据库获取项目信息
        project = ProjectResponse(
            project_id=project_id,
            name="示例项目",
            description="这是一个示例项目",
            source_language="zh-CN",
            target_languages=["en-US", "ja-JP"],
            created_at=datetime.now(),
            created_by=user["user_id"],
            status="active",
            file_count=3
        )
        
        return project
        
    except Exception as e:
        logger.error("获取项目详情失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取项目详情失败")

@app.delete("/projects/{project_id}", tags=["项目管理"])
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """删除项目"""
    try:
        # 这里应该从数据库删除项目
        return {"message": f"项目 {project_id} 已删除"}
        
    except Exception as e:
        logger.error("删除项目失败", error=str(e))
        raise HTTPException(status_code=500, detail="删除项目失败")

# 文件管理API
@app.post("/projects/{project_id}/files", response_model=FileUploadResponse, tags=["文件管理"])
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """上传字幕文件"""
    try:
        # 验证文件类型
        allowed_types = ['srt', 'vtt', 'ass', 'ssa', 'txt']
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_extension}"
            )
        
        # 验证文件大小 (50MB限制)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件过大，最大支持50MB")
        
        # 保存文件
        file_id = f"file_{int(datetime.now().timestamp())}"
        saved_path = await file_manager.save_file(file_id, content, file.filename)
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=len(content),
            file_type=file_extension,
            upload_time=datetime.now(),
            file_path=saved_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("文件上传失败", error=str(e))
        raise HTTPException(status_code=500, detail="文件上传失败")

@app.get("/projects/{project_id}/files", response_model=List[FileInfo], tags=["文件管理"])
async def list_files(
    project_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """获取项目文件列表"""
    try:
        # 这里应该从数据库获取文件列表
        files = [
            FileInfo(
                file_id="file_001",
                filename="example.srt",
                file_size=1024,
                file_type="srt",
                upload_time=datetime.now(),
                status="ready"
            )
        ]
        
        return files
        
    except Exception as e:
        logger.error("获取文件列表失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取文件列表失败")

@app.delete("/projects/{project_id}/files/{file_id}", tags=["文件管理"])
async def delete_file(
    project_id: str,
    file_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """删除文件"""
    try:
        # 这里应该删除文件和数据库记录
        return {"message": f"文件 {file_id} 已删除"}
        
    except Exception as e:
        logger.error("删除文件失败", error=str(e))
        raise HTTPException(status_code=500, detail="删除文件失败")

# 翻译任务API
@app.post("/translation/tasks", response_model=TaskResponse, tags=["翻译任务"])
async def create_translation_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """创建翻译任务"""
    try:
        if not master_agent:
            raise HTTPException(status_code=500, detail="翻译系统未初始化")
        
        # 创建翻译请求
        task_id = f"task_{int(datetime.now().timestamp())}"
        
        # 这里应该从数据库获取文件信息，现在使用示例数据
        source_files = [
            SubtitleFile(
                file_path=f"/tmp/{file_id}",
                original_filename=f"file_{file_id}.srt",
                file_format="srt",
                language=request.source_language,
                encoding="utf-8"
            ) for file_id in request.file_ids
        ]
        
        master_request = MasterAgentRequest(
            request_id=task_id,
            project_id=request.project_id,
            source_files=source_files,
            target_languages=request.target_languages,
            quality_requirements=request.quality_requirements,
            processing_options=request.processing_options
        )
        
        # 在后台执行翻译任务
        background_tasks.add_task(execute_translation_task, master_request)
        
        return TaskResponse(
            task_id=task_id,
            project_id=request.project_id,
            status="submitted",
            progress=0.0,
            created_at=datetime.now(),
            file_count=len(request.file_ids),
            target_language_count=len(request.target_languages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("创建翻译任务失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建翻译任务失败")

async def execute_translation_task(request: MasterAgentRequest):
    """执行翻译任务（后台任务）"""
    try:
        logger.info("开始执行翻译任务", task_id=request.request_id)
        
        # 执行翻译
        response = await master_agent.execute_workflow(request)
        
        # 保存结果到数据库
        # 这里应该更新任务状态和结果
        
        logger.info("翻译任务完成", 
                   task_id=request.request_id,
                   success=response.success)
        
    except Exception as e:
        logger.error("翻译任务执行失败", 
                    task_id=request.request_id,
                    error=str(e))

@app.get("/translation/tasks", response_model=List[TaskResponse], tags=["翻译任务"])
async def list_tasks(
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit),
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """获取翻译任务列表"""
    try:
        # 这里应该从数据库获取任务列表
        tasks = [
            TaskResponse(
                task_id="task_001",
                project_id="project_001",
                status="completed",
                progress=100.0,
                created_at=datetime.now(),
                completed_at=datetime.now(),
                file_count=2,
                target_language_count=3
            )
        ]
        
        # 应用过滤条件
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks[skip:skip + limit]
        
    except Exception as e:
        logger.error("获取任务列表失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取任务列表失败")

@app.get("/translation/tasks/{task_id}", response_model=TaskDetailResponse, tags=["翻译任务"])
async def get_task_detail(
    task_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """获取翻译任务详情"""
    try:
        # 这里应该从数据库获取任务详情
        task_detail = TaskDetailResponse(
            task_id=task_id,
            project_id="project_001",
            status="completed",
            progress=100.0,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            file_count=2,
            target_language_count=3,
            processing_stages=[
                ProcessingStage(
                    stage_name="文件解析",
                    status="completed",
                    progress=100.0,
                    start_time=datetime.now(),
                    end_time=datetime.now()
                )
            ],
            output_files=[
                OutputFile(
                    file_id="output_001",
                    filename="translated_en.srt",
                    language="en-US",
                    file_size=2048,
                    download_url="/download/output_001"
                )
            ],
            quality_metrics={
                "translation_accuracy": 95.2,
                "terminology_consistency": 98.1,
                "cultural_adaptation": 92.7
            }
        )
        
        return task_detail
        
    except Exception as e:
        logger.error("获取任务详情失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取任务详情失败")

@app.delete("/translation/tasks/{task_id}", tags=["翻译任务"])
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """取消翻译任务"""
    try:
        # 这里应该取消正在执行的任务
        return {"message": f"任务 {task_id} 已取消"}
        
    except Exception as e:
        logger.error("取消任务失败", error=str(e))
        raise HTTPException(status_code=500, detail="取消任务失败")

# 进度监控API
@app.get("/monitoring/progress/{task_id}", response_model=ProgressResponse, tags=["进度监控"])
async def get_task_progress(
    task_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """获取任务进度"""
    try:
        # 从进度监控Agent获取实时进度
        progress_monitor = master_agent.sub_agents.get("progress_monitor") if master_agent else None
        
        if progress_monitor:
            progress_data = progress_monitor.get_workflow_progress(task_id)
            if progress_data:
                return ProgressResponse(
                    task_id=task_id,
                    overall_progress=progress_data.overall_progress,
                    current_stage=progress_data.current_stage,
                    stage_progress=progress_data.stage_progress,
                    estimated_completion_time=progress_data.estimated_completion_time,
                    processing_rate=progress_data.processing_rate,
                    success_rate=progress_data.success_rate
                )
        
        # 返回默认进度信息
        return ProgressResponse(
            task_id=task_id,
            overall_progress=0.0,
            current_stage="unknown",
            stage_progress=0.0
        )
        
    except Exception as e:
        logger.error("获取任务进度失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取任务进度失败")

@app.get("/monitoring/statistics", response_model=SystemStatistics, tags=["进度监控"])
async def get_system_statistics(
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """获取系统统计信息"""
    try:
        stats = {}
        if master_agent:
            stats = master_agent.get_execution_statistics()
        
        return SystemStatistics(
            total_projects=stats.get("total_workflows", 0),
            active_tasks=len(master_agent.active_workflows) if master_agent else 0,
            completed_tasks=stats.get("successful_workflows", 0),
            failed_tasks=stats.get("failed_workflows", 0),
            average_processing_time=stats.get("average_processing_time_ms", 0),
            system_uptime=datetime.now(),
            agent_status=master_agent.get_all_agent_health() if master_agent else {}
        )
        
    except Exception as e:
        logger.error("获取系统统计失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取系统统计失败")

# 文件下载API
@app.get("/download/{file_id}", tags=["文件下载"])
async def download_file(
    file_id: str,
    user: dict = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """下载文件"""
    try:
        # 这里应该从数据库获取文件路径
        file_path = f"/tmp/{file_id}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=file_path,
            filename=f"{file_id}.srt",
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("文件下载失败", error=str(e))
        raise HTTPException(status_code=500, detail="文件下载失败")

# 异常处理
@app.exception_handler(APIException)
async def api_exception_handler(request, exc: APIException):
    """API异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """通用异常处理"""
    logger.error("未处理的异常", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )