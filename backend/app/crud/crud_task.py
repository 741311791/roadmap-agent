"""
任务CRUD操作

扩展了以下Repository方法：
- 批量查询优化（get_tasks_by_roadmap_ids_batch）
- 状态更新（update_task_status）
- 用户任务统计（get_user_tasks_with_stats）
"""
from typing import Optional, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.crud.base import BaseCRUD
from app.models.database import RoadmapTask, beijing_now

logger = structlog.get_logger()

# ===== Task相关的Schema定义 =====

class TaskCreate(BaseModel):
    """任务创建Schema"""
    task_id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    status: str = Field(default="pending", description="任务状态")
    task_type: str = Field(..., description="任务类型")

class TaskUpdate(BaseModel):
    """任务更新Schema"""
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, description="进度百分比")
    result: Optional[dict] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误消息")

class TaskCRUD(BaseCRUD[RoadmapTask, TaskCreate, TaskUpdate]):
    """
    任务CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_task_id(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[RoadmapTask]:
        """
        根据task_id获取任务
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            任务实例或None
        """
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[RoadmapTask]:
        """
        获取用户的任务列表
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            任务列表
        """
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.user_id == user_id)
            .order_by(RoadmapTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_pending_tasks(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RoadmapTask]:
        """
        获取待处理的任务
        
        Args:
            session: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            任务列表
        """
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.status == "pending")
            .order_by(RoadmapTask.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ========== Week 4扩展方法 ==========
    
    async def get_tasks_by_roadmap_ids_batch(
        self,
        session: AsyncSession,
        roadmap_ids: List[str],
    ) -> Dict[str, RoadmapTask]:
        """
        批量获取多个路线图的最新任务（解决N+1查询问题）
        
        使用窗口函数获取每个roadmap_id的最新任务
        
        Args:
            session: 数据库会话
            roadmap_ids: 路线图ID列表
            
        Returns:
            字典，键为roadmap_id，值为对应的最新任务
        """
        if not roadmap_ids:
            return {}
        
        # 子查询：按roadmap_id分组，获取最新的created_at
        subquery = (
            select(
                RoadmapTask.roadmap_id,
                func.max(RoadmapTask.created_at).label("max_created_at"),
            )
            .where(RoadmapTask.roadmap_id.in_(roadmap_ids))
            .group_by(RoadmapTask.roadmap_id)
            .subquery()
        )
        
        # 主查询：关联子查询获取完整任务记录
        result = await session.execute(
            select(RoadmapTask)
            .join(
                subquery,
                (RoadmapTask.roadmap_id == subquery.c.roadmap_id) &
                (RoadmapTask.created_at == subquery.c.max_created_at)
            )
        )
        
        tasks = result.scalars().all()
        return {task.roadmap_id: task for task in tasks}
    
    async def update_task_status(
        self,
        session: AsyncSession,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
        current_step: Optional[str] = None,
    ) -> bool:
        """
        更新任务状态
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息（可选）
            current_step: 当前步骤（可选）
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_status_update", task_id=task_id)
            return False
        
        task.status = status
        task.updated_at = beijing_now()
        
        if error_message is not None:
            task.error_message = error_message
        
        if current_step is not None:
            task.current_step = current_step
        
        if status in ["completed", "failed", "partial_failure"]:
            task.completed_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_status_updated",
            task_id=task_id,
            status=status,
            current_step=current_step,
        )
        
        return True
    
    async def get_user_tasks_with_stats(
        self,
        session: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict:
        """
        获取用户任务列表及统计信息
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            status: 状态筛选（可选）
            task_type: 任务类型筛选（可选）
            skip: 跳过记录数
            limit: 返回数量限制
            
        Returns:
            包含tasks和status_counts的字典
        """
        # 构建基础查询
        query = select(RoadmapTask).where(RoadmapTask.user_id == user_id)
        
        if status:
            query = query.where(RoadmapTask.status == status)
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)
        
        query = query.order_by(RoadmapTask.created_at.desc())
        
        # 获取任务列表
        tasks_result = await session.execute(query.offset(skip).limit(limit))
        tasks = list(tasks_result.scalars().all())
        
        # 统计各状态任务数量
        stats_query = (
            select(
                RoadmapTask.status,
                func.count(RoadmapTask.task_id).label('count')
            )
            .where(RoadmapTask.user_id == user_id)
        )
        
        if task_type:
            stats_query = stats_query.where(RoadmapTask.task_type == task_type)
        
        stats_query = stats_query.group_by(RoadmapTask.status)
        
        stats_result = await session.execute(stats_query)
        status_counts = {row.status: row.count for row in stats_result}
        
        return {
            "tasks": tasks,
            "status_counts": status_counts,
        }


# 工厂函数
def get_task_crud() -> TaskCRUD:
    """获取TaskCRUD实例"""
    return TaskCRUD(RoadmapTask)

