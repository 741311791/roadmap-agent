"""
需求分析节点执行器

负责执行需求分析节点（Step 1: Intent Analysis）
"""
import time
import uuid
import structlog

from app.agents.factory import AgentFactory
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger, LogCategory
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.session import AsyncSessionLocal
from app.core.error_handler import error_handler
from ..base import RoadmapState, ensure_unique_roadmap_id
from ..state_manager import StateManager

logger = structlog.get_logger()


class IntentAnalysisRunner:
    """
    需求分析节点执行器
    
    职责：
    1. 执行 IntentAnalyzerAgent
    2. 确保 roadmap_id 唯一性
    3. 更新数据库（task 状态和 roadmap_id）
    4. 发布进度通知
    5. 记录执行日志
    6. 错误处理（通过统一 ErrorHandler）
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        agent_factory: AgentFactory,
    ):
        """
        Args:
            state_manager: StateManager 实例
            agent_factory: AgentFactory 实例
        """
        self.state_manager = state_manager
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行需求分析节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "intent_analysis")
        
        logger.info(
            "workflow_step_started",
            step="intent_analysis",
            task_id=task_id,
            user_goal=state["user_request"].preferences.learning_goal[:50]
            if state["user_request"].preferences.learning_goal
            else "N/A",
        )
        
        # 记录执行日志
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="intent_analysis",
            message="开始需求分析",
            details={
                "learning_goal": state["user_request"].preferences.learning_goal[:100]
            },
        )
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="intent_analysis",
            status="processing",
            message="正在分析学习需求...",
        )
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution("intent_analysis", task_id, "需求分析") as ctx:
            # 执行 Agent
            agent = self.agent_factory.create_intent_analyzer()
            result = await agent.execute(state["user_request"])
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "workflow_step_completed",
                step="intent_analysis",
                task_id=task_id,
                key_technologies=result.key_technologies[:3]
                if result.key_technologies
                else [],
            )
            
            # 记录执行日志（详细记录需求分析结果）
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="intent_analysis",
                message="需求分析完成",
                duration_ms=duration_ms,
                roadmap_id=result.roadmap_id,
                details={
                    "roadmap_id": result.roadmap_id,
                    "parsed_goal": result.parsed_goal,
                    "key_technologies": result.key_technologies[:5],
                    "difficulty_profile": result.difficulty_profile,
                    "time_constraint": result.time_constraint,
                    "recommended_focus": result.recommended_focus[:3]
                    if result.recommended_focus
                    else [],
                    "skill_gap_analysis": result.skill_gap_analysis[:3] 
                    if result.skill_gap_analysis 
                    else [],
                    "personalized_suggestions": result.personalized_suggestions[:2]
                    if result.personalized_suggestions
                    else [],
                },
            )
            
            # 确保 roadmap_id 唯一性
            unique_roadmap_id = await self._ensure_unique_roadmap_id(
                result, state, task_id
            )
            
            # 更新数据库
            await self._update_database(task_id, unique_roadmap_id)
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="intent_analysis",
                status="completed",
                message="需求分析完成",
                extra_data={
                    "key_technologies": result.key_technologies[:5],
                    "roadmap_id": unique_roadmap_id,
                },
            )
            
            # 存储结果到上下文
            ctx["result"] = {
                "intent_analysis": result,
                "roadmap_id": unique_roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
        
        # 返回状态更新
        return ctx["result"]
    
    async def _ensure_unique_roadmap_id(
        self, result, state: RoadmapState, task_id: str
    ) -> str:
        """
        确保 roadmap_id 唯一性
        
        Args:
            result: IntentAnalysisOutput 实例
            state: 工作流状态
            task_id: 追踪ID
            
        Returns:
            唯一的 roadmap_id
        """
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 如果 LLM 没有生成 roadmap_id，则使用回退方案
            if not result.roadmap_id or not result.roadmap_id.strip():
                logger.warning(
                    "roadmap_id_missing_from_llm",
                    task_id=task_id,
                    message="IntentAnalyzerAgent 未生成 roadmap_id，使用回退方案",
                )
                # 回退：基于技术栈生成简单 ID
                tech_slug = (
                    "-".join(result.key_technologies[:2])
                    .lower()
                    .replace(" ", "-")[:30]
                    if result.key_technologies
                    else "roadmap"
                )
                result.roadmap_id = f"{tech_slug}-{uuid.uuid4().hex[:8]}"
            
            # 验证并确保唯一性
            original_id = result.roadmap_id
            unique_id = await ensure_unique_roadmap_id(result.roadmap_id, repo)
            result.roadmap_id = unique_id
            
            if original_id != unique_id:
                logger.info(
                    "roadmap_id_uniqueness_ensured",
                    task_id=task_id,
                    original_id=original_id,
                    unique_id=unique_id,
                )
            else:
                logger.info(
                    "roadmap_id_validated",
                    task_id=task_id,
                    roadmap_id=unique_id,
                    learning_goal=state["user_request"].preferences.learning_goal[:50],
                )
            
            return unique_id
    
    async def _update_database(self, task_id: str, roadmap_id: str):
        """
        更新数据库记录
        
        关键：立即更新 task 记录的 roadmap_id 字段，
        这样前端跳转时就能通过 roadmap_id 找到活跃的 task。
        
        Args:
            task_id: 追踪ID
            roadmap_id: 唯一的路线图ID
        """
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="intent_analysis",
                roadmap_id=roadmap_id,
            )
            await session.commit()
            
            logger.info(
                "task_roadmap_id_updated",
                task_id=task_id,
                roadmap_id=roadmap_id,
                message="已将roadmap_id关联到task记录，前端现在可以安全跳转",
            )

