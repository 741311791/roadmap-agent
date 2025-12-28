"""
路线图元数据 Repository

负责 RoadmapMetadata 表的数据访问操作。

职责范围：
- 路线图元数据的 CRUD 操作
- 路线图查询（根据 ID、用户等）
- 路线图 ID 唯一性检查

不包含：
- 教程、资源、测验数据（各自独立 Repository）
- 任务状态管理（在 TaskRepository）
- 需求分析数据（在 IntentAnalysisRepository）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import RoadmapMetadata
from app.models.domain import RoadmapFramework
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class RoadmapMetadataRepository(BaseRepository[RoadmapMetadata]):
    """
    路线图元数据数据访问层
    
    管理路线图元数据（不包含详细教程内容）。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RoadmapMetadata)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_roadmap_id(self, roadmap_id: str) -> Optional[RoadmapMetadata]:
        """
        根据 roadmap_id 查询路线图元数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            元数据记录，如果不存在则返回 None
        """
        return await self.get_by_id(roadmap_id)
    
    async def roadmap_id_exists(self, roadmap_id: str) -> bool:
        """
        检查 roadmap_id 是否已存在于数据库中
        
        Args:
            roadmap_id: 要检查的路线图 ID
            
        Returns:
            True 如果存在，False 如果不存在
        """
        return await self.exists(roadmap_id=roadmap_id)
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RoadmapMetadata]:
        """
        获取用户的所有路线图列表
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            路线图元数据列表（按创建时间降序排列，最新的在前）
        """
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.user_id == user_id)
            .order_by(RoadmapMetadata.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        roadmaps = list(result.scalars().all())
        
        logger.debug(
            "roadmaps_listed_by_user",
            user_id=user_id,
            count=len(roadmaps),
        )
        
        return roadmaps
    
    async def list_by_task(self, task_id: str) -> List[RoadmapMetadata]:
        """
        根据任务 ID 查询关联的路线图列表
        
        通常一个任务对应一个路线图，但支持多个（如重试生成）。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            路线图元数据列表
        """
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.task_id == task_id)
            .order_by(RoadmapMetadata.created_at.desc())
        )
        
        roadmaps = list(result.scalars().all())
        
        logger.debug(
            "roadmaps_listed_by_task",
            task_id=task_id,
            count=len(roadmaps),
        )
        
        return roadmaps
    
    async def count_by_user(self, user_id: str) -> int:
        """
        统计用户的路线图数量
        
        Args:
            user_id: 用户 ID
            
        Returns:
            路线图数量
        """
        return await self.count(user_id=user_id)
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
        framework: RoadmapFramework,
    ) -> RoadmapMetadata:
        """
        保存路线图元数据（如果存在则更新，不存在则插入）
        
        Args:
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            framework: 路线图框架
            
        Returns:
            保存的元数据记录
        """
        # 检查是否已存在
        existing = await self.get_by_roadmap_id(roadmap_id)
        
        if existing:
            # 更新现有记录（使用 ORM 对象更新以确保 JSON 字段变更被追踪）
            from sqlalchemy.orm.attributes import flag_modified
            
            existing.user_id = user_id
            existing.title = framework.title
            existing.total_estimated_hours = framework.total_estimated_hours
            existing.recommended_completion_weeks = framework.recommended_completion_weeks
            existing.framework_data = framework.model_dump()
            
            # 关键修复：显式标记 JSON 字段已修改
            # SQLAlchemy 默认无法检测 JSON 列的变更，需要手动标记
            flag_modified(existing, "framework_data")
            
            await self.session.flush()
            await self.session.refresh(existing)
            
            logger.info(
                "roadmap_metadata_updated",
                roadmap_id=roadmap_id,
                user_id=user_id,
            )
            
            return existing
        else:
            # 创建新记录
            metadata = RoadmapMetadata(
                roadmap_id=roadmap_id,
                user_id=user_id,
                title=framework.title,
                total_estimated_hours=framework.total_estimated_hours,
                recommended_completion_weeks=framework.recommended_completion_weeks,
                framework_data=framework.model_dump(),
            )
            
            await self.create(metadata, flush=True)
            
            logger.info(
                "roadmap_metadata_saved",
                roadmap_id=roadmap_id,
                user_id=user_id,
            )
            
            return metadata
    
    async def update_framework_data(
        self,
        roadmap_id: str,
        framework: RoadmapFramework,
    ) -> bool:
        """
        更新路线图的框架数据
        
        Args:
            roadmap_id: 路线图 ID
            framework: 新的路线图框架
            
        Returns:
            True 如果更新成功，False 如果路线图不存在
        """
        from sqlalchemy.orm.attributes import flag_modified
        
        # 获取现有记录
        existing = await self.get_by_roadmap_id(roadmap_id)
        
        if not existing:
            return False
        
        # 更新字段
        existing.title = framework.title
        existing.total_estimated_hours = framework.total_estimated_hours
        existing.recommended_completion_weeks = framework.recommended_completion_weeks
        existing.framework_data = framework.model_dump()
        
        # 关键修复：显式标记 JSON 字段已修改
        # SQLAlchemy 默认无法检测 JSON 列的变更，需要手动标记
        flag_modified(existing, "framework_data")
        
        await self.session.flush()
        
        logger.info(
            "roadmap_framework_data_updated",
            roadmap_id=roadmap_id,
        )
        
        return True
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_roadmap(self, roadmap_id: str) -> bool:
        """
        删除路线图元数据
        
        注意：如果设置了外键级联删除（ON DELETE CASCADE），
        关联的教程、资源、测验数据也会被删除。
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            True 如果删除成功，False 如果路线图不存在
        """
        deleted = await self.delete_by_id(roadmap_id)
        
        if deleted:
            logger.info("roadmap_metadata_deleted", roadmap_id=roadmap_id)
        
        return deleted
