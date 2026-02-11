"""
封面图生成 Celery 任务

负责在后台异步生成路线图封面图，解决 BackgroundTasks 导致的 Session 泄漏问题。

架构变更（v2.0）：
- 旧方案：FastAPI BackgroundTasks + 请求级 Session（存在泄漏风险）
- 新方案：Celery 独立进程 + 独立 Session（资源隔离）

优势：
1. 独立进程，独立数据库连接
2. 支持任务重试和失败处理
3. 任务状态可追踪
4. 避免 HTTP 请求结束后 Session 关闭的问题
"""
from app.core.celery_app import celery_app
from app.services.roadmaps.cover_image_service import CoverImageService
from app.db.celery_session import get_celery_session
from app.crud.crud_roadmap import get_roadmap_crud
import structlog

logger = structlog.get_logger()


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
def generate_cover_image_task(self, roadmap_id: str, prompt: str = None):
    """
    封面图生成任务（Celery Worker）
    
    Args:
        self: Celery 任务实例（bind=True 时注入）
        roadmap_id: 路线图 ID
        prompt: 图片生成提示词（可选）
    
    Returns:
        dict: 生成结果
            - status: "success" | "failed"
            - roadmap_id: 路线图 ID
            - cover_image_url: 封面图 URL（成功时）
            - error: 错误信息（失败时）
    
    Raises:
        Exception: 任务执行失败时抛出异常，触发自动重试
    """
    try:
        logger.info(
            "cover_image_task_started",
            roadmap_id=roadmap_id,
            task_id=self.request.id,
            retry_count=self.request.retries,
        )
        
        # ✅ 在 Worker 进程的持久事件循环中执行异步逻辑
        # 注意：使用 run_async_in_worker_loop() 替代 asyncio.run()，
        #      避免创建新的 event loop（可能与 OrchestratorFactory 的 Lock 冲突）
        from app.tasks.event_loop_manager import run_async_in_worker_loop
        
        result = run_async_in_worker_loop(_generate_cover_image_async(roadmap_id, prompt))
        
        logger.info(
            "cover_image_task_completed",
            roadmap_id=roadmap_id,
            task_id=self.request.id,
            status=result["status"],
            cover_image_url=result.get("cover_image_url"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "cover_image_task_failed",
            roadmap_id=roadmap_id,
            task_id=self.request.id,
            error=str(e),
            error_type=type(e).__name__,
            retry_count=self.request.retries,
            exc_info=True,
        )
        
        # 抛出异常，触发自动重试
        raise


async def _generate_cover_image_async(roadmap_id: str, prompt: str = None) -> dict:
    """
    异步生成封面图（内部辅助函数）
    
    Args:
        roadmap_id: 路线图 ID
        prompt: 图片生成提示词（可选）
    
    Returns:
        dict: 生成结果
    """
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
            return {
                "status": "success",
                "roadmap_id": roadmap_id,
                "cover_image_url": cover_image_url,
            }
        else:
            return {
                "status": "failed",
                "roadmap_id": roadmap_id,
                "error": "封面图生成失败（API 返回空）",
            }


@celery_app.task(
    name="cover_image.batch_generate",
    bind=True,
    max_retries=1,
)
def batch_generate_cover_images_task(self, roadmap_ids: list[str]):
    """
    批量生成封面图任务
    
    Args:
        self: Celery 任务实例
        roadmap_ids: 路线图 ID 列表
    
    Returns:
        dict: 批量生成结果
    """
    logger.info(
        "batch_cover_image_task_started",
        task_id=self.request.id,
        total_count=len(roadmap_ids),
    )
    
    triggered = []
    
    # 为每个路线图分发独立任务
    for roadmap_id in roadmap_ids:
        task = generate_cover_image_task.delay(roadmap_id)
        triggered.append({
            "roadmap_id": roadmap_id,
            "task_id": task.id,
        })
    
    logger.info(
        "batch_cover_image_task_completed",
        task_id=self.request.id,
        triggered_count=len(triggered),
    )
    
    return {
        "triggered": len(triggered),
        "tasks": triggered,
    }

