"""
工作流执行器

负责执行和恢复工作流：
- execute: 执行完整工作流
- resume_after_human_review: 在人工审核后恢复工作流
"""
import structlog
import time
from langgraph.types import Command
from prometheus_client import Histogram, Counter

from app.models.domain import UserRequest
from .base import RoadmapState
from .builder import WorkflowBuilder
from .state_manager import StateManager

logger = structlog.get_logger()

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
    工作流执行器
    
    负责执行和恢复 LangGraph 工作流。
    """
    
    def __init__(
        self,
        builder: WorkflowBuilder,
        state_manager: StateManager,
        checkpointer,
        execution_logger: "ExecutionLogger",
    ):
        """
        Args:
            builder: WorkflowBuilder 实例
            state_manager: StateManager 实例
            checkpointer: AsyncPostgresSaver 实例
            execution_logger: ExecutionLogger 实例（用于刷新日志缓冲区）
        """
        self.builder = builder
        self.state_manager = state_manager
        self.checkpointer = checkpointer
        self.execution_logger = execution_logger
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
        执行完整的工作流
        
        Args:
            user_request: 用户请求
            task_id: 追踪 ID
            pre_generated_roadmap_id: 预生成的路线图 ID（可选，用于加速前端跳转）
            
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
        
        # LangGraph 配置
        config = {"configurable": {"thread_id": task_id}}
        
        try:
            logger.info(
                "workflow_graph_streaming",
                task_id=task_id,
            )
            
            # 使用 stream() 替换 ainvoke() 实现实时监控
            # stream_mode="updates" 返回每个节点的输出
            final_state = None
            async for chunk in self.graph.astream(
                initial_state, 
                config=config, 
                stream_mode="updates"
            ):
                # chunk 格式: {node_name: node_output}
                node_name = list(chunk.keys())[0] if chunk else None
                node_output = list(chunk.values())[0] if chunk else None
                
                if node_name and node_output:
                    # 记录 Prometheus 指标（节点执行成功）
                    # 注意：这里记录的是节点完成，不是执行时长
                    # 执行时长需要在节点开始和结束时分别记录
                    langgraph_node_duration.labels(
                        node_name=node_name,
                        status="success"
                    ).observe(0)  # 这里无法准确测量，仅标记成功
                    
                    logger.info(
                        "workflow_node_completed",
                        task_id=task_id,
                        node=node_name,
                    )
                    
                    # 旁路记录业务日志（不侵入 Graph 代码）
                    from app.services.execution_logger import execution_logger, LogCategory
                    await execution_logger.info(
                        task_id=task_id,
                        category=LogCategory.WORKFLOW,
                        step=node_name,
                        message=f"Node {node_name} completed",
                        details={"node_output_keys": list(node_output.keys()) if isinstance(node_output, dict) else None},
                    )
                    
                    # 更新最终状态
                    final_state = node_output if isinstance(node_output, dict) else final_state
            
            # 如果 stream 未产生任何输出，使用 initial_state
            if final_state is None:
                final_state = initial_state
            
            logger.info(
                "workflow_execution_completed",
                task_id=task_id,
                final_step=final_state.get("current_step") if isinstance(final_state, dict) else None,
                roadmap_id=final_state.get("roadmap_id") if isinstance(final_state, dict) else None,
            )
            
            # 清除 live_step 缓存（Redis）
            await self.state_manager.clear_live_step(task_id)
            
            # 刷新执行日志缓冲区
            await self.execution_logger.flush()
            logger.debug(
                "workflow_execution_logs_flushed",
                task_id=task_id,
            )
            
            return final_state
            
        except Exception as e:
            # 记录 Prometheus 指标（工作流失败）
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
            
            # 清除 live_step 缓存（Redis）
            await self.state_manager.clear_live_step(task_id)
            
            # 关键修复：即使失败也要刷新日志，确保错误日志被记录
            await self.execution_logger.flush()
            
            raise
    
    async def resume_after_human_review(
        self,
        task_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> RoadmapState:
        """
        在人工审核后恢复工作流
        
        使用 Command(resume=...) 来恢复被 interrupt() 暂停的工作流。
        
        Args:
            task_id: 追踪 ID
            approved: 是否批准
            feedback: 可选的反馈信息（当拒绝时）
            
        Returns:
            最终的工作流状态
        """
        config = {"configurable": {"thread_id": task_id}}
        
        # 使用 Command(resume=...) 来恢复工作流
        # resume 的值将作为 interrupt() 函数的返回值
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
            final_state = await self.graph.ainvoke(
                Command(resume=resume_value),
                config=config,
            )
            
            logger.info(
                "workflow_resumed_successfully",
                task_id=task_id,
                approved=approved,
                final_step=final_state.get("current_step"),
            )
            
            # 关键修复：刷新执行日志缓冲区，确保恢复后的所有日志都被写入
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
            
            # 关键修复：即使恢复失败也要刷新日志
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

