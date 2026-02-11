"""
修改计划分析Handler（人工审核触发）

处理EditPlanNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_edit_plan import get_edit_plan_crud
from app.crud.crud_review_feedback import get_review_feedback_crud
from app.schemas.handler_io import EditPlanHandlerInput

logger = structlog.get_logger()


class EditPlanHandler(NodeOutputHandler[EditPlanHandlerInput]):
    """
    修改计划分析Handler（人工审核触发）
    
    职责：
    1. 保存用户反馈和解析后的修改计划
    """
    
    input_model_class = EditPlanHandlerInput
    
    def get_node_name(self) -> str:
        return "edit_plan_analysis"
    
    async def _handle_output(
        self,
        output: EditPlanHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理修改计划分析输出（具体实现）
        
        流程：
        1. 先保存用户反馈到 human_review_feedbacks 表
        2. 获取 feedback_id
        3. 保存修改计划到 edit_plan_records 表，并关联 feedback_id
        
        Args:
            output: 修改计划分析 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        edit_plan_output = output.edit_plan  # EditPlanAnalyzerOutput
        edit_plan = edit_plan_output.edit_plan  # EditPlan（实际的修改计划）
        user_feedback = output.user_feedback
        roadmap_id = output.roadmap_id
        user_id = output.user_id
        approved = output.approved  # 始终为 False（用户拒绝）
        roadmap_version_snapshot = output.roadmap_version_snapshot
        review_round = output.review_round
        
        logger.info(
            "edit_plan_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
            user_id=user_id,
            has_user_feedback=bool(user_feedback),
            confidence=edit_plan_output.confidence,
            review_round=review_round,
        )
        
        # 步骤1: 保存用户反馈到 human_review_feedbacks 表
        review_feedback_crud = get_review_feedback_crud()
        feedback_record = await review_feedback_crud.create_feedback(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
            user_id=user_id,
            approved=approved,
            feedback_text=user_feedback,
            roadmap_version_snapshot=roadmap_version_snapshot,
            review_round=review_round,
        )
        
        logger.info(
            "edit_plan_handler_feedback_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
            feedback_id=feedback_record.id,
            review_round=review_round,
        )
        
        # 步骤2: 保存修改计划到 edit_plan_records 表（关联 feedback_id）
        edit_plan_crud = get_edit_plan_crud()
        await edit_plan_crud.create_plan(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_plan=edit_plan,  # ✅ 传入 EditPlan 对象
            feedback_id=feedback_record.id,  # ✅ 关联用户反馈记录
            confidence=str(edit_plan_output.confidence),  # ✅ 保存置信度
            needs_clarification=edit_plan_output.needs_clarification,
            clarification_questions=edit_plan_output.clarification_questions,
        )
        
        logger.info(
            "edit_plan_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
            feedback_id=feedback_record.id,
        )

