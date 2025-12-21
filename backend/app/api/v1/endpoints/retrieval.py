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
