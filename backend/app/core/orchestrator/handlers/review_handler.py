"""
人工审核Handler

处理ReviewNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_task import get_task_crud
from app.schemas.handler_io import ReviewHandlerInput

logger = structlog.get_logger()


class ReviewHandler(NodeOutputHandler[ReviewHandlerInput]):
    """
    人工审核Handler
    
    职责：
    1. 更新task状态为human_review_pending或processing
    2. 发送人工审核通知
    
    注意：
    - ReviewNode使用interrupt()机制暂停工作流
    - Handler在interrupt前后都会被调用
    """
    
    input_model_class = ReviewHandlerInput
    
    def get_node_name(self) -> str:
        return "human_review"
    
    async def _handle_output(
        self,
        output: ReviewHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理人工审核输出（具体实现）
        
        Args:
            output: 人工审核 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        human_approved = output.human_approved
        roadmap_id = output.roadmap_id
        
        logger.info(
            "review_handler_processing",
            task_id=task_id,
            roadmap_id=roadmap_id,
            human_approved=human_approved,
        )
        
        if human_approved:
            # 审核通过，更新为content_generation_queued状态
            task_crud = get_task_crud()
            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status="processing",
                current_step="content_generation_queued",  # ✅ 修复：使用正确的WorkflowStep枚举值
            )
            
            logger.info(
                "review_handler_approved",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        else:
            # 等待人工审核或被拒绝
            # 状态更新由ReviewHandler.on_start()处理（每次进入human_review节点时）
            logger.info(
                "review_handler_pending",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
    
    async def on_start(
        self,
        task_id: str,
        state: dict,
        session: AsyncSession,
    ) -> None:
        """
        人工审核节点开始前的处理
        
        发送human_review_required通知
        """
        roadmap_id = state.get("roadmap_id")
        framework = state.get("roadmap_framework")
        
        # 提取路线图信息
        roadmap_title = "Untitled Roadmap"
        stages_count = 0
        if framework:
            roadmap_title = framework.title if hasattr(framework, "title") else roadmap_title
            stages_count = len(framework.stages) if hasattr(framework, "stages") else 0
        
        logger.info(
            "review_handler_on_start",
            task_id=task_id,
            roadmap_id=roadmap_id,
            roadmap_title=roadmap_title,
            stages_count=stages_count,
        )
        
        # 更新task状态为human_review_pending
        task_crud = get_task_crud()
        await task_crud.update_task_status(
            session=session,
            task_id=task_id,
            status="human_review_pending",
            current_step="human_review",
            roadmap_id=roadmap_id,
        )
        
        # 发送human_review_required通知
        await self.notification_service.publish_human_review_required(
            task_id=task_id,
            roadmap_id=roadmap_id or "",
            roadmap_title=roadmap_title,
            stages_count=stages_count,
        )
        
        return None

