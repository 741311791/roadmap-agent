"""
Tavily API Key 分配器服务

职责：
- 在内容生成任务开始前，一次性从数据库获取所有可用的 API Keys
- 按配额优先策略为每个 Concept 预分配 API Key
- 支持 Key 复用（当 Keys 不足时）
- 提供详细的分配日志
"""
from typing import Optional
import structlog

from app.db.repositories.tavily_key_repo import TavilyKeyRepository
from app.db.celery_session import celery_safe_session_with_retry

logger = structlog.get_logger(__name__)


async def allocate_keys_for_concepts(
    concept_ids: list[str],
    min_quota: int = 4,
) -> dict[str, Optional[str]]:
    """
    为 Concept 列表预分配 Tavily API Keys
    
    分配策略：
    1. 从数据库获取所有 remaining_quota >= min_quota 的 Keys
    2. 按 remaining_quota 降序排序（配额最多的优先）
    3. 使用轮询方式分配（确保 Keys 均匀使用）
    4. 如果 Keys 不足，允许多个 Concepts 复用同一个 Key
    
    Args:
        concept_ids: 需要分配 Key 的 Concept ID 列表
        min_quota: 最小剩余配额要求（默认 4 次）
        
    Returns:
        映射字典：concept_id -> api_key（如果某个 Concept 分配失败则为 None）
        
    示例：
        {
            "concept-1": "tvly-abc123...",
            "concept-2": "tvly-def456...",
            "concept-3": None,  # 没有可用 Key
        }
    """
    logger.info(
        "tavily_key_allocation_start",
        total_concepts=len(concept_ids),
        min_quota=min_quota,
    )
    
    # 初始化分配结果
    allocation: dict[str, Optional[str]] = {cid: None for cid in concept_ids}
    
    try:
        # 一次性从数据库获取所有可用 Keys
        async with celery_safe_session_with_retry() as session:
            repo = TavilyKeyRepository(session)
            all_keys = await repo.get_all_keys()
        
        # 过滤出满足最小配额要求的 Keys
        available_keys = [
            key for key in all_keys 
            if key.remaining_quota >= min_quota
        ]
        
        if not available_keys:
            logger.warning(
                "tavily_no_available_keys",
                total_keys=len(all_keys),
                min_quota=min_quota,
                message=f"数据库中没有剩余配额 >= {min_quota} 的 Tavily API Key"
            )
            return allocation
        
        # 已经按 remaining_quota 降序排序（由 get_all_keys 保证）
        logger.info(
            "tavily_keys_fetched",
            total_keys=len(all_keys),
            available_keys=len(available_keys),
            top_key_quota=available_keys[0].remaining_quota if available_keys else 0,
        )
        
        # 轮询分配策略（Round Robin）
        # 优点：确保每个 Key 被均匀使用，避免某个 Key 快速耗尽
        for idx, concept_id in enumerate(concept_ids):
            key_idx = idx % len(available_keys)
            selected_key = available_keys[key_idx]
            allocation[concept_id] = selected_key.api_key
            
            logger.debug(
                "tavily_key_allocated",
                concept_id=concept_id,
                key_prefix=selected_key.api_key[:10] + "...",
                remaining_quota=selected_key.remaining_quota,
            )
        
        # 统计分配结果
        keys_used = set(allocation.values()) - {None}
        concepts_with_keys = sum(1 for k in allocation.values() if k is not None)
        concepts_without_keys = len(concept_ids) - concepts_with_keys
        
        logger.info(
            "tavily_key_allocation_complete",
            total_concepts=len(concept_ids),
            concepts_with_keys=concepts_with_keys,
            concepts_without_keys=concepts_without_keys,
            unique_keys_used=len(keys_used),
            allocation_rate=f"{concepts_with_keys / len(concept_ids) * 100:.1f}%",
        )
        
        return allocation
        
    except Exception as e:
        logger.error(
            "tavily_key_allocation_failed",
            error=str(e),
            error_type=type(e).__name__,
            total_concepts=len(concept_ids),
        )
        # 返回全部为 None 的分配结果（允许任务继续，回退到 DuckDuckGo）
        return allocation


async def get_allocation_stats(allocation: dict[str, Optional[str]]) -> dict:
    """
    获取分配统计信息（用于日志和监控）
    
    Args:
        allocation: Key 分配映射
        
    Returns:
        统计信息字典
    """
    total = len(allocation)
    with_keys = sum(1 for k in allocation.values() if k is not None)
    without_keys = total - with_keys
    unique_keys = len(set(allocation.values()) - {None})
    
    return {
        "total_concepts": total,
        "concepts_with_keys": with_keys,
        "concepts_without_keys": without_keys,
        "unique_keys_used": unique_keys,
        "allocation_rate": f"{with_keys / total * 100:.1f}%" if total > 0 else "0%",
    }

