"""
任务查询 API 端点

提供任务状态查询、用户任务列表、活跃任务查询等功能。

重构变更：
- ✅ 合并多个文件的任务查询接口：
  - workflows/generation/generation.py: 任务状态、内容生成状态
  - users/users.py: 用户任务列表
  - roadmaps/status.py: 路线图活跃任务、重试任务
- ✅ 统一到 /tasks prefix
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, Dict, Any, Optional
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession, CurrentUserService
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
from app.services.roadmaps.roadmap_service import RoadmapService
from app.services.roadmaps.status_service import StatusService, get_status_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.schemas.task import TaskStatusDetailResponse, TaskListResponse, ContentGenerationStatusResponse

router = APIRouter(prefix="/tasks", tags=["task-query"])
logger = structlog.get_logger()

# 依赖注入
CurrentOrchestrator = Annotated[WorkflowExecutor, Depends(get_workflow_executor)]
CurrentStatusService = Annotated[StatusService, Depends(get_status_service)]


@router.get("/{task_id}/status", response_model=ResponseSchemaModel[TaskStatusDetailResponse])
async def get_generation_status(
    task_id: str,
    orchestrator: CurrentOrchestrator,
) -> ResponseSchemaModel[TaskStatusDetailResponse]:
    """
    查询路线图生成任务状态
    
    Args:
        task_id: 任务ID
        orchestrator: 工作流执行器
        
    Returns:
        任务状态信息
        
    Raises:
        NotFoundError: 任务不存在
    """
    service = RoadmapService(orchestrator)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise errors.NotFoundError(msg="任务不存在")
    
    return response_base.success(data=status)


@router.get("/{task_id}/content-status", response_model=ResponseSchemaModel[ContentGenerationStatusResponse])
async def get_content_generation_status(
    task_id: str,
) -> ResponseSchemaModel[ContentGenerationStatusResponse]:
    """
    查询内容生成进度（Celery 任务状态）
    
    当路线图框架生成完成后，内容生成（教程、资源、测验）会在独立的 Celery Worker 中执行。
    该接口用于查询内容生成的实时进度。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        内容生成状态信息
        
    Raises:
        NotFoundError: 任务不存在
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
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
        }
        ```
    """
    from celery.result import AsyncResult
    from app.core.celery_app import celery_app
    
    # 从数据库获取任务和 Celery task ID
    async with async_session_maker() as session:
        task_crud = get_task_crud()
        task = await task_crud.get_by_task_id(session, task_id)
    
    if not task:
        raise errors.NotFoundError(msg="任务不存在")
    
    content_celery_task_id = task.content_generation_celery_id
    content_generation_status = task.content_generation_status

    # 优先信任数据库中的最终状态，避免 Result Backend 过期或 Broker 抖动时返回误导性状态。
    if content_generation_status == "completed":
        return response_base.success(data={
            "task_id": task_id,
            "celery_task_id": content_celery_task_id,
            "status": "SUCCESS",
            "message": "内容生成完成",
        })

    if content_generation_status == "partial_failure":
        return response_base.success(data={
            "task_id": task_id,
            "celery_task_id": content_celery_task_id,
            "status": "PARTIAL_FAILURE",
            "message": "内容生成部分完成",
        })

    if content_generation_status == "failed":
        return response_base.success(data={
            "task_id": task_id,
            "celery_task_id": content_celery_task_id,
            "status": "FAILURE",
            "message": "内容生成失败",
        })

    if not content_celery_task_id:
        # 内容生成尚未启动，或尚未成功回写独立内容任务 ID。
        message = "内容生成任务排队中" if content_generation_status == "processing" else "内容生成尚未开始"
        status_value = "STARTED" if content_generation_status == "processing" else "NOT_STARTED"
        return response_base.success(data={
            "task_id": task_id,
            "celery_task_id": None,
            "status": status_value,
            "message": message,
        })
    
    # 查询独立内容 Worker 的 Celery 任务状态
    result = AsyncResult(content_celery_task_id, app=celery_app)
    
    response_data = {
        "task_id": task_id,
        "celery_task_id": content_celery_task_id,
        "status": result.status,
    }
    
    # 根据任务状态添加额外信息
    if result.status == "PENDING":
        response_data["message"] = "内容生成任务排队中"
    elif result.status == "PROGRESS":
        response_data["progress"] = result.info
    elif result.status == "SUCCESS":
        response_data["result"] = result.result
        response_data["message"] = "内容生成完成"
    elif result.status == "FAILURE":
        response_data["error"] = str(result.info)
        response_data["message"] = "内容生成失败"
    elif result.status == "RETRY":
        response_data["message"] = "内容生成任务重试中"
        response_data["retry_count"] = result.info.get("retry_count") if result.info else 0
    
    return response_base.success(data=response_data)


@router.get("/my", response_model=ResponseSchemaModel[TaskListResponse])
async def get_user_tasks(
    db: CurrentSession,
    service: CurrentUserService,
    current_user: User = Depends(current_active_user),
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> ResponseSchemaModel[TaskListResponse]:
    """
    获取当前用户的任务列表，支持按状态和任务类型筛选
    
    Args:
        db: 数据库会话
        current_user: 当前用户（从JWT提取）
        service: 用户服务
        status: 任务状态筛选（可选）：pending, processing, completed, failed
        task_type: 任务类型筛选（可选）：creation, retry_tutorial, retry_resources, retry_quiz, retry_batch
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        任务列表及各状态统计
        
    状态归类说明：
        - pending: 仅 pending
        - processing: processing, running, human_review_pending, human_review_required
        - completed: completed, partial_failure, approved
        - failed: failed, rejected
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "tasks": [
                    {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "human_review_pending",
                        "current_step": "human_review",
                        "title": "Python Web Development",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:01:00Z",
                        "completed_at": null,
                        "error_message": null,
                        "roadmap_id": "python-guide-xxx"
                    }
                ],
                "total": 1,
                "pending_count": 0,
                "processing_count": 1,
                "completed_count": 5,
                "failed_count": 0
            }
        }
        ```
    """
    user_id = current_user.id  # 从JWT提取user_id
    logger.info("get_user_tasks_requested", user_id=user_id, status=status, task_type=task_type, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    result = await service.get_user_tasks(
        db, user_id, status=status, task_type=task_type, skip=offset, limit=limit
    )
    
    return response_base.success(data=result)


@router.get("/roadmaps/{roadmap_id}/active-task", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_active_task(
    roadmap_id: str,
    db: CurrentSession,
    service: CurrentStatusService,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取路线图当前的活跃任务
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        活跃任务信息
    """
    result = await service.get_active_task(db, roadmap_id)
    return response_base.success(data=result)


@router.get("/roadmaps/{roadmap_id}/active-retry-task", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_active_retry_task(
    roadmap_id: str,
    db: CurrentSession,
    service: CurrentStatusService,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取路线图当前正在进行的重试任务
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        重试任务信息
        
    Raises:
        NotFoundError: 路线图不存在
    """
    result = await service.get_active_retry_task(db, roadmap_id)
    
    if result is None:
        raise errors.NotFoundError(msg="路线图不存在")
    
    return response_base.success(data=result)


@router.get("/{task_id}/edit/history-full", response_model=ResponseSchemaModel)
async def get_task_edit_history_full(
    task_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel:
    """
    获取任务关联路线图的完整编辑历史（包含详细diff和修改内容）
    
    这是一个便捷端点，根据 task_id 查找关联的 roadmap_id，然后返回编辑历史。
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        完整编辑历史列表（按时间倒序）
        
    Raises:
        NotFoundError: 任务不存在或任务未关联路线图
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "roadmap_id": "xxx",
                "edit_history": [
                    {
                        "id": 1,
                        "timestamp": "2026-01-23T12:00:00Z",
                        "edit_source": "validation_failed",
                        "edit_plan_id": "xxx",
                        "changes_made": {...},
                        "diff_summary": "修改了3个模块...",
                        "version": 2
                    }
                ],
                "total": 3
            }
        }
        ```
    """
    from app.crud.crud_edit import get_edit_crud
    from app.crud.crud_edit_plan import get_edit_plan_crud
    
    # 1. 根据 task_id 查找任务
    task_crud = get_task_crud()
    task = await task_crud.get_by_task_id(db, task_id)
    
    if not task:
        raise errors.NotFoundError(msg=f"任务 {task_id} 不存在")
    
    if not task.roadmap_id:
        raise errors.NotFoundError(msg=f"任务 {task_id} 未关联路线图")
    
    # 2. 查询编辑历史
    edit_crud = get_edit_crud()
    edit_records = await edit_crud.get_by_roadmap_id(db, task.roadmap_id)
    
    # 3. 组装编辑历史详情
    edit_plan_crud = get_edit_plan_crud()
    history = []
    
    for edit_record in edit_records:
        # 查找关联的编辑计划（如果存在）
        edit_plan = None
        if edit_record.edit_plan_id:
            edit_plan = await edit_plan_crud.get_by_id(db, edit_record.edit_plan_id)
        
        history_item = {
            "id": edit_record.id,
            "timestamp": edit_record.created_at.isoformat() if edit_record.created_at else None,
            "edit_source": edit_record.edit_source,
            "edit_plan_id": edit_record.edit_plan_id,
            "changes_made": edit_record.changes_made,
            "diff_summary": edit_record.diff_summary,
            "version": edit_record.version,
        }
        
        # 如果有编辑计划，添加计划详情
        if edit_plan:
            history_item["edit_plan"] = {
                "id": edit_plan.id,
                "edit_plan_id": edit_plan.edit_plan_id,
                "modifications": edit_plan.modifications,
                "reasoning": edit_plan.reasoning,
            }
        
        history.append(history_item)
    
    return response_base.success(data={
        "roadmap_id": task.roadmap_id,
        "edit_history": history,
        "total": len(history),
    })

