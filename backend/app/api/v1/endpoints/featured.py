"""
Featured Roadmaps API

获取精选路线图，用于首页展示
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.db.session import get_db_readonly
from app.services.featured_service import FeaturedService

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.featured import (
    StageSummary,
    FeaturedRoadmapItem,
    FeaturedRoadmapsResponse,
)

router = APIRouter(prefix="/featured", tags=["featured"])
logger = structlog.get_logger()


@router.get("/roadmaps", response_model=FeaturedRoadmapsResponse)
async def get_featured_roadmaps(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_readonly),
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
    
    service = FeaturedService()
    
    # 1. 根据邮箱查找Featured用户
    featured_user = await service.get_featured_user(db, FEATURED_USER_EMAIL)
    
    if not featured_user:
        raise HTTPException(
            status_code=404,
            detail=f"Featured user with email {FEATURED_USER_EMAIL} not found. "
                   f"Please create this user first using the admin API."
        )
    
    user_id = featured_user.id
    
    # 2. 获取该用户的所有已完成路线图及Task
    roadmaps, tasks_by_roadmap = await service.get_featured_roadmaps(
        db, user_id, limit, offset
    )
    
    roadmap_items = []
    
    # 4. 转换路线图数据（优化版）
    for roadmap in roadmaps:
        framework_data = roadmap.framework_data or {}
        stages = framework_data.get("stages", [])
        
        # 优化：快速计算总概念数
        total_concepts = sum(
            len(module.get("concepts", []))
            for stage in stages
            for module in stage.get("modules", [])
        )
        
        # 从批量获取的 tasks 中获取 topic（无需额外查询）
        task = tasks_by_roadmap.get(roadmap.roadmap_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        # 优化：提取 stages 摘要（使用列表推导式）
        stage_summaries = [
            StageSummary(
                name=stage.get("name", ""),
                description=stage.get("description"),
                order=stage.get("order", idx + 1),
            )
            for idx, stage in enumerate(stages)
        ]
        
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

