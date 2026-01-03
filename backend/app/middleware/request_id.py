"""
Request ID 中间件

为每个请求生成唯一标识，方便追踪和排查错误。
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Request ID 中间件
    
    功能：
    1. 从请求头中读取 X-Request-ID（如果客户端提供）
    2. 如果没有提供，自动生成一个 UUID
    3. 将 request_id 注入到 request.state.request_id
    4. 在响应头中返回 X-Request-ID
    
    使用方式：
        app.add_middleware(RequestIDMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        处理请求，注入 request_id
        
        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: 响应对象（包含 X-Request-ID 响应头）
        """
        # 1. 尝试从请求头中获取 request_id
        request_id = request.headers.get("X-Request-ID")
        
        # 2. 如果没有，生成一个新的 UUID
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 3. 注入到 request.state（供后续处理器使用）
        request.state.request_id = request_id
        
        # 4. 将 request_id 添加到 structlog 的上下文中
        # 这样所有日志都会自动包含 request_id
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            # 5. 调用下一个处理器
            response = await call_next(request)
            
            # 6. 在响应头中返回 request_id
            response.headers["X-Request-ID"] = request_id
            
            return response

