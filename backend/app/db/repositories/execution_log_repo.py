"""
执行日志 Repository

负责 ExecutionLog 表的数据访问操作。

职责范围：
- 执行日志的 CRUD 操作
- 日志查询（根据 task_id、level、category 等）
- 日志统计

不包含：
- 日志分析逻辑（在 Service 层）
- 日志格式化和输出（在 Logger 服务）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import ExecutionLog
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class ExecutionLogRepository(BaseRepository[ExecutionLog]):
    """
    执行日志数据访问层
    
    管理工作流执行日志。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ExecutionLog)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def list_by_trace(
        self,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExecutionLog]:
        """
        获取指定 task_id 的执行日志
        
        Args:
            task_id: 追踪 ID（对应 task_id）
            level: 过滤日志级别（可选）
            category: 过滤日志分类（可选）
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            执行日志列表（按时间降序）
        """
        query = select(ExecutionLog).where(ExecutionLog.task_id == task_id)
        
        if level:
            query = query.where(ExecutionLog.level == level)
        if category:
            query = query.where(ExecutionLog.category == category)
        
        query = (
            query
            .order_by(ExecutionLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        logs = list(result.scalars().all())
        
        logger.debug(
            "execution_logs_listed",
            task_id=task_id,
            count=len(logs),
            level_filter=level,
            category_filter=category,
        )
        
        return logs
    
    async def get_error_logs(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[ExecutionLog]:
        """
        获取指定 task_id 的错误日志
        
        Args:
            task_id: 追踪 ID
            limit: 返回数量限制
            
        Returns:
            错误日志列表（按时间降序）
        """
        result = await self.session.execute(
            select(ExecutionLog)
            .where(
                ExecutionLog.task_id == task_id,
                ExecutionLog.level == "error",
            )
            .order_by(ExecutionLog.created_at.desc())
            .limit(limit)
        )
        
        logs = list(result.scalars().all())
        
        logger.debug(
            "error_logs_retrieved",
            task_id=task_id,
            count=len(logs),
        )
        
        return logs
    
    async def get_logs_summary(self, task_id: str) -> dict:
        """
        获取执行日志摘要统计
        
        Args:
            task_id: 追踪 ID
            
        Returns:
            包含统计信息的字典
        """
        # 统计各级别日志数量
        level_counts_result = await self.session.execute(
            select(
                ExecutionLog.level,
                func.count(ExecutionLog.id).label("count"),
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.level)
        )
        level_stats = {row[0]: row[1] for row in level_counts_result.fetchall()}
        
        # 统计各分类日志数量
        category_counts_result = await self.session.execute(
            select(
                ExecutionLog.category,
                func.count(ExecutionLog.id).label("count"),
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.category)
        )
        category_stats = {row[0]: row[1] for row in category_counts_result.fetchall()}
        
        # 计算总耗时
        duration_result = await self.session.execute(
            select(func.sum(ExecutionLog.duration_ms))
            .where(ExecutionLog.task_id == task_id)
            .where(ExecutionLog.duration_ms.isnot(None))
        )
        total_duration_ms = duration_result.scalar_one_or_none() or 0
        
        # 获取时间范围
        time_range_result = await self.session.execute(
            select(
                func.min(ExecutionLog.created_at).label("first"),
                func.max(ExecutionLog.created_at).label("last"),
            )
            .where(ExecutionLog.task_id == task_id)
        )
        time_range = time_range_result.fetchone()
        
        summary = {
            "task_id": task_id,
            "level_stats": level_stats,
            "category_stats": category_stats,
            "total_duration_ms": total_duration_ms,
            "first_log_at": time_range[0].isoformat() if time_range and time_range[0] else None,
            "last_log_at": time_range[1].isoformat() if time_range and time_range[1] else None,
            "total_logs": sum(level_stats.values()),
        }
        
        logger.debug(
            "execution_logs_summary_calculated",
            task_id=task_id,
            total_logs=summary["total_logs"],
            total_duration_ms=total_duration_ms,
        )
        
        return summary
    
    # ============================================================
    # 创建方法
    # ============================================================
    
    async def create_log(
        self,
        task_id: str,
        level: str,
        category: str,
        message: str,
        roadmap_id: Optional[str] = None,
        concept_id: Optional[str] = None,
        step: Optional[str] = None,
        agent_name: Optional[str] = None,
        details: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> ExecutionLog:
        """
        创建执行日志记录
        
        Args:
            task_id: 追踪 ID（对应 task_id）
            level: 日志级别 (debug, info, warning, error)
            category: 日志分类 (workflow, agent, tool, database)
            message: 日志消息
            roadmap_id: 路线图 ID（可选）
            concept_id: 概念 ID（可选）
            step: 当前步骤（可选）
            agent_name: Agent 名称（可选）
            details: 详细数据（可选）
            duration_ms: 执行耗时（毫秒，可选）
            
        Returns:
            创建的日志记录
        """
        log = ExecutionLog(
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            level=level,
            category=category,
            step=step,
            agent_name=agent_name,
            message=message,
            details=details,
            duration_ms=duration_ms,
        )
        
        await self.create(log, flush=False)  # 日志不需要立即刷新
        
        return log
    
    # ============================================================
    # 删除方法（清理）
    # ============================================================
    
    async def delete_logs_by_trace(self, task_id: str) -> int:
        """
        删除指定 task_id 的所有日志
        
        Args:
            task_id: 追踪 ID
            
        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(ExecutionLog).where(ExecutionLog.task_id == task_id)
        )
        
        deleted_count = result.rowcount
        
        logger.info(
            "execution_logs_deleted",
            task_id=task_id,
            deleted_count=deleted_count,
        )
        
        return deleted_count
    
    async def delete_old_logs(self, days: int = 90) -> int:
        """
        删除指定天数之前的日志（归档清理）
        
        Args:
            days: 保留天数（默认 90 天）
            
        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        from datetime import timedelta
        from app.models.database import beijing_now
        
        cutoff_date = beijing_now() - timedelta(days=days)
        
        result = await self.session.execute(
            delete(ExecutionLog).where(ExecutionLog.created_at < cutoff_date)
        )
        
        deleted_count = result.rowcount
        
        logger.info(
            "old_execution_logs_deleted",
            days=days,
            cutoff_date=cutoff_date.isoformat(),
            deleted_count=deleted_count,
        )
        
        return deleted_count
