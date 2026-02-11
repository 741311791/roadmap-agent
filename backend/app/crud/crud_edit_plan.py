"""
编辑计划CRUD操作

提供路线图编辑计划记录的数据库操作。
"""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import EditPlanRecord

if TYPE_CHECKING:
    from app.models.domain import EditPlan

logger = structlog.get_logger()


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
        edit_plan: "EditPlan",
        feedback_id: Optional[str] = None,
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
            edit_plan: 修改计划对象
            feedback_id: 关联的用户反馈记录ID（可选，验证失败触发时为None）
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

