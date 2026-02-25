"""
内容生成 Celery 任务

独立的内容生成 Worker，与主工作流（LangGraph）完全分离。

架构优势：
- ✅ 主工作流 checkpoint 不包含内容数据（减少 90% 数据量）
- ✅ 内容生成失败可单独重试，不影响框架
- ✅ 更高并发（独立 worker，可配置更多 concurrency）
- ✅ 更好的监控和告警（独立队列）

队列配置：
- Queue Name: content_generation
- Concurrency: 推荐 20-30（根据 LLM API 限流调整）
- Retry: 最多 3 次
- Timeout: 5 分钟/concept
"""
import structlog
from celery import group, chord
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.db.celery_session import get_celery_session
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_task import get_task_crud
from app.crud.crud_concept import get_concept_crud
from app.agents.factory import AgentFactory
from app.config.settings import settings
from app.models.domain import (
    Concept,
    LearningPreferences,
    RoadmapFramework,
    TutorialGenerationInput,
    ResourceRecommendationInput,
    QuizGenerationInput,
)
from app.models.constants import WorkflowStep
from app.services.shared.notification_service import notification_service
from app.services.shared.execution_logger import execution_logger

logger = structlog.get_logger()


# ============================================================
# 辅助函数
# ============================================================

def _apply_test_mode_truncation(
    framework: "RoadmapFramework",
    concepts: list[Concept],
    task_id: str,
) -> tuple["RoadmapFramework", list[Concept]]:
    """
    应用测试模式截断（统一的截断逻辑）
    
    只保留第一个 Stage 的第一个 Module 的所有 Concepts
    
    Args:
        framework: 原始框架
        concepts: 原始 Concepts 列表
        task_id: 任务 ID
        
    Returns:
        (截断后的 framework, 截断后的 concepts)
    """
    from app.models.domain import RoadmapFramework
    from copy import deepcopy
    
    logger.warning(
        "test_mode_truncate_framework_enabled",
        task_id=task_id,
        original_stages=len(framework.stages),
        original_modules=sum(len(s.modules) for s in framework.stages),
        original_concepts=len(concepts),
    )
    
    # 深拷贝避免修改原始对象
    framework = deepcopy(framework)
    
    # 只保留第一个 Stage 的第一个 Module
    if framework.stages:
        first_stage = framework.stages[0]
        if first_stage.modules:
            first_module = first_stage.modules[0]
            first_stage.modules = [first_module]
        framework.stages = [first_stage]
    
    # 重新提取 Concepts
    truncated_concepts = []
    for stage in framework.stages:
        for module in stage.modules:
            truncated_concepts.extend(module.concepts)
    
    logger.info(
        "test_mode_framework_truncated",
        task_id=task_id,
        truncated_stages=len(framework.stages),
        truncated_modules=sum(len(s.modules) for s in framework.stages),
        truncated_concepts=len(truncated_concepts),
    )
    
    return framework, truncated_concepts


async def _execute_content_generation_subgraph(
    task_id: str,
    roadmap_id: str,
    concepts: list[Concept],
    user_constraints: dict,
    user_request: dict,
) -> Dict[str, Any]:
    """
    执行内容生成子图（LangGraph 无状态模式）
    
    架构：
    - 使用 build_content_generation_subgraph() 构建子图
    - checkpointer=None：无状态模式，避免 psycopg pipeline 连接超时
    - 内容数据已通过 get_celery_session() 独立持久化，不依赖 LangGraph checkpoint
    - LangGraph 自动管理 Fan-Out/Fan-In
    
    为什么不使用 checkpointer：
    - Tavily rate limiter 等待期间（50+秒），psycopg pipeline 连接会超时断开
    - aput_writes 写入 checkpoint 时触发 OperationalError，导致整个任务崩溃
    - 内容生成的实际数据已保存至数据库（concept 表），checkpoint 仅用于断点续传
    - 内容生成失败时用户可单独重试，无需 LangGraph 级别的断点续传
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concepts: Concept 列表（已经过测试模式截断）
        user_constraints: 用户约束（来自 IntentAnalysis.full_analysis_data）
        user_request: 原始用户请求（来自 RoadmapTask.user_request）
        
    Returns:
        执行结果
    """
    from app.core.orchestrator_factory import OrchestratorFactory
    from app.core.orchestrator.runtime_context import RuntimeContext
    from app.core.orchestrator.subgraphs.content_generation import build_content_generation_subgraph
    from app.models.domain import LearningPreferences
    
    logger.info(
        "langgraph_subgraph_execution_starting",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(concepts),
        has_checkpointer=False,
        architecture="stateless_no_checkpoint",
    )
    
    # 1. 创建 RuntimeContext（复用现有依赖）
    context = RuntimeContext(
        agent_factory=OrchestratorFactory.get_agent_factory(),
        notification_service=notification_service,
        execution_logger=execution_logger,
        state_manager=OrchestratorFactory.get_state_manager(),
        child_checkpointer=None,  # 无状态模式，不传入 checkpointer
    )
    
    # 2. 从 user_request 构建 LearningPreferences
    # user_request 格式: {"user_id": "...", "preferences": {...}, "additional_context": "..."}
    preferences_data = user_request.get("preferences", {})
    
    logger.debug(
        "building_learning_preferences",
        task_id=task_id,
        has_preferences=bool(preferences_data),
        preferences_keys=list(preferences_data.keys()) if preferences_data else [],
    )
    
    user_preferences = LearningPreferences(**preferences_data)
    
    # 3. 构建子图（无状态模式，不使用 checkpointer）
    subgraph = build_content_generation_subgraph(checkpointer=None)
    
    # 4. 准备子图输入状态
    sub_state = {
        "roadmap_id": roadmap_id,
        "concepts": concepts,
        "user_preferences": user_preferences,
        "task_id": task_id,
        "concept": None,  # 用于 Send API
        "concept_results": [],  # Reducer 自动累加
    }
    
    # 5. 运行时配置（不含 thread_id，因为无状态模式不需要）
    child_config = {
        "configurable": {
            "runtime_context": context,
        }
    }
    
    logger.info(
        "langgraph_subgraph_invoking",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concepts_count=len(concepts),
        mode="stateless",
    )
    
    # 6. 执行子图（无状态模式，不写入 checkpoint）
    result = await subgraph.ainvoke(sub_state, child_config)
    
    # 7. 统计结果
    concept_results = result.get("concept_results", [])
    successful_count = len([
        r for r in concept_results
        if r.get("save_status", {}).get("metadata_saved", False)
    ])
    failed_count = len(concept_results) - successful_count
    
    logger.info(
        "langgraph_subgraph_execution_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(concept_results),
        successful_count=successful_count,
        failed_count=failed_count,
    )
    
    # 8. 成功后删除 Redis 缓存（释放内存）
    try:
        from app.db.redis_client import redis_client
        redis_key = f"content_gen_cache:{task_id}"
        await redis_client.delete(redis_key)
        logger.info(
            "content_gen_cache_deleted",
            task_id=task_id,
            redis_key=redis_key,
            reason="task_completed",
        )
    except Exception as e:
        logger.warning(
            "content_gen_cache_delete_failed",
            task_id=task_id,
            error=str(e),
        )
    
    return {
        "status": "completed" if failed_count == 0 else "partial_failure",
        "total_concepts": len(concept_results),
        "successful_count": successful_count,
        "failed_count": failed_count,
        "concept_results": concept_results,
    }


# ============================================================
# Celery 任务
# ============================================================

@celery_app.task(
    name="generate_all_content",
    bind=True,
    queue="content_generation",
)
def generate_all_content_task(
    self,
    roadmap_id: str,
    task_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    生成所有内容的协调任务（LangGraph 子图版本）
    
    架构改进：
    - ✅ 使用 LangGraph 子图替代 Celery Chord
    - ✅ 支持 Fan-Out/Fan-In 并行架构
    - ✅ 无状态模式（不使用 checkpointer，避免 psycopg pipeline 超时）
    
    职责：
    1. 获取 Framework 和 Concepts（含测试模式截断）
    2. 调用 LangGraph 子图执行内容生成
    3. 子图内部自动 Fan-Out/Fan-In 和保存结果
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 主任务 ID
        user_id: 用户 ID
        
    Returns:
        执行结果
    """
    logger.info(
        "content_generation_coordinator_started_langgraph",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=self.request.id,
        architecture="langgraph_subgraph",
    )
    
    try:
        from app.tasks.event_loop_manager import run_async_in_worker_loop
        
        # 1. 获取 Framework 和 Concepts（优先从 Redis，含测试模式截断）
        # ⚠️ 使用 Worker 持久 event loop
        framework, concepts, user_constraints, user_request = run_async_in_worker_loop(
            _get_framework_and_concepts_optimized(
                roadmap_id=roadmap_id,
                task_id=task_id,
                user_id=user_id,
            )
        )
        
        if not concepts:
            logger.warning(
                "no_concepts_to_generate",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
            return {
                "status": "completed",
                "total_concepts": 0,
                "message": "无内容需要生成",
            }
        
        # 1.5 更新任务步骤为 content_generation（从 content_generation_queued 切换）
        run_async_in_worker_loop(
            _update_task_current_step(task_id=task_id, current_step=WorkflowStep.CONTENT_GENERATION)
        )
        
        # 2. 执行 LangGraph 子图（替代 Celery Chord）
        # ⚠️ 必须使用 Worker 的持久 event loop，不能创建新的 loop
        # 原因：OrchestratorFactory 的 AsyncPostgresSaver 绑定到 Worker 持久 loop
        #      如果使用 asyncio.run() 创建新 loop，会导致 Lock 跨 loop 使用错误
        from app.tasks.event_loop_manager import run_async_in_worker_loop
        
        result = run_async_in_worker_loop(
            _execute_content_generation_subgraph(
                task_id=task_id,
                roadmap_id=roadmap_id,
                concepts=concepts,
                user_constraints=user_constraints,
                user_request=user_request,
            )
        )
        
        logger.info(
            "content_generation_coordinator_completed_langgraph",
            task_id=task_id,
            roadmap_id=roadmap_id,
            status=result.get("status"),
            successful_count=result.get("successful_count"),
            failed_count=result.get("failed_count"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "content_generation_coordinator_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
            exc_info=True,
        )
        # ✅ 更新 DB 任务状态为 failed，并推送 WebSocket 通知
        try:
            run_async_in_worker_loop(
                _handle_content_generation_failure(
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    error_message=str(e),
                )
            )
        except Exception as notify_err:
            logger.warning(
                "content_generation_failure_notification_failed",
                task_id=task_id,
                error=str(notify_err),
            )
        raise


# ============================================================
# 辅助函数
# ============================================================

async def _handle_content_generation_failure(
    task_id: str,
    roadmap_id: str,
    error_message: str,
) -> None:
    """
    内容生成任务失败时的善后处理
    
    职责：
    1. 将 RoadmapTask 状态更新为 failed，写入错误信息
    2. 通过 WebSocket 推送失败通知，让前端感知
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        error_message: 异常信息
    """
    from datetime import datetime
    
    try:
        async with get_celery_session() as session:
            task_crud = get_task_crud()
            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status="failed",
                current_step=WorkflowStep.CONTENT_GENERATION,
                error_message=error_message,
            )
        logger.info(
            "content_generation_failure_status_updated",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
    except Exception as db_err:
        logger.warning(
            "content_generation_failure_db_update_failed",
            task_id=task_id,
            error=str(db_err),
        )
    
    try:
        await notification_service.publish_progress(
            task_id=task_id,
            step=WorkflowStep.CONTENT_GENERATION,
            status="failed",
            message=f"内容生成失败: {error_message}",
        )
    except Exception as ws_err:
        logger.warning(
            "content_generation_failure_websocket_failed",
            task_id=task_id,
            error=str(ws_err),
        )


async def _update_task_current_step(task_id: str, current_step: str) -> None:
    """
    更新任务的 current_step 字段
    
    在内容生成任务的关键时间点调用：
    - 任务开始执行时：content_generation_queued → content_generation
    
    Args:
        task_id: 任务 ID
        current_step: 新的步骤值（WorkflowStep 枚举值）
    """
    try:
        async with get_celery_session() as session:
            task_crud = get_task_crud()
            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status="processing",
                current_step=current_step,
            )
        logger.info(
            "content_generation_task_step_updated",
            task_id=task_id,
            current_step=current_step,
        )
    except Exception as e:
        logger.warning(
            "content_generation_task_step_update_failed",
            task_id=task_id,
            current_step=current_step,
            error=str(e),
        )


async def _get_framework_and_concepts_optimized(
    roadmap_id: str,
    task_id: str,
    user_id: str,
) -> tuple["RoadmapFramework", list[Concept], dict, dict]:
    """
    获取 Framework 和 Concepts（优化版 - 三级读取策略）
    
    读取策略：
    1. 优先从 Redis 读取（~10ms，快速，首次执行路径）
    2. 从主图 Checkpointer 提取（任务重试路径）
       - 内容生成子图已移除 checkpointer，重试时 Redis 可能已过期/被清理
       - 主图 checkpoint 中保有完整的 roadmap_framework / intent_analysis / user_request
    3. 从数据库读取（~50ms，最终兜底）
    4. 应用测试模式截断（统一逻辑）
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 任务 ID（用于 Redis key 和 Checkpointer thread_id）
        user_id: 用户 ID（DB Fallback 时使用）
        
    Returns:
        (framework, concepts, user_constraints, user_request)
    """
    from app.db.redis_client import redis_client
    from app.models.domain import RoadmapFramework, Concept
    
    # ============ 优先级1：从 Redis 读取 ============
    if settings.CONTENT_GEN_CACHE_ENABLED:
        try:
            redis_key = f"content_gen_cache:{task_id}"
            cache_data = await redis_client.get_json(redis_key)
            
            if cache_data:
                logger.info(
                    "content_gen_cache_hit",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    redis_key=redis_key,
                    total_concepts=len(cache_data["concepts"]),
                    cached_at=cache_data.get("cached_at"),
                )
                
                # 反序列化 Pydantic 模型
                framework = RoadmapFramework(**cache_data["framework"])
                concepts = [Concept(**c) for c in cache_data["concepts"]]
                user_constraints = cache_data["user_constraints"]
                user_request = cache_data.get("user_request", {})
                
                # ✅ 应用测试模式截断（在缓存数据上应用）
                if settings.TEST_MODE_TRUNCATE_FRAMEWORK:
                    framework, concepts = _apply_test_mode_truncation(
                        framework, concepts, task_id
                    )
                
                return framework, concepts, user_constraints, user_request
        
        except Exception as e:
            logger.warning(
                "redis_cache_read_failed_fallback_to_checkpoint",
                task_id=task_id,
                roadmap_id=roadmap_id,
                error=str(e),
            )
    
    # ============ 优先级2：从主图 Checkpointer 提取 ============
    # 重试场景：内容生成子图已移除 checkpointer，Redis 缓存可能已过期（TTL）或
    # 被上次执行成功后主动删除。此时从主图 checkpoint 中恢复完整的工作流状态，
    # 可直接获取 roadmap_framework、intent_analysis、user_request，无需多次 DB 查询。
    try:
        from app.core.orchestrator_factory import OrchestratorFactory
        
        if OrchestratorFactory._initialized:
            executor = OrchestratorFactory.create_workflow_executor()
            config = {"configurable": {"thread_id": task_id}}
            main_state = await executor.graph.aget_state(config)
            
            if main_state and main_state.values:
                state_values = main_state.values
                framework_obj = state_values.get("roadmap_framework")
                intent_analysis_obj = state_values.get("intent_analysis")
                user_request_obj = state_values.get("user_request")
                
                if framework_obj:
                    # 从 framework 扁平提取所有 Concepts
                    concepts = []
                    for stage in framework_obj.stages:
                        for module in stage.modules:
                            concepts.extend(module.concepts)
                    
                    user_constraints = (
                        intent_analysis_obj.full_analysis_data
                        if intent_analysis_obj
                        else {}
                    )
                    user_request_dict = (
                        user_request_obj.model_dump()
                        if user_request_obj
                        else {}
                    )
                    
                    logger.info(
                        "content_gen_data_from_main_checkpoint",
                        task_id=task_id,
                        roadmap_id=roadmap_id,
                        total_concepts=len(concepts),
                        has_user_constraints=bool(user_constraints),
                        source="main_graph_checkpoint",
                    )
                    
                    if settings.TEST_MODE_TRUNCATE_FRAMEWORK:
                        framework_obj, concepts = _apply_test_mode_truncation(
                            framework_obj, concepts, task_id
                        )
                    
                    return framework_obj, concepts, user_constraints, user_request_dict
            
            logger.info(
                "main_checkpoint_empty_fallback_to_db",
                task_id=task_id,
                roadmap_id=roadmap_id,
                has_state=main_state is not None,
                has_values=bool(main_state.values) if main_state else False,
            )
        else:
            logger.info(
                "orchestrator_factory_not_initialized_skip_checkpoint",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
    
    except Exception as e:
        logger.warning(
            "main_checkpoint_read_failed_fallback_to_db",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
        )
    
    # ============ 优先级3：从数据库读取（最终兜底） ============
    logger.info(
        "content_gen_cache_miss_or_disabled_using_db",
        task_id=task_id,
        roadmap_id=roadmap_id,
        cache_enabled=settings.CONTENT_GEN_CACHE_ENABLED,
    )
    
    # 使用原有的数据库查询逻辑
    async with get_celery_session() as session:
        # 查询 RoadmapMetadata
        roadmap_crud = get_roadmap_crud()
        roadmap_metadata = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not roadmap_metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        # 解析 Framework
        framework = RoadmapFramework(**roadmap_metadata.framework_data)
        
        # 提取 Concepts
        concepts = []
        for stage in framework.stages:
            for module in stage.modules:
                concepts.extend(module.concepts)
        
        # 获取用户约束（Intent Analysis）
        from app.crud.crud_intent_analysis import get_intent_analysis_crud
        intent_crud = get_intent_analysis_crud()
        intent_analysis = await intent_crud.get_by_roadmap_id(session, roadmap_id)
        user_constraints = intent_analysis.full_analysis_data if intent_analysis else {}
        
        # 获取原始用户请求（来自 RoadmapTask）
        task_crud = get_task_crud()
        task = await task_crud.get_by_task_id(session, task_id)
        user_request = task.user_request if task else {}
        
        # ✅ 应用测试模式截断
        if settings.TEST_MODE_TRUNCATE_FRAMEWORK:
            framework, concepts = _apply_test_mode_truncation(
                framework, concepts, task_id
            )
        
        return framework, concepts, user_constraints, user_request


# ============================================================
# 单 Concept 特定内容类型重新生成任务
# ============================================================

@celery_app.task(
    name="content.regenerate_single",
    bind=True,
    queue="content_generation",
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=600,
    soft_time_limit=540,
)
def regenerate_single_content_task(
    self,
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    content_type: str,
) -> dict:
    """
    单个 Concept 特定内容类型重新生成（content_generation 队列）

    由 regenerate API 端点派发，避免占用主应用进程。
    使用 ContentService.retry_content 执行生成逻辑（状态更新、Agent 调用、
    结果保存、WebSocket 通知均在 Worker 内完成）。

    Args:
        task_id: 关联的 RoadmapTask ID（用于僵尸状态检测）
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        content_type: 内容类型（'tutorial' | 'resources' | 'quiz'）
    """
    from app.tasks.utils import run_async

    logger.info(
        "regenerate_single_content_started",
        celery_task_id=self.request.id,
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type=content_type,
    )

    try:
        result = run_async(
            _regenerate_single_content_async(
                celery_task_id=self.request.id,
                task_id=task_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
            )
        )
        logger.info(
            "regenerate_single_content_finished",
            task_id=task_id,
            success=result.get("success"),
        )
        return result
    except Exception as e:
        logger.error(
            "regenerate_single_content_task_error",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        return {"success": False, "task_id": task_id, "error": str(e)}


async def _regenerate_single_content_async(
    celery_task_id: str,
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    content_type: str,
) -> dict:
    """
    内容重新生成的异步实现

    在 Celery Worker 内执行，使用专用 NullPool 数据库连接。
    调用 ContentService.retry_content 复用生成逻辑。
    preferences=None 时，ContentService 自动从 framework_data 提取。

    任务结束后更新 RoadmapTask.status 为 completed/failed，
    确保僵尸状态检测能正确判断任务是否仍在运行。
    """
    from datetime import datetime
    from app.services.content.content_service import ContentService
    from app.schemas.roadmap import ConceptRetryRequest

    service = ContentService()
    request = ConceptRetryRequest(preferences=None)

    async with get_celery_session() as session:
        task_crud = get_task_crud()

        # celery_task_id 已在 API 端点创建任务时写入，此处仅确认（幂等）
        task = await task_crud.get_by_task_id(session, task_id)
        # 从任务记录中获取 user_id，供 ContentService 读取 UserProfile 语言偏好
        user_id = task.user_id if task else None

        result = await service.retry_content(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
            request=request,
            task_id=task_id,
            user_id=user_id,
        )

        # 更新 RoadmapTask 最终状态，使僵尸检测能正确感知任务已结束
        if task:
            task.status = "completed" if result.success else "failed"
            task.completed_at = datetime.utcnow()
            if not result.success:
                task.error_message = result.message
            await session.flush()

    return {
        "success": result.success,
        "task_id": task_id,
        "concept_id": result.concept_id,
        "content_type": result.content_type,
        "message": result.message,
    }
