"""
课程设计节点执行器

负责执行课程设计节点（Step 2: Curriculum Design）
"""
import time
import structlog

from app.agents.factory import AgentFactory
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger, LogCategory
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.session import AsyncSessionLocal
from app.core.error_handler import error_handler
from ..base import RoadmapState
from ..state_manager import StateManager

logger = structlog.get_logger()


class CurriculumDesignRunner:
    """
    课程设计节点执行器
    
    职责：
    1. 执行 CurriculumArchitectAgent
    2. 保存路线图框架到数据库
    3. 发布进度通知
    4. 记录执行日志
    5. 错误处理（通过统一 ErrorHandler）
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
        执行课程设计节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "curriculum_design")
        
        logger.info(
            "workflow_step_started",
            step="curriculum_design",
            task_id=task_id,
            has_intent_analysis=bool(state.get("intent_analysis")),
            roadmap_id=state.get("roadmap_id"),
        )
        
        # 获取 roadmap_id（在 intent_analysis 阶段已经生成）
        roadmap_id = state.get("roadmap_id")
        
        # 记录执行日志（包含 roadmap_id）
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="curriculum_design",
            message="开始设计课程架构",
            roadmap_id=roadmap_id,
        )
        
        # 更新数据库状态为 curriculum_design
        await self._update_task_status(task_id, "curriculum_design", roadmap_id)
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="curriculum_design",
            status="processing",
            message="正在设计学习路线图框架...",
        )
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution("curriculum_design", task_id, "课程架构设计") as ctx:
            agent = self.agent_factory.create_curriculum_architect()
            logger.debug(
                "curriculum_design_agent_created",
                task_id=task_id,
                model=agent.model_name,
                provider=agent.model_provider,
            )
            
            # 使用已生成和验证过的 roadmap_id
            roadmap_id = state.get("roadmap_id")
            if not roadmap_id:
                raise ValueError("roadmap_id 在 intent_analysis 阶段未生成")
            
            # 执行 Agent
            result = await agent.execute({
                "intent_analysis": state["intent_analysis"],
                "user_preferences": state["user_request"].preferences,
                "roadmap_id": roadmap_id,
            })
            
            duration_ms = int((time.time() - start_time) * 1000)
            roadmap_id = result.framework.roadmap_id if result.framework else None
            stages_count = len(result.framework.stages) if result.framework else 0
            
            logger.info(
                "workflow_step_completed",
                step="curriculum_design",
                task_id=task_id,
                roadmap_id=roadmap_id,
                stages_count=stages_count,
            )
            
            # 统计模块和概念数量
            modules_count = (
                sum(len(stage.modules) for stage in result.framework.stages)
                if result.framework
                else 0
            )
            concepts_count = (
                sum(
                    len(module.concepts)
                    for stage in result.framework.stages
                    for module in stage.modules
                )
                if result.framework
                else 0
            )
            
            # 记录执行日志
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="curriculum_design",
                message="课程架构设计完成",
                duration_ms=duration_ms,
                roadmap_id=roadmap_id,
                details={
                    "roadmap_id": roadmap_id,
                    "title": result.framework.title if result.framework else None,
                    "stages_count": stages_count,
                    "modules_count": modules_count,
                    "concepts_count": concepts_count,
                    "total_estimated_hours": result.framework.total_estimated_hours
                    if result.framework
                    else 0,
                },
            )
            
            # 保存路线图框架到数据库
            await self._save_roadmap_framework(state, result.framework)
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="curriculum_design",
                status="completed",
                message="课程架构设计完成",
                extra_data={
                    "stages_count": stages_count,
                    "modules_count": modules_count,
                    "concepts_count": concepts_count,
                },
            )
            
            # 存储结果到上下文
            ctx["result"] = {
                "roadmap_framework": result.framework,
                "current_step": "curriculum_design",
                "execution_history": ["课程架构设计完成"],
            }
        
        # 返回状态更新
        return ctx["result"]
    
    async def _update_task_status(self, task_id: str, current_step: str, roadmap_id: str | None):
        """
        更新任务状态到数据库
        
        Args:
            task_id: 任务 ID
            current_step: 当前步骤
            roadmap_id: 路线图 ID
        """
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step=current_step,
                roadmap_id=roadmap_id,
            )
            await session.commit()
            
            logger.debug(
                "task_status_updated",
                task_id=task_id,
                current_step=current_step,
                roadmap_id=roadmap_id,
            )
    
    async def _save_roadmap_framework(self, state: RoadmapState, framework):
        """
        保存路线图框架到数据库
        
        Args:
            state: 工作流状态
            framework: RoadmapFramework 实例
        """
        task_id = state["task_id"]
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 保存路线图元数据和框架
            await repo.save_roadmap_metadata(
                roadmap_id=framework.roadmap_id,
                user_id=state["user_request"].user_id,
                framework=framework,
            )
            
            logger.info(
                "roadmap_framework_saved",
                task_id=task_id,
                roadmap_id=framework.roadmap_id,
                stages_count=len(framework.stages),
            )

