"""
用户服务

处理用户相关的业务逻辑：
- 用户画像管理
- 路线图历史查询
- 任务列表查询
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    ) -> Optional[UserProfileResponse]:
        """
        获取用户画像
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            
        Returns:
            用户画像 Schema 或 None
        """
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
        保存或更新用户画像
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            profile_data: 画像数据
            
        Returns:
            更新后的用户画像 Schema
        """
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
        
        # 批量获取进度（避免N+1查询）
        roadmap_ids = [r.roadmap_id for r in roadmaps]
        
        # 使用批量查询获取进度
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
        
        # 构建进度字典
        progress_dict = {row[0]: row[1] for row in progress_rows}
        
        # 构造响应
        result_list = []
        for roadmap in roadmaps:
            # 计算总概念数
            total_concepts = sum(
                len(module.get("concepts", []))
                for stage in roadmap.framework_data.get("stages", [])
                for module in stage.get("modules", [])
            )
            
            completed_concepts = progress_dict.get(roadmap.roadmap_id, 0)
            
            # 提取stages摘要
            stages = [
                StageSummary(
                    name=stage.get("name", ""),
                    description=stage.get("description"),
                    order=stage.get("order", idx),
                )
                for idx, stage in enumerate(roadmap.framework_data.get("stages", []))
            ]
            
            result_list.append(RoadmapHistoryItem(
                roadmap_id=roadmap.roadmap_id,
                title=roadmap.title,
                created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
                total_concepts=total_concepts,
                completed_concepts=completed_concepts,
                topic=roadmap.topic,
                status=roadmap.status,
                stages=stages,
            ))
        
        return RoadmapHistoryResponse(
            roadmaps=result_list,
            total=len(roadmaps),
            in_progress_count=0,  # TODO: 计算pending任务数
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
                error_message=task.error_message,
            ))
        
        # TODO: 实际统计各状态数量
        return TaskListResponse(
            tasks=result_list,
            total=len(tasks),
            pending_count=0,
            processing_count=0,
            completed_count=0,
            failed_count=0,
        )


def get_user_service() -> UserService:
    """获取UserService实例"""
    return UserService()

