from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.database import MentorModelConfig
from app.schemas.mentor_model import MentorModelCreateRequest
from app.services.shared.mentor_model_registry_service import MentorModelRegistryService
from app.utils.secret_box import encrypt_secret


class _FakeExecuteResult:
    """模拟 SQLAlchemy execute 结果。"""

    def __init__(self, *, one=None, all_items=None) -> None:
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return SimpleNamespace(all=lambda: self._all_items)


@pytest.mark.asyncio
async def test_list_available_models_falls_back_to_env_when_registry_empty(monkeypatch) -> None:
    """当注册表为空时，应返回环境变量兜底模型。"""
    service = MentorModelRegistryService()
    fake_session = SimpleNamespace(
        execute=AsyncMock(return_value=_FakeExecuteResult(all_items=[]))
    )

    redis_client = SimpleNamespace(
        get_json=AsyncMock(return_value=None),
        set_json=AsyncMock(),
    )
    monkeypatch.setattr(service, "redis_client", redis_client)

    items, default_model_id = await service.list_available_models(
        fake_session,
        user_id="user-1",
    )

    assert len(items) == 1
    assert items[0].model_id == default_model_id
    assert items[0].is_default is True
    runtime_config = service._build_fallback_runtime_config()
    assert runtime_config.supports_thinking is False
    redis_client.set_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_runtime_config_returns_decrypted_registry_item(monkeypatch) -> None:
    """命中注册表时，应返回解密后的运行时配置。"""
    service = MentorModelRegistryService()
    record = MentorModelConfig(
        model_id="model-1",
        display_name="Claude Sonnet 4",
        provider="anthropic",
        model_name="anthropic/claude-sonnet-4",
        base_url="https://gateway.example.com/v1",
        api_key_encrypted=encrypt_secret("secret-key"),
        supports_streaming=True,
        supports_structured_output=True,
        supports_tools=False,
        supports_thinking=True,
    )
    fake_session = SimpleNamespace(
        execute=AsyncMock(return_value=_FakeExecuteResult(one=record))
    )

    redis_client = SimpleNamespace(
        get_json=AsyncMock(return_value=None),
        set_json=AsyncMock(),
    )
    monkeypatch.setattr(service, "redis_client", redis_client)

    runtime_config = await service.get_runtime_config(
        fake_session,
        model_id="model-1",
        user_id="user-1",
    )

    assert runtime_config.model_id == "model-1"
    assert runtime_config.model_name == "anthropic/claude-sonnet-4"
    assert runtime_config.base_url == "https://gateway.example.com/v1"
    assert runtime_config.api_key == "secret-key"
    assert runtime_config.source == "registry"
    assert runtime_config.supports_thinking is True


@pytest.mark.asyncio
async def test_create_model_encrypts_api_key_and_triggers_default_update(monkeypatch) -> None:
    """创建模型时应加密 API Key，并在需要时触发默认模型更新。"""
    service = MentorModelRegistryService()
    fake_session = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
    )
    set_default_mock = AsyncMock()
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(service, "_set_system_default", set_default_mock)
    monkeypatch.setattr(service, "_invalidate_caches", invalidate_mock)

    record = await service.create_model(
        fake_session,
        MentorModelCreateRequest(
            display_name="Gemini 3.1 Pro Preview",
            provider="openai",
            model_name="google/gemini-3.1-pro-preview",
            base_url="https://api.example.com/v1",
            api_key="secret-key",
            is_active=True,
            is_visible=True,
            is_default=True,
            supports_streaming=True,
            supports_structured_output=True,
            supports_tools=False,
            supports_thinking=True,
            scope="system",
        ),
    )

    assert record.api_key_encrypted != "secret-key"
    assert record.scope == "system"
    assert record.owner_user_id is None
    assert record.supports_thinking is True
    fake_session.add.assert_called_once()
    fake_session.flush.assert_awaited()
    set_default_mock.assert_awaited_once()
    invalidate_mock.assert_awaited_once_with(record.model_id)

