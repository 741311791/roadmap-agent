"""
副作用协调器（Side Effect Coordinator）

统一管理工作流执行过程中的所有副作用：
- Task 状态更新（PostgreSQL）
- WebSocket 通知发送（Redis Pub/Sub）
- live_step 缓存更新（Redis）
- 执行日志记录（PostgreSQL）

设计原则：
- 单一职责：所有副作用由此协调器统一管理
- 原子性：每个副作用操作独立，失败不影响其他
- 容错性：副作用失败不影响主流程
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager
from app.crud.crud_task import get_task_crud
from app.db.celery_session import get_celery_session

logger = structlog.get_logger()


def _safe_get(obj, key: str, default=None):
    """
    安全地从字典或Pydantic模型获取值
    
    Args:
        obj: 字典或Pydantic BaseModel实例
        key: 键名
        default: 默认值
        
    Returns:
        获取的值或默认值
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        # Pydantic 模型，使用 getattr
        return getattr(obj, key, default)


class SideEffectCoordinator:
    """
    副作用协调器
    
    职责：
    1. 统一管理所有副作用（状态、通知、缓存、日志）
    2. 确保副作用的一致性和完整性
    3. 提供统一的错误处理和重试机制
    
    使用示例：
        coordinator = SideEffectCoordinator(...)
        await coordinator.on_node_start(task_id, "intent_analysis")
        await coordinator.on_node_complete(task_id, "intent_analysis", output)
    """
    
    def __init__(
        self,
        notification_service: NotificationService,
        execution_logger: ExecutionLogger,
        state_manager: StateManager,
    ):
        """
        初始化协调器
        
        Args:
            notification_service: 通知服务
            execution_logger: 执行日志服务
            state_manager: 状态管理器（Redis）
        """
        self.notification_service = notification_service
        self.execution_logger = execution_logger
        self.state_manager = state_manager
        
        logger.info("side_effect_coordinator_initialized")
    
    async def on_node_start(
        self,
        task_id: str,
        node_name: str,
        roadmap_id: Optional[str] = None,
    ) -> None:
        """
        节点开始时的副作用处理
        
        执行：
        1. 更新 Task 状态为 processing
        2. 更新 live_step 缓存
        3. 发送 WebSocket 进度通知
        
        Args:
            task_id: 任务ID
            node_name: 节点名称
            roadmap_id: 路线图ID（可选）
        """
        logger.info(
            "coordinator_node_start",
            task_id=task_id,
            node_name=node_name,
            roadmap_id=roadmap_id,
        )
        
        # 1. 更新 Task 状态
        await self._update_task_status(
            task_id=task_id,
            status="processing",
            current_step=node_name,
            roadmap_id=roadmap_id,
        )
        
        # 2. 更新 live_step 缓存（Redis）
        await self._update_live_step(task_id, node_name)
        
        # 3. 发送 WebSocket 通知
        await self._send_progress_notification(
            task_id=task_id,
            step=node_name,
            status="processing",
        )
    
    async def on_node_complete(
        self,
        task_id: str,
        node_name: str,
        output: dict,
        duration_ms: int,
    ) -> None:
        """
        节点完成时的副作用处理
        
        执行：
        1. 更新 live_step 缓存
        2. 发送 WebSocket 完成通知
        3. 记录执行日志
        
        Args:
            task_id: 任务ID
            node_name: 节点名称
            output: 节点输出（可能是dict或Pydantic模型）
            duration_ms: 执行时长（毫秒）
        """
        roadmap_id = _safe_get(output, "roadmap_id")
        
        logger.info(
            "coordinator_node_complete",
            task_id=task_id,
            node_name=node_name,
            roadmap_id=roadmap_id,
            duration_ms=duration_ms,
        )
        
        # 1. 更新 live_step 缓存
        await self._update_live_step(task_id, node_name)
        
        # 2. 构建extra_data，包含关键信息供前端使用
        extra_data = {"duration_ms": duration_ms}
        
        # ✅ 修复：传递edit_source给前端（用于分支判断）
        edit_source = _safe_get(output, "edit_source")
        
        # 🔍 Debug日志：检查edit_source是否存在
        logger.info(
            "coordinator_extract_edit_source",
            task_id=task_id,
            node_name=node_name,
            edit_source=edit_source,
            output_has_edit_source="edit_source" in output if isinstance(output, dict) else False,
            output_keys=list(output.keys()) if isinstance(output, dict) else "not_dict",
        )
        
        if edit_source is not None:
            extra_data["edit_source"] = edit_source
            logger.info(
                "coordinator_added_edit_source_to_extra_data",
                task_id=task_id,
                node_name=node_name,
                edit_source=edit_source,
            )
        
        # ✅ 修复：传递modified_node_ids给前端（用于高亮修改的节点）
        # EditorHandler会将modified_node_ids放在output中
        modified_node_ids = _safe_get(output, "modified_node_ids")
        if modified_node_ids is not None:
            extra_data["modified_concept_ids"] = modified_node_ids
        
        # ✅ 关键修复：从 output 提取 current_step（必须存在）
        # 原因：
        # 1. output 是 executor 传递的 final_state（完整的工作流状态）
        # 2. 所有节点都返回 current_step 字段（已验证）
        # 3. current_step 代表工作流的逻辑状态，不同于物理节点名称 node_name
        # 例如：human_review 批准后返回 current_step="content_generation_queued"
        #       但 node_name="human_review"，前端需要收到 "content_generation_queued"
        current_step = _safe_get(output, "current_step")
        
        # ⚠️ 严格校验：current_step 必须存在
        # 如果缺失，说明状态机有严重bug，必须立即发现
        if not current_step:
            logger.critical(
                "coordinator_missing_current_step_critical_bug",
                task_id=task_id,
                node_name=node_name,
                output_keys=list(output.keys()) if isinstance(output, dict) else "not_dict",
                output_sample=str(output)[:500],
                message="CRITICAL: final_state 中缺少 current_step！这是状态机的严重bug！",
            )
            # ❌ 不使用 node_name fallback（会导致前端状态异常）
            # 直接抛出异常，强制修复底层问题
            raise ValueError(
                f"CRITICAL BUG: Node {node_name} completed but final_state has no current_step. "
                f"This breaks frontend state sync. output_keys={list(output.keys()) if isinstance(output, dict) else 'not_dict'}"
            )
        
        # 3. 发送 WebSocket 通知
        logger.info(
            "coordinator_sending_websocket",
            task_id=task_id,
            node_name=node_name,
            current_step=current_step,
            extra_data=extra_data,
        )
        
        await self._send_progress_notification(
            task_id=task_id,
            step=current_step,  # ✅ 强制使用 current_step（前端依赖此字段，不能fallback到node_name）
            status="completed",
            extra_data=extra_data,
        )
        
        # 4. 记录执行日志（可选）
        # ExecutionLogger 由各 Node 内部记录，这里不重复
        # 日志会在工作流完成时统一刷新到数据库（on_workflow_complete）
    
    async def on_node_failed(
        self,
        task_id: str,
        node_name: str,
        error: Exception,
        duration_ms: int,
    ) -> None:
        """
        节点失败时的副作用处理
        
        执行：
        1. 更新 Task 状态为 failed（不覆盖 current_step）
        2. 发送 WebSocket 失败通知
        3. 记录错误日志
        
        Args:
            task_id: 任务ID
            node_name: 节点名称
            error: 异常对象
            duration_ms: 执行时长（毫秒）
        """
        logger.error(
            "coordinator_node_failed",
            task_id=task_id,
            node_name=node_name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=duration_ms,
        )
        
        # 1. 更新 Task 状态为 failed（不覆盖 current_step）
        await self._update_task_status(
            task_id=task_id,
            status="failed",
            current_step=None,  # 保留失败时的阶段信息
            error_message=str(error)[:500],
        )
        
        # 2. 发送 WebSocket 失败通知
        await self._send_failed_notification(
            task_id=task_id,
            error=error,
            step=node_name,
        )
        
        # 3. 记录错误日志
        await self._log_error(
            task_id=task_id,
            node_name=node_name,
            error=error,
            duration_ms=duration_ms,
        )
    
    async def on_workflow_complete(
        self,
        task_id: str,
        final_state: dict,
    ) -> None:
        """
        工作流完成时的副作用处理
        
        执行：
        1. 清除 live_step 缓存
        2. 发送 WebSocket 完成通知
        3. 刷新执行日志缓冲区
        
        Args:
            task_id: 任务ID
            final_state: 最终状态（可能是dict或Pydantic模型）
        """
        roadmap_id = _safe_get(final_state, "roadmap_id")
        
        logger.info(
            "coordinator_workflow_complete",
            task_id=task_id,
            roadmap_id=roadmap_id,
            final_step=_safe_get(final_state, "current_step"),
        )
        
        # 1. 清除 live_step 缓存
        await self.state_manager.clear_live_step(task_id)
        
        # 2. 发送 WebSocket 完成通知（可选，通常由最后的节点发送）
        # 这里不发送，避免重复
        
        # 3. 刷新执行日志缓冲区
        await self.execution_logger.flush()
    
    async def on_workflow_failed(
        self,
        task_id: str,
        error: Exception,
    ) -> None:
        """
        工作流失败时的副作用处理
        
        执行：
        1. 更新 Task 状态为 failed（不覆盖 current_step）
        2. 清除 live_step 缓存
        3. 发送 WebSocket 失败通知
        4. 刷新执行日志缓冲区
        
        Args:
            task_id: 任务ID
            error: 异常对象
        """
        logger.error(
            "coordinator_workflow_failed",
            task_id=task_id,
            error=str(error),
            error_type=type(error).__name__,
        )
        
        # 1. 更新 Task 状态（不覆盖 current_step）
        await self._update_task_status(
            task_id=task_id,
            status="failed",
            current_step=None,  # 保留失败时的阶段信息
            error_message=str(error)[:500],
        )
        
        # 2. 清除 live_step 缓存
        await self.state_manager.clear_live_step(task_id)
        
        # 3. 发送 WebSocket 失败通知
        await self._send_failed_notification(
            task_id=task_id,
            error=error,
            step="workflow",
        )
        
        # 4. 刷新执行日志缓冲区
        try:
            await self.execution_logger.flush()
        except Exception as e:
            logger.error(
                "failed_to_flush_logs",
                task_id=task_id,
                error=str(e),
            )
    
    # ============================================================
    # 私有方法：原子操作
    # ============================================================
    
    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        roadmap_id: Optional[str] = None,
    ) -> None:
        """
        更新 Task 状态（原子操作）
        
        副作用失败不影响主流程。
        
        Args:
            task_id: 任务ID
            status: 新状态
            current_step: 当前步骤（None表示不更新）
            error_message: 错误信息（可选）
            roadmap_id: 路线图ID（可选）
        """
        try:
            async with get_celery_session() as session:
                task_crud = get_task_crud()
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=status,
                    current_step=current_step,
                    error_message=error_message,
                    roadmap_id=roadmap_id,
                )
                # Session 自动 commit
            
            logger.debug(
                "coordinator_task_status_updated",
                task_id=task_id,
                status=status,
                current_step=current_step,
            )
        except Exception as e:
            logger.error(
                "coordinator_failed_to_update_task_status",
                task_id=task_id,
                status=status,
                error=str(e),
                error_type=type(e).__name__,
            )
    
    async def _update_live_step(
        self,
        task_id: str,
        step: str,
    ) -> None:
        """
        更新 live_step 缓存（原子操作）
        
        Args:
            task_id: 任务ID
            step: 当前步骤
        """
        try:
            await self.state_manager.set_live_step(task_id, step)
            
            logger.debug(
                "coordinator_live_step_updated",
                task_id=task_id,
                step=step,
            )
        except Exception as e:
            logger.error(
                "coordinator_failed_to_update_live_step",
                task_id=task_id,
                step=step,
                error=str(e),
            )
    
    async def _send_progress_notification(
        self,
        task_id: str,
        step: str,
        status: str = "processing",
        message: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """
        发送进度通知（原子操作）
        
        Args:
            task_id: 任务ID
            step: 当前步骤
            status: 状态
            message: 消息（可选）
            extra_data: 额外数据（可选）
        """
        try:
            await self.notification_service.publish_progress(
                task_id=task_id,
                step=step,
                status=status,
                message=message,
                extra_data=extra_data,
            )
            
            logger.debug(
                "coordinator_notification_sent",
                task_id=task_id,
                step=step,
                status=status,
            )
        except Exception as e:
            logger.error(
                "coordinator_failed_to_send_notification",
                task_id=task_id,
                step=step,
                error=str(e),
            )
    
    async def _send_failed_notification(
        self,
        task_id: str,
        error: Exception,
        step: str,
    ) -> None:
        """
        发送失败通知（原子操作）
        
        Args:
            task_id: 任务ID
            error: 异常对象
            step: 失败步骤
        """
        try:
            await self.notification_service.publish_failed(
                task_id=task_id,
                error=str(error),
                step=step,
                exception=error,
            )
            
            logger.debug(
                "coordinator_failure_notification_sent",
                task_id=task_id,
                step=step,
            )
        except Exception as e:
            logger.error(
                "coordinator_failed_to_send_failure_notification",
                task_id=task_id,
                step=step,
                error=str(e),
            )
    
    async def _log_error(
        self,
        task_id: str,
        node_name: str,
        error: Exception,
        duration_ms: int,
    ) -> None:
        """
        记录错误日志（原子操作）
        
        Args:
            task_id: 任务ID
            node_name: 节点名称
            error: 异常对象
            duration_ms: 执行时长（毫秒）
        """
        try:
            await self.execution_logger.error(
                task_id=task_id,
                category="workflow",
                message=f"节点执行失败: {node_name}",
                step=node_name,
                duration_ms=duration_ms,
                details={
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
            )
            
            logger.debug(
                "coordinator_error_logged",
                task_id=task_id,
                node_name=node_name,
            )
        except Exception as e:
            logger.error(
                "coordinator_failed_to_log_error",
                task_id=task_id,
                node_name=node_name,
                error=str(e),
            )


# 全局单例（可选）
_coordinator_instance: Optional[SideEffectCoordinator] = None


def get_side_effect_coordinator(
    notification_service: NotificationService,
    execution_logger: ExecutionLogger,
    state_manager: StateManager,
) -> SideEffectCoordinator:
    """
    获取副作用协调器实例（工厂函数）
    
    Args:
        notification_service: 通知服务
        execution_logger: 执行日志服务
        state_manager: 状态管理器
    
    Returns:
        SideEffectCoordinator 实例
    """
    global _coordinator_instance
    
    if _coordinator_instance is None:
        _coordinator_instance = SideEffectCoordinator(
            notification_service=notification_service,
            execution_logger=execution_logger,
            state_manager=state_manager,
        )
    
    return _coordinator_instance

