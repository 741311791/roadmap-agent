"""
执行日志CRUD操作

提供工作流执行日志的数据库操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import ExecutionLog

logger = structlog.get_logger()


class ExecutionLogCRUD(BaseCRUD[ExecutionLog, dict, dict]):
    """
    执行日志CRUD
    
    职责：
    - 执行日志的增删改查
    - 根据任务ID查询日志
    - 日志流式读取
    """
    
    async def get_logs_by_task_id(
        self,
        session: AsyncSession,
        task_id: str,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """
        根据任务ID获取执行日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            limit: 返回日志条数限制
            
        Returns:
            日志列表（按时间倒序）
        """
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.task_id == task_id)
            .order_by(desc(ExecutionLog.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_logs_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
        step_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """
        根据路线图ID获取执行日志
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            step_name: 步骤名称（可选筛选）
            limit: 返回日志条数限制
            
        Returns:
            日志列表（按时间倒序）
        """
        stmt = select(ExecutionLog).where(ExecutionLog.roadmap_id == roadmap_id)
        
        if step_name:
            stmt = stmt.where(ExecutionLog.step_name == step_name)
        
        stmt = stmt.order_by(desc(ExecutionLog.created_at)).limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


# 单例模式
_execution_log_crud_instance: Optional[ExecutionLogCRUD] = None


def get_execution_log_crud() -> ExecutionLogCRUD:
    """获取ExecutionLogCRUD单例"""
    global _execution_log_crud_instance
    if _execution_log_crud_instance is None:
        _execution_log_crud_instance = ExecutionLogCRUD(ExecutionLog)
    return _execution_log_crud_instance

