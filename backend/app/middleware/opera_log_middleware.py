"""
操作日志中间件

记录所有 API 请求的操作日志，包括：
- 请求路径、方法、参数
- 响应状态码、耗时
- 用户信息（如果已认证）
- 异常信息（如果发生错误）

用于：
- 审计追踪
- 性能监控
- 问题排查
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class OperaLogMiddleware(BaseHTTPMiddleware):
    """
    操作日志中间件
    
    记录每个 HTTP 请求的完整生命周期。
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        中间件处理逻辑
        
        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            HTTP 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()
        
        # 提取请求信息
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # 提取用户信息（如果已认证）
        user_id = None
        try:
            # 尝试从请求状态中获取用户信息（由认证中间件设置）
            if hasattr(request.state, "user"):
                user = request.state.user
                user_id = getattr(user, "id", None)
        except Exception:
            pass
        
        # 记录请求开始
        logger.info(
            "http_request_started",
            method=method,
            path=path,
            client_host=client_host,
            user_id=user_id,
        )
        
        # 处理请求
        response = None
        status_code = None
        error = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error = str(e)
            logger.error(
                "http_request_error",
                method=method,
                path=path,
                error=error,
                exc_info=True,
            )
            raise
        finally:
            # 计算请求耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录请求完成
            log_data = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "client_host": client_host,
                "user_id": user_id,
            }
            
            if error:
                log_data["error"] = error
            
            # 根据状态码选择日志级别
            if status_code and status_code >= 500:
                logger.error("http_request_completed", **log_data)
            elif status_code and status_code >= 400:
                logger.warning("http_request_completed", **log_data)
            else:
                logger.info("http_request_completed", **log_data)
        
        return response

