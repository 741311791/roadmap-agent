"""
FastAPI Users 认证模块

提供基于 JWT 的用户认证功能。
"""
from .deps import (
    fastapi_users,
    auth_backend,
    current_active_user,
    current_user,
    get_user_manager,
)
from .schemas import UserCreate, UserRead, UserUpdate

__all__ = [
    "fastapi_users",
    "auth_backend",
    "current_active_user",
    "current_user",
    "get_user_manager",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]

