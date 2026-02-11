"""
意图分析Handler

处理IntentAnalysisNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_intent_analysis import get_intent_analysis_crud
from app.crud.crud_task import get_task_crud
from app.core.orchestrator.base import ensure_unique_roadmap_id
from app.crud.crud_roadmap import get_roadmap_crud
from app.schemas.handler_io import IntentAnalysisHandlerInput

logger = structlog.get_logger()


class IntentAnalysisHandler(NodeOutputHandler[IntentAnalysisHandlerInput]):
    """
    意图分析Handler
    
    职责：
    1. 保存IntentAnalysisOutput到数据库
    2. 更新task状态和roadmap_id
    """
    
    input_model_class = IntentAnalysisHandlerInput
    
    def get_node_name(self) -> str:
        return "intent_analysis"
    
    async def _handle_output(
        self,
        output: IntentAnalysisHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理意图分析输出（具体实现）
        
        Args:
            output: 意图分析 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        intent_analysis = output.intent_analysis
        roadmap_id = output.roadmap_id
        
        logger.info(
            "intent_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 确保 roadmap_id 唯一性
        roadmap_crud = get_roadmap_crud()
        unique_roadmap_id = await ensure_unique_roadmap_id(
            roadmap_id,
            roadmap_crud,
            session,
        )
        
        # 更新task状态和roadmap_id（先更新，以便Intent Analysis可以使用）
        task_crud = get_task_crud()
        await task_crud.update_task_status(
            session=session,
            task_id=task_id,
            status="processing",
            current_step="intent_analysis",
            roadmap_id=unique_roadmap_id,
        )
        
        # 保存Intent Analysis元数据（使用unique_roadmap_id）
        intent_crud = get_intent_analysis_crud()
        await intent_crud.save_intent_analysis(
            session,
            unique_roadmap_id,
            intent_analysis,
        )
        
        logger.info(
            "intent_handler_saved",
            task_id=task_id,
            roadmap_id=unique_roadmap_id,
        )

