"""
自定义异常类（用于API层抛出）

提供可在业务逻辑中直接抛出的异常类，自动映射到HTTP状态码和错误码。
"""
from typing import Any, Optional

from app.core.exceptions import ErrorCode


class BaseAPIException(Exception):
    """
    API异常基类
    
    所有业务异常都继承此类，全局异常处理器会捕获并转换为统一的JSON响应。
    """
    
    code: int = 500
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR
    default_message: str = "An error occurred"
    
    def __init__(
        self,
        msg: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        初始化异常
        
        Args:
            msg: 自定义错误消息（可选，默认使用default_message）
            details: 错误详情（可选）
        """
        self.msg = msg or self.default_message
        self.details = details
        super().__init__(self.msg)


class RequestError(BaseAPIException):
    """请求参数错误（400 Bad Request）"""
    code = 400
    error_code = ErrorCode.BAD_REQUEST
    default_message = "请求参数错误"


class UnauthorizedError(BaseAPIException):
    """未授权（401 Unauthorized）"""
    code = 401
    error_code = ErrorCode.UNAUTHORIZED
    default_message = "未授权访问"


class ForbiddenError(BaseAPIException):
    """权限不足（403 Forbidden）"""
    code = 403
    error_code = ErrorCode.FORBIDDEN
    default_message = "权限不足"


class NotFoundError(BaseAPIException):
    """资源不存在（404 Not Found）"""
    code = 404
    error_code = ErrorCode.NOT_FOUND
    default_message = "资源不存在"


class ConflictError(BaseAPIException):
    """资源冲突（409 Conflict）"""
    code = 409
    error_code = ErrorCode.CONFLICT
    default_message = "资源已存在"


class ValidationError(BaseAPIException):
    """数据验证错误（422 Unprocessable Entity）"""
    code = 422
    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "数据验证失败"


class InternalServerError(BaseAPIException):
    """服务器内部错误（500 Internal Server Error）"""
    code = 500
    error_code = ErrorCode.INTERNAL_SERVER_ERROR
    default_message = "服务器内部错误"


class DatabaseError(BaseAPIException):
    """数据库错误（500 Internal Server Error）"""
    code = 500
    error_code = ErrorCode.DATABASE_ERROR
    default_message = "数据库操作失败"


class ExternalServiceError(BaseAPIException):
    """外部服务错误（500 Internal Server Error）"""
    code = 500
    error_code = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message = "外部服务调用失败"


class TimeoutError(BaseAPIException):
    """超时错误（500 Internal Server Error）"""
    code = 500
    error_code = ErrorCode.TIMEOUT_ERROR
    default_message = "请求超时"


# ===== 便捷的错误模块（供API层导入使用）=====

class errors:
    """
    错误类便捷访问
    
    使用示例：
    ```python
    from app.core.custom_exceptions import errors
    
    raise errors.NotFoundError(msg="路线图不存在")
    raise errors.RequestError(msg="参数非法", details={"field": "roadmap_id"})
    ```
    """
    RequestError = RequestError
    UnauthorizedError = UnauthorizedError
    ForbiddenError = ForbiddenError
    NotFoundError = NotFoundError
    ConflictError = ConflictError
    ValidationError = ValidationError
    InternalServerError = InternalServerError
    DatabaseError = DatabaseError
    ExternalServiceError = ExternalServiceError
    TimeoutError = TimeoutError

