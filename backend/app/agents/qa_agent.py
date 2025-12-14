"""
答疑Agent

用生活化类比和故事化方式解释复杂概念，降低理解门槛，祛魅复杂性。
"""
import json
from typing import AsyncIterator, List, Dict, Any, Optional
from app.agents.base import BaseAgent
from app.models.domain import MentorAgentInput, ChatMessage
from app.config.settings import settings
from app.core.tool_registry import tool_registry
import structlog

logger = structlog.get_logger()


class QAAgent(BaseAgent):
    """
    答疑Agent
    
    核心使命：
    1. 用生活化类比方式回答用户问题
    2. 自动获取相关学习资料（通过工具）
    3. 降低理解门槛，祛魅复杂概念
    
    配置从环境变量加载：
    - MENTOR_PROVIDER / GENERATOR_PROVIDER: 模型提供商
    - MENTOR_MODEL / GENERATOR_MODEL: 模型名称
    """
    
    def __init__(
        self,
        agent_id: str = "qa_agent",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        # 使用MENTOR配置，如果没有则使用GENERATOR配置
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or getattr(settings, 'QA_PROVIDER', None) or settings.GENERATOR_PROVIDER,
            model_name=model_name or getattr(settings, 'QA_MODEL', None) or settings.GENERATOR_MODEL,
            base_url=base_url or getattr(settings, 'QA_BASE_URL', None) or settings.GENERATOR_BASE_URL,
            api_key=api_key or getattr(settings, 'QA_API_KEY', None) or settings.GENERATOR_API_KEY,
            temperature=0.7,  # 较高温度允许更有创意的类比
            max_tokens=2048,
        )
    
    def _get_tools(self) -> List[Dict]:
        """
        获取可用的工具定义
        
        Returns:
            工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "搜索最新的技术资料、文档和案例。当需要获取最新信息或验证某些说法时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询字符串"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大结果数量",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_concept_tutorial",
                    "description": "获取当前概念的完整教程内容。当需要参考教程来回答问题时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "roadmap_id": {
                                "type": "string",
                                "description": "路线图ID"
                            },
                            "concept_id": {
                                "type": "string",
                                "description": "概念ID"
                            }
                        },
                        "required": ["roadmap_id", "concept_id"]
                    }
                }
            }
        ]
    
    def _format_chat_history(self, history: List[ChatMessage]) -> List[Dict[str, str]]:
        """
        格式化聊天历史为LLM消息格式
        
        Args:
            history: 聊天历史
            
        Returns:
            格式化后的消息列表
        """
        messages = []
        for msg in history[-5:]:  # 只取最近5条
            role = "assistant" if msg.role == "assistant" else "user"
            messages.append({
                "role": role,
                "content": msg.content,
            })
        return messages
    
    async def execute(self, input_data: MentorAgentInput) -> Any:
        """
        执行答疑（非流式版本）
        
        收集所有流式输出并返回完整响应。
        推荐使用 execute_stream 以获得更好的用户体验。
        
        Args:
            input_data: 伴学Agent输入
            
        Returns:
            完整的响应文本
        """
        # 收集所有流式输出
        full_response = ""
        async for chunk in self.execute_stream(input_data):
            full_response += chunk
        
        return full_response
    
    async def execute_stream(
        self,
        input_data: MentorAgentInput,
    ) -> AsyncIterator[str]:
        """
        流式执行答疑
        
        Args:
            input_data: 伴学Agent输入
            
        Yields:
            流式文本片段
        """
        logger.info(
            "qa_agent_started",
            user_id=input_data.user_id,
            concept_name=input_data.concept_name,
            question_preview=input_data.user_message[:50],
        )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "qa_agent.j2",
            user_question=input_data.user_message,
            user_background=input_data.user_background or "未知",
            user_level=input_data.user_level or "beginner",
            motivation=input_data.motivation or "学习",
            concept_name=input_data.concept_name,
            concept_description=input_data.concept_description,
            tutorial_summary=input_data.tutorial_summary,
            roadmap_title=input_data.roadmap_title,
            chat_history=input_data.session_history,
        )
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        if input_data.session_history:
            messages.extend(self._format_chat_history(input_data.session_history))
        
        # 添加当前问题
        messages.append({"role": "user", "content": input_data.user_message})
        
        try:
            # 直接使用流式输出（工具调用功能暂时禁用以支持仅流式模型）
            # TODO: 未来可以在流式模式下实现工具调用
            async for chunk in self._call_llm_stream(messages):
                yield chunk
        
        except Exception as e:
            logger.error(
                "qa_agent_failed",
                error=str(e),
                user_id=input_data.user_id,
            )
            yield f"抱歉，我在处理你的问题时遇到了一些困难。请稍后再试，或者换个方式问我。\n\n错误信息: {str(e)}"
    
    async def _handle_tool_calls(
        self,
        tool_calls,
        roadmap_id: str,
        concept_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        处理工具调用
        
        Args:
            tool_calls: 工具调用列表
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            工具调用结果列表
        """
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}
            
            logger.info(
                "qa_agent_tool_call",
                tool_name=tool_name,
                args=args,
            )
            
            try:
                if tool_name == "web_search":
                    search_tool = tool_registry.get("web_search_v1")
                    if search_tool:
                        from app.models.domain import SearchQuery
                        query = SearchQuery(
                            query=args.get("query", ""),
                            max_results=args.get("max_results", 3),
                        )
                        result = await search_tool.execute(query)
                        results.append(result.model_dump())
                    else:
                        results.append({"error": "搜索工具不可用"})
                
                elif tool_name == "get_concept_tutorial":
                    tutorial_tool = tool_registry.get("get_concept_tutorial_v1")
                    if tutorial_tool:
                        from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialInput
                        query = GetConceptTutorialInput(
                            roadmap_id=args.get("roadmap_id", roadmap_id),
                            concept_id=args.get("concept_id", concept_id or ""),
                        )
                        result = await tutorial_tool.execute(query)
                        results.append(result.model_dump())
                    else:
                        results.append({"error": "教程工具不可用"})
                
                else:
                    results.append({"error": f"未知工具: {tool_name}"})
            
            except Exception as e:
                logger.error(
                    "qa_agent_tool_call_failed",
                    tool_name=tool_name,
                    error=str(e),
                )
                results.append({"error": str(e)})
        
        return results
