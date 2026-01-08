"""
单概念内容生成器

为单个 Concept 串行生成 Tutorial、Resource、Quiz，
完成后立即写入数据库。
"""
import asyncio
import structlog
from typing import Any

from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationInput,
    ResourceRecommendationInput,
    QuizGenerationInput,
)
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def generate_single_concept(
    task_id: str,
    roadmap_id: str,
    concept: Concept,
    concept_map: dict[str, Concept],
    preferences: LearningPreferences,
    agent_factory: Any,
    total_concepts: int,
    progress_counter: dict[str, int],
    progress_lock: asyncio.Lock,
    tutorial_refs: dict[str, Any],
    resource_refs: dict[str, Any],
    quiz_refs: dict[str, Any],
    failed_concepts: list[str],
    results_lock: asyncio.Lock,
    db_semaphore: asyncio.Semaphore,
    allocated_tavily_key: str | None = None,
) -> None:
    """
    为单个概念串行生成教程、资源、测验，完成后立即写入数据库
    
    执行顺序：
    1. Tutorial Generation（教程生成）
    2. Resource Recommendation（资源推荐）
    3. Quiz Generation（测验生成）
    4. 立即写入数据库（受信号量限制，防止连接池耗尽）
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concept: 概念
        concept_map: 概念ID到概念对象的映射
        preferences: 用户学习偏好
        agent_factory: Agent 工厂
        total_concepts: 总概念数
        progress_counter: 共享进度计数器
        progress_lock: 进度计数器保护锁
        tutorial_refs: 教程引用累积字典
        resource_refs: 资源引用累积字典
        quiz_refs: 测验引用累积字典
        failed_concepts: 失败概念累积列表
        results_lock: 结果累积保护锁
        db_semaphore: 数据库操作信号量（限制并发数据库连接数）
        allocated_tavily_key: 预分配的 Tavily API Key（可选，用于优化性能）
    """
    concept_id = concept.concept_id
    concept_name = concept.name
    
    # 更新进度计数器（线程安全）
    async with progress_lock:
        progress_counter["current"] += 1
        current_progress = progress_counter["current"]
    
    # 发送 WebSocket 事件：概念开始生成
    await notification_service.publish_concept_start(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept_name,
        current=current_progress,
        total=total_concepts,
        content_type="tutorial",
    )
    
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
    
    try:
        # ==================== 串行执行：Tutorial → Resource → Quiz ====================
        
        # 1️⃣ 生成教程
        tutorial_agent = agent_factory.create_tutorial_generator()
        tutorial_input = TutorialGenerationInput(
            concept=concept,
            user_preferences=preferences,
            context={
                "roadmap_id": roadmap_id,
                "prerequisite_details": prerequisite_details,
            },
        )
        
        logger.info(
            "generating_tutorial",
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
        )
        
        tutorial = await tutorial_agent.execute(tutorial_input)
        
        logger.info(
            "tutorial_generated",
            task_id=task_id,
            concept_id=concept_id,
            tutorial_id=tutorial.tutorial_id if tutorial and hasattr(tutorial, 'tutorial_id') else None,
        )
        
        # 2️⃣ 生成资源推荐
        resource_agent = agent_factory.create_resource_recommender(
            tavily_key=allocated_tavily_key
        )
        resource_input = ResourceRecommendationInput(
            concept=concept,
            user_preferences=preferences,
            context={"roadmap_id": roadmap_id},
        )
        
        logger.info(
            "generating_resources",
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
        )
        
        resource = await resource_agent.execute(resource_input)
        
        logger.info(
            "resources_generated",
            task_id=task_id,
            concept_id=concept_id,
            resources_count=len(resource.resources) if resource and hasattr(resource, 'resources') else 0,
        )
        
        # 3️⃣ 生成测验
        quiz_agent = agent_factory.create_quiz_generator()
        quiz_input = QuizGenerationInput(
            concept=concept,
            user_preferences=preferences,
            context={"roadmap_id": roadmap_id},
        )
        
        logger.info(
            "generating_quiz",
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
        )
        
        quiz = await quiz_agent.execute(quiz_input)
        
        logger.info(
            "quiz_generated",
            task_id=task_id,
            concept_id=concept_id,
            questions_count=len(quiz.questions) if quiz and hasattr(quiz, 'questions') else 0,
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
        
        # ==================== 立即写入数据库（以 Concept 为单位） ====================
        logger.info(
            "saving_concept_to_database",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
        
        from app.db.celery_session import get_celery_session
        
        # 🔧 使用信号量限制并发数据库连接数
        # 防止 30+ 个 Concept 同时打开数据库会话导致连接池耗尽
        async with db_semaphore:
            logger.debug(
                "db_semaphore_acquired",
                concept_id=concept_id,
                message="获取数据库操作许可",
            )
            
            async with get_celery_session() as session:
                # 保存教程
                if tutorial:
                    try:
                        from app.crud.crud_tutorial import get_tutorial_crud
                        tutorial_crud = get_tutorial_crud()
                        await tutorial_crud.save_tutorial(
                            session,
                            tutorial_output=tutorial,
                            roadmap_id=roadmap_id,
                        )
                        logger.debug(
                            "tutorial_saved",
                            concept_id=concept_id,
                            tutorial_id=tutorial.tutorial_id if hasattr(tutorial, 'tutorial_id') else None,
                        )
                    except Exception as e:
                        logger.error("tutorial_save_failed", concept_id=concept_id, error=str(e))
                
                # 保存资源
                if resource:
                    try:
                        from app.crud.crud_resource import get_resource_crud
                        resource_crud = get_resource_crud()
                        await resource_crud.save_resource_recommendation(
                            session,
                            resource_output=resource,
                            roadmap_id=roadmap_id,
                        )
                        logger.debug(
                            "resources_saved",
                            concept_id=concept_id,
                            resources_count=len(resource.resources) if hasattr(resource, 'resources') else 0,
                        )
                    except Exception as e:
                        logger.error("resources_save_failed", concept_id=concept_id, error=str(e))
                
                # 保存测验
                if quiz:
                    try:
                        from app.crud.crud_quiz import get_quiz_crud
                        quiz_crud = get_quiz_crud()
                        await quiz_crud.save_quiz(
                            session,
                            quiz_output=quiz,
                            roadmap_id=roadmap_id,
                        )
                        logger.debug(
                            "quiz_saved",
                            concept_id=concept_id,
                            questions_count=len(quiz.questions) if hasattr(quiz, 'questions') else 0,
                        )
                    except Exception as e:
                        logger.error("quiz_save_failed", concept_id=concept_id, error=str(e))
                
                # 🆕 更新 ConceptMetadata（追踪内容生成状态）
                from app.crud.crud_concept import get_concept_crud
                concept_crud = get_concept_crud()
                
                # 更新三项内容的状态
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="tutorial",
                    status="completed" if tutorial else "failed",
                    content_id=tutorial.tutorial_id if tutorial and hasattr(tutorial, 'tutorial_id') else None,
                )
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="resources",
                    status="completed" if resource else "failed",
                    content_id=resource.id if resource and hasattr(resource, 'id') else None,
                )
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="quiz",
                    status="completed" if quiz else "failed",
                    content_id=quiz.quiz_id if quiz and hasattr(quiz, 'quiz_id') else None,
                )
                
                # 检查是否全部完成
                concept_meta = await concept_crud.get_by_concept_id(session, concept_id)
                is_all_complete = (concept_meta and concept_meta.overall_status == "completed")
                
                await session.commit()
            
            logger.debug(
                "db_semaphore_released",
                concept_id=concept_id,
                message="释放数据库操作许可",
            )
        
        logger.info(
            "concept_saved_to_database",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
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
        
        # 🆕 如果三项内容全部完成，发送新的完整完成事件
        if is_all_complete:
            await notification_service.publish_concept_all_content_complete(
                task_id=task_id,
                concept_id=concept_id,
                concept_name=concept_name,
                data={
                    "tutorial_id": tutorial.tutorial_id if tutorial and hasattr(tutorial, 'tutorial_id') else None,
                    "resources_id": resource.id if resource and hasattr(resource, 'id') else None,
                    "quiz_id": quiz.quiz_id if quiz and hasattr(quiz, 'quiz_id') else None,
                }
            )
        
        # 累积到最终结果（线程安全）
        async with results_lock:
            if tutorial:
                tutorial_refs[concept_id] = tutorial
            if resource:
                resource_refs[concept_id] = resource
            if quiz:
                quiz_refs[concept_id] = quiz
    
    except Exception as e:
        logger.error(
            "concept_generation_failed",
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
            error=str(e),
            exc_info=True,
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
        
        # 累积失败的概念（线程安全）
        # 使用细粒度格式记录失败（因为整个 Concept 生成失败，三项都失败）
        async with results_lock:
            failed_concepts.append(f"{concept_id}:tutorial")
            failed_concepts.append(f"{concept_id}:resources")
            failed_concepts.append(f"{concept_id}:quiz")
        
        # 🆕 更新 ConceptMetadata 为失败状态
        try:
            from app.db.celery_session import get_celery_session
            from app.crud.crud_concept import get_concept_crud
            
            async with get_celery_session() as session:
                concept_crud = get_concept_crud()
                # 标记所有三项为失败（因为整个 Concept 生成失败了）
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="tutorial",
                    status="failed",
                )
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="resources",
                    status="failed",
                )
                await concept_crud.update_content_status(
                    session,
                    concept_id=concept_id,
                    content_type="quiz",
                    status="failed",
                )
                await session.commit()
        except Exception as meta_error:
            logger.error(
                "concept_metadata_update_failed",
                concept_id=concept_id,
                error=str(meta_error),
            )
        
        # 发送失败通知
        await notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept_id,
            concept_name=concept_name,
            error=str(e)[:200],
            content_type="tutorial",
        )
        
        # 不要 raise，让其他 Concept 继续执行

