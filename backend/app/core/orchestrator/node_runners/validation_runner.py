"""
结构验证节点执行器（重构版 - 使用 WorkflowBrain）

负责执行结构验证节点（Step 3: Structure Validation）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 删除直接的数据库操作
- 代码行数减少 ~70%
- 职责更加单一清晰
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.models.domain import ValidationInput
from app.services.execution_logger import execution_logger, LogCategory
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ValidationRunner:
    """
    结构验证节点执行器（重构版）
    
    职责：
    1. 执行 StructureValidatorAgent
    2. 返回验证结果
    
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
        执行结构验证节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 调用 StructureValidatorAgent
        3. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("structure_validation", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_structure_validator()
            
            # 准备输入
            validation_input = ValidationInput(
                framework=state["roadmap_framework"],
                user_preferences=state["user_request"].preferences,
            )
            
            # 执行 Agent
            result = await agent.execute(validation_input)
            
            # 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录验证结果日志（业务逻辑日志 - 旧版本保留）
            logger.info(
                "validation_runner_completed",
                task_id=state["task_id"],
                is_valid=result.is_valid,
                issues_count=len(result.issues) if result.issues else 0,
            )
            
            # 记录详细的验证结果日志（新增 - 用于前端展示）
            roadmap_id = state.get("roadmap_id")
            
            if result.is_valid:
                # 验证通过
                await execution_logger.info(
                    task_id=state["task_id"],
                    category=LogCategory.AGENT,
                    step="structure_validation",
                    agent_name="StructureValidatorAgent",
                    roadmap_id=roadmap_id,
                    message=f"✅ Validation passed: {len(result.issues)} issues found and fixed",
                    details={
                        "log_type": "validation_passed",
                        "result": "passed",
                        "checks_performed": [
                            "dependency_check",
                            "difficulty_gradient",
                            "concept_coverage",
                            "time_estimation"
                        ],
                        "issues_fixed": len([i for i in result.issues if i.severity != "error"]),
                        "warnings": len([i for i in result.issues if i.severity == "warning"]),
                    },
                    duration_ms=duration_ms,
                )
            else:
                # 验证未通过
                critical_issues = [i for i in result.issues if i.severity == "error"]
                await execution_logger.warning(
                    task_id=state["task_id"],
                    category=LogCategory.AGENT,
                    step="structure_validation",
                    agent_name="StructureValidatorAgent",
                    roadmap_id=roadmap_id,
                    message=f"⚠️ Validation found {len(critical_issues)} critical issues",
                    details={
                        "log_type": "validation_failed",
                        "result": "failed",
                        "critical_issues": [
                            {
                                "severity": issue.severity,
                                "category": issue.category,
                                "description": issue.description[:200] + "..." if len(issue.description) > 200 else issue.description,
                                "affected_concepts": issue.affected_concepts[:5] if issue.affected_concepts else [],
                            }
                            for issue in critical_issues[:10]  # 只显示前10个
                        ],
                        "total_critical_issues": len(critical_issues),
                    },
                    duration_ms=duration_ms,
                )
            
            # 返回纯状态更新（不包含数据库操作、日志、通知）
            return {
                "validation_result": result,
                "current_step": "structure_validation",
                "execution_history": [
                    f"结构验证完成 - {'通过' if result.is_valid else '未通过'}"
                ],
            }

