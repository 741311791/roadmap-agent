"""
路线图生成 API 端点

遵循企业级架构：API层瘦身，业务逻辑在Service层。

重构说明：
- ✅ 业务逻辑移到GenerationService（从100+行减少到20行）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
- ✅ 符合企业级架构规范
"""
from fastapi import APIRouter, Depends
from typing import Annotated, Dict, Any
import structlog

from app.models.domain import UserRequest
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
from app.services.roadmap_service import RoadmapService
from app.services.generation_service import GenerationService, get_generation_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.generation import (
    GenerateRoadmapResponse,
    CancelTaskResponse,
)
from app.schemas.task import TaskStatusDetailResponse

router = APIRouter(prefix="/roadmaps", tags=["generation"])
logger = structlog.get_logger()

# 依赖注入类型别名
CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentOrchestrator = Annotated[WorkflowExecutor, Depends(get_workflow_executor)]
CurrentGenerationService = Annotated[GenerationService, Depends(get_generation_service)]


@router.post("/generate", response_model=ResponseSchemaModel[GenerateRoadmapResponse])
async def generate_roadmap_async(
    request: UserRequest,
    generation_service: CurrentGenerationService,
) -> ResponseSchemaModel[GenerateRoadmapResponse]:
    """
    生成学习路线图（Celery 异步任务）
    
    将任务分发到 Celery Worker 执行，FastAPI 进程立即返回。
    
    激进重构版本：
    - API层只负责HTTP适配（从100+行减少到20行）
    - 所有业务逻辑（任务创建、持久化验证、Celery调度）在Service层
    
    Args:
        request: 用户请求，包含学习目标和偏好
        generation_service: 生成服务
        
    Returns:
        任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
        
    Raises:
        RequestError: 请求参数错误或任务创建失败
        InternalServerError: 服务器内部错误
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "路线图生成任务已创建"
            }
        }
        ```
    """
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    try:
        # ✅ 业务逻辑在Service层
        task_id, celery_task_id = await generation_service.create_and_verify_task(request)
        
        logger.info(
            "roadmap_generation_task_created",
            task_id=task_id,
            celery_task_id=celery_task_id,
            user_id=request.user_id,
        )
        
        return response_base.success(data=GenerateRoadmapResponse(
            task_id=task_id,
            status="pending",
            message="路线图生成任务已创建，正在队列中等待执行",
        ))
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error(
            "generate_roadmap_failed",
            user_id=request.user_id,
            error=str(e),
            exc_info=True,
        )
        raise errors.InternalServerError(msg="任务创建失败")


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


@router.post("/tasks/{task_id}/cancel", response_model=ResponseSchemaModel[CancelTaskResponse])
async def cancel_task(
    task_id: str,
    current_user: CurrentUser,
    generation_service: CurrentGenerationService,
) -> ResponseSchemaModel[CancelTaskResponse]:
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
        current_user: 当前登录用户
        generation_service: 生成服务
        
    Returns:
        取消结果
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限取消此任务
        RequestError: 任务状态不允许取消
        InternalServerError: 取消失败
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "success": true,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "任务已取消",
                "previous_status": "processing"
            }
        }
        ```
    """
    logger.info(
        "cancel_task_requested",
        task_id=task_id,
        user_id=current_user.id,
    )
    
    try:
        # ✅ 业务逻辑在Service层
        result = await generation_service.cancel_task(task_id, current_user.id)
        
        return response_base.success(data=CancelTaskResponse(**result))
        
    except ValueError as e:
        error_msg = str(e)
        if "不存在" in error_msg:
            raise errors.NotFoundError(msg=error_msg)
        else:
            raise errors.RequestError(msg=error_msg)
    except PermissionError as e:
        raise errors.ForbiddenError(msg=str(e))
    except Exception as e:
        logger.error(
            "cancel_task_failed",
            task_id=task_id,
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise errors.InternalServerError(msg="取消任务失败")


@router.get("/{task_id}/content-status", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_content_generation_status(
    task_id: str,
) -> ResponseSchemaModel[Dict[str, Any]]:
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
    
    # 从数据库获取任务和 Celery task ID
    async with async_session_maker() as session:
        task_crud = get_task_crud()
        task = await task_crud.get_by_task_id(session, task_id)
    
    if not task:
        raise errors.NotFoundError(msg="任务不存在")
    
    if not task.celery_task_id:
        # 内容生成尚未启动
        return response_base.success(data={
            "task_id": task_id,
            "celery_task_id": None,
            "status": "NOT_STARTED",
            "message": "内容生成尚未开始",
        })
    
    # 查询 Celery 任务状态
    result = AsyncResult(task.celery_task_id)
    
    response_data = {
        "task_id": task_id,
        "celery_task_id": task.celery_task_id,
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
