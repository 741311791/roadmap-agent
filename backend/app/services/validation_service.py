"""
验证记录服务

负责处理:
- 验证记录查询
"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_workflow import ValidationCRUD, get_validation_crud
from app.models.database import StructureValidationRecord

logger = structlog.get_logger()


class ValidationService:
    """验证记录业务逻辑"""
    
    def __init__(self):
        self.validation_crud = get_validation_crud()
    
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
    
    async def get_all_validation_records(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[StructureValidationRecord]:
        """获取所有验证记录"""
        records = await self.validation_crud.get_all_by_task(session, task_id)
        
        logger.info("all_validation_records_retrieved", task_id=task_id, count=len(records))
        
        return records

