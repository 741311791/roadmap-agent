"""
编辑记录服务

负责处理:
- 编辑记录查询
- 路线图对比生成
"""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_workflow import EditCRUD, get_edit_crud
from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.models.database import RoadmapEditRecord, RoadmapMetadata, RoadmapTask
from app.services.roadmap_comparison_service import RoadmapComparisonService

logger = structlog.get_logger()


class EditService:
    """编辑记录业务逻辑"""
    
    def __init__(self):
        self.edit_crud = get_edit_crud()
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
        self._comparison_service = RoadmapComparisonService()
    
    async def get_latest_edit_record(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[RoadmapEditRecord]:
        """获取最新的编辑记录"""
        record = await self.edit_crud.get_latest_by_task(session, task_id)
        
        if record:
            logger.info("latest_edit_record_retrieved", task_id=task_id)
        
        return record
    
    async def get_all_edit_records(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[RoadmapEditRecord]:
        """获取所有编辑记录"""
        records = await self.edit_crud.get_all_by_task(session, task_id)
        
        logger.info("all_edit_records_retrieved", task_id=task_id, count=len(records))
        
        return records
    
    async def get_roadmap_comparison(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[Dict]:
        """
        获取路线图对比结果
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            对比结果字典（如果存在多个版本）
        """
        # 获取所有编辑记录
        records = await self.edit_crud.get_all_by_task(session, task_id)
        
        if len(records) < 2:
            return None
        
        # 通过task_id获取路线图
        task = await self.task_crud.get(session, task_id)
        if not task or not task.roadmap_id:
            return None
        
        roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, task.roadmap_id)
        
        if not roadmap_metadata or not roadmap_metadata.framework_data:
            return None
        
        # 生成对比结果
        from app.models.domain import RoadmapFramework
        current_framework = RoadmapFramework(**roadmap_metadata.framework_data)
        
        previous_record = records[-2]
        previous_framework = RoadmapFramework(**previous_record.original_framework)
        
        comparison = self._comparison_service.compare_frameworks(
            old=previous_framework,
            new=current_framework,
        )
        
        logger.info(
            "roadmap_comparison_generated",
            task_id=task_id,
            version_count=len(records),
        )
        
        return comparison

