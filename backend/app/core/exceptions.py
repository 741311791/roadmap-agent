"""
统一错误响应模型和错误码枚举

提供全局异常处理所需的数据结构和工具函数。
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import traceback
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class ErrorCode(str, Enum):
    """
    错误码枚举
    
    用于标识不同类型的错误，方便前端根据错误码做差异化处理。
    """
    # 客户端错误 (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    
    # 服务器错误 (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


class DebugInfo(BaseModel):
    """
    调试信息（仅开发环境）
    
    包含异常类型、完整堆栈跟踪等敏感信息。
    """
    exception_type: str = Field(..., description="异常类型")
    traceback: str = Field(..., description="完整堆栈跟踪")
    locals: Optional[dict[str, Any]] = Field(None, description="局部变量（可选）")


class ErrorDetail(BaseModel):
    """
    错误详情
    
    统一的错误响应格式。
    """
    code: ErrorCode = Field(..., description="错误码")
    message: str = Field(..., description="用户友好的错误描述")
    details: Optional[dict[str, Any]] = Field(None, description="业务相关详情（可选）")
    request_id: Optional[str] = Field(None, description="请求唯一标识")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="错误发生时间（UTC）")
    debug_info: Optional[DebugInfo] = Field(None, description="调试信息（仅开发环境）")


class ErrorResponse(BaseModel):
    """
    错误响应包装器
    
    所有API错误都返回此格式。
    """
    error: ErrorDetail = Field(..., description="错误详情")


def format_error_response(
    code: ErrorCode,
    message: str,
    exception: Optional[Exception] = None,
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
    include_debug: Optional[bool] = None,
) -> ErrorResponse:
    """
    格式化错误响应
    
    根据环境变量决定是否包含调试信息。
    
    Args:
        code: 错误码
        message: 用户友好的错误描述
        exception: 异常对象（可选）
        details: 业务相关详情（可选）
        request_id: 请求唯一标识（可选）
        include_debug: 是否包含调试信息（默认根据环境变量决定）
        
    Returns:
        ErrorResponse: 格式化的错误响应
        
    Example:
        >>> format_error_response(
        ...     code=ErrorCode.NOT_FOUND,
        ...     message="Roadmap not found",
        ...     details={"roadmap_id": "abc123"},
        ...     request_id="req-123",
        ... )
    """
    # 决定是否包含调试信息
    if include_debug is None:
        include_debug = settings.DEBUG or settings.ENVIRONMENT == "development"
    
    # 构建错误详情
    error_detail = ErrorDetail(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
    )
    
    # 如果需要调试信息且有异常对象
    if include_debug and exception:
        try:
            error_detail.debug_info = DebugInfo(
                exception_type=type(exception).__name__,
                traceback=traceback.format_exc(),
            )
        except Exception as e:
            logger.warning(
                "failed_to_format_debug_info",
                error=str(e),
            )
    
    return ErrorResponse(error=error_detail)


def sanitize_error_message(message: str, exception: Optional[Exception] = None) -> str:
    """
    清理错误消息，移除敏感信息
    
    移除可能包含的数据库连接字符串、API密钥等敏感信息。
    
    Args:
        message: 原始错误消息
        exception: 异常对象（可选）
        
    Returns:
        str: 清理后的错误消息
    """
    # 敏感信息关键词列表
    sensitive_patterns = [
        "password",
        "api_key",
        "secret",
        "token",
        "postgresql://",
        "redis://",
        "DATABASE_URL",
    ]
    
    # 如果是生产环境，检查并替换敏感信息
    if settings.ENVIRONMENT == "production":
        lower_message = message.lower()
        for pattern in sensitive_patterns:
            if pattern.lower() in lower_message:
                logger.warning(
                    "sensitive_info_detected_in_error_message",
                    pattern=pattern,
                    exception_type=type(exception).__name__ if exception else None,
                )
                # 返回通用错误消息
                return "An internal error occurred. Please contact support."
    
    return message


def get_user_friendly_message(exception: Exception) -> str:
    """
    获取用户友好的错误消息
    
    将技术性的异常消息转换为用户易于理解的描述。
    
    Args:
        exception: 异常对象
        
    Returns:
        str: 用户友好的错误消息
    """
    exception_type = type(exception).__name__
    
    # 常见异常的用户友好消息映射
    friendly_messages = {
        "ConnectionError": "Failed to connect to the service. Please try again later.",
        "TimeoutError": "The request timed out. Please try again.",
        "OperationalError": "A database error occurred. Please try again later.",
        "IntegrityError": "Data integrity constraint violated. Please check your input.",
        "ValidationError": "Invalid input data. Please check your request.",
        "PermissionDenied": "You don't have permission to perform this action.",
        "NotFound": "The requested resource was not found.",
    }
    
    # 返回映射的消息，或返回原始消息
    return friendly_messages.get(exception_type, str(exception))

