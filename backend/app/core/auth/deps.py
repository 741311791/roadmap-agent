"""
FastAPI Users 依赖注入

提供认证相关的 FastAPI 依赖。
"""
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
)

from app.models.database import User
from .strategies import get_jwt_strategy
from .user_manager import get_user_manager


# Bearer Token 传输（用于 API 调用）
bearer_transport = BearerTransport(tokenUrl="api/v1/auth/jwt/login")

# Cookie 传输（用于浏览器会话，可选）
cookie_transport = CookieTransport(
    cookie_name="fast_learning_auth",
    cookie_max_age=3600 * 24,  # 24 小时
    cookie_secure=False,  # 开发环境设为 False，生产环境应为 True
    cookie_httponly=True,
    cookie_samesite="lax",
)

# JWT 认证后端（Bearer Token）
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Cookie 认证后端（可选）
cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users 实例
fastapi_users = FastAPIUsers[User, str](
    get_user_manager,
    [auth_backend],  # 主要使用 JWT 认证
)

# 依赖注入：获取当前活跃用户（必须登录且激活）
current_active_user = fastapi_users.current_user(active=True)

# 依赖注入：获取当前用户（仅需登录）
current_user = fastapi_users.current_user()

# 依赖注入：获取当前超级管理员用户
current_superuser = fastapi_users.current_user(active=True, superuser=True)

