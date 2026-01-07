"""
资源推荐CRUD操作
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import ResourceRecommendationMetadata
from app.schemas.resource import ResourceCreate, ResourceUpdate

logger = structlog.get_logger()

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
    
    async def save_resource_recommendation(
        self,
        session: AsyncSession,
        resource_output: "ResourceRecommendationOutput",
        roadmap_id: str,
    ) -> ResourceRecommendationMetadata:
        """
        保存资源推荐元数据（幂等操作）
        
        Args:
            session: 数据库会话
            resource_output: 资源推荐输出
            roadmap_id: 路线图ID
            
        Returns:
            保存的元数据记录
        """
        # 先检查是否已存在（通过主键id）
        existing = await self.get(session, resource_output.id)
        
        if existing:
            # 更新现有记录
            existing.resources = [r.model_dump() for r in resource_output.resources]
            existing.resources_count = len(resource_output.resources)
            existing.search_queries_used = resource_output.search_queries_used
            existing.generated_at = resource_output.generated_at
            
            await session.flush()
            await session.refresh(existing)
            
            logger.info(
                "resource_recommendation_metadata_updated",
                id=resource_output.id,
                concept_id=resource_output.concept_id,
                roadmap_id=roadmap_id,
                resources_count=len(resource_output.resources),
            )
            
            return existing
        else:
            # 创建新记录
            metadata = ResourceRecommendationMetadata(
                id=resource_output.id,
                concept_id=resource_output.concept_id,
                roadmap_id=roadmap_id,
                resources=[r.model_dump() for r in resource_output.resources],
                resources_count=len(resource_output.resources),
                search_queries_used=resource_output.search_queries_used,
                generated_at=resource_output.generated_at,
            )
            
            session.add(metadata)
            await session.flush()
            
            logger.info(
                "resource_recommendation_metadata_created",
                id=resource_output.id,
                concept_id=resource_output.concept_id,
                roadmap_id=roadmap_id,
                resources_count=len(resource_output.resources),
            )
            
            return metadata
    
    async def save_resources_batch(
        self,
        session: AsyncSession,
        resource_refs: dict[str, "ResourceRecommendationOutput"],
        roadmap_id: str,
    ) -> List[ResourceRecommendationMetadata]:
        """
        批量保存资源推荐元数据
        
        Args:
            session: 数据库会话
            resource_refs: 资源推荐字典（concept_id -> ResourceRecommendationOutput）
            roadmap_id: 路线图ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        
        for concept_id, resource_output in resource_refs.items():
            metadata = await self.save_resource_recommendation(session, resource_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "resources_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list

# 单例模式
_resource_crud_instance: Optional[ResourceCRUD] = None

def get_resource_crud() -> ResourceCRUD:
    """获取ResourceCRUD单例"""
    global _resource_crud_instance
    if _resource_crud_instance is None:
        _resource_crud_instance = ResourceCRUD(ResourceRecommendationMetadata)
    return _resource_crud_instance

