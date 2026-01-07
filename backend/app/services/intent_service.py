"""
需求分析服务

负责处理:
- 需求分析元数据查询
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_workflow import IntentAnalysisCRUD, get_intent_analysis_crud
from app.models.database import IntentAnalysisMetadata

logger = structlog.get_logger()


class IntentService:
    """需求分析业务逻辑"""
    
    def __init__(self):
        self.intent_crud = get_intent_analysis_crud()
    
    async def get_intent_analysis_metadata(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        获取需求分析元数据
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            需求分析元数据对象（如果存在）
        """
        metadata = await self.intent_crud.get_by_task_id(session, task_id)
        
        if metadata:
            logger.info("intent_analysis_metadata_retrieved", task_id=task_id)
        
        return metadata

