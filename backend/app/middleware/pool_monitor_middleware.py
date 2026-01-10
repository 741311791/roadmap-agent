"""
连接池健康监控中间件

功能：
1. 实时监控连接池使用率
2. 使用率 > 90% 时拒绝非关键请求
3. 记录连接池耗尽告警
4. 集成 Prometheus 指标
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class PoolMonitorMiddleware(BaseHTTPMiddleware):
    """
    数据库连接池监控中间件
    
    在每个请求前检查连接池状态，防止连接池耗尽导致服务不可用。
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        中间件主逻辑
        
        Args:
            request: HTTP 请求
            call_next: 下一个中间件/路由处理函数
            
        Returns:
            HTTP 响应
            
        Raises:
            HTTPException: 当连接池使用率 > 90% 时拒绝非关键请求
        """
        from app.db.session import engine
        
        pool = engine.pool
        checked_out = pool.checkedout()
        max_connections = pool.size() + pool._max_overflow
        usage_ratio = checked_out / max_connections if max_connections > 0 else 0
        
        # 使用率 > 90% 时触发保护机制
        if usage_ratio > 0.9:
            # 只允许健康检查端点通过
            if not request.url.path.startswith("/health"):
                logger.critical(
                    "connection_pool_critical",
                    usage_ratio=round(usage_ratio * 100, 1),
                    checked_out=checked_out,
                    max_connections=max_connections,
                    path=request.url.path,
                )
                raise HTTPException(
                    status_code=503,
                    detail="Service busy, please retry later (connection pool exhausted)",
                )
        
        # 使用率 > 80% 时记录警告
        elif usage_ratio > 0.8:
            logger.warning(
                "connection_pool_high_usage",
                usage_ratio=round(usage_ratio * 100, 1),
                checked_out=checked_out,
                max_connections=max_connections,
            )
        
        response = await call_next(request)
        return response

