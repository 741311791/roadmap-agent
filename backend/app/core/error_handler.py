"""
统一错误处理器（已废弃 - DEPRECATED）

⚠️ 此模块已废弃，请使用 SideEffectCoordinator 替代。

废弃原因：
- 职责重叠：与 SideEffectCoordinator、handlers/base.py 重复
- 未被使用：代码库中无实际调用
- 维护困难：多处状态更新导致不一致

新架构：
- 副作用统一由 SideEffectCoordinator 管理
- Handler 只负责保存业务数据
- Executor 调用协调器处理所有副作用

保留原因：
- 作为历史参考
- 待确认无依赖后删除
"""
import time
import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, Dict, Optional

from app.services.shared.notification_service import notification_service
from app.services.shared.execution_logger import execution_logger, LogCategory
from app.crud.crud_task import get_task_crud
from app.db.session import async_session_maker

logger = structlog.get_logger()


class WorkflowErrorHandler:
    """
    工作流错误处理器
    
    职责：
    1. 统一处理工作流节点执行中的错误
    2. 自动记录错误日志
    3. 发布失败通知
    4. 更新任务状态
    5. 清理资源
    
    使用方式：
        async with error_handler.handle_node_execution("intent_analysis", task_id) as ctx:
            # 执行节点逻辑
            result = await agent.execute(...)
            ctx["result"] = result
            
        # 如果执行成功，ctx["result"] 包含结果
        return ctx["result"]
    """
    
    def __init__(self):
        """初始化错误处理器"""
        pass
    
    @asynccontextmanager
    async def handle_node_execution(
        self,
        node_name: str,
        task_id: str,
        step_display_name: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        处理节点执行的错误
        
        这是一个异步上下文管理器，自动处理节点执行中的异常。
        使用 `ctx["result"]` 来存储成功执行的结果。
        
        Args:
            node_name: 节点名称（如 "intent_analysis"）
            task_id: 追踪ID
            step_display_name: 步骤显示名称（用于日志和通知，默认使用 node_name）
            
        Yields:
            context: 上下文字典，用于存储执行结果和中间数据
            
        Raises:
            Exception: 重新抛出原始异常（在记录和通知后）
        
        Example:
            async with error_handler.handle_node_execution("intent_analysis", task_id) as ctx:
                agent = self.agent_factory.create_intent_analyzer()
                result = await agent.execute(request)
                ctx["result"] = {
                    "intent_analysis": result,
                    "roadmap_id": roadmap_id,
                }
            
            return ctx["result"]
        """
        start_time = time.time()
        context: Dict[str, Any] = {}
        display_name = step_display_name or node_name
        
        try:
            yield context
            
            # 如果执行成功，记录调试信息
            duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                "node_execution_succeeded",
                node=node_name,
                task_id=task_id,
                duration_ms=duration_ms,
                has_result="result" in context,
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 1. 记录错误日志
            logger.error(
                "workflow_step_failed",
                step=node_name,
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            
            # 2. 记录执行日志
            await execution_logger.error(
                task_id=task_id,
                category=LogCategory.WORKFLOW,
                message=f"{display_name}失败: {str(e)[:100]}",
                step=node_name,
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": duration_ms,
                },
            )
            
            # 3. 发布失败通知（传递异常对象以获取完整堆栈）
            await notification_service.publish_failed(
                task_id=task_id,
                error=str(e),
                step=node_name,
                exception=e,
            )
            
            # 4. 更新任务状态为失败
            await self._update_task_status_failed(
                task_id=task_id,
                error=e,
                node_name=node_name,
            )
            
            # 5. 重新抛出异常（让调用方决定如何处理）
            raise
    
    async def _update_task_status_failed(
        self,
        task_id: str,
        error: Exception,
        node_name: str,
    ) -> None:
        """
        更新任务状态为失败
        
        Args:
            task_id: 追踪ID
            error: 异常对象
            node_name: 节点名称
        """
        try:
            async with async_session_maker.begin() as session:
                task_crud = get_task_crud()
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status="failed",
                    current_step=None,  # 不更新current_step，保留失败时的阶段信息
                    error_message=str(error)[:500],
                )
                # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
                
                logger.debug(
                    "task_status_updated_failed",
                    task_id=task_id,
                    node=node_name,
                )
        except Exception as db_error:
            # 如果更新数据库失败，记录日志但不影响主异常
            logger.error(
                "failed_to_update_task_status",
                task_id=task_id,
                node=node_name,
                error=str(db_error),
            )


# 全局单例
error_handler = WorkflowErrorHandler()
