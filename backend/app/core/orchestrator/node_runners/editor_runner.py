"""
路线图编辑节点执行器（重构版 - 使用 WorkflowBrain）

负责执行路线图编辑节点（Step 2E: Roadmap Edit）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 使用 brain.save_roadmap_framework() 保存更新后的框架
- 代码行数减少 ~70%
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.models.domain import RoadmapEditInput
from app.services.execution_logger import execution_logger, LogCategory
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class EditorRunner:
    """
    路线图编辑节点执行器（重构版）
    
    职责：
    1. 执行 RoadmapEditorAgent
    2. 保存更新后的路线图框架
    3. 递增 modification_count
    
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
        执行路线图编辑节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 调用 RoadmapEditorAgent
        3. 使用 brain.save_roadmap_framework() 保存更新后的框架
        4. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        modification_count = state.get("modification_count", 0)
        edit_round = modification_count + 1
        
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("roadmap_edit", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_roadmap_editor()
            
            # 准备输入
            edit_input = RoadmapEditInput(
                existing_framework=state["roadmap_framework"],
                validation_issues=state["validation_result"].issues
                if state.get("validation_result")
                else [],
                user_preferences=state["user_request"].preferences,
                modification_context=f"第 {edit_round} 次修改"
            )
            
            # 保存原始框架（用于对比）
            origin_framework = state["roadmap_framework"]
            
            # 执行 Agent
            result = await agent.execute(edit_input)
            
            # 保存编辑记录（在更新框架之前）
            roadmap_id = result.framework.roadmap_id
            await self.brain.save_edit_result(
                task_id=state["task_id"],
                roadmap_id=roadmap_id,
                origin_framework=origin_framework,
                modified_framework=result.framework,
                edit_round=edit_round,
            )
            
            # 保存更新后的框架（使用 brain 的事务性保存方法）
            await self.brain.save_roadmap_framework(
                task_id=state["task_id"],
                roadmap_id=roadmap_id,
                user_id=state["user_request"].user_id,
                framework=result.framework,
            )
            
            # 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录修改日志（业务逻辑日志 - 旧版本保留）
            logger.info(
                "editor_runner_completed",
                task_id=state["task_id"],
                modification_count=modification_count + 1,
                roadmap_id=result.framework.roadmap_id,
            )
            
            # 记录详细的编辑完成日志（新增 - 用于前端展示）
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="roadmap_edit",
                agent_name="RoadmapEditorAgent",
                roadmap_id=result.framework.roadmap_id,
                message="✅ Roadmap updated based on your feedback",
                details={
                    "log_type": "edit_completed",
                    "modification_count": modification_count + 1,
                    "changes_summary": result.modification_summary if hasattr(result, 'modification_summary') else "Roadmap structure updated",
                },
                duration_ms=duration_ms,
            )
            
            # 递增 validation_round（下次 validation 时使用）
            validation_round = state.get("validation_round", 1) + 1
            
            # 返回纯状态更新
            return {
                "roadmap_framework": result.framework,
                "modification_count": modification_count + 1,
                "validation_round": validation_round,
                "current_step": "roadmap_edit",
                "execution_history": [f"路线图修改完成（第 {edit_round} 次）"],
            }
