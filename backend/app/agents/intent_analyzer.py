"""
Intent Analyzer Agent（需求分析师）
"""
import json
from typing import AsyncIterator
from app.agents.base import BaseAgent
from app.models.domain import UserRequest, IntentAnalysisOutput
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
        
        # 加载 System Prompt
        logger.debug("intent_analysis_loading_prompt", template="intent_analyzer.j2")
        system_prompt = self._load_system_prompt(
            "intent_analyzer.j2",
            agent_name="Intent Analyzer",
            role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。",
            user_goal=user_request.preferences.learning_goal,
        )
        
        # 构建用户消息
        user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {user_request.preferences.learning_goal}
**每周可投入时间**: {user_request.preferences.available_hours_per_week} 小时
**学习动机**: {user_request.preferences.motivation}
**当前水平**: {user_request.preferences.current_level}
**职业背景**: {user_request.preferences.career_background}
**内容偏好**: {", ".join(user_request.preferences.content_preference)}
{"**期望完成时间**: " + str(user_request.preferences.target_deadline) if user_request.preferences.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请提取关键技术栈、难度画像、时间约束，并给出学习重点建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。
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
            
            # 使用 Pydantic 验证输出格式
            result = IntentAnalysisOutput.model_validate(result_dict)
            logger.info(
                "intent_analysis_success",
                user_id=user_request.user_id,
                tech_stack_count=len(result.key_technologies) if result.key_technologies else 0,
                learning_priority_count=len(result.recommended_focus) if result.recommended_focus else 0,
                difficulty_profile=result.difficulty_profile if result.difficulty_profile else None,
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
            # 加载 System Prompt（复用现有逻辑）
            logger.debug("intent_analysis_stream_loading_prompt", template="intent_analyzer.j2")
            system_prompt = self._load_system_prompt(
                "intent_analyzer.j2",
                agent_name="Intent Analyzer",
                role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。",
                user_goal=user_request.preferences.learning_goal,
            )
            
            # 构建用户消息（复用现有逻辑）
            user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {user_request.preferences.learning_goal}
**每周可投入时间**: {user_request.preferences.available_hours_per_week} 小时
**学习动机**: {user_request.preferences.motivation}
**当前水平**: {user_request.preferences.current_level}
**职业背景**: {user_request.preferences.career_background}
**内容偏好**: {", ".join(user_request.preferences.content_preference)}
{"**期望完成时间**: " + str(user_request.preferences.target_deadline) if user_request.preferences.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请提取关键技术栈、难度画像、时间约束，并给出学习重点建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。
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
            
            # 使用 Pydantic 验证输出格式
            result = IntentAnalysisOutput.model_validate(result_dict)
            logger.info(
                "intent_analysis_stream_success",
                user_id=user_request.user_id,
                tech_stack_count=len(result.key_technologies) if result.key_technologies else 0,
                learning_priority_count=len(result.recommended_focus) if result.recommended_focus else 0,
                difficulty_profile=result.difficulty_profile if result.difficulty_profile else None,
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
        """实现基类的抽象方法"""
        return await self.analyze(input_data)

