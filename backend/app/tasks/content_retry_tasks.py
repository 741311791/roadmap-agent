"""
内容重试 Celery 任务（重构版）

使用ContentService统一处理所有重试逻辑，消除重复代码
"""
import structlog

from app.core.celery_app import celery_app
from app.db.celery_session import CeleryRepositoryFactory
from app.tasks.content_utils import run_async

logger = structlog.get_logger()


# ============================================================
# 统一的重试任务处理器
# ============================================================

async def _execute_content_retry(
    task_id: str,
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    concept_data: dict,
    context_data: dict,
    user_preferences_data: dict,
):
    """
    统一的内容重试执行逻辑
    
    Args:
        task_id: 任务ID
        roadmap_id: 路线图ID
        concept_id: 概念ID
        content_type: 内容类型 (tutorial/resources/quiz)
        concept_data: 概念数据
        context_data: 上下文数据
        user_preferences_data: 用户偏好数据
    """
    from app.services.content_service import get_content_service
    from app.services.execution_logger import execution_logger, LogCategory
    from app.models.domain import LearningPreferences, ConceptRetryRequest
    
    content_service = get_content_service()
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    logger.info(
        "content_retry_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type=content_type,
    )
    
    # 记录开始日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.WORKFLOW,
        step="content_generation",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        message=f"🔄 Starting {content_type} retry for concept",
    )
    
    try:
        # 使用ContentService统一处理
        async with CeleryRepositoryFactory().create_session() as session:
            request = ConceptRetryRequest(
                preferences=preferences,
                retry_reason=f"Retry via task {task_id}",
            )
            
            result = await content_service.retry_content(
                session=session,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
                request=request,
            )
            
            await session.commit()
        
        if result.success:
            # 更新任务状态为completed
            async with CeleryRepositoryFactory().create_session() as session:
                from app.crud.crud_task import get_task_crud
                task_crud = get_task_crud()
                task = await task_crud.get_by_task_id(session, task_id)
                if task:
                    await task_crud.update(
                        session,
                        db_obj=task,
                        obj_in={
                            "status": "completed",
                            "current_step": "completed",
                        }
                    )
                    await session.commit()
            
            # 记录成功日志
            await execution_logger.info(
                task_id=task_id,
                category=LogCategory.WORKFLOW,
                step="content_generation",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                message=f"✅ {content_type.capitalize()} regenerated successfully",
            )
            
            logger.info(
                "content_retry_completed",
                task_id=task_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
            )
        else:
            raise Exception(result.message)
            
    except Exception as e:
        logger.error(
            "content_retry_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
            error=str(e),
            exc_info=True,
        )
        
        # 记录失败日志
        await execution_logger.error(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            step="content_generation",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            message=f"❌ {content_type.capitalize()} retry failed: {str(e)[:100]}",
            details={"error": str(e)},
        )
        
        # 更新任务状态为failed
        try:
            async with CeleryRepositoryFactory().create_session() as session:
                from app.crud.crud_task import get_task_crud
                task_crud = get_task_crud()
                task = await task_crud.get_by_task_id(session, task_id)
                if task:
                    await task_crud.update(
                        session,
                        db_obj=task,
                        obj_in={
                            "status": "failed",
                            "current_step": "failed",
                            "error_message": str(e)[:500],
                        }
                    )
                    await session.commit()
        except Exception as update_error:
            logger.error(
                "task_status_update_failed",
                task_id=task_id,
                error=str(update_error),
            )
        
        raise


# ============================================================
# Celery任务定义
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
    
    重构说明：使用ContentService统一处理，消除重复代码
    """
    logger.info(
        "retry_tutorial_task_invoked",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    run_async(_execute_content_retry(
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="tutorial",
        concept_data=concept_data,
        context_data=context_data,
        user_preferences_data=user_preferences_data,
    ))


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
    """
    重试单个概念的资源推荐生成（Celery 异步任务）
    
    重构说明：使用ContentService统一处理，消除重复代码
    """
    logger.info(
        "retry_resources_task_invoked",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    run_async(_execute_content_retry(
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="resources",
        concept_data=concept_data,
        context_data=context_data,
        user_preferences_data=user_preferences_data,
    ))


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
    """
    重试单个概念的测验生成（Celery 异步任务）
    
    重构说明：使用ContentService统一处理，消除重复代码
    """
    logger.info(
        "retry_quiz_task_invoked",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    run_async(_execute_content_retry(
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="quiz",
        concept_data=concept_data,
        context_data=context_data,
        user_preferences_data=user_preferences_data,
    ))
