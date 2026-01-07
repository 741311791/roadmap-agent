"""
用户画像相关 API 端点

提供用户画像的获取、保存、路线图历史、任务列表等功能。
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import CurrentSession, CurrentUserService

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.user import (
    TechStackItem,
    UserProfileRequest,
    UserProfileResponse,
    StageSummary,
    RoadmapHistoryItem,
    RoadmapHistoryResponse,
    TaskListItem,
    TaskListResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()


# ============================================================
# 路由端点 - 用户画像
# ============================================================


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    session: CurrentSession,
    service: CurrentUserService,
):
    """
    获取用户画像
    
    Args:
        user_id: 用户 ID
        db: 数据库会话
        
    Returns:
        用户画像数据，如果不存在则返回默认值
        
    Example:
        ```json
        {
            "user_id": "user-123",
            "industry": "Technology",
            "current_role": "Software Engineer",
            "tech_stack": [
                {
                    "technology": "Python",
                    "proficiency": "intermediate",
                    "capability_analysis": {}
                }
            ],
            "primary_language": "zh",
            "weekly_commitment_hours": 10,
            "learning_style": ["text", "hands_on"],
            "ai_personalization": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    logger.info("get_user_profile_requested", user_id=user_id)
    
    profile = await service.get_user_profile(session, user_id)
    
    if profile:
        return profile
    else:
        # 返回默认画像
        return UserProfileResponse(
            user_id=user_id,
            tech_stack=[],
            learning_style=[],
        )


@router.put("/{user_id}/profile", response_model=UserProfileResponse)
async def save_user_profile(
    user_id: str,
    session: CurrentSession,
    service: CurrentUserService,
    request: UserProfileRequest = ...,
):
    """
    保存或更新用户画像
    
    Args:
        user_id: 用户 ID
        request: 用户画像数据
        db: 数据库会话
        
    Returns:
        保存后的用户画像
        
    Example Request:
        ```json
        {
            "industry": "Technology",
            "current_role": "Software Engineer",
            "tech_stack": [
                {
                    "technology": "Python",
                    "proficiency": "intermediate"
                }
            ],
            "primary_language": "zh",
            "weekly_commitment_hours": 15,
            "learning_style": ["text", "hands_on"],
            "ai_personalization": true
        }
        ```
    """
    logger.info(
        "save_user_profile_requested",
        user_id=user_id,
        tech_stack_count=len(request.tech_stack),
    )
    
    # 转换为字典格式
    profile_data = {
        "industry": request.industry,
        "current_role": request.current_role,
        "tech_stack": [item.model_dump() for item in request.tech_stack],
        "primary_language": request.primary_language,
        "secondary_language": request.secondary_language,
        "weekly_commitment_hours": request.weekly_commitment_hours,
        "learning_style": request.learning_style,
        "ai_personalization": request.ai_personalization,
    }
    
    profile = await service.save_user_profile(session, user_id, profile_data)
    await session.commit()
    
    return profile


# ============================================================
# 路由端点 - 路线图历史
# ============================================================


@router.get("/{user_id}/roadmaps", response_model=RoadmapHistoryResponse)
async def get_user_roadmaps(
    user_id: str,
    session: CurrentSession,
    service: CurrentUserService,
    limit: int = 50,
    offset: int = 0,
):
    """
    获取用户的路线图列表（只包括已生成完成的路线图）
    
    Args:
        user_id: 用户 ID
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        db: 数据库会话
        
    Returns:
        用户的路线图列表（从 roadmap_metadata 表查询）
        
    Note:
        学习进度从 concept_progress 表获取，而不是 content_status 字段。
        content_status 表示内容生成状态，concept_progress 表示用户学习进度。
        
    Example:
        ```json
        {
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
        ```
    """
    logger.info("get_user_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    return await service.get_user_roadmaps(session, user_id, skip=offset, limit=limit)


@router.get("/{user_id}/roadmaps/trash", response_model=RoadmapHistoryResponse)
async def get_deleted_roadmaps(
    user_id: str,
    session: CurrentSession,
    service: CurrentUserService,
    limit: int = 50,
    offset: int = 0,
):
    """
    获取用户回收站中的路线图列表
    
    Args:
        user_id: 用户 ID
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        db: 数据库会话
        
    Returns:
        回收站中的路线图列表，按删除时间降序排列
        
    Example:
        ```json
        {
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
        ```
    """
    logger.info("get_deleted_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    return await service.get_deleted_roadmaps(session, user_id, skip=offset, limit=limit)


# ============================================================
# 路由端点 - 任务列表
# ============================================================


@router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def get_user_tasks(
    user_id: str,
    session: CurrentSession,
    service: CurrentUserService,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    获取用户的任务列表，支持按状态和任务类型筛选
    
    Args:
        user_id: 用户 ID
        status: 任务状态筛选（可选）：pending, processing, completed, failed
        task_type: 任务类型筛选（可选）：creation, retry_tutorial, retry_resources, retry_quiz, retry_batch
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        db: 数据库会话
        
    Returns:
        任务列表及各状态统计
        
    状态归类说明：
        - pending: 仅 pending
        - processing: processing, running, human_review_pending, human_review_required
        - completed: completed, partial_failure, approved
        - failed: failed, rejected
        
    Example:
        ```json
        {
            "tasks": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "human_review_pending",
                    "current_step": "human_review",
                    "title": "Python Web Development",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:01:00Z",
                    "completed_at": null,
                    "error_message": null,
                    "roadmap_id": "python-guide-xxx"
                }
            ],
            "total": 1,
            "pending_count": 0,
            "processing_count": 1,
            "completed_count": 5,
            "failed_count": 0
        }
        ```
    """
    logger.info("get_user_tasks_requested", user_id=user_id, status=status, task_type=task_type, limit=limit, offset=offset)
    
    # 调用Service层（Service 已返回 Schema，无需手动转换）
    return await service.get_user_tasks(
        session, user_id, status=status, task_type=task_type, skip=offset, limit=limit
    )
