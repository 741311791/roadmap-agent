"""
概念服务 - 封装概念相关的业务逻辑
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.models.database import RoadmapMetadata
from app.services.notification_service import (
    NotificationService,
    notification_service as default_notification_service,
)

logger = structlog.get_logger()

class ConceptService:
    """
    概念服务
    
    职责：
    - 概念查询和状态管理
    - WebSocket通知
    - 业务逻辑编排（协调CRUD和通知）
    """
    
    def __init__(
        self,
        concept_crud: Optional[ConceptCRUD] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        """
        初始化概念服务
        
        Args:
            concept_crud: 概念CRUD实例（可选，默认创建新实例）
            notification_service: 通知服务实例（可选，使用全局单例）
        """
        self.concept_crud = concept_crud or get_concept_crud()
        self.notification = notification_service or default_notification_service
    
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
        # 更新数据库
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
        
        # 发送WebSocket通知
        try:
            if status == "generating":
                await self.notification.publish_concept_start(
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    content_type=content_type,
                )
            elif status == "completed":
                await self.notification.publish_concept_complete(
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    content_type=content_type,
                    result=result,
                )
            elif status == "failed":
                await self.notification.publish_concept_error(
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    content_type=content_type,
                    error=result.get("error") if result else "Unknown error",
                )
        except Exception as e:
            # WebSocket通知失败不影响业务流程
            logger.error(
                "concept_notification_failed",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
                status=status,
                error=str(e),
                exc_info=True,
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

