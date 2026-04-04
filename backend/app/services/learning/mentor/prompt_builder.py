"""
答疑 Agent Prompt 构建器
"""

from app.services.learning.mentor.event_types import MentorQaAgentInput
from app.utils.prompt_loader import PromptLoader


class QaPromptBuilder:
    """
    负责构建答疑 Agent 的系统 Prompt 与消息列表
    """

    def __init__(self) -> None:
        self.prompt_loader = PromptLoader()

    @staticmethod
    def get_template_name() -> str:
        """
        获取答疑 Agent 的 Prompt 模板名称
        """

        return "qa_agent.j2"

    def build_system_prompt(self, input_data: MentorQaAgentInput, *, current_date: str) -> str:
        """
        渲染系统 Prompt
        """

        return self.prompt_loader.render(
            self.get_template_name(),
            current_date=current_date,
            concept_title=input_data.concept_title,
            tutorial_excerpt=input_data.tutorial_excerpt,
            roadmap_context=input_data.roadmap_context,
            ltm_facts=input_data.ltm_facts,
            ltm_preferences=input_data.ltm_preferences,
            ltm_goals=input_data.ltm_goals,
            ltm_misconceptions=input_data.ltm_misconceptions,
            ltm_progress=input_data.ltm_progress,
            ltm_other_facts=input_data.ltm_other_facts,
            learning_profile=input_data.learning_profile,
            qa_style=input_data.qa_style,
            emotion_label=input_data.emotion.label,
            emotion_summary=input_data.emotion.summary,
        )

    def build_messages(self, input_data: MentorQaAgentInput, *, current_date: str) -> list[dict[str, str]]:
        """
        组装模型输入消息
        """

        system_prompt = self.build_system_prompt(input_data, current_date=current_date)
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(input_data.history_messages)
        messages.append({"role": "user", "content": input_data.user_message})
        return messages
