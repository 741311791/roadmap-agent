"""
LangGraph 工作流编排器

工作流节点控制说明：
- 核心 Agent（不可跳过）：Intent Analyzer、Curriculum Architect
- 内容生成 Agent（可通过环境变量跳过）：
  - SKIP_TUTORIAL_GENERATION: 跳过教程生成（Tutorial Generator）
  - SKIP_RESOURCE_RECOMMENDATION: 跳过资源推荐（Resource Recommender）
  - SKIP_QUIZ_GENERATION: 跳过测验生成（Quiz Generator）
- 流程控制 Agent（可通过环境变量跳过）：
  - SKIP_STRUCTURE_VALIDATION: 跳过 Structure Validator + Roadmap Editor
  - SKIP_HUMAN_REVIEW: 跳过 Human Review

状态机流程（按时序图）：
START → A1(需求分析师) → A2(课程架构师) → Loop[A3(结构审查员) ↔ A2E(路线图编辑师)]
     → HUMAN_REVIEW_PENDING → [A4(教程生成器) || A5(资源推荐师) || A6(测验生成器)] → COMPLETED

LangGraph 最佳实践：
- 使用 Annotated + reducer 来处理列表类型的状态更新（追加而非覆盖）
- 使用 AsyncPostgresSaver 作为生产级 checkpointer
- 使用 interrupt() + Command(resume=...) 实现 Human-in-the-Loop
"""
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import interrupt, Command
import structlog
import asyncio

from app.models.domain import (
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    Concept,
    TutorialGenerationOutput,
    TutorialGenerationInput,
    ResourceRecommendationOutput,
    ResourceRecommendationInput,
    QuizGenerationOutput,
    QuizGenerationInput,
)
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.roadmap_editor import RoadmapEditorAgent
from app.agents.structure_validator import StructureValidatorAgent
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.agents.resource_recommender import ResourceRecommenderAgent
from app.agents.quiz_generator import QuizGeneratorAgent
from app.config.settings import settings
from app.services.notification_service import notification_service

logger = structlog.get_logger()


def merge_dicts(left: dict, right: dict) -> dict:
    """合并字典的 reducer 函数（用于 tutorial_refs）"""
    return {**left, **right}


class RoadmapState(TypedDict):
    """
    工作流全局状态
    
    LangGraph 最佳实践：
    - 使用 Annotated 配合 reducer 函数来处理列表和字典的更新
    - reducer 函数确保状态更新是追加/合并而非覆盖
    """
    # 输入
    user_request: UserRequest
    
    # 中间产出
    intent_analysis: IntentAnalysisOutput | None
    roadmap_framework: RoadmapFramework | None
    validation_result: ValidationOutput | None
    
    # 内容生成相关（A4: 教程生成器）
    # 使用 merge_dicts reducer 来合并教程引用
    tutorial_refs: Annotated[dict[str, TutorialGenerationOutput], merge_dicts]
    # 使用 add reducer 来追加失败的 concept_id
    failed_concepts: Annotated[list[str], add]
    
    # 资源推荐相关（A5: 资源推荐师）
    # 使用 merge_dicts reducer 来合并资源推荐
    resource_refs: Annotated[dict[str, ResourceRecommendationOutput], merge_dicts]
    
    # 测验生成相关（A6: 测验生成器）
    # 使用 merge_dicts reducer 来合并测验
    quiz_refs: Annotated[dict[str, QuizGenerationOutput], merge_dicts]
    
    # 流程控制
    current_step: str
    modification_count: int
    human_approved: bool
    
    # 元数据
    trace_id: str
    # 使用 add reducer 来追加执行历史
    execution_history: Annotated[list[str], add]


class RoadmapOrchestrator:
    """
    学习路线图生成的主编排器
    
    使用 AsyncPostgresSaver 进行状态持久化，支持：
    - 完全异步：使用 psycopg 异步连接池
    - 持久化：状态存储在 PostgreSQL
    - 分布式：所有后端实例共享同一个数据库
    - Human-in-the-Loop：支持人工审核流程
    """
    
    _checkpointer: AsyncPostgresSaver | None = None
    _checkpointer_cm = None  # 上下文管理器引用，用于正确关闭
    _initialized: bool = False
    
    def __init__(self):
        self._live_step_cache: dict[str, str] = {}  # trace_id -> current_step (内存缓存)
        self._graph: CompiledStateGraph | None = None  # 编译后的工作流图
    
    @classmethod
    async def initialize(cls) -> None:
        """
        初始化 Orchestrator（应用启动时调用一次）
        
        使用 from_conn_string 创建 checkpointer，自动处理连接池和 autocommit 模式
        """
        if cls._initialized:
            logger.info("orchestrator_already_initialized")
            return
        
        logger.info(
            "orchestrator_initializing",
            checkpointer_type="AsyncPostgresSaver",
            database=settings.POSTGRES_DB,
        )
        
        # 使用 from_conn_string 创建 AsyncPostgresSaver
        # 添加 TCP keepalive 参数以防止长时间空闲后连接被关闭
        conn_string = settings.CHECKPOINTER_DATABASE_URL
        
        # 在连接字符串中添加 keepalive 参数
        separator = "&" if "?" in conn_string else "?"
        conn_string_with_keepalive = (
            f"{conn_string}{separator}"
            "keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"
        )
        
        cls._checkpointer_cm = AsyncPostgresSaver.from_conn_string(
            conn_string_with_keepalive
        )
        
        # 进入上下文管理器获取实际的 checkpointer 实例
        cls._checkpointer = await cls._checkpointer_cm.__aenter__()
        
        # 初始化数据库表结构（首次使用需要）
        # setup() 需要 autocommit 模式，from_conn_string 已经处理好了
        await cls._checkpointer.setup()
        
        cls._initialized = True
        logger.info("orchestrator_initialized", status="success")
    
    @classmethod
    async def shutdown(cls) -> None:
        """关闭 Orchestrator（应用关闭时调用）"""
        if cls._checkpointer_cm:
            await cls._checkpointer_cm.__aexit__(None, None, None)
        cls._checkpointer_cm = None
        cls._checkpointer = None
        cls._initialized = False
        logger.info("orchestrator_shutdown")
    
    @property
    def checkpointer(self) -> AsyncPostgresSaver:
        """获取 checkpointer 实例"""
        if not self._initialized or self._checkpointer is None:
            raise RuntimeError("Orchestrator 未初始化，请先调用 RoadmapOrchestrator.initialize()")
        return self._checkpointer
    
    @property
    def graph(self) -> CompiledStateGraph:
        """获取编译后的工作流图（延迟构建）"""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    def get_live_step(self, trace_id: str) -> str | None:
        """获取工作流的实时执行步骤（从内存缓存）"""
        return self._live_step_cache.get(trace_id)
    
    def _set_live_step(self, trace_id: str, step: str):
        """设置工作流的实时执行步骤"""
        self._live_step_cache[trace_id] = step
        logger.debug("live_step_updated", trace_id=trace_id, step=step)
    
    def _clear_live_step(self, trace_id: str):
        """清除工作流的实时执行步骤（工作流完成时调用）"""
        if trace_id in self._live_step_cache:
            del self._live_step_cache[trace_id]
    
    def _build_graph(self) -> CompiledStateGraph:
        """
        构建 LangGraph 工作流
        
        工作流结构（按时序图）：
        START → intent_analysis → curriculum_design → [structure_validation ↔ roadmap_edit]
              → human_review → tutorial_generation → END
              
        返回编译后的 CompiledStateGraph，配置了 AsyncPostgresSaver checkpointer
        """
        workflow = StateGraph(RoadmapState)
        
        # 记录工作流配置
        logger.info(
            "workflow_config",
            skip_structure_validation=settings.SKIP_STRUCTURE_VALIDATION,
            skip_human_review=settings.SKIP_HUMAN_REVIEW,
            skip_tutorial_generation=settings.SKIP_TUTORIAL_GENERATION,
            skip_resource_recommendation=settings.SKIP_RESOURCE_RECOMMENDATION,
            skip_quiz_generation=settings.SKIP_QUIZ_GENERATION,
        )
        
        # 核心节点（始终添加）
        workflow.add_node("intent_analysis", self._run_intent_analysis)
        workflow.add_node("curriculum_design", self._run_curriculum_design)
        
        # 可选节点：结构验证和路线图编辑
        if not settings.SKIP_STRUCTURE_VALIDATION:
            workflow.add_node("structure_validation", self._run_structure_validation)
            workflow.add_node("roadmap_edit", self._run_roadmap_edit)
        
        # 可选节点：人工审核
        if not settings.SKIP_HUMAN_REVIEW:
            workflow.add_node("human_review", self._run_human_review)
        
        # 可选节点：教程生成
        if not settings.SKIP_TUTORIAL_GENERATION:
            workflow.add_node("tutorial_generation", self._run_tutorial_generation)
        
        # 定义边（流程控制）
        workflow.set_entry_point("intent_analysis")
        workflow.add_edge("intent_analysis", "curriculum_design")
        
        # 根据配置构建不同的流程路径
        if settings.SKIP_STRUCTURE_VALIDATION:
            # 跳过结构验证：课程设计 → 人工审核/教程生成/结束
            if settings.SKIP_HUMAN_REVIEW:
                if settings.SKIP_TUTORIAL_GENERATION:
                    workflow.add_edge("curriculum_design", END)
                else:
                    workflow.add_edge("curriculum_design", "tutorial_generation")
                    workflow.add_edge("tutorial_generation", END)
            else:
                workflow.add_edge("curriculum_design", "human_review")
                self._add_human_review_edges(workflow)
        else:
            # 正常流程：课程设计 → 结构验证
            workflow.add_edge("curriculum_design", "structure_validation")
            
            # 结构验证后的条件路由
            workflow.add_conditional_edges(
                "structure_validation",
                self._route_after_validation,
                {
                    "edit_roadmap": "roadmap_edit",
                    "human_review": "human_review"
                    if not settings.SKIP_HUMAN_REVIEW
                    else (
                        "tutorial_generation"
                        if not settings.SKIP_TUTORIAL_GENERATION
                        else END
                    ),
                    "tutorial_generation": "tutorial_generation"
                    if not settings.SKIP_TUTORIAL_GENERATION
                    else END,
                    "end": END,
                },
            )
            
            # 路线图编辑后重新验证
            workflow.add_edge("roadmap_edit", "structure_validation")
            
            # 人工审核后路由
            if not settings.SKIP_HUMAN_REVIEW:
                self._add_human_review_edges(workflow)
            
            # 教程生成完成后结束
            if not settings.SKIP_TUTORIAL_GENERATION:
                workflow.add_edge("tutorial_generation", END)
        
        # 编译工作流（使用 AsyncPostgresSaver 进行状态持久化）
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _add_human_review_edges(self, workflow: StateGraph):
        """添加人工审核节点的边"""
        if settings.SKIP_TUTORIAL_GENERATION:
            workflow.add_conditional_edges(
                "human_review",
                self._route_after_human_review,
                {
                    "approved": END,
                    "modify": "roadmap_edit" if not settings.SKIP_STRUCTURE_VALIDATION else END,
                    "end": END,
                }
            )
        else:
            workflow.add_conditional_edges(
                "human_review",
                self._route_after_human_review,
                {
                    "approved": "tutorial_generation",
                    "modify": "roadmap_edit" if not settings.SKIP_STRUCTURE_VALIDATION else "curriculum_design",
                    "end": END,
                }
            )
    
    async def _run_intent_analysis(self, state: RoadmapState) -> dict:
        """Step 1: 需求分析（A1: 需求分析师）"""
        self._set_live_step(state["trace_id"], "intent_analysis")
        logger.info(
            "workflow_step_started",
            step="intent_analysis",
            trace_id=state["trace_id"],
            user_goal=state["user_request"].preferences.learning_goal[:50] if state["user_request"].preferences.learning_goal else "N/A",
        )
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="intent_analysis",
            status="processing",
            message="正在分析学习需求...",
        )
        
        try:
            agent = IntentAnalyzerAgent()
            result = await agent.analyze(state["user_request"])
            
            logger.info(
                "workflow_step_completed",
                step="intent_analysis",
                trace_id=state["trace_id"],
                key_technologies=result.key_technologies[:3] if result.key_technologies else [],
            )
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=state["trace_id"],
                step="intent_analysis",
                status="completed",
                message="需求分析完成",
                extra_data={"key_technologies": result.key_technologies[:5]},
            )
            
            # 使用 reducer 后，直接返回新条目（会自动追加）
            return {
                "intent_analysis": result,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],  # reducer 会自动追加
            }
        except Exception as e:
            logger.error(
                "workflow_step_failed",
                step="intent_analysis",
                trace_id=state["trace_id"],
                error=str(e),
                error_type=type(e).__name__,
            )
            # 发布失败通知
            await notification_service.publish_failed(
                task_id=state["trace_id"],
                error=str(e),
                step="intent_analysis",
            )
            raise
    
    async def _run_curriculum_design(self, state: RoadmapState) -> dict:
        """Step 2: 课程设计（A2: 课程架构师）"""
        self._set_live_step(state["trace_id"], "curriculum_design")
        logger.info(
            "workflow_step_started",
            step="curriculum_design",
            trace_id=state["trace_id"],
            has_intent_analysis=bool(state.get("intent_analysis")),
        )
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="curriculum_design",
            status="processing",
            message="正在设计学习路线图框架...",
        )
        
        try:
            agent = CurriculumArchitectAgent()
            logger.debug(
                "curriculum_design_agent_created",
                trace_id=state["trace_id"],
                model=agent.model_name,
                provider=agent.model_provider,
            )
            
            result = await agent.design(
                intent_analysis=state["intent_analysis"],
                user_preferences=state["user_request"].preferences,
            )
            
            logger.info(
                "workflow_step_completed",
                step="curriculum_design",
                trace_id=state["trace_id"],
                roadmap_id=result.framework.roadmap_id if result.framework else None,
                stages_count=len(result.framework.stages) if result.framework else 0,
            )
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=state["trace_id"],
                step="curriculum_design",
                status="completed",
                message="路线图框架设计完成",
                extra_data={
                    "roadmap_id": result.framework.roadmap_id if result.framework else None,
                    "stages_count": len(result.framework.stages) if result.framework else 0,
                },
            )
            
            # 使用 reducer 后，直接返回新条目
            return {
                "roadmap_framework": result.framework,
                "current_step": "curriculum_design",
                "execution_history": ["课程设计完成"],  # reducer 会自动追加
                "modification_count": state.get("modification_count", 0),
            }
        except Exception as e:
            logger.error(
                "workflow_step_failed",
                step="curriculum_design",
                trace_id=state["trace_id"],
                error=str(e),
                error_type=type(e).__name__,
            )
            await notification_service.publish_failed(
                task_id=state["trace_id"],
                error=str(e),
                step="curriculum_design",
            )
            raise
    
    async def _run_structure_validation(self, state: RoadmapState) -> dict:
        """Step 3: 结构验证（A3: 结构审查员）"""
        self._set_live_step(state["trace_id"], "structure_validation")
        logger.info(
            "workflow_step_started",
            step="structure_validation",
            trace_id=state["trace_id"],
            has_framework=bool(state.get("roadmap_framework")),
        )
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="structure_validation",
            status="processing",
            message="正在验证路线图结构...",
        )
        
        try:
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=state["roadmap_framework"],
                user_preferences=state["user_request"].preferences,
            )
            
            modification_count = state.get("modification_count", 0)
            history_message = f"结构验证完成 (有效性: {result.is_valid}, 评分: {result.overall_score})"
            
            if not result.is_valid and modification_count >= settings.MAX_FRAMEWORK_RETRY:
                next_step = "人工审核" if not settings.SKIP_HUMAN_REVIEW else (
                    "教程生成" if not settings.SKIP_TUTORIAL_GENERATION else "结束"
                )
                history_message += f" [已达到最大重试次数({settings.MAX_FRAMEWORK_RETRY})，将进入{next_step}]"
            
            logger.info(
                "workflow_step_completed",
                step="structure_validation",
                trace_id=state["trace_id"],
                is_valid=result.is_valid,
                overall_score=result.overall_score,
                issues_count=len(result.issues) if result.issues else 0,
            )
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=state["trace_id"],
                step="structure_validation",
                status="completed",
                message=f"结构验证完成（评分: {result.overall_score}）",
                extra_data={
                    "is_valid": result.is_valid,
                    "overall_score": result.overall_score,
                    "issues_count": len(result.issues) if result.issues else 0,
                },
            )
            
            # 使用 reducer 后，直接返回新条目
            return {
                "validation_result": result,
                "current_step": "structure_validation",
                "execution_history": [history_message],  # reducer 会自动追加
            }
        except Exception as e:
            logger.error(
                "workflow_step_failed",
                step="structure_validation",
                trace_id=state["trace_id"],
                error=str(e),
                error_type=type(e).__name__,
            )
            await notification_service.publish_failed(
                task_id=state["trace_id"],
                error=str(e),
                step="structure_validation",
            )
            raise
    
    def _route_after_validation(self, state: RoadmapState) -> str:
        """
        验证后的路由逻辑
        
        路由规则：
        1. 验证失败且未达到最大重试次数 → 编辑路线图 (A2E)
        2. 验证失败且达到最大重试次数 → 人工审核（或跳过）
        3. 验证通过 → 人工审核（或跳过）→ 教程生成（或结束）
        """
        validation_result = state.get("validation_result")
        modification_count = state.get("modification_count", 0)
        
        if not validation_result or not validation_result.is_valid:
            if modification_count < settings.MAX_FRAMEWORK_RETRY:
                logger.info(
                    "validation_failed_retry",
                    attempt=modification_count + 1,
                    max_retries=settings.MAX_FRAMEWORK_RETRY,
                    trace_id=state["trace_id"],
                    message="验证未通过，将使用 RoadmapEditor 进行修改",
                )
                return "edit_roadmap"
            else:
                logger.warning(
                    "validation_failed_max_retries_exceeded",
                    modification_count=modification_count,
                    max_retries=settings.MAX_FRAMEWORK_RETRY,
                    trace_id=state["trace_id"],
                    message="已达到最大重试次数，继续后续流程",
                )
        
        return self._get_next_step_after_validation(state)
    
    def _get_next_step_after_validation(self, state: RoadmapState) -> str:
        """验证后获取下一步骤"""
        if settings.SKIP_HUMAN_REVIEW:
            if settings.SKIP_TUTORIAL_GENERATION:
                logger.info(
                    "skipping_to_end",
                    trace_id=state["trace_id"],
                    reason="skip_human_review_and_tutorial",
                )
                return "end"
            else:
                logger.info("skipping_human_review", trace_id=state["trace_id"])
                return "tutorial_generation"
        else:
            return "human_review"
    
    async def _run_roadmap_edit(self, state: RoadmapState) -> dict:
        """Step 3b: 路线图编辑（A2E: 路线图编辑师）"""
        self._set_live_step(state["trace_id"], "roadmap_edit")
        logger.info("workflow_step_started", step="roadmap_edit", trace_id=state["trace_id"])
        
        roadmap_framework = state.get("roadmap_framework")
        validation_result = state.get("validation_result")
        
        if not roadmap_framework:
            raise ValueError("路线图框架不存在，无法进行修改")
        if not validation_result:
            raise ValueError("验证结果不存在，无法进行修改")
        
        modification_count = state.get("modification_count", 0)
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="roadmap_edit",
            status="processing",
            message=f"正在修正路线图结构（第{modification_count + 1}次修改）...",
        )
        
        agent = RoadmapEditorAgent()
        
        result = await agent.edit(
            existing_framework=roadmap_framework,
            validation_issues=validation_result.issues,
            user_preferences=state["user_request"].preferences,
            modification_count=modification_count,
        )
        
        logger.info(
            "roadmap_edit_completed",
            roadmap_id=result.framework.roadmap_id,
            modification_count=modification_count + 1,
            issues_resolved=len(validation_result.issues),
            trace_id=state["trace_id"],
        )
        
        # 发布步骤完成通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="roadmap_edit",
            status="completed",
            message=f"路线图修改完成（第{modification_count + 1}次）",
            extra_data={"modification_count": modification_count + 1},
        )
        
        # 使用 reducer 后，直接返回新条目
        return {
            "roadmap_framework": result.framework,
            "current_step": "roadmap_edit",
            "modification_count": modification_count + 1,
            "execution_history": [
                f"路线图修改完成（第{modification_count + 1}次修改）：{result.modification_summary}"
            ],  # reducer 会自动追加
        }
    
    async def _run_human_review(self, state: RoadmapState) -> dict:
        """
        Step 4: 人工审核（Human-in-the-Loop）
        
        使用 LangGraph 的 interrupt() 机制暂停工作流等待人工审核。
        恢复时需要使用 Command(resume={"approved": True/False}) 来提供审核结果。
        """
        self._set_live_step(state["trace_id"], "human_review")
        logger.info("workflow_step_started", step="human_review", trace_id=state["trace_id"])
        
        # 准备需要审核的内容
        roadmap_framework = state.get("roadmap_framework")
        review_payload = {
            "trace_id": state["trace_id"],
            "roadmap_title": roadmap_framework.title if roadmap_framework else "N/A",
            "roadmap_id": roadmap_framework.roadmap_id if roadmap_framework else "N/A",
            "stages_count": len(roadmap_framework.stages) if roadmap_framework else 0,
            "message": "请审核此路线图框架",
        }
        
        logger.info(
            "human_review_interrupt_starting",
            trace_id=state["trace_id"],
            roadmap_id=review_payload.get("roadmap_id"),
        )
        
        # 发布人工审核请求通知（关键：主动推送给用户）
        await notification_service.publish_human_review_required(
            task_id=state["trace_id"],
            roadmap_id=roadmap_framework.roadmap_id if roadmap_framework else "N/A",
            roadmap_title=roadmap_framework.title if roadmap_framework else "N/A",
            stages_count=len(roadmap_framework.stages) if roadmap_framework else 0,
        )
        
        # 使用 interrupt() 暂停工作流，等待人工审核
        # 返回值将是通过 Command(resume=...) 提供的审核结果
        human_response = interrupt(review_payload)
        
        # 处理人工审核结果
        approved = human_response.get("approved", False) if isinstance(human_response, dict) else bool(human_response)
        feedback = human_response.get("feedback", "") if isinstance(human_response, dict) else ""
        
        logger.info(
            "human_review_completed",
            trace_id=state["trace_id"],
            approved=approved,
            has_feedback=bool(feedback),
        )
        
        # 发布审核结果通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="human_review",
            status="completed",
            message="人工审核已通过" if approved else "人工审核被拒绝，将重新修改",
            extra_data={"approved": approved, "feedback": feedback if feedback else None},
        )
        
        history_message = "人工审核已通过" if approved else f"人工审核被拒绝: {feedback}" if feedback else "人工审核被拒绝"
        
        # 使用 reducer 后，直接返回新条目
        return {
            "current_step": "human_review",
            "human_approved": approved,
            "execution_history": [history_message],  # reducer 会自动追加
        }
    
    def _route_after_human_review(self, state: RoadmapState) -> str:
        """
        人工审核后的路由逻辑
        
        路由规则：
        1. 用户批准 → 教程生成（或结束）
        2. 用户拒绝 → 编辑路线图 (A2E)
        """
        if state.get("human_approved", False):
            if settings.SKIP_TUTORIAL_GENERATION:
                logger.info("tutorial_generation_skipped", trace_id=state["trace_id"])
                return "end"
            return "approved"
        else:
            return "modify"
    
    def _extract_concepts_from_roadmap(
        self,
        framework: RoadmapFramework,
    ) -> list[tuple[Concept, dict]]:
        """从路线图框架中提取所有 Concepts 及其上下文信息"""
        concepts_with_context = []
        
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    context = {
                        "roadmap_id": framework.roadmap_id,
                        "stage_id": stage.stage_id,
                        "stage_name": stage.name,
                        "module_id": module.module_id,
                        "module_name": module.name,
                    }
                    concepts_with_context.append((concept, context))
        
        return concepts_with_context
    
    async def _run_tutorial_generation(self, state: RoadmapState) -> dict:
        """
        Step 5: 内容生成（并行执行 A4/A5/A6）
        
        按时序图，并行执行三个 Agent：
        - A4: 教程生成器 - 生成详细教程并上传到 S3
        - A5: 资源推荐师 - 搜索并推荐学习资源
        - A6: 测验生成器 - 生成测验题目
        
        每个 Agent 可通过环境变量单独跳过。
        """
        self._set_live_step(state["trace_id"], "content_generation")
        logger.info("workflow_step_started", step="content_generation", trace_id=state["trace_id"])
        
        framework = state.get("roadmap_framework")
        if not framework:
            raise ValueError("路线图框架不存在，无法生成内容")
        
        user_preferences = state["user_request"].preferences
        concepts_with_context = self._extract_concepts_from_roadmap(framework)
        
        # 计算启用的 Agent 数量
        enabled_agents = []
        if not settings.SKIP_TUTORIAL_GENERATION:
            enabled_agents.append("教程生成")
        if not settings.SKIP_RESOURCE_RECOMMENDATION:
            enabled_agents.append("资源推荐")
        if not settings.SKIP_QUIZ_GENERATION:
            enabled_agents.append("测验生成")
        
        # 发布内容生成开始通知
        await notification_service.publish_progress(
            task_id=state["trace_id"],
            step="content_generation",
            status="processing",
            message=f"开始生成内容（共 {len(concepts_with_context)} 个概念，启用: {', '.join(enabled_agents)}）...",
            extra_data={
                "total_concepts": len(concepts_with_context),
                "enabled_agents": enabled_agents,
            },
        )
        
        logger.info(
            "content_generation_started",
            concepts_count=len(concepts_with_context),
            enabled_agents=enabled_agents,
            trace_id=state["trace_id"],
        )
        
        # 获取已有数据（用于跳过）
        existing_tutorial_refs = state.get("tutorial_refs", {})
        existing_resource_refs = state.get("resource_refs", {})
        existing_quiz_refs = state.get("quiz_refs", {})
        
        # 新生成的数据（将被 reducer 合并/追加）
        new_tutorial_refs: dict[str, TutorialGenerationOutput] = {}
        new_resource_refs: dict[str, ResourceRecommendationOutput] = {}
        new_quiz_refs: dict[str, QuizGenerationOutput] = {}
        new_failed_concepts: list[str] = []
        
        # 创建 Agents
        tutorial_generator = TutorialGeneratorAgent() if not settings.SKIP_TUTORIAL_GENERATION else None
        resource_recommender = ResourceRecommenderAgent() if not settings.SKIP_RESOURCE_RECOMMENDATION else None
        quiz_generator = QuizGeneratorAgent() if not settings.SKIP_QUIZ_GENERATION else None
        
        async def generate_content_for_concept(
            concept: Concept,
            context: dict,
        ) -> dict:
            """为单个概念并行生成所有内容"""
            results = {
                "concept_id": concept.concept_id,
                "tutorial": None,
                "resources": None,
                "quiz": None,
                "errors": [],
            }
            
            # 准备并行任务
            tasks = []
            task_names = []
            
            # A4: 教程生成
            if tutorial_generator and concept.concept_id not in existing_tutorial_refs:
                # 使用默认参数捕获当前值，避免闭包问题
                async def gen_tutorial(c=concept, ctx=context):
                    try:
                        logger.debug(
                            "tutorial_generation_starting",
                            concept_id=c.concept_id,
                            concept_name=c.name,
                            trace_id=state["trace_id"],
                        )
                        input_data = TutorialGenerationInput(
                            concept=c,
                            context=ctx,
                            user_preferences=user_preferences,
                        )
                        result = await tutorial_generator.execute(input_data)
                        logger.info(
                            "tutorial_generation_success",
                            concept_id=c.concept_id,
                            tutorial_id=result.tutorial_id if result else None,
                            trace_id=state["trace_id"],
                        )
                        return result
                    except Exception as e:
                        logger.error(
                            "tutorial_generation_failed",
                            concept_id=c.concept_id,
                            error=str(e),
                            error_type=type(e).__name__,
                            trace_id=state["trace_id"],
                        )
                        return None
                tasks.append(gen_tutorial())
                task_names.append("tutorial")
            
            # A5: 资源推荐
            if resource_recommender and concept.concept_id not in existing_resource_refs:
                # 使用默认参数捕获当前值，避免闭包问题
                async def gen_resources(c=concept, ctx=context):
                    try:
                        logger.debug(
                            "resource_recommendation_starting",
                            concept_id=c.concept_id,
                            concept_name=c.name,
                            trace_id=state["trace_id"],
                        )
                        input_data = ResourceRecommendationInput(
                            concept=c,
                            context=ctx,
                            user_preferences=user_preferences,
                        )
                        result = await resource_recommender.execute(input_data)
                        logger.info(
                            "resource_recommendation_success",
                            concept_id=c.concept_id,
                            resources_id=result.id if result else None,
                            resources_count=len(result.resources) if result else 0,
                            trace_id=state["trace_id"],
                        )
                        return result
                    except Exception as e:
                        logger.error(
                            "resource_recommendation_failed",
                            concept_id=c.concept_id,
                            error=str(e),
                            error_type=type(e).__name__,
                            trace_id=state["trace_id"],
                        )
                        return None
                tasks.append(gen_resources())
                task_names.append("resources")
            
            # A6: 测验生成
            if quiz_generator and concept.concept_id not in existing_quiz_refs:
                # 使用默认参数捕获当前值，避免闭包问题
                async def gen_quiz(c=concept, ctx=context):
                    try:
                        logger.debug(
                            "quiz_generation_starting",
                            concept_id=c.concept_id,
                            concept_name=c.name,
                            trace_id=state["trace_id"],
                        )
                        input_data = QuizGenerationInput(
                            concept=c,
                            context=ctx,
                            user_preferences=user_preferences,
                        )
                        result = await quiz_generator.execute(input_data)
                        logger.info(
                            "quiz_generation_success",
                            concept_id=c.concept_id,
                            quiz_id=result.quiz_id if result else None,
                            questions_count=result.total_questions if result else 0,
                            trace_id=state["trace_id"],
                        )
                        return result
                    except Exception as e:
                        logger.error(
                            "quiz_generation_failed",
                            concept_id=c.concept_id,
                            error=str(e),
                            error_type=type(e).__name__,
                            trace_id=state["trace_id"],
                        )
                        return None
                tasks.append(gen_quiz())
                task_names.append("quiz")
            
            # 并行执行
            if tasks:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for name, result in zip(task_names, task_results):
                    if isinstance(result, Exception):
                        results["errors"].append(f"{name}: {str(result)}")
                    elif result is not None:
                        results[name] = result
            
            return results
        
        # 并发执行（限制并发数量）
        semaphore = asyncio.Semaphore(settings.PARALLEL_TUTORIAL_LIMIT)
        total_concepts = len(concepts_with_context)
        
        # 用于跟踪进度的计数器
        completed_count = 0
        failed_count = 0
        
        async def generate_with_limit(concept: Concept, context: dict, index: int):
            """带并发限制和进度通知的内容生成"""
            nonlocal completed_count, failed_count
            
            # 发布 concept_start 事件
            await notification_service.publish_concept_start(
                task_id=state["trace_id"],
                concept_id=concept.concept_id,
                concept_name=concept.name,
                current=index + 1,
                total=total_concepts,
            )
            
            async with semaphore:
                result = await generate_content_for_concept(concept, context)
            
            # 根据结果发布 concept_complete 或 concept_failed 事件
            if result["errors"]:
                failed_count += 1
                await notification_service.publish_concept_failed(
                    task_id=state["trace_id"],
                    concept_id=concept.concept_id,
                    concept_name=concept.name,
                    error="; ".join(result["errors"]),
                )
            else:
                completed_count += 1
                # 构建完成数据
                complete_data = {}
                if result["tutorial"]:
                    complete_data["tutorial_id"] = result["tutorial"].tutorial_id
                    complete_data["content_url"] = result["tutorial"].content_url
                if result["resources"]:
                    complete_data["resources_count"] = len(result["resources"].resources)
                if result["quiz"]:
                    complete_data["quiz_id"] = result["quiz"].quiz_id
                    complete_data["questions_count"] = result["quiz"].total_questions
                
                await notification_service.publish_concept_complete(
                    task_id=state["trace_id"],
                    concept_id=concept.concept_id,
                    concept_name=concept.name,
                    data=complete_data if complete_data else None,
                )
            
            return result
        
        # 创建所有任务（带索引）
        all_tasks = [
            generate_with_limit(concept, context, idx)
            for idx, (concept, context) in enumerate(concepts_with_context)
        ]
        
        # 执行所有任务
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # 处理结果
        for result in all_results:
            if isinstance(result, Exception):
                logger.error(
                    "content_generation_task_failed",
                    error=str(result),
                    error_type=type(result).__name__,
                    trace_id=state["trace_id"],
                )
                continue
            
            concept_id = result["concept_id"]
            
            # 记录每个 concept 的处理结果摘要
            logger.debug(
                "content_generation_result",
                concept_id=concept_id,
                has_tutorial=result["tutorial"] is not None,
                has_resources=result["resources"] is not None,
                has_quiz=result["quiz"] is not None,
                errors=result["errors"],
                trace_id=state["trace_id"],
            )
            
            # 收集教程结果
            if result["tutorial"]:
                new_tutorial_refs[concept_id] = result["tutorial"]
                logger.info(
                    "tutorial_collected",
                    concept_id=concept_id,
                    tutorial_id=result["tutorial"].tutorial_id,
                    content_url=result["tutorial"].content_url,
                    trace_id=state["trace_id"],
                )
            else:
                logger.warning(
                    "tutorial_missing",
                    concept_id=concept_id,
                    trace_id=state["trace_id"],
                )
            
            # 收集资源推荐结果
            if result["resources"]:
                new_resource_refs[concept_id] = result["resources"]
                logger.info(
                    "resources_collected",
                    concept_id=concept_id,
                    resources_id=result["resources"].id,
                    resources_count=len(result["resources"].resources),
                    trace_id=state["trace_id"],
                )
            else:
                logger.warning(
                    "resources_missing",
                    concept_id=concept_id,
                    trace_id=state["trace_id"],
                )
            
            # 收集测验结果
            if result["quiz"]:
                new_quiz_refs[concept_id] = result["quiz"]
                logger.info(
                    "quiz_collected",
                    concept_id=concept_id,
                    quiz_id=result["quiz"].quiz_id,
                    questions_count=result["quiz"].total_questions,
                    trace_id=state["trace_id"],
                )
            else:
                logger.warning(
                    "quiz_missing",
                    concept_id=concept_id,
                    trace_id=state["trace_id"],
                )
            
            # 记录失败
            if result["errors"]:
                new_failed_concepts.append(concept_id)
                logger.warning(
                    "content_generation_partial_failure",
                    concept_id=concept_id,
                    errors=result["errors"],
                    trace_id=state["trace_id"],
                )
        
        # 合并所有引用用于更新框架状态
        all_tutorial_refs = {**existing_tutorial_refs, **new_tutorial_refs}
        all_resource_refs = {**existing_resource_refs, **new_resource_refs}
        all_quiz_refs = {**existing_quiz_refs, **new_quiz_refs}
        
        # 更新路线图框架中的 Concept 状态（包括教程、资源、测验）
        updated_framework = self._update_concept_statuses(
            framework=framework,
            tutorial_refs=all_tutorial_refs,
            resource_refs=all_resource_refs,
            quiz_refs=all_quiz_refs,
        )
        
        # 记录详细的收集结果统计
        logger.info(
            "content_generation_completed",
            total_concepts=len(concepts_with_context),
            tutorials_count=len(new_tutorial_refs),
            tutorials_concept_ids=list(new_tutorial_refs.keys()),
            resources_count=len(new_resource_refs),
            resources_concept_ids=list(new_resource_refs.keys()),
            quizzes_count=len(new_quiz_refs),
            quizzes_concept_ids=list(new_quiz_refs.keys()),
            failed_count=len(new_failed_concepts),
            failed_concept_ids=new_failed_concepts,
            trace_id=state["trace_id"],
        )
        
        # 检查是否有数据丢失
        all_concept_ids = [c.concept_id for c, _ in concepts_with_context]
        missing_tutorials = set(all_concept_ids) - set(new_tutorial_refs.keys()) - set(existing_tutorial_refs.keys())
        missing_resources = set(all_concept_ids) - set(new_resource_refs.keys()) - set(existing_resource_refs.keys())
        missing_quizzes = set(all_concept_ids) - set(new_quiz_refs.keys()) - set(existing_quiz_refs.keys())
        
        if missing_tutorials or missing_resources or missing_quizzes:
            logger.warning(
                "content_generation_missing_items",
                missing_tutorials=list(missing_tutorials) if not settings.SKIP_TUTORIAL_GENERATION else "skipped",
                missing_resources=list(missing_resources) if not settings.SKIP_RESOURCE_RECOMMENDATION else "skipped",
                missing_quizzes=list(missing_quizzes) if not settings.SKIP_QUIZ_GENERATION else "skipped",
                trace_id=state["trace_id"],
            )
        
        # 发布任务完成通知
        await notification_service.publish_completed(
            task_id=state["trace_id"],
            roadmap_id=framework.roadmap_id,
            tutorials_count=len(all_tutorial_refs),
            failed_count=len(new_failed_concepts),
        )
        
        # 构建执行历史消息
        history_parts = []
        if not settings.SKIP_TUTORIAL_GENERATION:
            history_parts.append(f"教程: {len(new_tutorial_refs)}")
        if not settings.SKIP_RESOURCE_RECOMMENDATION:
            history_parts.append(f"资源: {len(new_resource_refs)}")
        if not settings.SKIP_QUIZ_GENERATION:
            history_parts.append(f"测验: {len(new_quiz_refs)}")
        history_message = f"内容生成完成 ({', '.join(history_parts)}, 失败: {len(new_failed_concepts)})"
        
        # 使用 reducer 后，只返回新生成的条目
        return {
            "roadmap_framework": updated_framework,
            "tutorial_refs": new_tutorial_refs,  # merge_dicts reducer 会合并
            "resource_refs": new_resource_refs,  # merge_dicts reducer 会合并
            "quiz_refs": new_quiz_refs,  # merge_dicts reducer 会合并
            "failed_concepts": new_failed_concepts,  # add reducer 会追加
            "current_step": "content_generation",
            "execution_history": [history_message],  # add reducer 会追加
        }
    
    def _update_concept_statuses(
        self,
        framework: RoadmapFramework,
        tutorial_refs: dict[str, TutorialGenerationOutput],
        resource_refs: dict[str, ResourceRecommendationOutput] = None,
        quiz_refs: dict[str, QuizGenerationOutput] = None,
    ) -> RoadmapFramework:
        """
        更新路线图框架中所有 Concept 的状态
        
        包括：
        - content_status/content_ref/content_summary: 教程内容
        - resources_status/resources_count: 资源推荐
        - quiz_status/quiz_id/quiz_questions_count: 测验
        """
        resource_refs = resource_refs or {}
        quiz_refs = quiz_refs or {}
        
        updated_stages = []
        
        for stage in framework.stages:
            updated_modules = []
            for module in stage.modules:
                updated_concepts = []
                for concept in module.concepts:
                    concept_dict = concept.model_dump()
                    
                    # 更新教程状态
                    if concept.concept_id in tutorial_refs:
                        tutorial_output = tutorial_refs[concept.concept_id]
                        concept_dict.update({
                            "content_status": "completed",
                            "content_ref": tutorial_output.content_url,
                            "content_summary": tutorial_output.summary,
                        })
                    else:
                        # 如果有教程生成任务但失败
                        if not settings.SKIP_TUTORIAL_GENERATION:
                            concept_dict["content_status"] = "failed"
                    
                    # 更新资源推荐状态
                    if concept.concept_id in resource_refs:
                        resource_output = resource_refs[concept.concept_id]
                        concept_dict.update({
                            "resources_status": "completed",
                            "resources_id": resource_output.id,  # 关联 resource_recommendation_metadata 表
                            "resources_count": len(resource_output.resources),
                        })
                    else:
                        # 如果有资源推荐任务但失败
                        if not settings.SKIP_RESOURCE_RECOMMENDATION:
                            concept_dict["resources_status"] = "failed"
                    
                    # 更新测验状态
                    if concept.concept_id in quiz_refs:
                        quiz_output = quiz_refs[concept.concept_id]
                        concept_dict.update({
                            "quiz_status": "completed",
                            "quiz_id": quiz_output.quiz_id,
                            "quiz_questions_count": quiz_output.total_questions,
                        })
                    else:
                        # 如果有测验生成任务但失败
                        if not settings.SKIP_QUIZ_GENERATION:
                            concept_dict["quiz_status"] = "failed"
                    
                    updated_concept = Concept(**concept_dict)
                    updated_concepts.append(updated_concept)
                
                # 修复：排除原有的 concepts 字段，避免重复参数错误
                module_dict = module.model_dump()
                module_dict.pop('concepts', None)
                updated_module = type(module)(
                    **module_dict,
                    concepts=updated_concepts,
                )
                updated_modules.append(updated_module)
            
            # 修复：排除原有的 modules 字段，避免重复参数错误
            stage_dict = stage.model_dump()
            stage_dict.pop('modules', None)
            updated_stage = type(stage)(
                **stage_dict,
                modules=updated_modules,
            )
            updated_stages.append(updated_stage)
        
        # 修复：排除原有的 stages 字段，避免重复参数错误
        framework_dict = framework.model_dump()
        framework_dict.pop('stages', None)
        return RoadmapFramework(
            **framework_dict,
            stages=updated_stages,
        )
    
    async def execute(self, user_request: UserRequest, trace_id: str) -> RoadmapState:
        """
        执行完整的工作流
        
        Args:
            user_request: 用户请求
            trace_id: 追踪 ID
            
        Returns:
            最终的工作流状态
        """
        logger.info(
            "workflow_execution_starting",
            trace_id=trace_id,
            user_id=user_request.user_id,
            skip_structure_validation=settings.SKIP_STRUCTURE_VALIDATION,
            skip_human_review=settings.SKIP_HUMAN_REVIEW,
            skip_tutorial_generation=settings.SKIP_TUTORIAL_GENERATION,
            skip_resource_recommendation=settings.SKIP_RESOURCE_RECOMMENDATION,
            skip_quiz_generation=settings.SKIP_QUIZ_GENERATION,
        )
        
        initial_state: RoadmapState = {
            "user_request": user_request,
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
            "trace_id": trace_id,
            "execution_history": [],
        }
        
        config = {"configurable": {"thread_id": trace_id}}
        
        try:
            logger.info(
                "workflow_graph_invoking",
                trace_id=trace_id,
            )
            
            # 使用异步 ainvoke（AsyncPostgresSaver 完全支持异步）
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            logger.info(
                "workflow_execution_completed",
                trace_id=trace_id,
                final_step=final_state.get("current_step"),
                has_framework=bool(final_state.get("roadmap_framework")),
                execution_history_count=len(final_state.get("execution_history", [])),
            )
            
            # 清除内存缓存中的实时步骤
            self._clear_live_step(trace_id)
            
            return final_state
            
        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            self._clear_live_step(trace_id)
            raise
    
    async def resume_after_human_review(
        self,
        trace_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> RoadmapState:
        """
        在人工审核后恢复工作流
        
        使用 Command(resume=...) 来恢复被 interrupt() 暂停的工作流。
        
        Args:
            trace_id: 追踪 ID
            approved: 是否批准
            feedback: 可选的反馈信息（当拒绝时）
            
        Returns:
            最终的工作流状态
        """
        config = {"configurable": {"thread_id": trace_id}}
        
        # 使用 Command(resume=...) 来恢复工作流
        # resume 的值将作为 interrupt() 函数的返回值
        resume_value = {
            "approved": approved,
            "feedback": feedback or "",
        }
        
        logger.info(
            "resume_after_human_review",
            trace_id=trace_id,
            approved=approved,
            has_feedback=bool(feedback),
        )
        
        final_state = await self.graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
        
        return final_state
