"""
流式生成服务

负责处理:
- 流式生成的数据库操作封装
- Task创建与状态更新
- Roadmap元数据查询
"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.models.database import RoadmapTask, RoadmapMetadata

logger = structlog.get_logger()


class StreamingService:
    """流式生成业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
    
    async def create_task(
        self,
        session: AsyncSession,
        task_data: Dict,
    ) -> RoadmapTask:
        """
        创建Task记录
        
        Args:
            session: 数据库会话
            task_data: RoadmapTask数据字典
            
        Returns:
            创建的Task对象
        """
        task = await self.task_crud.create(session, obj_in=task_data)
        
        logger.info("streaming_task_created", task_id=task.task_id)
        
        return task
    
    async def update_task_status(
        self,
        session: AsyncSession,
        task_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """
        更新Task状态
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            status: 新状态
            error: 错误信息（可选）
        """
        await self.task_crud.update_task_status(session, task_id, status, error)
        
        logger.info("streaming_task_status_updated", task_id=task_id, status=status)
    
    async def get_roadmap_metadata(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ):
        """
        获取路线图元数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图元数据对象
        """
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if metadata:
            logger.info("streaming_roadmap_metadata_retrieved", roadmap_id=roadmap_id)
        
        return metadata

