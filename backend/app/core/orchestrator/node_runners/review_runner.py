"""
人工审核节点执行器

负责执行人工审核节点（Human Review）
"""
import time
import structlog
from langgraph.types import interrupt

from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger, LogCategory
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.session import AsyncSessionLocal
from ..base import RoadmapState
from ..state_manager import StateManager

logger = structlog.get_logger()


class ReviewRunner:
    """
    人工审核节点执行器
    
    职责：
    1. 标记任务状态为 "human_review_pending"
    2. 使用 interrupt() 暂停工作流
    3. 发布进度通知
    4. 记录执行日志
    5. 恢复时处理审核结果
    """
    
    def __init__(
        self,
        state_manager: StateManager,
    ):
        """
        Args:
            state_manager: StateManager 实例
        """
        self.state_manager = state_manager
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行人工审核节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "human_review")
        
        logger.info(
            "workflow_step_started",
            step="human_review",
            task_id=task_id,
            roadmap_id=state.get("roadmap_id"),
        )
        
        # 获取 roadmap_id
        roadmap_id = state.get("roadmap_id")
        
        # 记录执行日志（包含 roadmap_id）
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="human_review",
            message="等待人工审核",
            roadmap_id=roadmap_id,
        )
        
        # 更新任务状态为 "human_review_pending"
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="human_review_pending",
                current_step="human_review",
                roadmap_id=roadmap_id,
            )
            await session.commit()
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="human_review",
            status="human_review_pending",
            message="路线图已生成，等待您的审核",
            extra_data={
                "roadmap_id": state.get("roadmap_id"),
            },
        )
        
        logger.info(
            "workflow_paused_for_human_review",
            task_id=task_id,
            roadmap_id=state.get("roadmap_id"),
        )
        
        # 使用 interrupt() 暂停工作流，等待人工审核
        # resume_value 将在 resume_after_human_review() 中传入
        resume_value = interrupt({"pause_reason": "human_review_required"})
        
        # 恢复后继续执行
        approved = resume_value.get("approved", False)
        feedback = resume_value.get("feedback", "")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "workflow_resumed_after_human_review",
            task_id=task_id,
            approved=approved,
            has_feedback=bool(feedback),
        )
        
        # 记录执行日志
        await execution_logger.log_workflow_complete(
            task_id=task_id,
            step="human_review",
            message=f"人工审核完成 - {'批准' if approved else '拒绝'}",
            duration_ms=duration_ms,
            roadmap_id=state.get("roadmap_id"),
            details={
                "approved": approved,
                "feedback": feedback[:200] if feedback else None,
            },
        )
        
        # 更新任务状态为 "processing"
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="human_review_completed",
            )
            await session.commit()
        
        # 发布步骤完成通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="human_review",
            status="completed",
            message=f"人工审核完成 - {'批准' if approved else '拒绝'}",
            extra_data={
                "approved": approved,
            },
        )
        
        # 返回状态更新
        return {
            "human_approved": approved,
            "current_step": "human_review",
            "execution_history": [f"人工审核完成 - {'批准' if approved else '拒绝'}"],
        }

