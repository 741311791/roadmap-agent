"""
验证记录服务

负责处理:
- 验证记录查询
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_validation import ValidationCRUD, get_validation_crud
from app.crud.crud_task import TaskCRUD
from app.models.database import StructureValidationRecord, RoadmapTask

logger = structlog.get_logger()


class ValidationService:
    """验证记录业务逻辑"""
    
    def __init__(self):
        self.validation_crud = get_validation_crud()
        self.task_crud = TaskCRUD(RoadmapTask)
    
    async def get_task_id_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[str]:
        """
        通过roadmap_id查询最新的task_id
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新的task_id（如果存在）
        """
        from sqlalchemy import select, desc
        
        stmt = (
            select(RoadmapTask.task_id)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapTask.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        task_id = result.scalar_one_or_none()
        
        if task_id:
            logger.info("task_id_found_by_roadmap", roadmap_id=roadmap_id, task_id=task_id)
        else:
            logger.warning("task_id_not_found_by_roadmap", roadmap_id=roadmap_id)
        
        return task_id
    
    async def get_task_id_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[str]:
        """
        通过roadmap_id查询最新的task_id
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新的task_id（如果存在）
        """
        from sqlalchemy import select, desc
        
        stmt = (
            select(RoadmapTask.task_id)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapTask.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        task_id = result.scalar_one_or_none()
        
        if task_id:
            logger.info("task_id_found_by_roadmap", roadmap_id=roadmap_id, task_id=task_id)
        else:
            logger.warning("task_id_not_found_by_roadmap", roadmap_id=roadmap_id)
        
        return task_id
    
    async def get_latest_validation_record(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> StructureValidationRecord | None:
        """获取最新的验证记录"""
        record = await self.validation_crud.get_latest_by_task(session, task_id)
        
        if record:
            logger.info("latest_validation_record_retrieved", task_id=task_id)
        
        return record
    
    async def get_latest_validation_record_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        通过roadmap_id获取最新的验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新的验证记录（如果存在）
        """
        task_id = await self.get_task_id_by_roadmap(session, roadmap_id)
        
        if not task_id:
            return None
        
        return await self.get_latest_validation_record(session, task_id)
    
    async def get_latest_validation_record_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        通过roadmap_id获取最新的验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新的验证记录（如果存在）
        """
        task_id = await self.get_task_id_by_roadmap(session, roadmap_id)
        
        if not task_id:
            return None
        
        return await self.get_latest_validation_record(session, task_id)
    
    async def get_all_validation_records(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[StructureValidationRecord]:
        """获取所有验证记录"""
        records = await self.validation_crud.get_all_by_task(session, task_id)
        
        logger.info("all_validation_records_retrieved", task_id=task_id, count=len(records))
        
        return records
    
    async def get_all_validation_records_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[StructureValidationRecord]:
        """
        通过roadmap_id获取所有验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            验证记录列表（按创建时间降序）
        """
        task_id = await self.get_task_id_by_roadmap(session, roadmap_id)
        
        if not task_id:
            return []
        
        return await self.get_all_validation_records(session, task_id)
    
    async def get_all_validation_records_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[StructureValidationRecord]:
        """
        通过roadmap_id获取所有验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            验证记录列表（按创建时间降序）
        """
        task_id = await self.get_task_id_by_roadmap(session, roadmap_id)
        
        if not task_id:
            return []
        
        return await self.get_all_validation_records(session, task_id)

