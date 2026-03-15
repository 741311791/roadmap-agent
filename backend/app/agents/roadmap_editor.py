"""
Roadmap Editor Agent（路线图编辑师）

重构说明（第三版 - 极简版）：
- 移除 StageProcessor（过度工程化）
- 移除依赖关系和并行处理逻辑
- 采用两阶段生成（效仿 IntentAnalyzer）
- 修改总结改为本地生成，减少额外 LLM 开销
- 完全依赖 LLM 的语义理解能力
"""
from app.agents.base import BaseAgent
from app.agents.framework_diff import compute_modified_node_ids
from app.agents.framework_normalizer import normalize_framework_ids
from app.models.domain import (
    RoadmapFramework,
    LearningPreferences,
    RoadmapEditInput,
    RoadmapEditOutput,
    EditPlan,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class RoadmapEditorAgent(BaseAgent):
    """
    路线图编辑师 Agent（极简版）
    
    重构后职责：
    - 接收 EditPlan（只包含 tasks）
    - 使用两阶段生成修改整个 RoadmapFramework
    - 使用 FrameworkDiff 自动生成 modified_node_ids
    - 本地生成修改总结
    
    配置从环境变量加载：
    - EDITOR_PROVIDER: 模型提供商（默认: anthropic）
    - EDITOR_MODEL: 模型名称（默认: claude-3-5-sonnet-20241022）
    - EDITOR_BASE_URL: 自定义 API 端点（可选）
    - EDITOR_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "roadmap_editor",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.EDITOR_PROVIDER,
            model_name=model_name or settings.EDITOR_MODEL,
            base_url=base_url or settings.EDITOR_BASE_URL,
            api_key=api_key or settings.EDITOR_API_KEY,
            temperature=0.4,  # 较低温度，确保修改的严谨性
            max_tokens=20000,
        )
    
    def _get_required_constraints(self) -> list[str]:
        """路线图编辑器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.SKILL_GAP,
            ConstraintNames.RECOMMENDED_FOCUS,
        ]
    
    async def execute(self, input_data: RoadmapEditInput) -> RoadmapEditOutput:
        """
        基于 EditPlan 修改路线图框架（极简版）
        
        执行流程：
        1. 构建 Prompt（包含所有 tasks 和 existing_framework）
        2. 使用两阶段生成新的 RoadmapFramework
        3. 使用 FrameworkDiff 自动生成 modified_node_ids
        4. 本地生成修改总结
        
        Args:
            input_data: 包含现有框架、用户偏好和修改计划
            
        Returns:
            修改后的路线图框架（包含 modified_node_ids 和 LLM 生成的总结）
        """
        existing_framework = input_data.existing_framework
        user_preferences = input_data.user_preferences
        edit_plan = input_data.edit_plan
        user_constraints = await self._load_user_constraints(
            roadmap_id=existing_framework.roadmap_id
        )
        
        logger.info(
            "roadmap_edit_started",
            roadmap_id=existing_framework.roadmap_id,
            tasks_count=len(edit_plan.tasks),
        )
        
        # ====================================================================
        # 阶段 1: 使用两阶段生成修改路线图
        # ====================================================================
        logger.info("roadmap_edit_stage1_two_stage_generation")
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "roadmap_editor.j2",
            user_constraints=user_constraints,
            agent_name="Roadmap Editor",
            role_description="路线图编辑专家，根据修改任务调整路线图框架。",
            user_goal=user_preferences.learning_goal,
        )
        
        # 构建用户消息
        user_message = self._build_user_message(
            existing_framework=existing_framework,
            user_preferences=user_preferences,
            edit_plan=edit_plan,
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 使用两阶段生成（思维链 + 结构化提取）
        logger.info(
            "roadmap_edit_calling_llm_two_stage",
            model=self.model_name,
            tasks_count=len(edit_plan.tasks),
        )
        
        updated_framework = await self._call_llm(
            messages,
            response_model=RoadmapFramework,
            use_two_stage=True,  # 启用两阶段生成
        )
        
        # ✅ 关键修复：强制使用原始的roadmap_id，防止LLM生成新ID
        # 这确保了数据库更新而不是创建新记录
        original_roadmap_id = existing_framework.roadmap_id
        if updated_framework.roadmap_id != original_roadmap_id:
            logger.warning(
                "roadmap_id_mismatch_fixed",
                original_id=original_roadmap_id,
                llm_generated_id=updated_framework.roadmap_id,
                message="LLM生成了不同的roadmap_id，已强制使用原始ID",
            )
            updated_framework.roadmap_id = original_roadmap_id
        
        # ✅ ID规范化：移除LLM生成的非标准ID（如xxx-new）
        # 确保所有Stage、Module、Concept的ID符合规范
        logger.info("roadmap_edit_normalizing_ids")
        updated_framework = normalize_framework_ids(updated_framework)
        
        # 验证：确保修改后的路线图有非空的阶段列表
        if not updated_framework.stages:
            logger.error(
                "roadmap_edit_empty_stages",
                roadmap_id=existing_framework.roadmap_id,
            )
            raise ValueError(
                "路线图编辑失败：修改后的路线图没有任何学习阶段。"
            )
        
        # ====================================================================
        # 阶段 2: 使用 FrameworkDiff 对比新旧框架
        # ====================================================================
        logger.info("roadmap_edit_stage2_diff")
        
        modified_node_ids = compute_modified_node_ids(
            old_framework=existing_framework,
            new_framework=updated_framework,
        )
        
        # ====================================================================
        # 阶段 3: 本地生成修改总结
        # ====================================================================
        logger.info("roadmap_edit_stage3_generate_summary_local")

        modification_summary = self._build_modification_summary(
            old_framework=existing_framework,
            new_framework=updated_framework,
            tasks=edit_plan.tasks,
            modified_node_ids=modified_node_ids,
        )
        
        logger.info(
            "roadmap_edit_success",
            roadmap_id=updated_framework.roadmap_id,
            tasks_executed=len(edit_plan.tasks),
            modified_nodes_count=len(modified_node_ids),
            stages_count=len(updated_framework.stages),
        )
        
        # 构建输出
        return RoadmapEditOutput(
            framework=updated_framework,
            modification_summary=modification_summary,
            modified_node_ids=modified_node_ids,
        )
    
    def _build_user_message(
        self,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
        edit_plan: EditPlan,
    ) -> str:
        """
        构建用户消息
        
        Args:
            existing_framework: 现有路线图框架
            user_preferences: 用户偏好
            edit_plan: 修改计划
            
        Returns:
            格式化的用户消息
        """
        # 格式化修改任务
        tasks_text = "\n".join([
            f"- [{task.action}] {task.stage_id or 'NEW'}: {task.instruction}"
            for task in edit_plan.tasks
        ])
        
        return f"""
请根据以下修改任务编辑学习路线图：

**修改计划摘要**:
{edit_plan.feedback_summary}

**修改任务列表**:
{tasks_text}

**当前路线图框架**:
```json
{existing_framework.model_dump_json(indent=2)}
```

**用户约束**:
- 学习目标: {user_preferences.learning_goal}
- 当前水平: {user_preferences.current_level}
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时

请返回修改后的完整路线图框架。
"""
    
    def _build_modification_summary(
        self,
        old_framework: RoadmapFramework,
        new_framework: RoadmapFramework,
        tasks: list,
        modified_node_ids: list[str],
    ) -> str:
        """
        本地生成修改总结
        
        Args:
            old_framework: 旧版框架
            new_framework: 新版框架
            tasks: 修改任务列表
            modified_node_ids: 被修改的节点 ID 列表
            
        Returns:
            修改总结文本
        """
        tasks_summary = "；".join([
            f"{task.action} {task.stage_id or 'new'}"
            for task in tasks
        ])
        hours_diff = new_framework.total_estimated_hours - old_framework.total_estimated_hours
        hours_sign = "+" if hours_diff >= 0 else ""
        summary = (
            f"{len(tasks)} 个任务已执行（{tasks_summary}），"
            f"修改了 {len(modified_node_ids)} 个节点，"
            f"总时长变化: {hours_sign}{hours_diff:.1f}h"
        )
        logger.info("modification_summary_generated_local", summary=summary)
        return summary
