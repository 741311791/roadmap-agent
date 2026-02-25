"""
封面图生成 Celery 任务

负责在后台异步生成路线图封面图，解决 BackgroundTasks 导致的 Session 泄漏问题。

架构变更（v2.0）：
- 旧方案：FastAPI BackgroundTasks + 请求级 Session（存在泄漏风险）
- 新方案：Celery 独立进程 + 独立 Session（资源隔离）

优势：
1. 独立进程，独立数据库连接
2. 支持任务重试和失败处理
3. 任务状态可追踪（通过 roadmap_tasks 表）
4. 避免 HTTP 请求结束后 Session 关闭的问题
"""
from typing import Optional
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.services.roadmaps.cover_image_service import CoverImageService
from app.db.celery_session import get_celery_session
from app.models.database import RoadmapTask, beijing_now
import structlog

logger = structlog.get_logger()


async def _update_task_status(
    task_id: str,
    status: str,
    current_step: str,
    error_message: Optional[str] = None,
) -> None:
    """
    使用独立 Session 更新 RoadmapTask 状态
    
    Args:
        task_id: RoadmapTask 的任务 ID
        status: 新状态（pending/processing/completed/failed）
        current_step: 当前步骤标识
        error_message: 错误信息（失败时）
    """
    async with get_celery_session() as session:
        stmt = select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            task.current_step = current_step
            task.updated_at = beijing_now()
            if status in ("completed", "failed"):
                task.completed_at = beijing_now()
            if error_message:
                task.error_message = error_message


@celery_app.task(
    name="cover_image.generate",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_cover_image_task(self, roadmap_id: str, prompt: str = None, task_id: str = None):
    """
    封面图生成任务（Celery Worker）
    
    Args:
        self: Celery 任务实例（bind=True 时注入）
        roadmap_id: 路线图 ID
        prompt: 图片生成提示词（可选）
        task_id: RoadmapTask ID（用户手动触发时传入，自动触发时为 None）
    
    Returns:
        dict: 生成结果
            - status: "success" | "failed"
            - roadmap_id: 路线图 ID
            - cover_image_url: 封面图 URL（成功时）
            - error: 错误信息（失败时）
    
    Raises:
        Exception: 任务执行失败时抛出异常，触发自动重试
    """
    from app.tasks.event_loop_manager import run_async_in_worker_loop
    
    try:
        logger.info(
            "cover_image_task_started",
            roadmap_id=roadmap_id,
            celery_task_id=self.request.id,
            roadmap_task_id=task_id,
            retry_count=self.request.retries,
        )
        
        # ✅ 在 Worker 进程的持久事件循环中执行异步逻辑
        # 注意：使用 run_async_in_worker_loop() 替代 asyncio.run()，
        #      避免创建新的 event loop（可能与 OrchestratorFactory 的 Lock 冲突）
        result = run_async_in_worker_loop(_generate_cover_image_async(roadmap_id, prompt, task_id))
        
        logger.info(
            "cover_image_task_completed",
            roadmap_id=roadmap_id,
            celery_task_id=self.request.id,
            roadmap_task_id=task_id,
            status=result["status"],
            cover_image_url=result.get("cover_image_url"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "cover_image_task_failed",
            roadmap_id=roadmap_id,
            celery_task_id=self.request.id,
            roadmap_task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
            retry_count=self.request.retries,
            exc_info=True,
        )
        
        # 所有重试耗尽后，将 RoadmapTask 标记为 failed
        if task_id and self.request.retries >= self.max_retries:
            try:
                run_async_in_worker_loop(
                    _update_task_status(task_id, "failed", "failed", str(e))
                )
            except Exception as update_err:
                logger.warning(
                    "failed_to_update_task_status_on_error",
                    task_id=task_id,
                    update_error=str(update_err),
                )
        
        # 抛出异常，触发自动重试
        raise


async def _generate_cover_image_async(
    roadmap_id: str,
    prompt: str = None,
    task_id: str = None,
) -> dict:
    """
    异步生成封面图（内部辅助函数）
    
    Args:
        roadmap_id: 路线图 ID
        prompt: 图片生成提示词（可选）
        task_id: RoadmapTask ID（有值时同步更新任务状态）
    
    Returns:
        dict: 生成结果
    """
    # 更新任务状态为 processing（使用独立 Session，避免与封面图生成事务相互干扰）
    if task_id:
        await _update_task_status(task_id, "processing", "generating_cover")
    
    async with get_celery_session() as session:
        # 创建服务实例（使用独立 Session）
        service = CoverImageService(session)
        
        # 执行封面图生成
        cover_image_url = await service.generate_cover_image(
            roadmap_id=roadmap_id,
            prompt=prompt,
        )
        
        # get_celery_session() 会自动 commit/rollback
    
    if cover_image_url:
        # 更新任务状态为 completed
        if task_id:
            await _update_task_status(task_id, "completed", "completed")
        return {
            "status": "success",
            "roadmap_id": roadmap_id,
            "cover_image_url": cover_image_url,
        }
    else:
        # 更新任务状态为 failed
        if task_id:
            await _update_task_status(task_id, "failed", "failed", "封面图生成失败（API 返回空）")
        return {
            "status": "failed",
            "roadmap_id": roadmap_id,
            "error": "封面图生成失败（API 返回空）",
        }



