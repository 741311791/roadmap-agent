"""
用户画像相关 API 端点

提供用户画像的获取、保存、路线图历史、任务列表等功能。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.repositories.progress_repo import ProgressRepository

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型 - 用户画像
# ============================================================


class TechStackItem(BaseModel):
    """技术栈项"""
    technology: str = Field(..., description="技术名称")
    proficiency: str = Field(..., description="熟练程度: beginner, intermediate, expert")
    capability_analysis: Optional[dict] = Field(None, description="能力分析结果（可选）")


class UserProfileRequest(BaseModel):
    """用户画像请求体"""
    # 职业背景
    industry: Optional[str] = Field(None, description="所属行业")
    current_role: Optional[str] = Field(None, description="当前职位")
    # 技术栈
    tech_stack: List[TechStackItem] = Field(default=[], description="技术栈列表")
    # 语言偏好
    primary_language: str = Field(default="zh", description="主要语言")
    secondary_language: Optional[str] = Field(None, description="次要语言")
    # 学习习惯
    weekly_commitment_hours: int = Field(default=10, ge=1, le=168, description="每周学习时间")
    learning_style: List[str] = Field(default=[], description="学习风格: visual, text, audio, hands_on")
    # AI 个性化
    ai_personalization: bool = Field(default=True, description="是否启用 AI 个性化")


class UserProfileResponse(BaseModel):
    """用户画像响应体"""
    user_id: str
    industry: Optional[str] = None
    current_role: Optional[str] = None
    tech_stack: List[dict] = []
    primary_language: str = "zh"
    secondary_language: Optional[str] = None
    weekly_commitment_hours: int = 10
    learning_style: List[str] = []
    ai_personalization: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================
# Pydantic 模型 - 路线图历史
# ============================================================


class StageSummary(BaseModel):
    """Stage 摘要信息，用于卡片展示"""
    name: str
    description: Optional[str] = None
    order: int


class RoadmapHistoryItem(BaseModel):
    """路线图历史项"""
    roadmap_id: str
    title: str
    created_at: str
    total_concepts: int
    completed_concepts: int
    topic: Optional[str] = None
    status: Optional[str] = None
    # Stages 摘要信息
    stages: Optional[list[StageSummary]] = None
    # 新增字段：用于支持未完成路线图的恢复
    task_id: Optional[str] = None
    task_status: Optional[str] = None  # processing, pending, human_review_pending 等
    current_step: Optional[str] = None  # intent_analysis, curriculum_design 等
    # 软删除相关字段
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None


class RoadmapHistoryResponse(BaseModel):
    """用户路线图历史响应"""
    roadmaps: list[RoadmapHistoryItem]
    total: int
    # 新增字段：进行中的任务数量
    in_progress_count: int = 0


# ============================================================
# Pydantic 模型 - 任务列表
# ============================================================


class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    status: str  # pending, processing, completed, failed
    current_step: str
    title: str  # 从 user_request 提取
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    roadmap_id: Optional[str] = None  # 如果任务成功，关联的路线图ID


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskListItem]
    total: int
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int


# ============================================================
# 路由端点 - 用户画像
# ============================================================


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
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
    
    repo = RoadmapRepository(db)
    profile = await repo.get_user_profile(user_id)
    
    if profile:
        return UserProfileResponse(
            user_id=profile.user_id,
            industry=profile.industry,
            current_role=profile.current_role,
            tech_stack=profile.tech_stack,
            primary_language=profile.primary_language,
            secondary_language=profile.secondary_language,
            weekly_commitment_hours=profile.weekly_commitment_hours,
            learning_style=profile.learning_style,
            ai_personalization=profile.ai_personalization,
            created_at=profile.created_at.isoformat() if profile.created_at else None,
            updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
        )
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
    request: UserProfileRequest,
    db: AsyncSession = Depends(get_db),
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
    
    repo = RoadmapRepository(db)
    
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
    
    profile = await repo.save_user_profile(user_id, profile_data)
    
    return UserProfileResponse(
        user_id=profile.user_id,
        industry=profile.industry,
        current_role=profile.current_role,
        tech_stack=profile.tech_stack,
        primary_language=profile.primary_language,
        secondary_language=profile.secondary_language,
        weekly_commitment_hours=profile.weekly_commitment_hours,
        learning_style=profile.learning_style,
        ai_personalization=profile.ai_personalization,
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


# ============================================================
# 路由端点 - 路线图历史
# ============================================================


@router.get("/{user_id}/roadmaps", response_model=RoadmapHistoryResponse)
async def get_user_roadmaps(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
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
    
    repo = RoadmapRepository(db)
    progress_repo = ProgressRepository(db)
    
    # 获取已保存的路线图
    roadmaps = await repo.get_roadmaps_by_user(user_id, limit=limit, offset=offset)
    
    # 批量获取所有路线图的 Task 和进度（解决 N+1 查询问题）
    roadmap_ids = [r.roadmap_id for r in roadmaps]
    tasks_by_roadmap = await repo.get_tasks_by_roadmap_ids_batch(roadmap_ids)
    completed_counts = await progress_repo.get_completed_counts_batch(user_id, roadmap_ids)
    
    roadmap_items = []
    
    # 转换已保存的路线图
    for roadmap in roadmaps:
        # 从 framework_data 中提取概念信息
        framework_data = roadmap.framework_data or {}
        stages_data = framework_data.get("stages", [])
        
        total_concepts = 0
        
        # 统计总概念数，同时提取 Stage 摘要
        stage_summaries = []
        for stage in stages_data:
            modules = stage.get("modules", [])
            for module in modules:
                concepts = module.get("concepts", [])
                total_concepts += len(concepts)
            
            # 提取 Stage 摘要信息
            stage_summaries.append(StageSummary(
                name=stage.get("name", ""),
                description=stage.get("description"),
                order=stage.get("order", 0),
            ))
        
        # 从批量获取的数据中获取已完成概念数（无需额外查询）
        completed_concepts = completed_counts.get(roadmap.roadmap_id, 0)
        
        # 从批量获取的 tasks 中获取 topic（无需额外查询）
        task = tasks_by_roadmap.get(roadmap.roadmap_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        # 根据完成度确定状态
        if completed_concepts == total_concepts and total_concepts > 0:
            status = "completed"
        else:
            status = "learning"
        
        roadmap_items.append(RoadmapHistoryItem(
            roadmap_id=roadmap.roadmap_id,
            title=roadmap.title,
            created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
            total_concepts=total_concepts,
            completed_concepts=completed_concepts,
            topic=topic,
            status=status,
            stages=stage_summaries if stage_summaries else None,
        ))
    
    return RoadmapHistoryResponse(
        roadmaps=roadmap_items,
        total=len(roadmap_items),
    )


@router.get("/{user_id}/roadmaps/trash", response_model=RoadmapHistoryResponse)
async def get_deleted_roadmaps(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
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
    
    repo = RoadmapRepository(db)
    progress_repo = ProgressRepository(db)
    
    # 获取已删除的路线图
    deleted_roadmaps = await repo.get_deleted_roadmaps(user_id, limit=limit, offset=offset)
    
    # 批量获取所有路线图的 Task 和进度（解决 N+1 查询问题）
    roadmap_ids = [r.roadmap_id for r in deleted_roadmaps]
    tasks_by_roadmap = await repo.get_tasks_by_roadmap_ids_batch(roadmap_ids)
    completed_counts = await progress_repo.get_completed_counts_batch(user_id, roadmap_ids)
    
    roadmap_items = []
    
    # 转换已删除的路线图
    for roadmap in deleted_roadmaps:
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
        
        # 从批量获取的数据中获取已完成概念数（无需额外查询）
        completed_concepts = completed_counts.get(roadmap.roadmap_id, 0)
        
        # 从批量获取的 tasks 中获取 topic（无需额外查询）
        task = tasks_by_roadmap.get(roadmap.roadmap_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        roadmap_items.append(RoadmapHistoryItem(
            roadmap_id=roadmap.roadmap_id,
            title=roadmap.title,
            created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
            total_concepts=total_concepts,
            completed_concepts=completed_concepts,
            topic=topic,
            status="deleted",
            task_id=task.task_id if task else None,
            task_status=None,
            current_step=None,
            deleted_at=roadmap.deleted_at.isoformat() if roadmap.deleted_at else None,
            deleted_by=roadmap.deleted_by,
        ))
    
    return RoadmapHistoryResponse(
        roadmaps=roadmap_items,
        total=len(roadmap_items),
        in_progress_count=0,
    )


# ============================================================
# 路由端点 - 任务列表
# ============================================================


@router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def get_user_tasks(
    user_id: str,
    status: Optional[str] = None,  # 筛选：pending, processing, completed, failed
    task_type: Optional[str] = None,  # 筛选：creation, retry_tutorial, retry_resources, retry_quiz, retry_batch
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
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
    
    repo = RoadmapRepository(db)
    
    # 查询任务（应用task_type过滤）
    tasks = await repo.get_tasks_by_user(user_id, status=status, task_type=task_type, limit=limit, offset=offset)
    
    # 使用聚合查询统计各状态数量（性能优化：避免加载所有任务到内存）
    status_counts = await repo.count_tasks_by_status(user_id, task_type=task_type)
    
    # 将 human_review_pending、human_review_required、running 等状态归类到 processing
    # 将 approved、rejected 等状态归类到 completed/failed
    stats = {
        "pending": status_counts.get("pending", 0),
        "processing": (
            status_counts.get("processing", 0) +
            status_counts.get("running", 0) +
            status_counts.get("human_review_pending", 0) +
            status_counts.get("human_review_required", 0)
        ),
        "completed": (
            status_counts.get("completed", 0) +
            status_counts.get("partial_failure", 0) +
            status_counts.get("approved", 0)
        ),
        "failed": (
            status_counts.get("failed", 0) +
            status_counts.get("rejected", 0)
        ),
    }
    
    task_items = []
    for task in tasks:
        # 从 user_request 中提取标题
        title = "Generating roadmap"
        if task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            if learning_goal:
                title = learning_goal[:100]
        
        task_items.append(TaskListItem(
            task_id=task.task_id,
            status=task.status,
            current_step=task.current_step,
            title=title,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=task.error_message,
            roadmap_id=task.roadmap_id,
        ))
    
    return TaskListResponse(
        tasks=task_items,
        total=len(task_items),
        pending_count=stats["pending"],
        processing_count=stats["processing"],
        completed_count=stats["completed"],
        failed_count=stats["failed"],
    )
