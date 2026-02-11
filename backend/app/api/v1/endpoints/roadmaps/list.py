"""
路线图列表查询 API 端点

提供用户路线图列表、回收站列表、精选路线图列表查询功能。

重构变更：
- ✅ 合并多个文件的列表查询接口：
  - users/users.py: 用户路线图列表、回收站列表
  - roadmaps/featured.py: 精选路线图
- ✅ 统一到 /roadmaps prefix
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import CurrentSession, CurrentUserService
from app.db.session import get_db_readonly
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.services.roadmaps.featured_service import FeaturedService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.user import RoadmapHistoryResponse
from app.schemas.featured import (
    StageSummary,
    FeaturedRoadmapItem,
    FeaturedRoadmapsResponse,
)

router = APIRouter(prefix="/roadmaps", tags=["roadmap-list"])
logger = structlog.get_logger()


@router.get("/my", response_model=ResponseSchemaModel[RoadmapHistoryResponse])
async def get_user_roadmaps(
    db: CurrentSession,
    service: CurrentUserService,
    current_user: User = Depends(current_active_user),
    limit: int = 50,
    offset: int = 0,
) -> ResponseSchemaModel[RoadmapHistoryResponse]:
    """
    获取当前用户的路线图列表（只包括已生成完成的路线图）
    
    Args:
        db: 数据库会话
        current_user: 当前用户（从JWT提取）
        service: 用户服务
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        用户的路线图列表（从 roadmap_metadata 表查询）
        
    Note:
        学习进度从 concept_progress 表获取，而不是 content_status 字段。
        content_status 表示内容生成状态，concept_progress 表示用户学习进度。
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "roadmaps": [
                    {
                        "roadmap_id": "python-guide-xxx",
                        "title": "Python Web Development",
                        "created_at": "2024-01-01T00:00:00Z",
                        "total_concepts": 20,
                        "completed_concepts": 5,
                        "topic": "python web development",
                        "status": "learning"
                    }
                ],
                "total": 1,
                "in_progress_count": 0
            }
        }
        ```
    """
    user_id = current_user.id  # 从JWT提取user_id
    logger.info("get_user_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    result = await service.get_user_roadmaps(db, user_id, skip=offset, limit=limit)
    
    return response_base.success(data=result)


@router.get("/trash", response_model=ResponseSchemaModel[RoadmapHistoryResponse])
async def get_deleted_roadmaps(
    db: CurrentSession,
    service: CurrentUserService,
    current_user: User = Depends(current_active_user),
    limit: int = 50,
    offset: int = 0,
) -> ResponseSchemaModel[RoadmapHistoryResponse]:
    """
    获取当前用户回收站中的路线图列表
    
    Args:
        db: 数据库会话
        current_user: 当前用户（从JWT提取）
        service: 用户服务
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        回收站中的路线图列表，按删除时间降序排列
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "roadmaps": [
                    {
                        "roadmap_id": "python-guide-xxx",
                        "title": "Python Web Development",
                        "created_at": "2024-01-01T00:00:00Z",
                        "total_concepts": 20,
                        "completed_concepts": 5,
                        "topic": "python web development",
                        "status": "deleted",
                        "deleted_at": "2024-01-15T00:00:00Z",
                        "deleted_by": "user-123"
                    }
                ],
                "total": 1,
                "in_progress_count": 0
            }
        }
        ```
    """
    user_id = current_user.id  # 从JWT提取user_id
    logger.info("get_deleted_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    result = await service.get_deleted_roadmaps(db, user_id, skip=offset, limit=limit)
    
    return response_base.success(data=result)


@router.get("/featured", response_model=FeaturedRoadmapsResponse)
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

