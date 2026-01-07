"""
工作流相关CRUD操作

提供意图分析、执行日志、验证记录、编辑记录的数据库操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import (
    IntentAnalysisMetadata,
    ExecutionLog,
    StructureValidationRecord,
    RoadmapEditRecord,
    EditPlanRecord,
    HumanReviewFeedback,
)

logger = structlog.get_logger()


class IntentAnalysisCRUD(BaseCRUD[IntentAnalysisMetadata, dict, dict]):
    """
    意图分析CRUD
    
    职责：
    - 意图分析记录的增删改查
    - 根据任务ID查询分析记录
    """
    
    async def get_by_task_id(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        根据任务ID获取意图分析
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            意图分析记录或None
        """
        stmt = select(IntentAnalysisMetadata).where(
            IntentAnalysisMetadata.task_id == task_id
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        根据路线图ID获取意图分析
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            意图分析记录或None
        """
        stmt = select(IntentAnalysisMetadata).where(
            IntentAnalysisMetadata.roadmap_id == roadmap_id
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# 单例模式
_intent_analysis_crud_instance: Optional[IntentAnalysisCRUD] = None


def get_intent_analysis_crud() -> IntentAnalysisCRUD:
    """获取IntentAnalysisCRUD单例"""
    global _intent_analysis_crud_instance
    if _intent_analysis_crud_instance is None:
        _intent_analysis_crud_instance = IntentAnalysisCRUD(IntentAnalysisMetadata)
    return _intent_analysis_crud_instance


class ExecutionLogCRUD(BaseCRUD[ExecutionLog, dict, dict]):
    """
    执行日志CRUD
    
    职责：
    - 执行日志的增删改查
    - 根据任务ID查询日志
    - 日志流式读取
    """
    
    async def get_logs_by_task_id(
        self,
        session: AsyncSession,
        task_id: str,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """
        根据任务ID获取执行日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            limit: 返回日志条数限制
            
        Returns:
            日志列表（按时间倒序）
        """
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.task_id == task_id)
            .order_by(desc(ExecutionLog.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_logs_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
        step_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """
        根据路线图ID获取执行日志
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            step_name: 步骤名称（可选筛选）
            limit: 返回日志条数限制
            
        Returns:
            日志列表（按时间倒序）
        """
        stmt = select(ExecutionLog).where(ExecutionLog.roadmap_id == roadmap_id)
        
        if step_name:
            stmt = stmt.where(ExecutionLog.step_name == step_name)
        
        stmt = stmt.order_by(desc(ExecutionLog.created_at)).limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


# 单例模式
_execution_log_crud_instance: Optional[ExecutionLogCRUD] = None


def get_execution_log_crud() -> ExecutionLogCRUD:
    """获取ExecutionLogCRUD单例"""
    global _execution_log_crud_instance
    if _execution_log_crud_instance is None:
        _execution_log_crud_instance = ExecutionLogCRUD(ExecutionLog)
    return _execution_log_crud_instance


class ValidationCRUD(BaseCRUD[StructureValidationRecord, dict, dict]):
    """
    验证记录CRUD
    
    职责：
    - 验证记录的增删改查
    - 根据路线图ID/任务ID查询验证记录
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[StructureValidationRecord]:
        """
        根据路线图ID获取所有验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            验证记录列表（按时间倒序）
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.roadmap_id == roadmap_id)
            .order_by(desc(StructureValidationRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        获取路线图的最新验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新验证记录或None
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.roadmap_id == roadmap_id)
            .order_by(desc(StructureValidationRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_latest_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        根据任务ID获取最新验证记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            最新验证记录或None
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(desc(StructureValidationRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[StructureValidationRecord]:
        """
        根据任务ID获取所有验证记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            验证记录列表（按时间倒序）
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(desc(StructureValidationRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


# 单例模式
_validation_crud_instance: Optional[ValidationCRUD] = None


def get_validation_crud() -> ValidationCRUD:
    """获取ValidationCRUD单例"""
    global _validation_crud_instance
    if _validation_crud_instance is None:
        _validation_crud_instance = ValidationCRUD(StructureValidationRecord)
    return _validation_crud_instance


class EditCRUD(BaseCRUD[RoadmapEditRecord, dict, dict]):
    """
    编辑记录CRUD
    
    职责：
    - 路线图编辑记录的增删改查
    - 根据路线图ID/任务ID查询编辑历史
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
        limit: int = 50,
    ) -> List[RoadmapEditRecord]:
        """
        根据路线图ID获取编辑历史
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            limit: 返回记录数限制
            
        Returns:
            编辑记录列表（按时间倒序）
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapEditRecord]:
        """
        获取路线图的最新编辑记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新编辑记录或None
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_latest_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[RoadmapEditRecord]:
        """
        根据任务ID获取最新编辑记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            最新编辑记录或None
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[RoadmapEditRecord]:
        """
        根据任务ID获取所有编辑记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            编辑记录列表（按时间倒序）
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(desc(RoadmapEditRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


# 单例模式
_edit_crud_instance: Optional[EditCRUD] = None


def get_edit_crud() -> EditCRUD:
    """获取EditCRUD单例"""
    global _edit_crud_instance
    if _edit_crud_instance is None:
        _edit_crud_instance = EditCRUD(RoadmapEditRecord)
    return _edit_crud_instance


class EditPlanCRUD(BaseCRUD[EditPlanRecord, dict, dict]):
    """
    编辑计划CRUD
    
    职责：
    - 编辑计划记录的增删改查
    - 根据路线图ID查询编辑计划
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[EditPlanRecord]:
        """
        根据路线图ID获取编辑计划
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            编辑计划列表（按时间倒序）
        """
        stmt = (
            select(EditPlanRecord)
            .where(EditPlanRecord.roadmap_id == roadmap_id)
            .order_by(desc(EditPlanRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[EditPlanRecord]:
        """
        获取路线图的最新编辑计划
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新编辑计划或None
        """
        stmt = (
            select(EditPlanRecord)
            .where(EditPlanRecord.roadmap_id == roadmap_id)
            .order_by(desc(EditPlanRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_plan(
        self,
        session: AsyncSession,
        task_id: str,
        roadmap_id: str,
        feedback_id: str,
        edit_plan: "EditPlan",
        confidence: Optional[str] = None,
        needs_clarification: bool = False,
        clarification_questions: Optional[List[str]] = None,
    ) -> EditPlanRecord:
        """
        创建修改计划记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            roadmap_id: 路线图ID
            feedback_id: 关联的用户反馈记录ID
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
        
        session.add(plan_record)
        await session.flush()
        
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


# 单例模式
_edit_plan_crud_instance: Optional[EditPlanCRUD] = None


def get_edit_plan_crud() -> EditPlanCRUD:
    """获取EditPlanCRUD单例"""
    global _edit_plan_crud_instance
    if _edit_plan_crud_instance is None:
        _edit_plan_crud_instance = EditPlanCRUD(EditPlanRecord)
    return _edit_plan_crud_instance


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

