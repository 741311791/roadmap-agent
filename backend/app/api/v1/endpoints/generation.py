"""
路线图生成相关端点
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import structlog
import uuid
import traceback

from app.models.domain import UserRequest
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import get_repository_factory, RepositoryFactory

router = APIRouter(prefix="/roadmaps", tags=["generation"])
logger = structlog.get_logger()


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
