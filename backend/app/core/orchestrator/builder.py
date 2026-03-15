"""
工作流构建器

负责构建 LangGraph 工作流图，定义节点和边。

工作流结构（优化版 - 内容生成已独立）：
START → intent_analysis → curriculum_design 
      → [structure_validation ↔ roadmap_edit] 
      → human_review 
      → END
      
注意：内容生成已从主工作流中移除，改为独立的 Celery Worker。
框架完成后，在 human_review 通过时触发内容生成任务。
"""
import structlog
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .base import RoadmapState, WorkflowConfig
from .routers import WorkflowRouter
from .retry_policies import LLM_RETRY_POLICY, NO_RETRY_POLICY

logger = structlog.get_logger()


class WorkflowBuilder:
    """
    工作流构建器（重构版 - 纯函数Node）
    
    负责根据配置构建 LangGraph 工作流图。
    
    重构改进：
    - 接受纯函数 Node 替代 Runner 类
    - Node 通过 config 获取依赖（RuntimeContext）
    """
    
    def __init__(
        self,
        config: WorkflowConfig,
        router: WorkflowRouter,
        # 纯函数 Node
        intent_node=None,
        curriculum_node=None,
        validation_node=None,
        editor_node=None,
        review_node=None,
        edit_plan_node=None,
        auto_content_node=None,  # 极速模式：跳过人工审查直接触发内容生成
    ):
        self.config = config
        self.router = router
        
        # 纯函数 Node
        self.intent_node = intent_node
        self.curriculum_node = curriculum_node
        self.validation_node = validation_node
        self.editor_node = editor_node
        self.review_node = review_node
        self.edit_plan_node = edit_plan_node
        self.auto_content_node = auto_content_node
    
    def build(self, checkpointer) -> CompiledStateGraph:
        """
        构建并编译工作流图
        
        Args:
            checkpointer: AsyncPostgresSaver 实例，用于状态持久化
            
        Returns:
            CompiledStateGraph: 编译后的工作流图
        """
        # 记录工作流配置
        logger.info(
            "workflow_config",
            skip_human_review=self.config.skip_human_review,
            max_framework_retry=self.config.max_framework_retry,
        )
        
        workflow = StateGraph(RoadmapState)
        
        # 添加节点
        self._add_nodes(workflow)
        
        # 定义边（流程控制）
        self._add_edges(workflow)
        
        # 编译工作流（使用 AsyncPostgresSaver 进行状态持久化）
        # ✅ 修复：不使用 interrupt_before，因为 human_review 节点内部已经使用了 interrupt() API
        # 使用 interrupt_before 会导致节点在执行前就中断，ReviewHandler.on_start() 不会被调用，
        # 因此前端无法收到 human_review_required 通知，UI 不会更新
        return workflow.compile(
            checkpointer=checkpointer,
        )
    
    def _add_nodes(self, workflow: StateGraph):
        """
        添加工作流节点（含 RetryPolicy）
        
        重构版：
        - 使用纯函数 Node 替代 Runner 类
        - Node 通过 config 获取依赖（RuntimeContext）
        - LLM 调用节点使用 LLM_RETRY_POLICY（5 次重试）
        - 纯逻辑节点使用 NO_RETRY_POLICY（不重试）
        """
        # 核心节点（始终添加）
        if self.intent_node:
            workflow.add_node(
                "intent_analysis",
                self.intent_node,
                retry_policy=LLM_RETRY_POLICY,
            )
        if self.curriculum_node:
            workflow.add_node(
                "curriculum_design",
                self.curriculum_node,
                retry_policy=LLM_RETRY_POLICY,
            )
        
        # 结构验证和路线图编辑（始终添加）
        if self.validation_node:
            workflow.add_node(
                "structure_validation",
                self.validation_node,
                retry_policy=NO_RETRY_POLICY,  # 纯逻辑节点
            )
        # ✅ 共享的编辑计划分析节点（validation和review都使用此节点，由edit_source区分）
        if self.edit_plan_node:
            workflow.add_node(
                "edit_plan_analysis",
                self.edit_plan_node,
                retry_policy=LLM_RETRY_POLICY,
            )
        
        # ✅ 共享的路线图编辑节点（由edit_source区分来源）
        if self.editor_node:
            workflow.add_node(
                "roadmap_edit",
                self.editor_node,
                retry_policy=LLM_RETRY_POLICY,
            )
        
        # 可选节点：人工审核（普通模式使用）
        if not self.config.skip_human_review and self.review_node:
            workflow.add_node(
                "human_review",
                self.review_node,
                retry_policy=NO_RETRY_POLICY,  # 使用 interrupt
            )

        # 极速模式专用节点：跳过人工审查，直接触发内容生成入队
        if self.auto_content_node:
            workflow.add_node(
                "auto_content_generation",
                self.auto_content_node,
                retry_policy=NO_RETRY_POLICY,
            )
    
    def _add_edges(self, workflow: StateGraph):
        """
        定义工作流边（流程控制）

        流程说明：
        - 极速模式：intent_analysis → curriculum_design → auto_content_generation → END
        - 普通模式：intent_analysis → curriculum_design → structure_validation
          → [验证循环] → human_review（可选） → END
        """
        # 设置入口点
        workflow.set_entry_point("intent_analysis")

        # 固定边：Intent → Curriculum
        workflow.add_edge("intent_analysis", "curriculum_design")

        # 课程设计后的条件路由：
        # - 极速模式 → auto_content_generation（跳过验证和人工审查）
        # - 普通模式 → structure_validation
        workflow.add_conditional_edges(
            "curriculum_design",
            self.router.route_after_curriculum,
            {
                "auto_content_generation": "auto_content_generation",
                "structure_validation": "structure_validation",
            },
        )

        # 极速模式：自动内容生成节点完成后直接结束主工作流
        if self.auto_content_node:
            workflow.add_edge("auto_content_generation", END)
        
        # 结构验证后的条件路由
        workflow.add_conditional_edges(
            "structure_validation",
            self.router.route_after_validation,
            {
                # ✅ 验证失败后进入共享的编辑计划分析节点（edit_source会被设置为validation_failed）
                "edit_plan_analysis": "edit_plan_analysis",
                # 验证通过后进入人工审核（或直接结束主工作流）
                "human_review": "human_review" if not self.config.skip_human_review else END,
                # ✅ 主工作流结束（等待内容生成）
                "end": END,
            },
        )
        
        # ✅ 编辑计划分析 → 路线图编辑（validation和review都使用此边）
        if self.edit_plan_node:
            workflow.add_edge("edit_plan_analysis", "roadmap_edit")
        
        # 路线图编辑后的条件路由：
        # - 如果编辑来源是 "human_review"，直接返回人工审核（或结束）
        # - 如果编辑来源是 "validation_failed"，返回结构验证
        workflow.add_conditional_edges(
            "roadmap_edit",
            self.router.route_after_edit,
            {
                "human_review": "human_review" if not self.config.skip_human_review else END,
                "structure_validation": "structure_validation",
            },
        )
        
        # 人工审核后路由
        if not self.config.skip_human_review:
            self._add_human_review_edges(workflow)
        
        # ✅ 移除内容生成相关的边（已独立为 Celery Worker）
        # 工作流在 human_review 通过后直接结束，内容生成由 review_node 触发 Celery 任务
    
    def _add_human_review_edges(self, workflow: StateGraph):
        """
        添加人工审核节点的边
        
        流程（当用户拒绝时）：
        human_review → edit_plan_analysis → roadmap_edit → human_review
        
        注意：roadmap_edit 后的路由由 route_after_edit() 根据 edit_source 决定：
        - edit_source="human_review" → 返回 human_review（用户反馈触发的修改）
        - edit_source="validation_failed" → 返回 structure_validation（验证失败触发的修改）
        """
        # 确定用户拒绝后的下一个节点
        # 正常流程：edit_plan_node 存在 → 进入修改计划分析
        if self.edit_plan_node:
            modify_next_node = "edit_plan_analysis"
        else:
            # Fallback：无 edit_plan_node → 直接编辑
            modify_next_node = "roadmap_edit"
        
        # 人工审核后的条件路由
        workflow.add_conditional_edges(
            "human_review",
            self.router.route_after_human_review,
            {
                # ✅ 批准后直接结束工作流（内容生成由 review_node 触发 Celery 任务）
                "approved": END,
                "modify": modify_next_node,  # 拒绝后进入修改流程
                "end": END,
            },
        )
        
        # edit_plan_analysis → roadmap_edit 的边
        if self.edit_plan_node:
            workflow.add_edge("edit_plan_analysis", "roadmap_edit")

