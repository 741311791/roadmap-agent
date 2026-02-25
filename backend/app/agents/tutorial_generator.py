"""
Tutorial Generator Agent（基于 BaseAgent ReAct 模式）
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationInput,
    TutorialGenerationOutput,
    S3UploadRequest,
)
from app.tools.mcp_loader import load_context7_tools
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class TutorialGeneratorAgent(BaseAgent):
    """
    教程生成器 Agent（基于 BaseAgent ReAct 模式）
    
    特性：
    - 使用 BaseAgent._call_llm_with_tools_react（自动管理 ReAct 循环）
    - 集成 Context7 MCP 工具（通过 langchain-mcp-adapters）
    - 区分开发场景和非开发场景
    - 无需额外的 LangChain Agent 依赖
    
    工具列表：
    - resolve-library-id: 解析库的 Context7 ID（MCP，仅开发场景）
    - query-docs: 查询官方文档（MCP，仅开发场景）
    
    场景分类：
    - 开发场景：需要查询特定版本的技术文档（如React、Python、FastAPI）
    - 非开发场景：使用LLM自有知识库（如烹饪、健身、语言学习）
    """
    
    def __init__(
        self,
        agent_id: str = "tutorial_generator",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.GENERATOR_PROVIDER,
            model_name=model_name or settings.GENERATOR_MODEL,
            base_url=base_url or settings.GENERATOR_BASE_URL,
            api_key=api_key or settings.GENERATOR_API_KEY,
            temperature=0.8,
            max_tokens=32768,
        )
        
        # 存储 LangChain 工具实例（用于执行）
        self._langchain_tools = {}
    
    def _get_required_constraints(self) -> list[str]:
        """教程生成器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.DIFFICULTY,
            ConstraintNames.CONTENT_FORMAT_PREFERENCE,
            ConstraintNames.KEY_TECHNOLOGIES,
        ]
    
    async def _get_tools(self, is_dev_scenario: bool = True) -> list[Dict]:
        """
        获取可用工具（OpenAI function calling 格式）
        
        Args:
            is_dev_scenario: 是否为开发场景
                - True: 加载Context7工具（查询官方文档）
                - False: 不加载任何工具（使用LLM自有知识）
        
        Returns:
            OpenAI function calling 格式的工具列表
        """
        tools = []
        
        # 仅在开发场景下加载Context7工具
        if is_dev_scenario:
            try:
                # 加载LangChain工具
                context7_tools = await load_context7_tools()
                
                # 转换为OpenAI function calling格式
                for tool in context7_tools:
                    # 保存工具实例以供后续执行
                    self._langchain_tools[tool.name] = tool
                    
                    # 获取参数schema（兼容多种格式）
                    if hasattr(tool, 'args_schema') and tool.args_schema:
                        # 如果是Pydantic模型，调用schema()
                        if hasattr(tool.args_schema, 'schema'):
                            parameters = tool.args_schema.schema()
                        # 如果已经是字典，直接使用
                        elif isinstance(tool.args_schema, dict):
                            parameters = tool.args_schema
                        else:
                            parameters = {"type": "object", "properties": {}}
                    else:
                        parameters = {"type": "object", "properties": {}}
                    
                    # 转换为OpenAI格式
                    tool_def = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": parameters
                        }
                    }
                    tools.append(tool_def)
                
                logger.info(
                    "tutorial_generator_tools_loaded",
                    scenario="development",
                    tools_count=len(tools),
                    tools=[t["function"]["name"] for t in tools]
                )
            except Exception as e:
                logger.warning(
                    "context7_tools_loading_failed",
                    error=str(e),
                    message="Continue without tools (LLM knowledge only)"
                )
        else:
            logger.info(
                "tutorial_generator_no_tools_needed",
                scenario="non_development",
                message="Using LLM knowledge base only"
            )
        
        return tools
    
    def _get_system_prompt(
        self, 
        concept: Concept, 
        context: dict, 
        user_preferences: LearningPreferences,
        is_dev_scenario: bool = True
    ) -> str:
        """
        加载 ReAct 风格的 System Prompt
        
        使用新模板：tutorial_generator_react.j2
        
        Args:
            concept: 概念信息
            context: 上下文
            user_preferences: 用户偏好
            is_dev_scenario: 是否为开发场景
        """
        language_prefs = user_preferences.get_language_preferences()
        
        return self._load_system_prompt(
            "tutorial_generator_react.j2",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            language_preferences=language_prefs.model_dump() if language_prefs else None,
            is_dev_scenario=is_dev_scenario,
        )
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Any:
        """
        执行工具调用（调用LangChain工具）
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
        
        Returns:
            工具执行结果
        
        Raises:
            ValueError: 工具不存在
        """
        if tool_name not in self._langchain_tools:
            raise ValueError(f"Tool '{tool_name}' not found in registered tools")
        
        tool = self._langchain_tools[tool_name]
        
        try:
            # 调用LangChain工具
            result = await tool.ainvoke(tool_args)
            
            logger.debug(
                "tool_executed",
                tool_name=tool_name,
                args=tool_args,
                result_preview=str(result)[:200]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "tool_execution_failed",
                tool_name=tool_name,
                args=tool_args,
                error=str(e)
            )
            raise
    
    async def _is_development_scenario(self, concept: Concept) -> bool:
        """
        判断是否为开发场景（使用LLM智能判断）
        
        开发场景的特征：
        - 涉及编程语言、框架、库等技术栈
        - 需要查询特定版本的官方文档
        - 对依赖版本敏感
        
        非开发场景的特征：
        - 烹饪、健身、语言学习等生活技能
        - 不涉及技术文档和代码
        
        Args:
            concept: 概念信息
            
        Returns:
            是否为开发场景
        """
        # 构建判断Prompt
        prompt = f"""请判断以下学习概念是否为"开发场景"。

概念名称：{concept.name}
概念描述：{concept.description or "无"}

定义：
- **开发场景**：涉及编程语言、框架、库、API、工具等技术栈，需要查询官方文档和代码示例。例如：学习React、Python、FastAPI、LangGraph、Docker等。
- **非开发场景**：生活技能、兴趣爱好、语言学习等，不涉及编程和技术文档。例如：烹饪、健身、英语口语、绘画、音乐等。

请仅回答 "YES" 或 "NO"（不要有任何其他内容）：
- YES：这是开发场景
- NO：这不是开发场景"""

        try:
            # 调用LLM判断
            messages = [{"role": "user", "content": prompt}]
            response = await self._call_llm(messages)
            
            # 提取响应内容
            content = response.choices[0].message.content.strip().upper()
            is_dev = content == "YES"
            
            logger.info(
                "scenario_detection_completed",
                concept_id=concept.concept_id,
                concept_name=concept.name,
                scenario="development" if is_dev else "non_development",
                llm_response=content
            )
            
            return is_dev
            
        except Exception as e:
            # 如果LLM调用失败，默认为开发场景（保守策略）
            logger.warning(
                "scenario_detection_failed",
                concept_id=concept.concept_id,
                concept_name=concept.name,
                error=str(e),
                fallback="development"
            )
            return True
    
    async def generate(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> TutorialGenerationOutput:
        """
        生成教程（使用 BaseAgent ReAct 模式）
        
        流程：
        1. 判断开发场景 vs 非开发场景
        2. 加载工具（开发场景加载Context7，非开发场景无工具）
        3. 使用 BaseAgent._call_llm_with_tools_react 调用LLM
        4. 解析输出并上传 S3
        
        Args:
            concept: 要生成教程的概念
            context: 上下文信息
            user_preferences: 用户偏好
            
        Returns:
            教程生成结果
        """
        # 1. 判断场景类型（使用LLM智能判断）
        is_dev_scenario = await self._is_development_scenario(concept)
        
        # 2. 加载工具（OpenAI function calling格式）
        tools = await self._get_tools(is_dev_scenario=is_dev_scenario)
        
        # 3. 构建System Prompt
        system_prompt = self._get_system_prompt(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            is_dev_scenario=is_dev_scenario,
        )
        
        # 4. 构建用户消息
        language_prefs = user_preferences.get_language_preferences()
        
        if is_dev_scenario:
            scenario_reminder = """
**场景说明**：
这是开发场景（涉及技术栈），你可以选择性使用工具查询官方文档。

**决策建议**：
1. **优先使用你的知识库**：如果你对这个概念有充分且准确的了解，直接生成教程
2. **按需使用工具**：只在以下情况调用工具：
   - 知识点非常新（可能超出你的训练数据）
   - 需要特定版本的API说明
   - 你的知识库不确定或有限
   - 需要官方权威的最佳实践

**工具使用**（如果需要）：
- Step 1: 调用 `resolve-library-id` 获取库ID
- Step 2: 调用 `query-docs` 查询官方文档
- Step 3: 基于查询结果生成教程

**最终输出**：
- 格式：纯JSON对象（以`{`开始）
- 内容：完整的教程（markdown_content + metadata）
"""
        else:
            scenario_reminder = """
**重要提醒**：
1. 这是非开发场景，直接使用你的知识库生成教程
2. 确保内容准确、实用、易懂
3. **最终输出格式**：纯 JSON 对象，包含 markdown_content 和 metadata 字段
"""
        
        user_message = f"""
请为以下概念生成详细的教程内容：

**概念信息**:
- 名称: {concept.name}
- 描述: {concept.description}
- 难度: {concept.difficulty}
- 预估学习时长: {concept.estimated_hours} 小时
- 前置概念: {", ".join(concept.prerequisites) if concept.prerequisites else "无"}

**用户偏好**:
- 内容偏好: {", ".join(user_preferences.content_preference)}
- 当前水平: {user_preferences.current_level}
- 主要语言: {language_prefs.primary_language}

{scenario_reminder}

**最终输出要求**：

当你完成信息收集后，输出JSON格式的教程内容。

✅ **正确格式**（直接复制这个结构）：
{{
  "markdown_content": "# 教程标题\n\n## 概述\n内容...\n\n## 核心概念\n内容...\n\n## 实践示例\n代码...\n\n## 总结\n总结...",
  "metadata": {{
    "title": "教程标题",
    "summary": "简短摘要（不超过100字）",
    "estimated_completion_time": 90
  }}
}}

**输出检查**：
- 第一个字符是`{{`吗？
- 包含`markdown_content`和`metadata`字段吗？
- JSON格式有效吗（双引号、正确转义）？

现在开始执行！
"""
        
        # 5. 调用 BaseAgent ReAct 方法（自动管理工具调用循环）
        logger.info(
            "tutorial_generation_start",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            scenario="development" if is_dev_scenario else "non_development",
            tools_count=len(tools),
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 根据概念复杂度动态设置最大迭代次数
        max_iter = 7  # 基础值
        if concept.difficulty in ["advanced", "expert"]:
            max_iter = 10  # 复杂概念允许更多迭代
        if concept.prerequisites and len(concept.prerequisites) > 3:
            max_iter = min(max_iter + 2, 12)  # 前置概念多的允许更多，但不超过12
        
        logger.info(
            "tutorial_generation_max_iterations_set",
            concept_id=concept.concept_id,
            max_iterations=max_iter,
            difficulty=concept.difficulty,
            prerequisites_count=len(concept.prerequisites) if concept.prerequisites else 0,
        )
        
        # 使用BaseAgent的ReAct方法
        response = await self._call_llm(
            messages=messages,
            tools=tools if tools else None,
            use_react=True if tools else False,
            max_iterations=max_iter,
        )
        
        # 6. 提取最终输出
        content = response.choices[0].message.content
        
        # 验证内容是字符串
        if not isinstance(content, str):
            logger.error(
                "tutorial_generation_invalid_content_type",
                concept_id=concept.concept_id,
                content_type=type(content).__name__,
            )
            raise TypeError(
                f"Final message content is not a string, got {type(content).__name__}. "
                "The Agent may not have produced a final text response."
            )
        
        if not content.strip():
            logger.error(
                "tutorial_generation_empty_content",
                concept_id=concept.concept_id,
            )
            raise ValueError("Final message content is empty")
        
        logger.info(
            "tutorial_generation_llm_completed",
            concept_id=concept.concept_id,
            content_length=len(content),
            content_preview=content[:500] if len(content) > 500 else content,
        )
        
        # 7. 解析两段式输出
        tutorial_markdown, metadata = await self._parse_output(content, concept)
        
        # 8. 上传到 S3
        s3_key = await self._upload_to_s3(
            tutorial_markdown,
            concept.concept_id,
            context
        )
        
        # 9. 返回结果
        return TutorialGenerationOutput(
            concept_id=concept.concept_id,
            tutorial_id=str(uuid.uuid4()),
            title=metadata.get("title", concept.name),
            summary=metadata.get("summary", concept.description[:100] if concept.description else ""),
            content_url=s3_key,
            content_status="completed",
            estimated_completion_time=metadata.get("estimated_completion_time", int(concept.estimated_hours * 60)),
            generated_at=datetime.now(),
            content_version=context.get("content_version", 1),
        )
    
    async def execute(self, input_data: TutorialGenerationInput) -> TutorialGenerationOutput:
        """实现基类抽象方法"""
        return await self.generate(
            concept=input_data.concept,
            context=input_data.context,
            user_preferences=input_data.user_preferences,
        )
    
    # ============================================================
    # 辅助方法（保留旧版本逻辑）
    # ============================================================
    
    @staticmethod
    def _sanitize_json_control_chars(json_str: str) -> str:
        """
        转义 JSON 字符串值内的裸控制字符

        LLM 有时会在 markdown_content 等字段中直接输出实际的换行符（0x0A）、
        制表符（0x09）等控制字符，而 JSON 规范要求这些字符必须以 \\n、\\t 形式转义。
        此方法遍历字符串，仅对处于 JSON 字符串值内部（引号之间）的控制字符进行转义，
        不影响 JSON 结构字符。

        Args:
            json_str: 可能含裸控制字符的 JSON 字符串

        Returns:
            修复后的 JSON 字符串
        """
        _ESCAPE_MAP = {
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\b': '\\b',
            '\f': '\\f',
        }
        result: list[str] = []
        in_string = False
        escaped = False

        for ch in json_str:
            if escaped:
                result.append(ch)
                escaped = False
            elif ch == '\\' and in_string:
                result.append(ch)
                escaped = True
            elif ch == '"':
                result.append(ch)
                in_string = not in_string
            elif in_string and ord(ch) < 0x20:
                # 字符串值内的裸控制字符，转义为 JSON 合法形式
                result.append(_ESCAPE_MAP.get(ch, f'\\u{ord(ch):04x}'))
            else:
                result.append(ch)

        return ''.join(result)

    def _extract_json_object(self, content: str, concept_id: str) -> str | None:
        """
        从文本中提取JSON对象（使用正则表达式的健壮策略）
        
        Args:
            content: 包含JSON的文本
            concept_id: 概念ID（用于日志）
            
        Returns:
            提取的JSON字符串，如果找不到返回None
        """
        import re
        
        # 策略: 使用正则表达式查找JSON对象（支持嵌套）
        # 这个正则表达式会匹配从{开始到对应的}结束的内容
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        if matches:
            # 尝试解析每个匹配，返回第一个有效的JSON
            for match in sorted(matches, key=len, reverse=True):  # 优先尝试最长的匹配
                try:
                    json.loads(match)  # 验证是否是有效JSON
                    logger.info(
                        "tutorial_json_extracted_by_regex",
                        concept_id=concept_id,
                        extracted_length=len(match),
                        extracted_preview=match[:200]
                    )
                    return match
                except json.JSONDecodeError:
                    continue
        
        return None
    
    async def _parse_output(self, content: str, concept: Concept) -> tuple[str, dict]:
        """
        解析 JSON 格式的输出
        
        期望格式：
        {
            "markdown_content": "完整的 Markdown 教程内容",
            "metadata": {
                "title": "教程标题",
                "summary": "简短摘要",
                "estimated_completion_time": 90
            }
        }
        
        Args:
            content: LLM 返回的内容（应该是 JSON 格式）
            concept: 概念信息
        
        Returns:
            (Markdown 内容, 元数据字典) 元组
            
        Raises:
            ValueError: 当格式错误或必填字段缺失时
            json.JSONDecodeError: 当 JSON 解析失败时
            TypeError: 当返回类型不是字典时
        """
        # 记录接收到的原始内容
        logger.info(
            "tutorial_parse_output_start",
            concept_id=concept.concept_id,
            content_length=len(content),
            content_preview=content[:200],
        )
        
        # 去除可能的ReAct思考过程前缀
        json_content = content.strip()
        
        # 如果内容以"Thought:"开头,尝试找到JSON部分
        if json_content.startswith("Thought:"):
            # 尝试找到JSON对象的开始位置
            json_start = json_content.find("{")
            if json_start != -1:
                # 尝试找到匹配的JSON对象结束位置
                # 策略：从第一个{开始，找到完整的JSON对象
                brace_count = 0
                in_string = False
                escape_next = False
                json_end = json_start
                
                for i in range(json_start, len(json_content)):
                    char = json_content[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not in_string:
                        in_string = True
                    elif char == '"' and in_string:
                        in_string = False
                    elif char == '{' and not in_string:
                        brace_count += 1
                    elif char == '}' and not in_string:
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_content = json_content[json_start:json_end]
                else:
                    # 如果找不到完整的JSON对象，仍然使用从第一个{开始的内容
                    json_content = json_content[json_start:]
                
                logger.info(
                    "tutorial_react_thought_stripped",
                    concept_id=concept.concept_id,
                    message="Removed ReAct thought prefix, extracted JSON",
                    extracted_json_preview=json_content[:300],  # 增加：记录提取后的内容
                    extracted_json_length=len(json_content)
                )
            else:
                # 检测到 ReAct Thought 但没有 JSON：说明 LLM 提前终止
                logger.warning(
                    "tutorial_react_incomplete_response",
                    concept_id=concept.concept_id,
                    content_preview=json_content[:500],
                    message="LLM returned only ReAct thought without JSON. Attempting recovery..."
                )
                
                # 兜底策略：使用补充 prompt 强制生成 JSON
                recovery_prompt = f"""
你之前的思考过程已经完成：

{json_content[:1000]}

现在，请直接输出完整的 JSON 格式教程内容。

⚠️ 严格要求：
1. **第一个字符必须是左花括号 {{**
2. 不要添加任何前缀文字（如"Thought:"、"Action:"、"Final Answer:"等）
3. 不要使用代码块标记（不要用```包裹）
4. 使用标准JSON格式（双引号、正确转义）

JSON格式示例：
{{
  "markdown_content": "完整的 Markdown 教程内容（包含所有章节）",
  "metadata": {{
    "title": "教程标题",
    "summary": "简短摘要",
    "estimated_completion_time": 90
  }}
}}

请立即输出JSON（以 {{ 开始）：
"""
                
                try:
                    # 进行补充调用
                    recovery_messages = [
                        {"role": "user", "content": recovery_prompt}
                    ]
                    recovery_response = await self._call_llm(recovery_messages)
                    recovery_content = recovery_response.choices[0].message.content
                    
                    if not recovery_content or not recovery_content.strip():
                        raise ValueError("Recovery call returned empty content")
                    
                    logger.info(
                        "tutorial_react_recovery_success",
                        concept_id=concept.concept_id,
                        recovery_content_length=len(recovery_content),
                        recovery_content_preview=recovery_content[:200]
                    )
                    
                    # 使用恢复后的内容
                    json_content = recovery_content.strip()
                    
                except Exception as recovery_error:
                    logger.error(
                        "tutorial_react_recovery_failed",
                        concept_id=concept.concept_id,
                        recovery_error=str(recovery_error),
                        original_content_preview=json_content[:500]
                    )
                    raise ValueError(
                        f"LLM returned ReAct thought but no JSON object found, and recovery failed. "
                        f"Original content preview: {json_content[:200]}, "
                        f"Recovery error: {str(recovery_error)}"
                    )
        
        # 去除可能的代码块标记
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        elif json_content.startswith("```"):
            json_content = json_content[3:]
        
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        
        json_content = json_content.strip()
        
        # 额外的清理：移除JSON前后可能的文本
        # 如果内容不是以{开始，尝试找到第一个{
        if json_content and not json_content.startswith("{"):
            first_brace = json_content.find("{")
            if first_brace != -1:
                json_content = json_content[first_brace:]
                logger.info(
                    "tutorial_json_additional_cleanup",
                    concept_id=concept.concept_id,
                    message="Removed leading non-JSON text"
                )
        
        # 如果内容不是以}结束，尝试找到最后一个}
        if json_content and not json_content.endswith("}"):
            last_brace = json_content.rfind("}")
            if last_brace != -1:
                json_content = json_content[:last_brace + 1]
                logger.info(
                    "tutorial_json_additional_cleanup_trailing",
                    concept_id=concept.concept_id,
                    message="Removed trailing non-JSON text"
                )
        
        # 验证不为空
        if not json_content:
            logger.error(
                "tutorial_json_content_empty",
                concept_id=concept.concept_id,
                original_length=len(content),
            )
            raise ValueError(
                f"JSON content is empty after preprocessing. "
                f"Original content length: {len(content)}, "
                f"Preview: {content[:200]}"
            )
        
        # 解析 JSON（含三级容错）
        # 第一级：直接解析
        output = None
        first_error: json.JSONDecodeError | None = None
        try:
            output = json.loads(json_content)
        except json.JSONDecodeError as e:
            first_error = e
            logger.warning(
                "tutorial_json_parse_failed_attempt_extraction",
                concept_id=concept.concept_id,
                error_msg=str(e),
                error_line=e.lineno,
                error_col=e.colno,
                error_pos=e.pos,
                json_content_length=len(json_content),
                json_content_preview=json_content[:500],
                json_content_first_100_chars=repr(json_content[:100]),
            )

        # 第二级：转义 JSON 字符串值内的裸控制字符后重试
        # 原因：LLM 有时在 markdown_content 中输出实际的 \n、\t 等控制字符，
        # 而非 JSON 规范要求的 \\n、\\t 转义序列，导致 json.loads 失败。
        if output is None:
            sanitized = self._sanitize_json_control_chars(json_content)
            if sanitized != json_content:
                try:
                    output = json.loads(sanitized)
                    logger.info(
                        "tutorial_json_parsed_after_control_char_sanitize",
                        concept_id=concept.concept_id,
                        message="Parsed JSON successfully after sanitizing control characters",
                    )
                except json.JSONDecodeError:
                    pass  # 继续尝试第三级

        # 第三级：正则提取兜底
        if output is None:
            logger.info(
                "tutorial_attempting_regex_extraction",
                concept_id=concept.concept_id,
                message="Attempting to extract JSON using regex",
            )
            extracted_json = self._extract_json_object(content, concept.concept_id)
            if extracted_json:
                try:
                    output = json.loads(extracted_json)
                    logger.info(
                        "tutorial_regex_extraction_success",
                        concept_id=concept.concept_id,
                        message="Successfully extracted and parsed JSON using regex",
                    )
                except json.JSONDecodeError as regex_error:
                    logger.error(
                        "tutorial_regex_extraction_failed",
                        concept_id=concept.concept_id,
                        regex_error=str(regex_error),
                    )

        if output is None:
            logger.error(
                "tutorial_no_json_found",
                concept_id=concept.concept_id,
                message="Could not find valid JSON object in content",
            )
            raise ValueError(
                f"Failed to parse JSON for concept {concept.concept_id}. "
                f"Error: {str(first_error)} at line {first_error.lineno}, column {first_error.colno}. "
                f"Content preview (first 500 chars): {json_content[:500]}"
            ) from first_error
        
        # 类型检查：必须是字典
        if not isinstance(output, dict):
            logger.error(
                "tutorial_output_invalid_type",
                concept_id=concept.concept_id,
                expected_type="dict",
                actual_type=type(output).__name__,
                output_preview=str(output)[:200],
            )
            raise TypeError(
                f"Expected JSON object (dict), but got {type(output).__name__}. "
                f"Output preview: {str(output)[:200]}"
            )
        
        # 提取字段
        tutorial_markdown = output.get("markdown_content", "")
        metadata = output.get("metadata", {})
        
        # 验证必填字段
        if not tutorial_markdown:
            logger.error(
                "tutorial_markdown_empty",
                concept_id=concept.concept_id,
                output_keys=list(output.keys()),
            )
            raise ValueError(
                f"markdown_content field is empty or missing. "
                f"Available keys: {list(output.keys())}"
            )
        
        if not metadata:
            logger.error(
                "tutorial_metadata_empty",
                concept_id=concept.concept_id,
                output_keys=list(output.keys()),
            )
            raise ValueError(
                f"metadata field is missing or empty. "
                f"Available keys: {list(output.keys())}"
            )
        
        # 确保元数据包含所有必填字段
        if "title" not in metadata:
            metadata["title"] = concept.name
        if "summary" not in metadata:
            metadata["summary"] = concept.description[:100] if concept.description else ""
        if "estimated_completion_time" not in metadata:
            metadata["estimated_completion_time"] = int(concept.estimated_hours * 60)
        
        logger.info(
            "tutorial_output_parsed",
            concept_id=concept.concept_id,
            format="json",
            markdown_length=len(tutorial_markdown),
            metadata_keys=list(metadata.keys()),
        )
        
        return tutorial_markdown, metadata
    
    async def _upload_to_s3(
        self, 
        markdown: str, 
        concept_id: str, 
        context: dict
    ) -> str:
        """
        上传教程到 S3
        
        Returns:
            S3 Key（不是预签名 URL）
        """
        from app.tools.tool_helpers import tool_registry
        
        s3_tool = tool_registry.get("s3_upload")
        if not s3_tool:
            raise RuntimeError("S3 Storage Tool 未注册")
        
        # 构建 S3 Key
        roadmap_id = context.get("roadmap_id", "unknown")
        content_version = context.get("content_version", 1)
        s3_key = f"{roadmap_id}/concepts/{concept_id}/v{content_version}.md"
        
        upload_request = S3UploadRequest(
            key=s3_key,
            content=markdown,
            content_type="text/markdown",
        )
        
        await s3_tool.execute(upload_request)
        
        logger.info(
            "tutorial_uploaded_to_s3",
            concept_id=concept_id,
            s3_key=s3_key,
        )
        
        return s3_key
