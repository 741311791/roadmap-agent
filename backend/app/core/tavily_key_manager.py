"""
Tavily API Key Manager（特殊模块）

职责：
- 从数据库读取 Tavily API Key 配额信息
- 选择剩余配额最多的 Key
- 管理分布式锁和配额轮询

特殊说明：
本模块保留原Repository模式，因为包含复杂的业务逻辑：
- 分布式锁机制
- 配额轮询和健康检查
- Redis操作
这些逻辑不适合拆分到纯CRUD层。
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import TavilyAPIKey

logger = structlog.get_logger(__name__)


class TavilyKeyManager(BaseCRUD[TavilyAPIKey, dict, dict]):
    """
    Tavily API Key 管理器（特殊模块）
    
    提供对 tavily_api_keys 表的数据访问和配额管理方法。
    保留原Repository接口以保持向后兼容。
    """
    
    # 注意：保持原Repository接口以便于迁移
    
    async def get_best_key(self, session: AsyncSession) -> Optional[TavilyAPIKey]:
        """
        获取剩余配额最多的 API Key
        
        选择策略：
        - 只考虑 remaining_quota > 0 的 Key
        - 按 remaining_quota 降序排序
        - 返回第一条记录
        
        Returns:
            TavilyAPIKey 对象，如果没有可用 Key 则返回 None
        """
        try:
            stmt = (
                select(TavilyAPIKey)
                .where(TavilyAPIKey.remaining_quota > 0)
                .order_by(TavilyAPIKey.remaining_quota.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            key_record = result.scalar_one_or_none()
            
            if key_record:
                logger.info(
                    "tavily_best_key_selected",
                    key_prefix=key_record.api_key[:10] + "...",
                    remaining_quota=key_record.remaining_quota,
                    plan_limit=key_record.plan_limit,
                )
            else:
                logger.warning(
                    "tavily_no_available_key",
                    message="数据库中没有可用的 Tavily API Key"
                )
            
            return key_record
            
        except Exception as e:
            logger.error(
                "tavily_get_best_key_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def get_all_keys(self, session: AsyncSession) -> List[TavilyAPIKey]:
        """
        获取所有 API Keys（按剩余配额降序排序）
        
        Returns:
            TavilyAPIKey 对象列表
        """
        try:
            stmt = (
                select(TavilyAPIKey)
                .order_by(TavilyAPIKey.remaining_quota.desc())
            )
            result = await session.execute(stmt)
            keys = result.scalars().all()
            
            logger.debug(
                "tavily_all_keys_fetched",
                total_keys=len(keys),
            )
            
            return list(keys)
            
        except Exception as e:
            logger.error(
                "tavily_get_all_keys_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def get_by_key(self, session: AsyncSession, api_key: str) -> Optional[TavilyAPIKey]:
        """
        根据 API Key 获取记录
        
        Args:
            api_key: Tavily API Key
            
        Returns:
            TavilyAPIKey 对象，如果不存在则返回 None
        """
        try:
            stmt = select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(
                "tavily_get_by_key_failed",
                key_prefix=api_key[:10] + "..." if api_key else "None",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

