"""
工作流状态管理器

负责管理 live_step 缓存（内存中的当前执行步骤）
"""
import structlog

logger = structlog.get_logger()


class StateManager:
    """
    状态管理器
    
    维护内存中的 live_step 缓存，用于实时查询当前执行步骤。
    
    注意：这是内存缓存，不持久化到数据库。主要用于：
    1. WebSocket 实时推送当前步骤
    2. 前端轮询时快速返回当前状态
    3. 避免频繁查询数据库
    """
    
    def __init__(self):
        self._live_step_cache: dict[str, str] = {}  # task_id -> current_step
    
    def set_live_step(self, task_id: str, step: str) -> None:
        """
        设置当前执行步骤
        
        Args:
            task_id: 任务追踪ID
            step: 当前步骤名称（如 "intent_analysis", "curriculum_design"）
        """
        self._live_step_cache[task_id] = step
        logger.debug(
            "live_step_set",
            task_id=task_id,
            step=step,
        )
    
    def get_live_step(self, task_id: str) -> str | None:
        """
        获取当前执行步骤
        
        Args:
            task_id: 任务追踪ID
            
        Returns:
            当前步骤名称，如果不存在则返回 None
        """
        step = self._live_step_cache.get(task_id)
        logger.debug(
            "live_step_get",
            task_id=task_id,
            step=step,
        )
        return step
    
    def clear_live_step(self, task_id: str) -> None:
        """
        清除执行步骤缓存
        
        在工作流完成或失败时调用。
        
        Args:
            task_id: 任务追踪ID
        """
        if task_id in self._live_step_cache:
            del self._live_step_cache[task_id]
            logger.debug(
                "live_step_cleared",
                task_id=task_id,
            )
    
    def get_all_live_steps(self) -> dict[str, str]:
        """
        获取所有活跃的执行步骤
        
        用于监控和调试。
        
        Returns:
            {task_id: current_step} 的字典
        """
        return dict(self._live_step_cache)
    
    def clear_all(self) -> None:
        """
        清除所有缓存
        
        用于测试或重启场景。
        """
        self._live_step_cache.clear()
        logger.info("all_live_steps_cleared")

