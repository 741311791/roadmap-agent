"""
Prometheus 监控中间件

自动记录 HTTP 请求的监控指标：
- 请求总数（按方法、路径、状态码）
- 请求响应时间（按方法、路径）
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.prometheus.instruments import REQUEST_COUNTER, RESPONSE_TIME_HISTOGRAM

logger = structlog.get_logger()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 监控中间件
    
    记录每个 HTTP 请求的指标到 Prometheus。
    """
    
    def __init__(self, app, app_name: str = "roadmap_agent"):
        super().__init__(app)
        self.app_name = app_name
    
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
        
        # 处理请求
        response = None
        status_code = 500  # 默认为 500，防止异常时没有状态码
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # 异常时也记录指标
            raise
        finally:
            # 计算请求耗时
            duration = time.time() - start_time
            
            # 记录 Prometheus 指标
            try:
                # 请求计数器
                REQUEST_COUNTER.labels(
                    app_name=self.app_name,
                    method=method,
                    path=path,
                    status_code=str(status_code),
                ).inc()
                
                # 响应时间直方图
                RESPONSE_TIME_HISTOGRAM.labels(
                    app_name=self.app_name,
                    method=method,
                    path=path,
                ).observe(duration)
            except Exception as e:
                # 指标记录失败不应影响正常响应
                logger.warning(
                    "prometheus_metrics_record_failed",
                    error=str(e),
                    method=method,
                    path=path,
                )
        
        return response

