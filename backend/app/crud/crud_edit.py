"""
路线图编辑记录CRUD操作

提供路线图编辑记录的数据库操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import RoadmapEditRecord

logger = structlog.get_logger()


class EditCRUD(BaseCRUD[RoadmapEditRecord, dict, dict]):
    """
    编辑记录CRUD
    
    职责：
    - 路线图编辑记录的增删改查
    - 根据路线图ID/任务ID查询编辑历史
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
        limit: int = 50,
    ) -> List[RoadmapEditRecord]:
        """
        根据路线图ID获取编辑历史
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            limit: 返回记录数限制
            
        Returns:
            编辑记录列表（按时间倒序）
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapEditRecord]:
        """
        获取路线图的最新编辑记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新编辑记录或None
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.roadmap_id == roadmap_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_latest_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[RoadmapEditRecord]:
        """
        根据任务ID获取最新编辑记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            最新编辑记录或None
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(desc(RoadmapEditRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[RoadmapEditRecord]:
        """
        根据任务ID获取所有编辑记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            编辑记录列表（按时间倒序）
        """
        stmt = (
            select(RoadmapEditRecord)
            .where(RoadmapEditRecord.task_id == task_id)
            .order_by(desc(RoadmapEditRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_edit_record(
        self,
        session: AsyncSession,
        task_id: str,
        roadmap_id: str,
        origin_framework_data: dict,
        modified_framework_data: dict,
        modification_summary: str,
        modified_node_ids: list[str],
        edit_round: int = 1,
    ) -> RoadmapEditRecord:
        """
        创建编辑记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            roadmap_id: 路线图ID
            origin_framework_data: 编辑前的框架数据(字典)
            modified_framework_data: 编辑后的框架数据(字典)
            modification_summary: 修改摘要
            modified_node_ids: 修改的节点ID列表
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
        
        session.add(record)
        await session.flush()
        
        logger.info(
            "edit_record_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_round=edit_round,
            modified_nodes_count=len(modified_node_ids),
        )
        
        return record


# 单例模式
_edit_crud_instance: Optional[EditCRUD] = None


def get_edit_crud() -> EditCRUD:
    """获取EditCRUD单例"""
    global _edit_crud_instance
    if _edit_crud_instance is None:
        _edit_crud_instance = EditCRUD(RoadmapEditRecord)
    return _edit_crud_instance

