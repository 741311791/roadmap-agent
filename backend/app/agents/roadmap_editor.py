"""
Roadmap Editor Agent（路线图编辑师）

重构说明：
- 统一使用 EditPlan 作为修改指令来源
- 移除了 validation_issues 直接处理逻辑
- 所有修改来源（验证失败、人工反馈）都通过 EditPlanAnalyzerAgent 转换为 EditPlan
"""
import re
import yaml
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


def _try_extract_yaml(content: str) -> str | None:
    """
    尝试从内容中提取 YAML
    
    检测优先级：
    1. 被 ```yaml ... ``` 包裹的 YAML（最高优先级）
    2. 被 ``` ... ``` 包裹的 YAML
    3. 直接的 YAML 内容（启发式检测，最低优先级）
    
    Returns:
        提取的 YAML 字符串，如果没找到则返回 None
    """
    content = content.strip()
    
    # 【优先级1】情况1: 被 ```yaml 或 ```yml 包裹
    if "```yaml" in content or "```yml" in content:
        start_marker = "```yaml" if "```yaml" in content else "```yml"
        start = content.find(start_marker)
        if start != -1:
            start += len(start_marker)
            end = content.find("```", start)
            if end != -1:
                yaml_content = content[start:end].strip()
                logger.debug("yaml_extracted_from_code_block", format="yaml", length=len(yaml_content))
                return yaml_content
    
    # 【优先级2】情况2: 被 ``` 包裹（无语言标记，尝试解析为YAML）
    if content.startswith("```") and content.count("```") >= 2:
        start = content.find("```")
        # 跳过第一行的 ``` 标记
        start = content.find("\n", start) + 1
        end = content.find("```", start)
        if end != -1:
            yaml_content = content[start:end].strip()
            # 简单检查是否像YAML（包含冒号和换行）
            if ":" in yaml_content and "\n" in yaml_content:
                logger.debug("yaml_extracted_from_generic_code_block", length=len(yaml_content))
                return yaml_content
    
    # 【优先级3】情况3: 直接的YAML内容（启发式检测）
    # ⚠️ 注意：只有当内容不包含代码块标记时才使用此检测
    if "```" not in content:
        # YAML通常以键值对开始，检查是否有顶层字段
        lines = content.split("\n")
        if lines and any(line.strip().startswith(key + ":") for line in lines[:10] 
                         for key in ["roadmap_id", "title", "stages", "modification_summary"]):
            logger.debug("yaml_detected_as_plain_text", length=len(content))
            return content
    
    # 所有检测失败
    logger.warning(
        "yaml_extraction_failed",
        content_preview=content[:200],
        has_yaml_marker="```yaml" in content,
        has_generic_marker="```" in content,
    )
    return None


def _parse_yaml_roadmap(yaml_content: str) -> dict:
    """
    解析 YAML 格式的路线图编辑输出
    
    Args:
        yaml_content: YAML 字符串
        
    Returns:
        包含 framework, modification_summary, preserved_elements 的字典
        
    Raises:
        ValueError: YAML 解析失败
    """
    try:
        data = yaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            raise ValueError(f"YAML 解析结果不是字典: {type(data)}")
        
        # 提取编辑相关字段
        modification_summary = data.pop("modification_summary", "")
        preserved_elements = data.pop("preserved_elements", [])
        
        # 确保必填字段存在
        required_fields = ["roadmap_id", "title", "stages"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ValueError(f"YAML 缺少必填字段: {missing_fields}")
        
        # 确保 stages 是列表
        if not isinstance(data.get("stages"), list):
            raise ValueError(f"stages 字段必须是数组，实际类型: {type(data.get('stages'))}")
        
        # 补全可选字段
        if "total_estimated_hours" not in data:
            # 计算总时长
            total_hours = 0.0
            for stage in data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        total_hours += concept.get("estimated_hours", 0.0)
            data["total_estimated_hours"] = total_hours
        
        if "recommended_completion_weeks" not in data:
            # 假设每周学习10小时
            data["recommended_completion_weeks"] = max(1, int(data.get("total_estimated_hours", 0) / 10))
        
        # 补全或修正 stage.order（缺失或无效时自动修正）
        # 注意：order 必须 >= 1，LLM 可能错误输出 0 或负数
        for idx, stage in enumerate(data.get("stages", []), start=1):
            if "order" not in stage or not isinstance(stage.get("order"), int) or stage["order"] < 1:
                stage["order"] = idx
        
        # 补全 concept 的默认字段（如果LLM遗漏）
        for stage in data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    # 补全 content_status 等字段
                    if "content_status" not in concept:
                        concept["content_status"] = "pending"
                    if "content_ref" not in concept:
                        concept["content_ref"] = None
                    if "content_version" not in concept:
                        concept["content_version"] = "v1"
                    if "content_summary" not in concept:
                        concept["content_summary"] = None
        
        logger.info(
            "yaml_roadmap_edit_parsed",
            stages_count=len(data.get("stages", [])),
            roadmap_id=data.get("roadmap_id"),
        )
        
        return {
            "framework": data,
            "modification_summary": modification_summary,
            "preserved_elements": preserved_elements
        }
        
    except yaml.YAMLError as e:
        error_msg = str(e)
        
        # 检测是否包含 Markdown 格式标记，提供更明确的错误提示
        markdown_markers = []
        if '`' in yaml_content:
            markdown_markers.append("反引号（`）")
        if '**' in yaml_content or '__' in yaml_content:
            markdown_markers.append("强调标记（** 或 __）")
        if re.search(r'\*[^\s*]', yaml_content):
            markdown_markers.append("斜体标记（*）")
        
        if markdown_markers:
            error_msg += f"\n\n⚠️ 检测到 YAML 内容包含 Markdown 格式标记：{', '.join(markdown_markers)}"
            error_msg += "\n提示：YAML 字段值不应包含 Markdown 格式，请使用纯文本。"
            error_msg += "\n示例：name: useEffect Hook（正确） 而不是 name: `useEffect` Hook（错误）"
        
        logger.error(
            "yaml_parse_error", 
            error=str(e), 
            yaml_content_preview=yaml_content[:500],
            has_markdown_markers=bool(markdown_markers),
            markdown_markers=markdown_markers if markdown_markers else None
        )
        raise ValueError(f"YAML 解析失败: {error_msg}")
    except Exception as e:
        logger.error("yaml_roadmap_processing_error", error=str(e))
        raise


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
            max_tokens=16384,
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
        
        # 调用 LLM
        response = await self._call_llm(messages)
        
        # 解析输出
        content = response.choices[0].message.content
        
        try:
            # 尝试提取 YAML
            yaml_content = _try_extract_yaml(content)
            
            if not yaml_content:
                logger.error(
                    "roadmap_edit_yaml_not_found",
                    content_preview=content[:500]
                )
                raise ValueError("LLM 输出中未找到有效的 YAML 格式内容")
            
            # 解析 YAML
            result_dict = _parse_yaml_roadmap(yaml_content)
            
            # 验证并构建输出
            framework = RoadmapFramework.model_validate(result_dict["framework"])
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
                intents_executed=len(edit_plan.intents),
                preserved_count=len(preserved_elements),
            )
            return result
            
        except yaml.YAMLError as e:
            logger.error("roadmap_edit_yaml_parse_error", error=str(e), content=content[:500])
            raise ValueError(f"LLM 输出不是有效的 YAML 格式: {e}")
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

