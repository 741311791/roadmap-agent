"""
工作流执行器（重构版 - 统一副作用管理）

负责执行和恢复工作流：
- execute: 执行完整工作流
- resume_after_human_review: 在人工审核后恢复工作流

重构改进：
- 使用 SideEffectCoordinator 统一管理所有副作用
- Handler 只负责保存业务数据
- 通过 RuntimeContext 注入依赖
"""
import structlog
import time
from typing import TYPE_CHECKING
from langgraph.types import Command
from prometheus_client import Histogram, Counter

from app.models.domain import UserRequest
from app.db.celery_session import get_celery_session
from .base import RoadmapState
from .builder import WorkflowBuilder
from .state_manager import StateManager
from .runtime_context import RuntimeContext
from .handlers import HandlerRegistry
from .side_effect_coordinator import SideEffectCoordinator

if TYPE_CHECKING:
    from app.services.shared.execution_logger import ExecutionLogger

logger = structlog.get_logger()


# ====================================================================
# 辅助函数
# ====================================================================
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


def _deep_convert_to_dict(obj):
    """
    递归将对象转换为纯字典（深度转换所有嵌套的Pydantic模型）
    
    Args:
        obj: 任意对象（dict, list, Pydantic模型等）
        
    Returns:
        纯字典或列表（所有Pydantic模型都被转换）
    """
    from pydantic import BaseModel
    
    if isinstance(obj, BaseModel):
        # Pydantic 模型 -> 字典（递归处理）
        return _deep_convert_to_dict(obj.model_dump())
    elif isinstance(obj, dict):
        # 字典 -> 递归处理所有值
        return {k: _deep_convert_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # 列表/元组 -> 递归处理所有元素
        return [_deep_convert_to_dict(item) for item in obj]
    else:
        # 其他类型（基本类型）直接返回
        return obj


# ====================================================================
# Prometheus 指标定义
# ====================================================================
langgraph_node_duration = Histogram(
    'langgraph_node_duration_seconds',
    'LangGraph node execution duration',
    labelnames=['node_name', 'status'],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300, 600]
)

langgraph_node_failures = Counter(
    'langgraph_node_failures_total',
    'LangGraph node execution failures',
    labelnames=['node_name', 'error_type']
)


class WorkflowExecutor:
    """
    工作流执行器（重构版 - 统一副作用管理）
    
    负责执行和恢复 LangGraph 工作流。
    
    重构改进：
    - 使用 SideEffectCoordinator 统一管理所有副作用
    - Handler 只负责保存业务数据
    - 清晰的职责分离
    """
    
    def __init__(
        self,
        builder: WorkflowBuilder,
        state_manager: StateManager,
        checkpointer,
        execution_logger: "ExecutionLogger",
        runtime_context: RuntimeContext,
        handler_registry: HandlerRegistry,
        side_effect_coordinator: SideEffectCoordinator,
    ):
        """
        Args:
            builder: WorkflowBuilder 实例
            state_manager: StateManager 实例
            checkpointer: AsyncPostgresSaver 实例
            execution_logger: ExecutionLogger 实例（用于刷新日志缓冲区）
            runtime_context: RuntimeContext 实例（包含依赖）
            handler_registry: HandlerRegistry 实例（处理业务数据保存）
            side_effect_coordinator: SideEffectCoordinator 实例（处理副作用）
        """
        self.builder = builder
        self.state_manager = state_manager
        self.checkpointer = checkpointer
        self.execution_logger = execution_logger
        self.runtime_context = runtime_context
        self.handler_registry = handler_registry
        self.coordinator = side_effect_coordinator
        self._graph = None
    
    @property
    def graph(self):
        """
        延迟构建工作流图
        
        只在第一次访问时构建，避免启动时的性能开销。
        """
        if self._graph is None:
            self._graph = self.builder.build(self.checkpointer)
        return self._graph
    
    async def execute(
        self,
        user_request: UserRequest,
        task_id: str,
        pre_generated_roadmap_id: str | None = None,
    ) -> RoadmapState:
        """
        执行完整的工作流（重构版 - Handler模式）
        
        在Stream Loop中统一处理副作用（数据库保存、日志、通知）。
        
        Args:
            user_request: 用户请求
            task_id: 追踪 ID
            pre_generated_roadmap_id: 预生成的路线图 ID（可选）
            
        Returns:
            最终的工作流状态
        """
        logger.info(
            "workflow_execution_starting",
            task_id=task_id,
            user_id=user_request.user_id,
            pre_generated_roadmap_id=pre_generated_roadmap_id,
            config=self.builder.config.model_dump(),
        )
        
        # 创建初始状态
        initial_state = self._create_initial_state(user_request, task_id)
        
        # LangGraph 配置（包含RuntimeContext）
        config = {
            "configurable": {
                "thread_id": task_id,
                "runtime_context": self.runtime_context,
            }
        }
        
        try:
            logger.info(
                "workflow_graph_streaming",
                task_id=task_id,
            )
            
            # ===== 使用 astream_events 监听完整节点生命周期 =====
            # 优势：
            # 1. 监听 on_chain_start（节点开始）→ 调用 handler.on_start()
            # 2. 监听 on_chain_end（节点结束）→ 调用 handler.handle() + on_complete()
            # 3. 支持子图节点的生命周期监听
            final_state = initial_state
            node_start_times = {}

            async for event in self.graph.astream_events(
                initial_state,
                config=config,
                version="v2",  # 使用 v2 版本获取详细事件
            ):
                event_type = event.get("event")
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")
                
                # 过滤出 LangGraph 节点事件（排除 LLM、Tool 等其他事件）
                if not node_name:
                    continue
                
                # ===== 节点开始事件 =====
                if event_type == "on_chain_start":
                    node_start_times[node_name] = time.time()
                    
                    logger.info(
                        "workflow_node_starting",
                        task_id=task_id,
                        node=node_name,
                    )
                    
                    # 调用协调器处理副作用
                    # ✅ 方案 A：edit_plan_analysis/roadmap_edit 开始时传递 edit_source，避免前端分支显示竞态
                    extra_data = None
                    if node_name in ("edit_plan_analysis", "roadmap_edit"):
                        edit_source = _safe_get(final_state, "edit_source")
                        if edit_source is not None:
                            extra_data = {"edit_source": edit_source}
                    
                    await self.coordinator.on_node_start(
                        task_id=task_id,
                        node_name=node_name,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                        extra_data=extra_data,
                    )
                
                # ===== 节点结束事件 =====
                elif event_type == "on_chain_end":
                    start_time = node_start_times.pop(node_name, time.time())
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # 🔍 从 event data 中提取节点输出
                    node_output = event.get("data", {}).get("output", {})
                    
                    # 🔍 详细日志：查看 event.data.output 的实际内容
                    logger.info(
                        "event_data_output_debug",
                        task_id=task_id,
                        node=node_name,
                        output_type=type(node_output).__name__,
                        output_keys=list(node_output.keys()) if isinstance(node_output, dict) else "not_dict",
                        output_sample=str(node_output)[:500],  # 查看前500字符
                    )
                    
                    # ====================================================================
                    # 类型检查：只处理字典类型的输出（节点函数的状态更新）
                    # ====================================================================
                    # LangGraph astream_events 会为同一节点产生多个 on_chain_end 事件：
                    # 1. 内层 LLM/Agent 调用 → output 是 Pydantic 模型（如 IntentAnalysisOutput）
                    # 2. 节点函数返回 → output 是状态更新字典（如 {"intent_analysis": ..., "user_id": ...}）
                    # 
                    # Handler 只需要处理节点函数的最终返回（字典类型），跳过内层调用的返回。
                    # ====================================================================
                    if not isinstance(node_output, dict):
                        logger.debug(
                            "workflow_skip_non_dict_output",
                            task_id=task_id,
                            node=node_name,
                            output_type=type(node_output).__name__,
                            reason="Only dict outputs (node state updates) are processed by handlers",
                        )
                        # 跳过非字典类型的输出（内层 LLM/Agent 调用的返回）
                        continue
                    
                    # 将 node_output 增量合并到本地 final_state，避免查询 PostgreSQL checkpoint。
                    # node_output 包含节点函数返回的所有状态字段，coordinator 只需要 current_step/roadmap_id 等，
                    # 这些字段在节点返回值中均已包含。
                    # ⚠️ 流结束后（第339行）仍会 aget_state 一次确认最终状态。
                    final_state = {**final_state, **node_output}
                    
                    logger.info(
                        "workflow_node_completed",
                        task_id=task_id,
                        node=node_name,
                        duration_ms=duration_ms,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                    )
                    
                    # ===== 副作用统一处理 =====
                    try:
                        # ✅ 关键修复：使用 node_output（Node返回值），而不是 final_state（整个State）
                        # 因为Handler需要的临时字段（如user_id, approved等）在Node返回值中，不在State的顶级
                        handler_input = _deep_convert_to_dict(node_output)
                        
                        async with get_celery_session() as session:
                            await self.handler_registry.handle(
                                node_name=node_name,
                                output=handler_input,
                                task_id=task_id,
                                session=session,
                            )
                        
                        # 2. 统一处理副作用（协调器）
                        # ✅ 现在传递的 final_state 已经包含了 node_output 中的所有字段（包括 roadmap_id）
                        await self.coordinator.on_node_complete(
                            task_id=task_id,
                            node_name=node_name,
                            output=final_state,
                            duration_ms=duration_ms,
                        )
                        
                    except Exception as e:
                        logger.error(
                            "workflow_handler_failed",
                            task_id=task_id,
                            node_name=node_name,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        
                        # 统一处理失败副作用（协调器）
                        await self.coordinator.on_node_failed(
                            task_id=task_id,
                            node_name=node_name,
                            error=e,
                            duration_ms=duration_ms,
                        )
                    
                    # 3. 记录Prometheus指标
                    langgraph_node_duration.labels(
                        node_name=node_name,
                        status="success"
                    ).observe(duration_ms / 1000.0)
            
            # ✅ 检查工作流是否被interrupt暂停
            state_snapshot = await self.graph.aget_state(config)
            next_nodes = list(state_snapshot.next) if state_snapshot.next else []
            
            if next_nodes:
                logger.info(
                    "workflow_interrupted",
                    task_id=task_id,
                    current_step=_safe_get(final_state, "current_step"),
                    next_nodes=next_nodes,
                    roadmap_id=_safe_get(final_state, "roadmap_id"),
                    message="工作流在interrupt处暂停",
                )
                
                # 如果是human_review暂停，Handler已经处理了状态更新
                if "human_review" in next_nodes:
                    final_state["current_step"] = "human_review"
                    # ✅ 修复前端状态不同步：
                    # coordinator.on_node_start(human_review) 发送的是 status=processing，
                    # interrupt 触发后没有节点的 on_chain_end 事件，前端永远收不到 pending 状态。
                    # 必须主动推送 human_review pending 通知，告知前端工作流已暂停等待审核。
                    await self.coordinator.on_workflow_interrupted_for_review(
                        task_id=task_id,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                    )
            else:
                logger.info(
                    "workflow_execution_completed",
                    task_id=task_id,
                    final_step=_safe_get(final_state, "current_step"),
                    roadmap_id=_safe_get(final_state, "roadmap_id"),
                )
            
            # 工作流完成，统一处理副作用（协调器）
            await self.coordinator.on_workflow_complete(
                task_id=task_id,
                final_state=final_state,
            )
            
            return final_state
            
        except Exception as e:
            # 记录Prometheus指标（工作流失败）
            error_type = type(e).__name__
            langgraph_node_failures.labels(
                node_name="workflow",
                error_type=error_type
            ).inc()
            
            logger.error(
                "workflow_execution_failed",
                task_id=task_id,
                error=str(e),
                error_type=error_type,
            )
            
            # 工作流失败，统一处理副作用（协调器）
            await self.coordinator.on_workflow_failed(
                task_id=task_id,
                error=e,
            )
            
            # 刷新日志
            await self.execution_logger.flush()
            
            raise
    
    async def resume_after_human_review(
        self,
        task_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> RoadmapState:
        """
        在人工审核后恢复工作流（重构版）
        
        使用Command(resume=...)来恢复被interrupt()暂停的工作流。
        
        Args:
            task_id: 追踪ID
            approved: 是否批准
            feedback: 可选的反馈信息（当拒绝时）
            
        Returns:
            最终的工作流状态
        """
        # LangGraph配置（包含RuntimeContext）
        # is_resume=True 标志告知 human_review_node 跳过重复的 pending 状态写入
        config = {
            "configurable": {
                "thread_id": task_id,
                "runtime_context": self.runtime_context,
                "is_resume": True,
            }
        }
        
        # 使用Command(resume=...)来恢复工作流
        resume_value = {
            "approved": approved,
            "feedback": feedback or "",
        }
        
        logger.info(
            "resume_after_human_review",
            task_id=task_id,
            approved=approved,
            has_feedback=bool(feedback),
        )
        
        try:
            # ✅ 获取resume前的State（包含roadmap_id等关键信息）
            # ⚠️ 性能瓶颈点②：aget_state 需查询 PostgreSQL checkpoint 表并反序列化完整 state
            t_state1_start = time.time()
            state_before_resume = await self.graph.aget_state(config)
            final_state = state_before_resume.values if state_before_resume else {}
            node_start_times = {}
            
            logger.info(
                "resume_initial_state_loaded",
                task_id=task_id,
                roadmap_id=_safe_get(final_state, "roadmap_id"),
                current_step=_safe_get(final_state, "current_step"),
                aget_state_duration_ms=int((time.time() - t_state1_start) * 1000),
            )

            # ⚠️ 性能瓶颈点③：astream_events 内部会重新读取 checkpoint 并恢复完整图状态
            t_stream_start = time.time()
            logger.info(
                "resume_astream_events_starting",
                task_id=task_id,
                approved=approved,
            )

            async for event in self.graph.astream_events(
                Command(resume=resume_value),
                config=config,
                version="v2",
            ):
                event_type = event.get("event")
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")
                
                # 过滤出 LangGraph 节点事件
                if not node_name:
                    continue
                
                # ===== 节点开始事件 =====
                if event_type == "on_chain_start":
                    node_start_times[node_name] = time.time()
                    
                    logger.info(
                        "workflow_resume_node_starting",
                        task_id=task_id,
                        node=node_name,
                    )
                    
                    # 调用协调器处理副作用（更新current_step）
                    # ✅ 方案 A：edit_plan_analysis/roadmap_edit 开始时传递 edit_source，避免前端分支显示竞态
                    # ✅ 关键修复：resume 流程中 edit 节点必定来自 human_review 拒绝，直接使用 human_review
                    #    原因：LangGraph Command(resume=...) 可能先 emit edit_plan_analysis 的 on_chain_start，
                    #    再 emit human_review 的 on_chain_end，此时 final_state 仍是 checkpoint 旧值（validation_failed）
                    extra_data = None
                    if node_name in ("edit_plan_analysis", "roadmap_edit"):
                        extra_data = {"edit_source": "human_review"}
                    
                    await self.coordinator.on_node_start(
                        task_id=task_id,
                        node_name=node_name,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                        extra_data=extra_data,
                    )
                
                # ===== 节点结束事件 =====
                elif event_type == "on_chain_end":
                    start_time = node_start_times.pop(node_name, time.time())
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # 🔍 从 event data 中提取节点输出
                    node_output = event.get("data", {}).get("output", {})
                    
                    # ====================================================================
                    # 类型检查：只处理字典类型的输出（节点函数的状态更新）
                    # ====================================================================
                    # LangGraph astream_events 会为同一节点产生多个 on_chain_end 事件：
                    # 1. 内层 LLM/Agent 调用 → output 是 Pydantic 模型（如 IntentAnalysisOutput）
                    # 2. 节点函数返回 → output 是状态更新字典
                    # 
                    # Handler 只需要处理节点函数的最终返回（字典类型），跳过内层调用的返回。
                    # ====================================================================
                    if not isinstance(node_output, dict):
                        logger.debug(
                            "workflow_resume_skip_non_dict_output",
                            task_id=task_id,
                            node=node_name,
                            output_type=type(node_output).__name__,
                            reason="Only dict outputs (node state updates) are processed by handlers",
                        )
                        # 跳过非字典类型的输出（内层 LLM/Agent 调用的返回）
                        continue
                    
                    # 将 node_output 合并到本地 final_state，避免每次都查询 PostgreSQL checkpoint。
                    # node_output 是节点函数返回的状态增量，直接合并即可满足 coordinator 和 handler 的需求。
                    # ⚠️ 注意：只在流结束后（第571行）做一次 aget_state 确认最终状态。
                    final_state = {**final_state, **node_output}
                    
                    logger.info(
                        "workflow_resume_node_completed",
                        task_id=task_id,
                        node=node_name,
                        duration_ms=duration_ms,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                    )
                    
                    # ===== 副作用统一处理 =====
                    try:
                        # ✅ 使用 node_output（Node返回值）作为Handler输入
                        handler_input = _deep_convert_to_dict(node_output)
                        
                        async with get_celery_session() as session:
                            await self.handler_registry.handle(
                                node_name=node_name,
                                output=handler_input,
                                task_id=task_id,
                                session=session,
                            )
                        
                        # 2. 统一处理副作用（协调器）
                        await self.coordinator.on_node_complete(
                            task_id=task_id,
                            node_name=node_name,
                            output=final_state,
                            duration_ms=duration_ms,
                        )
                        
                    except Exception as e:
                        logger.error(
                            "workflow_resume_handler_failed",
                            task_id=task_id,
                            node_name=node_name,
                            error=str(e),
                            error_type=type(e).__name__,
                            exc_info=True,
                        )
                    
                    # 3. 记录Prometheus指标
                    langgraph_node_duration.labels(
                        node_name=node_name,
                        status="success"
                    ).observe(duration_ms / 1000.0)
            
            t_stream_end = time.time()
            logger.info(
                "resume_astream_events_completed",
                task_id=task_id,
                stream_duration_ms=int((t_stream_end - t_stream_start) * 1000),
                final_step=_safe_get(final_state, "current_step"),
            )
            
            # ✅ 检查工作流是否被新的 interrupt 暂停（与 execute() 方法保持一致）
            # 场景：用户拒绝后，工作流经过 edit_plan_analysis → roadmap_edit 后，
            # 再次进入 human_review 并触发新的 interrupt，等待下一次用户审核。
            # 此时流结束但 final_state["current_step"] 仍是最后一个完成节点（roadmap_edit），
            # 需要检测到 interrupt 状态并修正 current_step，避免误判为 PARTIAL_FAILURE。
            # ⚠️ 性能瓶颈点④：第二次 aget_state，用于检测是否再次 interrupt
            t_state2_start = time.time()
            state_snapshot_after = await self.graph.aget_state(config)
            next_nodes_after = list(state_snapshot_after.next) if state_snapshot_after.next else []
            logger.info(
                "resume_aget_state_after_done",
                task_id=task_id,
                aget_state_duration_ms=int((time.time() - t_state2_start) * 1000),
                next_nodes=next_nodes_after,
            )
            
            if next_nodes_after:
                logger.info(
                    "workflow_resume_interrupted_again",
                    task_id=task_id,
                    next_nodes=next_nodes_after,
                    current_step=_safe_get(final_state, "current_step"),
                    message="工作流在 interrupt 处再次暂停",
                )
                
                if "human_review" in next_nodes_after:
                    final_state["current_step"] = "human_review"
                    # ✅ 修复前端状态不同步：
                    # 工作流再次 interrupt 在 human_review 时，LangGraph 不会触发 human_review 的
                    # on_chain_end 事件，导致前端最后收到的 WebSocket 通知是 roadmap_edit 完成。
                    # 必须主动推送 human_review pending 通知，否则前端需要刷新页面才能恢复正常状态。
                    await self.coordinator.on_workflow_interrupted_for_review(
                        task_id=task_id,
                        roadmap_id=_safe_get(final_state, "roadmap_id"),
                    )
            
            logger.info(
                "workflow_resumed_successfully",
                task_id=task_id,
                approved=approved,
                final_step=_safe_get(final_state, "current_step"),
            )
            
            # 工作流恢复完成，统一处理副作用
            await self.coordinator.on_workflow_complete(
                task_id=task_id,
                final_state=final_state,
            )
            
            # 刷新执行日志缓冲区
            await self.execution_logger.flush()
            logger.debug(
                "workflow_resume_logs_flushed",
                task_id=task_id,
            )
            
            return final_state
            
        except Exception as e:
            logger.error(
                "workflow_resume_failed",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # 工作流失败，统一处理副作用
            await self.coordinator.on_workflow_failed(
                task_id=task_id,
                error=e,
            )
            
            # 刷新日志
            await self.execution_logger.flush()
            
            raise
    
    def _create_initial_state(
        self,
        user_request: UserRequest,
        task_id: str,
    ) -> RoadmapState:
        """
        创建初始工作流状态
        
        Args:
            user_request: 用户请求
            task_id: 追踪 ID
            
        Returns:
            初始状态
        """
        return {
            "user_request": user_request,
            "task_id": task_id,
            "roadmap_id": None,  # 将在需求分析完成后生成
            "intent_analysis": None,
            "roadmap_framework": None,
            "validation_result": None,
            "tutorial_refs": {},
            "resource_refs": {},
            "quiz_refs": {},
            "failed_concepts": [],
            "current_step": "init",
            "modification_count": 0,
            "human_approved": False,
            "execution_history": [],
        }

