"""
验证结果修改计划分析Handler（验证失败触发）

处理ValidationEditPlanNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_edit_plan import get_edit_plan_crud

logger = structlog.get_logger()


class ValidationEditPlanHandler(NodeOutputHandler):
    """
    验证结果修改计划分析Handler（验证失败触发）
    
    职责：
    1. 保存基于验证结果生成的修改计划
    """
    
    def get_node_name(self) -> str:
        return "validation_edit_plan_analysis"
    
    async def _handle_output(
        self,
        output: dict,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理验证结果修改计划分析输出（具体实现）
        
        Args:
            output: 包含 edit_plan, validation_result, roadmap_id
            task_id: 任务ID
            session: 数据库会话
        """
        edit_plan = output.get("edit_plan")
        validation_result = output.get("validation_result")
        roadmap_id = output.get("roadmap_id")
        
        if not edit_plan:
            logger.warning(
                "validation_edit_plan_handler_missing_data",
                task_id=task_id,
                has_edit_plan=edit_plan is not None,
            )
            return
        
        logger.info(
            "validation_edit_plan_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
            has_validation_result=bool(validation_result),
        )
        
        # 构造基于验证结果的反馈摘要
        feedback_summary = "Based on validation results:"
        if validation_result:
            feedback_summary += f" overall_score={validation_result.overall_score}"
            if validation_result.issues:
                feedback_summary += f", {len(validation_result.issues)} issues found"
        
        # 保存修改计划记录（验证失败触发，无 feedback_id）
        edit_plan_crud = get_edit_plan_crud()
        await edit_plan_crud.create_plan(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_plan=edit_plan,
            feedback_id=None,  # 验证失败触发，无用户反馈
        )
        
        logger.info(
            "validation_edit_plan_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )

