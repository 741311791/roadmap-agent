"""
极速模式自动内容生成节点（纯函数）

职责：
- 极速模式下，路线图框架生成完成后直接触发内容生成，跳过人工审查
- 提供可复用的 trigger_content_generation helper，供 human_review_node 共用
- 集中管理 Redis 缓存写入逻辑（_cache_content_generation_data）
"""
import asyncio
from datetime import datetime

import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.models.constants import WorkflowStep

logger = structlog.get_logger()


async def _cache_content_generation_data(
    task_id: str,
    roadmap_id: str,
    state: RoadmapState,
) -> None:
    """
    缓存内容生成所需的数据到 Redis（性能优化）

    Celery 内容生成任务会优先从此缓存读取，
    若缓存缺失则自动 Fallback 到数据库查询。

    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        state: 主工作流的完整状态
    """
    from app.config.settings import settings
    from app.db.redis_client import redis_client

    if not settings.CONTENT_GEN_CACHE_ENABLED:
        logger.info(
            "content_gen_cache_disabled",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        return

    try:
        framework = state.get("roadmap_framework")
        intent_analysis = state.get("intent_analysis")
        user_request = state.get("user_request")

        if not framework:
            raise ValueError("framework 不存在，无法缓存")

        # 预提取 Concepts（扁平化列表）
        concepts = [
            concept
            for stage in framework.stages
            for module in stage.modules
            for concept in module.concepts
        ]

        user_constraints = {}
        if intent_analysis and intent_analysis.full_analysis_data:
            user_constraints = intent_analysis.full_analysis_data

        cache_data = {
            "roadmap_id": roadmap_id,
            "task_id": task_id,
            "user_id": user_request.user_id if user_request else None,
            "framework": framework.model_dump(),
            "concepts": [c.model_dump() for c in concepts],
            "user_constraints": user_constraints,
            "user_request": user_request.model_dump() if user_request else {},
            "cached_at": datetime.utcnow().isoformat(),
            "version": "v1",
        }

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
        # 不抛出异常，Celery 任务会 Fallback 到数据库查询
        logger.warning(
            "content_gen_cache_write_failed_task_will_fallback",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
        )


async def trigger_content_generation(
    task_id: str,
    roadmap_id: str,
    user_id: str | None,
    state: RoadmapState,
) -> str:
    """
    触发独立的内容生成 Celery 任务（可复用 helper）

    人工审查批准路径和极速模式直通路径共用此函数，
    避免两处各自维护重复的副作用逻辑。

    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        user_id: 用户 ID
        state: 主工作流的完整状态（用于缓存数据）

    Returns:
        Celery 任务 ID

    Raises:
        Exception: 入队失败时抛出，由调用方决定是否记录并继续
    """
    from app.crud.crud_task import get_task_crud
    from app.db.celery_session import get_celery_session
    from app.tasks.content_generation_tasks import generate_all_content_task

    # 步骤1：缓存数据到 Redis（失败不阻断主流程）
    await _cache_content_generation_data(
        task_id=task_id,
        roadmap_id=roadmap_id,
        state=state,
    )

    # 步骤2：触发 Celery 内容生成任务
    # 使用 asyncio.to_thread 避免 .apply_async() 阻塞事件循环
    celery_result = await asyncio.to_thread(
        generate_all_content_task.apply_async,
        kwargs={
            "roadmap_id": roadmap_id,
            "task_id": task_id,
            "user_id": user_id,
        },
    )

    # 步骤3：回写 Celery 任务 ID 到数据库
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

    return celery_result.id


async def auto_content_generation_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    极速模式自动内容生成节点（纯函数）

    极速模式下，路线图框架生成完毕后直接触发内容生成，
    不经过人工审查，主工作流随即结束。

    Args:
        state: 工作流状态
        config: 运行时配置

    Returns:
        状态更新字典：
        - current_step: content_generation_queued
        - human_approved: True（视为自动批准，保持状态字段一致）
        - roadmap_id: 路线图 ID
    """
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    user_request = state.get("user_request")
    user_id = user_request.user_id if user_request else None

    logger.info(
        "auto_content_generation_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        message="极速模式：跳过人工审查，直接触发内容生成",
    )

    if not roadmap_id:
        logger.error(
            "auto_content_generation_missing_roadmap_id",
            task_id=task_id,
        )
        return {
            "current_step": WorkflowStep.CONTENT_GENERATION_QUEUED.value,
            "human_approved": True,
            "execution_history": ["极速模式：内容生成入队失败（roadmap_id 缺失）"],
        }

    try:
        await trigger_content_generation(
            task_id=task_id,
            roadmap_id=roadmap_id,
            user_id=user_id,
            state=state,
        )
    except Exception as e:
        logger.error(
            "auto_content_generation_trigger_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
            exc_info=True,
        )

    return {
        "current_step": WorkflowStep.CONTENT_GENERATION_QUEUED.value,
        "human_approved": True,
        "roadmap_id": roadmap_id,
        "execution_history": ["极速模式：跳过人工审查，内容生成已入队"],
    }
