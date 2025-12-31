"""
工作流执行器

负责执行和恢复工作流：
- execute: 执行完整工作流
- resume_after_human_review: 在人工审核后恢复工作流
"""
import structlog
from langgraph.types import Command

from app.models.domain import UserRequest
from .base import RoadmapState
from .builder import WorkflowBuilder
from .state_manager import StateManager

logger = structlog.get_logger()


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
                "workflow_graph_invoking",
                task_id=task_id,
            )
            
            # 执行工作流
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            logger.info(
                "workflow_execution_completed",
                task_id=task_id,
                final_step=final_state.get("current_step"),
                roadmap_id=final_state.get("roadmap_id"),
            )
            
            # 清除 live_step 缓存
            self.state_manager.clear_live_step(task_id)
            
            # 关键修复：刷新执行日志缓冲区，确保所有日志都被写入
            # 场景：工作流快速暂停（如 human_review interrupt）时，日志可能还在缓冲区中
            await self.execution_logger.flush()
            logger.debug(
                "workflow_execution_logs_flushed",
                task_id=task_id,
            )
            
            return final_state
            
        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # 清除 live_step 缓存
            self.state_manager.clear_live_step(task_id)
            
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

