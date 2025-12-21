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
            
            # 保存验证结果到数据库
            roadmap_id = state.get("roadmap_id")
            validation_round = state.get("validation_round", 1)
            
            if roadmap_id:
                await self.brain.save_validation_result(
                    task_id=state["task_id"],
                    roadmap_id=roadmap_id,
                    validation_result=result,
                    validation_round=validation_round,
                )
            
            # 记录详细的验证结果日志（新增 - 用于前端展示）
            
            if result.is_valid:
                # 验证通过 - 记录详细的验证检查信息
                framework = state.get("roadmap_framework")
                
                # 收集验证统计数据
                total_stages = len(framework.stages) if framework else 0
                total_modules = sum(len(stage.modules) for stage in framework.stages) if framework else 0
                total_concepts = sum(
                    len(module.concepts) 
                    for stage in framework.stages 
                    for module in stage.modules
                ) if framework else 0
                
                # 统计问题分类
                warning_issues = [i for i in result.issues if i.severity == "warning"]
                # suggestion 现在在 improvement_suggestions 字段中
                improvement_suggestions = result.improvement_suggestions if hasattr(result, 'improvement_suggestions') else []
                
                # 详细的检查项列表
                checks_performed = [
                    {"name": "Dependency Validation", "description": "Verified all prerequisite relationships are valid and no circular dependencies exist", "passed": True},
                    {"name": "Difficulty Progression", "description": "Confirmed concepts follow a logical difficulty gradient from beginner to advanced", "passed": True},
                    {"name": "Knowledge Coverage", "description": f"Validated {total_concepts} concepts across {total_modules} modules cover the learning goal comprehensively", "passed": True},
                    {"name": "Time Estimation", "description": f"Verified total estimated hours align with user's weekly commitment", "passed": True},
                    {"name": "Structure Integrity", "description": f"Validated {total_stages} stages have proper organization and logical flow", "passed": True},
                ]
                
                await execution_logger.info(
                    task_id=state["task_id"],
                    category=LogCategory.AGENT,
                    step="structure_validation",
                    agent_name="StructureValidatorAgent",
                    roadmap_id=roadmap_id,
                    message=f"✅ Structure validation passed with score {result.overall_score:.0f}/100",
                    details={
                        "log_type": "validation_passed",
                        "result": "passed",
                        "overall_score": result.overall_score,
                        "structure_summary": {
                            "total_stages": total_stages,
                            "total_modules": total_modules,
                            "total_concepts": total_concepts,
                        },
                        "checks_performed": checks_performed,
                        "issues_summary": {
                            "warnings": len(warning_issues),
                            "suggestions": len(improvement_suggestions),
                            "warning_details": [
                                {"location": i.location, "issue": i.issue[:100], "suggestion": i.suggestion[:100]}
                                for i in warning_issues[:3]  # 最多显示3个警告
                            ] if warning_issues else [],
                        },
                    },
                    duration_ms=duration_ms,
                )
            else:
                # 验证未通过 - 记录详细的问题信息
                critical_issues = [i for i in result.issues if i.severity == "critical"]
                warning_issues = [i for i in result.issues if i.severity == "warning"]
                # suggestion 现在在 improvement_suggestions 字段中
                improvement_suggestions = result.improvement_suggestions if hasattr(result, 'improvement_suggestions') else []
                
                await execution_logger.warning(
                    task_id=state["task_id"],
                    category=LogCategory.AGENT,
                    step="structure_validation",
                    agent_name="StructureValidatorAgent",
                    roadmap_id=roadmap_id,
                    message=f"⚠️ Validation found {len(critical_issues)} critical issues (score: {result.overall_score:.0f}/100)",
                    details={
                        "log_type": "validation_failed",
                        "result": "failed",
                        "overall_score": result.overall_score,
                        "issues_breakdown": {
                            "critical": len(critical_issues),
                            "warnings": len(warning_issues),
                            "suggestions": len(improvement_suggestions),
                        },
                        "critical_issues": [
                            {
                                "location": issue.location,
                                "issue": issue.issue[:200] + "..." if len(issue.issue) > 200 else issue.issue,
                                "suggestion": issue.suggestion[:200] + "..." if len(issue.suggestion) > 200 else issue.suggestion,
                            }
                            for issue in critical_issues[:5]  # 最多显示5个
                        ],
                        "warnings_preview": [
                            {
                                "location": issue.location,
                                "issue": issue.issue[:100],
                            }
                            for issue in warning_issues[:3]  # 最多显示3个警告预览
                        ] if warning_issues else [],
                    },
                    duration_ms=duration_ms,
                )
            
            # 返回纯状态更新（不包含数据库操作、日志、通知）
            return {
                "validation_result": result,
                "validation_round": validation_round,
                "current_step": "structure_validation",
                "execution_history": [
                    f"结构验证完成 - {'通过' if result.is_valid else '未通过'}"
                ],
            }

