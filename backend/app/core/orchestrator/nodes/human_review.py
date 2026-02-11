"""
人工审核节点（纯函数）

职责：
- 使用interrupt()暂停工作流，等待人工审核
- 返回审核结果
"""
import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.core.orchestrator.base import RoadmapState

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
    
    logger.info(
        "human_review_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
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
    user_id = state.get("user_request", {}).get("user_id")
    
    logger.info(
        "human_review_node_resumed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        approved=approved,
        has_feedback=bool(feedback),
    )
    
    # ✅ 如果用户批准，触发独立的内容生成 Celery 任务
    if approved and roadmap_id:
        try:
            from app.tasks.content_generation_tasks import generate_all_content_task
            from app.db.celery_session import get_celery_session
            from app.crud.crud_task import get_task_crud
            
            # 触发内容生成任务
            celery_result = generate_all_content_task.delay(
                roadmap_id=roadmap_id,
                task_id=task_id,
                user_id=user_id,
            )
            
            # 保存 Celery 任务 ID 到数据库
            async with get_celery_session() as session:
                task_crud = get_task_crud()
                await task_crud.update_content_generation_celery_id(
                    session=session,
                    task_id=task_id,
                    celery_id=celery_result.id,
                )
            
            logger.info(
                "content_generation_task_triggered",
                task_id=task_id,
                roadmap_id=roadmap_id,
                content_celery_id=celery_result.id,
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
        "current_step": "human_review",
        "execution_history": [
            f"人工审核完成: {'批准' if approved else '拒绝'}"
        ],
    }

