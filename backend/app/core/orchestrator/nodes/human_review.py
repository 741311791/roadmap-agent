"""
人工审核节点（纯函数）

职责：
- 使用interrupt()暂停工作流，等待人工审核
- 返回审核结果
"""
import structlog
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.core.orchestrator.base import RoadmapState
from app.models.constants import WorkflowStep

logger = structlog.get_logger()


async def _cache_content_generation_data(
    task_id: str,
    roadmap_id: str,
    state: RoadmapState,
) -> None:
    """
    缓存内容生成所需的数据到 Redis
    
    职责：
    1. 从 state 提取 framework 和 intent_analysis
    2. 预提取 Concepts（扁平化列表）
    3. 提取用户约束（full_analysis_data）
    4. 写入 Redis（TTL: 24小时）
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        state: 主工作流的完整状态
    """
    from app.db.redis_client import redis_client
    from app.config.settings import settings
    
    # 检查是否启用缓存
    if not settings.CONTENT_GEN_CACHE_ENABLED:
        logger.info(
            "content_gen_cache_disabled",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        return
    
    try:
        # 1. 从 state 提取数据
        framework = state.get("roadmap_framework")
        intent_analysis = state.get("intent_analysis")
        user_request = state.get("user_request")
        
        if not framework:
            logger.error(
                "cache_content_gen_data_missing_framework",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
            raise ValueError("framework 不存在，无法缓存")
        
        # 2. 预提取 Concepts（扁平化列表）
        concepts = []
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    concepts.append(concept)
        
        # 3. 提取用户约束
        user_constraints = {}
        if intent_analysis and intent_analysis.full_analysis_data:
            user_constraints = intent_analysis.full_analysis_data
        
        # 4. 构建缓存数据
        cache_data = {
            "roadmap_id": roadmap_id,
            "task_id": task_id,
            "user_id": user_request.user_id if user_request else None,
            
            # 完整的 framework（Pydantic 模型序列化）
            "framework": framework.model_dump(),
            
            # 预提取的 Concepts（扁平化列表）
            "concepts": [c.model_dump() for c in concepts],
            
            # 用户约束（来自 IntentAnalysis）
            "user_constraints": user_constraints,
            
            # ✅ 用户请求（包含 preferences，内容生成需要）
            "user_request": user_request.model_dump() if user_request else {},
            
            # 元数据
            "cached_at": datetime.utcnow().isoformat(),
            "version": "v1",
        }
        
        # 5. 写入 Redis（TTL: 24小时）
        redis_key = f"content_gen_cache:{task_id}"
        await redis_client.set_json(
            key=redis_key,
            value=cache_data,
            ex=settings.CONTENT_GEN_CACHE_TTL,
        )
        
        logger.info(
            "content_gen_data_cached",
            task_id=task_id,
            roadmap_id=roadmap_id,
            redis_key=redis_key,
            total_concepts=len(concepts),
            cache_size_kb=round(len(str(cache_data)) / 1024, 2),
            ttl_hours=settings.CONTENT_GEN_CACHE_TTL / 3600,
        )
        
    except Exception as e:
        # ⚠️ 不抛出异常，只记录警告
        # Celery 任务会 Fallback 到数据库查询
        logger.warning(
            "content_gen_cache_write_failed_task_will_fallback",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
        )


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
    
    # ✅ 每次进入 human_review 节点时，更新任务状态为 human_review_pending
    # 这确保状态在每次循环回到 human_review 时都是正确的
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
    
    # ✅ 如果用户批准，触发独立的内容生成 Celery 任务
    if approved and roadmap_id:
        try:
            from app.tasks.content_generation_tasks import generate_all_content_task
            from app.db.celery_session import get_celery_session
            from app.crud.crud_task import get_task_crud
            
            # ✅ 步骤1：缓存数据到 Redis（性能优化）
            await _cache_content_generation_data(
                task_id=task_id,
                roadmap_id=roadmap_id,
                state=state,
            )
            
            # ✅ 步骤2：触发内容生成任务
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

