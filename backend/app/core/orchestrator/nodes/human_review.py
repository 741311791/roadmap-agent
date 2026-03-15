"""
人工审核节点（纯函数）

职责：
- 使用interrupt()暂停工作流，等待人工审核
- 批准时调用共享 helper 触发内容生成
- 返回审核结果
"""
import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.core.orchestrator.base import RoadmapState
from app.models.constants import WorkflowStep
from .auto_content_generation import trigger_content_generation

logger = structlog.get_logger()


async def human_review_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    人工审核节点（纯函数）
    
    使用LangGraph的interrupt() API暂停工作流。
    当用户通过API发送审核决策时，工作流会自动恢复。
    
    Args:
        state: 工作流状态
        config: 运行时配置
    
    Returns:
        状态更新字典：
        - human_approved: 是否批准
        - user_feedback: 用户反馈（如果拒绝）
        - current_step: 当前步骤
    """
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    
    # is_resume=True 代表这是 resume_after_human_review 触发的恢复执行。
    # 在恢复场景中节点函数会被重新执行，但 interrupt() 会立刻返回 resume value，
    # 此时写 human_review_pending 完全无意义（下一个节点立即接管），跳过以节省 ~500ms。
    is_resume = config.get("configurable", {}).get("is_resume", False)
    
    logger.info(
        "human_review_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        is_resume=is_resume,
    )
    
    if not is_resume:
        # 首次进入节点时写入 pending 状态，让前端/DB 感知工作流已暂停等待审核
        from app.db.celery_session import get_celery_session
        from app.crud.crud_task import get_task_crud
        
        try:
            async with get_celery_session() as session:
                task_crud = get_task_crud()
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status="human_review_pending",
                    current_step="human_review",
                    roadmap_id=roadmap_id,
                )
            logger.info(
                "human_review_status_updated",
                task_id=task_id,
                roadmap_id=roadmap_id,
                status="human_review_pending",
            )
        except Exception as e:
            logger.error(
                "human_review_status_update_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
    
    # 使用interrupt()暂停工作流，等待人工审核
    # resume_value将由WorkflowExecutor.resume_after_human_review()提供
    resume_value = interrupt(
        {
            "type": "human_review_required",
            "task_id": task_id,
            "roadmap_id": roadmap_id,
            "message": "等待人工审核...",
        }
    )
    
    # resume_value结构：{"approved": bool, "feedback": str}
    approved = resume_value.get("approved", False)
    feedback = resume_value.get("feedback", "")
    # ✅ 修复：UserRequest 是 Pydantic 对象，不是字典
    user_request = state.get("user_request")
    user_id = user_request.user_id if user_request else None
    
    logger.info(
        "human_review_node_resumed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        approved=approved,
        has_feedback=bool(feedback),
    )
    
    # 如果用户批准，触发独立的内容生成 Celery 任务
    if approved and roadmap_id:
        try:
            await trigger_content_generation(
                task_id=task_id,
                roadmap_id=roadmap_id,
                user_id=user_id,
                state=state,
            )
        except Exception as e:
            logger.error(
                "failed_to_trigger_content_generation",
                task_id=task_id,
                roadmap_id=roadmap_id,
                error=str(e),
                exc_info=True,
            )
    
    # 返回审核结果
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "human_approved": approved,
        "user_feedback": feedback if not approved else None,
        "roadmap_id": roadmap_id,  # ✅ Handler 需要
        # ✅ 批准时：主工作流结束，内容生成已入队（独立 Celery 任务）
        # ❌ 拒绝时：保持 human_review（等待下次审核）
        "current_step": (
            WorkflowStep.CONTENT_GENERATION_QUEUED.value 
            if approved 
            else WorkflowStep.HUMAN_REVIEW.value
        ),
        # ✅ 修复：拒绝时显式设置 edit_source 为 "human_review"，覆盖 state 中可能存在的旧值（如 "validation_failed"）
        # 这确保后续的 edit_plan_analysis 和 route_after_edit 能正确识别编辑来源
        "edit_source": "human_review" if not approved else state.get("edit_source"),
        "execution_history": [
            f"人工审核完成: {'批准' if approved else '拒绝'}"
        ],
    }

