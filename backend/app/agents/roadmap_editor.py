"""
Roadmap Editor Agent（路线图编辑师）
"""
import json
from app.agents.base import BaseAgent
from app.models.domain import (
    RoadmapFramework,
    LearningPreferences,
    RoadmapEditInput,
    RoadmapEditOutput,
    ValidationIssue,
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
    
    def __init__(self):
        super().__init__(
            agent_id="roadmap_editor",
            model_provider=settings.EDITOR_PROVIDER,
            model_name=settings.EDITOR_MODEL,
            base_url=settings.EDITOR_BASE_URL,
            api_key=settings.EDITOR_API_KEY,
            temperature=0.4,  # 较低温度，确保修改的严谨性
            max_tokens=8192,
        )
    
    async def edit(
        self,
        existing_framework: RoadmapFramework,
        validation_issues: list[ValidationIssue],
        user_preferences: LearningPreferences,
        modification_count: int = 0,
        modification_context: str | None = None,
    ) -> RoadmapEditOutput:
        """
        基于验证问题修改现有路线图框架
        
        Args:
            existing_framework: 现有路线图框架
            validation_issues: 验证发现的问题列表
            user_preferences: 用户偏好
            modification_count: 修改次数（用于上下文）
            modification_context: 修改上下文说明
            
        Returns:
            修改后的路线图框架
        """
        # 构建修改上下文
        if not modification_context:
            critical_count = sum(1 for issue in validation_issues if issue.severity == "critical")
            warning_count = sum(1 for issue in validation_issues if issue.severity == "warning")
            modification_context = (
                f"第 {modification_count + 1} 次修改，"
                f"主要解决 {critical_count} 个严重问题和 {warning_count} 个警告问题"
            )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "roadmap_editor.j2",
            agent_name="Roadmap Editor",
            role_description="路线图编辑专家，基于验证反馈对现有路线图进行针对性修改，保留合理部分，解决结构问题。",
            user_goal=user_preferences.learning_goal,
            existing_framework=existing_framework,
            validation_issues=validation_issues,
            modification_count=modification_count,
            modification_context=modification_context,
        )
        
        # 构建用户消息
        issues_text = "\n".join([
            f"- [{issue.severity.upper()}] {issue.location}: {issue.issue}\n  建议：{issue.suggestion}"
            for issue in validation_issues
        ])
        
        user_message = f"""
请根据以下验证反馈修改现有的学习路线图框架：

**现有路线图框架**:
- 标题: {existing_framework.title}
- 总预估时长: {existing_framework.total_estimated_hours} 小时
- 推荐完成周数: {existing_framework.recommended_completion_weeks} 周
- 阶段数量: {len(existing_framework.stages)}

**验证发现的问题**:
{issues_text if validation_issues else "无"}

**用户约束**:
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时
- 当前水平: {user_preferences.current_level}
- 学习目标: {user_preferences.learning_goal}

**修改要求**:
1. 必须解决所有 critical 级别的问题
2. 尽量解决 warning 级别的问题
3. 保留路线图中合理的部分（特别是没有问题的部分）
4. 确保修改后的路线图仍然符合用户的学习目标和时间约束
5. 保持路线图的整体结构和逻辑一致性

请以 JSON 格式返回修改后的路线图框架，严格遵循 RoadmapEditOutput Schema。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        response = await self._call_llm(messages)
        
        # 解析输出
        content = response.choices[0].message.content
        
        try:
            # 提取 JSON（可能包含 markdown 代码块）
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # 解析 JSON
            result_dict = json.loads(content)
            
            # 验证并构建输出
            framework = RoadmapFramework.model_validate(result_dict.get("framework", result_dict))
            modification_summary = result_dict.get("modification_summary", "")
            preserved_elements = result_dict.get("preserved_elements", [])
            
            result = RoadmapEditOutput(
                framework=framework,
                modification_summary=modification_summary,
                preserved_elements=preserved_elements,
            )
            
            logger.info(
                "roadmap_edit_success",
                roadmap_id=framework.roadmap_id,
                modification_count=modification_count + 1,
                issues_resolved=len(validation_issues),
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
            validation_issues=input_data.validation_issues,
            user_preferences=input_data.user_preferences,
            modification_context=input_data.modification_context,
        )

