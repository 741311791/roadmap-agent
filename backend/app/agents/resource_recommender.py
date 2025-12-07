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
    
    def __init__(
        self,
        agent_id: str = "resource_recommender",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.RECOMMENDER_PROVIDER,
            model_name=model_name or settings.RECOMMENDER_MODEL,
            base_url=base_url or settings.RECOMMENDER_BASE_URL,
            api_key=api_key or settings.RECOMMENDER_API_KEY,
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
    
    async def _handle_tool_calls(
        self, 
        tool_calls: List[Any],
        user_preferences: LearningPreferences | None = None
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        处理 LLM 返回的工具调用请求
        
        Args:
            tool_calls: 工具调用列表
            user_preferences: 用户偏好（可选，如果未提供则从实例变量获取）
            
        Returns:
            (工具调用结果列表, 使用的搜索查询列表)
        """
        tool_messages = []
        search_queries_used = []
        
        # 获取用户偏好（优先使用参数，否则使用实例变量）
        prefs = user_preferences or getattr(self, '_current_user_preferences', None)
        
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
                    
                    # 构建搜索查询（包含语言和内容类型信息）
                    # 从 user_preferences 提取语言信息（如果可用）
                    language = None
                    if prefs and prefs.preferred_language:
                        language = prefs.preferred_language
                    
                    # 从查询中推断内容类型（如果可能）
                    content_type = None
                    query_lower = tool_args["query"].lower()
                    if any(keyword in query_lower for keyword in ["video", "tutorial", "course", "youtube", "bilibili"]):
                        content_type = "video"
                    elif any(keyword in query_lower for keyword in ["documentation", "docs", "api"]):
                        content_type = "documentation"
                    elif any(keyword in query_lower for keyword in ["article", "blog", "post"]):
                        content_type = "article"
                    
                    search_query = SearchQuery(
                        query=tool_args["query"],
                        max_results=tool_args.get("max_results", 5),
                        language=language,
                        content_type=content_type,
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
        
        支持双语资源推荐：
        - 如果用户设置了不同的主语言和次语言，按 60%/40% 比例分配资源
        - 如果只有主语言，则 100% 使用主语言资源
        
        Args:
            concept: 要推荐资源的概念
            context: 上下文信息（所属阶段、模块等）
            user_preferences: 用户偏好
            
        Returns:
            资源推荐结果
        """
        # 保存用户偏好到实例变量，供工具调用时使用
        self._current_user_preferences = user_preferences
        
        # 获取语言偏好和资源分配比例
        language_prefs = user_preferences.get_language_preferences()
        resource_ratio = language_prefs.get_effective_ratio()
        
        # 判断是否需要双语搜索
        has_bilingual = (
            language_prefs.secondary_language and 
            language_prefs.secondary_language != language_prefs.primary_language and
            resource_ratio["secondary"] > 0
        )
        
        logger.info(
            "resource_recommender_language_config",
            concept_id=concept.concept_id,
            primary_language=language_prefs.primary_language,
            secondary_language=language_prefs.secondary_language,
            resource_ratio=resource_ratio,
            has_bilingual=has_bilingual,
        )
        
        # 加载 System Prompt（包含语言偏好信息）
        system_prompt = self._load_system_prompt(
            "resource_recommender.j2",
            agent_name="Resource Recommender",
            role_description="资深学习资源专家，擅长为学习者搜索并推荐高质量的学习资源，包括官方文档、教程、视频课程、书籍和工具。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            language_preferences=language_prefs.model_dump(),
            resource_ratio=resource_ratio,
        )
        
        # 根据内容偏好构建搜索建议
        content_pref_map = {
            "visual": "视频教程、图解、演示",
            "text": "文档、文章、书籍",
            "audio": "播客、有声内容",
            "hands_on": "互动练习、项目实战",
        }
        content_pref_desc = ", ".join([
            content_pref_map.get(pref, pref) 
            for pref in user_preferences.content_preference
        ])
        
        # 构建语言分配指令
        if has_bilingual:
            primary_count = int(10 * resource_ratio["primary"])  # 假设推荐10个资源
            secondary_count = 10 - primary_count
            language_instruction = f"""
**语言分配要求**（重要）:
- 主要语言（{language_prefs.primary_language}）资源: 约 {int(resource_ratio['primary'] * 100)}%（约 {primary_count} 个）
- 次要语言（{language_prefs.secondary_language}）资源: 约 {int(resource_ratio['secondary'] * 100)}%（约 {secondary_count} 个）
- 每个资源需要在 JSON 输出中标注其语言（language 字段）
- 搜索时需要分别使用主语言和次语言的搜索查询
"""
        else:
            language_instruction = f"""
**语言要求**:
- 主要使用 {language_prefs.primary_language} 语言的资源
- 每个资源需要在 JSON 输出中标注其语言（language 字段）
"""
        
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
- 内容偏好: {content_pref_desc}
- 当前水平: {user_preferences.current_level}
{language_instruction}
请执行以下步骤：
1. 根据用户的内容偏好（{", ".join(user_preferences.content_preference)}）和语言分配要求，构建针对性的搜索查询
2. 使用 web_search 工具搜索与概念相关的官方文档、教程、课程等资源
   - 优先搜索用户偏好的内容类型（如偏好 visual，优先搜索视频教程）
   - **按语言分配比例分别搜索不同语言的资源**
3. 基于搜索结果和你的知识，筛选 8-10 个高质量资源（按语言比例分配）
4. 按相关性评分排序，输出 JSON 格式的推荐结果（每个资源包含 language 字段）
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
                
                # 处理工具调用（传递用户偏好）
                tool_messages, search_queries = await self._handle_tool_calls(
                    message.tool_calls,
                    user_preferences=user_preferences
                )
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

