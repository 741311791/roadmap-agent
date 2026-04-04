"""
Mentor 运行时工厂
"""

from app.config.settings import Settings
from app.schemas.mentor_model import MentorModelRuntimeConfig
from app.services.learning.mentor.graph_runner import QaAgentGraphRunner
from app.services.learning.mentor.prompt_builder import QaPromptBuilder
from app.services.learning.mentor.tool_executor import MentorToolExecutor
from app.services.learning.mentor.tool_policy import MentorToolPolicy
from app.tools.registry import ToolRegistry


class MentorRuntimeFactory:
    """
    创建聊天 Agent 运行时实例
    """

    def __init__(
        self,
        *,
        settings: Settings,
        tool_registry: ToolRegistry | None,
    ) -> None:
        self.settings = settings
        self.tool_registry = tool_registry

    def create_qa_runner(
        self,
        *,
        runtime_config: MentorModelRuntimeConfig,
    ) -> QaAgentGraphRunner:
        """
        创建答疑 Agent 运行器
        """

        prompt_builder = QaPromptBuilder()
        tool_policy = MentorToolPolicy()
        tool_executor = MentorToolExecutor(self.tool_registry)
        return QaAgentGraphRunner(
            settings=self.settings,
            runtime_config=runtime_config,
            prompt_builder=prompt_builder,
            tool_policy=tool_policy,
            tool_executor=tool_executor,
        )
