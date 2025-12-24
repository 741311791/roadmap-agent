"""
路线图编辑记录 Repository

负责 RoadmapEditRecord 表的数据访问操作。

职责范围：
- 编辑记录的 CRUD 操作
- 根据 task_id 查询编辑记录
- 获取最新编辑结果
- 查询编辑历史
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import RoadmapEditRecord
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class EditRepository(BaseRepository[RoadmapEditRecord]):
    """
    路线图编辑记录数据访问层
    
    管理路线图编辑的历史记录和差异数据。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RoadmapEditRecord)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_latest_by_task(
        self, 
        task_id: str
    ) -> Optional[RoadmapEditRecord]:
        """
        获取任务的最新编辑记录
        
        Args:
            task_id: 任务 ID
            
        Returns:
            最新的编辑记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(RoadmapEditRecord.edit_round.desc())
            .limit(1)
        )
        
        record = result.scalar_one_or_none()
        
        if record:
            logger.debug(
                "latest_edit_record_found",
                task_id=task_id,
                edit_round=record.edit_round,
                modified_nodes_count=len(record.modified_node_ids) if record.modified_node_ids else 0,
            )
        else:
            logger.debug(
                "no_edit_record_found",
                task_id=task_id,
            )
        
        return record
    
    async def get_all_by_task(
        self, 
        task_id: str
    ) -> List[RoadmapEditRecord]:
        """
        获取任务的所有编辑记录（按轮次排序）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            编辑记录列表（按轮次降序）
        """
        result = await self.session.execute(
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(RoadmapEditRecord.edit_round.desc())
        )
        
        records = list(result.scalars().all())
        
        logger.debug(
            "edit_records_listed",
            task_id=task_id,
            count=len(records),
        )
        
        return records
    
    async def get_by_roadmap(
        self, 
        roadmap_id: str,
        limit: int = 10
    ) -> List[RoadmapEditRecord]:
        """
        获取路线图的所有编辑记录
        
        Args:
            roadmap_id: 路线图 ID
            limit: 返回数量限制
            
        Returns:
            编辑记录列表（按时间降序）
        """
        result = await self.session.execute(
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.roadmap_id == roadmap_id)
            .order_by(RoadmapEditRecord.created_at.desc())
            .limit(limit)
        )
        
        records = list(result.scalars().all())
        
        logger.debug(
            "roadmap_edit_records_listed",
            roadmap_id=roadmap_id,
            count=len(records),
        )
        
        return records
    
    # ============================================================
    # 创建方法
    # ============================================================
    
    async def create_edit_record(
        self,
        task_id: str,
        roadmap_id: str,
        origin_framework_data: dict,
        modified_framework_data: dict,
        modification_summary: str,
        modified_node_ids: list,
        edit_round: int = 1,
    ) -> RoadmapEditRecord:
        """
        创建编辑记录
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            origin_framework_data: 编辑前的框架数据
            modified_framework_data: 编辑后的框架数据
            modification_summary: 修改摘要
            modified_node_ids: 修改的节点 ID 列表
            edit_round: 编辑轮次
            
        Returns:
            创建的编辑记录
        """
        record = RoadmapEditRecord(
            task_id=task_id,
            roadmap_id=roadmap_id,
            origin_framework_data=origin_framework_data,
            modified_framework_data=modified_framework_data,
            modification_summary=modification_summary,
            modified_node_ids=modified_node_ids,
            edit_round=edit_round,
        )
        
        await self.create(record, flush=True)
        
        logger.info(
            "edit_record_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_round=edit_round,
            modified_nodes_count=len(modified_node_ids),
        )
        
        return record









