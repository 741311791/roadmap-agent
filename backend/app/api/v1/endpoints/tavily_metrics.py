"""
Tavily API Key 监控端点

提供 API 用于：
- 查看所有 Keys 的使用统计
- 查看所有 Keys 的健康状态
- 查看实时配额使用情况

仅限管理员访问
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
import structlog

from app.config.settings import settings
from app.db.redis_client import get_redis_client
from app.tools.search.tavily_key_manager import TavilyAPIKeyManager, KeyStats
from app.models.database import User
from app.core.auth.deps import current_active_user

logger = structlog.get_logger()
router = APIRouter()


def _get_key_manager() -> TavilyAPIKeyManager:
    """
    获取 TavilyAPIKeyManager 实例
    
    Returns:
        TavilyAPIKeyManager 实例
        
    Raises:
        HTTPException: 如果未配置 API Keys
    """
    api_keys = settings.get_tavily_api_keys
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API Keys not configured"
        )
    
    return TavilyAPIKeyManager(
        redis_client=get_redis_client(),
        api_keys=api_keys
    )


def _format_key_stats(stats: KeyStats) -> Dict[str, Any]:
    """
    格式化 KeyStats 为 JSON 可序列化的字典
    
    Args:
        stats: KeyStats 对象
        
    Returns:
        格式化后的字典
    """
    # 基本信息
    result = {
        "key_id": stats.key_id,
        "key_index": stats.key_index,
        "is_healthy": stats.is_healthy,
        "usage": {
            "total_calls": stats.total_calls,
            "success_calls": stats.success_calls,
            "failed_calls": stats.failed_calls,
            "rate_limit_errors": stats.rate_limit_errors,
            "success_rate": round(stats.success_rate * 100, 2),  # 百分比
        },
        "last_used_at": stats.last_used_at.isoformat() if stats.last_used_at else None,
    }
    
    # 配额信息（从 Tavily API 获取）
    if stats.usage_info:
        result["quota"] = {
            "key": {
                "usage": stats.usage_info.key_usage,
                "limit": stats.usage_info.key_limit,
                "remaining": stats.usage_info.key_remaining,
            },
            "plan": {
                "name": stats.usage_info.plan_name,
                "usage": stats.usage_info.plan_usage,
                "limit": stats.usage_info.plan_limit,
                "remaining": stats.usage_info.plan_remaining,
            },
            "paygo": {
                "usage": stats.usage_info.paygo_usage,
                "limit": stats.usage_info.paygo_limit,
            },
            "total_remaining": stats.usage_info.total_remaining,
        }
    else:
        result["quota"] = {
            "error": "Unable to fetch quota information from Tavily API",
            "total_remaining": "unknown",
        }
    
    return result


@router.get("/metrics")
async def get_tavily_metrics(
    current_user: User = Depends(current_active_user)
):
    """
    获取所有 Tavily API Keys 的使用统计
    
    返回每个 Key 的：
    - 调用次数、成功率
    - 配额使用情况（分钟级、日级）
    - 健康状态
    - 最后使用时间
    
    权限：需要登录
    """
    try:
        key_manager = _get_key_manager()
        
        # 获取所有 Keys 的统计信息
        all_stats = await key_manager.get_all_stats()
        
        # 格式化统计信息
        formatted_stats = [_format_key_stats(stats) for stats in all_stats]
        
        # 计算总体统计
        total_calls = sum(s.total_calls for s in all_stats)
        total_success = sum(s.success_calls for s in all_stats)
        total_failed = sum(s.failed_calls for s in all_stats)
        healthy_count = sum(1 for s in all_stats if s.is_healthy)
        
        return {
            "total_keys": len(all_stats),
            "healthy_keys": healthy_count,
            "unhealthy_keys": len(all_stats) - healthy_count,
            "overall_stats": {
                "total_calls": total_calls,
                "total_success": total_success,
                "total_failed": total_failed,
                "success_rate": round((total_success / total_calls * 100) if total_calls > 0 else 100, 2),
            },
            "keys": formatted_stats,
            "quota_tracking_enabled": settings.TAVILY_QUOTA_TRACKING_ENABLED,
        }
        
    except Exception as e:
        logger.error(
            "tavily_metrics_api_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Tavily metrics: {str(e)}"
        )


@router.get("/health")
async def get_tavily_health(
    current_user: User = Depends(current_active_user)
):
    """
    获取所有 Tavily API Keys 的健康状态
    
    返回简化的健康信息，适用于快速检查
    
    权限：需要登录
    """
    try:
        key_manager = _get_key_manager()
        
        # 获取所有 Keys 的统计信息
        all_stats = await key_manager.get_all_stats()
        
        # 提取健康状态
        health_status = [
            {
                "key_id": stats.key_id,
                "key_index": stats.key_index,
                "is_healthy": stats.is_healthy,
                "quota_exhausted": (
                    stats.usage_info.total_remaining <= 0 
                    if stats.usage_info else False
                ),
                "remaining_quota": (
                    stats.usage_info.total_remaining 
                    if stats.usage_info else "unknown"
                ),
                "rate_limit_errors": stats.rate_limit_errors,
            }
            for stats in all_stats
        ]
        
        healthy_count = sum(1 for s in all_stats if s.is_healthy)
        
        return {
            "total_keys": len(all_stats),
            "healthy_keys": healthy_count,
            "unhealthy_keys": len(all_stats) - healthy_count,
            "all_healthy": healthy_count == len(all_stats),
            "keys": health_status,
        }
        
    except Exception as e:
        logger.error(
            "tavily_health_api_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Tavily health status: {str(e)}"
        )


@router.post("/health-check")
async def trigger_health_check(
    current_user: User = Depends(current_active_user)
):
    """
    手动触发一次健康检查
    
    检查所有 Keys 的健康状态并更新 Redis
    
    权限：需要登录
    """
    try:
        key_manager = _get_key_manager()
        
        # 执行健康检查
        health_results = []
        for idx in range(len(key_manager.api_keys)):
            is_healthy = await key_manager.check_key_health(idx)
            health_results.append({
                "key_index": idx,
                "key_id": key_manager._get_key_id(idx),
                "is_healthy": is_healthy,
            })
        
        healthy_count = sum(1 for r in health_results if r["is_healthy"])
        
        logger.info(
            "tavily_manual_health_check_completed",
            total_keys=len(health_results),
            healthy=healthy_count,
            unhealthy=len(health_results) - healthy_count,
        )
        
        return {
            "message": "Health check completed",
            "total_keys": len(health_results),
            "healthy_keys": healthy_count,
            "unhealthy_keys": len(health_results) - healthy_count,
            "results": health_results,
        }
        
    except Exception as e:
        logger.error(
            "tavily_health_check_api_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger health check: {str(e)}"
        )


@router.get("/config")
async def get_tavily_config(
    current_user: User = Depends(current_active_user)
):
    """
    获取 Tavily 配置信息
    
    返回配额追踪设置和 Key 数量（不返回实际 Keys）
    
    权限：需要登录
    """
    api_keys = settings.get_tavily_api_keys
    
    return {
        "total_keys": len(api_keys),
        "quota_tracking_enabled": settings.TAVILY_QUOTA_TRACKING_ENABLED,
        "quota_source": "tavily_api",  # 配额来源：Tavily API
        "keys_configured": len(api_keys) > 0,
        "note": "Quota information is fetched from Tavily API /usage endpoint",
    }


@router.post("/refresh-quota")
async def refresh_quota(
    current_user: User = Depends(current_active_user)
):
    """
    刷新所有 Keys 的配额信息（强制重新获取）
    
    权限：需要登录
    """
    try:
        key_manager = _get_key_manager()
        
        # 强制刷新所有 Keys 的配额信息
        refresh_results = []
        for idx in range(len(key_manager.api_keys)):
            usage_info = await key_manager.get_usage_info(idx, force_refresh=True)
            
            if usage_info:
                refresh_results.append({
                    "key_index": idx,
                    "key_id": key_manager._get_key_id(idx),
                    "success": True,
                    "remaining": usage_info.total_remaining,
                })
            else:
                refresh_results.append({
                    "key_index": idx,
                    "key_id": key_manager._get_key_id(idx),
                    "success": False,
                    "error": "Failed to fetch usage info",
                })
        
        success_count = sum(1 for r in refresh_results if r["success"])
        
        logger.info(
            "tavily_quota_refreshed",
            total_keys=len(refresh_results),
            success=success_count,
            failed=len(refresh_results) - success_count,
        )
        
        return {
            "message": "Quota information refreshed",
            "total_keys": len(refresh_results),
            "success": success_count,
            "failed": len(refresh_results) - success_count,
            "results": refresh_results,
        }
        
    except Exception as e:
        logger.error(
            "tavily_refresh_quota_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh quota: {str(e)}"
        )

