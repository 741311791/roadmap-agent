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
    TutorialGenerationInput,
    ResourceRecommendationInput,
    QuizGenerationInput,
)
from app.services.shared.notification_service import notification_service

logger = structlog.get_logger()


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
    生成所有内容的协调任务（同步入口）
    
    职责：
    1. 从数据库获取 Framework
    2. 提取所有 Concepts
    3. 创建并发子任务组
    4. 更新 Task 表的 content_generation_celery_id
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 主任务 ID（用于进度通知）
        user_id: 用户 ID
        
    Returns:
        协调任务结果
    """
    logger.info(
        "content_generation_coordinator_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=self.request.id,
    )
    
    try:
        # 获取 Framework 和 Concepts
        import asyncio
        framework, concepts, user_preferences = asyncio.run(
            _get_framework_and_concepts(roadmap_id, user_id)
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
        
        logger.info(
            "creating_content_generation_tasks",
            task_id=task_id,
            roadmap_id=roadmap_id,
            total_concepts=len(concepts),
        )
        
        # 创建并发任务组（使用 chord 实现 Fan-Out + Callback）
        callback = finalize_content_generation.s(
            roadmap_id=roadmap_id,
            task_id=task_id,
        )
        
        job = chord([
            generate_concept_content_task.s(
                concept_data=concept.model_dump(),
                user_preferences_data=user_preferences.model_dump(),
                roadmap_id=roadmap_id,
                task_id=task_id,
            )
            for concept in concepts
        ])(callback)
        
        logger.info(
            "content_generation_tasks_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            chord_id=job.id,
            total_concepts=len(concepts),
        )
        
        return {
            "status": "processing",
            "chord_id": job.id,
            "total_concepts": len(concepts),
        }
        
    except Exception as e:
        logger.error(
            "content_generation_coordinator_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            error=str(e),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="generate_concept_content",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,  # 5 分钟硬超时
    soft_time_limit=270,  # 4.5 分钟软超时
    queue="content_generation",
)
def generate_concept_content_task(
    self,
    concept_data: Dict[str, Any],
    user_preferences_data: Dict[str, Any],
    roadmap_id: str,
    task_id: str,
) -> Dict[str, Any]:
    """
    生成单个 Concept 的所有内容
    
    职责：
    1. 并发生成 Tutorial、Resource、Quiz
    2. 保存到数据库
    3. 发送进度通知
    4. 失败自动重试（最多 3 次）
    
    Args:
        concept_data: Concept 序列化数据
        user_preferences_data: 用户偏好序列化数据
        roadmap_id: 路线图 ID
        task_id: 主任务 ID
        
    Returns:
        生成结果
        
    Raises:
        Retry: 失败时自动重试
    """
    concept = Concept(**concept_data)
    user_preferences = LearningPreferences(**user_preferences_data)
    concept_id = concept.concept_id
    
    logger.info(
        "concept_content_generation_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        celery_task_id=self.request.id,
        retry_count=self.request.retries,
    )
    
    try:
        # 执行异步生成
        import asyncio
        result = asyncio.run(
            _generate_and_save_concept_content(
                concept=concept,
                user_preferences=user_preferences,
                roadmap_id=roadmap_id,
                task_id=task_id,
            )
        )
        
        logger.info(
            "concept_content_generation_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            tutorial_status=result.get("tutorial_status"),
            resource_status=result.get("resource_status"),
            quiz_status=result.get("quiz_status"),
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "concept_content_generation_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(exc),
            retry_count=self.request.retries,
            exc_info=True,
        )
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.warning(
                "retrying_concept_content_generation",
                task_id=task_id,
                concept_id=concept_id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=exc)
        
        # 达到最大重试次数，标记为失败
        logger.error(
            "concept_content_generation_max_retries_exceeded",
            task_id=task_id,
            concept_id=concept_id,
            max_retries=self.max_retries,
        )
        
        return {
            "concept_id": concept_id,
            "status": "failed",
            "error": str(exc),
        }


@celery_app.task(
    name="finalize_content_generation",
    queue="content_generation",
)
def finalize_content_generation(
    results: list[Dict[str, Any]],
    roadmap_id: str,
    task_id: str,
) -> Dict[str, Any]:
    """
    最终汇总任务（Chord Callback）
    
    职责：
    1. 汇总所有 Concept 的生成结果
    2. 更新 Task 最终状态
    3. 发送完成通知
    
    Args:
        results: 所有子任务的结果列表
        roadmap_id: 路线图 ID
        task_id: 主任务 ID
        
    Returns:
        最终汇总结果
    """
    logger.info(
        "content_generation_finalization_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_results=len(results),
    )
    
    # 统计结果
    success_count = len([r for r in results if r.get("status") == "success"])
    failed_count = len([r for r in results if r.get("status") == "failed"])
    
    # 确定最终状态
    if failed_count == 0:
        final_status = "completed"
    elif success_count > 0:
        final_status = "partial_failure"
    else:
        final_status = "failed"
    
    # 更新 Task 状态
    import asyncio
    asyncio.run(_update_task_content_status(
        task_id=task_id,
        status=final_status,
    ))
    
    # 发送完成通知
    asyncio.run(notification_service.publish_completed(
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorials_count=success_count,
        failed_count=failed_count,
    ))
    
    logger.info(
        "content_generation_finalization_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        final_status=final_status,
        success_count=success_count,
        failed_count=failed_count,
    )
    
    return {
        "status": final_status,
        "total": len(results),
        "success": success_count,
        "failed": failed_count,
    }


# ============================================================
# 辅助函数
# ============================================================

async def _get_framework_and_concepts(
    roadmap_id: str,
    user_id: str,
) -> tuple[Any, list[Concept], LearningPreferences]:
    """
    从数据库获取 Framework 和 Concepts
    
    Returns:
        (framework, concepts, user_preferences)
    """
    async with get_celery_session() as session:
        # 获取 RoadmapMetadata
        roadmap_crud = get_roadmap_crud()
        roadmap_metadata = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not roadmap_metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        # 解析 Framework
        from app.models.domain import RoadmapFramework
        framework = RoadmapFramework(**roadmap_metadata.framework_data)
        
        # 提取所有 Concepts
        concepts = []
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    concepts.append(concept)
        
        # 获取用户偏好（从 Intent Analysis 获取）
        from app.crud.crud_intent_analysis import get_intent_analysis_crud
        intent_crud = get_intent_analysis_crud()
        intent_analysis = await intent_crud.get_by_roadmap_id(session, roadmap_id)
        
        if intent_analysis and intent_analysis.analysis_result:
            # 从 intent_analysis 提取用户偏好
            analysis_data = intent_analysis.analysis_result
            user_preferences = LearningPreferences(
                learning_goal=analysis_data.get("learning_goal", "学习目标"),
                available_hours_per_week=analysis_data.get("available_hours_per_week", 10),
                motivation=analysis_data.get("motivation", "学习"),
                current_level=analysis_data.get("current_level", "beginner"),
                career_background=analysis_data.get("career_background", "默认背景"),
            )
        else:
            # Fallback: 使用默认值
            user_preferences = LearningPreferences(
                learning_goal="默认学习目标",
                available_hours_per_week=10,
                motivation="学习",
                current_level="beginner",
                career_background="默认背景",
            )
        
        return framework, concepts, user_preferences


async def _generate_and_save_concept_content(
    concept: Concept,
    user_preferences: LearningPreferences,
    roadmap_id: str,
    task_id: str,
) -> Dict[str, Any]:
    """
    生成并保存单个 Concept 的所有内容
    
    Returns:
        生成结果
    """
    concept_id = concept.concept_id
    agent_factory = AgentFactory(settings)
    
    results = {
        "concept_id": concept_id,
        "status": "success",
        "tutorial_status": "skipped",
        "resource_status": "skipped",
        "quiz_status": "skipped",
    }
    
    # 1. 生成 Tutorial
    try:
        tutorial_agent = agent_factory.create_tutorial_generator()
        tutorial = await tutorial_agent.generate(
            concept=concept,
            context={},
            user_preferences=user_preferences,
        )
        
        # 保存到数据库
        async with get_celery_session() as session:
            from app.crud.crud_tutorial import get_tutorial_crud
            tutorial_crud = get_tutorial_crud()
            await tutorial_crud.save_tutorial(
                session=session,
                tutorial_output=tutorial,
                roadmap_id=roadmap_id,
            )
        
        results["tutorial_status"] = "success"
        results["tutorial_id"] = tutorial.tutorial_id
        
        # 发送进度通知
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="tutorial",
        )
        
        logger.info(
            "tutorial_generated_and_saved",
            task_id=task_id,
            concept_id=concept_id,
            tutorial_id=tutorial.tutorial_id,
        )
        
    except Exception as e:
        logger.error(
            "tutorial_generation_failed",
            task_id=task_id,
            concept_id=concept_id,
            error=str(e),
            exc_info=True,
        )
        results["tutorial_status"] = "failed"
        results["status"] = "partial_failure"
    
    # 2. 生成 Resource
    try:
        resource_agent = agent_factory.create_resource_recommender()
        resource_input = ResourceRecommendationInput(
            concept=concept,
            context={},
            user_preferences=user_preferences,
        )
        resource = await resource_agent.execute(resource_input)
        
        # 保存到数据库
        async with get_celery_session() as session:
            from app.crud.crud_resource import get_resource_crud
            resource_crud = get_resource_crud()
            await resource_crud.save_resource_recommendation(
                session=session,
                resource_output=resource,
                roadmap_id=roadmap_id,
            )
        
        results["resource_status"] = "success"
        results["resources_id"] = resource.id
        
        # 发送进度通知
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="resource",
        )
        
        logger.info(
            "resource_generated_and_saved",
            task_id=task_id,
            concept_id=concept_id,
            resources_id=resource.id,
            resource_count=len(resource.resources),
        )
        
    except Exception as e:
        logger.error(
            "resource_generation_failed",
            task_id=task_id,
            concept_id=concept_id,
            error=str(e),
            exc_info=True,
        )
        results["resource_status"] = "failed"
        results["status"] = "partial_failure"
    
    # 3. 生成 Quiz
    try:
        quiz_agent = agent_factory.create_quiz_generator()
        quiz = await quiz_agent.generate(
            concept=concept,
            context={},
            user_preferences=user_preferences,
        )
        
        # 保存到数据库
        async with get_celery_session() as session:
            from app.crud.crud_quiz import get_quiz_crud
            quiz_crud = get_quiz_crud()
            await quiz_crud.save_quiz(
                session=session,
                quiz_output=quiz,
                roadmap_id=roadmap_id,
            )
        
        results["quiz_status"] = "success"
        results["quiz_id"] = quiz.quiz_id
        
        # 发送进度通知
        await notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            content_type="quiz",
        )
        
        logger.info(
            "quiz_generated_and_saved",
            task_id=task_id,
            concept_id=concept_id,
            quiz_id=quiz.quiz_id,
            question_count=len(quiz.questions),
        )
        
    except Exception as e:
        logger.error(
            "quiz_generation_failed",
            task_id=task_id,
            concept_id=concept_id,
            error=str(e),
            exc_info=True,
        )
        results["quiz_status"] = "failed"
        results["status"] = "partial_failure"
    
    return results


async def _update_task_content_status(
    task_id: str,
    status: str,
) -> None:
    """
    更新 Task 的内容生成状态
    
    Args:
        task_id: 任务 ID
        status: 状态（completed | partial_failure | failed）
    """
    async with get_celery_session() as session:
        task_crud = get_task_crud()
        await task_crud.update_content_generation_status(
            session=session,
            task_id=task_id,
            status=status,
        )
        
        logger.info(
            "task_content_status_updated",
            task_id=task_id,
            status=status,
        )
