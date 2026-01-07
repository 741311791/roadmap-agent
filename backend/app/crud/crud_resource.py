"""
资源推荐CRUD操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import ResourceRecommendationMetadata
from app.schemas.resource import ResourceCreate, ResourceUpdate

class ResourceCRUD(BaseCRUD[ResourceRecommendationMetadata, ResourceCreate, ResourceUpdate]):
    """
    资源推荐CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_resource_id(
        self,
        session: AsyncSession,
        resource_id: str,
    ) -> Optional[ResourceRecommendationMetadata]:
        """
        根据resource_id获取资源推荐
        
        Args:
            session: 数据库会话
            resource_id: 资源ID
            
        Returns:
            资源元数据或None
        """
        result = await session.execute(
            select(ResourceRecommendationMetadata).where(
                ResourceRecommendationMetadata.resource_id == resource_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_concept(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[ResourceRecommendationMetadata]:
        """
        获取概念的资源推荐
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            资源元数据或None
        """
        result = await session.execute(
            select(ResourceRecommendationMetadata)
            .where(ResourceRecommendationMetadata.roadmap_id == roadmap_id)
            .where(ResourceRecommendationMetadata.concept_id == concept_id)
            .where(ResourceRecommendationMetadata.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

# 工厂函数
def get_resource_crud() -> ResourceCRUD:
    """获取ResourceCRUD实例"""
    return ResourceCRUD(ResourceRecommendationMetadata)

