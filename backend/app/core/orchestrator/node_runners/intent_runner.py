"""
需求分析节点执行器（重构版 - 使用 WorkflowBrain）

负责执行需求分析节点（Step 1: Intent Analysis）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 使用 brain.ensure_unique_roadmap_id() 确保唯一性
- 使用 brain.save_intent_analysis() 保存结果
- 代码行数减少 ~70%
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.services.execution_logger import execution_logger, LogCategory
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class IntentAnalysisRunner:
    """
    需求分析节点执行器（重构版）
    
    职责：
    1. 执行 IntentAnalyzerAgent
    2. 确保 roadmap_id 唯一性
    3. 保存需求分析结果
    
    不再负责:
    - 数据库操作（由 WorkflowBrain 处理）
    - 日志记录（由 WorkflowBrain 处理）
    - 通知发布（由 WorkflowBrain 处理）
    - 状态管理（由 WorkflowBrain 处理）
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
        执行需求分析节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 调用 IntentAnalyzerAgent
        3. 使用 brain.ensure_unique_roadmap_id() 确保 ID 唯一
        4. 使用 brain.save_intent_analysis() 保存结果
        5. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("intent_analysis", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_intent_analyzer()
            
            # 执行 Agent
            result = await agent.execute(state["user_request"])
            
            # 确保 roadmap_id 唯一性（由 brain 处理）
            unique_roadmap_id = await self.brain.ensure_unique_roadmap_id(result.roadmap_id)
            result.roadmap_id = unique_roadmap_id
            
            # 保存需求分析结果（由 brain 统一事务管理）
            await self.brain.save_intent_analysis(
                task_id=state["task_id"],
                intent_analysis=result,
                unique_roadmap_id=unique_roadmap_id,
            )
            
            # 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录分析结果日志（业务逻辑日志 - 旧版本保留）
            logger.info(
                "intent_runner_completed",
                task_id=state["task_id"],
                roadmap_id=unique_roadmap_id,
                key_technologies_count=len(result.key_technologies),
                difficulty_profile=result.difficulty_profile,
            )
            
            # 记录详细的分析输出日志（新增 - 用于前端展示）
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="intent_analysis",
                agent_name="IntentAnalyzerAgent",
                roadmap_id=unique_roadmap_id,
                message=f"✅ Intent analysis completed: {result.parsed_goal[:80]}{'...' if len(result.parsed_goal) > 80 else ''}",
                details={
                    "log_type": "intent_analysis_output",
                    "output_summary": {
                        "parsed_goal": result.parsed_goal,
                        "key_technologies": result.key_technologies,
                        "difficulty_profile": result.difficulty_profile,
                        "time_constraint": result.time_constraint,
                        "recommended_focus": result.recommended_focus,
                        "skill_gap_analysis": result.skill_gap_analysis[:5] if result.skill_gap_analysis else [],
                        "personalized_suggestions": result.personalized_suggestions[:3] if result.personalized_suggestions else [],
                    },
                    # 完整输出（可选，用于调试）
                    "full_output_available": True,
                },
                duration_ms=duration_ms,
            )
            
            # 返回纯状态更新
            return {
                "intent_analysis": result,
                "roadmap_id": unique_roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
