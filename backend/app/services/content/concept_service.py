"""
概念服务 - 封装概念相关的业务逻辑
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.models.database import RoadmapMetadata

logger = structlog.get_logger()

class ConceptService:
    """
    概念服务
    
    职责：
    - 概念查询和状态管理
    - 业务逻辑编排（协调CRUD层）
    
    注意：WebSocket通知由主工作流（content_generation subgraph）负责，
    此服务仅用于 API 重试流程，无需推送通知。
    """
    
    def __init__(
        self,
        concept_crud: Optional[ConceptCRUD] = None,
    ):
        """
        初始化概念服务
        
        Args:
            concept_crud: 概念CRUD实例（可选，默认创建新实例）
        """
        self.concept_crud = concept_crud or get_concept_crud()
    
    async def get_concept_from_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Tuple[Optional[dict], Optional[dict], Optional[RoadmapMetadata]]:
        """
        从路线图中获取概念（业务逻辑层）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            (concept, context, roadmap_metadata) 或 (None, None, None)
        """
        result = await self.concept_crud.get_concept_from_roadmap(
            session, roadmap_id, concept_id
        )
        
        if not result:
            logger.warning(
                "concept_not_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return None, None, None
        
        concept, context, roadmap_metadata = result
        
        logger.info(
            "concept_retrieved",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_name=concept.get("name"),
        )
        
        return concept, context, roadmap_metadata
    
    async def update_concept_status(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        content_type: str,
        status: str,
        result: Optional[dict] = None,
    ) -> bool:
        """
        更新概念状态（业务逻辑 + 通知）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            content_type: 内容类型 (tutorial/resources/quiz)
            status: 状态 (pending/generating/completed/failed)
            result: 结果数据（完成时提供）
            
        Returns:
            是否成功
        """
        # 1. 更新 framework_data 中的状态（RoadmapMetadata JSON 字段）
        success = await self.concept_crud.update_concept_status(
            session,
            roadmap_id,
            concept_id,
            content_type,
            status,
            result,
        )
        
        if not success:
            logger.error(
                "concept_status_update_failed",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return False

        # 2. 同步更新 ConceptMetadata 表（API 层读取此表作为权威来源）
        #    原始生成流程通过 ConceptContentHandler 更新此表，
        #    但 retry_content 流程此前只更新 framework_data，导致状态不一致。
        try:
            content_id = None
            if result and status == "completed":
                if content_type == "tutorial":
                    content_id = result.get("tutorial_id")
                elif content_type == "resources":
                    content_id = result.get("id")
                elif content_type == "quiz":
                    content_id = result.get("quiz_id")

            concept_meta = await self.concept_crud.get_by_concept_id(session, concept_id)
            if concept_meta:
                await self.concept_crud.update_content_status(
                    session=session,
                    concept_id=concept_id,
                    content_type=content_type,
                    status=status,
                    content_id=content_id,
                )
            else:
                logger.warning(
                    "concept_metadata_not_found_skipping_sync",
                    concept_id=concept_id,
                    content_type=content_type,
                    status=status,
                )
        except Exception as e:
            # ConceptMetadata 同步失败不阻断主流程，仅记录
            logger.warning(
                "concept_metadata_sync_failed",
                concept_id=concept_id,
                content_type=content_type,
                status=status,
                error=str(e),
            )

        logger.info(
            "concept_status_updated",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
            status=status,
        )
        
        return True


# 全局单例（可选）
_concept_service_instance: Optional[ConceptService] = None

def get_concept_service() -> ConceptService:
    """获取概念服务实例（单例模式）"""
    global _concept_service_instance
    if _concept_service_instance is None:
        _concept_service_instance = ConceptService()
    return _concept_service_instance

