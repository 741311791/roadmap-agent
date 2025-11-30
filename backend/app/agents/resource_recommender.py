"""
Resource Recommender Agent（资源推荐师）
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    ResourceRecommendationInput,
    ResourceRecommendationOutput,
    Resource,
    SearchQuery,
)
from app.core.tool_registry import tool_registry
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class ResourceRecommenderAgent(BaseAgent):
    """
    资源推荐师 Agent
    
    配置从环境变量加载：
    - RECOMMENDER_PROVIDER: 模型提供商（默认: openai）
    - RECOMMENDER_MODEL: 模型名称（默认: gpt-4o-mini）
    - RECOMMENDER_BASE_URL: 自定义 API 端点（可选）
    - RECOMMENDER_API_KEY: API 密钥（必需）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="resource_recommender",
            model_provider=settings.RECOMMENDER_PROVIDER,
            model_name=settings.RECOMMENDER_MODEL,
            base_url=settings.RECOMMENDER_BASE_URL,
            api_key=settings.RECOMMENDER_API_KEY,
            temperature=0.5,
            max_tokens=4096,
        )
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        获取工具定义（符合 OpenAI Function Calling 格式）
        
        Returns:
            工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "执行网络搜索以获取学习资源、官方文档、教程和课程。使用此工具搜索与概念相关的高质量学习资源。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询字符串，例如：'React Hooks 官方文档'、'Python 机器学习教程'",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大结果数量，默认5，范围1-20",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        ]
    
    async def _handle_tool_calls(self, tool_calls: List[Any]) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        处理 LLM 返回的工具调用请求
        
        Args:
            tool_calls: 工具调用列表
            
        Returns:
            (工具调用结果列表, 使用的搜索查询列表)
        """
        tool_messages = []
        search_queries_used = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id
            
            logger.info(
                "resource_recommender_tool_call",
                tool_name=tool_name,
                tool_args=tool_args,
                tool_call_id=tool_call_id,
            )
            
            # 处理 web_search 工具调用
            if tool_name == "web_search":
                try:
                    # 记录搜索查询
                    search_queries_used.append(tool_args["query"])
                    
                    # 获取搜索工具
                    search_tool = tool_registry.get("web_search_v1")
                    if not search_tool:
                        raise RuntimeError("Web Search Tool 未注册")
                    
                    # 构建搜索查询
                    search_query = SearchQuery(
                        query=tool_args["query"],
                        max_results=tool_args.get("max_results", 5),
                    )
                    
                    # 执行搜索
                    search_result = await search_tool.execute(search_query)
                    
                    # 格式化搜索结果
                    formatted_results = []
                    for idx, result in enumerate(search_result.results[:5], 1):
                        formatted_results.append(
                            f"{idx}. {result['title']}\n"
                            f"   URL: {result['url']}\n"
                            f"   摘要: {result['snippet']}\n"
                        )
                    
                    result_text = "\n".join(formatted_results) if formatted_results else "未找到相关结果"
                    
                    logger.info(
                        "resource_recommender_tool_success",
                        tool_name=tool_name,
                        results_count=len(search_result.results),
                    )
                    
                    # 构建工具响应消息
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_text,
                    })
                    
                except Exception as e:
                    logger.error(
                        "resource_recommender_tool_failed",
                        tool_name=tool_name,
                        error=str(e),
                    )
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"工具调用失败: {str(e)}",
                    })
            else:
                logger.warning("resource_recommender_unknown_tool", tool_name=tool_name)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"未知工具: {tool_name}",
                })
        
        return tool_messages, search_queries_used
    
    async def recommend(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> ResourceRecommendationOutput:
        """
        为给定的 Concept 推荐学习资源
        
        Args:
            concept: 要推荐资源的概念
            context: 上下文信息（所属阶段、模块等）
            user_preferences: 用户偏好
            
        Returns:
            资源推荐结果
        """
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "resource_recommender.j2",
            agent_name="Resource Recommender",
            role_description="资深学习资源专家，擅长为学习者搜索并推荐高质量的学习资源，包括官方文档、教程、视频课程、书籍和工具。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        # 构建用户消息
        user_message = f"""
请为以下概念推荐高质量的学习资源：

**概念信息**:
- 名称: {concept.name}
- 描述: {concept.description}
- 难度: {concept.difficulty}
- 关键词: {", ".join(concept.keywords) if concept.keywords else "无"}

**上下文信息**:
- 所属阶段: {context.get("stage_name", "未知")}
- 所属模块: {context.get("module_name", "未知")}

**用户偏好**:
- 内容偏好: {", ".join(user_preferences.content_preference)}
- 当前水平: {user_preferences.current_level}

请执行以下步骤：
1. 使用 web_search 工具搜索与概念相关的官方文档、教程、课程等资源
2. 基于搜索结果和你的知识，筛选 5-10 个高质量资源
3. 按相关性评分排序，输出 JSON 格式的推荐结果
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 获取工具定义
        tools = self._get_tools_definition()
        
        # 收集所有使用的搜索查询
        all_search_queries = []
        
        # 调用 LLM（支持工具调用）
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            logger.info(
                "resource_recommender_llm_call",
                concept_id=concept.concept_id,
                iteration=iteration,
            )
            
            response = await self._call_llm(messages, tools=tools)
            message = response.choices[0].message
            
            # 检查是否有工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info(
                    "resource_recommender_tool_calls_detected",
                    concept_id=concept.concept_id,
                    tool_calls_count=len(message.tool_calls),
                )
                
                # 将 assistant 的消息添加到对话历史
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # 处理工具调用
                tool_messages, search_queries = await self._handle_tool_calls(message.tool_calls)
                messages.extend(tool_messages)
                all_search_queries.extend(search_queries)
                
                iteration += 1
                continue
            
            # 没有工具调用，获取最终内容
            content = message.content
            break
        
        if iteration >= max_iterations:
            logger.warning(
                "resource_recommender_max_iterations_reached",
                concept_id=concept.concept_id,
            )
        
        # 解析输出
        if not content:
            raise ValueError("LLM 未返回任何内容")
        
        try:
            # 提取 JSON 内容
            json_content = content.strip()
            
            # 如果包含 ```json 代码块，提取其中的内容
            if "```json" in json_content:
                json_start = json_content.find("```json") + 7
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            elif json_content.startswith("```") and "```" in json_content[3:]:
                json_start = 3
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            
            # 解析 JSON
            data = json.loads(json_content)
            
            # 构建 Resource 列表
            resources = []
            for r in data.get("resources", []):
                try:
                    resource = Resource(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        type=r.get("type", "article"),
                        description=r.get("description", ""),
                        relevance_score=float(r.get("relevance_score", 0.5)),
                    )
                    resources.append(resource)
                except Exception as e:
                    logger.warning(
                        "resource_recommender_parse_resource_failed",
                        error=str(e),
                        resource_data=r,
                    )
            
            # 合并搜索查询（从 JSON 和实际调用中）
            json_queries = data.get("search_queries_used", [])
            combined_queries = list(set(all_search_queries + json_queries))
            
            # 生成唯一 ID（用于关联 resource_recommendation_metadata 表）
            resource_id = str(uuid.uuid4())
            
            # 构建输出
            result = ResourceRecommendationOutput(
                id=resource_id,
                concept_id=concept.concept_id,
                resources=resources,
                search_queries_used=combined_queries,
                generated_at=datetime.now(),
            )
            
            logger.info(
                "resource_recommender_success",
                concept_id=concept.concept_id,
                resources_count=len(resources),
                search_queries_count=len(combined_queries),
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "resource_recommender_json_parse_error",
                error=str(e),
                content=content[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error(
                "resource_recommender_failed",
                concept_id=concept.concept_id,
                error=str(e),
            )
            raise ValueError(f"资源推荐失败: {e}")
    
    async def execute(self, input_data: ResourceRecommendationInput) -> ResourceRecommendationOutput:
        """实现基类的抽象方法"""
        return await self.recommend(
            concept=input_data.concept,
            context=input_data.context,
            user_preferences=input_data.user_preferences,
        )

