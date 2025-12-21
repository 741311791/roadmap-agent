"""
Featured Roadmaps API

获取精选路线图，用于首页展示
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.db.session import get_db
from app.models.database import User
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.repositories.progress_repo import ProgressRepository
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/featured", tags=["featured"])
logger = structlog.get_logger()


class StageSummary(BaseModel):
    """阶段摘要信息"""
    name: str
    description: Optional[str] = None
    order: int


class FeaturedRoadmapItem(BaseModel):
    """精选路线图条目"""
    roadmap_id: str
    title: str
    created_at: str
    total_concepts: int
    completed_concepts: int = 0
    topic: Optional[str] = None
    status: str = "completed"
    stages: Optional[List[StageSummary]] = None


class FeaturedRoadmapsResponse(BaseModel):
    """精选路线图列表响应"""
    roadmaps: List[FeaturedRoadmapItem]
    total: int
    featured_user_id: str
    featured_user_email: str


@router.get("/roadmaps", response_model=FeaturedRoadmapsResponse)
async def get_featured_roadmaps(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取精选路线图列表
    
    从配置的Featured User (admin@example.com) 获取已完成的路线图，
    用于首页Featured Roadmaps模块展示。
    
    Args:
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        db: 数据库会话
        
    Returns:
        精选路线图列表（只包含已完成且未删除的路线图）
        
    Raises:
        HTTPException: 404 - Featured用户不存在
        
    Example:
        ```json
        {
            "roadmaps": [
                {
                    "roadmap_id": "roadmap-001",
                    "title": "Python Web Development",
                    "created_at": "2024-01-01T00:00:00",
                    "total_concepts": 28,
                    "completed_concepts": 0,
                    "topic": "python web",
                    "status": "completed"
                }
            ],
            "total": 1,
            "featured_user_id": "user-001",
            "featured_user_email": "admin@example.com"
        }
        ```
    """
    # Featured用户邮箱（硬编码，将来可以从配置文件读取）
    FEATURED_USER_EMAIL = "admin@example.com"
    
    logger.info("get_featured_roadmaps_requested", 
                email=FEATURED_USER_EMAIL,
                limit=limit, 
                offset=offset)
    
    # 1. 根据邮箱查找Featured用户
    result = await db.execute(
        select(User).where(User.email == FEATURED_USER_EMAIL)
    )
    featured_user = result.scalar_one_or_none()
    
    if not featured_user:
        logger.warning("featured_user_not_found", email=FEATURED_USER_EMAIL)
        raise HTTPException(
            status_code=404,
            detail=f"Featured user with email {FEATURED_USER_EMAIL} not found. "
                   f"Please create this user first using the admin API."
        )
    
    user_id = featured_user.id
    logger.info("featured_user_found", 
                user_id=user_id,
                email=featured_user.email,
                username=featured_user.username)
    
    # 2. 获取该用户的所有已完成路线图（只包含未删除的）
    repo = RoadmapRepository(db)
    roadmaps = await repo.get_roadmaps_by_user(
        user_id, 
        limit=limit, 
        offset=offset
    )
    
    roadmap_items = []
    
    # 3. 转换路线图数据
    for roadmap in roadmaps:
        # 从 framework_data 中提取概念信息
        framework_data = roadmap.framework_data or {}
        stages = framework_data.get("stages", [])
        
        total_concepts = 0
        
        # 统计总概念数
        for stage in stages:
            modules = stage.get("modules", [])
            for module in modules:
                concepts = module.get("concepts", [])
                total_concepts += len(concepts)
        
        # 从 user_request 中提取 topic
        task = await repo.get_task_by_roadmap_id(roadmap.roadmap_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        # 提取 stages 信息
        stage_summaries = []
        for stage in stages:
            stage_summaries.append(StageSummary(
                name=stage.get("name", ""),
                description=stage.get("description"),
                order=stage.get("order", len(stage_summaries) + 1),
            ))
        
        # Featured路线图默认为completed状态（因为是精选内容）
        roadmap_items.append(FeaturedRoadmapItem(
            roadmap_id=roadmap.roadmap_id,
            title=roadmap.title,
            created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
            total_concepts=total_concepts,
            completed_concepts=0,  # Featured路线图不显示完成进度
            topic=topic,
            status="completed",
            stages=stage_summaries if stage_summaries else None,
        ))
    
    logger.info("featured_roadmaps_retrieved", 
                count=len(roadmap_items),
                user_id=user_id)
    
    return FeaturedRoadmapsResponse(
        roadmaps=roadmap_items,
        total=len(roadmap_items),
        featured_user_id=user_id,
        featured_user_email=featured_user.email,
    )

