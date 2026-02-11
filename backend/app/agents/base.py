"""
Agent 基类（使用 OpenAI SDK 的两阶段生成）
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, TypeVar
import json
import time
import structlog
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI

from app.utils.prompt_loader import PromptLoader
from app.utils.cost_tracker import cost_tracker
from app.core.rate_limiter import get_rate_limiter
from app.models.domain import UserConstraints, ConstraintNames, IntentAnalysisOutput

logger = structlog.get_logger()

T = TypeVar('T', bound=BaseModel)


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    每个 Agent 都需要从环境变量中加载以下配置：
    - provider: 模型提供商（如 'openai', 'anthropic'）
    - model: 模型名称（如 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'）
    - base_url: 自定义 API 端点（可选，用于本地部署或代理）
    - api_key: API 密钥（必需）
    
    这些配置通过 Settings 类从 .env 文件加载。
    
    使用原生 OpenAI SDK 提供：
    - 标准 chat.completions.create: 标准 LLM 调用
    - beta.chat.completions.parse: 结构化输出（Pydantic 实例）
    - 两阶段生成：思维链 + 结构化提取（提升复杂 JSON 生成质量）
    - 自动成本追踪和速率限制管理
    """
    
    # 第二阶段的通用提取 prompt
    EXTRACTION_SYSTEM_PROMPT = """你是一个数据提取助手。请将用户提供的 Markdown 文本精确转换为 JSON 格式。
严格遵守给定的数据结构，不要遗漏任何信息。"""
    
    def __init__(
        self,
        agent_id: str,
        model_provider: str,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.agent_id = agent_id
        self.model_provider = model_provider
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.prompt_loader = PromptLoader()
        self.cost_tracker = cost_tracker
        self.rate_limiter = get_rate_limiter()
        
        # 创建 OpenAI 客户端（兼容 DashScope 等提供商）
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    async def _standard_call(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None
    ) -> Any:
        """
        标准 LLM 调用（不带结构化输出）
        
        Args:
            messages: 对话消息列表
            tools: 工具定义（可选）
            
        Returns:
            原始 LLM 响应对象
        """
        logger.debug(
            "calling_llm_standard",
            agent_id=self.agent_id,
            model=self.model_name,
            has_tools=tools is not None
        )
        
        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tools,
        )
        
        # 成本追踪
        if response.usage:
            self.cost_tracker.track(
                agent_id=self.agent_id,
                model=self.model_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )
        
        logger.info(
            "llm_call_success",
            agent_id=self.agent_id,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        
        return response
    
    async def _single_stage_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T]
    ) -> T:
        """
        单阶段结构化生成（直接生成 JSON）
        
        Args:
            messages: 对话消息列表
            response_model: Pydantic 输出模型
            
        Returns:
            Pydantic 模型实例
        """
        logger.info(
            "calling_llm_single_stage_structured",
            agent_id=self.agent_id,
            model=self.model_name,
            response_model=response_model.__name__,
        )
        
        response = await self._client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=response_model,
        )
        
        # 成本追踪
        if response.usage:
            self.cost_tracker.track(
                agent_id=self.agent_id,
                model=self.model_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )
        
        result = response.choices[0].message.parsed
        
        logger.info(
            "structured_output_success",
            agent_id=self.agent_id,
            response_type=type(result).__name__,
        )
        
        return result
    
    async def _two_stage_generation(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T]
    ) -> T:
        """
        两阶段生成（思维链 + 结构化提取）
        
        阶段 1：生成 Markdown（专注于内容质量，减轻格式负担）
        阶段 2：提取 JSON（专注于结构化，保证格式正确）
        
        Args:
            messages: 对话消息列表
            response_model: Pydantic 输出模型
            
        Returns:
            Pydantic 模型实例
        """
        logger.info(
            "calling_llm_two_stage_generation",
            agent_id=self.agent_id,
            model=self.model_name,
            response_model=response_model.__name__,
        )
        
        # ====== 阶段 1: 生成 Markdown ======
        stage1_start = time.time()
        
        logger.debug("two_stage_stage1_started", stage="markdown_generation")
        
        stage1_response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,  # 调用方已准备好的 prompt
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        stage1_duration = time.time() - stage1_start
        markdown_content = stage1_response.choices[0].message.content
        
        # 追踪阶段 1 成本
        if stage1_response.usage:
            self.cost_tracker.track(
                agent_id=f"{self.agent_id}_stage1",
                model=self.model_name,
                prompt_tokens=stage1_response.usage.prompt_tokens,
                completion_tokens=stage1_response.usage.completion_tokens,
            )
        
        logger.info(
            "two_stage_stage1_completed",
            duration_seconds=round(stage1_duration, 2),
            content_length=len(markdown_content),
            prompt_tokens=stage1_response.usage.prompt_tokens if stage1_response.usage else 0,
            completion_tokens=stage1_response.usage.completion_tokens if stage1_response.usage else 0,
        )
        logger.debug(
            "two_stage_stage1_content",
            content=markdown_content[:100] + "...",
        )
        
        # ====== 阶段 2: 结构化提取 ======
        stage2_start = time.time()
        
        logger.debug("two_stage_stage2_started", stage="json_extraction")
        
        stage2_response = await self._client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": markdown_content},
            ],
            response_format=response_model,
            temperature=0.1,

        )
        
        stage2_duration = time.time() - stage2_start
        result = stage2_response.choices[0].message.parsed
        
        # 追踪阶段 2 成本
        if stage2_response.usage:
            self.cost_tracker.track(
                agent_id=f"{self.agent_id}_stage2",
                model=self.model_name,
                prompt_tokens=stage2_response.usage.prompt_tokens,
                completion_tokens=stage2_response.usage.completion_tokens,
            )
        
        # 汇总统计
        total_duration = stage1_duration + stage2_duration
        total_input_tokens = (
            (stage1_response.usage.prompt_tokens if stage1_response.usage else 0) +
            (stage2_response.usage.prompt_tokens if stage2_response.usage else 0)
        )
        total_output_tokens = (
            (stage1_response.usage.completion_tokens if stage1_response.usage else 0) +
            (stage2_response.usage.completion_tokens if stage2_response.usage else 0)
        )
        
        logger.info(
            "two_stage_generation_completed",
            agent_id=self.agent_id,
            total_duration_seconds=round(total_duration, 2),
            stage1_duration=round(stage1_duration, 2),
            stage2_duration=round(stage2_duration, 2),
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            response_type=type(result).__name__,
        )
        
        return result
    
    async def _call_llm_with_tools_react(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        tool_choice: str = "auto",
        max_iterations: int = 5,
    ) -> Any:
        """
        ReAct 模式的工具调用（含循环）
        
        实现标准的 ReAct 循环：
        1. 调用 LLM（带工具定义）
        2. 如果 LLM 返回工具调用 → 执行工具 → 将结果添加到消息 → 重复
        3. 如果 LLM 返回文本响应 → 返回结果
        4. 达到最大迭代次数 → 抛出异常
        
        Args:
            messages: 对话消息列表
            tools: 工具定义列表（OpenAI function calling 格式）
            tool_choice: 工具选择策略（"auto" | "none" | {"type": "function", "function": {"name": "tool_name"}}）
            max_iterations: 最大迭代次数（防止无限循环）
        
        Returns:
            LLM 的最终文本响应
        
        Raises:
            ValueError: 达到最大迭代次数仍未得到最终响应
            Exception: 工具执行失败
        """
        iteration = 0
        conversation = messages.copy()
        
        logger.info(
            "react_loop_started",
            agent_id=self.agent_id,
            max_iterations=max_iterations,
            tools_count=len(tools),
        )
        
        while iteration < max_iterations:
            iteration += 1
            
            logger.debug(
                "react_iteration_started",
                agent_id=self.agent_id,
                iteration=iteration,
                conversation_length=len(conversation),
            )
            
            # 调用 LLM
            response = await self._standard_call(
                messages=conversation,
                tools=tools,
            )
            
            message = response.choices[0].message
            
            # 检查是否有工具调用
            if not message.tool_calls:
                # 没有工具调用，返回最终响应
                logger.info(
                    "react_loop_completed",
                    agent_id=self.agent_id,
                    total_iterations=iteration,
                    finish_reason=response.choices[0].finish_reason,
                )
                return response
            
            # 有工具调用，执行工具
            logger.debug(
                "react_executing_tools",
                agent_id=self.agent_id,
                iteration=iteration,
                tool_calls_count=len(message.tool_calls),
            )
            
            # 将 assistant 的工具调用消息添加到对话历史
            conversation.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            # 执行所有工具调用并添加结果到对话历史
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
                
                try:
                    # 解析工具参数
                    tool_args = json.loads(tool_args_str)
                    
                    logger.debug(
                        "react_tool_executing",
                        agent_id=self.agent_id,
                        iteration=iteration,
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )
                    
                    # 执行工具（子类需要实现 _execute_tool 方法）
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    
                    logger.debug(
                        "react_tool_executed",
                        agent_id=self.agent_id,
                        iteration=iteration,
                        tool_name=tool_name,
                        result_preview=str(tool_result)[:200],
                    )
                    
                    # 将工具结果添加到对话历史
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    })
                    
                except Exception as e:
                    logger.error(
                        "react_tool_execution_failed",
                        agent_id=self.agent_id,
                        iteration=iteration,
                        tool_name=tool_name,
                        error=str(e),
                    )
                    
                    # 将错误信息添加到对话历史
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps({
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }, ensure_ascii=False),
                    })
        
        # 达到最大迭代次数，强制生成最终输出
        logger.warning(
            "react_max_iterations_reached_forcing_output",
            agent_id=self.agent_id,
            max_iterations=max_iterations,
            message="已达最大迭代次数，强制LLM基于已收集信息生成最终输出"
        )
        
        # 添加系统强制输出指令
        conversation.append({
            "role": "system",
            "content": (
                "🚨 重要提示：你已达到最大工具调用次数限制。\n\n"
                "现在你**必须**基于目前已收集的所有信息，立即生成最终输出。\n"
                "不要再尝试调用任何工具，不要说'需要更多信息'。\n"
                "请综合利用你已经获取的文档内容和你的知识，完成教程生成任务。\n\n"
                "即使信息不够完美，也请生成一个质量尽可能高的教程。"
            )
        })
        
        # 最后一次调用LLM，强制文本输出（禁用工具）
        final_response = await self._standard_call(
            messages=conversation,
            tools=None,  # 不再提供工具
        )
        
        logger.info(
            "react_forced_completion",
            agent_id=self.agent_id,
            total_iterations=max_iterations,
            message="已强制生成最终输出"
        )
        
        return final_response
    
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T] | None = None,
        tools: List[Dict] | None = None,
        use_two_stage: bool = False,
        use_react: bool = False,
        max_iterations: int = 5,
    ) -> T | Any:
        """
        调用 LLM（支持单阶段、两阶段、ReAct 工具调用）
        
        速率限制说明：
        - 在调用LLM前，通过全局速率限制器获取许可
        - 如果当前速率超限，自动等待直到可以调用
        - 防止超过API厂商的IP级别RPM限制
        
        Args:
            messages: 对话消息列表
            response_model: Pydantic 输出模型（可选）
                - 如果传入：返回验证好的 Pydantic 实例
                - 如果不传：返回原始 LLM 响应对象
            tools: 工具定义（可选，OpenAI function calling 格式）
            use_two_stage: 是否使用两阶段生成（仅在 response_model 存在时有效）
            use_react: 是否使用 ReAct 工具调用循环（仅在 tools 存在时有效）
            max_iterations: ReAct 循环的最大迭代次数（默认 5）
        
        Returns:
            - 如果传入 response_model：返回 Pydantic 实例
            - 如果未传入：返回原始 LLM 响应对象
        """
        try:
            # ⭐ 速率限制：调用前获取许可
            await self.rate_limiter.acquire(self.model_provider)
            
            # 分支 1: ReAct 工具调用
            if tools and use_react:
                if response_model:
                    raise ValueError(
                        "ReAct 模式不支持同时使用 response_model。"
                        "请在工具调用完成后再进行结构化提取。"
                    )
                return await self._call_llm_with_tools_react(
                    messages, tools, tool_choice="auto", max_iterations=max_iterations
                )
            
            # 分支 2: 标准调用（无结构化输出）
            if not response_model:
                return await self._standard_call(messages, tools)
            
            # 分支 3: 两阶段生成
            if use_two_stage:
                return await self._two_stage_generation(messages, response_model)
            
            # 分支 4: 单阶段结构化生成
            return await self._single_stage_structured(messages, response_model)
            
        except ValidationError as e:
            logger.error(
                "pydantic_validation_failed",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        except Exception as e:
            logger.error(
                "llm_call_failed",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _get_required_constraints(self) -> List[str]:
        """
        获取当前 Agent 需要的约束类型
        
        子类可覆盖此方法以定制约束需求
        默认返回通用约束
        
        Returns:
            约束名称列表
        """
        return [
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
        ]
    
    def _filter_constraints(
        self,
        all_constraints: UserConstraints
    ) -> UserConstraints:
        """
        过滤出当前 Agent 需要的约束
        
        Args:
            all_constraints: 完整的约束字典
            
        Returns:
            过滤后的约束字典
        """
        required = self._get_required_constraints()
        return {
            name: content
            for name, content in all_constraints.items()
            if name in required
        }
    
    async def _load_user_constraints(
        self,
        roadmap_id: str | None = None,
        intent_analysis: IntentAnalysisOutput | None = None
    ) -> UserConstraints:
        """
        加载用户约束
        
        优先级：
        1. 直接传入的 intent_analysis
        2. 通过 roadmap_id 查询数据库
        3. 返回空字典
        
        Args:
            roadmap_id: 路线图ID（用于查询数据库）
            intent_analysis: 意图分析结果（直接传入）
            
        Returns:
            约束字典
        """
        # 方式1：直接传入
        if intent_analysis and intent_analysis.full_analysis_data:
            return self._filter_constraints(intent_analysis.full_analysis_data)
        
        # 方式2：通过 roadmap_id 查询
        if roadmap_id:
            try:
                from app.crud.crud_intent_analysis import get_intent_analysis_crud
                from app.db.session import async_session_maker
                
                async with async_session_maker() as session:
                    intent_crud = get_intent_analysis_crud()
                    metadata = await intent_crud.get_by_roadmap_id(session, roadmap_id)
                    
                    if metadata and metadata.full_analysis_data:
                        return self._filter_constraints(metadata.full_analysis_data)
            except Exception as e:
                logger.warning(
                    "failed_to_load_user_constraints",
                    agent_id=self.agent_id,
                    roadmap_id=roadmap_id,
                    error=str(e)
                )
        
        # 默认返回空字典
        return {}
    
    def _load_system_prompt(
        self,
        template_name: str,
        user_constraints: UserConstraints | None = None,
        **kwargs
    ) -> str:
        """
        加载并渲染 System Prompt
        
        Args:
            template_name: 模板文件名（如 "intent_analyzer.j2"）
            user_constraints: 用户约束字典（自动注入到模板）
            **kwargs: 其他模板变量
            
        Returns:
            渲染后的 Prompt
        """
        # 如果没有传入 user_constraints，则为空字典
        if user_constraints is None:
            user_constraints = {}
        
        # 自动注入 user_constraints 到模板变量
        kwargs["user_constraints"] = user_constraints
        
        return self.prompt_loader.render(template_name, **kwargs)
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Any:
        """
        执行工具调用（由子类实现）
        
        子类应该：
        1. 维护工具注册表（如 ToolRegistry）
        2. 根据 tool_name 查找对应的工具
        3. 执行工具并返回结果
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
        
        Returns:
            工具执行结果（可序列化为 JSON）
        
        Raises:
            NotImplementedError: 子类未实现此方法
            ValueError: 工具不存在或参数错误
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} 需要实现 _execute_tool 方法才能使用 ReAct 工具调用。"
            f"请在子类中实现工具执行逻辑。"
        )
    
    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """
        执行 Agent 任务（由子类实现）
        
        Args:
            input_data: 输入数据（对应 Agent 的 InputSchema）
            
        Returns:
            输出数据（对应 Agent 的 OutputSchema）
        """
        pass
