"""
用户反馈 CRUD 操作。
"""
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import UserFeedback, beijing_now

logger = structlog.get_logger()


class UserFeedbackCRUD(BaseCRUD[UserFeedback, dict, dict]):
    """
    用户反馈 CRUD。

    提供产品反馈记录的创建与提交状态更新能力。
    """

    async def create_feedback(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        username_snapshot: str,
        email_snapshot: str,
        category: str,
        rating: int,
        summary: str,
        details: str,
        page_url: str,
        context_type: str,
        roadmap_id: str | None,
        concept_id: str | None,
        task_id: str | None,
        screenshot_filename: str | None,
    ) -> UserFeedback:
        """
        创建一条待提交的反馈记录。

        Args:
            session: 数据库会话。
            user_id: 用户 ID。
            username_snapshot: 用户名快照。
            email_snapshot: 邮箱快照。
            category: 反馈分类。
            rating: 用户评分。
            summary: 反馈标题。
            details: 反馈详情。
            page_url: 页面 URL。
            context_type: 触发场景。
            roadmap_id: 路线图 ID。
            concept_id: Concept ID。
            task_id: 任务 ID。
            screenshot_filename: 截图文件名。

        Returns:
            创建后的反馈记录。

        Raises:
            Exception: 当数据库写入失败时抛出。
        """

        feedback = UserFeedback(
            user_id=user_id,
            username_snapshot=username_snapshot,
            email_snapshot=email_snapshot,
            category=category,
            rating=rating,
            summary=summary,
            details=details,
            page_url=page_url,
            context_type=context_type,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            task_id=task_id,
            screenshot_filename=screenshot_filename,
            submission_status="pending",
        )
        session.add(feedback)
        await session.flush()

        logger.info(
            "user_feedback_created",
            feedback_id=feedback.feedback_id,
            user_id=user_id,
            category=category,
            context_type=context_type,
        )
        return feedback

    async def mark_submitted(
        self,
        session: AsyncSession,
        *,
        feedback: UserFeedback,
        linear_issue_id: str,
        linear_issue_identifier: str,
        linear_issue_url: str | None,
        screenshot_asset_url: str | None,
    ) -> UserFeedback:
        """
        标记反馈已成功提交到 Linear。

        Args:
            session: 数据库会话。
            feedback: 反馈记录。
            linear_issue_id: Linear Issue UUID。
            linear_issue_identifier: Linear Issue 短标识。
            linear_issue_url: Linear Issue 链接。
            screenshot_asset_url: 截图资产地址。

        Returns:
            更新后的反馈记录。

        Raises:
            Exception: 当数据库更新失败时抛出。
        """

        feedback.submission_status = "submitted"
        feedback.linear_issue_id = linear_issue_id
        feedback.linear_issue_identifier = linear_issue_identifier
        feedback.linear_issue_url = linear_issue_url
        feedback.screenshot_asset_url = screenshot_asset_url
        feedback.error_message = None
        feedback.updated_at = beijing_now()
        session.add(feedback)
        await session.flush()
        await session.refresh(feedback)
        return feedback

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        feedback: UserFeedback,
        error_message: str,
        screenshot_asset_url: str | None = None,
    ) -> UserFeedback:
        """
        标记反馈提交失败。

        Args:
            session: 数据库会话。
            feedback: 反馈记录。
            error_message: 错误信息。
            screenshot_asset_url: 已上传成功的截图地址。

        Returns:
            更新后的反馈记录。

        Raises:
            Exception: 当数据库更新失败时抛出。
        """

        feedback.submission_status = "failed"
        feedback.error_message = error_message
        feedback.screenshot_asset_url = screenshot_asset_url
        feedback.updated_at = beijing_now()
        session.add(feedback)
        await session.flush()
        await session.refresh(feedback)
        logger.warning(
            "user_feedback_submission_failed",
            feedback_id=feedback.feedback_id,
            error_message=error_message,
        )
        return feedback


_user_feedback_crud_instance: Optional[UserFeedbackCRUD] = None


def get_user_feedback_crud() -> UserFeedbackCRUD:
    """
    获取用户反馈 CRUD 单例。

    Args:
        None

    Returns:
        用户反馈 CRUD 实例。

    Raises:
        None
    """

    global _user_feedback_crud_instance
    if _user_feedback_crud_instance is None:
        _user_feedback_crud_instance = UserFeedbackCRUD(UserFeedback)
    return _user_feedback_crud_instance
