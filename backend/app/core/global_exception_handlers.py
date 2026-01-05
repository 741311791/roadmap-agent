"""
FastAPI 全局异常处理器

捕获所有未处理的异常，返回统一格式的 JSON 响应。
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
import structlog

from app.core.exceptions import (
    ErrorCode,
    ErrorResponse,
    format_error_response,
    sanitize_error_message,
    get_user_friendly_message,
)

logger = structlog.get_logger()


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    处理 FastAPI HTTPException
    
    Args:
        request: FastAPI 请求对象
        exc: HTTP 异常对象
        
    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 从 request.state 中提取 request_id（如果有）
    request_id = getattr(request.state, "request_id", None)
    
    # 根据 HTTP 状态码映射错误码
    status_to_code = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
    }
    
    error_code = status_to_code.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    
    # 清理错误消息（移除敏感信息）
    message = sanitize_error_message(str(exc.detail), exc)
    
    # 记录日志
    logger.info(
        "http_exception",
        status_code=exc.status_code,
        error_code=error_code.value,
        message=message,
        request_id=request_id,
        url=str(request.url),
        method=request.method,
    )
    
    # 格式化错误响应
    error_response = format_error_response(
        code=error_code,
        message=message,
        exception=exc,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理 Pydantic 验证错误
    
    解析验证错误，返回友好的错误消息。
    
    Args:
        request: FastAPI 请求对象
        exc: 请求验证错误对象
        
    Returns:
        JSONResponse: 统一格式的错误响应
    """
    request_id = getattr(request.state, "request_id", None)
    
    # 解析验证错误
    errors = exc.errors()
    
    # 提取第一个错误消息（简化版）
    first_error = errors[0] if errors else {}
    field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
    error_msg = first_error.get("msg", "Validation error")
    
    message = f"Validation error in field '{field}': {error_msg}"
    
    # 记录日志
    logger.warning(
        "validation_error",
        request_id=request_id,
        url=str(request.url),
        method=request.method,
        errors_count=len(errors),
        first_error=first_error,
    )
    
    # 格式化错误响应
    error_response = format_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        exception=exc,
        details={"validation_errors": errors},
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    处理 SQLAlchemy 数据库错误
    
    隐藏 SQL 语句等敏感信息，返回通用的数据库错误消息。
    
    Args:
        request: FastAPI 请求对象
        exc: SQLAlchemy 异常对象
        
    Returns:
        JSONResponse: 统一格式的错误响应
    """
    request_id = getattr(request.state, "request_id", None)
    
    # 记录完整的错误信息到日志（包含 SQL 语句等敏感信息）
    logger.error(
        "database_error",
        request_id=request_id,
        url=str(request.url),
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
        # 注意：traceback 只记录到日志，不返回给客户端
    )
    
    # 返回通用的数据库错误消息（不暴露 SQL 细节）
    message = "A database error occurred. Please try again later."
    
    error_response = format_error_response(
        code=ErrorCode.DATABASE_ERROR,
        message=message,
        exception=exc,
        request_id=request_id,
        include_debug=False,  # 强制不包含调试信息（即使开发环境）
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器（兜底）
    
    捕获所有未被其他处理器捕获的异常。
    
    Args:
        request: FastAPI 请求对象
        exc: 异常对象
        
    Returns:
        JSONResponse: 统一格式的错误响应
    """
    request_id = getattr(request.state, "request_id", None)
    
    # 提取用户信息（如果已认证）
    user_id = None
    try:
        # 尝试从 request.state 中获取用户信息
        user = getattr(request.state, "user", None)
        if user:
            user_id = getattr(user, "id", None)
    except Exception:
        pass  # 忽略获取用户信息时的错误
    
    # 记录完整的错误信息到日志
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        url=str(request.url),
        method=request.method,
        client_ip=request.client.host if request.client else None,
        user_id=user_id,
        error_type=type(exc).__name__,
        error=str(exc),
        # traceback 会自动包含在 structlog 的上下文中
    )
    
    # 获取用户友好的错误消息
    user_message = get_user_friendly_message(exc)
    
    # 格式化错误响应
    error_response = format_error_response(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=user_message,
        exception=exc,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )

