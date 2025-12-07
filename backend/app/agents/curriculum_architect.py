"""
Curriculum Architect Agent（课程架构师）
"""
import json
import re
import uuid
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
    解析简洁格式的路线图（支持文本格式或JSON格式）
    
    支持两种格式：
    1. 文本格式（带 ===ROADMAP START=== 标记）
    2. JSON格式（可能被 ```json 包裹）
    
    输入格式示例（文本）：
    ===ROADMAP START===
    ROADMAP_ID: python-web-dev
    TITLE: Python Web开发完整学习路线
    TOTAL_HOURS: 120
    WEEKS: 8
    
    Stage 1: 基础知识（掌握Python语法）[30小时]
      Module 1.1: Python核心语法（学习Python基础）
        - Concept: 变量与数据类型（理解基本数据结构）[2小时]
    
    DESIGN_RATIONALE: 设计说明
    ===ROADMAP END===
    
    Args:
        content: LLM 响应内容
        
    Returns:
        符合 CurriculumDesignOutput 的字典
        
    Raises:
        ValueError: 无法解析文本格式
    """
    try:
        # 1. 先尝试JSON格式
        json_content = _try_extract_json(content)
        if json_content:
            logger.debug("curriculum_design_detected_json_format")
            return _parse_json_roadmap(json_content)
        
        # 2. 尝试文本格式
        logger.debug("curriculum_design_parsing_text_format")
        
        # 提取路线图内容（去除标记）
        start_marker = "===ROADMAP START==="
        end_marker = "===ROADMAP END==="
        
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            # 提供更详细的错误信息
            content_preview = content[:300] if len(content) > 300 else content
            raise ValueError(
                f"无法识别输出格式。期望: (1) JSON格式（可被```json包裹）或 (2) 文本格式（带{start_marker}标记）。"
                f"\n内容预览: {content_preview}..."
            )
        
        roadmap_content = content[start_idx + len(start_marker):end_idx].strip()
        lines = roadmap_content.split('\n')
        
        # 解析元信息
        roadmap_id = None
        title = None
        total_hours = 0
        weeks = 0
        design_rationale = ""
        
        stages = []
        current_stage = None
        current_module = None
        stage_counter = 0
        module_counter_in_stage = 0
        concept_counter_in_module = 0
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # 解析元信息
            if line_stripped.startswith("ROADMAP_ID:"):
                roadmap_id = line_stripped.split(":", 1)[1].strip()
            elif line_stripped.startswith("TITLE:"):
                title = line_stripped.split(":", 1)[1].strip()
            elif line_stripped.startswith("TOTAL_HOURS:"):
                total_hours = float(line_stripped.split(":", 1)[1].strip())
            elif line_stripped.startswith("WEEKS:"):
                weeks = int(line_stripped.split(":", 1)[1].strip())
            elif line_stripped.startswith("DESIGN_RATIONALE:"):
                design_rationale = line_stripped.split(":", 1)[1].strip()
            
            # 解析 Stage
            elif line_stripped.startswith("Stage "):
                if current_stage:
                    stages.append(current_stage)
                
                stage_counter += 1
                module_counter_in_stage = 0
                
                # 格式: Stage 1: 基础知识（描述）[30小时]
                # 支持中英文括号和小时标记
                match = re.match(r'Stage\s+(\d+):\s*([^（(]+)[（(]([^）)]+)[）)]\[([0-9.]+)(?:小时|hours?)\]', line_stripped, re.IGNORECASE)
                if not match:
                    logger.warning("stage_parse_failed", line=line_stripped, line_length=len(line_stripped))
                    continue
                
                stage_order = int(match.group(1))
                stage_name = match.group(2).strip()
                stage_desc = match.group(3).strip()
                
                current_stage = {
                    "stage_id": f"stage-{stage_order}",
                    "name": stage_name,
                    "description": stage_desc,
                    "order": stage_order,
                    "modules": []
                }
                current_module = None
            
            # 解析 Module
            elif line_stripped.startswith("Module "):
                module_counter_in_stage += 1
                concept_counter_in_module = 0
                
                # 格式: Module 1.1: Python核心语法（描述）
                # 支持中英文括号
                match = re.match(r'Module\s+\d+\.(\d+):\s*([^（(]+)[（(]([^）)]+)[）)]', line_stripped)
                if not match:
                    logger.warning("module_parse_failed", line=line_stripped, line_length=len(line_stripped))
                    continue
                
                module_num = int(match.group(1))
                module_name = match.group(2).strip()
                module_desc = match.group(3).strip()
                
                current_module = {
                    "module_id": f"mod-{stage_counter}-{module_counter_in_stage}",
                    "name": module_name,
                    "description": module_desc,
                    "concepts": []
                }
                
                if current_stage:
                    current_stage["modules"].append(current_module)
            
            # 解析 Concept
            elif line_stripped.startswith("- Concept:"):
                if not current_module:
                    logger.warning("concept_without_module", line=line_stripped)
                    continue
                
                concept_counter_in_module += 1
                
                # 格式: - Concept: 变量与数据类型（描述）[2小时]
                # 支持中英文括号和小时标记
                match = re.match(r'-\s*Concept:\s*([^（(]+)[（(]([^）)]+)[）)]\[([0-9.]+)(?:小时|hours?)\]', line_stripped, re.IGNORECASE)
                if not match:
                    logger.warning("concept_parse_failed", line=line_stripped, line_length=len(line_stripped))
                    continue
                
                concept_name = match.group(1).strip()
                concept_desc = match.group(2).strip()
                concept_hours = float(match.group(3))
                
                # 自动推断难度
                if concept_hours <= 2:
                    difficulty = "easy"
                elif concept_hours <= 4:
                    difficulty = "medium"
                else:
                    difficulty = "hard"
                
                concept = {
                    "concept_id": f"c-{stage_counter}-{module_counter_in_stage}-{concept_counter_in_module}",
                    "name": concept_name,
                    "description": concept_desc,
                    "estimated_hours": concept_hours,
                    "prerequisites": [],  # 初始为空，后续可通过其他流程补充
                    "difficulty": difficulty,
                    "keywords": _extract_keywords_from_description(concept_name, concept_desc),
                    "content_status": "pending",
                    "content_ref": None,
                    "content_version": "v1",
                    "content_summary": None
                }
                
                current_module["concepts"].append(concept)
        
        # 添加最后一个 stage
        if current_stage:
            stages.append(current_stage)
        
        # 构建完整结果
        result = {
            "framework": {
                "roadmap_id": roadmap_id or "roadmap",
                "title": title or "学习路线图",
                "stages": stages,
                "total_estimated_hours": total_hours,
                "recommended_completion_weeks": weeks
            },
            "design_rationale": design_rationale
        }
        
        logger.info(
            "compact_roadmap_parsed",
            stages_count=len(stages),
            total_hours=total_hours,
            weeks=weeks,
        )
        
        return result
        
    except Exception as e:
        # 详细记录解析错误，包括完整内容和具体的错误位置
        logger.error(
            "compact_roadmap_parse_error",
            error=str(e),
            error_type=type(e).__name__,
            content_preview=content[:500],
            content_length=len(content),
            has_start_marker=start_marker in content if 'start_marker' in locals() else False,
            has_end_marker=end_marker in content if 'end_marker' in locals() else False,
            stages_parsed=len(stages) if 'stages' in locals() else 0,
        )
        # 如果解析失败，尝试记录到日志系统（如果有trace_id的话会在调用方记录）
        raise ValueError(f"无法解析简洁格式的路线图: {e}")


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
    
    def __init__(self):
        super().__init__(
            agent_id="curriculum_architect",
            model_provider=settings.ARCHITECT_PROVIDER,
            model_name=settings.ARCHITECT_MODEL,
            base_url=settings.ARCHITECT_BASE_URL,
            api_key=settings.ARCHITECT_API_KEY,
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

请以 JSON 格式返回结果，严格遵循输出 Schema。
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
        logger.debug(
            "curriculum_design_llm_response_received",
            response_length=len(content),
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
            logger.error(
                "curriculum_design_parse_error",
                error=str(e),
                content_length=len(content),
                content_preview=content[:500] + "..." if len(content) > 500 else content,
            )
            raise ValueError(f"LLM 输出格式解析失败: {e}\n请检查是否超出 token 限制或格式不正确")
        except Exception as e:
            logger.error("curriculum_design_output_invalid", error=str(e), content=content)
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

请以 JSON 格式返回结果，严格遵循输出 Schema。
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
        )

