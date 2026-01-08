"""
工作流状态管理器（Redis版本）

负责管理 live_step 缓存（当前执行步骤），使用Redis存储以支持水平扩展。

性能优化：
- 迁移到Redis：支持多实例共享状态
- 自动过期：TTL设置为1小时
- 高性能：操作延迟<5ms
"""
import structlog
from app.db.redis_client import redis_client

logger = structlog.get_logger()


class StateManager:
    """
    状态管理器（Redis版本）
    
    使用Redis存储工作流状态，替代内存dict。
    
    优势：
    1. 支持水平扩展：多API实例共享状态
    2. 持久化：重启不丢失（有TTL保护）
    3. 自动过期：1小时后自动清理
    4. 高性能：Redis操作延迟<5ms
    
    使用场景：
    - WebSocket 实时推送当前步骤
    - 前端轮询时快速返回当前状态
    - 多实例部署时状态同步
    """
    
    LIVE_STEP_PREFIX = "workflow:live_step:"
    LIVE_STEP_TTL = 3600  # 1小时（秒）
    
    async def set_live_step(self, task_id: str, step: str) -> None:
        """
        设置任务当前步骤（Redis）
        
        Args:
            task_id: 任务追踪ID
            step: 当前步骤名称（如 "intent_analysis", "curriculum_design"）
        """
        await redis_client.connect()
        key = f"{self.LIVE_STEP_PREFIX}{task_id}"
        
        await redis_client._client.setex(
            key,
            self.LIVE_STEP_TTL,
            step,
        )
        
        logger.debug(
            "live_step_set",
            task_id=task_id,
            step=step,
            storage="redis",
        )
    
    async def get_live_step(self, task_id: str) -> str | None:
        """
        获取任务当前步骤
        
        Args:
            task_id: 任务追踪ID
            
        Returns:
            步骤名称或None
        """
        await redis_client.connect()
        key = f"{self.LIVE_STEP_PREFIX}{task_id}"
        
        step = await redis_client._client.get(key)
        
        if step:
            logger.debug(
                "live_step_retrieved",
                task_id=task_id,
                step=step,
                storage="redis",
            )
        
        return step
    
    async def clear_live_step(self, task_id: str) -> None:
        """
        清除任务步骤缓存
        
        在工作流完成或失败时调用。
        
        Args:
            task_id: 任务追踪ID
        """
        await redis_client.connect()
        key = f"{self.LIVE_STEP_PREFIX}{task_id}"
        
        await redis_client._client.delete(key)
        
        logger.debug(
            "live_step_cleared",
            task_id=task_id,
            storage="redis",
        )
    
    async def get_all_live_steps(self) -> dict[str, str]:
        """
        获取所有活跃的执行步骤
        
        用于监控和调试。
        
        Returns:
            {task_id: current_step} 的字典
        """
        await redis_client.connect()
        pattern = f"{self.LIVE_STEP_PREFIX}*"
        
        # 使用scan迭代器获取所有匹配的key
        result = {}
        async for key in redis_client._client.scan_iter(pattern):
            # 提取task_id
            task_id = key.replace(self.LIVE_STEP_PREFIX, "")
            # 获取步骤值
            step = await redis_client._client.get(key)
            if step:
                result[task_id] = step
        
        return result
    
    async def clear_all(self) -> None:
        """
        清除所有缓存
        
        用于测试或重启场景。
        
        ⚠️ 警告：此操作会删除所有工作流状态，仅用于测试或紧急情况。
        """
        await redis_client.connect()
        pattern = f"{self.LIVE_STEP_PREFIX}*"
        
        # 使用scan迭代器获取所有匹配的key
        keys_to_delete = []
        async for key in redis_client._client.scan_iter(pattern):
            keys_to_delete.append(key)
        
        # 批量删除
        if keys_to_delete:
            await redis_client._client.delete(*keys_to_delete)
            logger.info(
                "all_live_steps_cleared",
                count=len(keys_to_delete),
                storage="redis",
            )
        else:
            logger.info("no_live_steps_to_clear", storage="redis")

