"""
管理员用户管理 API 端点

提供用户邀请和超级管理员创建功能。

重构变更：
- ✅ 从 admin.py 拆分出来
- ✅ 专注于用户相关的管理功能
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter, Depends
from pydantic import EmailStr
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.models.database import User
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.services.shared.email_service import get_email_service, EmailService
from app.services.admin import UserInviteService, SuperuserService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema
from app.schemas.admin import (
    InviteUserRequest,
    InviteUserResponse,
)

router = APIRouter(prefix="/users", tags=["admin-users"])
logger = structlog.get_logger()


@router.post("/invite", response_model=ResponseSchemaModel[InviteUserResponse])
async def invite_user(
    request: InviteUserRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
) -> ResponseSchemaModel[InviteUserResponse]:
    """
    邀请Waitlist用户
    
    为指定邮箱创建用户账号，生成临时密码。
    只有超级管理员可以调用。
    
    Args:
        request: 邀请请求（包含邮箱、密码有效期等）
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        user_manager: 用户管理器
        email_service: 邮件服务
        
    Returns:
        邀请结果（包含用户名、密码等）
        
    Raises:
        RequestError: 请求参数错误
        InternalServerError: 服务器内部错误
    """
    logger.info(
        "admin_invite_user_requested",
        admin_id=current_user.id,
        target_email=request.email,
    )
    
    try:
        service = UserInviteService()
        result = await service.invite_single_user(
            session=db,
            email=request.email,
            password_validity_days=request.password_validity_days,
            user_manager=user_manager,
            email_service=email_service if request.send_email else None,
            send_email=request.send_email,
        )
        
        logger.info(
            "admin_invite_user_success",
            admin_id=current_user.id,
            email=request.email,
        )
        
        return response_base.success(data=InviteUserResponse(**result))
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("admin_invite_user_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg=f"用户创建失败: {str(e)}")


@router.post("/superuser")
async def create_initial_superuser(
    email: EmailStr,
    password: str,
    db: CurrentSessionTransaction,
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    创建初始超级管理员（仅在没有超级管理员时可用）
    
    这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
    
    Args:
        email: 管理员邮箱
        password: 管理员密码
        db: 数据库会话（自动commit/rollback）
        user_manager: 用户管理器
        
    Returns:
        创建结果
        
    Raises:
        RequestError: 已存在超级管理员或参数错误
        InternalServerError: 创建失败
    """
    try:
        service = SuperuserService()
        result = await service.create_initial_superuser(db, email, password, user_manager)
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("create_superuser_failed", email=email, error=str(e))
        raise errors.InternalServerError(msg=f"超级管理员创建失败: {str(e)}")

