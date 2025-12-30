"""
内容生成 Celery 任务

将内容生成从 FastAPI 主进程迁移到独立的 Celery Worker，
实现真正的进程隔离，避免阻塞主应用。

架构优势：
- FastAPI 进程：专注处理 HTTP 请求，响应速度快
- Celery Worker：独立进程执行内容生成（30+ 概念并发，90+ LLM 调用）
- Redis Queue：解耦两个进程，确保可靠性

模块拆分：
- content_generation_tasks.py: 主任务入口和并行生成逻辑
- concept_generator.py: 单概念内容生成
- content_retry_tasks.py: 重试任务
- content_utils.py: 工具函数
"""
import asyncio
import structlog
from typing import Any

from app.core.celery_app import celery_app
from app.models.domain import RoadmapFramework, LearningPreferences, Concept
from app.db.repository_factory import RepositoryFactory
from app.services.notification_service import notification_service

# 从工具模块导入
from app.tasks.content_utils import (
    run_async,
    update_framework_with_content_refs,
)

# 从概念生成器导入
from app.tasks.concept_generator import generate_single_concept

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.content_generation_tasks.generate_roadmap_content",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=1800,
    soft_time_limit=1500,
    acks_late=True,
)
def generate_roadmap_content(
    self,
    task_id: str,
    roadmap_id: str,
    roadmap_framework_data: dict,
    user_preferences_data: dict,
):
    """
    为路线图生成所有概念的内容（Celery 任务入口）
    
    该任务在独立的 Celery Worker 进程中执行，不会阻塞 FastAPI 主进程。
    
    执行流程：
    1. 反序列化输入数据
    2. 查询已完成的 Concept（断点续传）
    3. 过滤出未完成的 Concept
    4. 并行生成内容
    5. 保存结果到数据库
    6. 推送进度通知
    
    Args:
        task_id: 追踪 ID
        roadmap_id: 路线图 ID
        roadmap_framework_data: 路线图框架数据
        user_preferences_data: 用户偏好数据
        
    Returns:
        生成结果摘要
    """
    logger.info(
        "celery_content_generation_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=self.request.id,
    )
    
    try:
        result = run_async(
            _async_generate_content(
                task_id=task_id,
                roadmap_id=roadmap_id,
                roadmap_framework_data=roadmap_framework_data,
                user_preferences_data=user_preferences_data,
            )
        )
        
        logger.info(
            "celery_content_generation_task_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorial_count=result["tutorial_count"],
            failed_count=result["failed_count"],
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "celery_content_generation_task_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        
        # 更新任务状态为 failed
        try:
            from app.db.session import safe_session_with_retry
            from app.db.repositories.task_repo import TaskRepository
            
            async def _update_failed_status():
                async with safe_session_with_retry() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="content_generation",
                        error_message=str(e)[:500],
                    )
                    await session.commit()
            
            run_async(_update_failed_status())
        except Exception as update_error:
            logger.error("failed_to_update_task_status", task_id=task_id, error=str(update_error))
        
        raise


async def _async_generate_content(
    task_id: str,
    roadmap_id: str,
    roadmap_framework_data: dict,
    user_preferences_data: dict,
) -> dict[str, Any]:
    """
    内容生成核心逻辑（异步）
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        roadmap_framework_data: 路线图框架数据
        user_preferences_data: 用户偏好数据
        
    Returns:
        生成结果摘要
    """
    from app.agents.factory import get_agent_factory
    from app.core.orchestrator.base import WorkflowConfig
    from app.services.execution_logger import execution_logger
    
    logger.info(
        "async_content_generation_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
    )
    
    # 1. 反序列化数据
    framework = RoadmapFramework.model_validate(roadmap_framework_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 2. 提取所有概念
    all_concepts: list[Concept] = []
    concept_map: dict[str, Concept] = {}
    for stage in framework.stages:
        for module in stage.modules:
            for concept in module.concepts:
                all_concepts.append(concept)
                concept_map[concept.concept_id] = concept
    
    total_concepts = len(all_concepts)
    logger.info(
        "concepts_extracted",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=total_concepts,
    )
    
    # 3. 断点续传：查询已完成的 Concept
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    completed_concept_ids = set()
    async with safe_session_with_retry() as session:
        repo = RoadmapRepository(session)
        completed_tutorials = await repo.get_tutorials_by_roadmap(
            roadmap_id=roadmap_id,
            latest_only=True,
        )
        completed_concept_ids = {
            tutorial.concept_id 
            for tutorial in completed_tutorials 
            if tutorial.content_status == "completed"
        }
    
    # 4. 过滤：只生成未完成的 Concept
    pending_concepts = [
        concept 
        for concept in all_concepts 
        if concept.concept_id not in completed_concept_ids
    ]
    
    skipped_count = len(all_concepts) - len(pending_concepts)
    logger.info(
        "concepts_filtered_by_completion",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(all_concepts),
        completed_concepts=len(completed_concept_ids),
        pending_concepts=len(pending_concepts),
    )
    
    # 如果所有概念都已完成，直接返回
    if not pending_concepts:
        logger.info("all_concepts_already_completed", task_id=task_id, roadmap_id=roadmap_id)
        
        await notification_service.publish_completed(
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorials_count=len(completed_concept_ids),
            failed_count=0,
        )
        
        return {
            "tutorial_count": len(completed_concept_ids),
            "resource_count": len(completed_concept_ids),
            "quiz_count": len(completed_concept_ids),
            "failed_count": 0,
            "failure_rate": 0,
            "skipped_count": skipped_count,
        }
    
    # 5. 创建服务和工具
    repo_factory = RepositoryFactory()
    agent_factory = get_agent_factory()
    config = WorkflowConfig()
    
    # 6. 并行生成内容
    tutorial_refs, resource_refs, quiz_refs, failed_concepts = await _generate_content_parallel(
        task_id=task_id,
        roadmap_id=roadmap_id,
        concepts=pending_concepts,
        concept_map=concept_map,
        preferences=preferences,
        agent_factory=agent_factory,
    )
    
    # 7. 检查失败率
    failed_count = len(failed_concepts)
    attempted_concepts = len(pending_concepts)
    success_count = attempted_concepts - failed_count
    failure_rate = failed_count / attempted_concepts if attempted_concepts > 0 else 0
    
    FAILURE_THRESHOLD = 0.5
    
    if failure_rate >= FAILURE_THRESHOLD or failed_count == attempted_concepts:
        error_message = (
            f"Content generation failed: {failed_count}/{attempted_concepts} concepts failed "
            f"(failure rate: {failure_rate:.1%}). Threshold: {FAILURE_THRESHOLD:.1%}"
        )
        
        await execution_logger.error(
            task_id=task_id,
            category="workflow",
            step="content_generation",
            roadmap_id=roadmap_id,
            message=f"❌ Content generation aborted: failure rate too high ({failure_rate:.1%})",
            details={
                "log_type": "content_generation_aborted",
                "total_concepts": len(all_concepts),
                "attempted_concepts": attempted_concepts,
                "failed_concepts": failed_count,
                "failure_rate": failure_rate,
                "failed_concept_ids": failed_concepts,
            },
        )
        
        raise RuntimeError(error_message)
    
    # 8. 保存结果到数据库
    await _save_content_results(
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorial_refs=tutorial_refs,
        resource_refs=resource_refs,
        quiz_refs=quiz_refs,
        failed_concepts=failed_concepts,
        repo_factory=repo_factory,
    )
    
    # 9. 发布完成通知
    await notification_service.publish_completed(
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorials_count=len(tutorial_refs),
        failed_count=failed_count,
    )
    
    logger.info(
        "async_content_generation_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorial_count=len(tutorial_refs),
        failed_count=failed_count,
    )
    
    return {
        "tutorial_count": len(tutorial_refs),
        "resource_count": len(resource_refs),
        "quiz_count": len(quiz_refs),
        "failed_count": failed_count,
        "failure_rate": failure_rate,
        "skipped_count": skipped_count,
        "attempted_count": attempted_concepts,
    }


async def _generate_content_parallel(
    task_id: str,
    roadmap_id: str,
    concepts: list[Concept],
    concept_map: dict[str, Concept],
    preferences: LearningPreferences,
    agent_factory: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    """
    并行生成所有概念的内容
    
    每个概念独立生成（Tutorial → Resource → Quiz），完成后立即写入数据库。
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concepts: 概念列表
        concept_map: 概念映射
        preferences: 用户偏好
        agent_factory: Agent 工厂
        
    Returns:
        (tutorial_refs, resource_refs, quiz_refs, failed_concepts)
    """
    total_concepts = len(concepts)
    progress_counter = {"current": 0}
    progress_lock = asyncio.Lock()
    
    tutorial_refs: dict[str, Any] = {}
    resource_refs: dict[str, Any] = {}
    quiz_refs: dict[str, Any] = {}
    failed_concepts: list[str] = []
    results_lock = asyncio.Lock()
    
    # 并发执行所有概念的内容生成
    tasks = [
        generate_single_concept(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept=concept,
            concept_map=concept_map,
            preferences=preferences,
            agent_factory=agent_factory,
            total_concepts=total_concepts,
            progress_counter=progress_counter,
            progress_lock=progress_lock,
            tutorial_refs=tutorial_refs,
            resource_refs=resource_refs,
            quiz_refs=quiz_refs,
            failed_concepts=failed_concepts,
            results_lock=results_lock,
        )
        for concept in concepts
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info(
        "content_generation_parallel_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorial_count=len(tutorial_refs),
        resource_count=len(resource_refs),
        quiz_count=len(quiz_refs),
        failed_count=len(failed_concepts),
    )
    
    return tutorial_refs, resource_refs, quiz_refs, failed_concepts


async def _save_content_results(
    task_id: str,
    roadmap_id: str,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
    repo_factory: Any,
):
    """
    保存内容生成结果（分批事务操作，带容错机制）
    
    改进：
    - 捕获数据库错误，将失败的批次记录到 failed_concepts
    - 即使部分批次失败，也保存成功的部分
    - 确保 framework_data 和 task 状态始终被更新
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        tutorial_refs: 教程引用字典
        resource_refs: 资源引用字典
        quiz_refs: 测验引用字典
        failed_concepts: 失败的概念 ID 列表（会被修改）
        repo_factory: Repository 工厂
    """
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    from sqlalchemy.exc import IntegrityError, DBAPIError
    
    logger.info(
        "save_content_results_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorial_count=len(tutorial_refs),
        failed_count=len(failed_concepts),
    )
    
    BATCH_SIZE = 3
    
    # 用于跟踪保存失败的 concept_id
    save_failed_concepts = []
    
    # Phase 1: 分批保存元数据（带容错机制）
    if tutorial_refs:
        tutorial_items = list(tutorial_refs.items())
        for i in range(0, len(tutorial_items), BATCH_SIZE):
            batch = dict(tutorial_items[i:i + BATCH_SIZE])
            try:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_tutorials_batch(batch, roadmap_id)
                    await session.commit()
            except (IntegrityError, DBAPIError) as e:
                logger.error(
                    "tutorial_batch_save_failed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    batch_index=i // BATCH_SIZE,
                    concept_ids=list(batch.keys()),
                    error=str(e)[:500],
                    error_type=type(e).__name__,
                )
                # 将失败的概念添加到 failed_concepts
                for concept_id in batch.keys():
                    if concept_id not in failed_concepts and concept_id not in save_failed_concepts:
                        save_failed_concepts.append(concept_id)
                        failed_concepts.append(concept_id)
                # 继续处理下一批
                continue
    
    if resource_refs:
        resource_items = list(resource_refs.items())
        for i in range(0, len(resource_items), BATCH_SIZE):
            batch = dict(resource_items[i:i + BATCH_SIZE])
            try:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_resources_batch(batch, roadmap_id)
                    await session.commit()
            except (IntegrityError, DBAPIError) as e:
                logger.error(
                    "resource_batch_save_failed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    batch_index=i // BATCH_SIZE,
                    concept_ids=list(batch.keys()),
                    error=str(e)[:500],
                    error_type=type(e).__name__,
                )
                # 将失败的概念添加到 failed_concepts
                for concept_id in batch.keys():
                    if concept_id not in failed_concepts and concept_id not in save_failed_concepts:
                        save_failed_concepts.append(concept_id)
                        failed_concepts.append(concept_id)
                continue
    
    if quiz_refs:
        quiz_items = list(quiz_refs.items())
        for i in range(0, len(quiz_items), BATCH_SIZE):
            batch = dict(quiz_items[i:i + BATCH_SIZE])
            try:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_quizzes_batch(batch, roadmap_id)
                    await session.commit()
            except (IntegrityError, DBAPIError) as e:
                logger.error(
                    "quiz_batch_save_failed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    batch_index=i // BATCH_SIZE,
                    concept_ids=list(batch.keys()),
                    error=str(e)[:500],
                    error_type=type(e).__name__,
                )
                # 将失败的概念添加到 failed_concepts
                for concept_id in batch.keys():
                    if concept_id not in failed_concepts and concept_id not in save_failed_concepts:
                        save_failed_concepts.append(concept_id)
                        failed_concepts.append(concept_id)
                continue
    
    # 记录保存失败的统计
    if save_failed_concepts:
        logger.warning(
            "some_concepts_failed_to_save",
            task_id=task_id,
            roadmap_id=roadmap_id,
            save_failed_count=len(save_failed_concepts),
            save_failed_concepts=save_failed_concepts[:10],  # 只记录前 10 个
        )
    
    # Phase 2: 更新 framework_data（必须执行，即使 Phase 1 有失败）
    try:
        async with safe_session_with_retry() as session:
            repo = RoadmapRepository(session)
            roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
            
            if roadmap_metadata and roadmap_metadata.framework_data:
                updated_framework = update_framework_with_content_refs(
                    framework_data=roadmap_metadata.framework_data,
                    tutorial_refs=tutorial_refs,
                    resource_refs=resource_refs,
                    quiz_refs=quiz_refs,
                    failed_concepts=failed_concepts,
                )
                
                framework_obj = RoadmapFramework.model_validate(updated_framework)
                await repo.save_roadmap_metadata(
                    roadmap_id=roadmap_id,
                    user_id=roadmap_metadata.user_id,
                    framework=framework_obj,
                )
                await session.commit()
                
                logger.info(
                    "framework_data_updated",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    tutorial_count=len(tutorial_refs),
                    failed_count=len(failed_concepts),
                )
            else:
                logger.warning(
                    "framework_data_not_found",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
    except Exception as e:
        logger.error(
            "framework_data_update_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e)[:500],
            error_type=type(e).__name__,
        )
        # 不抛出异常，继续执行 Phase 3
    
    # Phase 3: 更新 task 最终状态（必须执行）
    final_status = "partial_failure" if failed_concepts else "completed"
    final_step = "content_generation" if failed_concepts else "completed"
    
    try:
        async with safe_session_with_retry() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status=final_status,
                current_step=final_step,
                failed_concepts={
                    "count": len(failed_concepts),
                    "concept_ids": failed_concepts,
                } if failed_concepts else None,
                execution_summary={
                    "tutorial_count": len(tutorial_refs),
                    "resource_count": len(resource_refs),
                    "quiz_count": len(quiz_refs),
                    "failed_count": len(failed_concepts),
                    "save_failed_count": len(save_failed_concepts),
                },
            )
            await session.commit()
            
            logger.info(
                "task_status_updated",
                task_id=task_id,
                final_status=final_status,
                failed_count=len(failed_concepts),
            )
    except Exception as e:
        logger.error(
            "task_status_update_failed",
            task_id=task_id,
            error=str(e)[:500],
            error_type=type(e).__name__,
        )
        # 不抛出异常，避免影响整体流程
    
    logger.info(
        "save_content_results_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        final_status=final_status,
        tutorial_saved=len(tutorial_refs) - len([c for c in save_failed_concepts if c in tutorial_refs]),
        tutorial_failed=len([c for c in save_failed_concepts if c in tutorial_refs]),
        total_failed=len(failed_concepts),
    )


@celery_app.task(
    name="app.tasks.content_generation_tasks.retry_failed_content_task",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=1800,
    soft_time_limit=1500,
    acks_late=True,
)
def retry_failed_content_task(
    self,
    roadmap_id: str,
    task_id: str,
    user_id: str,
    preferences: dict,
    content_types: list[str],
):
    """
    重试失败内容的生成（Celery 任务入口）
    
    该任务在独立的 Celery Worker 进程中执行，不会阻塞 FastAPI 主进程。
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 任务 ID（用于 WebSocket 通知）
        user_id: 用户 ID
        preferences: 用户偏好（字典格式）
        content_types: 要重试的内容类型列表（["tutorial", "resources", "quiz"]）
        
    Returns:
        重试结果摘要
    """
    from app.services.retry_service import execute_retry_failed_task
    from app.api.v1.endpoints.utils import get_failed_content_items
    from app.db.repository_factory import RepositoryFactory
    
    logger.info(
        "celery_retry_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=self.request.id,
    )
    
    try:
        # 反序列化用户偏好
        user_preferences = LearningPreferences.model_validate(preferences)
        
        # 查询失败的内容项目
        async def _get_failed_items():
            async with RepositoryFactory().create_session() as session:
                from app.db.repositories.roadmap_repo import RoadmapRepository
                repo = RoadmapRepository(session)
                roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
                
                if not roadmap_metadata:
                    raise RuntimeError(f"路线图 {roadmap_id} 不存在")
                
                # 获取失败的内容项目
                failed_items = get_failed_content_items(roadmap_metadata.framework_data)
                
                # 筛选要重试的类型
                items_to_retry = {}
                for content_type in content_types:
                    if content_type in failed_items and failed_items[content_type]:
                        items_to_retry[content_type] = failed_items[content_type]
                
                return items_to_retry
        
        items_to_retry = run_async(_get_failed_items())
        
        if not items_to_retry:
            logger.warning(
                "no_failed_items_to_retry",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
            return {
                "success": True,
                "retried_count": 0,
                "message": "没有需要重试的失败项目",
            }
        
        # 执行重试
        run_async(
            execute_retry_failed_task(
                retry_task_id=task_id,
                roadmap_id=roadmap_id,
                items_to_retry=items_to_retry,
                user_preferences=user_preferences,
                user_id=user_id,
            )
        )
        
        logger.info(
            "celery_retry_task_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        return {
            "success": True,
            "retried_count": sum(len(items) for items in items_to_retry.values()),
        }
        
    except Exception as e:
        logger.error(
            "celery_retry_task_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        
        # 更新任务状态为 failed
        try:
            from app.db.session import safe_session_with_retry
            from app.db.repositories.task_repo import TaskRepository
            
            async def _update_failed_status():
                async with safe_session_with_retry() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="content_retry",
                        error_message=str(e)[:500],
                    )
                    await session.commit()
            
            run_async(_update_failed_status())
        except Exception as update_error:
            logger.error("failed_to_update_task_status", task_id=task_id, error=str(update_error))
        
        raise
