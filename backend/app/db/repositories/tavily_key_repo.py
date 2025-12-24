"""
Tavily API Key Repository

职责：
- 从数据库读取 Tavily API Key 配额信息
- 选择剩余配额最多的 Key
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.repositories.base import BaseRepository
from app.models.database import TavilyAPIKey

logger = structlog.get_logger(__name__)


class TavilyKeyRepository(BaseRepository[TavilyAPIKey]):
    """
    Tavily API Key 仓储
    
    提供对 tavily_api_keys 表的数据访问方法。
    """
    
    def __init__(self, session: AsyncSession):
        """
        初始化 Repository
        
        Args:
            session: 异步数据库会话
        """
        super().__init__(session, TavilyAPIKey)
    
    async def get_best_key(self) -> Optional[TavilyAPIKey]:
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
            result = await self.session.execute(stmt)
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
    
    async def get_all_keys(self) -> List[TavilyAPIKey]:
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
            result = await self.session.execute(stmt)
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
    
    async def get_by_key(self, api_key: str) -> Optional[TavilyAPIKey]:
        """
        根据 API Key 获取记录
        
        Args:
            api_key: Tavily API Key
            
        Returns:
            TavilyAPIKey 对象，如果不存在则返回 None
        """
        try:
            stmt = select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(
                "tavily_get_by_key_failed",
                key_prefix=api_key[:10] + "..." if api_key else "None",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

