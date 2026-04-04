"""
Mentor 模型注册表相关 Schema
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MentorModelScope = Literal["system", "user"]
MentorModelTestStatus = Literal["untested", "passed", "failed"]


class MentorModelRuntimeConfig(BaseModel):
    """
    Mentor 模型运行时配置
    """

    model_id: str = Field(..., description="模型注册表 ID")
    display_name: str = Field(..., description="模型展示名称")
    provider: str = Field(..., description="提供商标识")
    model_name: str = Field(..., description="最终传给 OpenAI 兼容接口的模型名")
    base_url: str | None = Field(None, description="OpenAI 兼容网关地址")
    api_key: str | None = Field(None, description="运行时解密后的 API Key")
    supports_streaming: bool = Field(default=True, description="是否支持流式输出")
    supports_structured_output: bool = Field(default=True, description="是否支持结构化输出")
    supports_tools: bool = Field(default=False, description="是否支持工具调用")
    supports_thinking: bool = Field(default=False, description="是否支持深度思考流式输出")
    source: Literal["registry", "fallback"] = Field(
        default="registry",
        description="配置来源",
    )


class MentorModelBaseRequest(BaseModel):
    """
    Mentor 模型基础请求
    """

    display_name: str = Field(..., min_length=1, max_length=120, description="模型展示名称")
    description: str | None = Field(None, max_length=1000, description="模型说明")
    provider: str = Field(
        default="openai",
        min_length=1,
        max_length=64,
        description="提供商标识（主要用于观测与速率限制）",
    )
    model_name: str = Field(..., min_length=1, max_length=255, description="模型名称")
    base_url: str = Field(..., min_length=1, max_length=500, description="OpenAI 兼容网关地址")
    is_active: bool = Field(default=True, description="是否启用")
    is_visible: bool = Field(default=True, description="是否在 Mentor 前端可见")
    is_default: bool = Field(default=False, description="是否设为默认模型")
    supports_streaming: bool = Field(default=True, description="是否支持流式输出")
    supports_structured_output: bool = Field(default=True, description="是否支持结构化输出")
    supports_tools: bool = Field(default=False, description="是否支持工具调用")
    supports_thinking: bool = Field(default=False, description="是否支持深度思考流式输出")
    scope: MentorModelScope = Field(default="system", description="模型作用域")
    owner_user_id: str | None = Field(None, description="用户自定义模型所属用户 ID")


class MentorModelCreateRequest(MentorModelBaseRequest):
    """
    Mentor 模型创建请求
    """

    api_key: str = Field(..., min_length=1, description="API Key")


class MentorModelUpdateRequest(BaseModel):
    """
    Mentor 模型更新请求
    """

    display_name: str | None = Field(None, min_length=1, max_length=120, description="模型展示名称")
    description: str | None = Field(None, max_length=1000, description="模型说明")
    provider: str | None = Field(None, min_length=1, max_length=64, description="提供商标识")
    model_name: str | None = Field(None, min_length=1, max_length=255, description="模型名称")
    base_url: str | None = Field(None, min_length=1, max_length=500, description="OpenAI 兼容网关地址")
    api_key: str | None = Field(None, min_length=1, description="新的 API Key；为空则保留旧值")
    is_active: bool | None = Field(None, description="是否启用")
    is_visible: bool | None = Field(None, description="是否在 Mentor 前端可见")
    is_default: bool | None = Field(None, description="是否设为默认模型")
    supports_streaming: bool | None = Field(None, description="是否支持流式输出")
    supports_structured_output: bool | None = Field(None, description="是否支持结构化输出")
    supports_tools: bool | None = Field(None, description="是否支持工具调用")
    supports_thinking: bool | None = Field(None, description="是否支持深度思考流式输出")
    scope: MentorModelScope | None = Field(None, description="模型作用域")
    owner_user_id: str | None = Field(None, description="用户自定义模型所属用户 ID")


class MentorModelDraftTestRequest(BaseModel):
    """
    Mentor 模型草稿测试请求
    """

    provider: str = Field(
        default="openai",
        min_length=1,
        max_length=64,
        description="提供商标识（主要用于观测与速率限制）",
    )
    model_name: str = Field(..., min_length=1, max_length=255, description="模型名称")
    base_url: str = Field(..., min_length=1, max_length=500, description="OpenAI 兼容网关地址")
    api_key: str = Field(..., min_length=1, description="API Key")
    supports_streaming: bool = Field(default=True, description="是否验证流式能力")
    supports_structured_output: bool = Field(default=True, description="是否验证结构化输出能力")
    supports_thinking: bool = Field(default=False, description="是否验证深度思考能力")


class MentorModelAdminItem(BaseModel):
    """
    管理员模型列表项
    """

    model_id: str = Field(..., description="模型注册表 ID")
    display_name: str = Field(..., description="模型展示名称")
    description: str | None = Field(None, description="模型说明")
    provider: str = Field(..., description="提供商标识")
    model_name: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="OpenAI 兼容网关地址")
    api_key_masked: str = Field(..., description="脱敏后的 API Key")
    is_active: bool = Field(..., description="是否启用")
    is_visible: bool = Field(..., description="是否在 Mentor 前端可见")
    is_default: bool = Field(..., description="是否默认")
    supports_streaming: bool = Field(..., description="是否支持流式输出")
    supports_structured_output: bool = Field(..., description="是否支持结构化输出")
    supports_tools: bool = Field(..., description="是否支持工具调用")
    supports_thinking: bool = Field(..., description="是否支持深度思考流式输出")
    scope: MentorModelScope = Field(..., description="模型作用域")
    owner_user_id: str | None = Field(None, description="用户自定义模型所属用户 ID")
    test_status: MentorModelTestStatus = Field(..., description="测试状态")
    last_tested_at: datetime | None = Field(None, description="最后测试时间")
    last_test_error: str | None = Field(None, description="最近一次测试错误")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class MentorModelAdminListResponse(BaseModel):
    """
    管理员模型列表响应
    """

    items: list[MentorModelAdminItem] = Field(default_factory=list, description="模型列表")
    total: int = Field(..., description="总数")


class MentorModelPublicItem(BaseModel):
    """
    Mentor 前端可选模型项
    """

    model_id: str = Field(..., description="模型注册表 ID")
    display_name: str = Field(..., description="模型展示名称")
    description: str | None = Field(None, description="模型说明")
    provider: str = Field(..., description="提供商标识")
    is_default: bool = Field(default=False, description="是否默认模型")
    supports_thinking: bool = Field(default=False, description="是否支持深度思考")
    supports_reasoning_effort: bool = Field(default=False, description="是否支持推理深度控制")


class MentorModelPublicListResponse(BaseModel):
    """
    Mentor 前端模型列表响应
    """

    items: list[MentorModelPublicItem] = Field(default_factory=list, description="模型列表")
    default_model_id: str | None = Field(None, description="默认模型 ID")


class MentorModelDeleteResponse(BaseModel):
    """
    Mentor 模型删除响应
    """

    model_id: str = Field(..., description="被删除的模型 ID")


class MentorModelTestResponse(BaseModel):
    """
    Mentor 模型测试响应
    """

    success: bool = Field(..., description="测试是否成功")
    provider: str = Field(..., description="提供商标识")
    model_name: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="OpenAI 兼容网关地址")
    basic_completion_ok: bool = Field(..., description="基础请求是否成功")
    streaming_ok: bool = Field(..., description="流式请求是否成功")
    structured_output_ok: bool = Field(..., description="结构化请求是否成功")
    test_status: MentorModelTestStatus = Field(..., description="最终测试状态")
    error_message: str | None = Field(None, description="错误信息")
    tested_at: datetime = Field(..., description="测试时间")

