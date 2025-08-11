#!/usr/bin/env python3
"""
API异常处理模块
"""

from enum import Enum
from typing import Dict, Any, Optional

class ErrorCode(Enum):
    """错误代码枚举"""
    
    # 通用错误 (1000-1099)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    
    # 认证错误 (1100-1199)
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_DISABLED = "USER_DISABLED"
    
    # 速率限制错误 (1200-1299)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    IP_BLOCKED = "IP_BLOCKED"
    USER_BLOCKED = "USER_BLOCKED"
    
    # 项目管理错误 (1300-1399)
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_ALREADY_EXISTS = "PROJECT_ALREADY_EXISTS"
    PROJECT_ACCESS_DENIED = "PROJECT_ACCESS_DENIED"
    INVALID_PROJECT_CONFIG = "INVALID_PROJECT_CONFIG"
    
    # 文件管理错误 (1400-1499)
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    
    # 翻译任务错误 (1500-1599)
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_CREATION_FAILED = "TASK_CREATION_FAILED"
    TASK_EXECUTION_FAILED = "TASK_EXECUTION_FAILED"
    INVALID_TASK_CONFIG = "INVALID_TASK_CONFIG"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    
    # 系统错误 (1600-1699)
    SYSTEM_UNAVAILABLE = "SYSTEM_UNAVAILABLE"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

class APIException(Exception):
    """API异常基类"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class AuthenticationError(APIException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            message=message,
            status_code=401,
            details=details
        )

class InvalidTokenError(APIException):
    """无效令牌错误"""
    
    def __init__(self, message: str = "无效的访问令牌", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.INVALID_TOKEN,
            message=message,
            status_code=401,
            details=details
        )

class TokenExpiredError(APIException):
    """令牌过期错误"""
    
    def __init__(self, message: str = "访问令牌已过期", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.TOKEN_EXPIRED,
            message=message,
            status_code=401,
            details=details
        )

class InsufficientPermissionsError(APIException):
    """权限不足错误"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            message=message,
            status_code=403,
            details=details
        )

class RateLimitExceededError(APIException):
    """速率限制超出错误"""
    
    def __init__(self, message: str = "请求频率过高", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            status_code=429,
            details=details
        )

class ValidationError(APIException):
    """验证错误"""
    
    def __init__(self, message: str = "请求参数验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=400,
            details=details
        )

class NotFoundError(APIException):
    """资源不存在错误"""
    
    def __init__(self, message: str = "请求的资源不存在", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=404,
            details=details
        )

class ConflictError(APIException):
    """冲突错误"""
    
    def __init__(self, message: str = "资源冲突", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.CONFLICT,
            message=message,
            status_code=409,
            details=details
        )

class ProjectNotFoundError(APIException):
    """项目不存在错误"""
    
    def __init__(self, project_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"项目 {project_id} 不存在"
        if not details:
            details = {"project_id": project_id}
        super().__init__(
            error_code=ErrorCode.PROJECT_NOT_FOUND,
            message=message,
            status_code=404,
            details=details
        )

class ProjectAlreadyExistsError(APIException):
    """项目已存在错误"""
    
    def __init__(self, project_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"项目 {project_name} 已存在"
        if not details:
            details = {"project_name": project_name}
        super().__init__(
            error_code=ErrorCode.PROJECT_ALREADY_EXISTS,
            message=message,
            status_code=409,
            details=details
        )

class FileNotFoundError(APIException):
    """文件不存在错误"""
    
    def __init__(self, file_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"文件 {file_id} 不存在"
        if not details:
            details = {"file_id": file_id}
        super().__init__(
            error_code=ErrorCode.FILE_NOT_FOUND,
            message=message,
            status_code=404,
            details=details
        )

class FileTooLargeError(APIException):
    """文件过大错误"""
    
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        message = f"文件大小 {file_size} 字节超过限制 {max_size} 字节"
        if not details:
            details = {"file_size": file_size, "max_size": max_size}
        super().__init__(
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=message,
            status_code=413,
            details=details
        )

class InvalidFileFormatError(APIException):
    """无效文件格式错误"""
    
    def __init__(self, file_format: str, supported_formats: list, details: Optional[Dict[str, Any]] = None):
        message = f"不支持的文件格式 {file_format}，支持的格式: {', '.join(supported_formats)}"
        if not details:
            details = {"file_format": file_format, "supported_formats": supported_formats}
        super().__init__(
            error_code=ErrorCode.INVALID_FILE_FORMAT,
            message=message,
            status_code=400,
            details=details
        )

class TaskNotFoundError(APIException):
    """任务不存在错误"""
    
    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"翻译任务 {task_id} 不存在"
        if not details:
            details = {"task_id": task_id}
        super().__init__(
            error_code=ErrorCode.TASK_NOT_FOUND,
            message=message,
            status_code=404,
            details=details
        )

class TaskAlreadyRunningError(APIException):
    """任务已在运行错误"""
    
    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"翻译任务 {task_id} 已在运行中"
        if not details:
            details = {"task_id": task_id}
        super().__init__(
            error_code=ErrorCode.TASK_ALREADY_RUNNING,
            message=message,
            status_code=409,
            details=details
        )

class UnsupportedLanguageError(APIException):
    """不支持的语言错误"""
    
    def __init__(self, language: str, supported_languages: list, details: Optional[Dict[str, Any]] = None):
        message = f"不支持的语言 {language}，支持的语言: {', '.join(supported_languages)}"
        if not details:
            details = {"language": language, "supported_languages": supported_languages}
        super().__init__(
            error_code=ErrorCode.UNSUPPORTED_LANGUAGE,
            message=message,
            status_code=400,
            details=details
        )

class SystemUnavailableError(APIException):
    """系统不可用错误"""
    
    def __init__(self, message: str = "系统暂时不可用", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.SYSTEM_UNAVAILABLE,
            message=message,
            status_code=503,
            details=details
        )

class AgentUnavailableError(APIException):
    """Agent不可用错误"""
    
    def __init__(self, agent_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Agent {agent_name} 不可用"
        if not details:
            details = {"agent_name": agent_name}
        super().__init__(
            error_code=ErrorCode.AGENT_UNAVAILABLE,
            message=message,
            status_code=503,
            details=details
        )

class DatabaseError(APIException):
    """数据库错误"""
    
    def __init__(self, message: str = "数据库操作失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=500,
            details=details
        )

class ExternalServiceError(APIException):
    """外部服务错误"""
    
    def __init__(self, service_name: str, message: str = None, details: Optional[Dict[str, Any]] = None):
        if not message:
            message = f"外部服务 {service_name} 调用失败"
        if not details:
            details = {"service_name": service_name}
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            status_code=502,
            details=details
        )

class ConfigurationError(APIException):
    """配置错误"""
    
    def __init__(self, message: str = "系统配置错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.CONFIGURATION_ERROR,
            message=message,
            status_code=500,
            details=details
        )

# 异常映射字典，用于快速创建异常
EXCEPTION_MAP = {
    ErrorCode.AUTHENTICATION_FAILED: AuthenticationError,
    ErrorCode.INVALID_TOKEN: InvalidTokenError,
    ErrorCode.TOKEN_EXPIRED: TokenExpiredError,
    ErrorCode.INSUFFICIENT_PERMISSIONS: InsufficientPermissionsError,
    ErrorCode.RATE_LIMIT_EXCEEDED: RateLimitExceededError,
    ErrorCode.VALIDATION_ERROR: ValidationError,
    ErrorCode.NOT_FOUND: NotFoundError,
    ErrorCode.CONFLICT: ConflictError,
    ErrorCode.PROJECT_NOT_FOUND: ProjectNotFoundError,
    ErrorCode.FILE_NOT_FOUND: FileNotFoundError,
    ErrorCode.FILE_TOO_LARGE: FileTooLargeError,
    ErrorCode.INVALID_FILE_FORMAT: InvalidFileFormatError,
    ErrorCode.TASK_NOT_FOUND: TaskNotFoundError,
    ErrorCode.TASK_ALREADY_RUNNING: TaskAlreadyRunningError,
    ErrorCode.UNSUPPORTED_LANGUAGE: UnsupportedLanguageError,
    ErrorCode.SYSTEM_UNAVAILABLE: SystemUnavailableError,
    ErrorCode.AGENT_UNAVAILABLE: AgentUnavailableError,
    ErrorCode.DATABASE_ERROR: DatabaseError,
    ErrorCode.EXTERNAL_SERVICE_ERROR: ExternalServiceError,
    ErrorCode.CONFIGURATION_ERROR: ConfigurationError,
}

def create_exception(error_code: ErrorCode, message: str = None, **kwargs) -> APIException:
    """创建异常实例"""
    exception_class = EXCEPTION_MAP.get(error_code, APIException)
    
    if message:
        return exception_class(message, **kwargs)
    else:
        return exception_class(**kwargs)