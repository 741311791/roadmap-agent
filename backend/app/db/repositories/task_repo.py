"""
任务 Repository

负责 RoadmapTask 表的数据访问操作。

职责范围：
- 任务的 CRUD 操作
- 任务状态查询和更新
- 活跃任务查询

不包含：
- 业务逻辑计算（如状态聚合）
- 通知发送
- 日志记录（只保留数据访问日志）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import RoadmapTask, beijing_now
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class TaskRepository(BaseRepository[RoadmapTask]):
    """
    任务数据访问层
    
    管理路线图生成任务的数据库操作。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RoadmapTask)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_task_id(self, task_id: str) -> Optional[RoadmapTask]:
        """
        根据 task_id 查询任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务记录，如果不存在则返回 None
        """
        return await self.get_by_id(task_id)
    
    async def get_task(self, task_id: str) -> Optional[RoadmapTask]:
        """
        根据 task_id 查询任务（get_by_task_id 的别名，保持与 RoadmapRepository 的兼容性）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务记录，如果不存在则返回 None
        """
        return await self.get_by_task_id(task_id)
    
    async def get_active_task_by_roadmap(
        self,
        roadmap_id: str,
    ) -> Optional[RoadmapTask]:
        """
        通过 roadmap_id 获取活跃任务
        
        查询状态为 pending, processing 或 human_review_pending 的任务。
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            活跃任务记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.roadmap_id == roadmap_id,
                RoadmapTask.status.in_(["pending", "processing", "human_review_pending"]),
            )
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        
        task = result.scalar_one_or_none()
        
        if task:
            logger.debug(
                "active_task_found",
                roadmap_id=roadmap_id,
                task_id=task.task_id,
                status=task.status,
            )
        
        return task
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[RoadmapTask]:
        """
        查询用户的任务列表
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 分页偏移
            status: 过滤状态（可选）
            
        Returns:
            任务列表（按创建时间降序）
        """
        query = (
            select(RoadmapTask)
            .where(RoadmapTask.user_id == user_id)
        )
        
        if status:
            query = query.where(RoadmapTask.status == status)
        
        query = query.order_by(RoadmapTask.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        tasks = list(result.scalars().all())
        
        logger.debug(
            "tasks_listed_by_user",
            user_id=user_id,
            count=len(tasks),
            status_filter=status,
        )
        
        return tasks
    
    async def count_by_status(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        统计任务数量（按状态）
        
        Args:
            user_id: 用户 ID（可选，为 None 时统计所有用户）
            status: 状态过滤（可选）
            
        Returns:
            任务数量
        """
        query = select(func.count()).select_from(RoadmapTask)
        
        if user_id:
            query = query.where(RoadmapTask.user_id == user_id)
        
        if status:
            query = query.where(RoadmapTask.status == status)
        
        result = await self.session.execute(query)
        count = result.scalar_one()
        
        logger.debug(
            "tasks_counted",
            user_id=user_id,
            status=status,
            count=count,
        )
        
        return count
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def create_task(
        self,
        task_id: str,
        user_id: str,
        user_request: dict,
        task_type: str = "creation",
        concept_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> RoadmapTask:
        """
        创建路线图生成任务
        
        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            user_request: 用户请求（字典格式）
            task_type: 任务类型（'creation', 'retry_tutorial', 'retry_resources', 'retry_quiz', 'retry_batch'）
            concept_id: 概念 ID（重试任务需要）
            content_type: 内容类型（重试任务需要）
            
        Returns:
            创建的任务记录
        """
        task = RoadmapTask(
            task_id=task_id,
            user_id=user_id,
            user_request=user_request,
            status="pending",
            current_step="init",
            task_type=task_type,
            concept_id=concept_id,
            content_type=content_type,
        )
        
        # flush=True 以立即获取数据库生成的字段
        await self.create(task, flush=True)
        
        logger.info(
            "roadmap_task_created",
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
        )
        
        return task
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        current_step: str,
        roadmap_id: Optional[str] = None,
        error_message: Optional[str] = None,
        failed_concepts: Optional[dict] = None,
        execution_summary: Optional[dict] = None,
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态 (pending, processing, completed, partial_failure, failed)
            current_step: 当前步骤
            roadmap_id: 路线图 ID（可选）
            error_message: 错误信息（可选）
            failed_concepts: 失败概念详情（可选）
            execution_summary: 执行摘要（可选）
            
        Returns:
            True 如果更新成功，False 如果任务不存在
        """
        update_data = {
            "status": status,
            "current_step": current_step,
            "updated_at": beijing_now(),
        }
        
        # 可选字段
        if roadmap_id:
            update_data["roadmap_id"] = roadmap_id
        if error_message:
            update_data["error_message"] = error_message
        if failed_concepts is not None:
            update_data["failed_concepts"] = failed_concepts
        if execution_summary is not None:
            update_data["execution_summary"] = execution_summary
        
        # 任务完成时设置 completed_at（包括取消状态）
        if status in ("completed", "partial_failure", "failed", "cancelled"):
            update_data["completed_at"] = beijing_now()
        # 任务重新开始时清除 completed_at 和 error_message（重要：重试时恢复到处理中状态）
        elif status == "processing":
            update_data["completed_at"] = None
            # 只在没有显式传入error_message时才清除（避免覆盖新的错误消息）
            if error_message is None:
                update_data["error_message"] = None
        
        updated = await self.update_by_id(task_id, **update_data)
        
        if updated:
            logger.info(
                "roadmap_task_updated",
                task_id=task_id,
                status=status,
                current_step=current_step,
                has_failed_concepts=failed_concepts is not None,
                has_execution_summary=execution_summary is not None,
            )
        
        return updated
    
    async def update_task_roadmap_id(
        self,
        task_id: str,
        roadmap_id: str,
    ) -> bool:
        """
        更新任务的 roadmap_id
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            
        Returns:
            True 如果更新成功，False 如果任务不存在
        """
        return await self.update_by_id(
            task_id,
            roadmap_id=roadmap_id,
            updated_at=beijing_now(),
        )
    
    async def update_task_celery_id(
        self,
        task_id: str,
        celery_task_id: str,
    ) -> bool:
        """
        更新任务的 celery_task_id
        
        Args:
            task_id: 任务 ID
            celery_task_id: Celery 任务 ID
            
        Returns:
            True 如果更新成功，False 如果任务不存在
        """
        updated = await self.update_by_id(
            task_id,
            celery_task_id=celery_task_id,
            updated_at=beijing_now(),
        )
        
        if updated:
            logger.info(
                "task_celery_id_updated",
                task_id=task_id,
                celery_task_id=celery_task_id,
            )
        
        return updated
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            True 如果删除成功，False 如果任务不存在
        """
        deleted = await self.delete_by_id(task_id)
        
        if deleted:
            logger.info("roadmap_task_deleted", task_id=task_id)
        
        return deleted
    
    # ============================================================
    # 任务恢复相关方法
    # ============================================================
    
    async def find_interrupted_tasks(
        self,
        max_age_hours: int = 24,
    ) -> List[RoadmapTask]:
        """
        查找被中断的任务（服务器重启后需要恢复的任务）
        
        中断任务的特征：
        - 状态为 "processing"（正在执行中被中断）
        - 创建时间在 max_age_hours 小时内（避免恢复太旧的任务）
        - 任务类型为 "creation"（只恢复创建任务，不恢复重试任务）
        
        注意：不恢复 "human_review_pending" 状态的任务，因为这些任务需要用户手动操作。
        
        Args:
            max_age_hours: 任务最大年龄（小时），超过此时间的任务不会被恢复
            
        Returns:
            被中断的任务列表（按创建时间升序，先创建的先恢复）
        """
        from datetime import timedelta
        
        # 计算时间阈值（只恢复最近 max_age_hours 小时内的任务）
        cutoff_time = beijing_now() - timedelta(hours=max_age_hours)
        
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.status == "processing",
                RoadmapTask.created_at >= cutoff_time,
                # 只恢复创建任务，重试任务需要用户手动触发
                RoadmapTask.task_type == "creation",
            )
            .order_by(RoadmapTask.created_at.asc())  # 先创建的先恢复
        )
        
        tasks = list(result.scalars().all())
        
        logger.info(
            "interrupted_tasks_found",
            count=len(tasks),
            max_age_hours=max_age_hours,
            cutoff_time=cutoff_time.isoformat(),
        )
        
        return tasks
    
    async def mark_task_recovery_failed(
        self,
        task_id: str,
        reason: str,
    ) -> bool:
        """
        标记任务恢复失败
        
        当无法从 checkpoint 恢复任务时，将任务标记为失败。
        
        Args:
            task_id: 任务 ID
            reason: 失败原因
            
        Returns:
            True 如果更新成功
        """
        error_message = f"任务恢复失败: {reason}"
        
        updated = await self.update_task_status(
            task_id=task_id,
            status="failed",
            current_step="recovery_failed",
            error_message=error_message,
        )
        
        if updated:
            logger.warning(
                "task_recovery_marked_failed",
                task_id=task_id,
                reason=reason,
            )
        
        return updated
