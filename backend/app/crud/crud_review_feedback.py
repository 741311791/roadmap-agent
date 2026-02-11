"""
人工审核反馈CRUD操作

提供人工审核反馈记录的数据库操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import HumanReviewFeedback

logger = structlog.get_logger()


class ReviewFeedbackCRUD(BaseCRUD[HumanReviewFeedback, dict, dict]):
    """
    人工审核反馈CRUD
    
    职责：
    - 审核反馈记录的增删改查
    - 根据任务ID查询审核反馈
    """
    
    async def get_latest_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[HumanReviewFeedback]:
        """
        获取任务的最新审核反馈
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            最新的审核反馈记录或None
        """
        stmt = (
            select(HumanReviewFeedback)
            .where(HumanReviewFeedback.task_id == task_id)
            .order_by(desc(HumanReviewFeedback.review_round))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        feedback = result.scalar_one_or_none()
        
        if feedback:
            logger.debug(
                "latest_review_feedback_found",
                task_id=task_id,
                review_round=feedback.review_round,
                approved=feedback.approved,
            )
        else:
            logger.debug(
                "no_review_feedback_found",
                task_id=task_id,
            )
        
        return feedback
    
    async def get_all_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[HumanReviewFeedback]:
        """
        获取任务的所有审核反馈
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            审核反馈列表（按轮次降序）
        """
        stmt = (
            select(HumanReviewFeedback)
            .where(HumanReviewFeedback.task_id == task_id)
            .order_by(desc(HumanReviewFeedback.review_round))
        )
        
        result = await session.execute(stmt)
        feedbacks = list(result.scalars().all())
        
        logger.debug(
            "review_feedbacks_listed",
            task_id=task_id,
            count=len(feedbacks),
        )
        
        return feedbacks
    
    async def count_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> int:
        """
        统计任务的审核轮次
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            审核轮次总数
        """
        feedbacks = await self.get_all_by_task(session, task_id)
        return len(feedbacks)
    
    async def create_feedback(
        self,
        session: AsyncSession,
        task_id: str,
        roadmap_id: str,
        user_id: str,
        approved: bool,
        feedback_text: Optional[str],
        roadmap_version_snapshot: dict,
        review_round: int = 1,
    ) -> HumanReviewFeedback:
        """
        创建人工审核反馈记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            roadmap_id: 路线图ID
            user_id: 用户ID
            approved: 是否批准
            feedback_text: 反馈文本
            roadmap_version_snapshot: 路线图框架快照
            review_round: 审核轮次
            
        Returns:
            创建的反馈记录
        """
        feedback = HumanReviewFeedback(
            task_id=task_id,
            roadmap_id=roadmap_id,
            user_id=user_id,
            approved=approved,
            feedback_text=feedback_text,
            roadmap_version_snapshot=roadmap_version_snapshot,
            review_round=review_round,
        )
        
        session.add(feedback)
        await session.flush()
        
        logger.info(
            "review_feedback_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            user_id=user_id,
            approved=approved,
            review_round=review_round,
            has_feedback_text=bool(feedback_text),
        )
        
        return feedback


# 单例模式
_review_feedback_crud_instance: Optional[ReviewFeedbackCRUD] = None


def get_review_feedback_crud() -> ReviewFeedbackCRUD:
    """获取ReviewFeedbackCRUD单例"""
    global _review_feedback_crud_instance
    if _review_feedback_crud_instance is None:
        _review_feedback_crud_instance = ReviewFeedbackCRUD(HumanReviewFeedback)
    return _review_feedback_crud_instance

