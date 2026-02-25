"""
Pending 任务重新入队服务

解决 Celery 队列被清空后，数据库中遗留的「孤儿 pending 任务」问题。

问题场景：
1. 用户提交任务 → DB 写入 status=pending/current_step=init
2. Celery 消息分发到 Redis 队列
3. 执行 clear_celery_queue.py 或 Worker 重启导致队列清空
4. Redis 队列消息丢失，DB 记录依然存在
5. Worker 重启后队列为空，任务永远不会执行

解决方案：
- FastAPI 启动时扫描 pending+init+creation 且最近 N 小时内创建的任务
- 对这类孤儿任务调用 generate_roadmap.apply_async 重新入队
- 更新 celery_task_id（覆盖旧值）
"""
import asyncio
import structlog

from app.config.settings import settings
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.schemas.task_recovery import PendingTaskRecoveryReport

logger = structlog.get_logger()


class PendingTaskRecoveryService:
    """
    Pending 任务重新入队服务
    
    负责在服务启动后将孤儿 pending 任务重新分发到 Celery。
    与 TaskRecoveryService 互补：
    - TaskRecoveryService：恢复 processing 任务（依赖 LangGraph checkpoint）
    - PendingTaskRecoveryService：恢复 pending 任务（直接重新 apply_async）
    """
    
    def __init__(self, max_age_hours: int = 2):
        """
        Args:
            max_age_hours: 仅处理此时间窗口内创建的 pending 任务
        """
        self.max_age_hours = max_age_hours
    
    async def recover_orphaned_pending_tasks(self) -> PendingTaskRecoveryReport:
        """
        扫描并重新入队所有孤儿 pending 任务（主入口）
        
        Returns:
            Pending 任务重新入队报告
        """
        logger.info(
            "pending_task_recovery_starting",
            max_age_hours=self.max_age_hours,
        )
        
        result = PendingTaskRecoveryReport()
        
        try:
            # 第一步：查询孤儿 pending 任务
            async with async_session_maker() as session:
                task_crud = get_task_crud()
                orphaned_tasks = await task_crud.find_orphaned_pending_creation_tasks(
                    session=session,
                    max_age_hours=self.max_age_hours,
                )
            
            result.total_found = len(orphaned_tasks)
            result.task_ids = [t.task_id for t in orphaned_tasks]
            
            if not orphaned_tasks:
                logger.info("pending_task_recovery_no_tasks_found")
                return result
            
            logger.info(
                "pending_task_recovery_tasks_found",
                count=len(orphaned_tasks),
                task_ids=result.task_ids,
            )
            
            # 第二步：逐个重新入队
            for task in orphaned_tasks:
                task_result = await self._re_enqueue_task(task)
                if task_result == "re_enqueued":
                    result.re_enqueued += 1
                elif task_result == "skipped":
                    result.skipped += 1
                else:
                    result.failed += 1
            
            logger.info(
                "pending_task_recovery_completed",
                total_found=result.total_found,
                re_enqueued=result.re_enqueued,
                skipped=result.skipped,
                failed=result.failed,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "pending_task_recovery_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def _re_enqueue_task(self, task) -> str:
        """
        将单个 pending 任务重新分发到 Celery
        
        Args:
            task: RoadmapTask 实例
            
        Returns:
            处理结果：
            - "re_enqueued": 成功重新入队
            - "skipped": 数据格式异常，跳过
            - "failed": 入队失败
        """
        task_id = task.task_id
        
        logger.info(
            "pending_task_re_enqueue_starting",
            task_id=task_id,
            user_id=task.user_id,
            created_at=task.created_at.isoformat() if task.created_at else None,
        )
        
        # 第一步：从 user_request 提取 Celery 任务所需参数
        try:
            user_request = task.user_request or {}
            preferences = user_request.get("preferences", {})
            
            learning_goal = preferences.get("learning_goal", "")
            if not learning_goal:
                logger.warning(
                    "pending_task_re_enqueue_missing_learning_goal",
                    task_id=task_id,
                )
                return "skipped"
            
            kwargs = {
                "task_id": task_id,
                "user_request": learning_goal,
                "user_id": task.user_id,
                "learning_preferences": preferences,
            }
            
        except Exception as e:
            logger.warning(
                "pending_task_re_enqueue_parse_error",
                task_id=task_id,
                error=str(e),
            )
            return "skipped"
        
        # 第二步：重新分发到 Celery
        try:
            from app.tasks.roadmap_generation_tasks import generate_roadmap
            
            celery_task = await asyncio.to_thread(
                generate_roadmap.apply_async,
                kwargs=kwargs,
            )
            
            logger.info(
                "pending_task_re_enqueued",
                task_id=task_id,
                new_celery_task_id=celery_task.id,
                old_celery_task_id=task.celery_task_id,
            )
            
        except Exception as e:
            logger.error(
                "pending_task_re_enqueue_dispatch_failed",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return "failed"
        
        # 第三步：更新 celery_task_id（覆盖旧值）
        try:
            async with async_session_maker.begin() as session:
                task_crud = get_task_crud()
                await task_crud.update_celery_id(
                    session=session,
                    task_id=task_id,
                    celery_task_id=celery_task.id,
                )
        except Exception as e:
            # 更新 celery_task_id 失败不影响任务执行，记录日志即可
            logger.warning(
                "pending_task_re_enqueue_update_celery_id_failed",
                task_id=task_id,
                new_celery_task_id=celery_task.id,
                error=str(e),
            )
        
        return "re_enqueued"


# 全局单例
pending_task_recovery_service = PendingTaskRecoveryService(
    max_age_hours=settings.PENDING_TASK_RECOVERY_MAX_AGE_HOURS,
)


async def recover_orphaned_pending_tasks_on_startup() -> PendingTaskRecoveryReport:
    """
    启动时重新入队孤儿 pending 任务的便捷函数
    
    在应用启动时调用，自动重新入队因队列清空或 Worker 重启而遗失的 pending 任务。
    
    Returns:
        Pending 任务重新入队报告
    """
    if not settings.ENABLE_PENDING_TASK_RECOVERY:
        logger.info("pending_task_recovery_disabled_by_config")
        return PendingTaskRecoveryReport()
    
    return await pending_task_recovery_service.recover_orphaned_pending_tasks()
