"""
人工审核 API 端点

遵循企业级架构规范
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.core.dependencies import get_repository_factory
from app.db.repository_factory import RepositoryFactory
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.approval import (
    ApprovalRequest,
    ApprovalResponse,
)

router = APIRouter(prefix="/roadmaps", tags=["approval"])
logger = structlog.get_logger()

# 依赖注入
CurrentRepoFactory = Annotated[RepositoryFactory, Depends(get_repository_factory)]
CurrentOrchestrator = Annotated[WorkflowExecutor, Depends(get_workflow_executor)]


@router.post("/{task_id}/approve", response_model=ApprovalResponse)
async def approve_roadmap(
    task_id: str,
    request: ApprovalRequest,
    repo_factory: CurrentRepoFactory,
    orchestrator: CurrentOrchestrator,
):
    """人工审核端点（Human-in-the-Loop）"""
    from app.tasks.workflow_resume_tasks import resume_after_review
    
    try:
        # 验证任务状态
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            task = await task_repo.get_task(task_id)
            
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            
            if task.status != "human_review_pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"任务状态不正确，当前状态：{task.status}"
                )
        
        # 分发Celery任务恢复工作流
        celery_task = resume_after_review.delay(
            task_id=task_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        
        logger.info(
            "human_review_submitted",
            task_id=task_id,
            approved=approved,
            celery_task_id=celery_task.id,
        )
        
        return {
            "status": "approved" if approved else "rejected",
            "message": "审核通过，正在恢复工作流生成详细内容" if approved else "审核未通过，正在根据反馈修改路线图",
            "task_id": task_id,
            "feedback": feedback,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_roadmap_error", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="处理审核结果时发生错误")
