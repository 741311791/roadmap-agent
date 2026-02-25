"""
Resource Recommender Agent（资源推荐师 - 已适配统一工具框架）
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    ResourceRecommendationInput,
    ResourceRecommendationOutput,
    Resource,
)
from app.tools.registry import ToolRegistry
from app.config.settings import settings
import structlog
import httpx
import asyncio

logger = structlog.get_logger()


class ResourceRecommenderAgent(BaseAgent):
    """
    资源推荐师 Agent（已适配统一工具框架）
    
    配置从环境变量加载：
    - RECOMMENDER_PROVIDER: 模型提供商（默认: openai）
    - RECOMMENDER_MODEL: 模型名称（默认: gpt-4o-mini）
    - RECOMMENDER_BASE_URL: 自定义 API 端点（可选）
    - RECOMMENDER_API_KEY: API 密钥（必需）
    - tavily_key: 预分配的 Tavily API Key（可选，用于优化性能）
    
    改进：
    - ✅ 使用统一的 ToolRegistry
    - ✅ 自动生成工具 Schema
    - ✅ 统一的工具调用接口
    """
    
    def __init__(
        self,
        agent_id: str = "resource_recommender",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        tavily_key: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
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
        
        # 预分配的 Tavily API Key
        self._tavily_key = tavily_key
        
        # 注入 ToolRegistry
        self.tool_registry = tool_registry or ToolRegistry()
        
        # 搜索查询记录（用于 execute 方法）
        self._search_queries = []
        
        if tavily_key:
            logger.debug(
                "resource_recommender_initialized_with_tavily_key",
                agent_id=agent_id,
                key_prefix=tavily_key[:10] + "...",
            )
    
    def _get_required_constraints(self) -> list[str]:
        """资源推荐器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            ConstraintNames.LANGUAGE_RESOURCE_ALLOCATION,
            ConstraintNames.CONTENT_FORMAT_PREFERENCE,
        ]
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """获取工具定义（从 ToolRegistry 自动生成）"""
        return self.tool_registry.get_all_schemas(format="openai")
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Any:
        """
        执行工具调用（使用 ToolRegistry）
        
        覆盖 base 的抽象方法，使用 ToolRegistry 执行工具
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            格式化后的工具执行结果
        """
        # 记录搜索查询
        if tool_name == "web_search" and "query" in tool_args:
            self._search_queries.append(tool_args["query"])
        
        logger.info(
            "resource_recommender_tool_call",
            tool_name=tool_name,
            arguments=tool_args,
        )
        
        # 使用 ToolRegistry 执行工具
        result = await self.tool_registry.execute_tool(
            name=tool_name,
            arguments=tool_args,
            pre_allocated_tavily_key=self._tavily_key,
        )
        
        # 格式化返回结果
        if isinstance(result, str):
            return result
        
        # 格式化搜索结果
        if tool_name == "web_search" and hasattr(result, 'results'):
            formatted_results = []
            for idx, res in enumerate(result.results[:5], 1):
                formatted_results.append(
                    f"{idx}. {res['title']}\n"
                    f"   URL: {res['url']}\n"
                    f"   摘要: {res['snippet']}\n"
                )
            return "\n".join(formatted_results) if formatted_results else "未找到相关结果"
        
        # 其他工具结果转为 JSON
        return result.model_dump() if hasattr(result, 'model_dump') else result
    
    async def _handle_tool_calls(
        self, 
        tool_calls: List[Any],
        user_preferences: LearningPreferences | None = None
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        处理 LLM 返回的工具调用请求（使用 ToolRegistry 统一执行）
        
        Args:
            tool_calls: 工具调用列表
            user_preferences: 用户偏好（可选）
            
        Returns:
            (工具调用结果列表, 使用的搜索查询列表)
        """
        tool_messages = []
        search_queries_used = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_call_id = tool_call.id
            arguments_str = tool_call.function.arguments
            
            # 验证参数
            if not arguments_str or not arguments_str.strip():
                logger.warning(
                    "resource_recommender_empty_tool_arguments",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({
                        "error": "Invalid tool call: empty arguments",
                        "tool_name": tool_name
                    }, ensure_ascii=False)
                })
                continue
            
            # 解析 JSON 参数
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError as e:
                logger.error(
                    "resource_recommender_invalid_tool_arguments",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    arguments=arguments_str[:200],
                    error=str(e)
                )
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({
                        "error": f"Invalid JSON arguments: {str(e)}",
                        "tool_name": tool_name
                    }, ensure_ascii=False)
                })
                continue
            
            # 记录搜索查询
            if tool_name == "web_search" and "query" in arguments:
                search_queries_used.append(arguments["query"])
            
            logger.info(
                "resource_recommender_tool_call",
                tool_name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )
            
            # 使用 ToolRegistry 统一执行工具
            result = await self.tool_registry.execute_tool(
                name=tool_name,
                arguments=arguments,
                pre_allocated_tavily_key=self._tavily_key,
            )
            
            # 格式化返回结果
            if isinstance(result, str):
                content = result
            else:
                if tool_name == "web_search" and hasattr(result, 'results'):
                    # 格式化搜索结果
                    formatted_results = []
                    for idx, res in enumerate(result.results[:5], 1):
                        formatted_results.append(
                            f"{idx}. {res['title']}\n"
                            f"   URL: {res['url']}\n"
                            f"   摘要: {res['snippet']}\n"
                        )
                    content = "\n".join(formatted_results) if formatted_results else "未找到相关结果"
                else:
                    content = json.dumps(
                        result.model_dump() if hasattr(result, 'model_dump') else result,
                        ensure_ascii=False
                    )
            
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content
            })
        
        return tool_messages, search_queries_used
    
    # 软 404 特征：最终重定向 URL 路径中包含这些关键词则认为是无效页面
    _SOFT_404_URL_PATTERNS = (
        "/404", "/not-found", "/notfound", "/error", "/page-not-found",
        "404.html", "not_found", "missing",
    )
    
    # 软 404 特征：HTML 内容中 <title> 包含这些关键词则认为是无效页面
    _SOFT_404_TITLE_PATTERNS = (
        "404", "not found", "page not found", "找不到", "页面不存在",
        "没有找到", "该页面", "访问出错", "错误",
    )

    async def _verify_urls(
        self, 
        resources: List[Resource]
    ) -> List[Resource]:
        """
        批量验证资源 URL 有效性（并发）
        
        采用两阶段验证策略：
        1. HEAD 请求快速检查 HTTP 状态码
        2. 对 HEAD 返回 200 的 URL，发 GET 请求读取少量 HTML 内容，
           检测「软 404」——即 HTTP 200 但页面实际是 404 错误页的情况
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        def _is_soft_404(final_url: str, html_snippet: str) -> bool:
            """
            判断是否为软 404
            
            Args:
                final_url: 跟随重定向后的最终 URL
                html_snippet: 响应体的前 4KB 内容
                
            Returns:
                True 表示检测到软 404，应过滤掉
            """
            # 检查最终 URL 路径是否含 404 特征
            url_lower = final_url.lower()
            if any(pattern in url_lower for pattern in self._SOFT_404_URL_PATTERNS):
                return True
            
            # 提取 <title> 标签内容
            import re
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>",
                html_snippet,
                re.IGNORECASE | re.DOTALL,
            )
            if title_match:
                title = title_match.group(1).strip().lower()
                if any(pattern in title for pattern in self._SOFT_404_TITLE_PATTERNS):
                    return True
            
            return False
        
        async def verify_single(resource: Resource) -> Optional[Resource]:
            """
            验证单个 URL
            
            先 HEAD 快速判断，再对 200 响应做 GET 软 404 检测
            """
            try:
                async with httpx.AsyncClient(
                    timeout=15.0,
                    follow_redirects=True,
                ) as client:
                    # 第一阶段：HEAD 请求
                    head_response = await client.head(resource.url, headers=headers)
                    
                    if head_response.status_code in [403, 412]:
                        # 服务器拒绝 HEAD 但不代表页面不存在，保守保留
                        return resource
                    elif head_response.status_code == 404:
                        logger.debug("url_hard_404", url=resource.url)
                        return None
                    elif head_response.status_code >= 500:
                        logger.debug("url_server_error", url=resource.url, status=head_response.status_code)
                        return None
                    elif head_response.status_code != 200:
                        # 其他非 200 状态码保守保留（如 301 未跟随等边缘情况）
                        return resource
                    
                    # 第二阶段：HEAD 返回 200，发 GET 请求检测软 404
                    # 只读取前 4KB，足够获取 <title> 和重定向目标 URL
                    get_response = await client.get(
                        resource.url,
                        headers=headers,
                        # 通过 stream 只读取少量内容，减少带宽消耗
                    )
                    
                    # 更新为最终 URL（跟随重定向后）
                    final_url = str(get_response.url)
                    
                    # GET 请求返回明确的 404
                    if get_response.status_code == 404:
                        logger.debug("url_get_404", url=resource.url, final_url=final_url)
                        return None
                    
                    if get_response.status_code >= 500:
                        logger.debug("url_get_server_error", url=resource.url, status=get_response.status_code)
                        return None
                    
                    # 读取前 4KB 内容检测软 404
                    html_snippet = get_response.text[:4096]
                    
                    if _is_soft_404(final_url, html_snippet):
                        logger.debug(
                            "url_soft_404_detected",
                            url=resource.url,
                            final_url=final_url,
                        )
                        return None
                    
                    # 验证通过，更新为最终重定向 URL
                    resource.url = final_url
                    return resource
                        
            except httpx.TimeoutException:
                # 超时保守保留，避免因网络波动误删有效资源
                return resource
            except Exception as e:
                logger.debug("url_verify_exception", url=resource.url, error=str(e))
                return resource
        
        tasks = [verify_single(r) for r in resources]
        results = await asyncio.gather(*tasks)
        
        verified_resources = [r for r in results if r is not None]
        
        logger.info(
            "url_verification_complete",
            total=len(resources),
            verified=len(verified_resources),
            filtered=len(resources) - len(verified_resources),
        )
        
        return verified_resources
    
    async def execute(self, input_data: ResourceRecommendationInput) -> ResourceRecommendationOutput:
        """
        为给定的 Concept 推荐学习资源（支持工具调用）
        
        Args:
            input_data: 包含概念、上下文和用户偏好
            
        Returns:
            资源推荐结果
        """
        concept = input_data.concept
        context = input_data.context
        user_preferences = input_data.user_preferences
        
        # 保存用户偏好
        self._current_user_preferences = user_preferences
        
        # 获取语言偏好
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
        
        # 加载 System Prompt
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
        
        # 构建语言分配指令
        if has_bilingual:
            primary_count = int(10 * resource_ratio["primary"])
            secondary_count = 10 - primary_count
            language_instruction = f"""
**语言分配要求**（重要）:
- 主要语言（{language_prefs.primary_language}）资源: 约 {int(resource_ratio['primary'] * 100)}%（约 {primary_count} 个）
- 次要语言（{language_prefs.secondary_language}）资源: 约 {int(resource_ratio['secondary'] * 100)}%（约 {secondary_count} 个）
- 每个资源需要标注语言（language 字段）
- 搜索时分别使用主语言和次语言的搜索查询
"""
        else:
            language_instruction = f"""
**语言要求**:
- 主要使用 {language_prefs.primary_language} 语言的资源
- 每个资源需要标注语言（language 字段）
"""
        
        # 构建用户消息
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
1. 使用 web_search 工具搜索与概念相关的资源（按语言分配比例分别搜索）
2. 基于搜索结果，筛选 8-10 个高质量资源
3. 按相关性评分排序，输出 JSON 格式
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 获取工具定义
        tools = self._get_tools_definition()
        
        # 初始化搜索查询记录（用于工具执行）
        self._search_queries = []
        
        # 使用 base 的 ReAct 循环
        logger.info(
            "resource_recommender_using_react",
            concept_id=concept.concept_id,
        )
        
        response = await self._call_llm(
            messages=messages,
            tools=tools,
            use_react=True,
            max_iterations=5,
        )
        
        final_response = response.choices[0].message.content
        
        if not final_response:
            raise ValueError("LLM 未返回任何内容")
        
        # 获取收集到的搜索查询
        all_search_queries = self._search_queries
        
        # 使用 instructor 解析最终响应（添加一次性的 structured output 调用）
        # 由于已经完成工具调用循环，这里只需要解析最终的 JSON 输出
        try:
            # 简单的 JSON 提取
            json_content = final_response.strip()
            if "```json" in json_content:
                json_start = json_content.find("```json") + 7
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            
            data = json.loads(json_content)
            
            # 构建 Resource 列表
            resources = []
            for r in data.get("resources", []):
                try:
                    # 规范化 type 字段
                    raw_type = r.get("type", "article")
                    type_mapping = {
                        "tutorial": "hands_on",
                        "guide": "article",
                        "reference": "documentation",
                        "practice": "hands_on",
                    }
                    normalized_type = type_mapping.get(raw_type, raw_type)
                    
                    resource = Resource(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        type=normalized_type,
                        description=r.get("description", ""),
                        relevance_score=float(r.get("relevance_score", 0.5)),
                        confidence_score=float(r.get("confidence_score")) if r.get("confidence_score") is not None else None,
                        published_date=r.get("published_date"),
                        language=r.get("language"),
                    )
                    resources.append(resource)
                except Exception as e:
                    logger.warning(
                        "resource_recommender_parse_resource_failed",
                        error=str(e),
                        resource_data=r,
                    )
            
            # 验证URL有效性
            if resources:
                resources = await self._verify_urls(resources)
            
            # 合并搜索查询
            json_queries = data.get("search_queries_used", [])
            combined_queries = list(set(all_search_queries + json_queries))
            
            # 生成唯一 ID
            resource_id = str(uuid.uuid4())
            
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
                content=final_response[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error(
                "resource_recommender_failed",
                concept_id=concept.concept_id,
                error=str(e),
            )
            raise ValueError(f"资源推荐失败: {e}")
