"""
路线图生成相关端点

包含：
- 路线图生成（异步任务）
- 任务状态查询
- 单个概念内容重试（tutorial/resources/quiz）
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
import structlog
import uuid
import traceback

from app.models.domain import (
    UserRequest,
    LearningPreferences,
    Concept,
    TutorialGenerationInput,
    ResourceRecommendationInput,
    QuizGenerationInput,
)
from app.services.roadmap_service import RoadmapService
from app.services.notification_service import notification_service
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import get_repository_factory, RepositoryFactory
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.agents.resource_recommender import ResourceRecommenderAgent
from app.agents.quiz_generator import QuizGeneratorAgent

router = APIRouter(prefix="/roadmaps", tags=["generation"])
logger = structlog.get_logger()


# ============================================================
# 请求/响应模型
# ============================================================

class RetryContentRequest(BaseModel):
    """单个概念内容重试请求"""
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


class RetryContentResponse(BaseModel):
    """单个概念内容重试响应"""
    success: bool = Field(..., description="是否成功")
    concept_id: str = Field(..., description="概念 ID")
    content_type: Literal["tutorial", "resources", "quiz"] = Field(..., description="内容类型")
    message: str = Field(..., description="结果消息")
    data: Optional[dict] = Field(None, description="重试成功时返回的数据")


async def _execute_roadmap_generation_task(
    request: UserRequest,
    task_id: str,
    orchestrator: WorkflowExecutor,
    repo_factory: RepositoryFactory,
):
    """
    后台任务执行函数
    
    使用独立的数据库会话，避免请求结束后会话被关闭的问题
    
    Args:
        request: 用户请求
        task_id: 追踪 ID
        orchestrator: 编排器实例
        repo_factory: Repository 工厂
    """
    logger.info(
        "background_task_started",
        task_id=task_id,
        user_id=request.user_id,
    )
    
    try:
        service = RoadmapService(repo_factory, orchestrator)
        
        logger.info(
            "background_task_executing_workflow",
            task_id=task_id,
        )
        
        result = await service.generate_roadmap(
            request, task_id
        )
        
        logger.info(
            "background_task_completed",
            task_id=task_id,
            status=result.get("status"),
            roadmap_id=result.get("roadmap_id"),
        )
        
    except Exception as e:
        # 详细记录异常信息
        error_traceback = traceback.format_exc()
        logger.error(
            "background_task_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=error_traceback,
        )
        
        # 尝试更新任务状态为失败
        try:
            async with repo_factory.create_session() as session:
                task_repo = repo_factory.create_task_repo(session)
                await task_repo.update_task_status(
                    task_id=task_id,
                    status="failed",
                    current_step="failed",
                    error_message=f"{type(e).__name__}: {str(e)[:500]}",
                )
                await session.commit()
            
            logger.info(
                "background_task_status_updated_to_failed",
                task_id=task_id,
            )
        except Exception as update_error:
            logger.error(
                "background_task_status_update_failed",
                task_id=task_id,
                original_error=str(e),
                update_error=str(update_error),
            )


@router.post("/generate")
async def generate_roadmap_async(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    生成学习路线图（异步任务）
    
    Args:
        request: 用户请求，包含学习目标和偏好
        background_tasks: FastAPI后台任务
        orchestrator: 工作流执行器
        repo_factory: Repository 工厂
        
    Returns:
        任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "message": "路线图生成任务已启动"
        }
        ```
    """
    task_id = str(uuid.uuid4())
    
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        task_id=task_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    # 先创建初始任务记录
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=request.user_id,
            user_request=request.model_dump(mode='json'),
        )
        await task_repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="queued",
        )
        await session.commit()
    
    # 在后台任务中执行工作流
    background_tasks.add_task(
        _execute_roadmap_generation_task,
        request,
        task_id,
        orchestrator,
        repo_factory,
    )
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "路线图生成任务已启动，roadmap_id将在需求分析完成后通过WebSocket发送",
    }


@router.get("/{task_id}/status")
async def get_generation_status(
    task_id: str,
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    查询路线图生成任务状态
    
    Args:
        task_id: 任务ID
        orchestrator: 工作流执行器
        repo_factory: Repository 工厂
        
    Returns:
        任务状态信息
        
    Raises:
        HTTPException: 404 - 任务不存在
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "current_step": "tutorial_generation",
            "roadmap_id": "python-web-dev-2024",
            "created_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    service = RoadmapService(repo_factory, orchestrator)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return status


@router.get("/{task_id}/content-status")
async def get_content_generation_status(
    task_id: str,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    查询内容生成进度（Celery 任务状态）
    
    当路线图框架生成完成后，内容生成（教程、资源、测验）会在独立的 Celery Worker 中执行。
    该接口用于查询内容生成的实时进度。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        内容生成状态信息
        
    Raises:
        HTTPException: 404 - 任务不存在或内容生成未启动
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "status": "PROGRESS",
            "progress": {
                "current": 15,
                "total": 30,
                "percentage": 50.0
            },
            "result": null
        }
        ```
    """
    from celery.result import AsyncResult
    
    # 从数据库获取任务和 Celery task ID
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not task.celery_task_id:
        # 内容生成尚未启动
        return {
            "task_id": task_id,
            "celery_task_id": None,
            "status": "NOT_STARTED",
            "message": "Content generation has not been queued yet",
        }
    
    # 查询 Celery 任务状态
    result = AsyncResult(task.celery_task_id)
    
    response = {
        "task_id": task_id,
        "celery_task_id": task.celery_task_id,
        "status": result.status,
    }
    
    # 根据任务状态添加额外信息
    if result.status == "PENDING":
        response["message"] = "Content generation task is queued"
    elif result.status == "PROGRESS":
        response["progress"] = result.info
    elif result.status == "SUCCESS":
        response["result"] = result.result
        response["message"] = "Content generation completed successfully"
    elif result.status == "FAILURE":
        response["error"] = str(result.info)
        response["message"] = "Content generation failed"
    elif result.status == "RETRY":
        response["message"] = "Content generation task is being retried"
        response["retry_count"] = result.info.get("retry_count") if result.info else 0
    
    return response


@router.post("/{roadmap_id}/retry-failed")
async def retry_failed_concepts(
    roadmap_id: str,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    重试失败的概念内容生成
    
    Args:
        roadmap_id: 路线图 ID
        repo_factory: Repository 工厂
        
    Returns:
        重试结果
    """
    # 获取路线图元数据
    async with repo_factory.create_session() as session:
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap = await roadmap_repo.get_by_roadmap_id(roadmap_id)
    
    if not roadmap:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # TODO: 实现重试逻辑
    return {"message": "重试功能待实现"}


# ============================================================
# 单个概念内容重试 API
# ============================================================

def _generate_retry_task_id(roadmap_id: str, concept_id: str, content_type: str) -> str:
    """
    生成单个概念重试的任务 ID
    
    格式: retry-{content_type}-{concept_id[:8]}-{random}
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        content_type: 内容类型 (tutorial/resources/quiz)
        
    Returns:
        任务 ID
    """
    short_concept_id = concept_id[:8] if len(concept_id) >= 8 else concept_id
    random_suffix = str(uuid.uuid4())[:8]
    return f"retry-{content_type}-{short_concept_id}-{random_suffix}"


async def _get_concept_from_roadmap(
    roadmap_id: str,
    concept_id: str,
    repo_factory: RepositoryFactory,
) -> tuple[Optional[Concept], Optional[dict], Optional[dict]]:
    """
    从路线图中获取指定概念
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        repo_factory: Repository 工厂
        
    Returns:
        (Concept 对象, 上下文信息, 路线图元数据) 或 (None, None, None)
    """
    async with repo_factory.create_session() as session:
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap_metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
    
    if not roadmap_metadata:
        return None, None, None
    
    framework_data = roadmap_metadata.framework_data
    
    # 遍历查找概念
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept_data in module.get("concepts", []):
                if concept_data.get("concept_id") == concept_id:
                    concept = Concept.model_validate(concept_data)
                    context = {
                        "roadmap_id": roadmap_id,
                        "stage_name": stage.get("name"),
                        "module_name": module.get("name"),
                        "content_version": 1,
                    }
                    return concept, context, roadmap_metadata
    
    return None, None, None


async def _update_concept_status_in_framework(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    status: str,
    result: dict | None = None,
    repo_factory: RepositoryFactory = None,
):
    """
    更新路线图框架中的概念状态
    
    支持单独更新状态（generating/failed）或同时更新状态和结果数据（completed）。
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        content_type: 内容类型 (tutorial/resources/quiz)
        status: 状态 (pending/generating/completed/failed)
        result: 可选的结果数据（仅在 completed 状态时需要）
        repo_factory: Repository 工厂
    """
    async with repo_factory.create_session() as session:
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap_metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
        
        if not roadmap_metadata:
            return
        
        framework_data = roadmap_metadata.framework_data
        
        # 遍历更新概念状态
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        # 更新状态字段
                        if content_type == "tutorial":
                            concept["content_status"] = status
                            # 只有在 completed 状态且有 result 时才更新结果数据
                            if status == "completed" and result:
                                concept["content_ref"] = result.get("content_url")
                                concept["content_summary"] = result.get("summary")
                        elif content_type == "resources":
                            concept["resources_status"] = status
                            if status == "completed" and result:
                                concept["resources_id"] = result.get("resources_id")
                                concept["resources_count"] = result.get("resources_count", 0)
                        elif content_type == "quiz":
                            concept["quiz_status"] = status
                            if status == "completed" and result:
                                concept["quiz_id"] = result.get("quiz_id")
                                concept["quiz_questions_count"] = result.get("questions_count", 0)
                        
                        # 找到后直接退出循环
                        break
        
        # 保存更新后的框架（使用 save_roadmap 确保 flag_modified 被调用）
        from app.models.domain import RoadmapFramework
        updated_framework = RoadmapFramework.model_validate(framework_data)
        await roadmap_repo.save_roadmap(
            roadmap_id=roadmap_id,
            user_id=roadmap_metadata.user_id,
            framework=updated_framework,
        )
        await session.commit()


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/tutorial/retry",
    response_model=RetryContentResponse,
)
async def retry_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    重试单个概念的教程生成（异步 Celery 任务）
    
    当教程生成失败时，用户可以调用此接口重新生成教程内容。
    任务将提交到 Celery 队列异步执行，支持实时 WebSocket 推送生成状态。
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户学习偏好的请求
        
    Returns:
        任务 ID，前端可通过 WebSocket 订阅进度
    """
    from app.tasks.content_generation_tasks import retry_tutorial_task
    
    # 生成任务 ID 用于 WebSocket 推送
    task_id = _generate_retry_task_id(roadmap_id, concept_id, "tutorial")
    
    logger.info(
        "retry_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    # 获取概念
    concept, context, roadmap_metadata = await _get_concept_from_roadmap(
        roadmap_id, concept_id, repo_factory
    )
    
    if not concept:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 创建任务记录并关联到路线图
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=roadmap_metadata.user_id,
            user_request={
                "type": "retry_tutorial",
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "preferences": request.preferences.model_dump(mode='json'),
            },
            task_type="retry_tutorial",
            concept_id=concept_id,
            content_type="tutorial",
        )
        await task_repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="tutorial_generation",
            roadmap_id=roadmap_id,
        )
        await session.commit()
    
    # 提交 Celery 任务（异步执行）
    retry_tutorial_task.apply_async(
        args=[
            task_id,
            roadmap_id,
            concept_id,
            concept.model_dump(mode='json'),
            context,
            request.preferences.model_dump(mode='json'),
        ],
        task_id=task_id,  # 使用相同的 task_id
    )
    
    logger.info(
        "retry_tutorial_task_submitted",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    return RetryContentResponse(
        success=True,
        concept_id=concept_id,
        content_type="tutorial",
        message="Tutorial regeneration task submitted",
        data={"task_id": task_id},
    )


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/resources/retry",
    response_model=RetryContentResponse,
)
async def retry_resources(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    重试单个概念的资源推荐生成（异步 Celery 任务）
    
    当资源推荐生成失败时，用户可以调用此接口重新生成资源列表。
    任务将提交到 Celery 队列异步执行，支持实时 WebSocket 推送生成状态。
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户学习偏好的请求
        
    Returns:
        任务 ID，前端可通过 WebSocket 订阅进度
    """
    from app.tasks.content_generation_tasks import retry_resources_task
    
    # 生成任务 ID 用于 WebSocket 推送
    task_id = _generate_retry_task_id(roadmap_id, concept_id, "resources")
    
    logger.info(
        "retry_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    # 获取概念
    concept, context, roadmap_metadata = await _get_concept_from_roadmap(
        roadmap_id, concept_id, repo_factory
    )
    
    if not concept:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 创建任务记录并关联到路线图
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=roadmap_metadata.user_id,
            user_request={
                "type": "retry_resources",
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "preferences": request.preferences.model_dump(mode='json'),
            },
            task_type="retry_resources",
            concept_id=concept_id,
            content_type="resources",
        )
        await task_repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="resource_recommendation",
            roadmap_id=roadmap_id,
        )
        await session.commit()
    
    # 提交 Celery 任务（异步执行）
    retry_resources_task.apply_async(
        args=[
            task_id,
            roadmap_id,
            concept_id,
            concept.model_dump(mode='json'),
            context,
            request.preferences.model_dump(mode='json'),
        ],
        task_id=task_id,  # 使用相同的 task_id
    )
    
    logger.info(
        "retry_resources_task_submitted",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    return RetryContentResponse(
        success=True,
        concept_id=concept_id,
        content_type="resources",
        message="Resources regeneration task submitted",
        data={"task_id": task_id},
    )


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/quiz/retry",
    response_model=RetryContentResponse,
)
async def retry_quiz(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    重试单个概念的测验生成（异步 Celery 任务）
    
    当测验生成失败时，用户可以调用此接口重新生成测验题目。
    任务将提交到 Celery 队列异步执行，支持实时 WebSocket 推送生成状态。
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户学习偏好的请求
        
    Returns:
        任务 ID，前端可通过 WebSocket 订阅进度
    """
    # 生成任务 ID 用于 WebSocket 推送
    task_id = _generate_retry_task_id(roadmap_id, concept_id, "quiz")
    
    logger.info(
        "retry_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    # 获取概念
    concept, context, roadmap_metadata = await _get_concept_from_roadmap(
        roadmap_id, concept_id, repo_factory
    )
    
    if not concept:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 创建任务记录并关联到路线图
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=roadmap_metadata.user_id,
            user_request={
                "type": "retry_quiz",
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "preferences": request.preferences.model_dump(mode='json'),
            },
            task_type="retry_quiz",
            concept_id=concept_id,
            content_type="quiz",
        )
        await task_repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="quiz_generation",
            roadmap_id=roadmap_id,
        )
        await session.commit()
    
    # 提交 Celery 任务（异步执行）
    from app.tasks.content_generation_tasks import retry_quiz_task
    
    retry_quiz_task.apply_async(
        args=[
            task_id,
            roadmap_id,
            concept_id,
            concept.model_dump(mode='json'),
            context,
            request.preferences.model_dump(mode='json'),
        ],
        task_id=task_id,  # 使用相同的 task_id
    )
    
    logger.info(
        "retry_quiz_task_submitted",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        task_id=task_id,
    )
    
    return RetryContentResponse(
        success=True,
        concept_id=concept_id,
        content_type="quiz",
        message="Quiz regeneration task submitted",
        data={"task_id": task_id},
    )
