"""
Resource Modifier Agent（资源修改师）

负责根据用户修改要求调整现有学习资源推荐。
支持增删改资源，可选调用 Web Search 搜索新资源。
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    Resource,
    ResourceModificationInput,
    ResourceModificationOutput,
    SearchQuery,
)
from app.core.tool_registry import tool_registry
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class ResourceModifierAgent(BaseAgent):
    """
    资源修改师 Agent
    
    配置从环境变量加载：
    - RESOURCE_MODIFIER_PROVIDER: 模型提供商（默认: openai）
    - RESOURCE_MODIFIER_MODEL: 模型名称（默认: gpt-4o-mini）
    - RESOURCE_MODIFIER_BASE_URL: 自定义 API 端点（可选）
    - RESOURCE_MODIFIER_API_KEY: API 密钥（默认复用 RECOMMENDER_API_KEY）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="resource_modifier",
            model_provider=settings.RESOURCE_MODIFIER_PROVIDER,
            model_name=settings.RESOURCE_MODIFIER_MODEL,
            base_url=settings.RESOURCE_MODIFIER_BASE_URL,
            api_key=settings.get_resource_modifier_api_key,
            temperature=0.5,
            max_tokens=4096,
        )
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """获取工具定义（Web Search）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "搜索新的学习资源。当需要添加新资源或替换失效资源时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询字符串",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大结果数量，默认5",
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
        tool_calls: List[Any]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """处理工具调用"""
        tool_messages = []
        search_queries_used = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id
            
            logger.info(
                "resource_modifier_tool_call",
                tool_name=tool_name,
                tool_args=tool_args,
            )
            
            if tool_name == "web_search":
                try:
                    search_queries_used.append(tool_args["query"])
                    
                    search_tool = tool_registry.get("web_search_v1")
                    if not search_tool:
                        raise RuntimeError("Web Search Tool 未注册")
                    
                    search_query = SearchQuery(
                        query=tool_args["query"],
                        max_results=tool_args.get("max_results", 5),
                    )
                    
                    search_result = await search_tool.execute(search_query)
                    
                    formatted_results = []
                    for idx, result in enumerate(search_result.results[:5], 1):
                        formatted_results.append(
                            f"{idx}. {result['title']}\n"
                            f"   URL: {result['url']}\n"
                            f"   摘要: {result['snippet']}\n"
                        )
                    
                    result_text = "\n".join(formatted_results) if formatted_results else "未找到相关结果"
                    
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_text,
                    })
                    
                except Exception as e:
                    logger.error(
                        "resource_modifier_tool_failed",
                        tool_name=tool_name,
                        error=str(e),
                    )
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"工具调用失败: {str(e)}",
                    })
            else:
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"未知工具: {tool_name}",
                })
        
        return tool_messages, search_queries_used
    
    async def modify(
        self,
        input_data: ResourceModificationInput,
    ) -> ResourceModificationOutput:
        """
        修改资源推荐
        
        Args:
            input_data: 资源修改输入
            
        Returns:
            资源修改输出
        """
        concept = input_data.concept
        context = input_data.context
        user_preferences = input_data.user_preferences
        existing_resources = input_data.existing_resources
        modification_requirements = input_data.modification_requirements
        
        import time
        start_time = time.time()
        
        logger.info(
            "resource_modification_started",
            agent="resource_modifier",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            existing_count=len(existing_resources),
            requirements_count=len(modification_requirements),
            requirements=modification_requirements,
        )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "resource_modifier.j2",
            agent_name="Resource Modifier",
            role_description="专业的学习资源编辑师，擅长根据用户反馈调整资源推荐，替换失效链接，添加更合适的资源。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_resources=existing_resources,
            modification_requirements=modification_requirements,
        )
        
        # 构建现有资源列表
        existing_resources_text = "\n".join([
            f"- [{r.title}]({r.url}) - {r.type} - {r.description}"
            for r in existing_resources
        ])
        
        requirements_text = "\n".join([f"- {req}" for req in modification_requirements])
        
        user_message = f"""
请根据以下修改要求调整资源推荐：

**概念**: {concept.name}
**描述**: {concept.description}

**现有资源**:
{existing_resources_text}

**修改要求**:
{requirements_text}

**操作指南**:
1. 如果需要添加新资源，使用 web_search 工具搜索
2. 如果需要替换失效资源，先搜索替代资源
3. 如果需要调整资源类型分布（如更多视频），搜索对应类型资源
4. 最终输出 JSON 格式的修改后资源列表
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        tools = self._get_tools_definition()
        all_search_queries = []
        
        # 调用 LLM（支持工具调用）
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            logger.info(
                "resource_modifier_llm_call",
                agent="resource_modifier",
                concept_id=concept.concept_id,
                iteration=iteration,
                model=self.model_name,
            )
            
            llm_start = time.time()
            response = await self._call_llm(messages, tools=tools)
            llm_duration = time.time() - llm_start
            
            logger.debug(
                "resource_modifier_llm_response",
                agent="resource_modifier",
                iteration=iteration,
                llm_duration_seconds=llm_duration,
            )
            message = response.choices[0].message
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
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
                
                tool_messages, search_queries = await self._handle_tool_calls(message.tool_calls)
                messages.extend(tool_messages)
                all_search_queries.extend(search_queries)
                
                iteration += 1
                continue
            
            content = message.content
            break
        
        # 解析输出
        if not content:
            raise ValueError("LLM 未返回任何内容")
        
        result = self._parse_modification_output(
            content, 
            concept, 
            modification_requirements,
            all_search_queries,
        )
        
        total_duration = time.time() - start_time
        logger.info(
            "resource_modification_completed",
            agent="resource_modifier",
            concept_id=concept.concept_id,
            new_resources_count=len(result.resources),
            changes_count=len(result.changes_made),
            search_queries_used=result.search_queries_used,
            total_iterations=iteration,
            total_duration_seconds=total_duration,
        )
        
        return result
    
    def _parse_modification_output(
        self,
        llm_output: str,
        concept: Concept,
        requirements: List[str],
        search_queries: List[str],
    ) -> ResourceModificationOutput:
        """解析 LLM 输出"""
        try:
            # 提取 JSON
            json_content = llm_output.strip()
            
            if "```json" in json_content:
                json_start = json_content.find("```json") + 7
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            elif "```" in json_content:
                json_start = json_content.find("```") + 3
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            
            # 找到 JSON 对象
            start = json_content.find("{")
            end = json_content.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = json_content[start:end]
            
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
                        relevance_score=float(r.get("relevance_score", 0.8)),
                    )
                    resources.append(resource)
                except Exception as e:
                    logger.warning(
                        "resource_modifier_parse_resource_failed",
                        error=str(e),
                        resource_data=r,
                    )
            
            # 构建输出
            return ResourceModificationOutput(
                id=str(uuid.uuid4()),
                concept_id=concept.concept_id,
                resources=resources,
                modification_summary=data.get("modification_summary", "资源已按要求修改"),
                changes_made=data.get("changes_made", requirements),
                search_queries_used=list(set(search_queries + data.get("search_queries_used", []))),
                generated_at=datetime.now(),
            )
            
        except json.JSONDecodeError as e:
            logger.error(
                "resource_modifier_json_parse_error",
                error=str(e),
                content=llm_output[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
    
    async def execute(self, input_data: ResourceModificationInput) -> ResourceModificationOutput:
        """实现基类的抽象方法"""
        return await self.modify(input_data)

