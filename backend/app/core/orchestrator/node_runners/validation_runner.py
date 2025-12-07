"""
结构验证节点执行器

负责执行结构验证节点（Step 3: Structure Validation）
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


class ValidationRunner:
    """
    结构验证节点执行器
    
    职责：
    1. 执行 StructureValidatorAgent
    2. 发布进度通知
    3. 记录执行日志
    4. 错误处理（通过统一 ErrorHandler）
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
        执行结构验证节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "structure_validation")
        
        logger.info(
            "workflow_step_started",
            step="structure_validation",
            task_id=task_id,
            roadmap_id=state.get("roadmap_id"),
        )
        
        # 记录执行日志
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="structure_validation",
            message="开始验证路线图结构",
        )
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="structure_validation",
            status="processing",
            message="正在验证路线图结构...",
        )
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution("structure_validation", task_id, "结构验证") as ctx:
            from app.models.domain import ValidationInput
            
            agent = self.agent_factory.create_structure_validator()
            
            # 执行 Agent
            validation_input = ValidationInput(
                framework=state["roadmap_framework"],
                user_preferences=state["user_request"].preferences,
            )
            result = await agent.execute(validation_input)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "workflow_step_completed",
                step="structure_validation",
                task_id=task_id,
                is_valid=result.is_valid,
                issues_count=len(result.issues) if result.issues else 0,
            )
            
            # 记录执行日志
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="structure_validation",
                message=f"结构验证完成 - {'通过' if result.is_valid else '未通过'}",
                duration_ms=duration_ms,
                roadmap_id=state.get("roadmap_id"),
                details={
                    "is_valid": result.is_valid,
                    "issues_count": len(result.issues) if result.issues else 0,
                    "issues": [issue[:100] for issue in (result.issues or [])[:3]],
                },
            )
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="structure_validation",
                status="completed",
                message=f"结构验证完成 - {'通过' if result.is_valid else '未通过'}",
                extra_data={
                    "is_valid": result.is_valid,
                    "issues_count": len(result.issues) if result.issues else 0,
                },
            )
            
            # 存储结果到上下文
            ctx["result"] = {
                "validation_result": result,
                "current_step": "structure_validation",
                "execution_history": [
                    f"结构验证完成 - {'通过' if result.is_valid else '未通过'}"
                ],
            }
        
        # 返回状态更新
        return ctx["result"]

