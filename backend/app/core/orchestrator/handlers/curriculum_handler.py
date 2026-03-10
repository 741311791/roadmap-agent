"""
课程设计Handler

处理CurriculumDesignNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_roadmap import get_roadmap_crud
from app.schemas.handler_io import CurriculumDesignHandlerInput

logger = structlog.get_logger()


class CurriculumDesignHandler(NodeOutputHandler[CurriculumDesignHandlerInput]):
    """
    课程设计Handler
    
    职责：
    1. 保存RoadmapFramework到数据库
    注意：不更新 task 的 current_step/status，由 SideEffectCoordinator 统一管理
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
        
        logger.info(
            "curriculum_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        # 注意：不在此处更新 task 的 current_step / status。
        # 原因：human_review 节点会在 interrupt() 前先写入 human_review_pending 状态（早于本 Handler 执行）。
        # 若此处再写 curriculum_design，会覆盖已正确设置的 human_review_pending，
        # 导致 WS 通知携带错误步骤，前端显示错乱。
        # current_step 的持久化由 SideEffectCoordinator 统一管理。

