"""
课程设计节点执行器（重构版 - 使用 WorkflowBrain）

负责执行课程设计节点（Step 2: Curriculum Design）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 使用 brain.save_roadmap_framework() 保存路线图框架
- 代码行数减少 ~70%
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.services.execution_logger import execution_logger, LogCategory
from app.utils.framework_validator import validate_and_raise_if_invalid
from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class CurriculumDesignRunner:
    """
    课程设计节点执行器（重构版）
    
    职责：
    1. 执行 CurriculumArchitectAgent
    2. 保存路线图框架
    
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
        执行课程设计节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 调用 CurriculumArchitectAgent
        3. 使用 brain.save_roadmap_framework() 保存结果
        4. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("curriculum_design", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_curriculum_architect()
            
            # 准备输入数据
            from app.models.domain import CurriculumDesignInput
            curriculum_input = CurriculumDesignInput(
                intent_analysis=state["intent_analysis"],
                user_preferences=state["user_request"].preferences,
            )
            
            # 执行 Agent
            result = await agent.execute(curriculum_input)
            
            # ✅ 确保 framework 使用 state 中的 roadmap_id（防止 LLM 生成不一致的 ID）
            state_roadmap_id = state.get("roadmap_id")
            if state_roadmap_id and result.framework.roadmap_id != state_roadmap_id:
                logger.warning(
                    "curriculum_design_roadmap_id_mismatch",
                    task_id=state["task_id"],
                    state_roadmap_id=state_roadmap_id,
                    framework_roadmap_id=result.framework.roadmap_id,
                    message="强制使用 state 中的 roadmap_id，覆盖 LLM 返回的值",
                )
                result.framework.roadmap_id = state_roadmap_id
            
            # 🔍 验证 concept_id 唯一性（生成后强制检查）
            validate_and_raise_if_invalid(result.framework)
            
            # 保存路线图框架（由 brain 统一事务管理）
            await self.brain.save_roadmap_framework(
                task_id=state["task_id"],
                roadmap_id=result.framework.roadmap_id,
                user_id=state["user_request"].user_id,
                framework=result.framework,
            )
            
            # 🆕 批量初始化 ConceptMetadata（追踪内容生成状态）
            concept_ids = []
            for stage in result.framework.stages:
                for module in stage.modules:
                    for concept in module.concepts:
                        concept_ids.append(concept.concept_id)
            
            if concept_ids:
                from app.db.celery_session import celery_safe_session_with_retry
                from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
                
                async with celery_safe_session_with_retry() as session:
                    concept_meta_repo = ConceptMetadataRepository(session)
                    await concept_meta_repo.batch_initialize_concepts(
                        roadmap_id=result.framework.roadmap_id,
                        concept_ids=concept_ids,
                    )
                    await session.commit()
                    
                logger.info(
                    "concept_metadata_initialized",
                    task_id=state["task_id"],
                    roadmap_id=result.framework.roadmap_id,
                    concept_count=len(concept_ids),
                )
            
            # 统计路线图结构
            total_modules = sum(len(stage.modules) for stage in result.framework.stages)
            total_concepts = sum(
                len(module.concepts)
                for stage in result.framework.stages
                for module in stage.modules
            )
            
            # 计算执行时长
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录设计结果日志（业务逻辑日志 - 旧版本保留）
            logger.info(
                "curriculum_runner_completed",
                task_id=state["task_id"],
                roadmap_id=result.framework.roadmap_id,
                stages_count=len(result.framework.stages),
                modules_count=total_modules,
                concepts_count=total_concepts,
            )
            
            # 记录详细的设计输出日志（新增 - 用于前端展示）
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="curriculum_design",
                agent_name="CurriculumArchitectAgent",
                roadmap_id=result.framework.roadmap_id,
                message=f"✅ Curriculum designed: {total_concepts} concepts in {len(result.framework.stages)} stages",
                details={
                    "log_type": "curriculum_design_output",
                    "output_summary": {
                        "roadmap_id": result.framework.roadmap_id,
                        "title": result.framework.title,
                        "total_stages": len(result.framework.stages),
                        "total_modules": total_modules,
                        "total_concepts": total_concepts,
                        "total_hours": result.framework.total_estimated_hours,
                        "completion_weeks": result.framework.recommended_completion_weeks,
                        "stages": [
                            {
                                "name": stage.name,
                                "description": stage.description[:100] + "..." if len(stage.description) > 100 else stage.description,
                                "modules_count": len(stage.modules),
                                "estimated_hours": stage.total_hours,
                            }
                            for stage in result.framework.stages
                        ],
                    },
                    # 不存储完整输出（太大），前端需要时通过API获取
                    "full_output_available": True,
                },
                duration_ms=duration_ms,
            )
            
            # 返回纯状态更新
            return {
                "roadmap_framework": result.framework,
                "current_step": "curriculum_design",
                "execution_history": ["课程设计完成"],
            }
