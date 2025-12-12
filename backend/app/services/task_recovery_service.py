"""
任务恢复服务

服务器重启后自动恢复被中断任务的核心服务。

功能：
1. 扫描数据库中状态为 "processing" 的任务
2. 检查 LangGraph checkpoint 是否存在
3. 从 checkpoint 恢复工作流执行
4. 处理无法恢复的任务（标记为失败）

最佳实践：
- 恢复任务在后台异步执行，不阻塞服务启动
- 任务恢复有重试限制，避免无限重试
- 详细的日志记录，方便追踪恢复过程
- 支持配置是否启用自动恢复
"""
import asyncio
import structlog
from datetime import datetime

from app.config.settings import settings
from app.core.orchestrator_factory import OrchestratorFactory
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory
from app.models.database import RoadmapTask, beijing_now
from app.services.notification_service import notification_service

logger = structlog.get_logger()


class TaskRecoveryService:
    """
    任务恢复服务
    
    负责在服务器启动后恢复被中断的任务。
    
    使用 LangGraph 的 checkpoint 机制，通过传入 None 作为输入，
    让工作流从最后保存的 checkpoint 继续执行。
    """
    
    def __init__(
        self,
        max_age_hours: int = 24,
        max_concurrent_recoveries: int = 3,
        recovery_delay_seconds: float = 5.0,
    ):
        """
        Args:
            max_age_hours: 任务最大年龄（小时），超过此时间的任务不会被恢复
            max_concurrent_recoveries: 最大并发恢复数量
            recovery_delay_seconds: 恢复任务之间的延迟（秒），避免瞬间压力
        """
        self.max_age_hours = max_age_hours
        self.max_concurrent_recoveries = max_concurrent_recoveries
        self.recovery_delay_seconds = recovery_delay_seconds
        self.repo_factory = RepositoryFactory()
        self._recovery_tasks: dict[str, asyncio.Task] = {}
    
    async def recover_interrupted_tasks(self) -> dict:
        """
        恢复所有被中断的任务（主入口）
        
        Returns:
            恢复结果摘要：{
                "total_found": int,      # 找到的中断任务数
                "recovered": int,        # 成功恢复的任务数
                "failed": int,           # 恢复失败的任务数
                "no_checkpoint": int,    # 没有 checkpoint 的任务数
                "task_ids": list[str],   # 尝试恢复的任务 ID 列表
            }
        """
        logger.info(
            "task_recovery_starting",
            max_age_hours=self.max_age_hours,
            max_concurrent=self.max_concurrent_recoveries,
        )
        
        result = {
            "total_found": 0,
            "recovered": 0,
            "failed": 0,
            "no_checkpoint": 0,
            "task_ids": [],
        }
        
        try:
            # 1. 查找被中断的任务
            async with self.repo_factory.create_session() as session:
                task_repo = self.repo_factory.create_task_repo(session)
                interrupted_tasks = await task_repo.find_interrupted_tasks(
                    max_age_hours=self.max_age_hours
                )
            
            result["total_found"] = len(interrupted_tasks)
            result["task_ids"] = [t.task_id for t in interrupted_tasks]
            
            if not interrupted_tasks:
                logger.info("task_recovery_no_tasks_found")
                return result
            
            logger.info(
                "task_recovery_tasks_found",
                count=len(interrupted_tasks),
                task_ids=result["task_ids"],
            )
            
            # 2. 使用 semaphore 限制并发恢复数量
            semaphore = asyncio.Semaphore(self.max_concurrent_recoveries)
            
            async def recover_with_semaphore(task: RoadmapTask) -> str:
                """带并发控制的恢复包装器"""
                async with semaphore:
                    return await self._recover_single_task(task)
            
            # 3. 并发恢复所有任务
            recovery_results = await asyncio.gather(
                *[recover_with_semaphore(task) for task in interrupted_tasks],
                return_exceptions=True,
            )
            
            # 4. 统计结果
            for task_result in recovery_results:
                if isinstance(task_result, Exception):
                    result["failed"] += 1
                elif task_result == "recovered":
                    result["recovered"] += 1
                elif task_result == "no_checkpoint":
                    result["no_checkpoint"] += 1
                else:
                    result["failed"] += 1
            
            logger.info(
                "task_recovery_completed",
                **result,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "task_recovery_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def _recover_single_task(self, task: RoadmapTask) -> str:
        """
        恢复单个任务
        
        Args:
            task: 要恢复的任务
            
        Returns:
            恢复结果：
            - "recovered": 成功恢复
            - "no_checkpoint": 没有找到 checkpoint
            - "failed": 恢复失败
        """
        task_id = task.task_id
        
        logger.info(
            "task_recovery_single_starting",
            task_id=task_id,
            current_step=task.current_step,
            created_at=task.created_at.isoformat() if task.created_at else None,
        )
        
        try:
            # 1. 获取 checkpointer
            checkpointer = OrchestratorFactory.get_checkpointer()
            
            # 2. 检查是否存在 checkpoint
            config = {"configurable": {"thread_id": task_id}}
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            
            if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
                logger.warning(
                    "task_recovery_no_checkpoint",
                    task_id=task_id,
                    has_tuple=checkpoint_tuple is not None,
                )
                # 标记任务为失败（没有 checkpoint 无法恢复）
                await self._mark_task_failed(
                    task_id=task_id,
                    reason="服务器重启后没有找到 checkpoint 数据，无法恢复执行"
                )
                return "no_checkpoint"
            
            # 3. 获取 checkpoint 中的当前步骤（用于日志）
            channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
            checkpoint_step = channel_values.get("current_step", "unknown")
            
            logger.info(
                "task_recovery_checkpoint_found",
                task_id=task_id,
                checkpoint_step=checkpoint_step,
                checkpoint_id=checkpoint_tuple.checkpoint.get("id"),
            )
            
            # 4. 添加延迟，避免同时恢复太多任务造成压力
            if self.recovery_delay_seconds > 0:
                await asyncio.sleep(self.recovery_delay_seconds)
            
            # 5. 创建新的 executor 并从 checkpoint 恢复
            executor = OrchestratorFactory.create_workflow_executor()
            
            # 6. 在后台任务中恢复执行（不阻塞当前恢复流程）
            recovery_task = asyncio.create_task(
                self._execute_recovery(executor, task_id, config)
            )
            self._recovery_tasks[task_id] = recovery_task
            
            # 发送 WebSocket 通知
            await notification_service.notify_task_recovering(
                task_id=task_id,
                roadmap_id=task.roadmap_id,
                current_step=checkpoint_step,
            )
            
            logger.info(
                "task_recovery_started_in_background",
                task_id=task_id,
                checkpoint_step=checkpoint_step,
            )
            
            return "recovered"
            
        except Exception as e:
            logger.error(
                "task_recovery_single_error",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await self._mark_task_failed(
                task_id=task_id,
                reason=f"恢复执行时发生异常: {str(e)}"
            )
            return "failed"
    
    async def _execute_recovery(
        self,
        executor: WorkflowExecutor,
        task_id: str,
        config: dict,
    ) -> None:
        """
        执行恢复（后台任务）
        
        使用 LangGraph 的恢复机制：传入 None 作为输入，从 checkpoint 继续执行。
        
        Args:
            executor: 工作流执行器
            task_id: 任务 ID
            config: LangGraph 配置（包含 thread_id）
        """
        try:
            logger.info(
                "task_recovery_execution_starting",
                task_id=task_id,
            )
            
            # LangGraph 恢复机制：传入 None 会从最后的 checkpoint 继续执行
            # 参考文档：graph.invoke(None, config=config)
            final_state = await executor.graph.ainvoke(None, config=config)
            
            final_step = final_state.get("current_step", "unknown")
            roadmap_id = final_state.get("roadmap_id")
            
            logger.info(
                "task_recovery_execution_completed",
                task_id=task_id,
                final_step=final_step,
                roadmap_id=roadmap_id,
            )
            
            # 清除 live_step 缓存
            executor.state_manager.clear_live_step(task_id)
            
        except Exception as e:
            logger.error(
                "task_recovery_execution_failed",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # 标记任务为失败
            await self._mark_task_failed(
                task_id=task_id,
                reason=f"恢复执行过程中发生异常: {str(e)}"
            )
        finally:
            # 清理后台任务引用
            self._recovery_tasks.pop(task_id, None)
    
    async def _mark_task_failed(self, task_id: str, reason: str) -> None:
        """
        标记任务为失败
        
        Args:
            task_id: 任务 ID
            reason: 失败原因
        """
        try:
            async with self.repo_factory.create_session() as session:
                task_repo = self.repo_factory.create_task_repo(session)
                await task_repo.mark_task_recovery_failed(
                    task_id=task_id,
                    reason=reason,
                )
                await session.commit()
                
        except Exception as e:
            logger.error(
                "task_recovery_mark_failed_error",
                task_id=task_id,
                error=str(e),
            )
    
    async def wait_for_all_recoveries(self, timeout: float = 300.0) -> None:
        """
        等待所有恢复任务完成
        
        主要用于测试和优雅关闭。
        
        Args:
            timeout: 超时时间（秒）
        """
        if not self._recovery_tasks:
            return
        
        logger.info(
            "task_recovery_waiting",
            count=len(self._recovery_tasks),
            timeout=timeout,
        )
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._recovery_tasks.values(), return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "task_recovery_wait_timeout",
                remaining_tasks=list(self._recovery_tasks.keys()),
            )


# 全局单例（使用配置文件中的设置）
task_recovery_service = TaskRecoveryService(
    max_age_hours=settings.TASK_RECOVERY_MAX_AGE_HOURS,
    max_concurrent_recoveries=settings.TASK_RECOVERY_MAX_CONCURRENT,
    recovery_delay_seconds=settings.TASK_RECOVERY_DELAY_SECONDS,
)


async def recover_interrupted_tasks_on_startup() -> dict:
    """
    启动时恢复中断任务的便捷函数
    
    在应用启动时调用，自动恢复被服务器重启中断的任务。
    
    Returns:
        恢复结果摘要
    """
    if not settings.ENABLE_TASK_RECOVERY:
        logger.info("task_recovery_disabled_by_config")
        return {
            "total_found": 0,
            "recovered": 0,
            "failed": 0,
            "no_checkpoint": 0,
            "task_ids": [],
            "disabled": True,
        }
    
    return await task_recovery_service.recover_interrupted_tasks()
