"""
资源推荐 Repository

负责 ResourceRecommendationMetadata 表的数据访问操作。

职责范围：
- 资源推荐元数据的 CRUD 操作
- 资源查询（根据路线图、概念等）

不包含：
- 资源的搜索和推荐逻辑（在 Agent 层）
- 资源的有效性验证（在 Service 层）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.database import ResourceRecommendationMetadata
from app.models.domain import ResourceRecommendationOutput
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class ResourceRepository(BaseRepository[ResourceRecommendationMetadata]):
    """
    资源推荐数据访问层
    
    管理学习资源推荐元数据。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ResourceRecommendationMetadata)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_concept(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[ResourceRecommendationMetadata]:
        """
        获取指定概念的资源推荐
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            资源推荐元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(ResourceRecommendationMetadata)
            .where(
                ResourceRecommendationMetadata.roadmap_id == roadmap_id,
                ResourceRecommendationMetadata.concept_id == concept_id,
            )
        )
        
        resource = result.scalar_one_or_none()
        
        if resource:
            logger.debug(
                "resource_recommendation_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                resources_count=resource.resources_count,
            )
        
        return resource
    
    async def list_by_roadmap(
        self,
        roadmap_id: str,
    ) -> List[ResourceRecommendationMetadata]:
        """
        获取路线图的所有资源推荐
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            资源推荐元数据列表
        """
        result = await self.session.execute(
            select(ResourceRecommendationMetadata)
            .where(ResourceRecommendationMetadata.roadmap_id == roadmap_id)
        )
        
        resources = list(result.scalars().all())
        
        logger.debug(
            "resources_listed_by_roadmap",
            roadmap_id=roadmap_id,
            count=len(resources),
        )
        
        return resources
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_resource_recommendation(
        self,
        resource_output: ResourceRecommendationOutput,
        roadmap_id: str,
    ) -> ResourceRecommendationMetadata:
        """
        保存资源推荐元数据（幂等操作）
        
        Args:
            resource_output: 资源推荐输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录
        """
        # 先检查是否已存在（通过主键 id）
        existing = await self.get_by_id(resource_output.id)
        
        if existing:
            # 更新现有记录
            existing.resources = [r.model_dump() for r in resource_output.resources]
            existing.resources_count = len(resource_output.resources)
            existing.search_queries_used = resource_output.search_queries_used
            existing.generated_at = resource_output.generated_at
            
            await self.session.flush()
            await self.session.refresh(existing)
            
            logger.info(
                "resource_recommendation_metadata_updated",
                id=resource_output.id,
                concept_id=resource_output.concept_id,
                roadmap_id=roadmap_id,
                resources_count=len(resource_output.resources),
            )
            return existing
        
        # 删除该概念的旧资源推荐记录（通过 concept_id，清理可能的孤儿记录）
        await self.session.execute(
            delete(ResourceRecommendationMetadata)
            .where(
                ResourceRecommendationMetadata.roadmap_id == roadmap_id,
                ResourceRecommendationMetadata.concept_id == resource_output.concept_id,
            )
        )
        
        # 创建新记录
        metadata = ResourceRecommendationMetadata(
            id=resource_output.id,  # 使用 output 中的 ID，确保与 Concept 中的 resources_id 一致
            concept_id=resource_output.concept_id,
            roadmap_id=roadmap_id,
            resources=[r.model_dump() for r in resource_output.resources],
            resources_count=len(resource_output.resources),
            search_queries_used=resource_output.search_queries_used,
            generated_at=resource_output.generated_at,
        )
        
        await self.create(metadata, flush=True)
        
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
        resource_refs: dict[str, ResourceRecommendationOutput],
        roadmap_id: str,
    ) -> List[ResourceRecommendationMetadata]:
        """
        批量保存资源推荐元数据
        
        Args:
            resource_refs: 资源推荐字典（concept_id -> ResourceRecommendationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        
        for concept_id, resource_output in resource_refs.items():
            metadata = await self.save_resource_recommendation(
                resource_output, roadmap_id
            )
            metadata_list.append(metadata)
        
        logger.info(
            "resources_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_resource(self, resource_id: str) -> bool:
        """
        删除资源推荐元数据
        
        Args:
            resource_id: 资源推荐 ID
            
        Returns:
            True 如果删除成功，False 如果资源不存在
        """
        deleted = await self.delete_by_id(resource_id)
        
        if deleted:
            logger.info("resource_recommendation_deleted", resource_id=resource_id)
        
        return deleted
    
    async def delete_resources_by_roadmap(self, roadmap_id: str) -> int:
        """
        删除路线图的所有资源推荐
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            删除的记录数
        """
        result = await self.session.execute(
            delete(ResourceRecommendationMetadata)
            .where(ResourceRecommendationMetadata.roadmap_id == roadmap_id)
        )
        
        deleted_count = result.rowcount
        
        logger.info(
            "resources_deleted_by_roadmap",
            roadmap_id=roadmap_id,
            deleted_count=deleted_count,
        )
        
        return deleted_count
    
    async def delete_resource_by_concept(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> bool:
        """
        删除指定概念的资源推荐
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            True 如果删除成功，False 如果资源不存在
        """
        result = await self.session.execute(
            delete(ResourceRecommendationMetadata)
            .where(
                ResourceRecommendationMetadata.roadmap_id == roadmap_id,
                ResourceRecommendationMetadata.concept_id == concept_id,
            )
        )
        
        deleted = result.rowcount > 0
        
        if deleted:
            logger.info(
                "resource_recommendation_deleted_by_concept",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
        
        return deleted
