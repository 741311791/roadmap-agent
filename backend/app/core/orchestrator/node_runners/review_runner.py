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
- 保存用户审核反馈到数据库（HumanReviewFeedback 表）
"""
import structlog
from langgraph.types import interrupt

from app.services.execution_logger import execution_logger, LogCategory
from app.db.session import AsyncSessionLocal
from app.db.repositories.review_feedback_repo import ReviewFeedbackRepository
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
    
    async def _check_if_resumed(self, task_id: str) -> bool:
        """
        检查是否是从 interrupt 恢复的执行
        
        通过检查数据库中的任务状态来判断：
        - 如果状态是 human_review_pending，说明之前已经执行过暂停前的逻辑
        - 恢复时，工作流从头执行节点，但任务状态仍然是 human_review_pending
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否是恢复执行
        """
        from app.db.session import AsyncSessionLocal
        from app.db.repositories.roadmap_repo import RoadmapRepository
        
        try:
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                # 修复：使用正确的方法名 get_task 而不是 get_task_by_id
                task = await repo.get_task(task_id)
                
                if task and task.status == "human_review_pending":
                    logger.debug(
                        "review_runner_detected_resume",
                        task_id=task_id,
                        current_status=task.status,
                    )
                    return True
                return False
        except Exception as e:
            logger.warning(
                "review_runner_check_resumed_failed",
                task_id=task_id,
                error=str(e),
            )
            return False
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行人工审核节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 检查是否已处于 human_review_pending 状态（表示是从 interrupt 恢复）
        2. 首次执行：记录等待日志，调用 interrupt() 暂停
        3. 恢复执行：interrupt() 返回 resume_value，处理审核结果
        
        注意：LangGraph 恢复 interrupt 时会重新执行整个节点函数，
        但 interrupt() 会立即返回 resume_value 而不是再次暂停。
        使用任务状态来判断是首次执行还是恢复执行。
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        task_id = state["task_id"]
        roadmap_id = state.get("roadmap_id")
        
        # ========================================
        # 检查是否是从 interrupt 恢复的执行
        # ========================================
        # 方法：检查任务状态。如果已经是 human_review_pending，说明之前已经执行过暂停前的逻辑
        # 恢复时，任务状态仍然是 human_review_pending，直到审核完成后更新
        is_resumed = await self._check_if_resumed(task_id)
        
        # 使用 WorkflowBrain 统一管理执行生命周期
        # 注意：如果是恢复执行，跳过 node_execution 的 _before_node 逻辑
        async with self.brain.node_execution("human_review", state, skip_before=is_resumed):
            # ========================================
            # 第一次执行（暂停前）：只在首次进入时执行
            # ========================================
            if not is_resumed:
                # 获取路线图框架信息（用于前端展示和 WebSocket 通知）
                framework = state.get("roadmap_framework")
                total_concepts = 0
                total_stages = 0
                roadmap_title = "Untitled Roadmap"
                if framework:
                    total_concepts = sum(
                        len(module.concepts)
                        for stage in framework.stages
                        for module in stage.modules
                    )
                    total_stages = len(framework.stages)
                    roadmap_title = framework.title
                
                # 特殊处理：将状态更新为 "human_review_pending"
                # 同时发送 human_review_required WebSocket 事件通知前端
                await self.brain.update_task_to_pending_review(
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    roadmap_title=roadmap_title,
                    stages_count=total_stages,
                )
                
                logger.info(
                    "review_runner_pausing_for_human_review",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
                
                # 记录等待审核日志（用于前端展示）
                await execution_logger.info(
                    task_id=task_id,
                    category=LogCategory.WORKFLOW,
                    step="human_review",
                    roadmap_id=roadmap_id,
                    message="⏸️ Roadmap ready for review, awaiting your confirmation",
                    details={
                        "log_type": "review_waiting",
                        "roadmap_title": roadmap_title,
                        "roadmap_url": f"/roadmap/{roadmap_id}",
                        "summary": {
                            "total_concepts": total_concepts,
                            "total_stages": total_stages,
                            "total_hours": framework.total_estimated_hours if framework else 0,
                            "estimated_weeks": framework.recommended_completion_weeks if framework else 0,
                        },
                    },
                )
            else:
                logger.info(
                    "review_runner_resumed_from_interrupt",
                    task_id=task_id,
                    message="从 interrupt 恢复执行，跳过暂停前的逻辑",
                )
            
            # 使用 interrupt() 暂停工作流，等待人工审核
            # - 第一次执行：interrupt() 抛出 Interrupt 异常，工作流暂停
            # - 恢复执行：interrupt() 返回 resume_value
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
            
            # ========================================
            # 保存用户审核反馈到数据库
            # ========================================
            try:
                async with AsyncSessionLocal() as session:
                    feedback_repo = ReviewFeedbackRepository(session)
                    
                    # 计算当前审核轮次
                    review_count = await feedback_repo.count_by_task(task_id)
                    current_round = review_count + 1
                    
                    # 获取路线图框架快照
                    framework = state.get("roadmap_framework")
                    roadmap_snapshot = framework.model_dump() if framework else {}
                    
                    # 获取用户 ID（从 state 中提取）
                    user_id = state.get("user_request", {}).user_id if hasattr(state.get("user_request"), "user_id") else state["task_id"]
                    
                    # 创建审核反馈记录
                    feedback_record = await feedback_repo.create_feedback(
                        task_id=task_id,
                        roadmap_id=roadmap_id,
                        user_id=user_id,
                        approved=approved,
                        feedback_text=feedback if feedback else None,
                        roadmap_version_snapshot=roadmap_snapshot,
                        review_round=current_round,
                    )
                    
                    # 关键修复：提交事务以确保记录真正保存到数据库
                    await session.commit()
                    
                    logger.info(
                        "review_feedback_saved_to_db",
                        task_id=task_id,
                        feedback_id=feedback_record.id,
                        review_round=current_round,
                        approved=approved,
                    )
            except Exception as e:
                logger.error(
                    "failed_to_save_review_feedback",
                    task_id=task_id,
                    error=str(e),
                )
                # 不阻塞工作流执行，仅记录错误
            
            # 记录审核结果日志（用于前端展示）
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
            # 关键修复：将用户反馈传递到状态中，供后续 EditPlanAnalyzer 和 RoadmapEditor 使用
            # 同时传递 feedback_id 用于关联 EditPlanRecord
            # 同时添加 edit_source 标记（用于路由判断和前端分支显示）
            state_update = {
                "human_approved": approved,
                "user_feedback": feedback if not approved and feedback else None,  # 仅当拒绝且有反馈时保存
                "current_step": "human_review",
                "execution_history": [f"人工审核完成 - {'批准' if approved else '拒绝'}"],
            }
            
            # 当用户拒绝时，添加 edit_source 标记
            if not approved:
                state_update["edit_source"] = "human_review"
            
            # 如果成功保存了反馈记录，将 feedback_id 添加到状态中
            try:
                if 'feedback_record' in locals():
                    state_update["review_feedback_id"] = feedback_record.id
            except:
                pass
            
            return state_update
