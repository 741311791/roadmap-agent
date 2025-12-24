"""
工作流构建器

负责构建 LangGraph 工作流图，定义节点和边。

工作流结构：
START → intent_analysis → curriculum_design 
      → [structure_validation ↔ roadmap_edit] 
      → human_review 
      → tutorial_generation 
      → END
"""
import structlog
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .base import RoadmapState, WorkflowConfig
from .routers import WorkflowRouter

logger = structlog.get_logger()


class WorkflowBuilder:
    """
    工作流构建器
    
    负责根据配置构建 LangGraph 工作流图。
    """
    
    def __init__(
        self,
        config: WorkflowConfig,
        router: WorkflowRouter,
        # Node runners - 将在任务1.4中实现
        intent_runner=None,
        curriculum_runner=None,
        validation_runner=None,
        editor_runner=None,
        review_runner=None,
        content_runner=None,
        edit_plan_runner=None,  # 修改计划分析节点（人工审核触发）
        validation_edit_plan_runner=None,  # 验证结果修改计划分析节点（验证失败触发）
    ):
        self.config = config
        self.router = router
        
        # Node runners
        self.intent_runner = intent_runner
        self.curriculum_runner = curriculum_runner
        self.validation_runner = validation_runner
        self.editor_runner = editor_runner
        self.review_runner = review_runner
        self.content_runner = content_runner
        self.edit_plan_runner = edit_plan_runner
        self.validation_edit_plan_runner = validation_edit_plan_runner  # 新增
    
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
            skip_structure_validation=self.config.skip_structure_validation,
            skip_human_review=self.config.skip_human_review,
            skip_tutorial_generation=self.config.skip_tutorial_generation,
            skip_resource_recommendation=self.config.skip_resource_recommendation,
            skip_quiz_generation=self.config.skip_quiz_generation,
        )
        
        workflow = StateGraph(RoadmapState)
        
        # 添加节点
        self._add_nodes(workflow)
        
        # 定义边（流程控制）
        self._add_edges(workflow)
        
        # 编译工作流（使用 AsyncPostgresSaver 进行状态持久化）
        return workflow.compile(checkpointer=checkpointer)
    
    def _add_nodes(self, workflow: StateGraph):
        """添加工作流节点"""
        # 核心节点（始终添加）
        if self.intent_runner:
            workflow.add_node("intent_analysis", self.intent_runner.run)
        if self.curriculum_runner:
            workflow.add_node("curriculum_design", self.curriculum_runner.run)
        
        # 可选节点：结构验证和路线图编辑
        if not self.config.skip_structure_validation:
            if self.validation_runner:
                workflow.add_node("structure_validation", self.validation_runner.run)
            if self.editor_runner:
                workflow.add_node("roadmap_edit", self.editor_runner.run)
            # 新增：验证结果修改计划分析节点（验证失败时触发）
            if self.validation_edit_plan_runner:
                workflow.add_node("validation_edit_plan_analysis", self.validation_edit_plan_runner.run)
        
        # 可选节点：人工审核
        if not self.config.skip_human_review:
            if self.review_runner:
                workflow.add_node("human_review", self.review_runner.run)
            # 新增：修改计划分析节点（仅在有人工审核时添加）
            if self.edit_plan_runner:
                workflow.add_node("edit_plan_analysis", self.edit_plan_runner.run)
        
        # 可选节点：教程生成
        if not self.config.skip_tutorial_generation:
            if self.content_runner:
                workflow.add_node("tutorial_generation", self.content_runner.run)
    
    def _add_edges(self, workflow: StateGraph):
        """定义工作流边（流程控制）"""
        # 设置入口点
        workflow.set_entry_point("intent_analysis")
        
        # 固定边
        workflow.add_edge("intent_analysis", "curriculum_design")
        
        # 根据配置构建不同的流程路径
        if self.config.skip_structure_validation:
            # 跳过结构验证：课程设计 → 人工审核/教程生成/结束
            self._add_edges_skip_validation(workflow)
        else:
            # 正常流程：课程设计 → 结构验证
            self._add_edges_with_validation(workflow)
    
    def _add_edges_skip_validation(self, workflow: StateGraph):
        """添加跳过结构验证的边"""
        if self.config.skip_human_review:
            if self.config.skip_tutorial_generation:
                workflow.add_edge("curriculum_design", END)
            else:
                workflow.add_edge("curriculum_design", "tutorial_generation")
                workflow.add_edge("tutorial_generation", END)
        else:
            workflow.add_edge("curriculum_design", "human_review")
            self._add_human_review_edges(workflow)
    
    def _add_edges_with_validation(self, workflow: StateGraph):
        """
        添加包含结构验证的边
        
        重构后的流程：
        structure_validation → [失败] → validation_edit_plan_analysis → roadmap_edit → structure_validation
        structure_validation → [通过] → human_review / tutorial_generation / END
        """
        # 课程设计 → 结构验证
        workflow.add_edge("curriculum_design", "structure_validation")
        
        # 结构验证后的条件路由
        workflow.add_conditional_edges(
            "structure_validation",
            self.router.route_after_validation,
            {
                # 重构：验证失败后先进入修改计划分析
                "validation_edit_plan_analysis": "validation_edit_plan_analysis",
                "human_review": "human_review"
                if not self.config.skip_human_review
                else (
                    "tutorial_generation"
                    if not self.config.skip_tutorial_generation
                    else END
                ),
                "tutorial_generation": "tutorial_generation"
                if not self.config.skip_tutorial_generation
                else END,
                "end": END,
            },
        )
        
        # 新增：验证结果修改计划分析 → 路线图编辑
        if self.validation_edit_plan_runner:
            workflow.add_edge("validation_edit_plan_analysis", "roadmap_edit")
        
        # 路线图编辑后的条件路由：
        # - 如果编辑来源是 "human_review"，直接返回人工审核
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
        
        # 教程生成完成后结束
        if not self.config.skip_tutorial_generation:
            workflow.add_edge("tutorial_generation", END)
    
    def _add_human_review_edges(self, workflow: StateGraph):
        """
        添加人工审核节点的边
        
        新流程（当用户拒绝时）：
        human_review → edit_plan_analysis → roadmap_edit → human_review
        
        注意：roadmap_edit 后的路由由 route_after_edit() 根据 edit_source 决定：
        - edit_source="human_review" → 返回 human_review（用户反馈触发的修改）
        - edit_source="validation_failed" → 返回 structure_validation（验证失败触发的修改）
        """
        # 确定用户拒绝后的下一个节点
        # 正常流程：edit_plan_runner 存在 → 进入修改计划分析
        if self.edit_plan_runner:
            modify_next_node = "edit_plan_analysis"
        elif not self.config.skip_structure_validation:
            # Fallback 1：无 edit_plan_runner 但有 validation → 直接编辑
            modify_next_node = "roadmap_edit"
        else:
            # Fallback 2：无 edit_plan_runner 且无 validation（极端边缘情况）
            # 注意：当前 OrchestratorFactory 始终提供 edit_plan_runner，此分支不会触发
            # 保留作为防御性代码，避免配置异常时工作流崩溃
            modify_next_node = "curriculum_design" if not self.config.skip_tutorial_generation else END
        
        if self.config.skip_tutorial_generation:
            workflow.add_conditional_edges(
                "human_review",
                self.router.route_after_human_review,
                {
                    "approved": END,
                    "modify": modify_next_node,
                    "end": END,
                },
            )
        else:
            workflow.add_conditional_edges(
                "human_review",
                self.router.route_after_human_review,
                {
                    "approved": "tutorial_generation",
                    "modify": modify_next_node,
                    "end": END,
                },
            )
        
        # 新增：edit_plan_analysis → roadmap_edit 的边
        if self.edit_plan_runner and not self.config.skip_structure_validation:
            workflow.add_edge("edit_plan_analysis", "roadmap_edit")

