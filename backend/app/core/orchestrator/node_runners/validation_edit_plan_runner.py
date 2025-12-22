"""
验证结果修改计划分析节点执行器

负责执行验证结果的修改计划分析节点（validation_edit_plan_analysis）

职责:
- 将 ValidationOutput 格式化为自然语言 user_feedback
- 调用 EditPlanAnalyzerAgent（复用现有逻辑）
- 生成 EditPlan 存入工作流状态
- 为后续的 RoadmapEditor 提供精确的修改指导

流程：
ValidationOutput → format_validation_to_feedback() → user_feedback → EditPlanAnalyzerAgent → EditPlan
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.models.domain import EditPlanAnalyzerInput
from app.services.execution_logger import execution_logger, LogCategory
from app.utils.validation_formatter import format_validation_to_feedback
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ValidationEditPlanRunner:
    """
    验证结果修改计划分析节点执行器
    
    职责：
    1. 将 ValidationOutput 格式化为自然语言 user_feedback
    2. 调用 EditPlanAnalyzerAgent（完全复用现有逻辑）
    3. 将 EditPlan 存入工作流状态
    4. 记录分析日志
    
    注意:
    - 仅在结构验证失败时执行
    - 输出的 EditPlan 将指导 RoadmapEditor 精确执行修改
    - 完全复用 EditPlanAnalyzerAgent，不做任何修改
    """
    
    def __init__(
        self,
        brain: WorkflowBrain,
        agent_factory: AgentFactory,
    ):
        """
        Args:
            brain: WorkflowBrain 实例（统一协调者）
            agent_factory: AgentFactory 实例
        """
        self.brain = brain
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行验证结果的修改计划分析
        
        流程：
        1. 从 state 获取 ValidationOutput
        2. 格式化为自然语言 user_feedback
        3. 调用 EditPlanAnalyzerAgent
        4. 返回 EditPlan
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典，包含 edit_plan 和 user_feedback
        """
        validation_result = state.get("validation_result")
        roadmap_framework = state.get("roadmap_framework")
        
        if not validation_result:
            raise ValueError("validation_result 不存在，无法执行修改计划分析")
        
        if not roadmap_framework:
            raise ValueError("roadmap_framework 不存在，无法执行修改计划分析")
        
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("validation_edit_plan_analysis", state):
            start_time = time.time()
            
            # 1. 格式化 ValidationOutput → user_feedback
            user_feedback = format_validation_to_feedback(validation_result)
            
            logger.info(
                "validation_formatted_to_feedback",
                task_id=state["task_id"],
                feedback_length=len(user_feedback),
                issues_count=len(validation_result.issues),
                critical_count=len([i for i in validation_result.issues if i.severity == "critical"]),
                warning_count=len([i for i in validation_result.issues if i.severity == "warning"]),
            )
            
            # 2. 调用 EditPlanAnalyzerAgent（完全复用现有逻辑）
            agent = self.agent_factory.create_edit_plan_analyzer()
            
            analyzer_input = EditPlanAnalyzerInput(
                user_feedback=user_feedback,  # 格式化后的自然语言
                existing_framework=roadmap_framework,
                user_preferences=state["user_request"].preferences,
            )
            
            result = await agent.execute(analyzer_input)
            
            # 3. 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 4. 构建日志消息
            intents_summary = []
            for intent in result.edit_plan.intents:
                desc_preview = intent.description[:50] + "..." if len(intent.description) > 50 else intent.description
                intents_summary.append(f"- [{intent.intent_type}] {intent.target_path}: {desc_preview}")
            
            # 5. 记录分析完成日志
            logger.info(
                "validation_edit_plan_runner_completed",
                task_id=state["task_id"],
                intents_count=len(result.edit_plan.intents),
                confidence=result.confidence,
                needs_clarification=result.needs_clarification,
                duration_ms=duration_ms,
            )
            
            # 6. 记录详细的分析日志（用于前端展示）
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="validation_edit_plan_analysis",
                agent_name="EditPlanAnalyzerAgent",
                roadmap_id=state.get("roadmap_id"),
                message=f"🔍 Analyzed validation issues: {len(result.edit_plan.intents)} modification(s) identified",
                details={
                    "log_type": "validation_edit_plan_analyzed",
                    "feedback_summary": result.edit_plan.feedback_summary,
                    "intents_count": len(result.edit_plan.intents),
                    "intents_preview": intents_summary[:5],  # 展示前 5 个
                    "confidence": result.confidence,
                    "scope_analysis": result.edit_plan.scope_analysis,
                    "preservation_requirements": result.edit_plan.preservation_requirements,
                    "source": "structure_validation",  # 标识来源是结构验证
                },
                duration_ms=duration_ms,
            )
            
            # 7. 返回状态更新
            return {
                "edit_plan": result.edit_plan,
                "user_feedback": user_feedback,  # 保存格式化后的 feedback
                "edit_source": "validation_failed",  # 标记编辑来源为验证失败
                "current_step": "validation_edit_plan_analysis",
                "execution_history": [
                    f"验证问题分析完成（识别 {len(result.edit_plan.intents)} 个修改意图）"
                ],
            }

