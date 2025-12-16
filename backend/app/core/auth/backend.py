"""
FastAPI Users 数据库适配器

提供 SQLAlchemy 异步数据库支持。
"""
from typing import AsyncGenerator
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import User


async def get_user_db(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """
    获取用户数据库适配器
    
    FastAPI Users 使用此适配器与数据库交互。
    
    Args:
        session: 数据库会话
        
    Yields:
        SQLAlchemyUserDatabase 实例
    """
    yield SQLAlchemyUserDatabase(session, User)

