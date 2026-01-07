"""
Tavily API Key管理服务

负责处理:
- Tavily API Key的CRUD操作
- 配额管理
- 批量操作
"""
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.models.database import TavilyAPIKey, beijing_now

logger = structlog.get_logger()


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
    
    async def add_key(
        self,
        session: AsyncSession,
        api_key: str,
        plan_limit: int,
    ) -> TavilyAPIKey:
        """
        添加Tavily API Key
        
        Args:
            session: 数据库会话
            api_key: API密钥
            plan_limit: 计划配额
            
        Returns:
            新创建的API Key记录
            
        Raises:
            ValueError: Key已存在
        """
        # 检查是否已存在
        result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
        )
        if result.scalars().first():
            raise ValueError("API Key already exists")
        
        # 创建新记录
        new_key = TavilyAPIKey(
            api_key=api_key,
            plan_limit=plan_limit,
            remaining_quota=plan_limit,
        )
        
        session.add(new_key)
        await session.flush()
        await session.refresh(new_key)
        
        logger.info(
            "tavily_key_added",
            key_prefix=api_key[:10] + "...",
            plan_limit=plan_limit,
        )
        
        return new_key
    
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
    
    async def update_key(
        self,
        session: AsyncSession,
        api_key: str,
        remaining_quota: Optional[int] = None,
        plan_limit: Optional[int] = None,
    ) -> TavilyAPIKey:
        """
        更新Tavily API Key配额
        
        Args:
            session: 数据库会话
            api_key: API密钥
            remaining_quota: 新的剩余配额（可选）
            plan_limit: 新的计划配额（可选）
            
        Returns:
            更新后的API Key记录
            
        Raises:
            ValueError: Key不存在
        """
        result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
        )
        key_record = result.scalars().first()
        
        if not key_record:
            raise ValueError("API Key not found")
        
        # 更新字段
        if remaining_quota is not None:
            key_record.remaining_quota = remaining_quota
        if plan_limit is not None:
            key_record.plan_limit = plan_limit
        
        key_record.updated_at = beijing_now()
        
        session.add(key_record)
        await session.flush()
        await session.refresh(key_record)
        
        logger.info(
            "tavily_key_updated",
            key_prefix=api_key[:10] + "...",
            remaining_quota=remaining_quota,
            plan_limit=plan_limit,
        )
        
        return key_record
    
    async def rotate_key(
        self,
        session: AsyncSession,
        api_key: str,
    ) -> Dict:
        """
        轮转Tavily API Key（重置配额到plan_limit）
        
        Args:
            session: 数据库会话
            api_key: API密钥
            
        Returns:
            轮转结果
            
        Raises:
            ValueError: Key不存在
        """
        result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
        )
        key_record = result.scalars().first()
        
        if not key_record:
            raise ValueError("API Key not found")
        
        # 重置配额
        key_record.remaining_quota = key_record.plan_limit
        key_record.updated_at = beijing_now()
        
        session.add(key_record)
        await session.flush()
        
        logger.info(
            "tavily_key_rotated",
            key_prefix=api_key[:10] + "...",
            new_quota=key_record.remaining_quota,
        )
        
        return {
            "success": True,
            "api_key": f"{api_key[:10]}...{api_key[-4:]}",
            "new_quota": key_record.remaining_quota,
            "plan_limit": key_record.plan_limit,
        }
    
    async def manual_refresh_quota(
        self,
        session: AsyncSession,
        api_key: str,
        new_quota: int,
    ) -> Dict:
        """
        手动刷新Tavily API配额
        
        Args:
            session: 数据库会话
            api_key: API密钥
            new_quota: 新配额值
            
        Returns:
            刷新结果
            
        Raises:
            ValueError: Key不存在
        """
        result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
        )
        key_record = result.scalars().first()
        
        if not key_record:
            raise ValueError("API Key not found")
        
        old_quota = key_record.remaining_quota
        key_record.remaining_quota = new_quota
        key_record.updated_at = beijing_now()
        
        session.add(key_record)
        await session.flush()
        
        logger.info(
            "tavily_quota_manually_refreshed",
            key_prefix=api_key[:10] + "...",
            old_quota=old_quota,
            new_quota=new_quota,
        )
        
        return {
            "success": True,
            "api_key": f"{api_key[:10]}...{api_key[-4:]}",
            "old_quota": old_quota,
            "new_quota": new_quota,
            "plan_limit": key_record.plan_limit,
        }
    
    async def delete_key(
        self,
        session: AsyncSession,
        api_key: str,
    ) -> Dict:
        """
        删除Tavily API Key
        
        Args:
            session: 数据库会话
            api_key: API密钥
            
        Returns:
            删除结果
            
        Raises:
            ValueError: Key不存在
        """
        result = await session.execute(
            select(TavilyAPIKey).where(TavilyAPIKey.api_key == api_key)
        )
        key_record = result.scalars().first()
        
        if not key_record:
            raise ValueError("API Key not found")
        
        await session.delete(key_record)
        await session.flush()
        
        logger.info(
            "tavily_key_deleted",
            key_prefix=api_key[:10] + "...",
        )
        
        return {
            "success": True,
            "message": "API Key deleted successfully",
        }

