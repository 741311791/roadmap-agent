"""
任务CRUD操作

扩展了以下Repository方法：
- 批量查询优化（get_tasks_by_roadmap_ids_batch）
- 状态更新（update_task_status）
- 用户任务统计（get_user_tasks_with_stats）
- 管理员监控查询（get_admin_tasks、get_admin_status_counts 等）
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from pydantic import BaseModel, Field
import structlog

from app.config.settings import settings
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
    
    继承BaseCRUD，自动获得通用的CRUD方法。
    
    使用全局单例模式：
    ```python
    task_crud = get_task_crud()
    task = await task_crud.get_by_task_id(session, task_id)
    ```
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

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> int:
        """
        统计用户任务数量。

        Args:
            session: 数据库会话
            user_id: 用户ID
            status: 任务状态过滤
            task_type: 任务类型过滤

        Returns:
            任务数量
        """
        query = select(func.count()).select_from(RoadmapTask).where(RoadmapTask.user_id == user_id)

        if status:
            query = query.where(RoadmapTask.status == status)
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)

        result = await session.execute(query)
        return int(result.scalar() or 0)
    
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
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapTask]:
        """
        获取指定路线图的最新任务
        
        按 created_at 降序排列，返回第一条记录。
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新任务实例或None
        """
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    # ========== Week 4扩展方法 ==========
    
    async def get_tasks_by_roadmap_ids_batch(
        self,
        session: AsyncSession,
        roadmap_ids: List[str],
        exclude_task_types: Optional[List[str]] = None,
    ) -> Dict[str, RoadmapTask]:
        """
        批量获取多个路线图的最新任务（解决N+1查询问题）
        
        使用窗口函数获取每个roadmap_id的最新任务
        
        Args:
            session: 数据库会话
            roadmap_ids: 路线图ID列表
            exclude_task_types: 需要排除的任务类型列表
            
        Returns:
            字典，键为roadmap_id，值为对应的最新任务
        """
        if not roadmap_ids:
            return {}
        
        query = select(
            RoadmapTask,
            func.row_number().over(
                partition_by=RoadmapTask.roadmap_id,
                order_by=RoadmapTask.created_at.desc(),
            ).label("row_number"),
        ).where(RoadmapTask.roadmap_id.in_(roadmap_ids))

        if exclude_task_types:
            query = query.where(
                or_(
                    RoadmapTask.task_type.is_(None),
                    RoadmapTask.task_type.notin_(exclude_task_types),
                )
            )

        ranked_tasks = query.subquery()

        ranked_task = aliased(RoadmapTask, ranked_tasks)
        result = await session.execute(
            select(ranked_task).where(ranked_tasks.c.row_number == 1)
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
        roadmap_id: Optional[str] = None,
    ) -> bool:
        """
        更新任务状态
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息（可选）
            current_step: 当前步骤（可选）
            roadmap_id: 路线图ID（可选）
            
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
        
        if roadmap_id is not None:
            task.roadmap_id = roadmap_id
        
        if status in ["completed", "failed", "partial_failure"]:
            task.completed_at = beijing_now()
        else:
            task.completed_at = None
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_status_updated",
            task_id=task_id,
            status=status,
            current_step=current_step,
            roadmap_id=roadmap_id,
        )
        
        return True

    def _is_queue_visible_pending_creation_task(
        self,
        task: RoadmapTask,
        *,
        stale_cutoff_time: datetime,
    ) -> bool:
        """
        判断 pending 创建任务是否应参与排队展示。

        设计原因：
        - 队列消息丢失后，数据库里会残留长期停留在 init 的 pending 任务；
        - 这类历史孤儿任务不应继续污染“前方还有 N 个任务”的用户提示；
        - 仅将“超过阈值且仍停留在 init”的任务视为不可见，其余 pending 任务保持可见。

        Args:
            task: 任务记录
            stale_cutoff_time: 陈旧 pending 任务的截止时间

        Returns:
            是否参与排队展示
        """
        if task.status != "pending" or task.task_type != "creation" or not task.created_at:
            return False

        if (task.current_step or "init") != "init":
            return True

        return task.created_at >= stale_cutoff_time

    def build_creation_queue_info_map(
        self,
        tasks: List[RoadmapTask],
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, int]]:
        """
        基于任务列表构建创建类任务的排队信息映射。

        Args:
            tasks: 候选任务列表
            now: 当前时间（测试时可注入）

        Returns:
            以 task_id 为键的排队信息映射
        """
        current_time = now or beijing_now()
        stale_cutoff_time = current_time - timedelta(
            hours=settings.STALE_PENDING_TASK_CLEANUP_AFTER_HOURS
        )
        visible_tasks = [
            task
            for task in tasks
            if self._is_queue_visible_pending_creation_task(
                task,
                stale_cutoff_time=stale_cutoff_time,
            )
        ]
        visible_tasks.sort(key=lambda item: item.created_at)

        return {
            task.task_id: {
                "queue_ahead_count": index,
                "queue_position": index + 1,
            }
            for index, task in enumerate(visible_tasks)
        }

    async def get_creation_queue_info_map(
        self,
        session: AsyncSession,
        task_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, int]]:
        """
        获取创建类 pending 任务的排队信息映射。

        Args:
            session: 数据库会话
            task_ids: 需要返回排队信息的任务 ID 列表；为空时返回全部

        Returns:
            以 task_id 为键的排队信息映射
        """
        current_time = beijing_now()
        stale_cutoff_time = current_time - timedelta(
            hours=settings.STALE_PENDING_TASK_CLEANUP_AFTER_HOURS
        )

        visible_pending_creation_query = (
            select(
                RoadmapTask.task_id,
                func.row_number().over(
                    order_by=RoadmapTask.created_at.asc(),
                ).label("queue_position"),
            )
            .where(RoadmapTask.task_type == "creation")
            .where(RoadmapTask.status == "pending")
            .where(
                or_(
                    and_(
                        RoadmapTask.current_step.is_not(None),
                        RoadmapTask.current_step != "init",
                    ),
                    RoadmapTask.created_at >= stale_cutoff_time,
                )
            )
            .subquery()
        )

        query = select(
            visible_pending_creation_query.c.task_id,
            visible_pending_creation_query.c.queue_position,
        )

        if task_ids is not None:
            query = query.where(visible_pending_creation_query.c.task_id.in_(task_ids))

        result = await session.execute(query)
        return {
            task_id: {
                "queue_ahead_count": queue_position - 1,
                "queue_position": queue_position,
            }
            for task_id, queue_position in result.all()
        }

    async def get_creation_queue_info(
        self,
        session: AsyncSession,
        task: RoadmapTask,
    ) -> tuple[int, int] | None:
        """
        获取创建类任务的排队信息。

        仅对仍处于 pending 状态的 creation 任务生效，用于前端展示
        “前方还有多少任务”这类缓解焦虑的提示。

        Args:
            session: 数据库会话
            task: 当前任务

        Returns:
            tuple[int, int] | None:
                - ahead_count: 前方排队任务数
                - position: 当前任务在队列中的位置（从1开始）
                - None: 不适用排队统计的任务
        """
        if task.status != "pending" or task.task_type != "creation" or not task.created_at:
            return None

        queue_info_map = await self.get_creation_queue_info_map(session, [task.task_id])
        queue_info = queue_info_map.get(task.task_id)
        if not queue_info:
            return None

        return queue_info["queue_ahead_count"], queue_info["queue_position"]
    
    async def update_execution_summary(
        self,
        session: AsyncSession,
        task_id: str,
        execution_summary: dict,
    ) -> bool:
        """
        更新任务的执行摘要
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            execution_summary: 执行摘要字典
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_summary_update", task_id=task_id)
            return False
        
        task.execution_summary = execution_summary
        task.updated_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_execution_summary_updated",
            task_id=task_id,
            summary=execution_summary,
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
    
    async def find_interrupted_tasks(
        self,
        session: AsyncSession,
        max_age_hours: int = 24,
    ) -> List[RoadmapTask]:
        """
        查找被中断的任务
        
        被中断的任务定义：
        - 状态为 "processing"（正在处理中）
        - updated_at 时间距离现在超过 max_age_hours 小时
        
        Args:
            session: 数据库会话
            max_age_hours: 最大年龄（小时），超过此时间未更新的任务被认为是中断的
            
        Returns:
            被中断的任务列表
        """
        from datetime import timedelta
        
        # 计算截止时间（北京时间）
        cutoff_time = beijing_now() - timedelta(hours=max_age_hours)
        
        # 查询状态为 processing 且长时间未更新的任务
        result = await session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.status == "processing",
                RoadmapTask.updated_at < cutoff_time,
            )
            .order_by(RoadmapTask.updated_at.asc())
        )
        
        interrupted_tasks = list(result.scalars().all())
        
        logger.info(
            "find_interrupted_tasks_completed",
            max_age_hours=max_age_hours,
            cutoff_time=cutoff_time.isoformat(),
            count=len(interrupted_tasks),
        )
        
        return interrupted_tasks

    async def find_stale_processing_tasks(
        self,
        session: AsyncSession,
        *,
        stale_after_minutes: int,
        limit: Optional[int] = 20,
    ) -> List[RoadmapTask]:
        """
        查找长时间未更新的 processing 任务

        该方法用于后台 watchdog 与管理员手动清理场景。

        Args:
            session: 数据库会话
            stale_after_minutes: 判定为卡住的分钟阈值
            limit: 单次最多返回的任务数量；为 None 时返回全部

        Returns:
            符合条件的任务列表
        """
        cutoff_time = beijing_now() - timedelta(minutes=stale_after_minutes)

        query = (
            select(RoadmapTask)
            .where(
                RoadmapTask.status == "processing",
                RoadmapTask.updated_at < cutoff_time,
            )
            .order_by(RoadmapTask.updated_at.asc())
        )
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)

        stale_tasks = list(result.scalars().all())

        logger.info(
            "find_stale_processing_tasks_completed",
            stale_after_minutes=stale_after_minutes,
            cutoff_time=cutoff_time.isoformat(),
            count=len(stale_tasks),
        )

        return stale_tasks

    async def count_stale_processing_tasks(
        self,
        session: AsyncSession,
        *,
        stale_after_minutes: int,
    ) -> int:
        """
        统计长时间未更新的 processing 任务数量

        Args:
            session: 数据库会话
            stale_after_minutes: 判定为卡住的分钟阈值

        Returns:
            符合条件的任务数量
        """
        cutoff_time = beijing_now() - timedelta(minutes=stale_after_minutes)

        result = await session.execute(
            select(func.count())
            .select_from(RoadmapTask)
            .where(
                RoadmapTask.status == "processing",
                RoadmapTask.updated_at < cutoff_time,
            )
        )

        return int(result.scalar_one() or 0)
    
    async def find_orphaned_pending_creation_tasks(
        self,
        session: AsyncSession,
        max_age_hours: int = 2,
    ) -> List[RoadmapTask]:
        """
        查找孤儿 pending 创建任务
        
        孤儿 pending 任务定义：
        - 状态为 "pending"（从未开始执行）
        - 当前步骤为 "init"（队列消息丢失后的典型状态）
        - 任务类型为 "creation"（仅重新入队创建任务）
        - 创建时间在 max_age_hours 小时以内（避免重新处理历史脏数据）
        
        Args:
            session: 数据库会话
            max_age_hours: 最大年龄（小时），仅处理此时间内创建的任务
            
        Returns:
            孤儿 pending 任务列表
        """
        from datetime import timedelta
        
        # 计算截止时间（北京时间）：仅处理最近 max_age_hours 小时内创建的任务
        cutoff_time = beijing_now() - timedelta(hours=max_age_hours)
        
        result = await session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.status == "pending",
                RoadmapTask.current_step == "init",
                RoadmapTask.task_type == "creation",
                RoadmapTask.created_at >= cutoff_time,
            )
            .order_by(RoadmapTask.created_at.asc())
        )
        
        orphaned_tasks = list(result.scalars().all())
        
        logger.info(
            "find_orphaned_pending_creation_tasks_completed",
            max_age_hours=max_age_hours,
            cutoff_time=cutoff_time.isoformat(),
            count=len(orphaned_tasks),
        )
        
        return orphaned_tasks

    async def find_stale_pending_creation_tasks(
        self,
        session: AsyncSession,
        *,
        stale_after_hours: int,
    ) -> List[RoadmapTask]:
        """
        查找长时间停留在 init 的 pending 创建任务。

        这类任务通常意味着：
        - 分发到 Celery 之前后台协程失败；
        - Broker 消息丢失；
        - Worker/队列异常后任务未被重新入队。

        Args:
            session: 数据库会话
            stale_after_hours: 判定为陈旧 pending 的小时阈值

        Returns:
            长时间未启动的 pending 创建任务列表
        """
        cutoff_time = beijing_now() - timedelta(hours=stale_after_hours)

        result = await session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.status == "pending",
                RoadmapTask.current_step == "init",
                RoadmapTask.task_type == "creation",
                RoadmapTask.created_at < cutoff_time,
            )
            .order_by(RoadmapTask.created_at.asc())
        )

        stale_tasks = list(result.scalars().all())

        logger.info(
            "find_stale_pending_creation_tasks_completed",
            stale_after_hours=stale_after_hours,
            cutoff_time=cutoff_time.isoformat(),
            count=len(stale_tasks),
        )

        return stale_tasks
    
    async def update_celery_id(
        self,
        session: AsyncSession,
        task_id: str,
        celery_task_id: str,
    ) -> bool:
        """
        更新任务的Celery任务ID
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            celery_task_id: Celery任务ID
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_celery_id_update", task_id=task_id)
            return False
        
        task.celery_task_id = celery_task_id
        task.updated_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_celery_id_updated",
            task_id=task_id,
            celery_task_id=celery_task_id,
        )
        
        return True
    
    async def mark_task_recovery_failed(
        self,
        session: AsyncSession,
        task_id: str,
        reason: str,
    ) -> bool:
        """
        标记任务恢复失败
        
        用于服务器重启后任务恢复失败的场景。
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            reason: 失败原因
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_recovery_failed", task_id=task_id)
            return False
        
        task.status = "failed"
        task.content_generation_status = "failed"
        task.error_message = f"任务恢复失败: {reason}"
        task.current_step = "recovery_failed"
        task.completed_at = beijing_now()
        task.updated_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_marked_as_recovery_failed",
            task_id=task_id,
            reason=reason,
        )
        
        return True
    
    async def update_content_generation_celery_id(
        self,
        session: AsyncSession,
        task_id: str,
        celery_id: str,
    ) -> bool:
        """
        更新内容生成 Celery 任务 ID
        
        用于独立内容生成 Worker 的任务追踪。
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            celery_id: 内容生成 Celery 协调任务 ID
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_content_celery_id_update", task_id=task_id)
            return False
        
        task.content_generation_celery_id = celery_id
        task.content_generation_status = "processing"
        task.updated_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_content_generation_celery_id_updated",
            task_id=task_id,
            celery_id=celery_id,
        )
        
        return True
    
    async def update_content_generation_status(
        self,
        session: AsyncSession,
        task_id: str,
        status: str,
    ) -> bool:
        """
        更新内容生成状态
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            status: 内容生成状态（pending | processing | completed | partial_failure | failed）
            
        Returns:
            是否成功
        """
        task = await self.get_by_task_id(session, task_id)
        if not task:
            logger.error("task_not_found_for_content_status_update", task_id=task_id)
            return False
        
        task.content_generation_status = status
        task.updated_at = beijing_now()
        
        session.add(task)
        await session.flush()
        
        logger.info(
            "task_content_generation_status_updated",
            task_id=task_id,
            status=status,
        )
        
        return True


    # ========== 管理员监控专用方法 ==========

    async def get_by_celery_task_id(
        self,
        session: AsyncSession,
        celery_task_id: str,
    ) -> Optional[RoadmapTask]:
        """
        通过 Celery 任务 ID 反查业务任务

        Args:
            session: 数据库会话
            celery_task_id: Celery 任务 ID

        Returns:
            关联的业务任务，或 None
        """
        result = await session.execute(
            select(RoadmapTask).where(
                or_(
                    RoadmapTask.celery_task_id == celery_task_id,
                    RoadmapTask.content_generation_celery_id == celery_task_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_admin_tasks(
        self,
        session: AsyncSession,
        *,
        statuses: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        days: int = 1,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RoadmapTask]:
        """
        管理员任务列表查询（按时间范围、状态、类型筛选）

        Args:
            session: 数据库会话
            statuses: 多状态筛选
            task_type: 任务类型筛选（creation/retry_* 等）
            days: 查询最近 N 天的任务
            skip: 分页偏移
            limit: 返回数量上限

        Returns:
            任务列表
        """
        cutoff_time = beijing_now() - timedelta(days=days)

        query = (
            select(RoadmapTask)
            .where(RoadmapTask.created_at >= cutoff_time)
        )

        if statuses:
            query = query.where(RoadmapTask.status.in_(statuses))
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)

        query = query.order_by(RoadmapTask.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_admin_tasks(
        self,
        session: AsyncSession,
        *,
        statuses: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        days: int = 1,
    ) -> int:
        """
        统计管理员任务总数（与 get_admin_tasks 参数保持一致）

        Args:
            session: 数据库会话
            statuses: 多状态筛选
            task_type: 任务类型筛选
            days: 查询最近 N 天

        Returns:
            符合条件的任务总数
        """
        cutoff_time = beijing_now() - timedelta(days=days)

        query = (
            select(func.count())
            .select_from(RoadmapTask)
            .where(RoadmapTask.created_at >= cutoff_time)
        )

        if statuses:
            query = query.where(RoadmapTask.status.in_(statuses))
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)

        result = await session.execute(query)
        return int(result.scalar_one() or 0)

    async def get_admin_status_counts(
        self,
        session: AsyncSession,
        *,
        days: int = 1,
    ) -> Dict[str, int]:
        """
        管理员监控总览：按状态统计过去 N 天的任务数

        返回结构：
        {
            "pending": N,
            "processing": N,
            "completed": N,
            "failed": N,
            "human_review_pending": N,
            ...
        }

        Args:
            session: 数据库会话
            days: 统计最近 N 天（用于 24h 维度统计时传 1）

        Returns:
            各状态任务数字典
        """
        cutoff_time = beijing_now() - timedelta(days=days)

        result = await session.execute(
            select(RoadmapTask.status, func.count(RoadmapTask.task_id).label("count"))
            .where(RoadmapTask.created_at >= cutoff_time)
            .group_by(RoadmapTask.status)
        )
        return {row.status: row.count for row in result}

    async def get_active_status_counts(
        self,
        session: AsyncSession,
    ) -> Dict[str, int]:
        """
        统计当前活跃任务数（不限时间范围，仅统计未终结状态）

        活跃状态：pending、processing、human_review_pending、running

        Returns:
            各活跃状态的任务数字典
        """
        active_statuses = ["pending", "processing", "human_review_pending", "running"]

        result = await session.execute(
            select(RoadmapTask.status, func.count(RoadmapTask.task_id).label("count"))
            .where(RoadmapTask.status.in_(active_statuses))
            .group_by(RoadmapTask.status)
        )
        return {row.status: row.count for row in result}


# 工厂函数
def get_task_crud() -> TaskCRUD:
    """获取TaskCRUD实例"""
    return TaskCRUD(RoadmapTask)

