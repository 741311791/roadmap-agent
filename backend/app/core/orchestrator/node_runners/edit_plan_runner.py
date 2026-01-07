"""
修改计划分析节点执行器

负责执行修改计划分析节点（edit_plan_analysis）

职责:
- 调用 EditPlanAnalyzerAgent 解析用户反馈
- 将结构化的修改计划存入工作流状态
- 为后续的 RoadmapEditor 提供精确的修改指导
- 保存修改计划到数据库（EditPlanRecord 表）
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.models.domain import EditPlanAnalyzerInput
from app.services.execution_logger import execution_logger, LogCategory
from app.db.session import AsyncSessionLocal
from app.crud.crud_workflow import get_edit_plan_crud
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


def confidence_to_level(confidence: float) -> str:
    """
    将置信度数值（0-1）转换为级别字符串
    
    Args:
        confidence: 置信度数值，范围 [0, 1]
        
    Returns:
        置信度级别：'high', 'medium', 'low'
    """
    if confidence >= 0.7:
        return "high"
    elif confidence >= 0.4:
        return "medium"
    else:
        return "low"


class EditPlanRunner:
    """
    修改计划分析节点执行器
    
    职责：
    1. 调用 EditPlanAnalyzerAgent 解析用户反馈
    2. 将 EditPlan 存入工作流状态
    3. 记录分析日志
    
    注意:
    - 仅在用户拒绝路线图并提供反馈时执行
    - 输出的 EditPlan 将指导 RoadmapEditor 精确执行修改
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
        执行修改计划分析节点
        
        逻辑:
        1. 检查是否有用户反馈
        2. 调用 EditPlanAnalyzerAgent 解析反馈
        3. 将 EditPlan 存入状态供后续使用
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典，包含 edit_plan
        """
        user_feedback = state.get("user_feedback")
        roadmap_framework = state.get("roadmap_framework")
        
        # 如果没有用户反馈，直接返回空计划
        if not user_feedback:
            logger.warning(
                "edit_plan_runner_no_feedback",
                task_id=state["task_id"],
                message="没有用户反馈，跳过修改计划分析",
            )
            return {
                "edit_plan": None,
                "current_step": "edit_plan_analysis",
                "execution_history": ["修改计划分析跳过（无用户反馈）"],
            }
        
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("edit_plan_analysis", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_edit_plan_analyzer()
            
            # 准备输入
            analyzer_input = EditPlanAnalyzerInput(
                user_feedback=user_feedback,
                existing_framework=roadmap_framework,
                user_preferences=state["user_request"].preferences,
            )
            
            # 执行分析
            result = await agent.execute(analyzer_input)
            
            # 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 构建日志消息
            intents_summary = []
            for intent in result.edit_plan.intents:
                intents_summary.append(f"- [{intent.intent_type}] {intent.target_path}: {intent.description[:50]}...")
            
            # 记录分析完成日志
            logger.info(
                "edit_plan_runner_completed",
                task_id=state["task_id"],
                intents_count=len(result.edit_plan.intents),
                confidence=result.confidence,
                needs_clarification=result.needs_clarification,
            )
            
            # 记录详细的分析日志（用于前端展示）
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="edit_plan_analysis",
                agent_name="EditPlanAnalyzerAgent",
                roadmap_id=state.get("roadmap_id"),
                message=f"🔍 Analyzed your feedback: {len(result.edit_plan.intents)} modification(s) identified",
                details={
                    "log_type": "edit_plan_analyzed",
                    "feedback_summary": result.edit_plan.feedback_summary,
                    "intents_count": len(result.edit_plan.intents),
                    "intents_preview": intents_summary[:3],  # 只展示前3个
                    "confidence": result.confidence,
                    "preservation_requirements": result.edit_plan.preservation_requirements,
                    "needs_clarification": result.needs_clarification,
                    "edit_source": "human_review",  # 标记编辑来源
                },
                duration_ms=duration_ms,
            )
            
            # 如果需要澄清，记录额外日志
            if result.needs_clarification:
                await execution_logger.info(
                    task_id=state["task_id"],
                    category=LogCategory.WORKFLOW,
                    step="edit_plan_analysis",
                    roadmap_id=state.get("roadmap_id"),
                    message="⚠️ Your feedback may need clarification, but we'll proceed with our best understanding",
                    details={
                        "log_type": "clarification_suggested",
                        "clarification_questions": result.clarification_questions,
                    },
                )
            
            # ========================================
            # 保存修改计划到数据库
            # ========================================
            edit_plan_record_id = None
            try:
                async with AsyncSessionLocal() as session:
                    edit_plan_crud = get_edit_plan_crud()
                    
                    # 获取关联的 feedback_id（从上一步 review_runner 传递）
                    feedback_id = state.get("review_feedback_id")
                    
                    if feedback_id:
                        # 创建修改计划记录（将 confidence 从 float 转换为 str）
                        plan_record = await edit_plan_crud.create_plan(
                            session=session,
                            task_id=state["task_id"],
                            roadmap_id=state.get("roadmap_id"),
                            feedback_id=feedback_id,
                            edit_plan=result.edit_plan,
                            confidence=confidence_to_level(result.confidence),
                            needs_clarification=result.needs_clarification,
                            clarification_questions=result.clarification_questions,
                        )
                        
                        # 关键修复：提交事务以确保记录真正保存到数据库
                        await session.commit()
                        
                        edit_plan_record_id = plan_record.id
                        
                        logger.info(
                            "edit_plan_saved_to_db",
                            task_id=state["task_id"],
                            plan_id=plan_record.id,
                            feedback_id=feedback_id,
                            intents_count=len(result.edit_plan.intents),
                        )
                    else:
                        logger.warning(
                            "no_feedback_id_in_state",
                            task_id=state["task_id"],
                            message="无法关联 feedback_id，跳过保存修改计划到数据库",
                        )
            except Exception as e:
                logger.error(
                    "failed_to_save_edit_plan",
                    task_id=state["task_id"],
                    error=str(e),
                )
                # 不阻塞工作流执行，仅记录错误
            
            # 返回状态更新
            state_update = {
                "edit_plan": result.edit_plan,
                "edit_source": "human_review",  # 标记编辑来源为人工审核
                "current_step": "edit_plan_analysis",
                "execution_history": [f"修改计划分析完成（识别 {len(result.edit_plan.intents)} 个修改意图）"],
            }
            
            # 如果成功保存了修改计划记录，将 plan_id 添加到状态中
            if edit_plan_record_id:
                state_update["edit_plan_record_id"] = edit_plan_record_id
            
            return state_update

