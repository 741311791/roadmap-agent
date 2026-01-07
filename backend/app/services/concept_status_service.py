"""
Concept状态查询服务

负责处理:
- Concept内容生成状态查询
- Roadmap所有Concept状态汇总
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.models.database import ConceptMetadata

logger = structlog.get_logger()


class ConceptStatusService:
    """Concept状态业务逻辑"""
    
    def __init__(self):
        self.concept_crud = get_concept_crud()
    
    async def get_roadmap_concepts(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[ConceptMetadata]:
        """
        获取Roadmap的所有Concept状态
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            Concept元数据列表
        """
        concepts = await self.concept_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not concepts:
            logger.warning(
                "roadmap_concepts_not_found",
                roadmap_id=roadmap_id,
                message="No ConceptMetadata found for this roadmap"
            )
        
        return concepts
    
    async def get_concept(
        self,
        session: AsyncSession,
        concept_id: str,
    ) -> Optional[ConceptMetadata]:
        """
        获取单个Concept状态
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            
        Returns:
            Concept元数据（如果存在）
        """
        concept = await self.concept_crud.get_by_concept_id(session, concept_id)
        
        if concept:
            logger.info("concept_status_retrieved", concept_id=concept_id)
        
        return concept

