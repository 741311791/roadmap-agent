"""
Tutorial Generator Agent（教程生成器）
"""
import json
import uuid
from datetime import datetime
from typing import AsyncIterator, List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationInput,
    TutorialGenerationOutput,
    Tutorial,
    TutorialSection,
    S3UploadRequest,
    SearchQuery,
)
from app.core.tool_registry import tool_registry
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class TutorialGeneratorAgent(BaseAgent):
    """
    教程生成器 Agent
    
    配置从环境变量加载：
    - GENERATOR_PROVIDER: 模型提供商（默认: anthropic）
    - GENERATOR_MODEL: 模型名称（默认: claude-3-5-sonnet-20241022）
    - GENERATOR_BASE_URL: 自定义 API 端点（可选）
    - GENERATOR_API_KEY: API 密钥（必需）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="tutorial_generator",
            model_provider=settings.GENERATOR_PROVIDER,
            model_name=settings.GENERATOR_MODEL,
            base_url=settings.GENERATOR_BASE_URL,
            api_key=settings.GENERATOR_API_KEY,
            temperature=0.8,
            max_tokens=16384,
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
                    "description": "执行网络搜索以获取最新的学习资源、技术文档和教程信息。当需要获取某个技术概念的最新信息、最佳实践或示例代码时，可以使用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询字符串，例如：'React Hooks 最佳实践'、'Python 异步编程教程'",
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
    
    async def _handle_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        """
        处理 LLM 返回的工具调用请求
        
        Args:
            tool_calls: 工具调用列表
            
        Returns:
            工具调用结果列表（用于传递回 LLM）
        """
        tool_messages = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id
            
            logger.info(
                "tool_call_received",
                tool_name=tool_name,
                tool_args=tool_args,
                tool_call_id=tool_call_id,
            )
            
            # 处理 web_search 工具调用
            if tool_name == "web_search":
                try:
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
                        "tool_call_success",
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
                        "tool_call_failed",
                        tool_name=tool_name,
                        error=str(e),
                    )
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"工具调用失败: {str(e)}",
                    })
            else:
                logger.warning("unknown_tool_call", tool_name=tool_name)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"未知工具: {tool_name}",
                })
        
        return tool_messages
    
    async def generate(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> TutorialGenerationOutput:
        """
        为给定的 Concept 生成详细教程
        
        Args:
            concept: 要生成教程的概念
            context: 上下文信息（前置概念、所属模块等）
            user_preferences: 用户偏好
            
        Returns:
            教程生成结果（包含 S3 URL）
        """
        # 获取语言偏好
        language_prefs = user_preferences.get_language_preferences()
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "tutorial_generator.j2",
            agent_name="Tutorial Generator",
            role_description="专业教程撰写者，为每个 Concept 生成结构化、易懂、实用的教程内容，包含理论、示例、练习。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            language_preferences=language_prefs.model_dump() if language_prefs else None,
        )
        
        # 构建用户消息
        user_message = f"""
请为以下概念生成详细的教程内容：

**概念信息**:
- 名称: {concept.name}
- 描述: {concept.description}
- 难度: {concept.difficulty}
- 预估学习时长: {concept.estimated_hours} 小时
- 前置概念: {", ".join(concept.prerequisites) if concept.prerequisites else "无"}
- 关键词: {", ".join(concept.keywords) if concept.keywords else "无"}

**上下文信息**:
- 所属阶段: {context.get("stage_name", "未知")}
- 所属模块: {context.get("module_name", "未知")}

**用户偏好**:
- 内容偏好: {", ".join(user_preferences.content_preference)}
- 当前水平: {user_preferences.current_level}
- 主要语言: {language_prefs.primary_language}

请生成一个完整、结构化的教程，包含：
1. 概述
2. 前置知识回顾（如有）
3. 核心概念讲解
4. 实践示例
5. 总结

注意：
- **教程内容必须使用主要语言（{language_prefs.primary_language}）编写**
- 教程应专注于理论讲解和实践示例，不要包含推荐学习资源（这些将由专门的资源推荐 Agent 生成）
- 不要包含练习题或实战练习（这些将由专门的测验生成 Agent 生成）

教程内容请使用 Markdown 格式，确保结构清晰、内容易懂、示例实用。

生成后，请将完整教程内容上传到 S3 存储，并返回包含 content_url 的结果。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 获取工具定义
        tools = self._get_tools_definition()
        
        # 调用 LLM（支持工具调用）
        max_iterations = 5  # 最多允许5轮工具调用
        iteration = 0
        
        while iteration < max_iterations:
            logger.info(
                "tutorial_generation_llm_call",
                concept_id=concept.concept_id,
                iteration=iteration,
            )
            
            response = await self._call_llm(messages, tools=tools)
            message = response.choices[0].message
            
            # 检查是否有工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info(
                    "tutorial_generation_tool_calls_detected",
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
                tool_messages = await self._handle_tool_calls(message.tool_calls)
                messages.extend(tool_messages)
                
                iteration += 1
                continue
            
            # 没有工具调用，获取最终内容
            content = message.content
            break
        
        if iteration >= max_iterations:
            logger.warning(
                "tutorial_generation_max_iterations_reached",
                concept_id=concept.concept_id,
            )
        
        # 解析输出
        if not content:
            raise ValueError("LLM 未返回任何内容")
        
        try:
            # 新的两段式格式：Markdown 内容 + 分隔符 + JSON 元数据
            separator = "===TUTORIAL_METADATA==="
            
            if separator in content:
                # 两段式格式
                parts = content.split(separator, 1)
                tutorial_markdown = parts[0].strip()
                json_part = parts[1].strip()
                
                # 去除可能的代码块标记
                if json_part.startswith("```json"):
                    json_part = json_part[7:]
                if json_part.startswith("```"):
                    json_part = json_part[3:]
                if json_part.endswith("```"):
                    json_part = json_part[:-3]
                json_part = json_part.strip()
                
                # 解析 JSON 元数据
                metadata = json.loads(json_part)
                
                logger.info(
                    "tutorial_generation_two_part_format_detected",
                    concept_id=concept.concept_id,
                    markdown_length=len(tutorial_markdown),
                    metadata_keys=list(metadata.keys()),
                )
            else:
                # 兼容旧格式：尝试解析 JSON（可能包含 markdown 代码块）
                logger.warning(
                    "tutorial_generation_old_format_detected",
                    concept_id=concept.concept_id,
                    message="LLM 未使用两段式格式，尝试解析旧格式 JSON",
                )
                
                json_content = content.strip()
                
                # 如果包含 ```json 代码块，提取其中的内容
                if "```json" in json_content:
                    json_start = json_content.find("```json") + 7
                    json_end = json_content.find("```", json_start)
                    if json_end > json_start:
                        json_content = json_content[json_start:json_end].strip()
                # 如果包含普通 ``` 代码块
                elif json_content.startswith("```") and "```" in json_content[3:]:
                    json_start = 3
                    json_end = json_content.find("```", json_start)
                    if json_end > json_start:
                        json_content = json_content[json_start:json_end].strip()
                
                # 解析 JSON
                metadata = json.loads(json_content)
                
                # 从 JSON 中提取教程内容
                tutorial_markdown = metadata.get("tutorial_content", "")
                if not tutorial_markdown:
                    tutorial_markdown = metadata.get("content", "")
                
                if not tutorial_markdown:
                    raise ValueError("无法从 LLM 输出中提取教���内容")
            
            # 验证必需字段
            if not tutorial_markdown:
                raise ValueError("教程内容为空")
            
            # 获取版本号（从 context 中获取，默认为 1）
            content_version = context.get("content_version", 1)
            
            # 生成教程 ID（使用 UUID 确保全局唯一）
            tutorial_id = str(uuid.uuid4())
            
            # 上传到 S3
            s3_tool = tool_registry.get("minio_storage_v1")
            if not s3_tool:
                raise RuntimeError("MinIO Storage Tool 未注册")
            
            # 构建 S3 Key（包含版本号）
            roadmap_id = context.get("roadmap_id", "unknown")
            s3_key = f"{roadmap_id}/concepts/{concept.concept_id}/v{content_version}.md"
            
            from app.models.domain import S3UploadRequest
            upload_request = S3UploadRequest(
                key=s3_key,
                content=tutorial_markdown,
                content_type="text/markdown",
            )
            
            upload_result = await s3_tool.execute(upload_request)
            
            # 构建输出（包含版本信息）
            result = TutorialGenerationOutput(
                concept_id=concept.concept_id,
                tutorial_id=tutorial_id,
                title=metadata.get("title", concept.name),
                summary=metadata.get("summary", concept.description[:500] if concept.description else ""),
                content_url=upload_result.url,
                content_status="completed",
                estimated_completion_time=metadata.get("estimated_completion_time", int(concept.estimated_hours * 60)),
                generated_at=datetime.now(),
                content_version=content_version,  # 传递版本号
            )
            
            logger.info(
                "tutorial_generation_success",
                concept_id=concept.concept_id,
                tutorial_id=tutorial_id,
                content_url=upload_result.url,
                content_version=content_version,
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error("tutorial_generation_json_parse_error", error=str(e), content=content[:500])
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("tutorial_generation_failed", concept_id=concept.concept_id, error=str(e))
            raise ValueError(f"教程生成失败: {e}")
    
    async def generate_stream(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> AsyncIterator[dict]:
        """
        流式生成单个教程
        
        Args:
            concept: 要生成教程的概念
            context: 上下文信息（前置概念、所属模块等）
            user_preferences: 用户偏好
            
        Yields:
            {"type": "tutorial_chunk", "concept_id": "...", "content": "..."}
            {"type": "tutorial_complete", "concept_id": "...", "data": {...}}
            {"type": "tutorial_error", "concept_id": "...", "error": "..."}
        """
        # 获取语言偏好
        language_prefs = user_preferences.get_language_preferences()
        
        logger.info(
            "tutorial_generation_stream_started",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            primary_language=language_prefs.primary_language,
        )
        
        try:
            # 加载 System Prompt（复用现有逻辑）
            system_prompt = self._load_system_prompt(
                "tutorial_generator.j2",
                agent_name="Tutorial Generator",
                role_description="专业教程撰写者，为每个 Concept 生成结构化、易懂、实用的教程内容，包含理论、示例、练习。",
                concept=concept,
                context=context,
                user_preferences=user_preferences,
                language_preferences=language_prefs.model_dump() if language_prefs else None,
            )
            
            # 构建用户消息（复用现有逻辑）
            user_message = f"""
请为以下概念生成详细的教程内容：

**概念信息**:
- 名称: {concept.name}
- 描述: {concept.description}
- 难度: {concept.difficulty}
- 预估学习时长: {concept.estimated_hours} 小时
- 前置概念: {", ".join(concept.prerequisites) if concept.prerequisites else "无"}
- 关键词: {", ".join(concept.keywords) if concept.keywords else "无"}

**上下文信息**:
- 所属阶段: {context.get("stage_name", "未知")}
- 所属模块: {context.get("module_name", "未知")}

**用户偏好**:
- 内容偏好: {", ".join(user_preferences.content_preference)}
- 当前水平: {user_preferences.current_level}
- 主要语言: {language_prefs.primary_language}

请生成一个完整、结构化的教程，包含：
1. 概述
2. 前置知识回顾（如有）
3. 核心概念讲解
4. 实践示例
5. 总结

注意：
- **教程内容必须使用主要语言（{language_prefs.primary_language}）编写**
- 教程应专注于理论讲解和实践示例，不要包含推荐学习资源（这些将由专门的资源推荐 Agent 生成）
- 不要包含练习题或实战练习（这些将由专门的测验生成 Agent 生成）

教程内容请使用 Markdown 格式，确保结构清晰、内容易懂、示例实用。
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            # 获取工具定义
            tools = self._get_tools_definition()
            
            # 首先进行非流式调用以处理工具调用
            # （注意：流式调用时处理工具调用比较复杂，这里采用先处理工具调用，再流式生成最终内容的策略）
            max_iterations = 5
            iteration = 0
            
            logger.info(
                "tutorial_generation_stream_tool_phase",
                concept_id=concept.concept_id,
            )
            
            # 工具调用阶段（非流式）
            while iteration < max_iterations:
                response = await self._call_llm(messages, tools=tools)
                message = response.choices[0].message
                
                # 检查是否有工具调用
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    logger.info(
                        "tutorial_generation_stream_tool_calls_detected",
                        concept_id=concept.concept_id,
                        tool_calls_count=len(message.tool_calls),
                    )
                    
                    # 推送工具调用事件
                    for tc in message.tool_calls:
                        yield {
                            "type": "tool_call",
                            "concept_id": concept.concept_id,
                            "tool_name": tc.function.name,
                            "tool_args": json.loads(tc.function.arguments),
                        }
                    
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
                    tool_messages = await self._handle_tool_calls(message.tool_calls)
                    messages.extend(tool_messages)
                    
                    # 推送工具结果事件
                    yield {
                        "type": "tool_result",
                        "concept_id": concept.concept_id,
                        "results_count": len(tool_messages),
                    }
                    
                    iteration += 1
                    continue
                
                # 没有工具调用，准备流式生成最终内容
                break
            
            # 流式生成最终内容
            logger.info(
                "tutorial_generation_stream_content_phase",
                concept_id=concept.concept_id,
                model=self.model_name,
                provider=self.model_provider,
            )
            
            full_content = ""
            async for chunk in self._call_llm_stream(messages):
                full_content += chunk
                # 推送流式片段
                yield {
                    "type": "tutorial_chunk",
                    "concept_id": concept.concept_id,
                    "content": chunk
                }
            
            logger.debug(
                "tutorial_generation_stream_response_received",
                concept_id=concept.concept_id,
                response_length=len(full_content),
            )
            
            # 解析内容并上传 S3
            try:
                # 新的两段式格式：Markdown 内容 + 分隔符 + JSON 元数据
                separator = "===TUTORIAL_METADATA==="
                
                if separator in full_content:
                    # 两段式格式
                    parts = full_content.split(separator, 1)
                    tutorial_markdown = parts[0].strip()
                    json_part = parts[1].strip()
                    
                    # 去除可能的代码块标记
                    if json_part.startswith("```json"):
                        json_part = json_part[7:]
                    if json_part.startswith("```"):
                        json_part = json_part[3:]
                    if json_part.endswith("```"):
                        json_part = json_part[:-3]
                    json_part = json_part.strip()
                    
                    # 解析 JSON 元数据
                    metadata = json.loads(json_part)
                    
                    logger.info(
                        "tutorial_generation_stream_two_part_format_detected",
                        concept_id=concept.concept_id,
                        markdown_length=len(tutorial_markdown),
                    )
                else:
                    # 兼容旧格式
                    logger.warning(
                        "tutorial_generation_stream_old_format_detected",
                        concept_id=concept.concept_id,
                    )
                    
                    json_content = full_content.strip()
                    
                    # 如果包含 ```json 代码块，提取其中的内容
                    if "```json" in json_content:
                        json_start = json_content.find("```json") + 7
                        json_end = json_content.find("```", json_start)
                        if json_end > json_start:
                            json_content = json_content[json_start:json_end].strip()
                    # 如果包含普通 ``` 代码块
                    elif json_content.startswith("```") and "```" in json_content[3:]:
                        json_start = 3
                        json_end = json_content.find("```", json_start)
                        if json_end > json_start:
                            json_content = json_content[json_start:json_end].strip()
                    
                    # 解析 JSON
                    metadata = json.loads(json_content)
                    
                    # 提取教程内容（Markdown格式）
                    tutorial_markdown = metadata.get("tutorial_content", "")
                    if not tutorial_markdown:
                        tutorial_markdown = metadata.get("content", "")
                    
                    # 如果还是没有内容，使用原始内容
                    if not tutorial_markdown:
                        tutorial_markdown = full_content
                
                # 获取版本号（从 context 中获取，默认为 1）
                content_version = context.get("content_version", 1)
                
                # 生成教程 ID（使用 UUID 确保全局唯一）
                tutorial_id = str(uuid.uuid4())
                
                # 上传到 S3
                s3_tool = tool_registry.get("minio_storage_v1")
                if not s3_tool:
                    raise RuntimeError("MinIO Storage Tool 未注册")
                
                # 构建 S3 Key（包含版本号）
                roadmap_id = context.get("roadmap_id", "unknown")
                s3_key = f"{roadmap_id}/concepts/{concept.concept_id}/v{content_version}.md"
                
                upload_request = S3UploadRequest(
                    key=s3_key,
                    content=tutorial_markdown,
                    content_type="text/markdown",
                )
                
                upload_result = await s3_tool.execute(upload_request)
                
                # 构建输出（包含版本信息）
                result = TutorialGenerationOutput(
                    concept_id=concept.concept_id,
                    tutorial_id=tutorial_id,
                    title=metadata.get("title", concept.name),
                    summary=metadata.get("summary", concept.description[:500] if concept.description else ""),
                    content_url=upload_result.url,
                    content_status="completed",
                    estimated_completion_time=metadata.get("estimated_completion_time", int(concept.estimated_hours * 60)),
                    generated_at=datetime.now(),
                    content_version=content_version,  # 传递版本号
                )
                
                logger.info(
                    "tutorial_generation_stream_success",
                    concept_id=concept.concept_id,
                    tutorial_id=tutorial_id,
                    content_url=upload_result.url,
                    content_version=content_version,
                )
                
                # 推送完成事件（包含版本信息）
                yield {
                    "type": "tutorial_complete",
                    "concept_id": concept.concept_id,
                    "data": {
                        "tutorial_id": result.tutorial_id,
                        "title": result.title,
                        "summary": result.summary,
                        "content_url": result.content_url,
                        "content_status": result.content_status,
                        "estimated_completion_time": result.estimated_completion_time,
                        "content_version": content_version,
                    }
                }
                
            except json.JSONDecodeError as e:
                logger.error(
                    "tutorial_generation_stream_json_parse_error",
                    concept_id=concept.concept_id,
                    error=str(e),
                    content=full_content[:500],
                )
                yield {
                    "type": "tutorial_error",
                    "concept_id": concept.concept_id,
                    "error": f"JSON 解析错误: {str(e)}"
                }
                
        except Exception as e:
            logger.error(
                "tutorial_generation_stream_error",
                concept_id=concept.concept_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            yield {
                "type": "tutorial_error",
                "concept_id": concept.concept_id,
                "error": str(e)
            }
    
    async def execute(self, input_data: TutorialGenerationInput) -> TutorialGenerationOutput:
        """实现基类的抽象方法"""
        return await self.generate(
            concept=input_data.concept,
            context=input_data.context,
            user_preferences=input_data.user_preferences,
        )

