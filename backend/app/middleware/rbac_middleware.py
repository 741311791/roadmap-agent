"""
RBAC (Role-Based Access Control) 中间件

基于用户角色的权限控制中间件。

当前实现：
- 简化版 RBAC，支持基本的角色检查
- 预留扩展点，可根据需求添加复杂的权限规则

未来扩展：
- 资源级权限控制
- 动态权限规则
- 权限缓存
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.custom_exceptions import errors

logger = structlog.get_logger()


class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC 中间件
    
    检查用户是否有权访问特定资源。
    当前为简化实现，主要预留架构位置。
    """
    
    # 定义需要特殊权限的路径前缀
    # ⚠️ 已禁用：这些路径由 FastAPI Users 的依赖注入保护 (current_superuser)
    # ADMIN_PATHS = [
    #     "/api/v1/admin",
    #     "/api/v1/management",
    # ]
    ADMIN_PATHS = []  # 空列表：所有管理员路由由路由级依赖注入保护
    
    # 公开路径（无需认证）
    PUBLIC_PATHS = [
        "/api/v1/auth",
        "/api/v1/docs",
        "/api/v1/openapi.json",
        "/health",
        "/metrics",
    ]
    
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
            
        Raises:
            ForbiddenError: 无权访问
        """
        path = request.url.path
        
        # 检查是否是公开路径
        if any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # 检查是否是管理员路径
        is_admin_path = any(path.startswith(admin_path) for admin_path in self.ADMIN_PATHS)
        
        if is_admin_path:
            # 检查用户是否已认证且是管理员
            user = getattr(request.state, "user", None)
            
            if not user:
                raise errors.UnauthorizedError(msg="需要登录才能访问此资源")
            
            # 检查是否是超级管理员
            is_superuser = getattr(user, "is_superuser", False)
            
            if not is_superuser:
                logger.warning(
                    "rbac_access_denied",
                    user_id=getattr(user, "id", None),
                    path=path,
                    reason="not_superuser",
                )
                raise errors.ForbiddenError(msg="无权访问此资源，需要管理员权限")
        
        # 继续处理请求
        return await call_next(request)

