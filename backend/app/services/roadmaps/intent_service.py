"""
需求分析服务

负责处理:
- 需求分析元数据查询
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_intent_analysis import IntentAnalysisCRUD, get_intent_analysis_crud
from app.models.database import IntentAnalysisMetadata

logger = structlog.get_logger()


class IntentService:
    """需求分析业务逻辑"""
    
    def __init__(self):
        self.intent_crud = get_intent_analysis_crud()
    
    async def get_intent_analysis_metadata(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        获取需求分析元数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            需求分析元数据对象（如果存在）
        """
        # 根据roadmap_id直接获取意图分析元数据
        metadata = await self.intent_crud.get_by_roadmap_id(session, roadmap_id)
        
        if metadata:
            logger.info(
                "intent_analysis_metadata_retrieved",
                roadmap_id=roadmap_id,
                intent_id=metadata.intent_id,
            )
        
        return metadata

