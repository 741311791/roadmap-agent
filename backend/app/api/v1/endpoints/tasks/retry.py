"""
任务重试 API 端点

基于LangGraph 1.0 Checkpoint机制的两种重试模式：
- 断点续传（Resume）：从最后checkpoint恢复（主图/子图）
- 时间旅行（Time Travel）：回到主图历史节点重新执行

重构变更：
- ✅ 从 workflows/generation/retry.py 移动
- ✅ 路由prefix从 /retry 改为 /tasks
- ✅ 遵循企业级架构：API层瘦身，业务逻辑在Service层
"""
from fastapi import APIRouter, Depends
from typing import Annotated
import structlog

from app.models.database import User
from app.core.auth.deps import current_active_user
from app.core.response_schema import ResponseSchemaModel, response_base
from app.core.custom_exceptions import errors
from app.schemas.retry import (
    RetryRequest,
    RetryResponse,
    TaskRetryStatus,
)
from app.services.workflows.generation.retry_service import (
    RetryService,
    get_retry_service,
)

router = APIRouter(prefix="/tasks", tags=["task-retry"])
logger = structlog.get_logger()

# 依赖注入类型别名
CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentRetryService = Annotated[RetryService, Depends(get_retry_service)]


@router.get(
    "/{task_id}/retry-status",
    response_model=ResponseSchemaModel[TaskRetryStatus],
    summary="获取任务重试状态",
    description="""
    查询指定任务的重试状态，包括：
    - 是否可以重试
    - 当前checkpoint信息
    - 是否有子图在中断
    - 可用的重试模式（resume/time_travel）
    
    用于前端判断是否显示重试按钮以及支持的重试选项。
    """,
)
async def get_retry_status(
    task_id: str,
    retry_service: CurrentRetryService,
) -> ResponseSchemaModel[TaskRetryStatus]:
    """
    获取任务重试状态
    
    Args:
        task_id: 任务ID
        retry_service: 重试服务
        
    Returns:
        任务重试状态信息
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "can_retry": true,
                "retry_reason": null,
                "current_checkpoint": {
                    "checkpoint_id": "1ef12345-6789-4abc-def0-123456789abc",
                    "timestamp": "2026-01-11T10:30:00Z",
                    "node_name": "content_generation",
                    "next_nodes": [],
                    "can_retry": true
                },
                "available_retry_scopes": ["task", "stage", "concept"]
            }
        }
        ```
    """
    try:
        status = await retry_service.get_retry_status(task_id)
        return response_base.success(data=status)
        
    except Exception as e:
        logger.error(
            "get_retry_status_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        raise errors.InternalServerError(msg="获取重试状态失败")


@router.post(
    "/{task_id}/retry",
    response_model=ResponseSchemaModel[RetryResponse],
    summary="执行任务重试",
    description="""
    执行路线图生成任务的重试操作。
    
    支持两种重试模式：
    
    1. **断点续传（mode=resume）**：
       - 从最后的checkpoint自动恢复
       - 适用于Worker重启、临时失败、主图/子图节点失败
       - LangGraph自动处理所有并发失败的子图节点
       - 推荐优先使用
    
    2. **时间旅行（mode=time_travel）**：
       - 回到主图历史节点重新执行
       - 适用于用户需求变更、重新设计
       - 仅支持主图节点（Intent、Curriculum、Validation、Content）
       - 子图并发失败请使用断点续传
    
    注意：
    - 仅支持重试失败、部分失败或取消的任务
    - 正在执行中的任务需要先取消
    - 等待人工审核的任务请使用审核API
    - 概念内容重新生成请使用 /api/v1/content/{roadmap_id}/concepts/{concept_id}/regenerate
    """,
)
async def retry_task(
    task_id: str,
    request: RetryRequest,
    current_user: CurrentUser,
    retry_service: CurrentRetryService,
) -> ResponseSchemaModel[RetryResponse]:
    """
    执行任务重试
    
    Args:
        task_id: 任务ID
        request: 重试请求（包含重试范围和参数）
        current_user: 当前用户
        retry_service: 重试服务
        
    Returns:
        重试响应
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限重试此任务
        RequestError: 任务状态不允许重试或参数错误
        InternalServerError: 重试失败
        
    Examples:
        1. 断点续传（从最后checkpoint恢复）：
        ```json
        {
            "mode": "resume",
            "reason": "Worker重启后从失败点恢复"
        }
        ```
        
        2. 时间旅行（从Intent节点重新开始）：
        ```json
        {
            "mode": "time_travel",
            "target_node": "intent_analysis",
            "reason": "用户需求变更，从Intent重新开始"
        }
        ```
    """
    logger.info(
        "retry_task_requested",
        task_id=task_id,
        user_id=current_user.id,
        mode=request.mode,
        target_node=request.target_node,
    )
    
    try:
        # 调用Service层执行重试
        result = await retry_service.retry_task(
            task_id=task_id,
            request=request,
            user_id=current_user.id,
        )
        
        logger.info(
            "retry_task_success",
            task_id=task_id,
            retry_scope=result.retry_scope,
            retry_from=result.retry_from,
        )
        
        return response_base.success(data=result)
        
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
            "retry_task_failed",
            task_id=task_id,
            user_id=current_user.id,
            error=str(e),
            exc_info=True,
        )
        raise errors.InternalServerError(msg="重试任务失败")

