"""
用户CRUD操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import User
from app.schemas.user import UserCreate, UserUpdate

class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    """
    用户CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            session: 数据库会话
            username: 用户名
            
        Returns:
            用户实例或None
        """
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            session: 数据库会话
            email: 邮箱
            
        Returns:
            用户实例或None
        """
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """
        获取活跃用户列表
        
        Args:
            session: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            用户列表
        """
        result = await session.execute(
            select(User)
            .where(User.is_active == True)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

# 工厂函数
def get_user_crud() -> UserCRUD:
    """获取UserCRUD实例"""
    return UserCRUD(User)

