"""
任务生成 API 端点

提供路线图生成任务的创建和取消功能。

重构变更：
- ✅ 从 workflows/generation/generation.py 移动
- ✅ 路由prefix从无到 /tasks
- ✅ 遵循企业级架构：API层瘦身，业务逻辑在Service层
"""
from fastapi import APIRouter, Depends
from typing import Annotated
import structlog

from app.models.domain import UserRequest
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.services.workflows.generation.generation_service import GenerationService, get_generation_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema
from app.schemas.generation import (
    GenerateRoadmapResponse,
    CancelTaskResponse,
    DeleteTaskResponse,
)

router = APIRouter(prefix="/tasks", tags=["task-generation"])
logger = structlog.get_logger()

# 依赖注入类型别名
CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentGenerationService = Annotated[GenerationService, Depends(get_generation_service)]


@router.post("/generate", response_model=ResponseSchemaModel[GenerateRoadmapResponse])
async def generate_roadmap_async(
    request: UserRequest,
    generation_service: CurrentGenerationService,
) -> ResponseSchemaModel[GenerateRoadmapResponse]:
    """
    生成学习路线图（Celery 异步任务）
    
    将任务分发到 Celery Worker 执行，FastAPI 进程立即返回。
    
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
        task_id = await generation_service.create_and_verify_task(request)
        
        logger.info(
            "roadmap_generation_task_created",
            task_id=task_id,
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


@router.post("/{task_id}/cancel", response_model=ResponseSchemaModel[CancelTaskResponse])
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


@router.delete("/{task_id}", response_model=ResponseSchemaModel[DeleteTaskResponse])
async def delete_task(
    task_id: str,
    current_user: CurrentUser,
    generation_service: CurrentGenerationService,
) -> ResponseSchemaModel[DeleteTaskResponse]:
    """
    删除路线图生成任务
    
    删除任务记录。如果任务正在执行（processing状态），会先自动取消任务再删除。
    
    流程：
    1. 验证任务存在且属于当前用户
    2. 如果任务状态为 processing，先取消任务
    3. 删除任务记录
    
    Args:
        task_id: 任务 ID
        current_user: 当前登录用户
        generation_service: 生成服务
        
    Returns:
        删除结果
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限删除此任务
        InternalServerError: 删除失败
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "success": true,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "任务已删除",
                "previous_status": "failed"
            }
        }
        ```
    """
    logger.info(
        "delete_task_requested",
        task_id=task_id,
        user_id=current_user.id,
    )
    
    try:
        # ✅ 业务逻辑在Service层
        result = await generation_service.delete_task(task_id, current_user.id)
        
        return response_base.success(data=DeleteTaskResponse(**result))
        
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
            "delete_task_failed",
            task_id=task_id,
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise errors.InternalServerError(msg="删除任务失败")

