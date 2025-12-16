"""
Roadmap Editor Agent（路线图编辑师）
"""
import json
import yaml
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


def _try_extract_yaml(content: str) -> str | None:
    """
    尝试从内容中提取 YAML
    
    支持：
    1. 直接的 YAML 内容
    2. 被 ```yaml ... ``` 包裹的 YAML
    3. 被 ``` ... ``` 包裹的 YAML
    
    Returns:
        提取的 YAML 字符串，如果没找到则返回 None
    """
    content = content.strip()
    
    # 情况1: 被 ```yaml 包裹
    if "```yaml" in content or "```yml" in content:
        start_marker = "```yaml" if "```yaml" in content else "```yml"
        start = content.find(start_marker)
        if start != -1:
            start += len(start_marker)
            end = content.find("```", start)
            if end != -1:
                yaml_content = content[start:end].strip()
                logger.debug("yaml_extracted_from_code_block", format="yaml")
                return yaml_content
    
    # 情况2: 被 ``` 包裹（尝试解析为YAML）
    if content.startswith("```") and content.count("```") >= 2:
        start = content.find("```")
        # 跳过第一行的 ``` 标记
        start = content.find("\n", start) + 1
        end = content.find("```", start)
        if end != -1:
            yaml_content = content[start:end].strip()
            # 简单检查是否像YAML（包含冒号和换行）
            if ":" in yaml_content and "\n" in yaml_content:
                logger.debug("yaml_extracted_from_generic_code_block")
                return yaml_content
    
    # 情况3: 直接的YAML内容（启发式检测）
    # YAML通常以键值对开始，检查是否有顶层字段
    lines = content.split("\n")
    if lines and any(line.strip().startswith(key + ":") for line in lines[:10] 
                     for key in ["roadmap_id", "title", "stages", "modification_summary"]):
        logger.debug("yaml_detected_as_plain_text")
        return content
    
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
        
        # 补全 stage.order（如果缺失）
        for idx, stage in enumerate(data.get("stages", []), start=1):
            if "order" not in stage:
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
        logger.error("yaml_parse_error", error=str(e), yaml_content_preview=yaml_content[:500])
        raise ValueError(f"YAML 解析失败: {e}")
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
                modification_count=modification_count + 1,
                issues_resolved=len(validation_issues),
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
            validation_issues=input_data.validation_issues,
            user_preferences=input_data.user_preferences,
            modification_context=input_data.modification_context,
        )

