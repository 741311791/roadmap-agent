"""
Curriculum Architect Agent（课程架构师）
"""
import json
import re
import uuid
import yaml
from typing import AsyncIterator
from app.agents.base import BaseAgent
from app.models.domain import (
    IntentAnalysisOutput,
    LearningPreferences,
    CurriculumDesignOutput,
    RoadmapFramework,
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
                     for key in ["roadmap_id", "title", "stages"]):
        logger.debug("yaml_detected_as_plain_text")
        return content
    
    return None


def _parse_yaml_roadmap(yaml_content: str) -> dict:
    """
    解析 YAML 格式的路线图
    
    Args:
        yaml_content: YAML 字符串
        
    Returns:
        包含 framework 和 design_rationale 的字典
        
    Raises:
        ValueError: YAML 解析失败
    """
    try:
        data = yaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            raise ValueError(f"YAML 解析结果不是字典: {type(data)}")
        
        # 提取 design_rationale
        design_rationale = data.pop("design_rationale", "")
        
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
            "yaml_roadmap_parsed",
            stages_count=len(data.get("stages", [])),
            roadmap_id=data.get("roadmap_id"),
        )
        
        return {
            "framework": data,
            "design_rationale": design_rationale
        }
        
    except yaml.YAMLError as e:
        logger.error("yaml_parse_error", error=str(e), yaml_content_preview=yaml_content[:500])
        raise ValueError(f"YAML 解析失败: {e}")
    except Exception as e:
        logger.error("yaml_processing_error", error=str(e), error_type=type(e).__name__)
        raise ValueError(f"YAML 处理失败: {e}")


def _try_extract_json(content: str) -> str | None:
    """
    尝试从内容中提取JSON
    
    支持：
    1. 直接的JSON对象 { ... }
    2. 被 ```json ... ``` 包裹的JSON
    3. 被 ``` ... ``` 包裹的JSON
    
    Returns:
        提取的JSON字符串，如果不是JSON则返回None
    """
    content = content.strip()
    
    # 尝试1: 检测 ```json ... ``` 或 ``` ... ``` 包裹
    json_code_block_patterns = [
        r'```json\s*\n(.*?)\n```',  # ```json ... ```
        r'```\s*\n(\{.*?\})\s*\n```',  # ``` { ... } ```
    ]
    
    for pattern in json_code_block_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            # 验证是否是有效的JSON
            try:
                json.loads(json_str)
                logger.debug("json_extracted_from_code_block", pattern=pattern)
                return json_str
            except json.JSONDecodeError:
                continue
    
    # 尝试2: 直接是JSON对象（以 { 开始，以 } 结束）
    if content.startswith('{') and content.endswith('}'):
        try:
            json.loads(content)
            logger.debug("json_detected_directly")
            return content
        except json.JSONDecodeError:
            pass
    
    # 不是JSON格式
    return None


def _parse_json_roadmap(json_str: str) -> dict:
    """
    解析JSON格式的路线图，并补全缺失的必需字段
    
    Args:
        json_str: JSON字符串
        
    Returns:
        符合 CurriculumDesignOutput 的字典
    """
    try:
        data = json.loads(json_str)
        
        # 处理wrapped格式：{"output": {...}} 或 {"roadmap": {...}}
        if "stages" not in data:
            for wrap_key in ["output", "roadmap", "framework", "data", "result"]:
                if wrap_key in data and isinstance(data[wrap_key], dict):
                    logger.debug(f"json_unwrapping_from_key", key=wrap_key)
                    data = data[wrap_key]
                    break
        
        # 再次检查是否包含 stages 字段
        if "stages" not in data:
            raise ValueError(f"JSON格式不完整，缺少'stages'字段。实际键: {list(data.keys())}")
        
        # 补全 stage.order（如果缺失）
        for idx, stage in enumerate(data["stages"], start=1):
            if "order" not in stage:
                stage["order"] = idx
                logger.debug("json_补全_stage_order", stage_id=stage.get("stage_id"), order=idx)
        
        # 计算 total_estimated_hours（如果缺失）
        if "total_estimated_hours" not in data or "total_hours" in data:
            total_hours = 0.0
            for stage in data["stages"]:
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        total_hours += concept.get("estimated_hours", 0.0)
            
            data["total_estimated_hours"] = data.get("total_hours", total_hours)
            logger.debug("json_计算_total_estimated_hours", total=data["total_estimated_hours"])
        
        # 计算 recommended_completion_weeks（如果缺失）
        if "recommended_completion_weeks" not in data:
            # 从 weeks 字段获取，或根据总小时数估算
            if "weeks" in data:
                data["recommended_completion_weeks"] = data["weeks"]
            else:
                # 假设每周学习10小时（可调整）
                hours_per_week = 10.0
                data["recommended_completion_weeks"] = max(
                    1, int(data["total_estimated_hours"] / hours_per_week)
                )
            logger.debug(
                "json_计算_recommended_completion_weeks",
                weeks=data["recommended_completion_weeks"]
            )
        
        # 提取 design_rationale
        design_rationale = data.pop("design_rationale", "")
        
        # 返回标准格式
        return {
            "framework": data,
            "design_rationale": design_rationale
        }
            
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}")


def _parse_compact_roadmap(content: str) -> dict:
    """
    解析路线图输出（支持 YAML、JSON 和旧的文本格式）
    
    优先级：
    1. YAML 格式（推荐）- 结构化、易读、可靠
    2. JSON 格式（兼容）- 结构化、但冗长
    3. 文本格式（已废弃）- 仅作为回退兼容
    
    Args:
        content: LLM 输出内容
        
    Returns:
        包含 framework 和 design_rationale 的字典
        
    Raises:
        ValueError: 无法解析任何支持的格式
    """
    errors = {}
    
    # 1. 优先尝试 YAML 格式
    yaml_content = _try_extract_yaml(content)
    if yaml_content:
        try:
            result = _parse_yaml_roadmap(yaml_content)
            logger.info("parse_format_detected", format="yaml")
            return result
        except Exception as e:
            errors['yaml'] = str(e)
            logger.warning(
                "yaml_parse_failed",
                error=str(e),
                yaml_preview=yaml_content[:200] if yaml_content else None,
            )
    
    # 2. 回退到 JSON 格式
    json_content = _try_extract_json(content)
    if json_content:
        try:
            result = _parse_json_roadmap(json_content)
            logger.info("parse_format_detected", format="json")
            return result
        except Exception as e:
            errors['json'] = str(e)
            logger.warning(
                "json_parse_failed",
                error=str(e),
            )
    
    # 3. 所有格式都失败
    logger.error(
        "all_parse_formats_failed",
        errors=errors,
        content_preview=content[:500],
        content_length=len(content),
    )
    
    error_msg = "无法解析路线图输出。请确保输出为有效的 YAML 或 JSON 格式。\n"
    if errors:
        error_msg += "解析错误:\n"
        for fmt, err in errors.items():
            error_msg += f"  - {fmt.upper()}: {err}\n"
    
    raise ValueError(error_msg)


def _extract_keywords_from_description(name: str, description: str) -> list[str]:
    """
    从概念名称和描述中提取关键词
    
    Args:
        name: 概念名称
        description: 概念描述
        
    Returns:
        关键词列表（2-5个）
    """
    # 简单实现：提取名称中的关键词
    # 可以后续改进为更智能的关键词提取
    keywords = []
    
    # 从名称中提取（去除常见的停用词）
    stop_words = {'和', '与', '的', '了', '在', '是', '有', '对', '为', '以', '等'}
    name_words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', name)
    
    for word in name_words:
        if word not in stop_words and len(word) > 1:
            keywords.append(word)
            if len(keywords) >= 3:
                break
    
    # 如果关键词不够，从描述中补充
    if len(keywords) < 2:
        desc_words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', description)
        for word in desc_words:
            if word not in stop_words and word not in keywords and len(word) > 1:
                keywords.append(word)
                if len(keywords) >= 3:
                    break
    
    return keywords[:5] if keywords else ["学习", "掌握"]


def _ensure_unique_roadmap_id(roadmap_id: str) -> str:
    """
    确保 roadmap_id 的唯一性
    
    在 LLM 生成的描述性 roadmap_id 基础上添加 8 位 UUID 后缀，
    避免不同用户或同一用户多次请求生成相同的 roadmap_id。
    
    Args:
        roadmap_id: LLM 生成的原始 roadmap_id（如 "python-web-dev"）
        
    Returns:
        带唯一后缀的 roadmap_id（如 "python-web-dev-a1b2c3d4"）
    """
    unique_suffix = uuid.uuid4().hex[:8]
    return f"{roadmap_id}-{unique_suffix}"


def _ensure_unique_concept_ids(framework_dict: dict, roadmap_id: str) -> dict:
    """
    确保 concept_id 的唯一性
    
    在原始 concept_id（如 c-1-1-1）基础上添加 roadmap_id 前缀，
    确保跨 roadmap 的全局唯一性。
    
    格式: {roadmap_id}:c-{stage}-{module}-{concept}
    例如: python-web-dev-a1b2c3d4:c-1-1-1
    
    Args:
        framework_dict: 框架数据字典
        roadmap_id: 路线图 ID
        
    Returns:
        更新后的框架数据字典
    """
    # 创建旧 ID 到新 ID 的映射（用于更新 prerequisites）
    id_mapping = {}
    
    for stage in framework_dict.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                old_id = concept.get("concept_id")
                if old_id and not old_id.startswith(roadmap_id):
                    # 添加 roadmap_id 前缀
                    new_id = f"{roadmap_id}:{old_id}"
                    id_mapping[old_id] = new_id
                    concept["concept_id"] = new_id
    
    # 更新 prerequisites 中的引用
    for stage in framework_dict.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                prerequisites = concept.get("prerequisites", [])
                if prerequisites:
                    concept["prerequisites"] = [
                        id_mapping.get(prereq, prereq) for prereq in prerequisites
                    ]
    
    logger.debug(
        "concept_ids_updated",
        roadmap_id=roadmap_id,
        concepts_updated=len(id_mapping),
    )
    
    return framework_dict


class CurriculumArchitectAgent(BaseAgent):
    """
    课程架构师 Agent
    
    配置从环境变量加载：
    - ARCHITECT_PROVIDER: 模型提供商（默认: anthropic）
    - ARCHITECT_MODEL: 模型名称（默认: claude-3-5-sonnet-20241022）
    - ARCHITECT_BASE_URL: 自定义 API 端点（可选）
    - ARCHITECT_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "curriculum_architect",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.ARCHITECT_PROVIDER,
            model_name=model_name or settings.ARCHITECT_MODEL,
            base_url=base_url or settings.ARCHITECT_BASE_URL,
            api_key=api_key or settings.ARCHITECT_API_KEY,
            temperature=0.7,
            max_tokens=16384,  # 增加 token 限制，避免复杂路线图被截断
        )
    
    async def design(
        self,
        intent_analysis: IntentAnalysisOutput,
        user_preferences: LearningPreferences,
        roadmap_id: str,
    ) -> CurriculumDesignOutput:
        """
        设计三层学习路线图框架
        
        Args:
            intent_analysis: 需求分析结果
            user_preferences: 用户偏好
            roadmap_id: 路线图 ID（在需求分析完成后生成）
            
        Returns:
            路线图框架设计结果
        """
        # 获取语言偏好
        language_prefs = user_preferences.get_language_preferences()
        
        logger.info(
            "curriculum_design_started",
            learning_goal=user_preferences.learning_goal[:50] + "..." if len(user_preferences.learning_goal) > 50 else user_preferences.learning_goal,
            current_level=user_preferences.current_level,
            available_hours=user_preferences.available_hours_per_week,
            tech_stack_count=len(intent_analysis.key_technologies),
            primary_language=language_prefs.primary_language,
        )
        
        # 加载 System Prompt
        logger.debug("curriculum_design_loading_prompt", template="curriculum_architect.j2")
        system_prompt = self._load_system_prompt(
            "curriculum_architect.j2",
            agent_name="Curriculum Architect",
            role_description="资深课程设计师，根据用户需求设计科学的 Stage→Module→Concept 三层学习路线图，确保知识递进合理、时间分配科学。",
            user_goal=user_preferences.learning_goal,
            intent_analysis=intent_analysis,
            language_preferences=language_prefs.model_dump() if language_prefs else None,
        )
        
        # 构建语言信息
        language_info = f"- 主要语言: {language_prefs.primary_language}"
        if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
            language_info += f"\n- 次要语言: {language_prefs.secondary_language}"
        
        # 构建用户消息
        user_message = f"""
请根据以下需求分析结果设计学习路线图框架：

**需求分析结果**:
- 结构化学习目标: {intent_analysis.parsed_goal}
- 关键技术栈: {", ".join(intent_analysis.key_technologies)}
- 难度画像: {intent_analysis.difficulty_profile}
- 时间约束: {intent_analysis.time_constraint}
- 建议学习重点: {", ".join(intent_analysis.recommended_focus)}

**用户偏好**:
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时
- 当前水平: {user_preferences.current_level}
- 内容偏好: {", ".join(user_preferences.content_preference)}
{language_info}

请设计一个科学的三层学习路线图框架（Stage→Module→Concept），确保：
1. 知识递进合理，前置关系清晰
2. 时间分配符合用户的时间约束
3. 每个 Concept 都有明确的描述和预估时长
4. 总时长和推荐完成周数合理
5. **路线图标题、阶段名称、模块名称和概念描述使用用户的主要语言（{language_prefs.primary_language}）**

**重要**: 请以 YAML 格式返回结果，严格遵循 prompt 中定义的 YAML Schema 和示例格式。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        logger.info(
            "curriculum_design_calling_llm",
            model=self.model_name,
            provider=self.model_provider,
            max_tokens=self.max_tokens,
        )
        response = await self._call_llm(messages)
        
        # 解析输出
        content = response.choices[0].message.content
        logger.info(
            "curriculum_design_llm_response_received",
            response_length=len(content),
            # 记录完整输出以便调试（截取前1000字符避免日志过大）
            llm_output_preview=content[:1000] if len(content) > 1000 else content,
            llm_output_full_length=len(content),
        )
        
        # 为了方便调试，在 warning 级别记录完整输出（可以通过日志级别控制）
        logger.debug(
            "curriculum_design_llm_full_output",
            llm_output_full=content,
        )
        
        try:
            # 解析简洁格式的路线图
            logger.debug("curriculum_design_parsing_compact_format")
            result_dict = _parse_compact_roadmap(content)
            
            # 处理 roadmap_id - 使用传入的roadmap_id
            framework_dict = result_dict.get("framework", result_dict)
            framework_dict["roadmap_id"] = roadmap_id
            logger.info(
                "curriculum_design_using_roadmap_id",
                roadmap_id=roadmap_id,
            )
            
            # 确保 concept_id 唯一性（添加 roadmap_id 前缀）
            final_roadmap_id = roadmap_id
            framework_dict = _ensure_unique_concept_ids(framework_dict, final_roadmap_id)
            
            # 验证并构建输出
            logger.debug("curriculum_design_validating_schema")
            
            # 添加详细的结构检查日志
            logger.info(
                "curriculum_design_structure_check",
                has_stages=bool(framework_dict.get("stages")),
                stages_count=len(framework_dict.get("stages", [])),
                roadmap_id=framework_dict.get("roadmap_id"),
            )
            
            # 检查每个 stage 和 module 的完整性
            for stage_idx, stage in enumerate(framework_dict.get("stages", [])):
                logger.debug(
                    "stage_structure_check",
                    stage_idx=stage_idx,
                    stage_id=stage.get("stage_id"),
                    has_modules=bool(stage.get("modules")),
                    modules_count=len(stage.get("modules", [])),
                )
                for module_idx, module in enumerate(stage.get("modules", [])):
                    logger.debug(
                        "module_structure_check",
                        stage_idx=stage_idx,
                        module_idx=module_idx,
                        module_id=module.get("module_id"),
                        has_name=bool(module.get("name")),
                        has_description=bool(module.get("description")),
                        has_concepts=bool(module.get("concepts")),
                        concepts_count=len(module.get("concepts", [])),
                    )
            
            framework = RoadmapFramework.model_validate(framework_dict)
            design_rationale = result_dict.get("design_rationale", "")
            
            result = CurriculumDesignOutput(
                framework=framework,
                design_rationale=design_rationale,
            )
            
            # 统计路线图结构
            total_modules = sum(len(stage.modules) for stage in framework.stages)
            total_concepts = sum(
                len(module.concepts)
                for stage in framework.stages
                for module in stage.modules
            )
            
            logger.info(
                "curriculum_design_success",
                roadmap_id=framework.roadmap_id,
                title=framework.title[:30] + "..." if len(framework.title) > 30 else framework.title,
                stages_count=len(framework.stages),
                modules_count=total_modules,
                concepts_count=total_concepts,
                total_hours=framework.total_estimated_hours,
                completion_weeks=framework.recommended_completion_weeks,
            )
            return result
            
        except ValueError as e:
            # 检查是否是 Pydantic ValidationError
            error_str = str(e)
            if "validation error" in error_str.lower():
                # 提取验证错误的详细信息
                logger.error(
                    "curriculum_design_validation_error",
                    error=error_str,
                    parsed_data_keys=list(framework_dict.keys()) if 'framework_dict' in locals() else None,
                    stages_count=len(framework_dict.get("stages", [])) if 'framework_dict' in locals() else 0,
                    content_length=len(content),
                    content_full=content,  # 记录完整输出以便调试
                )
            else:
                logger.error(
                    "curriculum_design_parse_error",
                    error=error_str,
                    content_length=len(content),
                    content_preview=content[:500] + "..." if len(content) > 500 else content,
                )
            raise ValueError(f"LLM 输出格式解析失败: {e}\n请检查是否超出 token 限制或格式不正确")
        except Exception as e:
            logger.error(
                "curriculum_design_output_invalid",
                error=str(e),
                error_type=type(e).__name__,
                content_length=len(content),
                content_full=content,
            )
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def design_stream(
        self,
        intent_analysis: IntentAnalysisOutput,
        user_preferences: LearningPreferences,
        pre_generated_roadmap_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """
        流式设计路线图框架
        
        Args:
            intent_analysis: 需求分析结果
            user_preferences: 用户偏好
            pre_generated_roadmap_id: 预生成的路线图 ID（可选，用于加速前端跳转）
            
        Yields:
            {"type": "chunk", "content": "...", "agent": "curriculum_architect"}
            {"type": "complete", "data": {...}, "agent": "curriculum_architect"}
            {"type": "error", "error": "...", "agent": "curriculum_architect"}
        """
        # 获取语言偏好
        language_prefs = user_preferences.get_language_preferences()
        
        logger.info(
            "curriculum_design_stream_started",
            learning_goal=user_preferences.learning_goal[:50] + "..." if len(user_preferences.learning_goal) > 50 else user_preferences.learning_goal,
            current_level=user_preferences.current_level,
            available_hours=user_preferences.available_hours_per_week,
            tech_stack_count=len(intent_analysis.key_technologies),
            primary_language=language_prefs.primary_language,
        )
        
        try:
            # 加载 System Prompt（复用现有逻辑）
            logger.debug("curriculum_design_stream_loading_prompt", template="curriculum_architect.j2")
            system_prompt = self._load_system_prompt(
                "curriculum_architect.j2",
                agent_name="Curriculum Architect",
                role_description="资深课程设计师，根据用户需求设计科学的 Stage→Module→Concept 三层学习路线图，确保知识递进合理、时间分配科学。",
                user_goal=user_preferences.learning_goal,
                intent_analysis=intent_analysis,
                language_preferences=language_prefs.model_dump() if language_prefs else None,
            )
            
            # 构建语言信息
            language_info = f"- 主要语言: {language_prefs.primary_language}"
            if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
                language_info += f"\n- 次要语言: {language_prefs.secondary_language}"
            
            # 构建用户消息（复用现有逻辑）
            user_message = f"""
请根据以下需求分析结果设计学习路线图框架：

**需求分析结果**:
- 结构化学习目标: {intent_analysis.parsed_goal}
- 关键技术栈: {", ".join(intent_analysis.key_technologies)}
- 难度画像: {intent_analysis.difficulty_profile}
- 时间约束: {intent_analysis.time_constraint}
- 建议学习重点: {", ".join(intent_analysis.recommended_focus)}

**用户偏好**:
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时
- 当前水平: {user_preferences.current_level}
- 内容偏好: {", ".join(user_preferences.content_preference)}
{language_info}

请设计一个科学的三层学习路线图框架（Stage→Module→Concept），确保：
1. 知识递进合理，前置关系清晰
2. 时间分配符合用户的时间约束
3. 每个 Concept 都有明确的描述和预估时长
4. 总时长和推荐完成周数合理
5. **路线图标题、阶段名称、模块名称和概念描述使用用户的主要语言（{language_prefs.primary_language}）**

**重要**: 请以 YAML 格式返回结果，严格遵循 prompt 中定义的 YAML Schema 和示例格式。
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            # 流式调用 LLM
            logger.info(
                "curriculum_design_stream_calling_llm",
                model=self.model_name,
                provider=self.model_provider,
                max_tokens=self.max_tokens,
            )
            
            full_content = ""
            async for chunk in self._call_llm_stream(messages):
                full_content += chunk
                # 推送流式片段
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "agent": "curriculum_architect"
                }
            
            logger.debug(
                "curriculum_design_stream_response_received",
                response_length=len(full_content),
            )
            
            # 解析简洁格式的路线图
            logger.debug("curriculum_design_stream_parsing_compact_format")
            result_dict = _parse_compact_roadmap(full_content)
            
            # 处理 roadmap_id
            framework_dict = result_dict.get("framework", result_dict)
            
            if pre_generated_roadmap_id:
                # 使用预生成的 roadmap_id（来自 API 层）
                framework_dict["roadmap_id"] = pre_generated_roadmap_id
                logger.info(
                    "curriculum_design_stream_using_pre_generated_roadmap_id",
                    pre_generated_id=pre_generated_roadmap_id,
                )
            else:
                # 确保 roadmap_id 唯一性（兼容旧的调用方式）
                original_roadmap_id = framework_dict.get("roadmap_id", "roadmap")
                unique_roadmap_id = _ensure_unique_roadmap_id(original_roadmap_id)
                framework_dict["roadmap_id"] = unique_roadmap_id
                logger.info(
                    "curriculum_design_stream_roadmap_id_ensured_unique",
                    original_id=original_roadmap_id,
                    unique_id=unique_roadmap_id,
                )
            
            # 确保 concept_id 唯一性（添加 roadmap_id 前缀）
            final_roadmap_id = framework_dict["roadmap_id"]
            framework_dict = _ensure_unique_concept_ids(framework_dict, final_roadmap_id)
            
            # 验证并构建输出
            logger.debug("curriculum_design_stream_validating_schema")
            framework = RoadmapFramework.model_validate(framework_dict)
            design_rationale = result_dict.get("design_rationale", "")
            
            # 统计路线图结构
            total_modules = sum(len(stage.modules) for stage in framework.stages)
            total_concepts = sum(
                len(module.concepts)
                for stage in framework.stages
                for module in stage.modules
            )
            
            logger.info(
                "curriculum_design_stream_success",
                roadmap_id=framework.roadmap_id,
                title=framework.title[:30] + "..." if len(framework.title) > 30 else framework.title,
                stages_count=len(framework.stages),
                modules_count=total_modules,
                concepts_count=total_concepts,
                total_hours=framework.total_estimated_hours,
                completion_weeks=framework.recommended_completion_weeks,
            )
            
            # 推送最终结果
            yield {
                "type": "complete",
                "data": {
                    "framework": framework.model_dump(),
                    "design_rationale": design_rationale,
                },
                "agent": "curriculum_architect"
            }
            
        except ValueError as e:
            error_msg = f"LLM 输出格式解析失败: {str(e)}"
            logger.error(
                "curriculum_design_stream_parse_error",
                error=str(e),
                content_length=len(full_content) if 'full_content' in locals() else 0,
                content_preview=full_content[:500] + "..." if 'full_content' in locals() and len(full_content) > 500 else full_content if 'full_content' in locals() else "",
            )
            
            # 如果有trace_id可以记录到execution_logs (从调用方传入)
            # 这里先发送错误事件给调用方处理
            
            yield {
                "type": "error",
                "error": f"{error_msg}\n请检查是否超出 token 限制或格式不正确",
                "agent": "curriculum_architect",
                "details": {
                    "error_type": "parse_error",
                    "content_preview": full_content[:500] if 'full_content' in locals() else "",
                }
            }
        except Exception as e:
            logger.error("curriculum_design_stream_error", error=str(e), error_type=type(e).__name__)
            yield {
                "type": "error",
                "error": str(e),
                "agent": "curriculum_architect",
                "details": {
                    "error_type": type(e).__name__,
                }
            }
    
    async def execute(self, input_data: dict) -> CurriculumDesignOutput:
        """实现基类的抽象方法"""
        return await self.design(
            intent_analysis=input_data["intent_analysis"],
            user_preferences=input_data["user_preferences"],
            roadmap_id=input_data["roadmap_id"],
        )

