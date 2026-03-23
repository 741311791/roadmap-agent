from types import SimpleNamespace

from app.agents.mentor_agent import MentorAgent, MentorAgentInput


def build_mock_settings() -> SimpleNamespace:
    """构建 AI 伴学助手测试配置。"""
    return SimpleNamespace(
        MENTOR_AGENT_PROVIDER="openai",
        MENTOR_AGENT_MODEL="deepseek/deepseek-v3.2",
        MENTOR_AGENT_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        get_mentor_agent_api_key="test-key",
        GEMINI_API_KEY="gemini-key",
        get_gemini_openai_base_url="https://api.ofox.ai/v1",
        MENTOR_AGENT_TEMPERATURE=0.7,
        MENTOR_AGENT_MAX_TOKENS=1024,
    )


def test_company_agent_selects_company_template() -> None:
    """company 模式应加载 company Prompt。"""
    agent = MentorAgent(build_mock_settings(), agent_type="company")
    assert agent._get_template_name() == "company_agent.j2"


def test_tutoring_agent_builds_messages_with_context() -> None:
    """导学模式应正确组装系统消息、历史消息与当前问题。"""
    agent = MentorAgent(build_mock_settings(), agent_type="tutoring")
    agent.prompt_loader.render = lambda template_name, **kwargs: (
        f"{template_name}|{kwargs['concept_title']}|{kwargs['ltm_preferences'][0]}|{kwargs['ltm_misconceptions'][0]}"
    )

    input_data = MentorAgentInput(
        user_message="请解释一下 useEffect",
        history_messages=[
            {"role": "assistant", "content": "我们先回顾一下副作用。"},
        ],
        concept_title="React Hooks",
        tutorial_excerpt="讲解 useEffect 的依赖数组。",
        roadmap_context="当前路线图：React 进阶",
        ltm_facts=["用户更偏好类比解释"],
        ltm_preferences=["用户更偏好类比解释"],
        ltm_misconceptions=["用户经常混淆副作用与事件处理"],
        learning_profile="当前用户昵称：louie",
    )

    messages = agent._build_messages(input_data)

    assert messages[0]["role"] == "system"
    assert "tutorin_agent.j2" in messages[0]["content"]
    assert "React Hooks" in messages[0]["content"]
    assert "用户更偏好类比解释" in messages[0]["content"]
    assert "用户经常混淆副作用与事件处理" in messages[0]["content"]
    assert messages[1] == {"role": "assistant", "content": "我们先回顾一下副作用。"}
    assert messages[2] == {"role": "user", "content": "请解释一下 useEffect"}


def test_requested_model_name_is_passed_through_directly() -> None:
    """前端传入的模型名称应原样传给底层客户端。"""
    agent = MentorAgent(
        build_mock_settings(),
        agent_type="company",
        model_name="google/gemini-3.1-pro-preview",
    )

    assert agent.requested_model_name == "google/gemini-3.1-pro-preview"
    assert agent.model_name == "google/gemini-3.1-pro-preview"
    assert agent.base_url == "https://api.ofox.ai/v1"
    assert agent.api_key == "gemini-key"


def test_requested_deepseek_model_keeps_dynamic_override() -> None:
    """已指定模型时应继续保留动态覆盖能力。"""
    agent = MentorAgent(
        build_mock_settings(),
        agent_type="tutoring",
        model_name="deepseek/deepseek-v3.2",
    )

    assert agent.requested_model_name == "deepseek/deepseek-v3.2"
    assert agent.model_name == "deepseek/deepseek-v3.2"
    assert agent.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert agent.api_key == "test-key"


def test_empty_requested_model_falls_back_to_default_model() -> None:
    """仅当请求未提供模型名称时才回退到默认模型。"""
    agent = MentorAgent(
        build_mock_settings(),
        agent_type="tutoring",
        model_name="   ",
    )

    assert agent.requested_model_name == "deepseek/deepseek-v3.2"
    assert agent.model_name == "deepseek/deepseek-v3.2"
