"""
路线图重试服务

基于LangGraph 1.0 Checkpoint机制的两种重试模式：

1. **断点续传（Resume from Checkpoint）**：
   - 从最后的checkpoint恢复（主图或子图）
   - 适用于任意节点失败后重新启动
   - 自动处理并发失败的子图节点
   - 参考：https://docs.langchain.com/oss/python/langgraph/persistence

2. **时间旅行（Time Travel）**：
   - 回到主图历史节点重新执行
   - 仅支持主图节点（顺序执行）
   - 使用流式查找优化性能
   - 参考：https://docs.langchain.com/oss/python/langgraph/use-time-travel

注意：概念内容重新生成不属于Retry功能，已移到Content编辑服务
"""
import asyncio
import structlog
from typing import Optional
from datetime import datetime

from app.schemas.retry import (
    RetryRequest,
    RetryResponse,
    RetryMode,
    RetryScope,
    MainGraphNode,
    TaskRetryStatus,
    CheckpointInfo,
)
from app.models.constants import TaskStatus
from app.core.orchestrator_factory import OrchestratorFactory
from app.db.celery_session import get_celery_session
from app.crud.crud_task import get_task_crud
from app.services.shared.notification_service import notification_service

logger = structlog.get_logger()


class RetryService:
    """
    路线图重试服务
    
    职责：
    1. 验证任务状态是否可重试
    2. 实现断点续传（支持主图和子图）
    3. 实现时间旅行（仅支持主图）
    4. 启动重试任务（Celery）
    """
    
    async def get_retry_status(self, task_id: str) -> TaskRetryStatus:
        """
        获取任务的重试状态
        
        检查：
        1. 任务是否存在
        2. 任务状态是否允许重试
        3. 是否有子图在中断
        4. 可用的重试模式
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务重试状态信息
        """
        async with get_celery_session() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            
            if not task:
                return TaskRetryStatus(
                    task_id=task_id,
                    can_retry=False,
                    retry_reason="任务不存在",
                    is_subgraph_interrupted=False,
                    available_modes=[],
                )
            
            # 检查任务状态是否允许重试
            can_retry_statuses = [
                TaskStatus.FAILED.value,
                TaskStatus.PARTIAL_FAILURE.value,
                TaskStatus.CANCELLED.value,
            ]
            
            can_retry = task.status in can_retry_statuses
            retry_reason = None
            
            if not can_retry:
                if task.status == TaskStatus.COMPLETED.value:
                    retry_reason = "任务已完成，无需重试"
                elif task.status == TaskStatus.PROCESSING.value:
                    retry_reason = "任务正在执行中，请等待完成后再重试"
                elif task.status == TaskStatus.HUMAN_REVIEW.value:
                    retry_reason = "任务等待人工审核，请使用审核API而不是重试"
                else:
                    retry_reason = f"任务状态 {task.status} 不允许重试"
            
            # 获取checkpoint信息和子图状态
            current_checkpoint = None
            is_subgraph_interrupted = False
            available_modes = []
            
            if can_retry:
                try:
                    # 检查checkpoint状态（包括子图）
                    checkpoint_info = await self._get_checkpoint_info(task_id)
                    
                    current_checkpoint = checkpoint_info["checkpoint"]
                    is_subgraph_interrupted = checkpoint_info["is_subgraph"]
                    
                    # 所有失败任务都支持断点续传
                    available_modes.append(RetryMode.RESUME)
                    
                    # 如果有roadmap_id，且不是子图中断，支持时间旅行
                    # （子图并发失败不使用时间旅行，使用断点续传）
                    if task.roadmap_id and not is_subgraph_interrupted:
                        available_modes.append(RetryMode.TIME_TRAVEL)
                    
                except Exception as e:
                    logger.warning(
                        "failed_to_get_checkpoint_info",
                        task_id=task_id,
                        error=str(e),
                    )
            
            return TaskRetryStatus(
                task_id=task_id,
                can_retry=can_retry,
                retry_reason=retry_reason,
                current_checkpoint=current_checkpoint,
                is_subgraph_interrupted=is_subgraph_interrupted,
                available_modes=available_modes,
            )
    
    async def retry_task(
        self,
        task_id: str,
        request: RetryRequest,
        user_id: str,
    ) -> RetryResponse:
        """
        执行任务重试
        
        Args:
            task_id: 任务ID
            request: 重试请求
            user_id: 用户ID
            
        Returns:
            重试响应
            
        Raises:
            ValueError: 任务不存在、状态不允许重试、参数错误等
            PermissionError: 用户无权重试此任务
        """
        # 步骤1: 验证任务和权限
        async with get_celery_session() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            
            if not task:
                raise ValueError(f"任务 {task_id} 不存在")
            
            if task.user_id != user_id:
                raise PermissionError("您无权重试此任务")
            
            # 检查任务状态
            retry_status = await self.get_retry_status(task_id)
            if not retry_status.can_retry:
                raise ValueError(f"任务无法重试: {retry_status.retry_reason}")
        
        # 步骤2: 根据重试模式选择策略
        if request.mode == RetryMode.RESUME:
            return await self._resume_from_checkpoint(task_id, task, request)
        
        elif request.mode == RetryMode.TIME_TRAVEL:
            if not request.target_node:
                raise ValueError("时间旅行模式需要指定target_node参数")
            
            # 验证不是子图中断（子图不支持时间旅行）
            retry_status = await self.get_retry_status(task_id)
            if retry_status.is_subgraph_interrupted:
                raise ValueError(
                    "子图节点失败不支持时间旅行，请使用断点续传模式（mode=resume）"
                )
            
            return await self._time_travel_to_node(task_id, task, request)
        
        else:
            raise ValueError(f"不支持的重试模式: {request.mode}")
    
    async def _resume_from_checkpoint(
        self,
        task_id: str,
        task,
        request: RetryRequest,
    ) -> RetryResponse:
        """
        断点续传：从最后的checkpoint恢复
        
        适用场景：
        - Worker进程重启
        - 主图节点失败
        - 子图节点失败（包括并发失败）
        
        关键特性：
        - LangGraph自动从最后checkpoint恢复
        - 自动处理并发失败的子图节点
        - 不需要手动查找checkpoint
        
        Args:
            task_id: 任务ID
            task: 任务对象
            request: 重试请求
            
        Returns:
            重试响应
        """
        logger.info(
            "resume_from_checkpoint_starting",
            task_id=task_id,
            reason=request.reason,
        )
        
        factory = None
        try:
            factory = OrchestratorFactory()
            await factory.initialize()
            
            executor = factory.create_workflow_executor()
            config = {"configurable": {"thread_id": task_id}}
            
            # ===== 关键：检查子图状态（subgraphs=True）=====
            state = await executor.graph.aget_state(config, subgraphs=True)
            
            # 分析当前状态
            is_subgraph = bool(state.tasks)
            failed_nodes = []
            
            if is_subgraph:
                # 有子图在中断/失败
                subgraph_state = state.tasks[0].state
                
                # ✅ 修复：checkpoint 保存失败时（如数据库超时），subgraph_state 可能为 None。
                # 此时降级为主图节点处理，LangGraph 会从最后有效的 checkpoint 恢复。
                if subgraph_state is not None:
                    failed_nodes = list(subgraph_state.next) if subgraph_state.next else []
                    logger.info(
                        "subgraph_interrupted_detected",
                        task_id=task_id,
                        subgraph_next=failed_nodes,
                        failed_count=len(failed_nodes),
                    )
                else:
                    is_subgraph = False
                    failed_nodes = list(state.next) if state.next else []
                    logger.warning(
                        "subgraph_state_is_none_fallback_to_main_graph",
                        task_id=task_id,
                        tasks_count=len(state.tasks),
                        main_graph_next=failed_nodes,
                        hint="checkpoint 可能未完整保存（如数据库超时），降级为主图恢复",
                    )
            else:
                # 主图节点失败
                failed_nodes = list(state.next) if state.next else []
                
                logger.info(
                    "main_graph_failed",
                    task_id=task_id,
                    main_graph_next=failed_nodes,
                )
            
            # 创建Celery任务恢复执行
            # 注意：不传checkpoint_id，LangGraph会自动从最后checkpoint恢复
            # 使用 asyncio.to_thread 避免 .delay() 同步阻塞事件循环
            from app.tasks.workflow_resume_tasks import resume_from_checkpoint
            celery_task = await asyncio.to_thread(resume_from_checkpoint.delay, task_id)
            
            # 更新任务的celery_task_id 并将状态改为处理中
            async with get_celery_session() as session:
                task_crud = get_task_crud()
                await task_crud.update_celery_id(
                    session,
                    task_id=task_id,
                    celery_task_id=celery_task.id,
                )
                await task_crud.update_task_status(
                    session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # 发送WebSocket通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="resume_from_checkpoint",
                status=TaskStatus.PROCESSING.value,
                message="断点续传：正在从最后checkpoint恢复...",
                extra_data={
                    "mode": "resume",
                    "is_subgraph": is_subgraph,
                    "failed_nodes_count": len(failed_nodes),
                },
            )
            
            return RetryResponse(
                success=True,
                message=f"断点续传启动成功（{len(failed_nodes)}个节点将重试）",
                task_id=task_id,
                celery_task_id=celery_task.id,
                retry_scope=RetryScope.TASK,
                retry_from="last_checkpoint",
            )
        
        except Exception as e:
            logger.error(
                "resume_from_checkpoint_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise ValueError(f"断点续传失败: {str(e)}")
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持
        # 只在应用关闭时清理（main.py 的 shutdown 事件）
    
    async def _time_travel_to_node(
        self,
        task_id: str,
        task,
        request: RetryRequest,
    ) -> RetryResponse:
        """
        时间旅行：回到主图历史节点重新执行
        
        仅支持主图节点（顺序执行），不支持子图节点（并发执行）。
        
        使用流式查找优化性能：
        - 主图是顺序执行的（Intent -> Curriculum -> Content）
        - 找到第一个匹配的checkpoint即可
        - 不需要遍历所有历史
        
        参考：https://docs.langchain.com/oss/python/langgraph/use-time-travel
        
        Args:
            task_id: 任务ID
            task: 任务对象
            request: 重试请求
            
        Returns:
            重试响应
        """
        logger.info(
            "time_travel_starting",
            task_id=task_id,
            target_node=request.target_node,
            reason=request.reason,
        )
        
        # 验证roadmap存在
        if not task.roadmap_id:
            raise ValueError("任务没有关联的路线图，无法执行时间旅行")
        
        factory = None
        try:
            factory = OrchestratorFactory()
            await factory.initialize()
            
            executor = factory.create_workflow_executor()
            config = {"configurable": {"thread_id": task_id}}
            
            # ===== 步骤1: 流式查找目标节点的checkpoint（性能优化）=====
            logger.info(
                "searching_checkpoint_history",
                task_id=task_id,
                target_node=request.target_node.value,
            )
            
            checkpoint_id = None
            iteration_count = 0
            max_depth = 50  # 防护：最多查询50个checkpoint
            matched_checkpoint_state = None
            
            # 主图节点名称可能有别名
            target_node_names = [request.target_node.value]
            
            # 流式查找：找到即停止（关键性能优化）
            async for state in executor.graph.aget_state_history(config):
                iteration_count += 1
                current_step = state.values.get("current_step", "")
                
                # 检查是否匹配目标节点
                if current_step in target_node_names:
                    checkpoint_id = state.config["configurable"]["checkpoint_id"]
                    matched_checkpoint_state = state
                    
                    logger.info(
                        "checkpoint_found",
                        task_id=task_id,
                        target_node=request.target_node.value,
                        checkpoint_id=checkpoint_id[:8],
                        iterations=iteration_count,
                        timestamp=state.metadata.get("timestamp"),
                    )
                    break  # ✅ 主图是顺序的，找到第一个即可
                
                # 防护：防止无限遍历
                if iteration_count >= max_depth:
                    logger.warning(
                        "checkpoint_search_depth_exceeded",
                        task_id=task_id,
                        max_depth=max_depth,
                        target_node=request.target_node.value,
                    )
                    break
            
            if not checkpoint_id:
                # 提供可用的checkpoint列表帮助调试
                available_steps = []
                temp_count = 0
                async for state in executor.graph.aget_state_history(config):
                    available_steps.append(state.values.get("current_step", "unknown"))
                    temp_count += 1
                    if temp_count >= 10:  # 只收集最近10个
                        break
                
                raise ValueError(
                    f"未找到目标节点 {request.target_node.value} 的checkpoint。"
                    f"已查询 {iteration_count} 个checkpoint。"
                    f"最近的节点: {available_steps[:5]}"
                )
            
            # ===== 步骤2: 从该checkpoint恢复（时间旅行）=====
            logger.info(
                "time_travel_resuming_from_checkpoint",
                task_id=task_id,
                checkpoint_id=checkpoint_id,
                target_node=request.target_node.value,
            )
            
            # 创建Celery任务，指定checkpoint_id（时间旅行）
            # 使用 asyncio.to_thread 避免 .delay() 同步阻塞事件循环
            from app.tasks.workflow_resume_tasks import resume_from_checkpoint
            celery_task = await asyncio.to_thread(
                resume_from_checkpoint.apply_async,
                (task_id,),
                {"checkpoint_id": checkpoint_id},  # ✅ 时间旅行：指定checkpoint
            )
            
            # 更新任务状态
            async with get_celery_session() as session:
                task_crud = get_task_crud()
                await task_crud.update_celery_id(
                    session,
                    task_id=task_id,
                    celery_task_id=celery_task.id,
                )
                await task_crud.update_task_status(
                    session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step=request.target_node.value,
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # 发送WebSocket通知
            await notification_service.publish_progress(
                task_id=task_id,
                step=request.target_node.value,
                status=TaskStatus.PROCESSING.value,
                message=f"时间旅行：从{request.target_node.value}节点重新开始...",
                extra_data={
                    "mode": "time_travel",
                    "checkpoint_id": checkpoint_id,
                    "iterations_to_find": iteration_count,
                },
            )
            
            return RetryResponse(
                success=True,
                message=f"时间旅行成功：从{request.target_node.value}节点重新开始",
                task_id=task_id,
                celery_task_id=celery_task.id,
                retry_scope=RetryScope.TASK,
                retry_from=f"{request.target_node.value}_checkpoint_{checkpoint_id[:8]}",
            )
        
        except Exception as e:
            logger.error(
                "time_travel_failed",
                task_id=task_id,
                target_node=request.target_node.value if hasattr(request, 'target_node') else None,
                error=str(e),
                exc_info=True,
            )
            raise ValueError(f"时间旅行失败: {str(e)}")
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持
        # 只在应用关闭时清理（main.py 的 shutdown 事件）
    
    async def _get_checkpoint_info(self, task_id: str) -> dict:
        """
        获取checkpoint信息和子图状态
        
        返回：
        - checkpoint: CheckpointInfo对象
        - is_subgraph: 是否有子图在中断
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: {"checkpoint": CheckpointInfo, "is_subgraph": bool}
        """
        factory = None
        try:
            factory = OrchestratorFactory()
            await factory.initialize()
            
            executor = factory.create_workflow_executor()
            config = {"configurable": {"thread_id": task_id}}
            
            # 获取状态（包括子图）
            state = await executor.graph.aget_state(config, subgraphs=True)
            
            if not state or not state.values:
                return {
                    "checkpoint": None,
                    "is_subgraph": False,
                }
            
            # 检查子图状态
            is_subgraph = bool(state.tasks)
            
            # 获取checkpoint元数据（主图的）
            checkpoint_id = state.config.get("configurable", {}).get("checkpoint_id", "unknown")
            timestamp = state.metadata.get("timestamp", datetime.utcnow().isoformat())
            current_step = state.values.get("current_step", "unknown")
            next_nodes = list(state.next) if state.next else []
            
            # 判断是否可以重试
            can_retry = bool(next_nodes) or current_step != "completed"
            
            checkpoint_info = CheckpointInfo(
                checkpoint_id=checkpoint_id,
                timestamp=timestamp,
                node_name=current_step,
                next_nodes=next_nodes,
                can_retry=can_retry,
            )
            
            return {
                "checkpoint": checkpoint_info,
                "is_subgraph": is_subgraph,
            }
            
        except Exception as e:
            logger.error(
                "failed_to_get_checkpoint_info",
                task_id=task_id,
                error=str(e),
            )
            return {
                "checkpoint": None,
                "is_subgraph": False,
            }
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持。
        # cleanup() 会重置整个进程的单例状态，影响所有后续请求。


# 依赖注入
def get_retry_service() -> RetryService:
    """获取RetryService实例（依赖注入）"""
    return RetryService()
