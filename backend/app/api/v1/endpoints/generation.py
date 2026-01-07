"""
路线图生成 API 端点

遵循企业级架构：API层瘦身，业务逻辑在Service层
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Annotated
import structlog
import uuid

from app.models.domain import UserRequest
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.core.dependencies import get_workflow_executor, get_repository_factory
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory
from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction
from app.services.roadmap_service import RoadmapService

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.generation import (
    GenerateRoadmapResponse,
    RetryContentRequest,
    RetryContentResponse,
    CancelTaskResponse,
)

router = APIRouter(prefix="/roadmaps", tags=["generation"])
logger = structlog.get_logger()

# 依赖注入类型别名
CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentOrchestrator = Annotated[WorkflowExecutor, Depends(get_workflow_executor)]
CurrentRepoFactory = Annotated[RepositoryFactory, Depends(get_repository_factory)]


@router.post("/generate", response_model=GenerateRoadmapResponse)
async def generate_roadmap_async(
    request: UserRequest,
    repo_factory: CurrentRepoFactory,
):
    """
    生成学习路线图（Celery 异步任务）
    
    将任务分发到 Celery Worker 执行，FastAPI 进程立即返回。
    
    Args:
        request: 用户请求，包含学习目标和偏好
        repo_factory: Repository 工厂
        
    Returns:
        任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "pending",
            "message": "路线图生成任务已创建"
        }
        ```
    """
    from app.tasks.roadmap_generation_tasks import generate_roadmap
    import asyncio
    
    task_id = str(uuid.uuid4())
    
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        task_id=task_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    # ============================================================
    # 第一步：创建任务记录并 commit
    # ============================================================
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=request.user_id,
            user_request=request.model_dump(mode='json'),
        )
        await session.commit()
        
        logger.debug(
            "task_created_and_committed",
            task_id=task_id,
            user_id=request.user_id,
        )
    
    # ============================================================
    # 第二步：验证任务已持久化（使用新的 session 验证可见性）
    # 
    # 背景：由于数据库连接池和事务隔离，刚 commit 的数据可能
    # 在另一个连接中不可见。这里使用独立的 session 验证，
    # 确保在分发 Celery 任务之前数据已完全可见。
    # ============================================================
    max_verify_retries = 5
    task_verified = False
    
    for attempt in range(max_verify_retries):
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            task = await task_repo.get_by_task_id(task_id)
            
            if task:
                task_verified = True
                logger.debug(
                    "task_persistence_verified",
                    task_id=task_id,
                    attempt=attempt + 1,
                )
                break
        
        if attempt < max_verify_retries - 1:
            logger.warning(
                "task_not_visible_retrying",
                task_id=task_id,
                attempt=attempt + 1,
                max_retries=max_verify_retries,
            )
            # 指数退避等待：50ms, 100ms, 150ms, 200ms
            await asyncio.sleep(0.05 * (attempt + 1))
    
    if not task_verified:
        # 任务创建失败，这是一个严重错误
        logger.error(
            "task_persistence_verification_failed",
            task_id=task_id,
            max_retries=max_verify_retries,
        )
        raise HTTPException(
            status_code=500,
            detail=f"任务创建失败：数据库持久化验证失败（task_id={task_id}）",
        )
    
    # ============================================================
    # 第三步：分发 Celery 任务（此时任务已确认存在）
    # ============================================================
    celery_task = generate_roadmap.delay(
        task_id=task_id,
        user_request=request.preferences.learning_goal,
        user_id=request.user_id,
        learning_preferences=request.preferences.model_dump(mode='json'),
    )
    
    # ============================================================
    # 第四步：更新任务记录中的 celery_task_id
    # ============================================================
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.update_task_celery_id(
            task_id=task_id,
            celery_task_id=celery_task.id,
        )
        await session.commit()
    
    logger.info(
        "celery_task_dispatched",
        task_id=task_id,
        celery_task_id=celery_task.id,
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "路线图生成任务已创建，正在队列中等待执行",
    }


@router.get("/{task_id}/status")
async def get_generation_status(
    task_id: str,
    orchestrator: CurrentOrchestrator,
    repo_factory: CurrentRepoFactory,
):
    """查询路线图生成任务状态"""
    service = RoadmapService(repo_factory, orchestrator)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return status


@router.post("/tasks/{task_id}/cancel", response_model=CancelTaskResponse)
async def cancel_task(
    task_id: str,
    db: CurrentSessionTransaction,
    current_user: CurrentUser,
    repo_factory: CurrentRepoFactory,
):
    """
    取消路线图生成任务
    
    支持取消正在运行的路线图生成任务。取消后，任务状态将变为 "cancelled"，
    用户可以稍后重新生成路线图（会从断点继续）。
    
    流程：
    1. 验证任务存在且属于当前用户
    2. 检查任务状态（仅支持取消 processing 状态）
    3. 如果有 celery_task_id，调用 Celery revoke 终止后台任务
    4. 更新数据库状态为 "cancelled"
    5. 发送 WebSocket 通知
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        current_user: 当前登录用户
        repo_factory: Repository 工厂
        
    Returns:
        取消结果
        
    Raises:
        HTTPException: 404 - 任务不存在
        HTTPException: 403 - 无权限取消此任务
        HTTPException: 400 - 任务状态不允许取消
        
    Example:
        ```json
        {
            "success": true,
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "Task cancelled successfully",
            "previous_status": "processing"
        }
        ```
    """
    logger.info(
        "cancel_task_requested",
        task_id=task_id,
        user_id=current_user.id,
    )
    
    # 1. 获取任务记录
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id(task_id)
    
    if not task:
        logger.warning(
            "cancel_task_not_found",
            task_id=task_id,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 2. 验证用户权限
    if task.user_id != current_user.id:
        logger.warning(
            "cancel_task_forbidden",
            task_id=task_id,
            task_user_id=task.user_id,
            current_user_id=current_user.id,
        )
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to cancel this task"
        )
    
    # 3. 检查任务状态（仅支持取消 processing 状态）
    if task.status != "processing":
        logger.warning(
            "cancel_task_invalid_status",
            task_id=task_id,
            current_status=task.status,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status '{task.status}'. Only 'processing' tasks can be cancelled."
        )
    
    previous_status = task.status
    
    # 4. 如果有 Celery 任务，尝试终止
    if task.celery_task_id:
        try:
            from celery.result import AsyncResult
            from app.core.celery_app import celery_app
            
            result = AsyncResult(task.celery_task_id, app=celery_app)
            # 使用 terminate=True 强制终止，signal='SIGKILL' 确保立即停止
            result.revoke(terminate=True, signal='SIGKILL')
            
            logger.info(
                "celery_task_revoked",
                task_id=task_id,
                celery_task_id=task.celery_task_id,
            )
        except Exception as e:
            # Celery 取消失败不影响数据库状态更新
            logger.error(
                "celery_task_revoke_failed",
                task_id=task_id,
                celery_task_id=task.celery_task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
    
    # 5. 更新数据库状态为 cancelled（保留原 current_step，只更新 status）
    try:
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            # 保留原来的 current_step，只更新 status
            await task_repo.update_task_status(
                task_id=task_id,
                status="cancelled",
                current_step=task.current_step,  # 保留原来的步骤
                error_message="Task cancelled by user",
            )
            await session.commit()
        
        logger.info(
            "task_status_updated_to_cancelled",
            task_id=task_id,
            previous_status=previous_status,
            preserved_current_step=task.current_step,
        )
    except Exception as e:
        logger.error(
            "cancel_task_db_update_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update task status: {str(e)}"
        )
    
    # 6. 发送 WebSocket 取消通知
    try:
        await notification_service.publish_failed(
            task_id=task_id,
            error="Task cancelled by user",
            step=task.current_step,
        )
        
        logger.info(
            "cancel_notification_sent",
            task_id=task_id,
        )
    except Exception as e:
        # WebSocket 通知失败不影响取消操作
        logger.error(
            "cancel_notification_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
    
    return CancelTaskResponse(
        success=True,
        task_id=task_id,
        message="Task cancelled successfully",
        previous_status=previous_status,
    )


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
# 单个概念内容重试 API（激进重构版）
# 
# 所有辅助函数已移除，业务逻辑在Service层
# ============================================================


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/tutorial/retry",
    response_model=RetryContentResponse,
)
async def retry_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
):
    """
    重试单个概念的教程生成（异步 Celery 任务）
    
    激进重构版本：
    - API层只负责HTTP适配（参数验证、响应格式化）
    - 所有业务逻辑（任务创建、Celery调度）在Service层
    - 代码从70行精简到15行
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户学习偏好的请求
        content_service: 内容服务
        session: 数据库会话
        current_user: 当前用户
        
    Returns:
        任务 ID，前端可通过 WebSocket 订阅进度
    """
    try:
        result = await content_service.retry_content_async(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="tutorial",
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        
        return RetryContentResponse(
            success=True,
            concept_id=concept_id,
            content_type="tutorial",
            message=result["message"],
            data={"task_id": result["task_id"]},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "retry_tutorial_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to submit retry task: {str(e)}")


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/resources/retry",
    response_model=RetryContentResponse,
)
async def retry_resources(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
):
    """重试单个概念的资源推荐生成（激进重构版）"""
    try:
        result = await content_service.retry_content_async(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="resources",
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        
        return RetryContentResponse(
            success=True,
            concept_id=concept_id,
            content_type="resources",
            message=result["message"],
            data={"task_id": result["task_id"]},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("retry_resources_failed", roadmap_id=roadmap_id, concept_id=concept_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit retry task: {str(e)}")


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/quiz/retry",
    response_model=RetryContentResponse,
)
async def retry_quiz(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
):
    """重试单个概念的测验生成（激进重构版）"""
    try:
        result = await content_service.retry_content_async(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type="quiz",
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        
        return RetryContentResponse(
            success=True,
            concept_id=concept_id,
            content_type="quiz",
            message=result["message"],
            data={"task_id": result["task_id"]},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("retry_quiz_failed", roadmap_id=roadmap_id, concept_id=concept_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit retry task: {str(e)}")
