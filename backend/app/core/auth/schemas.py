"""
FastAPI Users Pydantic Schemas

定义用户数据的序列化/反序列化模式。
"""
from datetime import datetime
from typing import Any, Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[str]):
    """
    用户读取模式
    
    包含所有可对外展示的用户信息。
    """
    username: str
    avatar_config: Optional[dict[str, Any]] = None
    password_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    """
    用户创建模式
    
    注册或管理员创建用户时的输入模式。
    """
    username: str


class UserUpdate(schemas.BaseUserUpdate):
    """
    用户更新模式
    
    用户自行更新信息时的输入模式。
    支持更新用户名、密码（继承自 BaseUserUpdate）和头像配置。
    """
    username: Optional[str] = None
    avatar_config: Optional[dict[str, Any]] = None

