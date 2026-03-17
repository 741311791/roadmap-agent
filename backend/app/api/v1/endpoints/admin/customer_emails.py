"""
客户邮件管理 API 端点

提供管理员客户邮件模块的用户列表、模板读取和批量发送功能。
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.core.auth.deps import current_superuser
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.models.database import User
from app.schemas.admin import (
    CustomerEmailSendRequest,
    CustomerEmailSendResponse,
    CustomerEmailTemplateItem,
    CustomerEmailTemplateListResponse,
    CustomerEmailUserItem,
    CustomerEmailUserListResponse,
)
from app.services.admin.customer_email_service import CustomerEmailService
from app.services.shared.email_service import EmailService, get_email_service

logger = structlog.get_logger()

router = APIRouter(prefix="/customer-emails", tags=["admin-customer-emails"])


@router.get("/users", response_model=ResponseSchemaModel[CustomerEmailUserListResponse])
async def list_customer_email_users(
    db: CurrentSession,
    current_user: User = Depends(current_superuser),
    keyword: Annotated[str | None, Query(description="邮箱或用户名关键词")] = None,
    is_active: Annotated[bool | None, Query(description="激活状态过滤")] = None,
    include_superusers: Annotated[bool, Query(description="是否包含超级管理员")] = False,
    limit: Annotated[int, Query(ge=1, le=500, description="返回数量限制")] = 100,
    offset: Annotated[int, Query(ge=0, description="分页偏移")] = 0,
) -> ResponseSchemaModel[CustomerEmailUserListResponse]:
    """
    获取客户邮件模块用户列表

    Args:
        db: 数据库会话
        current_user: 当前超级管理员
        keyword: 邮箱或用户名关键词
        is_active: 激活状态过滤
        include_superusers: 是否包含超级管理员
        limit: 返回数量限制
        offset: 分页偏移

    Returns:
        用户列表与总数
    """
    service = CustomerEmailService()
    result = await service.list_users(
        db,
        keyword=keyword,
        is_active=is_active,
        include_superusers=include_superusers,
        limit=limit,
        offset=offset,
    )

    logger.info(
        "admin_list_customer_email_users",
        admin_id=current_user.id,
        keyword=keyword,
        is_active=is_active,
        include_superusers=include_superusers,
        total=result["total"],
    )

    return response_base.success(
        data=CustomerEmailUserListResponse(
            items=[
                CustomerEmailUserItem(
                    email=item.email,
                    username=item.username,
                    is_active=item.is_active,
                    is_superuser=item.is_superuser,
                    is_verified=item.is_verified,
                    created_at=item.created_at.isoformat(),
                )
                for item in result["items"]
            ],
            total=result["total"],
        )
    )


@router.get("/templates", response_model=ResponseSchemaModel[CustomerEmailTemplateListResponse])
async def list_customer_email_templates(
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[CustomerEmailTemplateListResponse]:
    """
    获取客户邮件内置模板

    Args:
        current_user: 当前超级管理员

    Returns:
        模板列表
    """
    service = CustomerEmailService()
    templates = service.list_templates()

    logger.info(
        "admin_list_customer_email_templates",
        admin_id=current_user.id,
        total=len(templates),
    )

    return response_base.success(
        data=CustomerEmailTemplateListResponse(
            items=[
                CustomerEmailTemplateItem(
                    key=item["key"],
                    name=item["name"],
                    description=item["description"],
                    subject=item["subject"],
                    html_content=item["html_content"],
                    text_content=item["text_content"],
                )
                for item in templates
            ]
        )
    )


@router.post("/send", response_model=ResponseSchemaModel[CustomerEmailSendResponse])
async def send_customer_emails(
    request: CustomerEmailSendRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    email_service: EmailService = Depends(get_email_service),
) -> ResponseSchemaModel[CustomerEmailSendResponse]:
    """
    批量发送客户邮件

    Args:
        request: 群发请求
        db: 数据库会话
        current_user: 当前超级管理员
        email_service: 邮件服务

    Returns:
        批量发送结果
    """
    service = CustomerEmailService()

    try:
        success_count, error_list = await service.send_custom_emails(
            db,
            recipient_emails=[str(email) for email in request.recipient_emails],
            subject=request.subject,
            html_content=request.html_content,
            text_content=request.text_content,
            email_service=email_service,
            admin_user_id=current_user.id,
        )
    except Exception as exc:
        logger.error(
            "admin_send_customer_emails_failed",
            admin_id=current_user.id,
            error=str(exc),
        )
        raise errors.InternalServerError(msg="客户邮件发送失败")

    return response_base.success(
        data=CustomerEmailSendResponse(
            success=success_count,
            failed=len(error_list),
            errors=error_list,
        )
    )

