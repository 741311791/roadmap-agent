"""
封面图 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import RoadmapCoverImage, beijing_now


class CoverImageCRUD(BaseCRUD[RoadmapCoverImage, dict, dict]):
    """
    封面图 CRUD 操作
    
    继承 BaseCRUD，扩展封面图特有的查询与更新方法。
    """

    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapCoverImage]:
        """
        根据 roadmap_id 获取封面图记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            封面图记录或 None
        """
        result = await session.execute(
            select(self.model).where(self.model.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none()

    async def upsert_generating(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> RoadmapCoverImage:
        """
        创建或更新封面图记录为「生成中」状态
        
        每次触发生成时调用，无论是否已有记录，均重置状态。
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            更新后的封面图记录
        """
        record = await self.get_by_roadmap_id(session, roadmap_id)

        if record is None:
            record = RoadmapCoverImage(
                roadmap_id=roadmap_id,
                generation_status="generating",
                retry_count=0,
            )
            session.add(record)
        else:
            record.generation_status = "generating"
            record.cover_image_url = None
            record.error_message = None
            record.retry_count = 0
            record.updated_at = beijing_now()

        await session.flush()
        return record

    async def mark_success(
        self,
        session: AsyncSession,
        roadmap_id: str,
        cover_image_url: str,
    ) -> Optional[RoadmapCoverImage]:
        """
        将封面图记录标记为生成成功，并写入图片 URL
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            cover_image_url: 生成的封面图 URL
            
        Returns:
            更新后的封面图记录
        """
        record = await self.get_by_roadmap_id(session, roadmap_id)
        if record is None:
            return None

        record.generation_status = "success"
        record.cover_image_url = cover_image_url
        record.error_message = None
        record.updated_at = beijing_now()

        await session.flush()
        return record

    async def mark_failed(
        self,
        session: AsyncSession,
        roadmap_id: str,
        error_message: str,
    ) -> Optional[RoadmapCoverImage]:
        """
        将封面图记录标记为生成失败
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            error_message: 错误信息
            
        Returns:
            更新后的封面图记录
        """
        record = await self.get_by_roadmap_id(session, roadmap_id)
        if record is None:
            return None

        record.generation_status = "failed"
        record.error_message = error_message
        record.updated_at = beijing_now()

        await session.flush()
        return record

    async def batch_get_by_roadmap_ids(
        self,
        session: AsyncSession,
        roadmap_ids: list[str],
    ) -> list[RoadmapCoverImage]:
        """
        批量获取封面图记录
        
        Args:
            session: 数据库会话
            roadmap_ids: 路线图 ID 列表
            
        Returns:
            封面图记录列表
        """
        if not roadmap_ids:
            return []

        result = await session.execute(
            select(self.model).where(self.model.roadmap_id.in_(roadmap_ids))
        )
        return list(result.scalars().all())


def get_cover_image_crud() -> CoverImageCRUD:
    """获取封面图 CRUD 实例"""
    return CoverImageCRUD(RoadmapCoverImage)
