"""
Concept 元数据数据访问层

负责 ConceptMetadata 表的数据库操作，追踪内容生成状态。
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional, List
import structlog

from app.models.database import ConceptMetadata, beijing_now

logger = structlog.get_logger()


class ConceptMetadataRepository:
    """Concept 元数据数据访问层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_concept_id(
        self,
        concept_id: str
    ) -> Optional[ConceptMetadata]:
        """
        查询单个 Concept 元数据
        
        Args:
            concept_id: 概念 ID
            
        Returns:
            ConceptMetadata 对象，不存在则返回 None
        """
        statement = select(ConceptMetadata).where(
            ConceptMetadata.concept_id == concept_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_by_roadmap_id(
        self,
        roadmap_id: str
    ) -> List[ConceptMetadata]:
        """
        查询某 roadmap 的所有 Concept 元数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            ConceptMetadata 对象列表
        """
        statement = select(ConceptMetadata).where(
            ConceptMetadata.roadmap_id == roadmap_id
        ).order_by(ConceptMetadata.created_at)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_completed_concepts(
        self,
        roadmap_id: str
    ) -> List[ConceptMetadata]:
        """
        查询某 roadmap 中所有完成的 Concept
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            状态为 completed 的 ConceptMetadata 对象列表
        """
        statement = select(ConceptMetadata).where(
            ConceptMetadata.roadmap_id == roadmap_id,
            ConceptMetadata.overall_status == "completed"
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def create_or_update(
        self,
        concept_id: str,
        roadmap_id: str,
        **fields
    ) -> ConceptMetadata:
        """
        创建或更新 Concept 元数据（Upsert）
        
        Args:
            concept_id: 概念 ID
            roadmap_id: 路线图 ID
            **fields: 其他字段（如 tutorial_status、tutorial_id 等）
            
        Returns:
            ConceptMetadata 对象
        """
        existing = await self.get_by_concept_id(concept_id)
        
        if existing:
            # 更新现有记录
            for key, value in fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = beijing_now()
            self.session.add(existing)
            logger.debug(
                "concept_metadata_updated",
                concept_id=concept_id,
                fields=list(fields.keys())
            )
            return existing
        else:
            # 创建新记录
            metadata = ConceptMetadata(
                concept_id=concept_id,
                roadmap_id=roadmap_id,
                **fields
            )
            self.session.add(metadata)
            logger.debug(
                "concept_metadata_created",
                concept_id=concept_id,
                roadmap_id=roadmap_id
            )
            return metadata
    
    async def update_content_status(
        self,
        concept_id: str,
        content_type: str,  # 'tutorial' | 'resources' | 'quiz'
        status: str,
        content_id: Optional[str] = None,
    ) -> ConceptMetadata:
        """
        更新单项内容状态，并自动检查是否全部完成
        
        Args:
            concept_id: 概念 ID
            content_type: 内容类型 ('tutorial', 'resources', 'quiz')
            status: 新状态 ('pending', 'generating', 'completed', 'failed')
            content_id: 内容 ID（可选，状态为 completed 时提供）
            
        Returns:
            更新后的 ConceptMetadata 对象
            
        Raises:
            ValueError: 如果 concept_id 不存在
        """
        metadata = await self.get_by_concept_id(concept_id)
        
        if not metadata:
            raise ValueError(f"ConceptMetadata not found for concept_id: {concept_id}")
        
        # 更新对应的状态字段
        status_field = f"{content_type}_status"
        id_field = f"{content_type}_id"
        completed_at_field = f"{content_type}_completed_at"
        
        setattr(metadata, status_field, status)
        
        if content_id:
            setattr(metadata, id_field, content_id)
        
        if status == "completed":
            setattr(metadata, completed_at_field, beijing_now())
        
        # 检查三项是否全部完成
        if (metadata.tutorial_status == "completed" and
            metadata.resources_status == "completed" and
            metadata.quiz_status == "completed"):
            metadata.overall_status = "completed"
            metadata.all_content_completed_at = beijing_now()
            logger.info(
                "concept_all_content_completed",
                concept_id=concept_id,
                roadmap_id=metadata.roadmap_id
            )
        elif (metadata.tutorial_status in ["completed", "failed"] and
              metadata.resources_status in ["completed", "failed"] and
              metadata.quiz_status in ["completed", "failed"] and
              (metadata.tutorial_status == "failed" or
               metadata.resources_status == "failed" or
               metadata.quiz_status == "failed")):
            # 至少一项失败，但都已完成尝试
            metadata.overall_status = "partial_failed"
            logger.warning(
                "concept_partial_failed",
                concept_id=concept_id,
                roadmap_id=metadata.roadmap_id,
                tutorial_status=metadata.tutorial_status,
                resources_status=metadata.resources_status,
                quiz_status=metadata.quiz_status
            )
        elif status == "generating":
            # 只要有一项正在生成，整体状态就是 generating
            if metadata.overall_status == "pending":
                metadata.overall_status = "generating"
        
        metadata.updated_at = beijing_now()
        self.session.add(metadata)
        
        logger.debug(
            "concept_content_status_updated",
            concept_id=concept_id,
            content_type=content_type,
            status=status,
            overall_status=metadata.overall_status
        )
        
        return metadata
    
    async def batch_initialize_concepts(
        self,
        roadmap_id: str,
        concept_ids: List[str]
    ):
        """
        批量初始化 Concept 元数据（在 framework 生成后调用）
        
        使用批量插入优化性能，避免 N 次 INSERT。
        
        Args:
            roadmap_id: 路线图 ID
            concept_ids: 概念 ID 列表
        """
        if not concept_ids:
            logger.warning(
                "batch_initialize_concepts_empty_list",
                roadmap_id=roadmap_id
            )
            return
        
        # 检查是否已存在（避免重复初始化）
        statement = select(ConceptMetadata.concept_id).where(
            ConceptMetadata.roadmap_id == roadmap_id,
            ConceptMetadata.concept_id.in_(concept_ids)
        )
        result = await self.session.execute(statement)
        existing_ids = set(result.scalars().all())
        
        # 过滤出需要新建的 concept_id
        new_concept_ids = [cid for cid in concept_ids if cid not in existing_ids]
        
        if not new_concept_ids:
            logger.info(
                "batch_initialize_concepts_all_exist",
                roadmap_id=roadmap_id,
                total_count=len(concept_ids)
            )
            return
        
        # 批量插入
        now = beijing_now()
        metadata_list = [
            ConceptMetadata(
                concept_id=cid,
                roadmap_id=roadmap_id,
                tutorial_status="pending",
                resources_status="pending",
                quiz_status="pending",
                overall_status="pending",
                created_at=now,
                updated_at=now
            )
            for cid in new_concept_ids
        ]
        
        self.session.add_all(metadata_list)
        
        logger.info(
            "batch_initialize_concepts_completed",
            roadmap_id=roadmap_id,
            new_count=len(new_concept_ids),
            skipped_count=len(existing_ids)
        )
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_by_concept_id(self, concept_id: str) -> bool:
        """
        删除单个 Concept 元数据
        
        Args:
            concept_id: 概念 ID
            
        Returns:
            True 如果删除成功，False 如果记录不存在
        """
        metadata = await self.get_by_concept_id(concept_id)
        
        if metadata:
            await self.session.delete(metadata)
            logger.info("concept_metadata_deleted", concept_id=concept_id)
            return True
        
        return False
    
    async def delete_by_roadmap_id(self, roadmap_id: str) -> int:
        """
        删除某 roadmap 的所有 Concept 元数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            删除的记录数量
        """
        concepts = await self.get_by_roadmap_id(roadmap_id)
        
        for concept in concepts:
            await self.session.delete(concept)
        
        count = len(concepts)
        logger.info(
            "concept_metadata_batch_deleted",
            roadmap_id=roadmap_id,
            deleted_count=count
        )
        
        return count

