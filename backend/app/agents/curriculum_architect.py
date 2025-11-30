"""
Curriculum Architect Agent（课程架构师）
"""
import json
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
            max_tokens=8192,
        )
    
    async def design(
        self,
        intent_analysis: IntentAnalysisOutput,
        user_preferences: LearningPreferences,
    ) -> CurriculumDesignOutput:
        """
        设计三层学习路线图框架
        
        Args:
            intent_analysis: 需求分析结果
            user_preferences: 用户偏好
            
        Returns:
            路线图框架设计结果
        """
        logger.info(
            "curriculum_design_started",
            learning_goal=user_preferences.learning_goal[:50] + "..." if len(user_preferences.learning_goal) > 50 else user_preferences.learning_goal,
            current_level=user_preferences.current_level,
            available_hours=user_preferences.available_hours_per_week,
            tech_stack_count=len(intent_analysis.key_technologies),
        )
        
        # 加载 System Prompt
        logger.debug("curriculum_design_loading_prompt", template="curriculum_architect.j2")
        system_prompt = self._load_system_prompt(
            "curriculum_architect.j2",
            agent_name="Curriculum Architect",
            role_description="资深课程设计师，根据用户需求设计科学的 Stage→Module→Concept 三层学习路线图，确保知识递进合理、时间分配科学。",
            user_goal=user_preferences.learning_goal,
            intent_analysis=intent_analysis,
        )
        
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

请设计一个科学的三层学习路线图框架（Stage→Module→Concept），确保：
1. 知识递进合理，前置关系清晰
2. 时间分配符合用户的时间约束
3. 每个 Concept 都有明确的描述和预估时长
4. 总时长和推荐完成周数合理

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
            logger.debug("curriculum_design_parsing_json")
            result_dict = json.loads(content)
            
            # 确保 roadmap_id 唯一性
            framework_dict = result_dict.get("framework", result_dict)
            original_roadmap_id = framework_dict.get("roadmap_id", "roadmap")
            unique_roadmap_id = _ensure_unique_roadmap_id(original_roadmap_id)
            framework_dict["roadmap_id"] = unique_roadmap_id
            
            logger.info(
                "curriculum_design_roadmap_id_ensured_unique",
                original_id=original_roadmap_id,
                unique_id=unique_roadmap_id,
            )
            
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
            
        except json.JSONDecodeError as e:
            logger.error("curriculum_design_json_parse_error", error=str(e), content=content)
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("curriculum_design_output_invalid", error=str(e), content=content)
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def design_stream(
        self,
        intent_analysis: IntentAnalysisOutput,
        user_preferences: LearningPreferences,
    ) -> AsyncIterator[dict]:
        """
        流式设计路线图框架
        
        Args:
            intent_analysis: 需求分析结果
            user_preferences: 用户偏好
            
        Yields:
            {"type": "chunk", "content": "...", "agent": "curriculum_architect"}
            {"type": "complete", "data": {...}, "agent": "curriculum_architect"}
            {"type": "error", "error": "...", "agent": "curriculum_architect"}
        """
        logger.info(
            "curriculum_design_stream_started",
            learning_goal=user_preferences.learning_goal[:50] + "..." if len(user_preferences.learning_goal) > 50 else user_preferences.learning_goal,
            current_level=user_preferences.current_level,
            available_hours=user_preferences.available_hours_per_week,
            tech_stack_count=len(intent_analysis.key_technologies),
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
            )
            
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

请设计一个科学的三层学习路线图框架（Stage→Module→Concept），确保：
1. 知识递进合理，前置关系清晰
2. 时间分配符合用户的时间约束
3. 每个 Concept 都有明确的描述和预估时长
4. 总时长和推荐完成周数合理

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
            
            # 解析完整 JSON（复用现有逻辑）
            # 提取 JSON（可能包含 markdown 代码块）
            content = full_content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # 解析 JSON
            logger.debug("curriculum_design_stream_parsing_json")
            result_dict = json.loads(content)
            
            # 确保 roadmap_id 唯一性
            framework_dict = result_dict.get("framework", result_dict)
            original_roadmap_id = framework_dict.get("roadmap_id", "roadmap")
            unique_roadmap_id = _ensure_unique_roadmap_id(original_roadmap_id)
            framework_dict["roadmap_id"] = unique_roadmap_id
            
            logger.info(
                "curriculum_design_stream_roadmap_id_ensured_unique",
                original_id=original_roadmap_id,
                unique_id=unique_roadmap_id,
            )
            
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
            
        except json.JSONDecodeError as e:
            logger.error("curriculum_design_stream_json_parse_error", error=str(e), content=full_content[:200] if 'full_content' in locals() else "")
            yield {
                "type": "error",
                "error": f"LLM 输出不是有效的 JSON 格式: {str(e)}",
                "agent": "curriculum_architect"
            }
        except Exception as e:
            logger.error("curriculum_design_stream_error", error=str(e), error_type=type(e).__name__)
            yield {
                "type": "error",
                "error": str(e),
                "agent": "curriculum_architect"
            }
    
    async def execute(self, input_data: dict) -> CurriculumDesignOutput:
        """实现基类的抽象方法"""
        return await self.design(
            intent_analysis=input_data["intent_analysis"],
            user_preferences=input_data["user_preferences"],
        )

