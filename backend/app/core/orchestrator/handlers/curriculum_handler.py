"""
课程设计Handler

处理CurriculumDesignNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_task import get_task_crud
from app.schemas.handler_io import CurriculumDesignHandlerInput

logger = structlog.get_logger()


class CurriculumDesignHandler(NodeOutputHandler[CurriculumDesignHandlerInput]):
    """
    课程设计Handler
    
    职责：
    1. 保存RoadmapFramework到数据库
    2. 更新task状态
    """
    
    input_model_class = CurriculumDesignHandlerInput
    
    def get_node_name(self) -> str:
        return "curriculum_design"
    
    async def _handle_output(
        self,
        output: CurriculumDesignHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理课程设计输出（具体实现）
        
        Args:
            output: 课程设计 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        framework = output.roadmap_framework
        roadmap_id = output.roadmap_id
        user_id = output.user_id
        
        logger.info(
            "curriculum_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
            stages_count=len(framework.stages),
        )
        
        # 保存路线图框架
        roadmap_crud = get_roadmap_crud()
        await roadmap_crud.save_roadmap_metadata(
            session,
            roadmap_id,
            user_id,
            framework,
        )
        
        # 更新task状态
        task_crud = get_task_crud()
        await task_crud.update_task_status(
            session=session,
            task_id=task_id,
            status="processing",
            current_step="curriculum_design",
        )
        
        logger.info(
            "curriculum_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )

