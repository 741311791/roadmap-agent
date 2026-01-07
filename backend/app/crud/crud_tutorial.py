"""
教程CRUD操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import TutorialMetadata
from app.schemas.tutorial import TutorialCreate, TutorialUpdate

class TutorialCRUD(BaseCRUD[TutorialMetadata, TutorialCreate, TutorialUpdate]):
    """
    教程CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_tutorial_id(
        self,
        session: AsyncSession,
        tutorial_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        根据tutorial_id获取教程
        
        Args:
            session: 数据库会话
            tutorial_id: 教程ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata).where(
                TutorialMetadata.tutorial_id == tutorial_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_concept(
        self,
        session: AsyncSession,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取概念的教程（最新版本）
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.concept_id == concept_id)
            .where(TutorialMetadata.deleted_at.is_(None))
            .order_by(TutorialMetadata.content_version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_latest_by_concept(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定路线图和概念的最新教程
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == roadmap_id)
            .where(TutorialMetadata.concept_id == concept_id)
            .where(TutorialMetadata.is_latest == True)
            .where(TutorialMetadata.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

# 工厂函数
def get_tutorial_crud() -> TutorialCRUD:
    """获取TutorialCRUD实例"""
    return TutorialCRUD(TutorialMetadata)

