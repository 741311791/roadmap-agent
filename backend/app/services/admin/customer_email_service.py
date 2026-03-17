"""
客户邮件服务

负责管理员客户邮件模块的用户查询、模板读取和批量发送。
"""
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_user import get_user_crud
from app.models.database import User
from app.services.admin.customer_email_renderer import (
    compose_email_html,
    markdown_to_plain_text,
)
from app.services.admin.customer_email_templates import (
    DEFAULT_CUSTOMER_EMAIL_TEMPLATES,
)
from app.services.shared.email_service import EmailService

logger = structlog.get_logger()


class CustomerEmailService:
    """客户邮件业务服务"""

    def __init__(self) -> None:
        """初始化服务依赖"""
        self.user_crud = get_user_crud()

    async def list_users(
        self,
        session: AsyncSession,
        *,
        keyword: str | None = None,
        is_active: bool | None = None,
        include_superusers: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        获取客户邮件模块用户列表

        Args:
            session: 数据库会话
            keyword: 邮箱或用户名关键词
            is_active: 激活状态过滤
            include_superusers: 是否包含超级管理员
            limit: 分页大小
            offset: 分页偏移

        Returns:
            列表数据与总数
        """
        users = await self.user_crud.get_customer_email_users(
            session,
            keyword=keyword,
            is_active=is_active,
            include_superusers=include_superusers,
            skip=offset,
            limit=limit,
        )
        total = await self.user_crud.count_customer_email_users(
            session,
            keyword=keyword,
            is_active=is_active,
            include_superusers=include_superusers,
        )
        return {
            "items": users,
            "total": total,
        }

    def list_templates(self) -> list[dict[str, str | None]]:
        """
        获取内置邮件模板列表

        Returns:
            模板列表
        """
        return DEFAULT_CUSTOMER_EMAIL_TEMPLATES

    async def send_custom_emails(
        self,
        session: AsyncSession,
        *,
        recipient_emails: list[str],
        subject: str,
        html_content: str,
        text_content: str | None,
        email_service: EmailService,
        admin_user_id: str,
    ) -> tuple[int, list[dict[str, str]]]:
        """
        批量发送客户邮件

        Args:
            session: 数据库会话
            recipient_emails: 收件人邮箱列表
            subject: 邮件主题
            html_content: HTML 模板壳
            text_content: Markdown 正文
            email_service: 邮件服务
            admin_user_id: 管理员 ID

        Returns:
            成功数量与错误列表
        """
        normalized_emails: list[str] = []
        seen_emails: set[str] = set()

        # 第一步：去重并标准化邮箱，避免重复发送。
        for email in recipient_emails:
            normalized_email = email.lower().strip()
            if normalized_email and normalized_email not in seen_emails:
                normalized_emails.append(normalized_email)
                seen_emails.add(normalized_email)

        result = await session.execute(
            select(User).where(User.email.in_(normalized_emails))
        )
        user_map = {
            user.email.lower(): user
            for user in result.scalars().all()
        }

        success_count = 0
        errors: list[dict[str, str]] = []
        markdown_content = (text_content or "").strip()
        composed_html = compose_email_html(
            html_content,
            subject=subject,
            markdown_content=markdown_content,
        )
        plain_text_fallback = markdown_to_plain_text(markdown_content) if markdown_content else None

        # 第二步：逐个发送邮件，确保能精确记录失败对象。
        for email in normalized_emails:
            user = user_map.get(email)

            if not user:
                errors.append({"email": email, "error": "User not found"})
                continue

            try:
                email_sent = await email_service.send_custom_email(
                    to_email=email,
                    subject=subject,
                    html_content=composed_html,
                    text_content=plain_text_fallback,
                )

                if not email_sent:
                    errors.append({"email": email, "error": "Failed to send email"})
                    continue

                success_count += 1
                logger.info(
                    "customer_email_sent",
                    admin_user_id=admin_user_id,
                    user_id=user.id,
                    email=email,
                    subject=subject,
                )
            except Exception as exc:
                logger.error(
                    "customer_email_send_failed",
                    admin_user_id=admin_user_id,
                    email=email,
                    error=str(exc),
                )
                errors.append({"email": email, "error": str(exc)})

        return success_count, errors

