"""
路线图查询相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_workflow_executor, get_repository_factory
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory
from app.db.repositories.roadmap_repo import RoadmapRepository

router = APIRouter(prefix="/roadmaps", tags=["retrieval"])
logger = structlog.get_logger()


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
):
    """
    获取完整的路线图数据
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        repo_factory: Repository 工厂
        orchestrator: 工作流执行器
        
    Returns:
        - 如果路线图存在，返回完整的路线图框架数据
        - 如果路线图不存在但有活跃任务，返回生成中状态
        - 如果都不存在，返回 404
        
    Raises:
        HTTPException: 404 - 路线图不存在
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "title": "Python Web开发学习路线",
            "topic": "Python Web开发",
            "concepts": [...],
            "status": "completed"
        }
        ```
    """
    service = RoadmapService(repo_factory, orchestrator)
    roadmap = await service.get_roadmap(roadmap_id)
    
    if not roadmap:
        # 检查是否有活跃任务正在生成这个路线图
        repo = RoadmapRepository(db)
        active_task = await repo.get_active_task_by_roadmap_id(roadmap_id)
        
        if active_task:
            # 路线图正在生成中
            return {
                "status": "processing",
                "task_id": active_task.task_id,
                "current_step": active_task.current_step,
                "message": "路线图正在生成中",
                "created_at": active_task.created_at.isoformat() if active_task.created_at else None,
                "updated_at": active_task.updated_at.isoformat() if active_task.updated_at else None,
            }
        
        # 路线图不存在且没有活跃任务
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    return roadmap


@router.get("/{roadmap_id}/active-task")
async def get_active_task(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取路线图当前的活跃任务
    
    用于前端轮询：查询该路线图是否有正在进行的任务
    - 如果有正在进行的任务，返回task_id和状态
    - 如果没有，返回null
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        活跃任务信息或null
        
    Raises:
        HTTPException: 404 - 路线图不存在
        
    Example:
        ```json
        {
            "has_active_task": true,
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "current_step": "tutorial_generation",
            "created_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # 获取关联的任务
    task = await repo.get_task(metadata.task_id) if metadata.task_id else None
    
    # 只有当任务状态为 processing 或 human_review_pending 时才算活跃
    if task and task.status in ['processing', 'human_review_pending']:
        return {
            "has_active_task": True,
            "task_id": task.task_id,
            "status": task.status,
            "current_step": task.current_step,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
    else:
        return {
            "has_active_task": False,
            "task_id": None,
            "status": None,
            "current_step": None,
        }
