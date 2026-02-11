"""
Tavily Key Cache 定时刷新任务

职责：
- 定期从数据库刷新 Redis 中的 Tavily Key 缓存
- 更新配额信息
- 清理失效的 Key
"""
import structlog
from app.core.celery_app import celery_app
from app.tasks.utils import run_async

logger = structlog.get_logger()


@celery_app.task(
    name="tavily_cache.refresh_keys",
    max_retries=3,
    default_retry_delay=60
)
async def refresh_tavily_key_cache():
    """
    刷新 Tavily API Key Redis 缓存（两阶段）
    
    定时执行：每 5 分钟
    
    刷新流程：
    1. ✅ Phase 1: 更新数据库配额（调用外部 API 或预留接口）
    2. ✅ Phase 2: 从数据库加载最新数据到 Redis 缓存
    3. ✅ Phase 3: 清理失效 Key
    
    Returns:
        刷新结果统计
    """
    logger.info("tavily_key_cache_refresh_task_started")
    
    try:
        # ============================================================
        # Phase 1: 更新数据库配额（调用 TavilyKeyService）
        # ============================================================
        logger.info("tavily_cache_refresh_phase1_updating_database")
        
        from app.db.celery_session import get_celery_session
        from app.services.admin.tavily_key_service import TavilyKeyService
        
        quota_update_result = None
        async with get_celery_session() as session:
            service = TavilyKeyService()
            quota_update_result = await service.batch_update_quotas_from_external_source(session)
            # Session 自动 commit
        
        logger.info(
            "tavily_cache_refresh_phase1_completed",
            quota_update_result=quota_update_result,
        )
        
        # ============================================================
        # Phase 2: 刷新 Redis 缓存（从数据库加载最新数据）
        # ============================================================
        logger.info("tavily_cache_refresh_phase2_updating_redis")
        
        from app.core.tavily_key_cache import get_tavily_key_cache
        
        key_cache = get_tavily_key_cache()
        refreshed_count = await key_cache.refresh()
        
        # 获取统计信息
        stats = await key_cache.get_cache_stats()
        
        logger.info(
            "tavily_key_cache_refresh_task_completed",
            refreshed_keys=refreshed_count,
            total_keys=stats.get("total_keys", 0),
            cache_version=stats.get("cache_version"),
        )
        
        return {
            "success": True,
            "phase1_quota_update": quota_update_result,
            "phase2_cache_refresh": {
                "refreshed_keys": refreshed_count,
                "stats": stats,
            },
        }
        
    except Exception as e:
        logger.error(
            "tavily_key_cache_refresh_task_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task(
    name="tavily_cache.cleanup_expired",
    max_retries=3,
    default_retry_delay=60
)
async def cleanup_expired_tavily_keys():
    """
    清理过期的 Tavily Key
    
    定时执行：每小时
    
    任务内容：
    1. 检查 Redis 中的所有 Key
    2. 移除配额为 0 的 Key
    3. 移除已失效的 Key
    
    Returns:
        清理结果统计
    """
    logger.info("tavily_key_cache_cleanup_task_started")
    
    try:
        from app.core.tavily_key_cache import get_tavily_key_cache
        from app.db.redis_client import redis_client
        
        key_cache = get_tavily_key_cache()
        
        # 确保 Redis 连接
        await redis_client.connect()
        
        # 获取所有 Key ID
        key_ids = await redis_client._client.smembers(key_cache.KEYS_SET)
        
        cleaned_count = 0
        for key_id in key_ids:
            key_hash = f"{key_cache.KEY_DETAIL_PREFIX}{key_id}"
            key_data = await redis_client._client.hgetall(key_hash)
            
            if not key_data:
                # Key 详情不存在，从集合中移除
                await redis_client._client.srem(key_cache.KEYS_SET, key_id)
                cleaned_count += 1
                continue
            
            # 检查配额（decode_responses=True，返回的是 str）
            remaining_quota = int(key_data.get("remaining_quota", 0))
            
            if remaining_quota <= 0:
                # 移除无效 Key
                await redis_client._client.delete(key_hash)
                await redis_client._client.srem(key_cache.KEYS_SET, key_id)
                cleaned_count += 1
                
                logger.debug(
                    "tavily_key_cleaned",
                    key_id=key_id,
                    reason="quota_exhausted",
                )
        
        stats = await key_cache.get_cache_stats()
        
        logger.info(
            "tavily_key_cache_cleanup_task_completed",
            cleaned_keys=cleaned_count,
            remaining_keys=stats.get("total_keys", 0),
        )
        
        return {
            "success": True,
            "cleaned_keys": cleaned_count,
            "remaining_keys": stats.get("total_keys", 0),
        }
        
    except Exception as e:
        logger.error(
            "tavily_key_cache_cleanup_task_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


