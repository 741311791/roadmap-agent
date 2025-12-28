"""
Roadmap Editor Agent（路线图编辑师）

重构说明：
- 统一使用 EditPlan 作为修改指令来源
- 移除了 validation_issues 直接处理逻辑
- 所有修改来源（验证失败、人工反馈）都通过 EditPlanAnalyzerAgent 转换为 EditPlan
"""
import json
import re
from app.agents.base import BaseAgent
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
    路线图编辑师 Agent
    
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
            max_tokens=32768,
        )
    
    def _build_user_message(
        self,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
        edit_plan: EditPlan,
    ) -> str:
        """
        构建用户消息（简化版：统一使用 EditPlan）
        
        Args:
            existing_framework: 现有路线图框架
            user_preferences: 用户偏好
            edit_plan: 修改计划（必需）
            
        Returns:
            格式化的用户消息
        """
        # 基础路线图信息
        base_info = f"""
**现有路线图框架**:
- 标题: {existing_framework.title}
- 总预估时长: {existing_framework.total_estimated_hours} 小时
- 推荐完成周数: {existing_framework.recommended_completion_weeks} 周
- 阶段数量: {len(existing_framework.stages)}

**用户约束**:
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时
- 当前水平: {user_preferences.current_level}
- 学习目标: {user_preferences.learning_goal}
"""
        
        # 格式化修改意图列表
        intents_text = "\n".join([
            f"- **[{intent.priority.upper()}]** {intent.intent_type} {intent.target_type} @ {intent.target_path}\n  描述: {intent.description}"
            for intent in edit_plan.intents
        ])
        
        # 格式化保留要求
        preservation_text = "\n".join([f"- {item}" for item in edit_plan.preservation_requirements]) if edit_plan.preservation_requirements else "- 修改计划中未提及的所有内容"
        
        return f"""
请根据以下修改计划编辑学习路线图：

{base_info}

**修改计划摘要**:
{edit_plan.feedback_summary}

**修改意图列表（请严格按照此计划执行）**:
{intents_text}

**影响范围分析**:
{edit_plan.scope_analysis}

**⚠️ 必须保留不变的部分**:
{preservation_text}

**执行要求**:
1. **严格执行**: 只修改计划中指定的内容，不要擅自修改其他部分
2. **优先级顺序**: 优先处理 priority=must 的意图，然后处理 should，最后处理 could
3. **保持稳定**: 计划中未提及的 Stage/Module/Concept 必须保持原样（包括 ID、名称、内容）
4. **最小改动**: 即使是要修改的部分，也要尽量保留原有的合理设计
5. **ID 保持**: 除非是新增或删除，否则保持所有 ID 不变

请以 YAML 格式返回修改后的完整路线图框架。
"""
    
    async def edit(
        self,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
        edit_plan: EditPlan,
        modification_context: str | None = None,
    ) -> RoadmapEditOutput:
        """
        基于 EditPlan 修改现有路线图框架（简化版）
        
        重构说明：
        - 统一使用 EditPlan 作为修改指令来源
        - 移除了 validation_issues 直接处理逻辑
        - 所有修改来源都通过 EditPlanAnalyzerAgent 转换为 EditPlan
        
        Args:
            existing_framework: 现有路线图框架
            user_preferences: 用户偏好
            edit_plan: 结构化的修改计划（必需，来自 EditPlanAnalyzerAgent）
            modification_context: 修改上下文说明
            
        Returns:
            修改后的路线图框架
        """
        # 构建修改上下文
        if not modification_context:
            must_count = sum(1 for i in edit_plan.intents if i.priority == "must")
            should_count = sum(1 for i in edit_plan.intents if i.priority == "should")
            modification_context = f"修改计划包含 {must_count} 个必须执行、{should_count} 个建议执行的意图"
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "roadmap_editor.j2",
            agent_name="Roadmap Editor",
            role_description="路线图编辑专家，基于 EditPlan 对现有路线图进行精确修改，保留未涉及部分，解决指定问题。",
            user_goal=user_preferences.learning_goal,
            existing_framework=existing_framework,
            modification_context=modification_context,
            edit_plan=edit_plan,
        )
        
        # 构建用户消息
        user_message = self._build_user_message(
            existing_framework=existing_framework,
            user_preferences=user_preferences,
            edit_plan=edit_plan,
        )
        
        logger.info(
            "roadmap_edit_started",
            roadmap_id=existing_framework.roadmap_id,
            intents_count=len(edit_plan.intents),
            must_count=sum(1 for i in edit_plan.intents if i.priority == "must"),
            should_count=sum(1 for i in edit_plan.intents if i.priority == "should"),
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM，使用 response_format 强制 JSON 输出
        logger.info(
            "roadmap_edit_calling_llm",
            intents_count=len(edit_plan.intents),
            response_format="json_object",
        )
        response = await self._call_llm(
            messages,
            response_format={"type": "json_object"}
        )
        
        # 解析输出
        content = response.choices[0].message.content
        
        try:
            # 解析 JSON 格式
            logger.debug("roadmap_edit_parsing_json_format")
            result_dict = json.loads(content)
            
            # 提取字段
            modification_summary = result_dict.pop("modification_summary", "")
            preserved_elements = result_dict.pop("preserved_elements", [])
            
            # 验证并构建输出
            framework = RoadmapFramework.model_validate(result_dict)
            
            result = RoadmapEditOutput(
                framework=framework,
                modification_summary=modification_summary,
                preserved_elements=preserved_elements,
            )
            
            logger.info(
                "roadmap_edit_success",
                roadmap_id=framework.roadmap_id,
                intents_executed=len(edit_plan.intents),
                preserved_count=len(preserved_elements),
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error("roadmap_edit_json_parse_error", error=str(e), content=content[:500])
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("roadmap_edit_output_invalid", error=str(e), content=content[:500])
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def execute(self, input_data: RoadmapEditInput) -> RoadmapEditOutput:
        """实现基类的抽象方法"""
        return await self.edit(
            existing_framework=input_data.existing_framework,
            user_preferences=input_data.user_preferences,
            edit_plan=input_data.edit_plan,
            modification_context=input_data.modification_context,
        )

