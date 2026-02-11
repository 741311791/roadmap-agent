"""
Tavily API Key管理服务

负责处理:
- Tavily API Key的批量添加
- Tavily API Key的批量更新（通过官方API查询配额）
- Tavily API Key的批量删除
- Tavily API Key的列表查询
"""
from typing import List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio
import httpx
import structlog

from app.models.database import TavilyAPIKey, beijing_now

logger = structlog.get_logger()

# Tavily API 配置
TAVILY_API_BASE_URL = "https://api.tavily.com"
TAVILY_USAGE_ENDPOINT = f"{TAVILY_API_BASE_URL}/usage"

# 并发控制配置
MAX_CONCURRENT_API_CALLS = 10  # 最大并发API调用数


class TavilyKeyService:
    """Tavily API Key业务逻辑"""
    
    async def get_all_keys(self, session: AsyncSession) -> List[TavilyAPIKey]:
        """
        获取所有Tavily API Keys
        
        Args:
            session: 数据库会话
            
        Returns:
            API Key列表
        """
        result = await session.execute(select(TavilyAPIKey))
        return list(result.scalars().all())
    
    async def batch_add_keys(
        self,
        session: AsyncSession,
        keys: List[Dict[str, int]],
    ) -> Tuple[int, List[Dict]]:
        """
        批量添加Tavily API Keys
        
        采用"一次读取，批量插入"策略。
        
        Args:
            session: 数据库会话
            keys: Key列表，每个元素包含 api_key 和 plan_limit
            
        Returns:
            (成功数量, 错误列表)
        """
        errors = []
        new_keys_to_add = []
        
        # Step 1: 一次性读取所有请求的Key，检查已存在的
        requested_api_keys = [k["api_key"] for k in keys]
        existing_result = await session.execute(
            select(TavilyAPIKey.api_key).where(TavilyAPIKey.api_key.in_(requested_api_keys))
        )
        existing_keys_set = set(existing_result.scalars().all())
        
        # Step 2: 区分已存在和新增的Key
        for key_data in keys:
            api_key = key_data["api_key"]
            plan_limit = key_data["plan_limit"]
            
            if api_key in existing_keys_set:
                errors.append({
                    "api_key": f"{api_key[:10]}...",
                    "error": "API Key already exists"
                })
            else:
                new_key = TavilyAPIKey(
                    api_key=api_key,
                    plan_limit=plan_limit,
                    remaining_quota=plan_limit,
                )
                new_keys_to_add.append(new_key)
        
        # Step 3: 一次性批量插入
        success_count = 0
        if new_keys_to_add:
            try:
                session.add_all(new_keys_to_add)
                await session.flush()
                success_count = len(new_keys_to_add)
                
                logger.info(
                    "tavily_keys_batch_added",
                    inserted_count=success_count,
                )
            except Exception as e:
                # 批量插入失败，所有Key都标记为失败
                for key_obj in new_keys_to_add:
                    errors.append({
                        "api_key": f"{key_obj.api_key[:10]}...",
                        "error": f"Bulk insert failed: {str(e)}"
                    })
                success_count = 0
                logger.error("tavily_keys_batch_add_failed", error=str(e))
        
        return success_count, errors
    
    async def _fetch_tavily_quota(self, api_key: str) -> Dict:
        """
        从Tavily官方API查询配额信息
        
        Args:
            api_key: Tavily API密钥
            
        Returns:
            配额信息字典，包含 usage 和 limit
            
        Raises:
            httpx.HTTPError: API请求失败
            Exception: 其他错误
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                TAVILY_USAGE_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            # 检查响应状态
            if response.status_code == 401:
                raise ValueError("Unauthorized: missing or invalid API key")
            
            response.raise_for_status()
            data = response.json()
            
            # 提取配额信息
            if "key" not in data:
                raise ValueError(f"Invalid response format: missing 'key' field")
            
            account_info = data["account"]
            
            # 获取 usage 和 limit，确保不为 None
            usage = account_info.get("plan_usage")
            limit = account_info.get("plan_limit")
            
            if usage is None or limit is None:
                raise ValueError(
                    f"Invalid quota data: usage={usage}, limit={limit}"
                )
            
            return {
                "usage": usage,
                "limit": limit,
            }
    
    async def _fetch_quota_for_key(
        self,
        api_key: str,
        semaphore: asyncio.Semaphore
    ) -> Tuple[str, Dict | None, str | None]:
        """
        为单个Key查询配额（带并发控制）
        
        Args:
            api_key: API密钥
            semaphore: 并发控制信号量
            
        Returns:
            (api_key, quota_info或None, error或None)
        """
        async with semaphore:
            try:
                quota_info = await self._fetch_tavily_quota(api_key)
                return api_key, quota_info, None
            except Exception as e:
                return api_key, None, str(e)
    
    async def batch_update_keys(
        self,
        session: AsyncSession,
        api_keys: List[str],
    ) -> Tuple[int, List[Dict]]:
        """
        批量更新Tavily API Keys配额（通过官方API查询）
        
        优化策略：
        1. 一次性读取所有待更新的Keys（避免N+1查询）
        2. 并发调用Tavily API查询配额（控制并发数）
        3. 批量更新数据库（使用bulk update）
        4. 如果遇到Unauthorized错误，自动删除无效的API Key并触发Redis缓存更新
        
        Args:
            session: 数据库会话
            api_keys: 待更新的API Key列表
            
        Returns:
            (成功数量, 错误列表)
        """
        errors = []
        updates_to_apply = []
        invalid_keys_to_delete = []  # 需要删除的无效Keys
        
        # Step 1: 一次性从数据库读取所有Keys（避免N+1）
        existing_result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key.in_(api_keys))
        )
        existing_keys_dict = {key.api_key: key for key in existing_result.scalars().all()}
        
        # 检查不存在的Keys
        for api_key in api_keys:
            if api_key not in existing_keys_dict:
                errors.append({
                    "api_key": f"{api_key[:10]}...",
                    "error": "API Key not found in database"
                })
        
        # 过滤出存在的Keys
        valid_api_keys = [k for k in api_keys if k in existing_keys_dict]
        
        if not valid_api_keys:
            return 0, errors
        
        # Step 2: 并发调用Tavily API查询配额（避免串行调用）
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_API_CALLS)
        tasks = [
            self._fetch_quota_for_key(api_key, semaphore)
            for api_key in valid_api_keys
        ]
        
        # 并发执行所有API调用
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 3: 处理API调用结果，准备批量更新数据
        current_time = beijing_now()
        
        for result in results:
            # 处理异常结果
            if isinstance(result, Exception):
                logger.error(
                    "tavily_api_call_exception",
                    error=str(result),
                    exc_info=True
                )
                errors.append({
                    "api_key": "unknown",
                    "error": f"API call exception: {str(result)}"
                })
                continue
            
            api_key, quota_info, error = result
            
            if error:
                # 检查是否为Unauthorized错误（无效的API Key）
                if "Unauthorized" in error or "invalid API key" in error:
                    # 标记为需要删除
                    invalid_keys_to_delete.append(api_key)
                    errors.append({
                        "api_key": f"{api_key[:10]}...",
                        "error": error,
                        "action": "deleted (invalid key)"
                    })
                    logger.warning(
                        "tavily_invalid_key_detected",
                        key_prefix=api_key[:10] + "...",
                        error=error,
                        action="will_be_deleted",
                    )
                else:
                    # 其他类型的API调用失败
                    errors.append({
                        "api_key": f"{api_key[:10]}...",
                        "error": error
                    })
                    logger.warning(
                        "tavily_quota_fetch_failed",
                        key_prefix=api_key[:10] + "...",
                        error=error,
                    )
                continue
            
            if quota_info:
                # API调用成功，准备更新数据
                try:
                    usage = quota_info.get("usage", 0)
                    limit = quota_info.get("limit", 0)
                    
                    # 确保 usage 和 limit 不为 None
                    if usage is None:
                        usage = 0
                    if limit is None:
                        limit = 0
                    
                    remaining_quota = limit - usage
                    
                    # 添加到批量更新列表
                    updates_to_apply.append({
                        "api_key": api_key,
                        "remaining_quota": remaining_quota,
                        "plan_limit": limit,
                    })
                    
                    logger.info(
                        "tavily_key_quota_fetched",
                        key_prefix=api_key[:10] + "...",
                        usage=usage,
                        limit=limit,
                        remaining=remaining_quota,
                    )
                    
                except Exception as e:
                    errors.append({
                        "api_key": f"{api_key[:10]}...",
                        "error": f"Data processing failed: {str(e)}"
                    })
                    logger.error(
                        "tavily_quota_processing_failed",
                        key_prefix=api_key[:10] + "...",
                        error=str(e),
                        exc_info=True,
                    )
        
        # Step 4: 删除无效的API Keys（如果有）
        deleted_count = 0
        should_refresh_cache = False
        
        if invalid_keys_to_delete:
            try:
                from sqlalchemy import delete as sql_delete
                
                stmt = sql_delete(TavilyAPIKey).where(
                    TavilyAPIKey.api_key.in_(invalid_keys_to_delete)
                )
                result = await session.execute(stmt)
                await session.flush()
                
                deleted_count = result.rowcount
                should_refresh_cache = True  # 标记需要刷新缓存
                
                logger.info(
                    "tavily_invalid_keys_deleted",
                    deleted_count=deleted_count,
                    keys=[k[:10] + "..." for k in invalid_keys_to_delete],
                )
                
            except Exception as e:
                logger.error(
                    "tavily_invalid_keys_deletion_failed",
                    error=str(e),
                    exc_info=True,
                )
                errors.append({
                    "api_key": "INVALID_KEYS",
                    "error": f"Failed to delete invalid keys: {str(e)}"
                })
        
        # Step 5: 批量更新数据库（避免N次更新）
        success_count = 0
        if updates_to_apply:
            try:
                # 使用bulk update一次性更新所有记录
                for update_data in updates_to_apply:
                    stmt = (
                        update(TavilyAPIKey)
                        .where(TavilyAPIKey.api_key == update_data["api_key"])
                        .values(
                            remaining_quota=update_data["remaining_quota"],
                            plan_limit=update_data["plan_limit"],
                            updated_at=current_time,
                        )
                    )
                    await session.execute(stmt)
                
                await session.flush()
                success_count = len(updates_to_apply)
                should_refresh_cache = True  # 标记需要刷新缓存
                
                logger.info(
                    "tavily_keys_batch_updated",
                    updated_count=success_count,
                    failed_count=len(errors),
                    deleted_count=deleted_count,
                )
                
            except Exception as e:
                # 批量更新失败
                logger.error(
                    "tavily_keys_batch_update_failed",
                    error=str(e),
                    exc_info=True,
                )
                errors.append({
                    "api_key": "ALL",
                    "error": f"Batch update failed: {str(e)}"
                })
                success_count = 0
        
        # Step 6: 触发Redis缓存刷新（如果有更新或删除操作）
        if should_refresh_cache:
            try:
                from app.core.tavily_key_cache import get_tavily_key_cache
                
                key_cache = get_tavily_key_cache()
                refreshed_count = await key_cache.refresh()
                
                logger.info(
                    "tavily_cache_refreshed_after_update",
                    refreshed_keys=refreshed_count,
                    trigger="batch_update_with_changes",
                )
                
            except Exception as e:
                logger.error(
                    "tavily_cache_refresh_failed",
                    error=str(e),
                    exc_info=True,
                )
                # 缓存刷新失败不影响主流程，只记录警告
                errors.append({
                    "api_key": "CACHE_REFRESH",
                    "error": f"Redis cache refresh failed: {str(e)}",
                    "severity": "warning"
                })
        
        return success_count, errors
    
    async def batch_delete_keys(
        self,
        session: AsyncSession,
        api_keys: List[str],
    ) -> Tuple[int, List[Dict]]:
        """
        批量删除Tavily API Keys
        
        优化策略：
        1. 一次性查询所有待删除的Keys（避免N+1查询）
        2. 使用SQL DELETE语句一次性删除（避免N次delete调用）
        
        Args:
            session: 数据库会话
            api_keys: 待删除的API Key列表
            
        Returns:
            (成功数量, 错误列表)
        """
        from sqlalchemy import delete as sql_delete
        
        errors = []
        success_count = 0
        
        # Step 1: 一次性查询所有存在的Keys（避免N+1查询）
        existing_result = await session.execute(
            select(TavilyAPIKey.api_key).where(TavilyAPIKey.api_key.in_(api_keys))
        )
        existing_keys_set = set(existing_result.scalars().all())
        
        # Step 2: 检查不存在的Keys
        for api_key in api_keys:
            if api_key not in existing_keys_set:
                errors.append({
                    "api_key": f"{api_key[:10]}...",
                    "error": "API Key not found"
                })
        
        # 过滤出存在的Keys
        valid_keys_to_delete = [k for k in api_keys if k in existing_keys_set]
        
        # Step 3: 使用SQL DELETE一次性删除所有Keys（避免N次delete）
        if valid_keys_to_delete:
            try:
                stmt = sql_delete(TavilyAPIKey).where(
                    TavilyAPIKey.api_key.in_(valid_keys_to_delete)
                )
                result = await session.execute(stmt)
                await session.flush()
                
                success_count = result.rowcount
                
                logger.info(
                    "tavily_keys_batch_deleted",
                    deleted_count=success_count,
                )
            except Exception as e:
                # 批量删除失败
                for api_key in valid_keys_to_delete:
                    errors.append({
                        "api_key": f"{api_key[:10]}...",
                        "error": f"Bulk delete failed: {str(e)}"
                    })
                success_count = 0
                logger.error(
                    "tavily_keys_batch_delete_failed",
                    error=str(e),
                    exc_info=True,
                )
        
        return success_count, errors

