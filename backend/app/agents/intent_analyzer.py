"""
Intent Analyzer Agent（需求分析师）
"""
import json
from typing import AsyncIterator
from app.agents.base import BaseAgent
from app.models.domain import UserRequest, IntentAnalysisOutput, LanguagePreferences
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class IntentAnalyzerAgent(BaseAgent):
    """
    需求分析师 Agent
    
    配置从环境变量加载：
    - ANALYZER_PROVIDER: 模型提供商（默认: openai）
    - ANALYZER_MODEL: 模型名称（默认: gpt-4o-mini）
    - ANALYZER_BASE_URL: 自定义 API 端点（可选）
    - ANALYZER_API_KEY: API 密钥（必需）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="intent_analyzer",
            model_provider=settings.ANALYZER_PROVIDER,
            model_name=settings.ANALYZER_MODEL,
            base_url=settings.ANALYZER_BASE_URL,
            api_key=settings.ANALYZER_API_KEY,
            temperature=0.3,
            max_tokens=2048,
        )
    
    async def analyze(self, user_request: UserRequest) -> IntentAnalysisOutput:
        """
        分析用户学习需求
        
        Args:
            user_request: 用户请求
            
        Returns:
            结构化的需求分析结果
        """
        logger.info(
            "intent_analysis_started",
            user_id=user_request.user_id,
            learning_goal=user_request.preferences.learning_goal[:50] + "..." if len(user_request.preferences.learning_goal) > 50 else user_request.preferences.learning_goal,
            current_level=user_request.preferences.current_level,
            available_hours=user_request.preferences.available_hours_per_week,
        )
        
        # 构建用户画像信息（包含双语偏好）
        prefs = user_request.preferences
        
        # 获取语言偏好
        language_prefs = prefs.get_language_preferences()
        
        user_profile = None
        if prefs.industry or prefs.current_role or prefs.tech_stack or language_prefs:
            user_profile = {
                "industry": prefs.industry,
                "current_role": prefs.current_role,
                "tech_stack": prefs.tech_stack or [],
                "primary_language": language_prefs.primary_language,
                "secondary_language": language_prefs.secondary_language,
                # 向后兼容
                "preferred_language": language_prefs.primary_language,
            }
        
        # 加载 System Prompt
        logger.debug("intent_analysis_loading_prompt", template="intent_analyzer.j2")
        system_prompt = self._load_system_prompt(
            "intent_analyzer.j2",
            agent_name="Intent Analyzer",
            role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。结合用户画像和语言偏好进行个性化分析。",
            user_goal=prefs.learning_goal,
            available_hours_per_week=prefs.available_hours_per_week,
            motivation=prefs.motivation,
            current_level=prefs.current_level,
            career_background=prefs.career_background,
            content_preference=prefs.content_preference,
            user_profile=user_profile,
            language_preferences=language_prefs.model_dump(),
        )
        
        # 构建用户消息
        profile_info = ""
        if user_profile:
            profile_parts = []
            if user_profile.get("industry"):
                profile_parts.append(f"**所属行业**: {user_profile['industry']}")
            if user_profile.get("current_role"):
                profile_parts.append(f"**当前职位**: {user_profile['current_role']}")
            if user_profile.get("tech_stack"):
                tech_list = [f"{t.get('technology', '')}({t.get('proficiency', '')})" for t in user_profile["tech_stack"]]
                profile_parts.append(f"**已掌握技术**: {', '.join(tech_list)}")
            if profile_parts:
                profile_info = "\n" + "\n".join(profile_parts)
        
        # 构建语言偏好信息
        language_info = f"\n**主要语言**: {language_prefs.primary_language}"
        if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
            language_info += f"\n**次要语言**: {language_prefs.secondary_language}"
        
        user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {prefs.learning_goal}
**每周可投入时间**: {prefs.available_hours_per_week} 小时
**学习动机**: {prefs.motivation}
**当前水平**: {prefs.current_level}
**职业背景**: {prefs.career_background}
**内容偏好**: {", ".join(prefs.content_preference)}{profile_info}{language_info}
{"**期望完成时间**: " + str(prefs.target_deadline) if prefs.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请结合用户画像和语言偏好进行个性化分析，提取关键技术栈、难度画像、时间约束、技能差距分析，并给出个性化学习建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。

**特别注意**：必须生成 roadmap_id 字段，格式为"英文语义短语-8位随机字符"（例如：python-web-development-a7f3e2c1）。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        logger.info(
            "intent_analysis_calling_llm",
            user_id=user_request.user_id,
            model=self.model_name,
            provider=self.model_provider,
            primary_language=language_prefs.primary_language,
            secondary_language=language_prefs.secondary_language,
        )
        response = await self._call_llm(messages)
        
        # 解析输出（假设 LLM 返回 JSON 格式）
        content = response.choices[0].message.content
        logger.debug(
            "intent_analysis_llm_response_received",
            user_id=user_request.user_id,
            response_length=len(content),
        )
        
        # 尝试提取 JSON（可能包含 markdown 代码块）
        try:
            # 如果内容包含 JSON 代码块，提取 JSON 部分
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # 解析 JSON
            logger.debug("intent_analysis_parsing_json", user_id=user_request.user_id)
            result_dict = json.loads(content)
            
            # 确保 language_preferences 被正确设置（LLM 可能不返回或返回格式不对）
            if "language_preferences" not in result_dict or result_dict["language_preferences"] is None:
                # 使用用户输入的语言偏好
                result_dict["language_preferences"] = language_prefs.model_dump()
            else:
                # 验证并补充 LLM 返回的语言偏好
                llm_lang_prefs = result_dict["language_preferences"]
                if not isinstance(llm_lang_prefs, dict):
                    result_dict["language_preferences"] = language_prefs.model_dump()
                else:
                    # 确保有有效的资源分配比例
                    if "resource_ratio" not in llm_lang_prefs:
                        llm_lang_prefs["resource_ratio"] = language_prefs.get_effective_ratio()
            
            # 使用 Pydantic 验证输出格式
            result = IntentAnalysisOutput.model_validate(result_dict)
            logger.info(
                "intent_analysis_success",
                user_id=user_request.user_id,
                tech_stack_count=len(result.key_technologies) if result.key_technologies else 0,
                learning_priority_count=len(result.recommended_focus) if result.recommended_focus else 0,
                difficulty_profile=result.difficulty_profile if result.difficulty_profile else None,
                primary_language=result.language_preferences.primary_language if result.language_preferences else None,
                secondary_language=result.language_preferences.secondary_language if result.language_preferences else None,
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error("intent_analysis_json_parse_error", error=str(e), content=content[:200])
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("intent_analysis_output_invalid", error=str(e), content=content[:200])
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def analyze_stream(
        self, 
        user_request: UserRequest
    ) -> AsyncIterator[dict]:
        """
        流式分析用户需求
        
        Args:
            user_request: 用户请求
            
        Yields:
            {"type": "chunk", "content": "...", "agent": "intent_analyzer"}
            {"type": "complete", "data": {...}, "agent": "intent_analyzer"}
            {"type": "error", "error": "...", "agent": "intent_analyzer"}
        """
        logger.info(
            "intent_analysis_stream_started",
            user_id=user_request.user_id,
            learning_goal=user_request.preferences.learning_goal[:50] + "..." if len(user_request.preferences.learning_goal) > 50 else user_request.preferences.learning_goal,
            current_level=user_request.preferences.current_level,
            available_hours=user_request.preferences.available_hours_per_week,
        )
        
        try:
            prefs = user_request.preferences
            
            # 获取语言偏好
            language_prefs = prefs.get_language_preferences()
            
            # 构建用户画像信息（包含双语偏好）
            user_profile = None
            if prefs.industry or prefs.current_role or prefs.tech_stack or language_prefs:
                user_profile = {
                    "industry": prefs.industry,
                    "current_role": prefs.current_role,
                    "tech_stack": prefs.tech_stack or [],
                    "primary_language": language_prefs.primary_language,
                    "secondary_language": language_prefs.secondary_language,
                    # 向后兼容
                    "preferred_language": language_prefs.primary_language,
                }
            
            # 加载 System Prompt（复用现有逻辑）
            logger.debug("intent_analysis_stream_loading_prompt", template="intent_analyzer.j2")
            system_prompt = self._load_system_prompt(
                "intent_analyzer.j2",
                agent_name="Intent Analyzer",
                role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。结合用户画像和语言偏好进行个性化分析。",
                user_goal=prefs.learning_goal,
                available_hours_per_week=prefs.available_hours_per_week,
                motivation=prefs.motivation,
                current_level=prefs.current_level,
                career_background=prefs.career_background,
                content_preference=prefs.content_preference,
                user_profile=user_profile,
                language_preferences=language_prefs.model_dump(),
            )
            
            # 构建用户消息（复用现有逻辑）
            profile_info = ""
            if user_profile:
                profile_parts = []
                if user_profile.get("industry"):
                    profile_parts.append(f"**所属行业**: {user_profile['industry']}")
                if user_profile.get("current_role"):
                    profile_parts.append(f"**当前职位**: {user_profile['current_role']}")
                if user_profile.get("tech_stack"):
                    tech_list = [f"{t.get('technology', '')}({t.get('proficiency', '')})" for t in user_profile["tech_stack"]]
                    profile_parts.append(f"**已掌握技术**: {', '.join(tech_list)}")
                if profile_parts:
                    profile_info = "\n" + "\n".join(profile_parts)
            
            # 构建语言偏好信息
            language_info = f"\n**主要语言**: {language_prefs.primary_language}"
            if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
                language_info += f"\n**次要语言**: {language_prefs.secondary_language}"
            
            user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {prefs.learning_goal}
**每周可投入时间**: {prefs.available_hours_per_week} 小时
**学习动机**: {prefs.motivation}
**当前水平**: {prefs.current_level}
**职业背景**: {prefs.career_background}
**内容偏好**: {", ".join(prefs.content_preference)}{profile_info}{language_info}
{"**期望完成时间**: " + str(prefs.target_deadline) if prefs.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请结合用户画像和语言偏好进行个性化分析，提取关键技术栈、难度画像、时间约束、技能差距分析，并给出个性化学习建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。

**特别注意**：必须生成 roadmap_id 字段，格式为"英文语义短语-8位随机字符"（例如：python-web-development-a7f3e2c1）。
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            # 流式调用 LLM 并累积内容
            logger.info(
                "intent_analysis_stream_calling_llm",
                user_id=user_request.user_id,
                model=self.model_name,
                provider=self.model_provider,
            )
            
            full_content = ""
            async for chunk in self._call_llm_stream(messages):
                full_content += chunk
                # 推送流式片段给前端
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "agent": "intent_analyzer"
                }
            
            logger.debug(
                "intent_analysis_stream_response_received",
                user_id=user_request.user_id,
                response_length=len(full_content),
            )
            
            # 解析完整 JSON（复用现有的提取和验证逻辑）
            # 如果内容包含 JSON 代码块，提取 JSON 部分
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
            logger.debug("intent_analysis_stream_parsing_json", user_id=user_request.user_id)
            result_dict = json.loads(content)
            
            # 确保 language_preferences 被正确设置（LLM 可能不返回或返回格式不对）
            if "language_preferences" not in result_dict or result_dict["language_preferences"] is None:
                # 使用用户输入的语言偏好
                result_dict["language_preferences"] = language_prefs.model_dump()
            else:
                # 验证并补充 LLM 返回的语言偏好
                llm_lang_prefs = result_dict["language_preferences"]
                if not isinstance(llm_lang_prefs, dict):
                    result_dict["language_preferences"] = language_prefs.model_dump()
                else:
                    # 确保有有效的资源分配比例
                    if "resource_ratio" not in llm_lang_prefs:
                        llm_lang_prefs["resource_ratio"] = language_prefs.get_effective_ratio()
            
            # 使用 Pydantic 验证输出格式
            result = IntentAnalysisOutput.model_validate(result_dict)
            logger.info(
                "intent_analysis_stream_success",
                user_id=user_request.user_id,
                tech_stack_count=len(result.key_technologies) if result.key_technologies else 0,
                learning_priority_count=len(result.recommended_focus) if result.recommended_focus else 0,
                difficulty_profile=result.difficulty_profile if result.difficulty_profile else None,
                primary_language=result.language_preferences.primary_language if result.language_preferences else None,
                secondary_language=result.language_preferences.secondary_language if result.language_preferences else None,
            )
            
            # 推送最终结果
            yield {
                "type": "complete",
                "data": result.model_dump(),
                "agent": "intent_analyzer"
            }
            
        except json.JSONDecodeError as e:
            logger.error("intent_analysis_stream_json_parse_error", error=str(e), content=full_content[:200] if 'full_content' in locals() else "")
            yield {
                "type": "error",
                "error": f"LLM 输出不是有效的 JSON 格式: {str(e)}",
                "agent": "intent_analyzer"
            }
        except Exception as e:
            logger.error("intent_analysis_stream_error", error=str(e), error_type=type(e).__name__)
            yield {
                "type": "error",
                "error": str(e),
                "agent": "intent_analyzer"
            }
    
    async def execute(self, input_data: UserRequest) -> IntentAnalysisOutput:
        """
        分析用户学习需求
        
        Args:
            input_data: 用户请求
            
        Returns:
            结构化的需求分析结果
        """
        user_request = input_data
        logger.info(
            "intent_analysis_started",
            user_id=user_request.user_id,
            learning_goal=user_request.preferences.learning_goal[:50] + "..." if len(user_request.preferences.learning_goal) > 50 else user_request.preferences.learning_goal,
            current_level=user_request.preferences.current_level,
            available_hours=user_request.preferences.available_hours_per_week,
        )
        
        # 构建用户画像信息（包含双语偏好）
        prefs = user_request.preferences
        
        # 获取语言偏好
        language_prefs = prefs.get_language_preferences()
        
        user_profile = None
        if prefs.industry or prefs.current_role or prefs.tech_stack or language_prefs:
            user_profile = {
                "industry": prefs.industry,
                "current_role": prefs.current_role,
                "tech_stack": prefs.tech_stack or [],
                "primary_language": language_prefs.primary_language,
                "secondary_language": language_prefs.secondary_language,
                # 向后兼容
                "preferred_language": language_prefs.primary_language,
            }
        
        # 加载 System Prompt
        logger.debug("intent_analysis_loading_prompt", template="intent_analyzer.j2")
        system_prompt = self._load_system_prompt(
            "intent_analyzer.j2",
            agent_name="Intent Analyzer",
            role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。结合用户画像和语言偏好进行个性化分析。",
            user_goal=prefs.learning_goal,
            available_hours_per_week=prefs.available_hours_per_week,
            motivation=prefs.motivation,
            current_level=prefs.current_level,
            career_background=prefs.career_background,
            content_preference=prefs.content_preference,
            user_profile=user_profile,
            language_preferences=language_prefs.model_dump(),
        )
        
        # 构建用户消息
        profile_info = ""
        if user_profile:
            profile_parts = []
            if user_profile.get("industry"):
                profile_parts.append(f"**所属行业**: {user_profile['industry']}")
            if user_profile.get("current_role"):
                profile_parts.append(f"**当前职位**: {user_profile['current_role']}")
            if user_profile.get("tech_stack"):
                tech_list = [f"{t.get('technology', '')}({t.get('proficiency', '')})" for t in user_profile["tech_stack"]]
                profile_parts.append(f"**已掌握技术**: {', '.join(tech_list)}")
            if profile_parts:
                profile_info = "\n" + "\n".join(profile_parts)
        
        # 构建语言偏好信息
        language_info = f"\n**主要语言**: {language_prefs.primary_language}"
        if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
            language_info += f"\n**次要语言**: {language_prefs.secondary_language}"
        
        user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {prefs.learning_goal}
**每周可投入时间**: {prefs.available_hours_per_week} 小时
**学习动机**: {prefs.motivation}
**当前水平**: {prefs.current_level}
**职业背景**: {prefs.career_background}
**内容偏好**: {", ".join(prefs.content_preference)}{profile_info}{language_info}
{"**期望完成时间**: " + str(prefs.target_deadline) if prefs.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请结合用户画像和语言偏好进行个性化分析，提取关键技术栈、难度画像、时间约束、技能差距分析，并给出个性化学习建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。

**特别注意**：必须生成 roadmap_id 字段，格式为"英文语义短语-8位随机字符"（例如：python-web-development-a7f3e2c1）。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        logger.debug("intent_analysis_calling_llm", model=self.model_name)
        
        # 调用 LLM
        response = await self._call_llm(messages)
        
        # 解析响应
        content = response.choices[0].message.content
        logger.debug("intent_analysis_llm_response", content_length=len(content))
        
        # 尝试解析 JSON
        try:
            result_data = json.loads(content)
            
            # 验证并构造输出
            result = IntentAnalysisOutput(**result_data)
            
            logger.info(
                "intent_analysis_completed",
                roadmap_id=result.roadmap_id,
                topic=result.analysis.primary_topic,
                difficulty_score=result.analysis.overall_difficulty_score,
                estimated_hours=result.analysis.total_estimated_hours,
                skills_to_learn_count=len(result.analysis.skill_gaps.skills_to_learn),
                recommendations_count=len(result.recommendations),
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("intent_analysis_json_decode_error", error=str(e), content=content[:500])
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("intent_analysis_output_invalid", error=str(e), content=content)
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")

