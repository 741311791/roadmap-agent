"""
精选路线图服务

负责处理:
- 精选用户的路线图查询
- 路线图批量数据获取
"""
from typing import List, Tuple, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.models.database import User, RoadmapTask, RoadmapMetadata
from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.crud.crud_cover_image import get_cover_image_crud

logger = structlog.get_logger()


class FeaturedService:
    """精选路线图业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
        self.cover_image_crud = get_cover_image_crud()
    
    async def get_featured_user(
        self,
        session: AsyncSession,
        featured_user_id: str,
    ) -> Optional[User]:
        """
        获取精选用户
        
        Args:
            session: 数据库会话
            featured_user_id: 精选用户 ID
            
        Returns:
            用户对象（如果存在）
        """
        result = await session.execute(
            select(User).where(User.id == featured_user_id)
        )
        user = result.scalars().first()
        
        if user:
            logger.info(
                "featured_user_found",
                user_id=user.id,
                email=user.email,
            )
        else:
            logger.warning("featured_user_not_found", featured_user_id=featured_user_id)
        
        return user
    
    async def get_featured_roadmaps(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List, Dict[str, RoadmapTask], Dict[str, str | None]]:
        """
        获取精选用户的路线图及相关Task
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            limit: 分页大小
            offset: 偏移量
            
        Returns:
            (路线图列表, {roadmap_id: RoadmapTask} 字典, {roadmap_id: cover_image_url} 字典)
        """
        # 获取路线图列表
        roadmaps = await self.roadmap_crud.get_roadmaps_by_user(
            session, user_id, skip=offset, limit=limit
        )
        
        # 批量获取Task（解决N+1问题）
        roadmap_ids = [r.roadmap_id for r in roadmaps]
        tasks_by_roadmap = await self.task_crud.get_tasks_by_roadmap_ids_batch(
            session, roadmap_ids
        )
        cover_image_records = await self.cover_image_crud.batch_get_by_roadmap_ids(session, roadmap_ids)
        cover_image_url_map = {
            record.roadmap_id: record.cover_image_url if record.generation_status == "success" else None
            for record in cover_image_records
        }
        
        logger.info(
            "featured_roadmaps_retrieved",
            user_id=user_id,
            count=len(roadmaps),
        )
        
        return roadmaps, tasks_by_roadmap, cover_image_url_map

