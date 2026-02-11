"""
人工审核 API 端点

提供路线图人工审核（批准/拒绝）功能。

重构变更：
- ✅ 从 workflows/generation/approval.py 移动
- ✅ 路由prefix改为 /tasks
- ✅ 遵循企业级架构规范
"""
from typing import Annotated
from fastapi import APIRouter, Depends
import structlog

from app.services.roadmaps.roadmap_service import RoadmapService
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud

# ✅ 导入 Schema
from app.schemas.approval import (
    ApprovalRequest,
    ApprovalResponse,
)

router = APIRouter(prefix="/tasks", tags=["task-approval"])
logger = structlog.get_logger()

# 依赖注入
CurrentOrchestrator = Annotated[WorkflowExecutor, Depends(get_workflow_executor)]


@router.post("/{task_id}/approve", response_model=ResponseSchemaModel[ApprovalResponse])
async def approve_roadmap(
    task_id: str,
    request: ApprovalRequest,
    orchestrator: CurrentOrchestrator,
) -> ResponseSchemaModel[ApprovalResponse]:
    """
    人工审核端点（Human-in-the-Loop）
    
    Args:
        task_id: 任务ID
        request: 审核请求（包含批准/拒绝和反馈）
        orchestrator: 工作流执行器
        
    Returns:
        审核结果
        
    Raises:
        NotFoundError: 任务不存在
        RequestError: 任务状态不正确
        InternalServerError: 处理审核结果失败
    """
    from app.tasks.workflow_resume_tasks import resume_after_review
    
    try:
        # 验证任务状态
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            
            if not task:
                raise errors.NotFoundError(msg="任务不存在")
            
            if task.status != "human_review_pending":
                raise errors.RequestError(msg=f"任务状态不正确，当前状态：{task.status}")
        
        # 分发Celery任务恢复工作流
        celery_task = resume_after_review.delay(
            task_id=task_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        
        logger.info(
            "human_review_submitted",
            task_id=task_id,
            approved=request.approved,
            celery_task_id=celery_task.id,
        )
        
        return response_base.success(data=ApprovalResponse(
            status="approved" if request.approved else "rejected",
            message="审核通过，正在恢复工作流生成详细内容" if request.approved else "审核未通过，正在根据反馈修改路线图",
            task_id=task_id,
            feedback=request.feedback,
        ))
        
    except (errors.NotFoundError, errors.RequestError):
        raise
    except Exception as e:
        logger.error(
            "approve_roadmap_error", 
            task_id=task_id, 
            error=str(e),
            error_type=type(e).__name__,
        )
        raise errors.InternalServerError(msg="处理审核结果时发生错误")

