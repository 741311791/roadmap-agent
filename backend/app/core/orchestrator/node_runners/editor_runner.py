"""
路线图编辑节点执行器

负责执行路线图编辑节点（Step 2E: Roadmap Edit）
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


class EditorRunner:
    """
    路线图编辑节点执行器
    
    职责：
    1. 执行 RoadmapEditorAgent
    2. 更新路线图框架
    3. 递增 modification_count
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
        执行路线图编辑节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        modification_count = state.get("modification_count", 0)
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "roadmap_edit")
        
        logger.info(
            "workflow_step_started",
            step="roadmap_edit",
            task_id=task_id,
            modification_count=modification_count,
            roadmap_id=state.get("roadmap_id"),
        )
        
        # 获取 roadmap_id
        roadmap_id = state.get("roadmap_id")
        
        # 记录执行日志（包含 roadmap_id）
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="roadmap_edit",
            message=f"开始修改路线图（第 {modification_count + 1} 次）",
            roadmap_id=roadmap_id,
        )
        
        # 更新数据库状态
        await self._update_task_status(task_id, "roadmap_edit", roadmap_id)
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="roadmap_edit",
            status="processing",
            message=f"正在根据验证反馈修改路线图（第 {modification_count + 1} 次）...",
        )
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution("roadmap_edit", task_id, "路线图修改") as ctx:
            from app.models.domain import RoadmapEditInput
            
            agent = self.agent_factory.create_roadmap_editor()
            
            # 执行 Agent
            edit_input = RoadmapEditInput(
                existing_framework=state["roadmap_framework"],
                validation_issues=state["validation_result"].issues
                if state.get("validation_result")
                else [],
                user_preferences=state["user_request"].preferences,
                modification_context=f"第 {modification_count + 1} 次修改"
            )
            result = await agent.execute(edit_input)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "workflow_step_completed",
                step="roadmap_edit",
                task_id=task_id,
                modification_count=modification_count + 1,
            )
            
            # 记录执行日志
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="roadmap_edit",
                message=f"路线图修改完成（第 {modification_count + 1} 次）",
                duration_ms=duration_ms,
                roadmap_id=state.get("roadmap_id"),
                details={
                    "modification_count": modification_count + 1,
                    "changes_made": result.changes_summary
                    if hasattr(result, "changes_summary")
                    else None,
                },
            )
            
            # 更新数据库中的路线图框架
            await self._update_roadmap_framework(state, result.updated_framework)
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="roadmap_edit",
                status="completed",
                message=f"路线图修改完成（第 {modification_count + 1} 次）",
                extra_data={
                    "modification_count": modification_count + 1,
                },
            )
            
            # 存储结果到上下文
            ctx["result"] = {
                "roadmap_framework": result.updated_framework,
                "modification_count": modification_count + 1,
                "current_step": "roadmap_edit",
                "execution_history": [f"路线图修改完成（第 {modification_count + 1} 次）"],
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
    
    async def _update_roadmap_framework(self, state: RoadmapState, framework):
        """
        更新数据库中的路线图框架
        
        Args:
            state: 工作流状态
            framework: 更新后的 RoadmapFramework 实例
        """
        task_id = state["task_id"]
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_roadmap_framework(
                roadmap_id=framework.roadmap_id,
                framework_data=framework.model_dump(),
            )
            await session.commit()
            
            logger.info(
                "roadmap_framework_updated",
                task_id=task_id,
                roadmap_id=framework.roadmap_id,
            )

