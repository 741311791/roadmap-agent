"""
FastAPI Users UserManager

自定义用户管理器，处理用户生命周期事件。
"""
from typing import Optional
from fastapi import Depends, Request, HTTPException
from fastapi_users import BaseUserManager, UUIDIDMixin
import structlog

from app.models.database import User, beijing_now
from .backend import get_user_db

logger = structlog.get_logger()


class UserManager(BaseUserManager[User, str]):
    """
    自定义用户管理器
    
    继承 FastAPI Users 的 BaseUserManager，添加自定义逻辑：
    - 临时密码过期检查
    - 用户注册后事件处理
    - 登录后事件处理
    """
    
    # 密码重置令牌密钥（用于忘记密码功能）
    reset_password_token_secret = "RESET_PASSWORD_SECRET"  # 应该从配置读取
    
    # 邮箱验证令牌密钥
    verification_token_secret = "VERIFICATION_SECRET"  # 应该从配置读取
    
    def parse_id(self, value: str) -> str:
        """
        解析用户 ID
        
        由于我们的 User ID 类型是 str（UUID 字符串），
        直接返回原值即可。
        """
        return value
    
    async def on_after_register(
        self,
        user: User,
        request: Optional[Request] = None,
    ) -> None:
        """
        用户注册后回调
        
        记录日志，可扩展为发送欢迎邮件等。
        """
        logger.info(
            "user_registered",
            user_id=user.id,
            email=user.email,
            username=user.username,
        )
    
    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[any] = None,
    ) -> None:
        """
        用户登录后回调
        
        检查临时密码是否过期。
        """
        # 检查密码是否过期
        if user.password_expires_at is not None:
            now = beijing_now()
            if user.password_expires_at < now:
                logger.warning(
                    "user_login_password_expired",
                    user_id=user.id,
                    email=user.email,
                    expired_at=user.password_expires_at.isoformat(),
                )
                raise HTTPException(
                    status_code=400,
                    detail="Your temporary password has expired. Please contact the administrator for a new invitation."
                )
        
        logger.info(
            "user_logged_in",
            user_id=user.id,
            email=user.email,
        )
    
    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ) -> None:
        """
        忘记密码后回调
        
        通常用于发送重置密码邮件。
        内测期间此功能可能不启用。
        """
        logger.info(
            "user_forgot_password",
            user_id=user.id,
            email=user.email,
        )
        # TODO: 发送重置密码邮件
    
    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ) -> None:
        """
        请求邮箱验证后回调
        
        内测期间可能不需要邮箱验证。
        """
        logger.info(
            "user_request_verify",
            user_id=user.id,
            email=user.email,
        )


async def get_user_manager(
    user_db=Depends(get_user_db),
) -> UserManager:
    """
    获取用户管理器实例
    
    FastAPI 依赖注入使用。
    """
    yield UserManager(user_db)

