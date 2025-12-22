"""
人工审核反馈和修改计划 Repository

负责 HumanReviewFeedback 和 EditPlanRecord 表的数据访问操作。

职责范围：
- 人工审核反馈记录的 CRUD 操作
- 修改计划记录的 CRUD 操作
- 根据 task_id/feedback_id 查询记录
- 查询审核历史和修改计划历史
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import HumanReviewFeedback, EditPlanRecord
from app.models.domain import EditPlan
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class ReviewFeedbackRepository(BaseRepository[HumanReviewFeedback]):
    """
    人工审核反馈数据访问层
    
    管理用户在 human_review 节点提交的审核反馈记录。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, HumanReviewFeedback)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_latest_by_task(
        self, 
        task_id: str
    ) -> Optional[HumanReviewFeedback]:
        """
        获取任务的最新审核反馈
        
        Args:
            task_id: 任务 ID
            
        Returns:
            最新的审核反馈记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(HumanReviewFeedback)
            .where(HumanReviewFeedback.task_id == task_id)
            .order_by(HumanReviewFeedback.review_round.desc())
            .limit(1)
        )
        
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
        task_id: str
    ) -> List[HumanReviewFeedback]:
        """
        获取任务的所有审核反馈（按轮次排序）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            审核反馈列表（按轮次降序）
        """
        result = await self.session.execute(
            select(HumanReviewFeedback)
            .where(HumanReviewFeedback.task_id == task_id)
            .order_by(HumanReviewFeedback.review_round.desc())
        )
        
        feedbacks = list(result.scalars().all())
        
        logger.debug(
            "review_feedbacks_listed",
            task_id=task_id,
            count=len(feedbacks),
        )
        
        return feedbacks
    
    async def count_by_task(self, task_id: str) -> int:
        """
        统计任务的审核轮次（用于计算下一轮的 review_round）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            审核轮次总数
        """
        feedbacks = await self.get_all_by_task(task_id)
        return len(feedbacks)
    
    # ============================================================
    # 创建方法
    # ============================================================
    
    async def create_feedback(
        self,
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
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            approved: 是否批准
            feedback_text: 反馈文本（拒绝时必填）
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
        
        await self.create(feedback, flush=True)
        
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


class EditPlanRepository(BaseRepository[EditPlanRecord]):
    """
    修改计划记录数据访问层
    
    管理 EditPlanAnalyzerAgent 生成的结构化修改计划记录。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, EditPlanRecord)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_latest_by_task(
        self, 
        task_id: str
    ) -> Optional[EditPlanRecord]:
        """
        获取任务的最新修改计划
        
        Args:
            task_id: 任务 ID
            
        Returns:
            最新的修改计划记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(EditPlanRecord)
            .where(EditPlanRecord.task_id == task_id)
            .order_by(EditPlanRecord.created_at.desc())
            .limit(1)
        )
        
        plan = result.scalar_one_or_none()
        
        if plan:
            logger.debug(
                "latest_edit_plan_found",
                task_id=task_id,
                plan_id=plan.id,
                intents_count=len(plan.intents) if plan.intents else 0,
            )
        else:
            logger.debug(
                "no_edit_plan_found",
                task_id=task_id,
            )
        
        return plan
    
    async def get_by_feedback_id(
        self, 
        feedback_id: str
    ) -> Optional[EditPlanRecord]:
        """
        根据反馈 ID 获取修改计划
        
        Args:
            feedback_id: 反馈记录 ID
            
        Returns:
            修改计划记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(EditPlanRecord)
            .where(EditPlanRecord.feedback_id == feedback_id)
        )
        
        plan = result.scalar_one_or_none()
        
        if plan:
            logger.debug(
                "edit_plan_found_by_feedback",
                feedback_id=feedback_id,
                plan_id=plan.id,
            )
        else:
            logger.debug(
                "no_edit_plan_found_for_feedback",
                feedback_id=feedback_id,
            )
        
        return plan
    
    async def get_all_by_task(
        self, 
        task_id: str
    ) -> List[EditPlanRecord]:
        """
        获取任务的所有修改计划（按时间排序）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            修改计划列表（按创建时间降序）
        """
        result = await self.session.execute(
            select(EditPlanRecord)
            .where(EditPlanRecord.task_id == task_id)
            .order_by(EditPlanRecord.created_at.desc())
        )
        
        plans = list(result.scalars().all())
        
        logger.debug(
            "edit_plans_listed",
            task_id=task_id,
            count=len(plans),
        )
        
        return plans
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def create_plan(
        self,
        task_id: str,
        roadmap_id: str,
        feedback_id: str,
        edit_plan: EditPlan,
        confidence: Optional[str] = None,
        needs_clarification: bool = False,
        clarification_questions: Optional[List[str]] = None,
    ) -> EditPlanRecord:
        """
        创建修改计划记录
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            feedback_id: 关联的用户反馈记录 ID
            edit_plan: 修改计划对象
            confidence: 解析置信度
            needs_clarification: 是否需要澄清
            clarification_questions: 澄清问题列表
            
        Returns:
            创建的修改计划记录
        """
        plan_record = EditPlanRecord(
            task_id=task_id,
            roadmap_id=roadmap_id,
            feedback_id=feedback_id,
            feedback_summary=edit_plan.feedback_summary,
            scope_analysis=edit_plan.scope_analysis,
            intents=[intent.model_dump() for intent in edit_plan.intents],
            preservation_requirements=edit_plan.preservation_requirements,
            full_plan_data=edit_plan.model_dump(),
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
            execution_status="pending",
        )
        
        await self.create(plan_record, flush=True)
        
        logger.info(
            "edit_plan_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            feedback_id=feedback_id,
            plan_id=plan_record.id,
            intents_count=len(edit_plan.intents),
            confidence=confidence,
        )
        
        return plan_record
    
    async def update_execution_status(
        self,
        plan_id: str,
        status: str,
    ) -> Optional[EditPlanRecord]:
        """
        更新修改计划的执行状态
        
        Args:
            plan_id: 修改计划 ID
            status: 新的执行状态（pending, executing, completed, failed）
            
        Returns:
            更新后的修改计划记录
        """
        plan = await self.get_by_id(plan_id)
        
        if not plan:
            logger.warning(
                "edit_plan_not_found_for_status_update",
                plan_id=plan_id,
            )
            return None
        
        await self.update_by_id(plan_id, execution_status=status)
        
        # 重新获取更新后的记录
        updated_plan = await self.get_by_id(plan_id)
        
        logger.info(
            "edit_plan_status_updated",
            plan_id=plan_id,
            old_status=plan.execution_status,
            new_status=status,
        )
        
        return updated_plan

