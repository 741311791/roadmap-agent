"""
执行日志追踪服务

负责处理:
- 执行日志查询
- 日志摘要统计
- 错误日志筛选
- 任务所有权验证
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import get_task_crud
from app.models.database import RoadmapMetadata, ExecutionLog
from app.core.custom_exceptions import errors

logger = structlog.get_logger()


class TraceService:
    """执行日志追踪业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = get_task_crud()
    
    async def verify_task_ownership(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        is_superuser: bool,
    ) -> None:
        """
        验证用户是否有权限访问此任务的日志
        
        权限规则：
        - 超级管理员可以查看所有任务日志
        - 普通用户只能查看自己的任务日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            is_superuser: 是否为超级管理员
            
        Raises:
            NotFoundError: 任务不存在
            ForbiddenError: 无权限访问此任务
        """
        # 获取任务信息
        task = await self.task_crud.get_by_task_id(session, task_id)
        
        if not task:
            raise errors.NotFoundError(msg=f"任务 {task_id} 不存在")
        
        # 权限检查：超级管理员可查看所有，普通用户只能查看自己的
        if not is_superuser and task.user_id != user_id:
            logger.warning(
                "unauthorized_trace_access_attempt",
                task_id=task_id,
                user_id=user_id,
                task_owner=task.user_id,
            )
            raise errors.ForbiddenError(msg="无权限查看此任务的执行日志")
        
        logger.debug(
            "trace_access_authorized",
            task_id=task_id,
            user_id=user_id,
            is_superuser=is_superuser,
        )
    
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


# 单例模式
_trace_service_instance: Optional[TraceService] = None


def get_trace_service() -> TraceService:
    """获取TraceService单例"""
    global _trace_service_instance
    if _trace_service_instance is None:
        _trace_service_instance = TraceService()
    return _trace_service_instance
