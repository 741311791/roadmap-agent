"""
FastAPI Users 数据库适配器

提供 SQLAlchemy 异步数据库支持。
"""
from typing import AsyncGenerator
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_readonly
from app.models.database import User


async def get_user_db(
    session: AsyncSession = Depends(get_db_readonly),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """
    获取用户数据库适配器
    
    FastAPI Users 使用此适配器与数据库交互。
    使用只读Session，因为认证操作主要是查询用户信息。
    
    注意：
    - 登录操作只需要读取用户数据，不需要事务
    - 使用只读会话避免"closed transaction"错误
    - 用户注册等写操作有独立的端点处理
    
    Args:
        session: 数据库会话（只读）
        
    Yields:
        SQLAlchemyUserDatabase 实例
    """
    yield SQLAlchemyUserDatabase(session, User)

