"""
人工审核相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_workflow_executor, get_repository_factory
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory

router = APIRouter(prefix="/roadmaps", tags=["approval"])
logger = structlog.get_logger()


@router.post("/{task_id}/approve")
async def approve_roadmap(
    task_id: str,
    approved: bool,
    feedback: str | None = None,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    人工审核端点（Human-in-the-Loop）
    
    在路线图框架生成后，允许用户审核并决定是否继续生成详细内容。
    审核结果保存后，分发 Celery 任务恢复工作流。
    
    Args:
        task_id: 任务 ID
        approved: 是否批准（True=批准继续生成，False=拒绝需要修改）
        feedback: 用户反馈（如果未批准，说明需要修改的内容）
        repo_factory: Repository 工厂
        
    Returns:
        审核处理结果
        
    Raises:
        HTTPException: 
            - 400: 任务状态不正确或参数错误
            - 500: 处理审核结果时发生错误
            
    Example Request:
        ```json
        {
            "approved": true,
            "feedback": null
        }
        ```
        
    Example Response (Approved):
        ```json
        {
            "status": "approved",
            "message": "审核通过，正在恢复工作流生成详细内容",
            "task_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```
        
    Example Response (Rejected):
        ```json
        {
            "status": "rejected",
            "message": "审核未通过，正在根据反馈修改路线图",
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "feedback": "需要增加更多实战项目"
        }
        ```
    """
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
                    detail=f"任务状态不正确，当前状态：{task.status}，期望状态：human_review_pending"
                )
        
        # 分发 Celery 任务恢复工作流
        celery_task = resume_after_review.delay(
            task_id=task_id,
            approved=approved,
            feedback=feedback,
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
