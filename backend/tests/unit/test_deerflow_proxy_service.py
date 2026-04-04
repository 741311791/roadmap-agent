from app.models.database import RoadmapChatThread, beijing_now
from app.services.learning.deerflow_context_service import DeerFlowContextService
from app.services.learning.deerflow_proxy_service import DeerFlowProxyService


def test_strip_injected_context_returns_original_user_request() -> None:
    """上下文注入包装应能恢复出原始用户输入。"""

    raw_message = (
        "<learning_context>\n"
        "这是产品侧注入的路线图上下文。\n"
        "</learning_context>\n\n"
        "<user_request>\n"
        "请解释一下当前 concept。\n"
        "</user_request>"
    )

    assert DeerFlowContextService.strip_injected_context(raw_message) == "请解释一下当前 concept。"


def test_map_upstream_messages_to_responses_strips_context_and_keeps_reasoning_parts() -> None:
    """Deer-Flow 状态消息应被映射为前端可消费的消息结构。"""

    service = DeerFlowProxyService()
    thread = RoadmapChatThread(
        thread_id="thread-1",
        user_id="user-1",
        roadmap_id="roadmap-1",
        created_at=beijing_now(),
        updated_at=beijing_now(),
    )
    upstream_messages = [
        {
            "id": "human-1",
            "type": "human",
            "content": (
                "<learning_context>\n"
                "这里是上下文。\n"
                "</learning_context>\n\n"
                "<user_request>\n"
                "真正的问题。\n"
                "</user_request>"
            ),
        },
        {
            "id": "ai-1",
            "type": "ai",
            "content": "这是最终回答。",
            "additional_kwargs": {
                "reasoning_content": "先分析当前学习状态。",
            },
        },
    ]

    messages = service._map_upstream_messages_to_responses(
        thread=thread,
        upstream_messages=upstream_messages,
    )

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "真正的问题。"
    assert messages[1].role == "assistant"
    assert messages[1].message_metadata is not None
    assert messages[1].message_metadata["content_parts"][0]["type"] == "thinking"
    assert messages[1].message_metadata["content_parts"][0]["text"] == "先分析当前学习状态。"
    assert messages[1].message_metadata["content_parts"][1]["type"] == "text"
    assert messages[1].message_metadata["content_parts"][1]["text"] == "这是最终回答。"


def test_map_upstream_messages_to_responses_keeps_tool_call_metadata() -> None:
    """assistant tool_calls 与 tool message 结果应被持久化到 message_metadata。"""

    service = DeerFlowProxyService()
    thread = RoadmapChatThread(
        thread_id="thread-2",
        user_id="user-1",
        roadmap_id="roadmap-1",
        created_at=beijing_now(),
        updated_at=beijing_now(),
    )
    upstream_messages = [
        {
            "id": "ai-1",
            "type": "ai",
            "content": "我先帮你查资料。",
            "tool_calls": [
                {
                    "id": "tool-1",
                    "name": "web_search",
                    "args": {
                        "query": "numpy slicing",
                    },
                }
            ],
        },
        {
            "id": "tool-msg-1",
            "type": "tool",
            "tool_call_id": "tool-1",
            "name": "web_search",
            "content": "搜索完成。",
        },
    ]

    messages = service._map_upstream_messages_to_responses(
        thread=thread,
        upstream_messages=upstream_messages,
    )

    assert len(messages) == 1
    content_parts = messages[0].message_metadata["content_parts"]
    assert content_parts[0]["type"] == "text"
    assert content_parts[1]["type"] == "tool-call"
    assert content_parts[1]["toolCallId"] == "tool-1"
    assert content_parts[1]["toolName"] == "web_search"
    assert content_parts[1]["arguments"] == {"query": "numpy slicing"}
    assert content_parts[1]["state"] == "completed"
    assert content_parts[1]["result"] == "搜索完成。"


def test_map_upstream_messages_to_responses_coerces_json_string_tool_arguments() -> None:
    """tool_calls 使用 arguments JSON 字符串或 OpenAI function.arguments 时应解析出 path 等字段。"""

    service = DeerFlowProxyService()
    thread = RoadmapChatThread(
        thread_id="thread-3",
        user_id="user-1",
        roadmap_id="roadmap-1",
        created_at=beijing_now(),
        updated_at=beijing_now(),
    )
    upstream_messages = [
        {
            "id": "ai-1",
            "type": "ai",
            "content": "",
            "tool_calls": [
                {
                    "id": "tool-1",
                    "name": "read_file",
                    "arguments": '{"path": "/mnt/user-data/workspace/a.md", "description": "read"}',
                }
            ],
        },
        {
            "id": "tool-msg-1",
            "type": "tool",
            "tool_call_id": "tool-1",
            "name": "read_file",
            "content": "ok",
        },
        {
            "id": "ai-2",
            "type": "ai",
            "content": "",
            "tool_calls": [
                {
                    "id": "tool-2",
                    "name": "write_file",
                    "function": {"arguments": '{"path": "/mnt/user-data/outputs/b.txt"}'},
                }
            ],
        },
        {
            "id": "tool-msg-2",
            "type": "tool",
            "tool_call_id": "tool-2",
            "name": "write_file",
            "content": "OK",
        },
    ]

    messages = service._map_upstream_messages_to_responses(
        thread=thread,
        upstream_messages=upstream_messages,
    )

    assert len(messages) == 2
    parts0 = messages[0].message_metadata["content_parts"]
    tool_read = next(p for p in parts0 if p.get("type") == "tool-call" and p.get("toolName") == "read_file")
    assert tool_read["arguments"]["path"] == "/mnt/user-data/workspace/a.md"

    parts1 = messages[1].message_metadata["content_parts"]
    tool_write = next(p for p in parts1 if p.get("type") == "tool-call" and p.get("toolName") == "write_file")
    assert tool_write["arguments"]["path"] == "/mnt/user-data/outputs/b.txt"


def test_collect_tool_results_extracts_error_state() -> None:
    """tool message 结果收集应保留错误状态。"""

    results = DeerFlowProxyService._collect_tool_results(
        [
            {
                "type": "tool",
                "tool_call_id": "tool-1",
                "content": "执行失败。",
                "status": "error",
            }
        ]
    )

    assert results == {
        "tool-1": {
            "result": "执行失败。",
            "is_error": True,
        }
    }
