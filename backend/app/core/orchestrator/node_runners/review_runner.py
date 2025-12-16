"""
人工审核节点执行器（重构版 - 使用 WorkflowBrain）

负责执行人工审核节点（Human Review）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 保留 interrupt() 逻辑（LangGraph 核心功能）
- 删除直接的数据库操作
- 代码行数减少 ~70%

特殊处理:
- 审核前将状态更新为 "human_review_pending"
- 审核后恢复为 "processing"
"""
import structlog
from langgraph.types import interrupt

from app.services.execution_logger import execution_logger, LogCategory
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ReviewRunner:
    """
    人工审核节点执行器（重构版）
    
    职责：
    1. 使用 interrupt() 暂停工作流
    2. 等待人工审核结果
    3. 处理审核反馈
    
    不再负责:
    - 数据库操作（由 WorkflowBrain 处理）
    - 日志记录（由 WorkflowBrain 处理）
    - 通知发布（由 WorkflowBrain 处理）
    - 状态管理（由 WorkflowBrain 处理）
    """
    
    def __init__(
        self,
        brain: WorkflowBrain,
    ):
        """
        Args:
            brain: WorkflowBrain 实例（统一协调者）
        """
        self.brain = brain
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行人工审核节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 使用 brain.update_task_to_pending_review() 更新状态
        3. 使用 interrupt() 暂停工作流
        4. 恢复后处理审核结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("human_review", state):
            # 特殊处理：将状态更新为 "human_review_pending"
            await self.brain.update_task_to_pending_review(
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
            )
            
            logger.info(
                "review_runner_pausing_for_human_review",
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
            )
            
            # 记录等待审核日志（新增 - 用于前端展示）
            framework = state.get("roadmap_framework")
            total_concepts = 0
            total_stages = 0
            if framework:
                total_concepts = sum(
                    len(module.concepts)
                    for stage in framework.stages
                    for module in stage.modules
                )
                total_stages = len(framework.stages)
            
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.WORKFLOW,
                step="human_review",
                roadmap_id=state.get("roadmap_id"),
                message="⏸️ Roadmap ready for review, awaiting your confirmation",
                details={
                    "log_type": "review_waiting",
                    "roadmap_title": framework.title if framework else "Untitled Roadmap",
                    "roadmap_url": f"/roadmap/{state.get('roadmap_id')}",
                    "summary": {
                        "total_concepts": total_concepts,
                        "total_stages": total_stages,
                        "total_hours": framework.total_estimated_hours if framework else 0,
                        "estimated_weeks": framework.recommended_completion_weeks if framework else 0,
                    },
                },
            )
            
            # 使用 interrupt() 暂停工作流，等待人工审核
            # resume_value 将在 resume_after_human_review() 中传入
            resume_value = interrupt({"pause_reason": "human_review_required"})
            
            # 恢复后继续执行
            approved = resume_value.get("approved", False)
            feedback = resume_value.get("feedback", "")
            
            logger.info(
                "review_runner_resumed_after_human_review",
                task_id=state["task_id"],
                approved=approved,
                has_feedback=bool(feedback),
            )
            
            # 记录审核结果日志（新增 - 用于前端展示）
            if approved:
                await execution_logger.info(
                    task_id=state["task_id"],
                    category=LogCategory.WORKFLOW,
                    step="human_review",
                    roadmap_id=state.get("roadmap_id"),
                    message="✅ Roadmap approved by user, proceeding to content generation",
                    details={
                        "log_type": "review_approved",
                        "approved_at": None,  # 时间戳由execution_logger自动添加
                        "user_feedback": feedback if feedback else None,
                    },
                )
            else:
                await execution_logger.info(
                    task_id=state["task_id"],
                    category=LogCategory.WORKFLOW,
                    step="human_review",
                    roadmap_id=state.get("roadmap_id"),
                    message=f"📝 User requested modifications: {feedback[:100]}{'...' if len(feedback) > 100 else ''}",
                    details={
                        "log_type": "review_modification_requested",
                        "user_feedback": feedback,
                        "requested_at": None,  # 时间戳由execution_logger自动添加
                    },
                )
            
            # 特殊处理：恢复后将状态改回 "processing"
            await self.brain.update_task_after_review(
                task_id=state["task_id"],
            )
            
            # 返回纯状态更新
            return {
                "human_approved": approved,
                "current_step": "human_review",
                "execution_history": [f"人工审核完成 - {'批准' if approved else '拒绝'}"],
            }
