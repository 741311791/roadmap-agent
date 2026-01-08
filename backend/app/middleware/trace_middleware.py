"""
TraceID中间件 - 请求链路追踪

为每个HTTP请求注入唯一的trace_id，支持分布式追踪和全链路日志关联。

功能：
1. 从请求头读取X-Trace-ID（如果有）或生成新的UUID
2. 注入到request.state.trace_id（后续可在路由中访问）
3. 绑定到structlog上下文（所有日志自动包含trace_id）
4. 在响应头中返回X-Trace-ID（前端可传递实现跨服务追踪）

使用场景：
- 单个请求的所有日志可按trace_id聚合查询
- 前端可传递trace_id实现端到端追踪
- 微服务间可传递trace_id实现分布式追踪
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    TraceID中间件
    
    为每个请求注入trace_id，支持分布式追踪。
    
    执行流程：
    1. 优先使用客户端传入的X-Trace-ID（跨服务追踪）
    2. 否则生成新的UUID
    3. 注入到request.state
    4. 绑定到structlog上下文（所有日志自动包含trace_id）
    5. 在响应头中返回X-Trace-ID
    
    示例日志查询：
    ```bash
    # 查询单个请求的所有日志
    grep "trace_id=abc-123" logs/app.log
    
    # 输出示例：
    # 2026-01-08 10:00:01 INFO request_started trace_id=abc-123 method=POST path=/api/v1/roadmaps/generate
    # 2026-01-08 10:00:02 INFO task_created trace_id=abc-123 task_id=task-456
    # 2026-01-08 10:00:05 INFO llm_call_started trace_id=abc-123 model=gpt-4
    # 2026-01-08 10:00:10 INFO llm_call_completed trace_id=abc-123 tokens=1234
    # 2026-01-08 10:00:11 INFO request_completed trace_id=abc-123 status_code=200
    ```
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        处理请求并注入trace_id
        
        Args:
            request: Starlette Request对象
            call_next: 下一个中间件/路由处理器
            
        Returns:
            Response对象（包含X-Trace-ID响应头）
        """
        # ✅ 优先使用客户端传入的trace_id（跨服务追踪）
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        
        # ✅ 注入到request.state（后续路由可访问）
        request.state.trace_id = trace_id
        
        # ✅ 绑定到structlog上下文（所有日志自动包含trace_id）
        with structlog.contextvars.bound_contextvars(trace_id=trace_id):
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )
            
            try:
                # 调用下游中间件/路由
                response = await call_next(request)
                
                # ✅ 在响应头中返回trace_id
                response.headers["X-Trace-ID"] = trace_id
                
                logger.info(
                    "request_completed",
                    status_code=response.status_code,
                )
                
                return response
                
            except Exception as e:
                logger.error(
                    "request_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise


def get_trace_id(request: Request) -> str:
    """
    从request.state获取trace_id
    
    便捷函数，用于在路由处理器中获取trace_id。
    
    Args:
        request: FastAPI/Starlette Request对象
        
    Returns:
        trace_id字符串
        
    Example:
        ```python
        from fastapi import Request
        from app.middleware.trace_middleware import get_trace_id
        
        @router.get("/example")
        async def example(request: Request):
            trace_id = get_trace_id(request)
            logger.info("处理请求", trace_id=trace_id)
            return {"trace_id": trace_id}
        ```
    """
    return getattr(request.state, "trace_id", "unknown")

