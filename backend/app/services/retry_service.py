"""
重试服务

处理失败内容的重试逻辑，包括后台任务执行、进度通知、数据库更新等。
"""
import asyncio
import time
import structlog

from app.models.domain import (
    LearningPreferences,
    Concept,
    TutorialGenerationInput,
    ResourceRecommendationInput,
    QuizGenerationInput,
    RoadmapFramework,
)
from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.agents.resource_recommender import ResourceRecommenderAgent
from app.agents.quiz_generator import QuizGeneratorAgent
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger
from app.config.settings import settings

logger = structlog.get_logger()


async def execute_retry_failed_task(
    retry_task_id: str,
    roadmap_id: str,
    items_to_retry: dict,
    user_preferences: LearningPreferences,
    user_id: str,
):
    """
    后台执行重试失败任务
    
    Args:
        retry_task_id: 重试任务 ID（用于 WebSocket 订阅）
        roadmap_id: 路线图 ID
        items_to_retry: 要重试的项目 {"tutorial": [...], "resources": [...], "quiz": [...]}
        user_preferences: 用户偏好
        user_id: 用户 ID（用于日志记录）
    """
    # 记录任务开始时间（用于计算总耗时）
    task_start_time = time.time()
    
    logger.info(
        "retry_failed_task_started",
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        items_count={k: len(v) for k, v in items_to_retry.items()},
    )
    
    # 记录 ExecutionLog：重试任务开始
    await execution_logger.log_workflow_start(
        task_id=retry_task_id,
        step="content_generation",  # 使用前端Content节点对应的步骤
        message="Starting retry of failed content",
        roadmap_id=roadmap_id,
        details={
            "user_id": user_id,
            "items_by_type": {k: len(v) for k, v in items_to_retry.items()},
            "total_items": sum(len(v) for v in items_to_retry.values()),
        },
    )
    
    # 发布重试开始事件
    await notification_service.publish_progress(
        task_id=retry_task_id,
        step="content_generation",  # 使用前端Content节点对应的步骤
        status="processing",
        message="Starting retry of failed items",
        extra_data={
            "roadmap_id": roadmap_id,
            "items_by_type": {k: len(v) for k, v in items_to_retry.items()},
        },
    )
    
    # 创建 Agents
    tutorial_generator = TutorialGeneratorAgent() if "tutorial" in items_to_retry else None
    resource_recommender = ResourceRecommenderAgent() if "resources" in items_to_retry else None
    quiz_generator = QuizGeneratorAgent() if "quiz" in items_to_retry else None
    
    # 统计结果
    success_count = 0
    failed_count = 0
    results = []
    
    # 并发控制已移除：改用 Celery --concurrency 参数控制全局并发
    # semaphore = asyncio.Semaphore(settings.PARALLEL_TUTORIAL_LIMIT)
    
    async def retry_single_item(content_type: str, item: dict, current: int, total: int) -> dict:
        """重试单个项目"""
        nonlocal success_count, failed_count
        
        concept_id = item["concept_id"]
        concept_data = item["concept_data"]
        context = item["context"]
        item_start_time = time.time()
        
        # Agent 名称映射
        agent_name_map = {
            "tutorial": "TutorialGenerator",
            "resources": "ResourceRecommender",
            "quiz": "QuizGenerator",
        }
        agent_name = agent_name_map.get(content_type, "UnknownAgent")
        
        # 构建 Concept 对象
        concept = Concept(
            concept_id=concept_data.get("concept_id"),
            name=concept_data.get("name"),
            description=concept_data.get("description", ""),
            estimated_hours=concept_data.get("estimated_hours", 1.0),
            prerequisites=concept_data.get("prerequisites", []),
            difficulty=concept_data.get("difficulty", "medium"),
            keywords=concept_data.get("keywords", []),
        )
        
        # 记录 ExecutionLog：单个项目开始
        await execution_logger.log_agent_start(
            task_id=retry_task_id,
            agent_name=agent_name,
            message=f"Starting retry of {content_type} content",
            concept_id=concept_id,
            details={
                "concept_name": concept.name,
                "content_type": content_type,
                "current": current,
                "total": total,
            },
        )
        
        # 发布概念开始事件
        await notification_service.publish_concept_start(
            task_id=retry_task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            current=current,
            total=total,
        )
        
        try:
            # 移除 semaphore 包装，直接执行
            if content_type == "tutorial" and tutorial_generator:
                input_data = TutorialGenerationInput(
                    concept=concept,
                    context=context,
                    user_preferences=user_preferences,
                )
                result = await tutorial_generator.execute(input_data)
                output_data = {
                    "tutorial_id": result.tutorial_id,
                    "content_url": result.content_url,
                }
                
            elif content_type == "resources" and resource_recommender:
                input_data = ResourceRecommendationInput(
                    concept=concept,
                    context=context,
                    user_preferences=user_preferences,
                )
                result = await resource_recommender.execute(input_data)
                output_data = {
                    "resources_id": result.id,
                    "resources_count": len(result.resources),
                }
                
            elif content_type == "quiz" and quiz_generator:
                input_data = QuizGenerationInput(
                    concept=concept,
                    context=context,
                    user_preferences=user_preferences,
                )
                result = await quiz_generator.execute(input_data)
                output_data = {
                    "quiz_id": result.quiz_id,
                    "questions_count": result.total_questions,
                }
            else:
                raise ValueError(f"Unknown content type: {content_type}")
            
            success_count += 1
            item_duration_ms = int((time.time() - item_start_time) * 1000)
            
            # 记录 ExecutionLog：单个项目成功
            await execution_logger.log_agent_complete(
                task_id=retry_task_id,
                agent_name=agent_name,
                message=f"Retry of {content_type} content succeeded",
                duration_ms=item_duration_ms,
                concept_id=concept_id,
                details={
                    "concept_name": concept.name,
                    "content_type": content_type,
                    "output": output_data,
                },
            )
            
            # 发布概念完成事件（使用标准事件）
            await notification_service.publish_concept_complete(
                task_id=retry_task_id,
                concept_id=concept_id,
                concept_name=concept.name,
                data=output_data,
            )
            
            return {
                "concept_id": concept_id,
                "content_type": content_type,
                "success": True,
                "result": result,
            }
            
        except Exception as e:
            failed_count += 1
            item_duration_ms = int((time.time() - item_start_time) * 1000)
            
            logger.error(
                "retry_item_failed",
                retry_task_id=retry_task_id,
                concept_id=concept_id,
                content_type=content_type,
                error=str(e),
            )
            
            # 记录 ExecutionLog：单个项目失败
            await execution_logger.log_agent_error(
                task_id=retry_task_id,
                agent_name=agent_name,
                message=f"Retry of {content_type} content failed",
                error=str(e),
                concept_id=concept_id,
                details={
                    "concept_name": concept.name,
                    "content_type": content_type,
                    "duration_ms": item_duration_ms,
                },
            )
            
            # 发布概念失败事件（使用标准事件）
            await notification_service.publish_concept_failed(
                task_id=retry_task_id,
                concept_id=concept_id,
                concept_name=concept.name,
                error=str(e),
            )
            
            return {
                "concept_id": concept_id,
                "content_type": content_type,
                "success": False,
                "error": str(e),
            }
    
    # 收集所有重试任务
    all_tasks = []
    total_items = sum(len(items) for items in items_to_retry.values())
    current = 0
    
    for content_type, items in items_to_retry.items():
        for item in items:
            current += 1
            all_tasks.append(retry_single_item(content_type, item, current, total_items))
    
    # 并行执行
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    
    # 初始化 remaining_failed（防止后面引用时未定义）
    remaining_failed = {
        "tutorial": 0,
        "resources": 0,
        "quiz": 0,
    }
    
    # 更新数据库中的框架数据
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
        
        if roadmap_metadata:
            framework_data = roadmap_metadata.framework_data
            
            # 更新成功的概念状态
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    concept_id = result["concept_id"]
                    content_type = result["content_type"]
                    output = result.get("result")
                    
                    # 遍历框架更新对应概念的状态
                    for stage in framework_data.get("stages", []):
                        for module in stage.get("modules", []):
                            for concept in module.get("concepts", []):
                                if concept.get("concept_id") == concept_id:
                                    if content_type == "tutorial" and output:
                                        concept["content_status"] = "completed"
                                        concept["content_ref"] = output.content_url
                                        concept["content_summary"] = output.summary
                                    elif content_type == "resources" and output:
                                        concept["resources_status"] = "completed"
                                        concept["resources_id"] = output.id
                                        concept["resources_count"] = len(output.resources)
                                    elif content_type == "quiz" and output:
                                        concept["quiz_status"] = "completed"
                                        concept["quiz_id"] = output.quiz_id
                                        concept["quiz_questions_count"] = output.total_questions
            
            # 保存更新后的框架
            updated_framework = RoadmapFramework.model_validate(framework_data)
            await repo.save_roadmap_metadata(
                roadmap_id=roadmap_id,
                user_id=roadmap_metadata.user_id,
                framework=updated_framework,
            )
            
            # 同时保存到各自的元数据表
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    content_type = result["content_type"]
                    output = result.get("result")
                    
                    if content_type == "tutorial" and output:
                        await repo.save_tutorial_metadata(output, roadmap_id)
                    elif content_type == "resources" and output:
                        await repo.save_resource_recommendation_metadata(output, roadmap_id)
                    elif content_type == "quiz" and output:
                        await repo.save_quiz_metadata(output, roadmap_id)
            
            await session.commit()
            
            # 计算更新后的失败统计
            remaining_failed = {
                "tutorial": 0,
                "resources": 0,
                "quiz": 0,
            }
            for stage in framework_data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        if concept.get("content_status") == "failed":
                            remaining_failed["tutorial"] += 1
                        if concept.get("resources_status") == "failed":
                            remaining_failed["resources"] += 1
                        if concept.get("quiz_status") == "failed":
                            remaining_failed["quiz"] += 1
    
    # 计算任务总耗时
    task_duration_ms = int((time.time() - task_start_time) * 1000)
    
    # 确定最终状态：如果有成功的项目则视为部分成功，否则为失败
    final_status = "completed" if success_count > 0 else "failed"
    
    # 更新 RoadmapTask 状态
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=retry_task_id,
            status=final_status,
            current_step="completed" if final_status == "completed" else "failed",  # 使用前端对应的步骤
            execution_summary={
                "success_count": success_count,
                "failed_count": failed_count,
                "remaining_failed": remaining_failed,
                "duration_ms": task_duration_ms,
            },
        )
        await session.commit()
    
    # 记录 ExecutionLog：重试任务完成
    await execution_logger.log_workflow_complete(
        task_id=retry_task_id,
        step="completed" if final_status == "completed" else "failed",  # 使用前端对应的步骤
        message=f"Retry task completed: {success_count} succeeded, {failed_count} failed",
        duration_ms=task_duration_ms,
        roadmap_id=roadmap_id,
        details={
            "success_count": success_count,
            "failed_count": failed_count,
            "remaining_failed": remaining_failed,
            "total_items": sum(len(v) for v in items_to_retry.values()),
            "final_status": final_status,
        },
    )
    
    # 发布重试完成事件（包含详细的统计数据）
    await notification_service.publish_completed(
        task_id=retry_task_id,
        roadmap_id=roadmap_id,
        tutorials_count=success_count,
        failed_count=failed_count,
    )
    
    # 发布进度通知，告知前端 framework 已更新
    await notification_service.publish_progress(
        task_id=retry_task_id,
        step="completed" if final_status == "completed" else "failed",  # 使用前端对应的步骤
        status=final_status,
        message=f"Retry completed: {success_count} succeeded, {failed_count} failed",
        extra_data={
            "roadmap_id": roadmap_id,
            "success_count": success_count,
            "failed_count": failed_count,
            "remaining_failed": remaining_failed,
            "framework_updated": True,
        },
    )
    
    logger.info(
        "retry_failed_task_completed",
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        success_count=success_count,
        failed_count=failed_count,
        duration_ms=task_duration_ms,
    )
