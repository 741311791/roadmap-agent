"""
验证Handler

处理ValidationNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_validation import get_validation_crud
from app.schemas.handler_io import ValidationHandlerInput

logger = structlog.get_logger()


class ValidationHandler(NodeOutputHandler[ValidationHandlerInput]):
    """
    验证Handler
    
    职责：
    1. 保存ValidationOutput到数据库
    """
    
    input_model_class = ValidationHandlerInput
    
    def get_node_name(self) -> str:
        return "structure_validation"
    
    async def _handle_output(
        self,
        output: ValidationHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理验证输出（具体实现）
        
        Args:
            output: 验证 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        validation_result = output.validation_result
        roadmap_id = output.roadmap_id
        validation_round = output.validation_round
        
        logger.info(
            "validation_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
            validation_round=validation_round,
            is_valid=validation_result.is_valid,
        )
        
        # 统计问题数量
        critical_count = len([
            i for i in validation_result.issues
            if i.severity == "critical"
        ])
        warning_count = len([
            i for i in validation_result.issues
            if i.severity == "warning"
        ])
        suggestion_count = len(validation_result.improvement_suggestions)
        
        # 保存验证结果
        validation_crud = get_validation_crud()
        await validation_crud.create_validation_record(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
            is_valid=validation_result.is_valid,
            overall_score=validation_result.overall_score,
            issues=[i.model_dump() for i in validation_result.issues],
            dimension_scores=[
                s.model_dump() for s in validation_result.dimension_scores
            ],
            improvement_suggestions=[
                s.model_dump() for s in validation_result.improvement_suggestions
            ],
            validation_summary=validation_result.validation_summary,
            validation_round=validation_round,
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )
        
        logger.info(
            "validation_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
            validation_round=validation_round,
            critical_count=critical_count,
            warning_count=warning_count,
        )

