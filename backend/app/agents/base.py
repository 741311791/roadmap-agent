"""
Agent 基类（封装 LiteLLM 调用）
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, AsyncIterator
import litellm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

from app.utils.prompt_loader import PromptLoader
from app.utils.cost_tracker import cost_tracker

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    每个 Agent 都需要从环境变量中加载以下配置：
    - provider: 模型提供商（如 'openai', 'anthropic'）
    - model: 模型名称（如 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'）
    - base_url: 自定义 API 端点（可选，用于本地部署或代理）
    - api_key: API 密钥（必需）
    
    这些配置通过 Settings 类从 .env 文件加载。
    """
    
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(litellm.RateLimitError),
    )
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
        response_format: Dict | None = None,
    ) -> Any:
        """
        调用 LLM（通过 LiteLLM）
        
        Args:
            messages: 对话消息列表
            tools: 工具定义（可选）
            response_format: 响应格式（可选，如 {"type": "json_object"} 强制返回 JSON）
            
        Returns:
            LLM 响应对象
        """
        try:
            # 构建模型标识符
            model_identifier = f"{self.model_provider}/{self.model_name}"
            
            # 准备调用参数
            call_params = {
                "model": model_identifier,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            # 添加可选参数
            if self.base_url:
                call_params["api_base"] = self.base_url
            if self.api_key:
                call_params["api_key"] = self.api_key
            if tools:
                call_params["tools"] = tools
            if response_format:
                call_params["response_format"] = response_format
            
            # 使用 custom_llm_provider 让 litellm 将请求转发到 base_url
            # 而不是尝试匹配内置模型配置
            if self.base_url:
                call_params["custom_llm_provider"] = "openai"
            
            response = await litellm.acompletion(**call_params)
            
            # 追踪成本
            if hasattr(response, 'usage') and response.usage:
                self.cost_tracker.track(
                    agent_id=self.agent_id,
                    model=self.model_name,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                )
            
            logger.info(
                "llm_call_success",
                agent_id=self.agent_id,
                model=self.model_name,
                prompt_tokens=getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                completion_tokens=getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
            )
            
            return response
            
        except litellm.RateLimitError as e:
            logger.warning("llm_rate_limit", agent_id=self.agent_id, error=str(e))
            raise
        except Exception as e:
            logger.error("llm_call_failed", agent_id=self.agent_id, error=str(e))
            raise
    
    async def _call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
    ) -> AsyncIterator[str]:
        """
        流式调用 LLM（通过 LiteLLM）
        
        Args:
            messages: 对话消息列表
            tools: 工具定义（可选）
            
        Yields:
            流式文本片段
        """
        try:
            # 构建模型标识符
            model_identifier = f"{self.model_provider}/{self.model_name}"
            
            # 准备调用参数
            call_params = {
                "model": model_identifier,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,  # 关键：开启流式
            }
            
            # 添加可选参数
            if self.base_url:
                call_params["api_base"] = self.base_url
            if self.api_key:
                call_params["api_key"] = self.api_key
            if tools:
                call_params["tools"] = tools
            
            # 使用 custom_llm_provider 让 litellm 将请求转发到 base_url
            if self.base_url:
                call_params["custom_llm_provider"] = "openai"
            
            # 流式调用
            response_stream = await litellm.acompletion(**call_params)
            
            # 累积完整响应用于成本追踪
            full_content = ""
            total_chunks = 0
            
            async for chunk in response_stream:
                # 提取 delta 内容
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_content += content
                        total_chunks += 1
                        yield content
            
            logger.info(
                "llm_stream_completed",
                agent_id=self.agent_id,
                model=self.model_name,
                total_length=len(full_content),
                total_chunks=total_chunks,
            )
            
        except litellm.RateLimitError as e:
            logger.warning("llm_stream_rate_limit", agent_id=self.agent_id, error=str(e))
            raise
        except Exception as e:
            logger.error("llm_stream_failed", agent_id=self.agent_id, error=str(e))
            raise
    
    def _load_system_prompt(self, template_name: str, **kwargs) -> str:
        """加载并渲染 System Prompt"""
        return self.prompt_loader.render(template_name, **kwargs)
    
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

