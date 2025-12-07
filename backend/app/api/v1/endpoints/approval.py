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
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
):
    """
    人工审核端点（Human-in-the-Loop）
    
    在路线图框架生成后，允许用户审核并决定是否继续生成详细内容
    
    Args:
        task_id: 任务 ID
        approved: 是否批准（True=批准继续生成，False=拒绝需要修改）
        feedback: 用户反馈（如果未批准，说明需要修改的内容）
        db: 数据库会话
        orchestrator: 工作流执行器
        
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
            "message": "审核通过，继续生成详细内容",
            "task_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```
        
    Example Response (Rejected):
        ```json
        {
            "status": "rejected",
            "message": "审核未通过，需要重新设计",
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "feedback": "需要增加更多实战项目"
        }
        ```
    """
    service = RoadmapService(repo_factory, orchestrator)
    
    try:
        result = await service.handle_human_review(
            task_id=task_id,
            approved=approved,
            feedback=feedback,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("approve_roadmap_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="处理审核结果时发生错误")
