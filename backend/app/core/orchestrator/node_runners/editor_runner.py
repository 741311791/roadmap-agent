"""
路线图编辑节点执行器（重构版 - 使用 WorkflowBrain）

负责执行路线图编辑节点（Step 2E: Roadmap Edit）

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 使用 brain.save_roadmap_framework() 保存更新后的框架
- 统一使用 EditPlan 作为修改指令来源（移除 validation_issues 直接处理）
- 代码行数减少 ~70%
"""
import structlog
import time

from app.agents.factory import AgentFactory
from app.models.domain import RoadmapEditInput
from app.services.execution_logger import execution_logger, LogCategory
from app.utils.framework_validator import validate_and_raise_if_invalid
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
    
    def _build_modification_context(self, state: RoadmapState, edit_round: int) -> str:
        """
        构建修改上下文说明
        
        重构后统一使用 EditPlan，上下文根据 EditPlan 内容生成
        
        Args:
            state: 工作流状态
            edit_round: 当前编辑轮次
            
        Returns:
            上下文说明字符串
        """
        context_parts = [f"第 {edit_round} 次修改"]
        
        edit_plan = state.get("edit_plan")
        if edit_plan:
            context_parts.append(f"修改计划：包含 {len(edit_plan.intents)} 个修改意图")
            # 统计各优先级的意图数量
            must_count = sum(1 for i in edit_plan.intents if i.priority == "must")
            should_count = sum(1 for i in edit_plan.intents if i.priority == "should")
            could_count = sum(1 for i in edit_plan.intents if i.priority == "could")
            if must_count:
                context_parts.append(f"必须执行：{must_count} 项")
            if should_count:
                context_parts.append(f"建议执行：{should_count} 项")
            if could_count:
                context_parts.append(f"可选执行：{could_count} 项")
        
        return "；".join(context_parts)
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行路线图编辑节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 检查 edit_plan 是否存在（必需）
        2. 使用 brain.node_execution() 自动处理状态/日志/通知
        3. 调用 RoadmapEditorAgent（统一使用 EditPlan）
        4. 使用 brain.save_roadmap_framework() 保存更新后的框架
        5. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
            
        Raises:
            ValueError: 如果 edit_plan 不存在
        """
        modification_count = state.get("modification_count", 0)
        edit_round = modification_count + 1
        
        # 检查 edit_plan 是否存在（重构后必需）
        edit_plan = state.get("edit_plan")
        if not edit_plan:
            raise ValueError(
                "edit_plan 不存在，无法执行路线图编辑。"
                "请确保在调用 EditorRunner 前已执行 EditPlanAnalyzerAgent "
                "（通过 EditPlanRunner 或 ValidationEditPlanRunner）。"
            )
        
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("roadmap_edit", state):
            start_time = time.time()
            
            # 创建 Agent
            agent = self.agent_factory.create_roadmap_editor()
            
            # 构建修改上下文
            modification_context = self._build_modification_context(state, edit_round)
            
            # 准备输入（简化版：统一使用 EditPlan）
            edit_input = RoadmapEditInput(
                existing_framework=state["roadmap_framework"],
                user_preferences=state["user_request"].preferences,
                modification_context=modification_context,
                edit_plan=edit_plan,
            )
            
            # 保存原始框架（用于对比）
            origin_framework = state["roadmap_framework"]
            
            # 执行 Agent
            result = await agent.execute(edit_input)
            
            # 🔍 验证 concept_id 唯一性（修改后强制检查）
            validate_and_raise_if_invalid(result.framework)
            
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
            
            # 🆕 更新 ConceptMetadata（处理新增/删除的 concept）
            new_concept_ids = []
            for stage in result.framework.stages:
                for module in stage.modules:
                    for concept in module.concepts:
                        new_concept_ids.append(concept.concept_id)
            
            if new_concept_ids:
                from app.db.celery_session import celery_safe_session_with_retry
                from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
                
                async with celery_safe_session_with_retry() as session:
                    concept_meta_repo = ConceptMetadataRepository(session)
                    # 批量初始化（只会创建不存在的 concept）
                    await concept_meta_repo.batch_initialize_concepts(
                        roadmap_id=roadmap_id,
                        concept_ids=new_concept_ids,
                    )
                    await session.commit()
                    
                logger.info(
                    "concept_metadata_synchronized_after_edit",
                    task_id=state["task_id"],
                    roadmap_id=roadmap_id,
                    concept_count=len(new_concept_ids),
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
            # 从状态中获取 edit_source（由上游的 EditPlanRunner 或 ValidationEditPlanRunner 设置）
            edit_source = state.get("edit_source")
            log_details = {
                "log_type": "edit_completed",
                "modification_count": modification_count + 1,
                "changes_summary": result.modification_summary if hasattr(result, 'modification_summary') else "Roadmap structure updated",
            }
            if edit_source:
                log_details["edit_source"] = edit_source
            
            await execution_logger.info(
                task_id=state["task_id"],
                category=LogCategory.AGENT,
                step="roadmap_edit",
                agent_name="RoadmapEditorAgent",
                roadmap_id=result.framework.roadmap_id,
                message="✅ Roadmap updated based on your feedback",
                details=log_details,
                duration_ms=duration_ms,
            )
            
            # 递增 validation_round（下次 validation 时使用）
            validation_round = state.get("validation_round", 1) + 1
            
            # 返回纯状态更新
            state_update = {
                "roadmap_framework": result.framework,
                "modification_count": modification_count + 1,
                "validation_round": validation_round,
                "current_step": "roadmap_edit",
                "execution_history": [f"路线图修改完成（第 {edit_round} 次）"],
            }
            
            # 关键修复：保持 edit_source 字段（用于前端区分分支）
            # edit_source 由上游的 EditPlanRunner 或 ValidationEditPlanRunner 设置
            if "edit_source" in state:
                state_update["edit_source"] = state["edit_source"]
            
            return state_update
