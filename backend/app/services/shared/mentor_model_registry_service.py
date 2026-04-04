"""
Mentor 模型注册表共享服务
"""
from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config.settings import settings
from app.core.custom_exceptions import errors
from app.db.redis_client import get_redis_client
from app.models.database import MentorModelConfig, beijing_now
from app.schemas.mentor_model import (
    MentorModelAdminItem,
    MentorModelCreateRequest,
    MentorModelDraftTestRequest,
    MentorModelPublicItem,
    MentorModelRuntimeConfig,
    MentorModelTestResponse,
    MentorModelUpdateRequest,
)
from app.utils.secret_box import decrypt_secret, encrypt_secret

logger = structlog.get_logger()


class _StructuredOutputProbe(BaseModel):
    """
    结构化输出探针
    """

    ok: bool
    message: str


class MentorModelRegistryService:
    """
    Mentor 模型注册表服务

    职责：
    - 管理模型注册表 CRUD
    - 提供 Mentor 前端可消费的模型列表
    - 为运行时解析完整模型配置
    - 测试 OpenAI 兼容网关能力
    """

    MODEL_CACHE_KEY_PREFIX = "mentor:model"
    MODEL_LIST_CACHE_KEY_PREFIX = "mentor:model-list"

    def __init__(self) -> None:
        self.redis_client = get_redis_client()

    def _build_model_cache_key(self, model_id: str) -> str:
        """
        构建单模型缓存键
        """
        return f"{self.MODEL_CACHE_KEY_PREFIX}:{model_id}"

    def _build_model_list_cache_key(self, user_id: str | None) -> str:
        """
        构建模型列表缓存键
        """
        scope_id = user_id or "anonymous"
        return f"{self.MODEL_LIST_CACHE_KEY_PREFIX}:{scope_id}"

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str | None:
        """
        规范化 Base URL
        """
        if not base_url:
            return None
        normalized_value = base_url.strip().rstrip("/")
        return normalized_value or None

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """
        脱敏展示 API Key
        """
        normalized_value = api_key.strip()
        if len(normalized_value) <= 10:
            return "*" * len(normalized_value)
        return f"{normalized_value[:6]}...{normalized_value[-4:]}"

    @staticmethod
    def _ensure_scope_constraints(scope: str, owner_user_id: str | None, is_default: bool) -> tuple[str, str | None]:
        """
        校验作用域约束
        """
        normalized_scope = scope.strip().lower()
        if normalized_scope not in {"system", "user"}:
            raise errors.RequestError(msg="模型作用域仅支持 system 或 user")

        normalized_owner_user_id = (owner_user_id or "").strip() or None

        if normalized_scope == "system":
            normalized_owner_user_id = None

        if normalized_scope == "user" and not normalized_owner_user_id:
            raise errors.RequestError(msg="用户级模型必须提供 owner_user_id")

        if normalized_scope == "user" and is_default:
            raise errors.RequestError(msg="当前版本暂不支持设置用户级默认模型")

        return normalized_scope, normalized_owner_user_id

    @staticmethod
    def _build_public_item(config: MentorModelRuntimeConfig, *, is_default: bool) -> MentorModelPublicItem:
        """
        构建前端公开模型项
        """
        return MentorModelPublicItem(
            model_id=config.model_id,
            display_name=config.display_name,
            description=None,
            provider=config.provider,
            is_default=is_default,
        )

    def _build_fallback_runtime_config(self) -> MentorModelRuntimeConfig:
        """
        构建基于环境变量的兜底配置
        """
        fallback_model_id = settings.MENTOR_AGENT_MODEL
        return MentorModelRuntimeConfig(
            model_id=fallback_model_id,
            display_name=settings.MENTOR_AGENT_MODEL,
            provider=settings.MENTOR_AGENT_PROVIDER,
            model_name=settings.MENTOR_AGENT_MODEL,
            base_url=self._normalize_base_url(settings.MENTOR_AGENT_BASE_URL),
            api_key=settings.get_mentor_agent_api_key,
            supports_streaming=True,
            supports_structured_output=True,
            supports_tools=False,
            supports_thinking=False,
            source="fallback",
        )

    def _serialize_runtime_config(self, runtime_config: MentorModelRuntimeConfig) -> dict[str, Any]:
        """
        序列化运行时配置到缓存
        """
        return runtime_config.model_dump(mode="json")

    def _deserialize_runtime_config(self, raw_value: dict[str, Any]) -> MentorModelRuntimeConfig:
        """
        从缓存反序列化运行时配置
        """
        return MentorModelRuntimeConfig.model_validate(raw_value)

    async def _clear_model_cache(self, model_id: str) -> None:
        """
        删除单模型缓存
        """
        await self.redis_client.delete(self._build_model_cache_key(model_id))

    async def _clear_model_list_cache(self) -> None:
        """
        删除所有模型列表缓存
        """
        await self.redis_client.connect()
        keys_to_delete: list[str] = []
        async for cache_key in self.redis_client._client.scan_iter(
            match=f"{self.MODEL_LIST_CACHE_KEY_PREFIX}:*"
        ):
            keys_to_delete.append(cache_key)

        if keys_to_delete:
            await self.redis_client._client.delete(*keys_to_delete)

    async def _invalidate_caches(self, model_id: str) -> None:
        """
        统一失效模型相关缓存
        """
        await self._clear_model_cache(model_id)
        await self._clear_model_list_cache()

    async def _set_system_default(
        self,
        session: AsyncSession,
        *,
        target_model_id: str,
    ) -> None:
        """
        设置系统默认模型
        """
        result = await session.execute(
            select(MentorModelConfig).where(
                and_(
                    MentorModelConfig.scope == "system",
                    MentorModelConfig.is_default.is_(True),
                )
            )
        )
        existing_default = result.scalar_one_or_none()
        if existing_default and existing_default.model_id != target_model_id:
            existing_default.is_default = False
            existing_default.updated_at = beijing_now()

        target_result = await session.execute(
            select(MentorModelConfig).where(MentorModelConfig.model_id == target_model_id)
        )
        target_model = target_result.scalar_one_or_none()
        if target_model is None:
            raise errors.NotFoundError(msg="模型不存在")
        target_model.is_default = True
        target_model.updated_at = beijing_now()
        await session.flush()

    async def list_admin_models(self, session: AsyncSession) -> list[MentorModelAdminItem]:
        """
        获取管理员模型列表
        """
        result = await session.execute(
            select(MentorModelConfig).order_by(
                MentorModelConfig.is_default.desc(),
                MentorModelConfig.updated_at.desc(),
                MentorModelConfig.created_at.desc(),
            )
        )
        records = list(result.scalars().all())
        items: list[MentorModelAdminItem] = []
        for record in records:
            decrypted_api_key = decrypt_secret(record.api_key_encrypted)
            items.append(
                MentorModelAdminItem(
                    model_id=record.model_id,
                    display_name=record.display_name,
                    description=record.description,
                    provider=record.provider,
                    model_name=record.model_name,
                    base_url=record.base_url,
                    api_key_masked=self._mask_api_key(decrypted_api_key),
                    is_active=record.is_active,
                    is_visible=record.is_visible,
                    is_default=record.is_default,
                    supports_streaming=record.supports_streaming,
                    supports_structured_output=record.supports_structured_output,
                    supports_tools=record.supports_tools,
                    supports_thinking=record.supports_thinking,
                    scope=record.scope,
                    owner_user_id=record.owner_user_id,
                    test_status=record.test_status,
                    last_tested_at=record.last_tested_at,
                    last_test_error=record.last_test_error,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        return items

    async def create_model(
        self,
        session: AsyncSession,
        request: MentorModelCreateRequest,
    ) -> MentorModelConfig:
        """
        创建 Mentor 模型配置
        """
        scope, owner_user_id = self._ensure_scope_constraints(
            request.scope,
            request.owner_user_id,
            request.is_default,
        )
        created_at = beijing_now()
        record = MentorModelConfig(
            display_name=request.display_name.strip(),
            description=(request.description or "").strip() or None,
            provider=request.provider.strip().lower(),
            model_name=request.model_name.strip(),
            base_url=self._normalize_base_url(request.base_url) or request.base_url.strip(),
            api_key_encrypted=encrypt_secret(request.api_key),
            is_active=request.is_active,
            is_visible=request.is_visible,
            is_default=request.is_default,
            supports_streaming=request.supports_streaming,
            supports_structured_output=request.supports_structured_output,
            supports_tools=request.supports_tools,
            supports_thinking=request.supports_thinking,
            scope=scope,
            owner_user_id=owner_user_id,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(record)
        await session.flush()

        if record.is_default:
            await self._set_system_default(session, target_model_id=record.model_id)

        await self._invalidate_caches(record.model_id)
        return record

    async def update_model(
        self,
        session: AsyncSession,
        *,
        model_id: str,
        request: MentorModelUpdateRequest,
    ) -> MentorModelConfig:
        """
        更新 Mentor 模型配置
        """
        result = await session.execute(
            select(MentorModelConfig).where(MentorModelConfig.model_id == model_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise errors.NotFoundError(msg="模型不存在")

        update_data = request.model_dump(exclude_unset=True)
        next_scope = update_data.get("scope", record.scope)
        next_owner_user_id = update_data.get("owner_user_id", record.owner_user_id)
        next_is_default = update_data.get("is_default", record.is_default)
        scope, owner_user_id = self._ensure_scope_constraints(
            next_scope,
            next_owner_user_id,
            next_is_default,
        )

        if "display_name" in update_data:
            record.display_name = update_data["display_name"].strip()
        if "description" in update_data:
            record.description = (update_data["description"] or "").strip() or None
        if "provider" in update_data:
            record.provider = update_data["provider"].strip().lower()
        if "model_name" in update_data:
            record.model_name = update_data["model_name"].strip()
        if "base_url" in update_data:
            record.base_url = self._normalize_base_url(update_data["base_url"]) or update_data["base_url"].strip()
        if "api_key" in update_data and update_data["api_key"] is not None:
            record.api_key_encrypted = encrypt_secret(update_data["api_key"])
        if "is_active" in update_data:
            record.is_active = update_data["is_active"]
        if "is_visible" in update_data:
            record.is_visible = update_data["is_visible"]
        if "supports_streaming" in update_data:
            record.supports_streaming = update_data["supports_streaming"]
        if "supports_structured_output" in update_data:
            record.supports_structured_output = update_data["supports_structured_output"]
        if "supports_tools" in update_data:
            record.supports_tools = update_data["supports_tools"]
        if "supports_thinking" in update_data:
            record.supports_thinking = update_data["supports_thinking"]

        record.scope = scope
        record.owner_user_id = owner_user_id
        record.is_default = next_is_default
        record.updated_at = beijing_now()
        await session.flush()

        if record.is_default:
            await self._set_system_default(session, target_model_id=record.model_id)

        await self._invalidate_caches(record.model_id)
        return record

    async def delete_model(
        self,
        session: AsyncSession,
        *,
        model_id: str,
    ) -> MentorModelConfig:
        """
        删除 Mentor 模型配置
        """
        result = await session.execute(
            select(MentorModelConfig).where(MentorModelConfig.model_id == model_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise errors.NotFoundError(msg="模型不存在")

        await session.delete(record)
        await session.flush()
        await self._invalidate_caches(model_id)
        return record

    async def _fetch_accessible_records(
        self,
        session: AsyncSession,
        *,
        user_id: str | None,
        only_visible: bool,
        only_active: bool,
    ) -> list[MentorModelConfig]:
        """
        查询当前用户可访问的模型记录
        """
        conditions: list[Any] = [
            or_(
                MentorModelConfig.scope == "system",
                and_(
                    MentorModelConfig.scope == "user",
                    MentorModelConfig.owner_user_id == user_id,
                ),
            )
        ]
        if only_visible:
            conditions.append(MentorModelConfig.is_visible.is_(True))
        if only_active:
            conditions.append(MentorModelConfig.is_active.is_(True))

        result = await session.execute(
            select(MentorModelConfig)
            .where(and_(*conditions))
            .order_by(
                MentorModelConfig.is_default.desc(),
                MentorModelConfig.updated_at.desc(),
                MentorModelConfig.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_available_models(
        self,
        session: AsyncSession,
        *,
        user_id: str | None,
    ) -> tuple[list[MentorModelPublicItem], str | None]:
        """
        获取 Mentor 前端可用模型列表
        """
        cache_key = self._build_model_list_cache_key(user_id)
        cached_value = await self.redis_client.get_json(cache_key)
        if isinstance(cached_value, dict):
            cached_items = [
                MentorModelPublicItem.model_validate(item)
                for item in cached_value.get("items", [])
            ]
            return cached_items, cached_value.get("default_model_id")

        records = await self._fetch_accessible_records(
            session,
            user_id=user_id,
            only_visible=True,
            only_active=True,
        )
        if not records:
            fallback_config = self._build_fallback_runtime_config()
            fallback_item = self._build_public_item(
                fallback_config,
                is_default=True,
            )
            result_items = [fallback_item]
            default_model_id = fallback_item.model_id
        else:
            result_items = [
                MentorModelPublicItem(
                    model_id=record.model_id,
                    display_name=record.display_name,
                    description=record.description,
                    provider=record.provider,
                    is_default=record.is_default,
                )
                for record in records
            ]
            default_model_id = next(
                (item.model_id for item in result_items if item.is_default),
                result_items[0].model_id if result_items else None,
            )

        await self.redis_client.set_json(
            cache_key,
            {
                "items": [item.model_dump(mode="json") for item in result_items],
                "default_model_id": default_model_id,
            },
            ex=settings.MENTOR_MODEL_LIST_CACHE_TTL_SECONDS,
        )
        return result_items, default_model_id

    async def _build_runtime_config_from_record(
        self,
        record: MentorModelConfig,
    ) -> MentorModelRuntimeConfig:
        """
        将数据库记录转换为运行时配置
        """
        return MentorModelRuntimeConfig(
            model_id=record.model_id,
            display_name=record.display_name,
            provider=record.provider,
            model_name=record.model_name,
            base_url=self._normalize_base_url(record.base_url),
            api_key=decrypt_secret(record.api_key_encrypted),
            supports_streaming=record.supports_streaming,
            supports_structured_output=record.supports_structured_output,
            supports_tools=record.supports_tools,
            supports_thinking=record.supports_thinking,
            source="registry",
        )

    async def get_runtime_config(
        self,
        session: AsyncSession,
        *,
        model_id: str | None,
        user_id: str | None,
    ) -> MentorModelRuntimeConfig:
        """
        根据 model_id 获取 Mentor 运行时配置
        """
        normalized_model_id = (model_id or "").strip()
        if not normalized_model_id:
            logger.info("mentor_model_runtime_fallback_no_model_id")
            return self._build_fallback_runtime_config()

        cache_key = self._build_model_cache_key(normalized_model_id)
        cached_value = await self.redis_client.get_json(cache_key)
        if isinstance(cached_value, dict):
            return self._deserialize_runtime_config(cached_value)

        result = await session.execute(
            select(MentorModelConfig).where(
                and_(
                    MentorModelConfig.model_id == normalized_model_id,
                    MentorModelConfig.is_active.is_(True),
                    or_(
                        MentorModelConfig.scope == "system",
                        and_(
                            MentorModelConfig.scope == "user",
                            MentorModelConfig.owner_user_id == user_id,
                        ),
                    ),
                )
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            logger.warning(
                "mentor_model_runtime_fallback_missing_registry_item",
                model_id=normalized_model_id,
                user_id=user_id,
            )
            return self._build_fallback_runtime_config()

        runtime_config = await self._build_runtime_config_from_record(record)
        await self.redis_client.set_json(
            cache_key,
            self._serialize_runtime_config(runtime_config),
            ex=settings.MENTOR_MODEL_REGISTRY_CACHE_TTL_SECONDS,
        )
        return runtime_config

    async def _run_test_request(
        self,
        runtime_config: MentorModelRuntimeConfig,
    ) -> MentorModelTestResponse:
        """
        对模型执行连通性测试
        """
        tested_at = beijing_now()
        client = AsyncOpenAI(
            api_key=runtime_config.api_key,
            base_url=runtime_config.base_url,
        )

        basic_completion_ok = False
        streaming_ok = False
        structured_output_ok = False
        error_message: str | None = None

        try:
            basic_request_kwargs = {
                "model": runtime_config.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with the single word OK.",
                    }
                ],
                "temperature": 0,
                "max_tokens": 8,
            }
            if runtime_config.supports_thinking:
                basic_request_kwargs["extra_body"] = {"enable_thinking": True}

            await client.chat.completions.create(
                **basic_request_kwargs,
            )
            basic_completion_ok = True

            if runtime_config.supports_streaming:
                stream_request_kwargs = {
                    "model": runtime_config.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Stream the single word OK.",
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 8,
                    "stream": True,
                }
                if runtime_config.supports_thinking:
                    stream_request_kwargs["extra_body"] = {"enable_thinking": True}

                stream = await client.chat.completions.create(**stream_request_kwargs)
                async for chunk in stream:
                    delta_text = ""
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        delta_text = delta.content or ""
                        if runtime_config.supports_thinking and getattr(delta, "reasoning_content", None):
                            streaming_ok = True
                            break
                    if delta_text:
                        streaming_ok = True
                        break
                if not streaming_ok:
                    streaming_ok = True
            else:
                streaming_ok = False

            if runtime_config.supports_structured_output:
                parsed_response = await client.beta.chat.completions.parse(
                    model=runtime_config.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": "Return a JSON object with ok=true and message='ok'.",
                        }
                    ],
                    temperature=0,
                    max_tokens=32,
                    response_format=_StructuredOutputProbe,
                )
                structured_output_ok = bool(parsed_response.choices[0].message.parsed)
            else:
                structured_output_ok = False
        except Exception as exc:
            error_message = str(exc)
            logger.warning(
                "mentor_model_test_failed",
                model_id=runtime_config.model_id,
                provider=runtime_config.provider,
                model_name=runtime_config.model_name,
                base_url=runtime_config.base_url,
                error=error_message,
            )

        success = basic_completion_ok
        if runtime_config.supports_streaming:
            success = success and streaming_ok
        if runtime_config.supports_structured_output:
            success = success and structured_output_ok

        return MentorModelTestResponse(
            success=success,
            provider=runtime_config.provider,
            model_name=runtime_config.model_name,
            base_url=runtime_config.base_url or "",
            basic_completion_ok=basic_completion_ok,
            streaming_ok=streaming_ok,
            structured_output_ok=structured_output_ok,
            test_status="passed" if success else "failed",
            error_message=error_message,
            tested_at=tested_at,
        )

    async def test_draft_model(
        self,
        request: MentorModelDraftTestRequest,
    ) -> MentorModelTestResponse:
        """
        测试未保存的模型草稿配置
        """
        runtime_config = MentorModelRuntimeConfig(
            model_id=request.model_name.strip(),
            display_name=request.model_name.strip(),
            provider=request.provider.strip().lower(),
            model_name=request.model_name.strip(),
            base_url=self._normalize_base_url(request.base_url),
            api_key=request.api_key.strip(),
            supports_streaming=request.supports_streaming,
            supports_structured_output=request.supports_structured_output,
            supports_tools=False,
            supports_thinking=request.supports_thinking,
            source="fallback",
        )
        return await self._run_test_request(runtime_config)

    async def test_registered_model(
        self,
        session: AsyncSession,
        *,
        model_id: str,
    ) -> MentorModelTestResponse:
        """
        测试已注册模型，并回写测试状态
        """
        result = await session.execute(
            select(MentorModelConfig).where(MentorModelConfig.model_id == model_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise errors.NotFoundError(msg="模型不存在")

        runtime_config = await self._build_runtime_config_from_record(record)
        test_result = await self._run_test_request(runtime_config)
        record.test_status = test_result.test_status
        record.last_tested_at = test_result.tested_at
        record.last_test_error = test_result.error_message
        record.updated_at = beijing_now()
        await session.flush()
        await self._invalidate_caches(record.model_id)
        return test_result


_mentor_model_registry_service: MentorModelRegistryService | None = None


def get_mentor_model_registry_service() -> MentorModelRegistryService:
    """
    获取 Mentor 模型注册表服务单例
    """
    global _mentor_model_registry_service
    if _mentor_model_registry_service is None:
        _mentor_model_registry_service = MentorModelRegistryService()
    return _mentor_model_registry_service

