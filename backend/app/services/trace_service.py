"""
执行日志追踪服务

负责处理:
- 执行日志查询
- 日志摘要统计
- 错误日志筛选
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.models.database import RoadmapMetadata, ExecutionLog

logger = structlog.get_logger()


class TraceService:
    """执行日志追踪业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
    
    async def get_execution_logs(
        self,
        session: AsyncSession,
        task_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[int, List[ExecutionLog]]:
        """
        获取执行日志列表
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            offset: 偏移量
            limit: 返回数量（最大2000）
            
        Returns:
            (总数, 日志列表)
        """
        # 限制最大返回数量
        limit = min(limit, 2000)
        
        # 获取总数和日志列表
        total = await self.roadmap_crud.count_execution_logs_by_trace(
            session, task_id
        )
        
        logs = await self.roadmap_crud.get_execution_logs_by_trace(
            session, task_id, offset=offset, limit=limit
        )
        
        logger.info(
            "execution_logs_retrieved",
            task_id=task_id,
            total=total,
            returned=len(logs),
        )
        
        return total, logs
    
    async def get_execution_logs_summary(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Dict:
        """
        获取执行日志摘要统计
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            摘要统计字典，包含:
            - total: 总日志数
            - by_level: 按级别统计
            - by_step: 按步骤统计
            - latest_log_time: 最新日志时间
        """
        summary = await self.roadmap_crud.get_execution_logs_summary(session, task_id)
        
        logger.info(
            "execution_logs_summary_retrieved",
            task_id=task_id,
            total=summary.get("total", 0),
        )
        
        return summary
    
    async def get_error_logs(
        self,
        session: AsyncSession,
        task_id: str,
        limit: int = 50,
    ) -> List[ExecutionLog]:
        """
        获取错误日志列表
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            limit: 返回数量
            
        Returns:
            错误日志列表
        """
        logs = await self.roadmap_crud.get_error_logs_by_trace(session, task_id, limit=limit)
        
        logger.info(
            "error_logs_retrieved",
            task_id=task_id,
            count=len(logs),
        )
        
        return logs

