"""
内容生成 Celery 任务

将内容生成从 FastAPI 主进程迁移到独立的 Celery Worker，
实现真正的进程隔离，避免阻塞主应用。

架构优势：
- FastAPI 进程：专注处理 HTTP 请求，响应速度快
- Celery Worker：独立进程执行内容生成（30+ 概念并发，90+ LLM 调用）
- Redis Queue：解耦两个进程，确保可靠性

工作流分离：
1. Framework 生成阶段（FastAPI 进程）：
   - IntentAnalysis → CurriculumDesign → Validation → Review
   
2. Content 生成阶段（Celery Worker 进程）：
   - Tutorial + Resource + Quiz 并行生成
"""
import asyncio
import structlog
from typing import Any

from app.core.celery_app import celery_app
from app.models.domain import RoadmapFramework, LearningPreferences, Concept
from app.db.repository_factory import RepositoryFactory
from app.services.notification_service import notification_service

logger = structlog.get_logger()

# 每个 Worker 进程的事件循环（懒加载）
_worker_loop = None


def get_worker_loop():
    """
    获取或创建 Worker 进程的事件循环
    
    每个 Worker 进程维护一个独立的事件循环，
    不在任务结束时关闭，避免连接清理问题。
    
    Returns:
        asyncio.AbstractEventLoop: Worker 进程的事件循环
    """
    global _worker_loop
    
    if _worker_loop is None or _worker_loop.is_closed():
        # 创建新的事件循环
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.debug("celery_worker_loop_created", loop_id=id(_worker_loop))
    
    return _worker_loop


def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    使用 Worker 进程级别的事件循环，避免频繁创建/销毁循环。
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    """
    loop = get_worker_loop()
    return loop.run_until_complete(coro)


@celery_app.task(
    name="app.tasks.content_generation_tasks.generate_roadmap_content",
    queue="content_generation",
    bind=True,
    max_retries=0,  # ✅ 禁用自动重试，失败后通过手动重试解决
    time_limit=1800,  # 30分钟硬超时
    soft_time_limit=1500,  # 25分钟软超时
    acks_late=True,  # 任务完成后才确认，确保不丢失任务
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
    1. 反序列化输入数据（RoadmapFramework、LearningPreferences）
    2. 从数据库查询已完成的 Concept（支持断点续传）
    3. 过滤出未完成的 Concept
    4. 并行生成教程、资源、测验（只生成未完成的）
    5. 批量保存结果到数据库
    6. 更新 roadmap_metadata 的 framework_data
    7. 通过 WebSocket 推送进度通知
    
    ✨ 断点续传：
    - Worker 重启后自动跳过已完成的 Concept
    - 只生成未完成的内容，避免重复调用 LLM
    - 节省成本和时间
    
    ❌ 不再自动重试：
    - 任务失败后不会自动重试
    - 需要通过 API 手动触发重试（`/retry-failed` 或单个 Concept 重试）
    - 避免重复失败浪费资源
    
    Args:
        self: Celery 任务实例（bind=True）
        task_id: 追踪 ID
        roadmap_id: 路线图 ID
        roadmap_framework_data: 路线图框架数据（JSON 序列化）
        user_preferences_data: 用户偏好数据（JSON 序列化）
        
    Returns:
        生成结果摘要
        
    Raises:
        Exception: 内容生成失败（不会自动重试）
    """
    logger.info(
        "celery_content_generation_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=self.request.id,
    )
    
    try:
        # 运行异步生成逻辑
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
        
        # ✅ 更新任务状态为 failed（确保 Worker 重启后状态正确）
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
            
            logger.info(
                "task_status_updated_to_failed",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        except Exception as update_error:
            logger.error(
                "failed_to_update_task_status",
                task_id=task_id,
                error=str(update_error),
            )
        
        # ❌ 不再自动重试，直接抛出异常
        # 用户可以通过 API 手动触发重试
        raise


async def _async_generate_content(
    task_id: str,
    roadmap_id: str,
    roadmap_framework_data: dict,
    user_preferences_data: dict,
) -> dict[str, Any]:
    """
    内容生成核心逻辑（异步）
    
    该函数执行实际的内容生成工作，包括：
    1. 反序列化数据
    2. 创建必要的服务和工具
    3. 并行生成内容
    4. 保存结果
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        roadmap_framework_data: 路线图框架数据（字典）
        user_preferences_data: 用户偏好数据（字典）
        
    Returns:
        生成结果摘要
    """
    from app.agents.factory import get_agent_factory
    from app.core.orchestrator.base import WorkflowConfig
    from app.core.orchestrator.workflow_brain import WorkflowBrain
    from app.core.orchestrator.state_manager import StateManager
    from app.services.execution_logger import execution_logger
    from app.models.domain import (
        TutorialGenerationInput,
        ResourceRecommendationInput,
        QuizGenerationInput,
        TutorialGenerationOutput,
        ResourceRecommendationOutput,
        QuizGenerationOutput,
    )
    
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
    
    # 3. ✅ 断点续传：查询数据库中已完成的 Concept
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    completed_concept_ids = set()
    async with safe_session_with_retry() as session:
        repo = RoadmapRepository(session)
        
        # 查询所有已完成的教程（以教程完成为准，因为它是核心内容）
        completed_tutorials = await repo.get_tutorials_by_roadmap(
            roadmap_id=roadmap_id,
            latest_only=True,
        )
        completed_concept_ids = {
            tutorial.concept_id 
            for tutorial in completed_tutorials 
            if tutorial.content_status == "completed"
        }
    
    # 4. ✅ 过滤：只生成未完成的 Concept
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
        skipped_count=skipped_count,
    )
    
    # 如果所有概念都已完成，直接返回
    if not pending_concepts:
        logger.info(
            "all_concepts_already_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 发布完成通知
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
    agent_factory = get_agent_factory()  # ✅ 使用全局单例，自动注入 settings
    config = WorkflowConfig()
    
    # 6. 并行生成内容（只生成未完成的 Concept）
    tutorial_refs, resource_refs, quiz_refs, failed_concepts = await _generate_content_parallel(
        task_id=task_id,
        roadmap_id=roadmap_id,
        concepts=pending_concepts,  # ✅ 使用过滤后的列表
        concept_map=concept_map,
        preferences=preferences,
        agent_factory=agent_factory,
        config=config,
    )
    
    # 7. 检查失败率（基于本次需要生成的 Concept 数量）
    failed_count = len(failed_concepts)
    attempted_concepts = len(pending_concepts)  # ✅ 本次尝试生成的数量
    success_count = attempted_concepts - failed_count
    failure_rate = failed_count / attempted_concepts if attempted_concepts > 0 else 0
    
    FAILURE_THRESHOLD = 0.5
    
    if failure_rate >= FAILURE_THRESHOLD or failed_count == attempted_concepts:
        error_message = (
            f"Content generation failed: {failed_count}/{attempted_concepts} concepts failed "
            f"(failure rate: {failure_rate:.1%}). Threshold: {FAILURE_THRESHOLD:.1%}"
        )
        
        # 记录致命错误
        await execution_logger.error(
            task_id=task_id,
            category="workflow",
            step="content_generation",
            roadmap_id=roadmap_id,
            message=f"❌ Content generation aborted: failure rate too high ({failure_rate:.1%})",
            details={
                "log_type": "content_generation_aborted",
                "total_concepts": len(all_concepts),
                "skipped_concepts": skipped_count,
                "attempted_concepts": attempted_concepts,
                "failed_concepts": failed_count,
                "success_concepts": success_count,
                "failure_rate": failure_rate,
                "threshold": FAILURE_THRESHOLD,
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
        total_concepts=len(all_concepts),
        skipped_count=skipped_count,
        attempted_count=attempted_concepts,
        tutorial_count=len(tutorial_refs),
        resource_count=len(resource_refs),
        quiz_count=len(quiz_refs),
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
    config: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    """
    并行生成教程、资源、测验（增量写入数据库优化版）
    
    优化策略：
    - 每完成 3 个 Concept 就写入数据库一次
    - 前端可以更及时地看到进度更新
    - 最后不满 3 个的批次也会被写入
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concepts: 概念列表
        concept_map: 概念ID到概念对象的映射
        preferences: 用户学习偏好
        agent_factory: Agent 工厂
        config: 工作流配置
        
    Returns:
        (tutorial_refs, resource_refs, quiz_refs, failed_concepts)
    """
    from app.models.domain import (
        TutorialGenerationInput,
        ResourceRecommendationInput,
        QuizGenerationInput,
    )
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    # 创建信号量（控制并发数）
    max_concurrent = config.parallel_tutorial_limit
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 创建共享数据结构（线程安全）
    total_concepts = len(concepts)
    progress_counter = {"current": 0}
    
    # 增量写入配置
    INCREMENTAL_BATCH_SIZE = 3  # 每完成 3 个就写数据库
    completed_buffer: dict[str, tuple[Any, Any, Any]] = {}  # 待写入缓冲区
    buffer_lock = asyncio.Lock()  # 保护缓冲区的锁
    
    # 最终结果累积
    tutorial_refs: dict[str, Any] = {}
    resource_refs: dict[str, Any] = {}
    quiz_refs: dict[str, Any] = {}
    failed_concepts: list[str] = []
    
    # 并发执行所有概念的内容生成
    tasks = [
        _generate_single_concept_with_incremental_save(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept=concept,
            concept_map=concept_map,
            preferences=preferences,
            agent_factory=agent_factory,
            semaphore=semaphore,
            total_concepts=total_concepts,
            progress_counter=progress_counter,
            completed_buffer=completed_buffer,
            buffer_lock=buffer_lock,
            batch_size=INCREMENTAL_BATCH_SIZE,
            tutorial_refs=tutorial_refs,
            resource_refs=resource_refs,
            quiz_refs=quiz_refs,
            failed_concepts=failed_concepts,
        )
        for concept in concepts
    ]
    
    await asyncio.gather(*tasks, return_exceptions=False)
    
    # 处理最后不满 3 个的剩余批次
    async with buffer_lock:
        if completed_buffer:
            logger.info(
                "incremental_save_final_batch",
                task_id=task_id,
                roadmap_id=roadmap_id,
                remaining_count=len(completed_buffer),
            )
            await _save_incremental_batch(
                task_id=task_id,
                roadmap_id=roadmap_id,
                completed_buffer=completed_buffer,
                tutorial_refs=tutorial_refs,
                resource_refs=resource_refs,
                quiz_refs=quiz_refs,
            )
            completed_buffer.clear()
    
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


async def _save_incremental_batch(
    task_id: str,
    roadmap_id: str,
    completed_buffer: dict[str, tuple[Any, Any, Any]],
    tutorial_refs: dict[str, Any],
    resource_refs: dict[str, Any],
    quiz_refs: dict[str, Any],
):
    """
    增量保存一批已完成的 Concept 内容到数据库
    
    每完成 3 个 Concept 就调用一次，实现增量写入，
    让前端可以更及时地看到状态更新。
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        completed_buffer: 待写入的 Concept 缓冲区 {concept_id: (tutorial, resource, quiz)}
        tutorial_refs: 教程引用累积字典
        resource_refs: 资源引用累积字典
        quiz_refs: 测验引用累积字典
    """
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    from app.models.domain import RoadmapFramework
    
    if not completed_buffer:
        return
    
    # 提取本批次的内容
    batch_tutorial_refs: dict[str, Any] = {}
    batch_resource_refs: dict[str, Any] = {}
    batch_quiz_refs: dict[str, Any] = {}
    
    for concept_id, (tutorial, resource, quiz) in completed_buffer.items():
        if tutorial:
            batch_tutorial_refs[concept_id] = tutorial
        if resource:
            batch_resource_refs[concept_id] = resource
        if quiz:
            batch_quiz_refs[concept_id] = quiz
    
    logger.info(
        "incremental_batch_save_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        batch_size=len(completed_buffer),
        tutorial_count=len(batch_tutorial_refs),
        resource_count=len(batch_resource_refs),
        quiz_count=len(batch_quiz_refs),
    )
    
    # 分批保存元数据（单个数据库事务）
    async with safe_session_with_retry() as session:
        repo = RoadmapRepository(session)
        
        # 保存教程
        if batch_tutorial_refs:
            await repo.save_tutorials_batch(batch_tutorial_refs, roadmap_id)
        
        # 保存资源
        if batch_resource_refs:
            await repo.save_resources_batch(batch_resource_refs, roadmap_id)
        
        # 保存测验
        if batch_quiz_refs:
            await repo.save_quizzes_batch(batch_quiz_refs, roadmap_id)
        
        await session.commit()
    
    # 更新 framework_data 中的状态（让前端可以立即看到更新）
    # ✅ 使用累积的 refs（tutorial_refs 等），确保 framework 包含所有已完成的状态
    async with safe_session_with_retry() as session:
        repo = RoadmapRepository(session)
        roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
        
        if roadmap_metadata and roadmap_metadata.framework_data:
            # 使用累积字典更新 framework（包含所有已完成的 Concept 状态）
            updated_framework = _update_framework_with_content_refs(
                framework_data=roadmap_metadata.framework_data,
                tutorial_refs=tutorial_refs,  # 累积字典，包含所有已完成的
                resource_refs=resource_refs,
                quiz_refs=quiz_refs,
                failed_concepts=[],  # 增量更新时不处理失败（失败会在最后统一处理）
            )
            
            framework_obj = RoadmapFramework.model_validate(updated_framework)
            await repo.save_roadmap_metadata(
                roadmap_id=roadmap_id,
                user_id=roadmap_metadata.user_id,
                framework=framework_obj,
            )
            await session.commit()
    
    logger.info(
        "incremental_batch_save_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        batch_size=len(completed_buffer),
    )


async def _generate_single_concept_with_incremental_save(
    task_id: str,
    roadmap_id: str,
    concept: Concept,
    concept_map: dict[str, Concept],
    preferences: LearningPreferences,
    agent_factory: Any,
    semaphore: asyncio.Semaphore,
    total_concepts: int,
    progress_counter: dict[str, int],
    completed_buffer: dict[str, tuple[Any, Any, Any]],
    buffer_lock: asyncio.Lock,
    batch_size: int,
    tutorial_refs: dict[str, Any],
    resource_refs: dict[str, Any],
    quiz_refs: dict[str, Any],
    failed_concepts: list[str],
) -> None:
    """
    为单个概念生成教程、资源、测验（增量保存版）
    
    每完成一个 Concept，就添加到缓冲区。
    当缓冲区达到 batch_size（3个）时，触发数据库写入。
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concept: 概念
        concept_map: 概念ID到概念对象的映射
        preferences: 用户学习偏好
        agent_factory: Agent 工厂
        semaphore: 信号量（控制并发）
        total_concepts: 总概念数
        progress_counter: 共享进度计数器
        completed_buffer: 已完成概念缓冲区（待写入）
        buffer_lock: 缓冲区保护锁
        batch_size: 批次大小（每达到该数量就写数据库）
        tutorial_refs: 教程引用累积字典
        resource_refs: 资源引用累积字典
        quiz_refs: 测验引用累积字典
        failed_concepts: 失败概念累积列表
    """
    from app.models.domain import (
        TutorialGenerationInput,
        ResourceRecommendationInput,
        QuizGenerationInput,
    )
    from app.services.execution_logger import execution_logger, LogCategory
    
    async with semaphore:
        # 主动让出事件循环时间片
        await asyncio.sleep(0)
        
        concept_id = concept.concept_id
        concept_name = concept.name
        
        # 更新进度计数器
        progress_counter["current"] += 1
        current_progress = progress_counter["current"]
        
        # 每处理 5 个概念后，额外让出
        if current_progress % 5 == 0:
            await asyncio.sleep(0.05)
        
        # 发送 WebSocket 事件：概念开始生成
        await notification_service.publish_concept_start(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
            current=current_progress,
            total=total_concepts,
            content_type="tutorial",
        )
        
        try:
            # 创建三个 Agent
            tutorial_agent = agent_factory.create_tutorial_generator()
            resource_agent = agent_factory.create_resource_recommender()
            quiz_agent = agent_factory.create_quiz_generator()
            
            # 构建前置概念详情列表
            prerequisite_details = []
            if concept.prerequisites:
                from urllib.parse import quote
                for prereq_id in concept.prerequisites:
                    prereq_concept = concept_map.get(prereq_id)
                    if prereq_concept:
                        prereq_url = f"/roadmap/{roadmap_id}?concept={quote(prereq_id)}"
                        prerequisite_details.append({
                            "concept_id": prereq_id,
                            "name": prereq_concept.name,
                            "url": prereq_url,
                        })
            
            # 准备输入
            tutorial_input = TutorialGenerationInput(
                concept=concept,
                user_preferences=preferences,
                context={
                    "roadmap_id": roadmap_id,
                    "prerequisite_details": prerequisite_details,
                },
            )
            resource_input = ResourceRecommendationInput(
                concept=concept,
                user_preferences=preferences,
                context={
                    "roadmap_id": roadmap_id,
                },
            )
            quiz_input = QuizGenerationInput(
                concept=concept,
                user_preferences=preferences,
                context={
                    "roadmap_id": roadmap_id,
                },
            )
            
            # 记录开始生成日志
            await execution_logger.info(
                task_id=task_id,
                category=LogCategory.WORKFLOW,
                step="content_generation",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                message=f"🚀 Generating content for concept: {concept_name}",
                details={
                    "log_type": "content_generation_start",
                    "concept": {
                        "id": concept_id,
                        "name": concept_name,
                        "difficulty": concept.difficulty,
                    },
                },
            )
            
            # 并行执行三个 Agent
            tutorial, resource, quiz = await asyncio.gather(
                tutorial_agent.execute(tutorial_input),
                resource_agent.execute(resource_input),
                quiz_agent.execute(quiz_input),
                return_exceptions=False,
            )
            
            # 记录概念完成日志
            await execution_logger.info(
                task_id=task_id,
                category=LogCategory.WORKFLOW,
                step="content_generation",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                message=f"🎉 All content generated for concept: {concept_name}",
                details={
                    "log_type": "concept_completed",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "completed_content": [
                        "tutorial" if tutorial else None,
                        "resources" if resource else None,
                        "quiz" if quiz else None,
                    ],
                },
            )
            
            # 发送 WebSocket 事件：概念生成完成
            await notification_service.publish_concept_complete(
                task_id=task_id,
                concept_id=concept_id,
                concept_name=concept_name,
                data={
                    "tutorial_id": tutorial.tutorial_id if tutorial and hasattr(tutorial, 'tutorial_id') else None,
                    "resources_count": len(resource.resources) if resource and hasattr(resource, 'resources') else 0,
                    "quiz_questions": len(quiz.questions) if quiz and hasattr(quiz, 'questions') else 0,
                },
                content_type="tutorial",
            )
            
            # ✅ 增量保存逻辑：添加到缓冲区，达到批次大小时触发写入
            async with buffer_lock:
                # 1. 添加到缓冲区
                completed_buffer[concept_id] = (tutorial, resource, quiz)
                
                # 2. 累积到最终结果
                if tutorial:
                    tutorial_refs[concept_id] = tutorial
                if resource:
                    resource_refs[concept_id] = resource
                if quiz:
                    quiz_refs[concept_id] = quiz
                
                # 3. 检查是否达到批次大小
                if len(completed_buffer) >= batch_size:
                    logger.info(
                        "incremental_batch_trigger",
                        task_id=task_id,
                        roadmap_id=roadmap_id,
                        buffer_size=len(completed_buffer),
                        batch_size=batch_size,
                    )
                    
                    # 触发增量保存
                    await _save_incremental_batch(
                        task_id=task_id,
                        roadmap_id=roadmap_id,
                        completed_buffer=completed_buffer,
                        tutorial_refs=tutorial_refs,
                        resource_refs=resource_refs,
                        quiz_refs=quiz_refs,
                    )
                    
                    # 清空缓冲区（已写入数据库）
                    completed_buffer.clear()
            
        except Exception as e:
            logger.error(
                "content_generation_concept_failed_exception",
                task_id=task_id,
                concept_id=concept_id,
                error=str(e),
            )
            
            # 记录失败日志
            await execution_logger.error(
                task_id=task_id,
                category=LogCategory.AGENT,
                step="content_generation",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                message=f"❌ Content generation failed for concept: {concept_name}",
                details={
                    "log_type": "content_generation_failed",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "error": str(e)[:500],
                    "error_type": type(e).__name__,
                },
            )
            
            # 发送 WebSocket 事件：概念生成失败
            await notification_service.publish_concept_failed(
                task_id=task_id,
                concept_id=concept_id,
                concept_name=concept_name,
                error=str(e)[:200],
                content_type="tutorial",
            )
            
            # ✅ 添加到失败列表
            async with buffer_lock:
                if concept_id not in failed_concepts:
                    failed_concepts.append(concept_id)
            
            # 不要 raise，让其他 Concept 继续执行
            # raise


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
    保存内容生成结果（分批事务操作）
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        tutorial_refs: 教程引用字典
        resource_refs: 资源引用字典
        quiz_refs: 测验引用字典
        failed_concepts: 失败的概念 ID 列表
        repo_factory: Repository 工厂
    """
    from app.db.session import safe_session_with_retry
    from app.db.repositories.roadmap_repo import RoadmapRepository
    from app.models.domain import RoadmapFramework
    
    logger.info(
        "save_content_results_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorial_count=len(tutorial_refs),
        resource_count=len(resource_refs),
        quiz_count=len(quiz_refs),
        failed_count=len(failed_concepts),
    )
    
    BATCH_SIZE = 3
    
    # Phase 1: 分批保存元数据
    # 1.1 分批保存教程元数据
    if tutorial_refs:
        tutorial_items = list(tutorial_refs.items())
        for i in range(0, len(tutorial_items), BATCH_SIZE):
            batch = dict(tutorial_items[i:i + BATCH_SIZE])
            async with safe_session_with_retry() as session:
                repo = RoadmapRepository(session)
                await repo.save_tutorials_batch(batch, roadmap_id)
                await session.commit()
    
    # 1.2 分批保存资源元数据
    if resource_refs:
        resource_items = list(resource_refs.items())
        for i in range(0, len(resource_items), BATCH_SIZE):
            batch = dict(resource_items[i:i + BATCH_SIZE])
            async with safe_session_with_retry() as session:
                repo = RoadmapRepository(session)
                await repo.save_resources_batch(batch, roadmap_id)
                await session.commit()
    
    # 1.3 分批保存测验元数据
    if quiz_refs:
        quiz_items = list(quiz_refs.items())
        for i in range(0, len(quiz_items), BATCH_SIZE):
            batch = dict(quiz_items[i:i + BATCH_SIZE])
            async with safe_session_with_retry() as session:
                repo = RoadmapRepository(session)
                await repo.save_quizzes_batch(batch, roadmap_id)
                await session.commit()
    
    # Phase 2: 更新 framework_data
    async with safe_session_with_retry() as session:
        repo = RoadmapRepository(session)
        roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
        
        if roadmap_metadata and roadmap_metadata.framework_data:
            # 更新 framework 中的 Concept 状态
            updated_framework = _update_framework_with_content_refs(
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
    
    # Phase 3: 更新 task 最终状态
    final_status = "partial_failure" if failed_concepts else "completed"
    final_step = "content_generation" if failed_concepts else "completed"
    
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
            },
        )
        await session.commit()
    
    logger.info(
        "save_content_results_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        final_status=final_status,
    )


def _update_framework_with_content_refs(
    framework_data: dict,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
) -> dict:
    """
    更新 framework 中所有 Concept 的内容引用字段
    
    Args:
        framework_data: 原始 framework 字典数据
        tutorial_refs: 教程引用字典
        resource_refs: 资源引用字典
        quiz_refs: 测验引用字典
        failed_concepts: 失败的概念 ID 列表
        
    Returns:
        更新后的 framework 字典
    """
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                if not concept_id:
                    continue
                
                # 更新教程相关字段
                if concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept_id]
                    concept["content_status"] = "completed"
                    concept["tutorial_id"] = tutorial_output.tutorial_id
                    concept["content_ref"] = tutorial_output.content_url
                    concept["content_summary"] = tutorial_output.summary
                    concept["content_version"] = f"v{tutorial_output.content_version}"  # ✅ 添加版本号（int → str）
                elif concept_id in failed_concepts:
                    if "content_status" not in concept or concept["content_status"] == "pending":
                        concept["content_status"] = "failed"
                
                # 更新资源相关字段
                if concept_id in resource_refs:
                    resource_output = resource_refs[concept_id]
                    concept["resources_status"] = "completed"
                    concept["resources_id"] = resource_output.id
                    concept["resources_count"] = len(resource_output.resources)
                elif concept_id in failed_concepts:
                    if "resources_status" not in concept or concept["resources_status"] == "pending":
                        concept["resources_status"] = "failed"
                
                # 更新测验相关字段
                if concept_id in quiz_refs:
                    quiz_output = quiz_refs[concept_id]
                    concept["quiz_status"] = "completed"
                    concept["quiz_id"] = quiz_output.quiz_id
                    concept["quiz_questions_count"] = quiz_output.total_questions
                elif concept_id in failed_concepts:
                    if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                        concept["quiz_status"] = "failed"
    
    return framework_data


# ============================================================
# 单个内容重试 Celery 任务
# ============================================================

@celery_app.task(
    name="app.tasks.content_generation_tasks.retry_tutorial_task",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=600,  # 10分钟
    soft_time_limit=540,  # 9分钟
    acks_late=True,
)
def retry_tutorial_task(
    self,
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    重试单个概念的教程生成（Celery 异步任务）
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        concept_data: 概念数据字典
        context_data: 上下文数据字典
        user_preferences_data: 用户偏好数据字典
    """
    logger.info(
        "retry_tutorial_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    try:
        run_async(_async_retry_tutorial(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_data=concept_data,
            context_data=context_data,
            user_preferences_data=user_preferences_data,
        ))
        logger.info(
            "retry_tutorial_task_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
    except Exception as e:
        logger.error(
            "retry_tutorial_task_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        # ✅ 如果内部函数未更新状态，在外层也尝试更新（防御性编程）
        try:
            from app.db.session import safe_session_with_retry
            from app.db.repositories.task_repo import TaskRepository
            
            async def _update_failed_status():
                async with safe_session_with_retry() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="retry_tutorial",
                        error_message=str(e)[:500],
                    )
                    await session.commit()
            
            run_async(_update_failed_status())
        except Exception:
            pass  # 静默失败，因为内部函数可能已经更新过了
        raise


async def _async_retry_tutorial(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    异步执行教程重试逻辑
    """
    from app.models.domain import Concept, LearningPreferences, TutorialGenerationInput
    from app.agents.factory import AgentFactory
    from app.services.execution_logger import execution_logger, LogCategory
    
    # 反序列化
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 1. 更新状态为 'generating'
    await _update_concept_status_in_framework_async(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="tutorial",
        status="generating",
    )
    
    # 2. 发送 WebSocket 事件：开始生成
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        current=1,
        total=1,
        content_type="tutorial",
    )
    
    try:
        # 3. 执行生成
        from app.agents.factory import get_agent_factory
        agent_factory = get_agent_factory()
        tutorial_agent = agent_factory.create_tutorial_generator()
        
        input_data = TutorialGenerationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await tutorial_agent.execute(input_data)
        
        # 4. 更新状态为 'completed' 并保存结果
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="tutorial",
            status="completed",
            result={
                "content_url": result.content_url,
                "summary": result.summary,
                "tutorial_id": result.tutorial_id,
                "content_version": f"v{result.content_version}",
            },
        )
        
        # 5. 保存教程元数据
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.tutorial_repo import TutorialRepository
            tutorial_repo = TutorialRepository(session)
            await tutorial_repo.save_tutorial(result, roadmap_id)
            await session.commit()
        
        # 6. 发送 WebSocket 事件：生成完成
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="tutorial",
            data={
                "tutorial_id": result.tutorial_id,
                "title": result.title,
                "content_url": result.content_url,
            },
        )
        
        # 7. 更新任务状态为 completed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
        
        # 8. 记录执行日志
        await execution_logger.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            step="retry_tutorial",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            message=f"✅ Tutorial regenerated for {concept.name}",
        )
        
    except Exception as e:
        logger.error(
            "retry_tutorial_execution_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        
        # 更新状态为 'failed'
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="tutorial",
            status="failed",
        )
        
        # 发送失败事件
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="tutorial",
        )
        
        # 更新任务状态为 failed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="failed",
                current_step="failed",
                error_message=str(e)[:500],
            )
            await session.commit()
        
        raise


@celery_app.task(
    name="app.tasks.content_generation_tasks.retry_resources_task",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=600,
    soft_time_limit=540,
    acks_late=True,
)
def retry_resources_task(
    self,
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    重试单个概念的资源推荐生成（Celery 异步任务）
    """
    logger.info(
        "retry_resources_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    try:
        run_async(_async_retry_resources(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_data=concept_data,
            context_data=context_data,
            user_preferences_data=user_preferences_data,
        ))
        logger.info(
            "retry_resources_task_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
    except Exception as e:
        logger.error(
            "retry_resources_task_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        # ✅ 如果内部函数未更新状态，在外层也尝试更新（防御性编程）
        try:
            from app.db.session import safe_session_with_retry
            from app.db.repositories.task_repo import TaskRepository
            
            async def _update_failed_status():
                async with safe_session_with_retry() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="retry_resources",
                        error_message=str(e)[:500],
                    )
                    await session.commit()
            
            run_async(_update_failed_status())
        except Exception:
            pass  # 静默失败，因为内部函数可能已经更新过了
        raise


async def _async_retry_resources(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    异步执行资源推荐重试逻辑
    """
    from app.models.domain import Concept, LearningPreferences, ResourceRecommendationInput
    from app.agents.factory import AgentFactory
    from app.services.execution_logger import execution_logger, LogCategory
    
    # 反序列化
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 1. 更新状态为 'generating'
    await _update_concept_status_in_framework_async(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="resources",
        status="generating",
    )
    
    # 2. 发送 WebSocket 事件：开始生成
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        current=1,
        total=1,
        content_type="resources",
    )
    
    try:
        # 3. 执行生成
        from app.agents.factory import get_agent_factory
        agent_factory = get_agent_factory()
        resource_agent = agent_factory.create_resource_recommender()
        
        input_data = ResourceRecommendationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await resource_agent.execute(input_data)
        
        # 4. 更新状态为 'completed' 并保存结果
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="resources",
            status="completed",
            result={
                "resources_id": result.id,
                "resources_count": len(result.resources),
            },
        )
        
        # 5. 保存资源元数据
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.resource_repo import ResourceRepository
            resource_repo = ResourceRepository(session)
            await resource_repo.save_resource_recommendation(result, roadmap_id)
            await session.commit()
        
        # 6. 发送 WebSocket 事件：生成完成
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="resources",
            data={
                "resources_id": result.id,
                "resources_count": len(result.resources),
            },
        )
        
        # 7. 更新任务状态为 completed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
        
        # 8. 记录执行日志
        await execution_logger.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            step="retry_resources",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            message=f"✅ Resources regenerated for {concept.name}",
        )
        
    except Exception as e:
        logger.error(
            "retry_resources_execution_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        
        # 更新状态为 'failed'
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="resources",
            status="failed",
        )
        
        # 发送失败事件
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="resources",
        )
        
        # 更新任务状态为 failed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="failed",
                current_step="failed",
                error_message=str(e)[:500],
            )
            await session.commit()
        
        raise


@celery_app.task(
    name="app.tasks.content_generation_tasks.retry_quiz_task",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=600,
    soft_time_limit=540,
    acks_late=True,
)
def retry_quiz_task(
    self,
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    重试单个概念的测验生成（Celery 异步任务）
    """
    logger.info(
        "retry_quiz_task_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    try:
        run_async(_async_retry_quiz(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_data=concept_data,
            context_data=context_data,
            user_preferences_data=user_preferences_data,
        ))
        logger.info(
            "retry_quiz_task_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
    except Exception as e:
        logger.error(
            "retry_quiz_task_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        # ✅ 如果内部函数未更新状态，在外层也尝试更新（防御性编程）
        try:
            from app.db.session import safe_session_with_retry
            from app.db.repositories.task_repo import TaskRepository
            
            async def _update_failed_status():
                async with safe_session_with_retry() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="retry_quiz",
                        error_message=str(e)[:500],
                    )
                    await session.commit()
            
            run_async(_update_failed_status())
        except Exception:
            pass  # 静默失败，因为内部函数可能已经更新过了
        raise


async def _async_retry_quiz(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    异步执行测验重试逻辑
    """
    from app.models.domain import Concept, LearningPreferences, QuizGenerationInput
    from app.agents.factory import AgentFactory
    from app.services.execution_logger import execution_logger, LogCategory
    
    # 反序列化
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 1. 更新状态为 'generating'
    await _update_concept_status_in_framework_async(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="quiz",
        status="generating",
    )
    
    # 2. 发送 WebSocket 事件：开始生成
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        current=1,
        total=1,
        content_type="quiz",
    )
    
    try:
        # 3. 执行生成
        from app.agents.factory import get_agent_factory
        agent_factory = get_agent_factory()
        quiz_agent = agent_factory.create_quiz_generator()
        
        input_data = QuizGenerationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await quiz_agent.execute(input_data)
        
        # 4. 更新状态为 'completed' 并保存结果
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="quiz",
            status="completed",
            result={
                "quiz_id": result.quiz_id,
                "quiz_questions_count": result.total_questions,
            },
        )
        
        # 5. 保存测验元数据
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.quiz_repo import QuizRepository
            quiz_repo = QuizRepository(session)
            await quiz_repo.save_quiz(result, roadmap_id)
            await session.commit()
        
        # 6. 发送 WebSocket 事件：生成完成
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="quiz",
            data={
                "quiz_id": result.quiz_id,
                "total_questions": result.total_questions,
            },
        )
        
        # 7. 更新任务状态为 completed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
        
        # 8. 记录执行日志
        await execution_logger.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            step="retry_quiz",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            message=f"✅ Quiz regenerated for {concept.name}",
        )
        
    except Exception as e:
        logger.error(
            "retry_quiz_execution_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        
        # 更新状态为 'failed'
        await _update_concept_status_in_framework_async(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="quiz",
            status="failed",
        )
        
        # 发送失败事件
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="quiz",
        )
        
        # 更新任务状态为 failed
        async with RepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="failed",
                current_step="failed",
                error_message=str(e)[:500],
            )
            await session.commit()
        
        raise


async def _update_concept_status_in_framework_async(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    status: str,
    result: dict | None = None,
):
    """
    更新路线图 framework 中特定概念的内容状态（异步版本）
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        content_type: 内容类型 ('tutorial', 'resources', 'quiz')
        status: 新状态 ('generating', 'completed', 'failed')
        result: 生成结果数据（可选）
    """
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    async with RepositoryFactory().create_session() as session:
        repo = RoadmapRepository(session)
        
        # 获取当前路线图
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata or not metadata.framework_data:
            logger.warning(
                "roadmap_not_found_for_status_update",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return
        
        framework_data = metadata.framework_data
        
        # 查找并更新概念
        status_field = f"{content_type}_status" if content_type != "tutorial" else "content_status"
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        # 更新状态
                        concept[status_field] = status
                        
                        # 如果有结果数据，更新相关字段
                        if result and status == "completed":
                            concept.update(result)
                        
                        logger.info(
                            "concept_status_updated",
                            roadmap_id=roadmap_id,
                            concept_id=concept_id,
                            content_type=content_type,
                            status=status,
                        )
                        break
        
        # 保存更新（使用 save_roadmap_metadata 确保 flag_modified 被调用）
        from app.models.domain import RoadmapFramework
        framework_obj = RoadmapFramework.model_validate(framework_data)
        await repo.save_roadmap_metadata(
            roadmap_id=roadmap_id,
            user_id=metadata.user_id,
            framework=framework_obj,
        )
        await session.commit()

