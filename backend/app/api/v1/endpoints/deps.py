"""
API 端点公共依赖

提供用户认证等通用依赖注入。
"""
from fastapi import Depends, Header, HTTPException
from typing import Optional
import structlog

from app.models.database import User
from app.core.auth.deps import current_active_user

logger = structlog.get_logger()


async def get_current_user_flexible(
    user: User = Depends(current_active_user),
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
) -> User:
    """
    灵活的用户认证依赖
    
    优先使用 JWT 认证，如果失败且提供了 x-user-id Header 则使用 Header。
    这是为了在内测期间提供向后兼容性。
    
    生产环境应该移除 x-user-id 支持。
    
    Args:
        user: JWT 认证的用户（可能为 None）
        x_user_id: 请求头中的用户 ID（兼容旧版）
        
    Returns:
        User 对象
        
    Raises:
        HTTPException: 401 如果未认证
    """
    if user:
        return user
    
    # JWT 认证失败，检查是否有 x-user-id Header
    if x_user_id:
        logger.warning(
            "using_deprecated_x_user_id_header",
            user_id=x_user_id,
            message="Using x-user-id header is deprecated. Please use JWT authentication."
        )
        # 创建一个虚拟的 User 对象（仅包含 id）
        # 注意：这是临时的兼容方案
        return User(
            id=x_user_id,
            email=f"{x_user_id}@temp.local",
            username=x_user_id,
            hashed_password="",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
    
    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Please provide a valid JWT token."
    )


async def get_current_user_id_flexible(
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
) -> str:
    """
    从 Header 获取用户 ID（兼容旧版前端）
    
    内测期间保持向后兼容性，允许前端继续使用 x-user-id Header。
    当 JWT 认证完全启用后，应该迁移到 get_current_user_flexible。
    
    Args:
        x_user_id: 请求头中的用户 ID
        
    Returns:
        用户 ID 字符串
        
    Raises:
        HTTPException: 401 如果未提供用户 ID
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Missing user ID. Please provide x-user-id header or use JWT authentication."
        )
    return x_user_id

