"""
内容重试 Celery 任务

提供单个 Concept 内容重试功能：
- retry_tutorial_task: 重试教程生成
- retry_resources_task: 重试资源推荐
- retry_quiz_task: 重试测验生成
"""
import structlog

from app.core.celery_app import celery_app
# 使用 Celery 专用的数据库连接管理，避免 Fork 进程继承问题
from app.db.celery_session import CeleryRepositoryFactory
from app.services.notification_service import notification_service
from app.tasks.content_utils import run_async, update_concept_status_in_framework

logger = structlog.get_logger()


# ============================================================
# 教程重试任务
# ============================================================

@celery_app.task(
    name="app.tasks.content_retry_tasks.retry_tutorial_task",
    queue="content_generation",
    bind=True,
    max_retries=0,
    time_limit=600,
    soft_time_limit=540,
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
        _update_task_status_on_failure(task_id, "retry_tutorial", str(e))
        raise


async def _async_retry_tutorial(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """异步执行教程重试逻辑"""
    from app.models.domain import Concept, LearningPreferences, TutorialGenerationInput
    from app.agents.factory import get_agent_factory
    from app.services.execution_logger import execution_logger, LogCategory
    
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 1. 更新状态为 'generating'
    await update_concept_status_in_framework(
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
        agent_factory = get_agent_factory()
        tutorial_agent = agent_factory.create_tutorial_generator()
        
        input_data = TutorialGenerationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await tutorial_agent.execute(input_data)
        
        # 4. 更新状态为 'completed' 并保存结果
        await update_concept_status_in_framework(
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
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.tutorial_repo import TutorialRepository
            tutorial_repo = TutorialRepository(session)
            await tutorial_repo.save_tutorial(result, roadmap_id)
            
            # 🆕 更新 ConceptMetadata
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="tutorial",
                status="completed",
                content_id=result.tutorial_id,
            )
            
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
        async with CeleryRepositoryFactory().create_session() as session:
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
        
        await update_concept_status_in_framework(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="tutorial",
            status="failed",
        )
        
        # 🆕 更新 ConceptMetadata 为失败状态
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="tutorial",
                status="failed",
            )
            await session.commit()
        
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="tutorial",
        )
        
        async with CeleryRepositoryFactory().create_session() as session:
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


# ============================================================
# 资源重试任务
# ============================================================

@celery_app.task(
    name="app.tasks.content_retry_tasks.retry_resources_task",
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
    """重试单个概念的资源推荐生成（Celery 异步任务）"""
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
        _update_task_status_on_failure(task_id, "retry_resources", str(e))
        raise


async def _async_retry_resources(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """异步执行资源推荐重试逻辑"""
    from app.models.domain import Concept, LearningPreferences, ResourceRecommendationInput
    from app.agents.factory import get_agent_factory
    from app.services.execution_logger import execution_logger, LogCategory
    
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    await update_concept_status_in_framework(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="resources",
        status="generating",
    )
    
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        current=1,
        total=1,
        content_type="resources",
    )
    
    try:
        agent_factory = get_agent_factory()
        resource_agent = agent_factory.create_resource_recommender()
        
        input_data = ResourceRecommendationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await resource_agent.execute(input_data)
        
        await update_concept_status_in_framework(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="resources",
            status="completed",
            result={
                "resources_id": result.id,
                "resources_count": len(result.resources),
            },
        )
        
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.resource_repo import ResourceRepository
            resource_repo = ResourceRepository(session)
            await resource_repo.save_resource_recommendation(result, roadmap_id)
            
            # 🆕 更新 ConceptMetadata
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="resources",
                status="completed",
                content_id=result.id,
            )
            
            await session.commit()
        
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
        
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
        
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
        
        await update_concept_status_in_framework(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="resources",
            status="failed",
        )
        
        # 🆕 更新 ConceptMetadata 为失败状态
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="resources",
                status="failed",
            )
            await session.commit()
        
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="resources",
        )
        
        async with CeleryRepositoryFactory().create_session() as session:
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


# ============================================================
# 测验重试任务
# ============================================================

@celery_app.task(
    name="app.tasks.content_retry_tasks.retry_quiz_task",
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
    """重试单个概念的测验生成（Celery 异步任务）"""
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
        _update_task_status_on_failure(task_id, "retry_quiz", str(e))
        raise


async def _async_retry_quiz(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """异步执行测验重试逻辑"""
    from app.models.domain import Concept, LearningPreferences, QuizGenerationInput
    from app.agents.factory import get_agent_factory
    from app.services.execution_logger import execution_logger, LogCategory
    
    concept = Concept.model_validate(concept_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    await update_concept_status_in_framework(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="quiz",
        status="generating",
    )
    
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        current=1,
        total=1,
        content_type="quiz",
    )
    
    try:
        agent_factory = get_agent_factory()
        quiz_agent = agent_factory.create_quiz_generator()
        
        input_data = QuizGenerationInput(
            concept=concept,
            context=context_data,
            user_preferences=preferences,
        )
        
        result = await quiz_agent.execute(input_data)
        
        await update_concept_status_in_framework(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="quiz",
            status="completed",
            result={
                "quiz_id": result.quiz_id,
                "quiz_questions_count": result.total_questions,
            },
        )
        
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.quiz_repo import QuizRepository
            quiz_repo = QuizRepository(session)
            await quiz_repo.save_quiz(result, roadmap_id)
            
            # 🆕 更新 ConceptMetadata
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="quiz",
                status="completed",
                content_id=result.quiz_id,
            )
            
            await session.commit()
        
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
        
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.task_repo import TaskRepository
            task_repo = TaskRepository(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
        
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
        
        await update_concept_status_in_framework(
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="quiz",
            status="failed",
        )
        
        # 🆕 更新 ConceptMetadata 为失败状态
        async with CeleryRepositoryFactory().create_session() as session:
            from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
            concept_meta_repo = ConceptMetadataRepository(session)
            await concept_meta_repo.update_content_status(
                concept_id=concept_id,
                content_type="quiz",
                status="failed",
            )
            await session.commit()
        
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            error=str(e),
            content_type="quiz",
        )
        
        async with CeleryRepositoryFactory().create_session() as session:
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


# ============================================================
# 辅助函数
# ============================================================

def _update_task_status_on_failure(task_id: str, step: str, error: str):
    """在任务失败时更新任务状态（防御性编程）"""
    try:
        from app.db.celery_session import celery_safe_session_with_retry as safe_session_with_retry
        from app.db.repositories.task_repo import TaskRepository
        
        async def _update():
            async with safe_session_with_retry() as session:
                task_repo = TaskRepository(session)
                await task_repo.update_task_status(
                    task_id=task_id,
                    status="failed",
                    current_step=step,
                    error_message=error[:500],
                )
                await session.commit()
        
        run_async(_update())
    except Exception:
        pass  # 静默失败

