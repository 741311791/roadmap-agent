"""
超级管理员服务

负责处理:
- 初始超级管理员创建
- 超级管理员权限验证
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.models.database import User
from app.core.auth.user_manager import UserManager
from app.core.auth.schemas import UserCreate

logger = structlog.get_logger()


class SuperuserService:
    """超级管理员业务逻辑"""
    
    async def create_initial_superuser(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        user_manager: UserManager,
    ) -> dict:
        """
        创建初始超级管理员
        
        只有当系统中没有超级管理员时才能调用。
        
        Args:
            session: 数据库会话
            email: 管理员邮箱
            password: 管理员密码
            user_manager: 用户管理器
            
        Returns:
            创建结果字典
            
        Raises:
            ValueError: 超级管理员已存在
        """
        # 检查是否已存在超级管理员
        result = await session.execute(
            select(User).where(User.is_superuser == True)
        )
        if result.scalars().first():
            raise ValueError("Superuser already exists. This operation is disabled.")
        
        # 创建超级管理员
        username = email.split('@')[0]
        user_create = UserCreate(
            email=email.lower().strip(),
            username=username,
            password=password,
        )
        
        new_user = await user_manager.create(user_create)
        
        # 设置为超级管理员
        new_user.is_superuser = True
        new_user.is_verified = True
        new_user.is_active = True
        await session.flush()
        
        logger.info(
            "initial_superuser_created",
            user_id=new_user.id,
            email=email,
        )
        
        return {
            "success": True,
            "message": "Superuser created successfully",
            "email": email,
            "user_id": new_user.id,
        }
    
    async def check_superuser_exists(self, session: AsyncSession) -> bool:
        """
        检查是否存在超级管理员
        
        Args:
            session: 数据库会话
            
        Returns:
            是否存在超级管理员
        """
        result = await session.execute(
            select(User).where(User.is_superuser == True)
        )
        return result.scalars().first() is not None

