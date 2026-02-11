"""
认证扩展端点

提供 FastAPI Users 未包含的额外认证功能：
- 登出（Token 撤销）
- 强制登出所有设备
- Token 黑名单统计（管理员）

重构变更：
- ✅ 从 users/auth.py 移动到 auth/auth.py
- ✅ 路由prefix从 /users/auth 改为 /auth
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
import time
from jose import jwt, JWTError

from app.core.auth.deps import current_active_user
from app.core.auth.jwt_blacklist import (
    add_to_blacklist,
    clear_user_tokens,
    get_blacklist_stats,
)
from app.models.database import User
from app.config.settings import settings
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.auth import (
    LogoutResponse,
    BlacklistStatsResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()

http_bearer = HTTPBearer()


@router.post("/logout", response_model=ResponseSchemaModel[LogoutResponse])
async def logout(
    current_user: User = Depends(current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> ResponseSchemaModel[LogoutResponse]:
    """
    用户登出（撤销当前 Token）
    
    机制：
    1. 解码 Token 获取 jti（JWT ID）和过期时间
    2. 将 jti 加入 Redis 黑名单
    3. 设置过期时间 = Token 剩余有效期
    4. Token 过期后自动清理
    
    Args:
        current_user: 当前用户（通过 JWT 验证）
        credentials: JWT Token（从 Authorization header 获取）
    
    Returns:
        登出成功消息
        
    Raises:
        RequestError: Token不包含必要字段或解码失败
    
    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/auth/logout \
          -H "Authorization: Bearer eyJ..."
        ```
    """
    token = credentials.credentials
    
    try:
        # 解码 Token 获取 jti 和过期时间
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not jti:
            raise errors.RequestError(msg="Token 不包含 jti 字段，无法撤销")
        
        if not exp:
            raise errors.RequestError(msg="Token 不包含过期时间，无法撤销")
        
        # 计算剩余有效期
        current_time = int(time.time())
        expires_in = max(int(exp) - current_time, 0)
        
        if expires_in == 0:
            # Token 已过期，无需加入黑名单
            logger.info(
                "logout_token_already_expired",
                user_id=current_user.id,
                jti=jti,
            )
        else:
            # 加入黑名单
            await add_to_blacklist(jti, expires_in)
            
            logger.info(
                "user_logged_out",
                user_id=current_user.id,
                jti=jti,
                expires_in=expires_in,
            )
        
        return response_base.success(data=LogoutResponse(
            message="成功登出",
            user_id=current_user.id,
        ))
        
    except JWTError as e:
        logger.error(
            "logout_token_decode_failed",
            error=str(e),
            user_id=current_user.id,
        )
        raise errors.RequestError(msg="Token 解码失败")


@router.post("/logout-all-devices", response_model=ResponseSchemaModel[LogoutResponse])
async def logout_all_devices(
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[LogoutResponse]:
    """
    强制登出所有设备（撤销用户所有 Token）
    
    ⚠️ 注意：此功能需要在 JWT payload 中包含 user_id 字段，
    并且在生成 jti 时使用特定格式（如：{user_id}:{random}）
    
    当前实现：由于 jti 是随机 UUID，无法批量撤销。
    需要修改 JWT 策略，在 jti 中包含 user_id。
    
    Args:
        current_user: 当前用户
    
    Returns:
        登出成功消息，包含清除的设备数量
    """
    # 清除用户所有 Token，返回清除的数量
    devices_count = await clear_user_tokens(current_user.id)
    
    logger.info(
        "user_logged_out_all_devices",
        user_id=current_user.id,
        devices_count=devices_count,
    )
    
    return response_base.success(data=LogoutResponse(
        message="已登出所有设备",
        user_id=current_user.id,
        devices_count=devices_count,
    ))


@router.get("/blacklist/stats", response_model=ResponseSchemaModel[BlacklistStatsResponse])
async def get_token_blacklist_stats(
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[BlacklistStatsResponse]:
    """
    获取 Token 黑名单统计（管理员功能）
    
    Args:
        current_user: 当前用户（需要管理员权限）
    
    Returns:
        黑名单统计信息，包含总数、活跃和过期的token数量
    """
    # 检查管理员权限
    if not current_user.is_superuser:
        raise errors.ForbiddenError(msg="需要管理员权限")
    
    stats = await get_blacklist_stats()
    
    return response_base.success(data=BlacklistStatsResponse(
        total_tokens=stats["total_tokens"],
        active_tokens=stats["active_tokens"],
        expired_tokens=stats["expired_tokens"],
    ))

