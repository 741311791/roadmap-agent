"""
用户服务

处理用户相关的业务逻辑：
- 用户画像管理（带 Redis 缓存）
- 路线图历史查询
- 任务列表查询
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.crud.crud_progress import ProgressCRUD
from app.models.database import RoadmapMetadata, RoadmapTask, ConceptProgress, UserProfile
from app.schemas.user import (
    UserProfileResponse,
    RoadmapHistoryItem,
    RoadmapHistoryResponse,
    DeletedRoadmapsResponse,
    TaskListItem,
    TaskListResponse,
    StageSummary,
)
from app.core.cache import get_or_set_cache, invalidate_cache

logger = structlog.get_logger()


class UserService:
    """用户业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
        self.progress_crud = ProgressCRUD(ConceptProgress)
    
    async def get_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        use_cache: bool = True,
    ) -> Optional[UserProfileResponse]:
        """
        获取用户画像（带 Redis 缓存）
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            use_cache: 是否使用缓存，默认 True
            
        Returns:
            用户画像 Schema 或 None
        """
        cache_key = f"user_profile:{user_id}"
        
        if use_cache:
            try:
                # 尝试从缓存读取
                async def fetch_from_db():
                    result = await session.execute(
                        select(UserProfile).where(UserProfile.user_id == user_id)
                    )
                    profile = result.scalars().first()
                    
                    if not profile:
                        return None
                    
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
                
                # 使用 Cache-Aside 模式，TTL 1小时
                return await get_or_set_cache(
                    key=cache_key,
                    fetch_func=fetch_from_db,
                    model_type=UserProfileResponse,
                    ttl=3600,  # 1 小时
                )
            except Exception as e:
                logger.warning("user_profile_cache_error_fallback_to_db", error=str(e))
                # 缓存失败，降级到直接查数据库
        
        # 不使用缓存或缓存失败时，直接查数据库
        result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalars().first()
        
        if not profile:
            return None
        
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
    
    async def save_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        profile_data: dict,
    ) -> UserProfileResponse:
        """
        保存或更新用户画像（更新后使缓存失效）
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            profile_data: 画像数据
            
        Returns:
            更新后的用户画像 Schema
        """
        # 使缓存失效（更新前删除旧缓存）
        await invalidate_cache(f"user_profile:{user_id}")
        
        # 查询现有画像
        result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        existing = result.scalars().first()
        
        if existing:
            # 更新现有画像
            for key, value in profile_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            
            from app.models.database import beijing_now
            existing.updated_at = beijing_now()
            session.add(existing)
        else:
            # 创建新画像
            import uuid
            new_profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                **profile_data
            )
            session.add(new_profile)
            existing = new_profile
        
        await session.flush()
        await session.refresh(existing)
        
        return UserProfileResponse(
            user_id=existing.user_id,
            industry=existing.industry,
            current_role=existing.current_role,
            tech_stack=existing.tech_stack,
            primary_language=existing.primary_language,
            secondary_language=existing.secondary_language,
            weekly_commitment_hours=existing.weekly_commitment_hours,
            learning_style=existing.learning_style,
            ai_personalization=existing.ai_personalization,
        )
    
    async def get_user_roadmaps(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> RoadmapHistoryResponse:
        """
        获取用户的路线图列表（包含进度信息）
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数
            
        Returns:
            路线图历史响应 Schema
        """
        # 获取路线图列表
        roadmaps = await self.roadmap_crud.get_by_user(
            session, user_id, skip=skip, limit=limit
        )
        
        if not roadmaps:
            return RoadmapHistoryResponse(roadmaps=[], total=0, in_progress_count=0)
        
        # 批量获取所需数据（避免 N+1 查询）
        roadmap_ids = [r.roadmap_id for r in roadmaps]
        
        # 优化：使用单次查询获取任务信息和进度
        from app.models.database import RoadmapTask
        from sqlalchemy import func, outerjoin
        
        # 批量查询任务信息
        task_result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id.in_(roadmap_ids))
        )
        tasks = task_result.scalars().all()
        task_dict = {task.roadmap_id: task for task in tasks}
        
        # 批量查询进度（使用 GROUP BY 聚合）
        progress_result = await session.execute(
            select(
                ConceptProgress.roadmap_id,
                func.count(ConceptProgress.id).label("completed_count"),
            )
            .where(
                ConceptProgress.user_id == user_id,
                ConceptProgress.roadmap_id.in_(roadmap_ids),
                ConceptProgress.is_completed == True,
            )
            .group_by(ConceptProgress.roadmap_id)
        )
        progress_rows = progress_result.fetchall()
        progress_dict = {row[0]: row[1] for row in progress_rows}
        
        # 构造响应
        result_list = []
        for roadmap in roadmaps:
            framework_data = roadmap.framework_data
            stages_data = framework_data.get("stages", [])
            
            # 优化：只在需要时计算总概念数
            # Home 页面只需要前几个，无需深度遍历所有 modules
            total_concepts = sum(
                len(module.get("concepts", []))
                for stage in stages_data
                for module in stage.get("modules", [])
            )
            
            completed_concepts = progress_dict.get(roadmap.roadmap_id, 0)
            
            # 优化：提取 stages 摘要（只提取必要字段）
            stages = [
                StageSummary(
                    name=stage.get("name", ""),
                    description=stage.get("description"),
                    order=stage.get("order", idx + 1),  # 确保从 1 开始
                )
                for idx, stage in enumerate(stages_data)
            ]
            
            # 从 framework_data 中提取 topic（优先使用 topic，降级到 title）
            topic = framework_data.get("topic") or framework_data.get("title", "").lower()
            
            # 从 task 获取 status 和其他任务信息
            task = task_dict.get(roadmap.roadmap_id)
            status = task.status if task else "completed"  # 如果没有任务记录，默认为 completed
            task_id = task.task_id if task else None
            task_status = task.status if task else None
            current_step = task.current_step if task else None
            
            result_list.append(RoadmapHistoryItem(
                roadmap_id=roadmap.roadmap_id,
                title=roadmap.title,
                created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
                total_concepts=total_concepts,
                completed_concepts=completed_concepts,
                topic=topic,
                status=status,
                stages=stages,
                task_id=task_id,
                task_status=task_status,
                current_step=current_step,
            ))
        
        # 统计进行中的任务数量
        from sqlalchemy import func
        in_progress_result = await session.execute(
            select(func.count(RoadmapTask.task_id))
            .where(
                RoadmapTask.user_id == user_id,
                RoadmapTask.status.in_(["pending", "processing"])
            )
        )
        in_progress_count = in_progress_result.scalar() or 0
        
        return RoadmapHistoryResponse(
            roadmaps=result_list,
            total=len(roadmaps),
            in_progress_count=in_progress_count,
        )
    
    async def get_deleted_roadmaps(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> DeletedRoadmapsResponse:
        """
        获取用户的已删除路线图
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数
            
        Returns:
            已删除路线图响应 Schema
        """
        # 查询已删除的路线图
        result = await session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.user_id == user_id)
            .where(RoadmapMetadata.deleted_at.is_not(None))
            .order_by(RoadmapMetadata.deleted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        roadmaps = list(result.scalars().all())
        
        if not roadmaps:
            return DeletedRoadmapsResponse(roadmaps=[], total=0)
        
        # 批量获取进度
        roadmap_ids = [r.roadmap_id for r in roadmaps]
        
        from sqlalchemy import func
        progress_result = await session.execute(
            select(
                ConceptProgress.roadmap_id,
                func.count(ConceptProgress.id).label("completed_count"),
            )
            .where(
                ConceptProgress.user_id == user_id,
                ConceptProgress.roadmap_id.in_(roadmap_ids),
                ConceptProgress.is_completed == True,
            )
            .group_by(ConceptProgress.roadmap_id)
        )
        progress_rows = progress_result.fetchall()
        progress_dict = {row[0]: row[1] for row in progress_rows}
        
        # 构造响应
        result_list = []
        for roadmap in roadmaps:
            total_concepts = sum(
                len(module.get("concepts", []))
                for stage in roadmap.framework_data.get("stages", [])
                for module in stage.get("modules", [])
            )
            
            result_list.append(RoadmapHistoryItem(
                roadmap_id=roadmap.roadmap_id,
                title=roadmap.title,
                created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
                deleted_at=roadmap.deleted_at.isoformat() if roadmap.deleted_at else None,
                total_concepts=total_concepts,
                completed_concepts=progress_dict.get(roadmap.roadmap_id, 0),
                topic=roadmap.topic,
                status="deleted",
            ))
        
        return DeletedRoadmapsResponse(roadmaps=result_list, total=len(roadmaps))
    
    async def get_user_tasks(
        self,
        session: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> TaskListResponse:
        """
        获取用户的任务列表
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            status: 任务状态过滤
            task_type: 任务类型过滤
            skip: 跳过记录数
            limit: 返回记录数
            
        Returns:
            任务列表响应 Schema
        """
        # 构建查询
        query = select(RoadmapTask).where(RoadmapTask.user_id == user_id)
        
        if status:
            query = query.where(RoadmapTask.status == status)
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)
        
        query = query.order_by(RoadmapTask.created_at.desc()).offset(skip).limit(limit)
        
        result = await session.execute(query)
        tasks = list(result.scalars().all())
        
        # 构造响应
        result_list = []
        for task in tasks:
            # 从 user_request 提取 title
            title = "Untitled Task"
            if task.user_request:
                learning_goal = task.user_request.get("preferences", {}).get("learning_goal")
                if learning_goal:
                    title = learning_goal[:100]  # 限制长度
            
            result_list.append(TaskListItem(
                task_id=task.task_id,
                roadmap_id=task.roadmap_id,
                status=task.status,
                current_step=task.current_step or "",
                task_type=task.task_type or "",
                concept_id=task.concept_id,
                content_type=task.content_type,
                title=title,
                created_at=task.created_at.isoformat() if task.created_at else "",
                updated_at=task.updated_at.isoformat() if task.updated_at else "",
                completed_at=task.completed_at.isoformat() if task.completed_at else None,
                error_message=task.error_message,
            ))
        
        # 统计各状态的任务数量
        status_stats_result = await session.execute(
            select(
                RoadmapTask.status,
                func.count(RoadmapTask.task_id).label("count")
            )
            .where(RoadmapTask.user_id == user_id)
            .group_by(RoadmapTask.status)
        )
        status_stats = {row.status: row.count for row in status_stats_result.fetchall()}
        
        # 获取各状态计数（包含 human_review_pending 和 partial_failure）
        pending_count = status_stats.get("pending", 0)
        processing_count = (
            status_stats.get("processing", 0) + 
            status_stats.get("human_review_pending", 0)  # human_review_pending 算作 processing
        )
        completed_count = (
            status_stats.get("completed", 0) + 
            status_stats.get("partial_failure", 0)  # partial_failure 算作 completed
        )
        failed_count = status_stats.get("failed", 0)
        
        return TaskListResponse(
            tasks=result_list,
            total=len(tasks),
            pending_count=pending_count,
            processing_count=processing_count,
            completed_count=completed_count,
            failed_count=failed_count,
        )


def get_user_service() -> UserService:
    """获取UserService实例"""
    return UserService()

