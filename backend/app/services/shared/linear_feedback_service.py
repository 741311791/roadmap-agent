"""
Linear 用户反馈服务。
"""
from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.crud.crud_user_feedback import UserFeedbackCRUD, get_user_feedback_crud
from app.models.database import User
from app.schemas.feedback import (
    FeedbackCategory,
    UserFeedbackCreatePayload,
    UserFeedbackSubmitResponse,
)

logger = structlog.get_logger()

LINEAR_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
MAX_SCREENSHOT_SIZE_BYTES = 10 * 1024 * 1024
# UUID v4 格式正则，用于校验 Linear 资源 ID
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
ALLOWED_SCREENSHOT_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


class LinearFeedbackService:
    """
    负责把产品内反馈同步到 Linear。

    同时在本地库中持久化反馈记录，便于后续分析、排障与补偿。
    """

    def __init__(
        self,
        user_feedback_crud: UserFeedbackCRUD | None = None,
    ) -> None:
        """
        初始化服务。

        Args:
            user_feedback_crud: 用户反馈 CRUD 实例。

        Returns:
            None

        Raises:
            None
        """

        self._user_feedback_crud = user_feedback_crud or get_user_feedback_crud()

    async def submit_feedback(
        self,
        session: AsyncSession,
        *,
        user: User,
        payload: UserFeedbackCreatePayload,
        screenshot_file: UploadFile | None = None,
    ) -> UserFeedbackSubmitResponse:
        """
        提交用户反馈到 Linear，并回写本地状态。

        Args:
            session: 数据库会话。
            user: 当前登录用户。
            payload: 反馈载荷。
            screenshot_file: 可选截图文件。

        Returns:
            提交成功后的反馈结果。

        Raises:
            ValueError: 当配置、文件类型或参数不合法时抛出。
            RuntimeError: 当 Linear API 调用失败时抛出。
        """

        self._ensure_linear_config()

        feedback = await self._user_feedback_crud.create_feedback(
            session,
            user_id=user.id,
            username_snapshot=user.username,
            email_snapshot=user.email,
            category=payload.category.value,
            rating=payload.rating,
            summary=payload.summary,
            details=payload.details,
            page_url=payload.page_url,
            context_type=payload.context_type.value,
            roadmap_id=payload.roadmap_id,
            concept_id=payload.concept_id,
            task_id=payload.task_id,
            screenshot_filename=screenshot_file.filename if screenshot_file else None,
        )

        screenshot_asset_url: str | None = None

        try:
            if screenshot_file is not None:
                screenshot_asset_url = await self._upload_screenshot_to_linear(screenshot_file)

            issue_data = await self._create_linear_issue(
                payload=payload,
                user=user,
                screenshot_asset_url=screenshot_asset_url,
            )

            if payload.page_url:
                await self._create_page_attachment(
                    issue_id=issue_data["id"],
                    page_url=payload.page_url,
                    payload=payload,
                )

            issue_url = self._build_issue_url(issue_data["identifier"])
            await self._user_feedback_crud.mark_submitted(
                session,
                feedback=feedback,
                linear_issue_id=issue_data["id"],
                linear_issue_identifier=issue_data["identifier"],
                linear_issue_url=issue_url,
                screenshot_asset_url=screenshot_asset_url,
            )

            logger.info(
                "user_feedback_submitted_to_linear",
                feedback_id=feedback.feedback_id,
                linear_issue_id=issue_data["id"],
                category=payload.category.value,
            )

            return UserFeedbackSubmitResponse(
                feedback_id=feedback.feedback_id,
                linear_issue_id=issue_data["id"],
                linear_issue_identifier=issue_data["identifier"],
                linear_issue_url=issue_url,
            )
        except Exception as exc:
            await self._user_feedback_crud.mark_failed(
                session,
                feedback=feedback,
                error_message=str(exc),
                screenshot_asset_url=screenshot_asset_url,
            )
            raise

    def _ensure_linear_config(self) -> None:
        """
        校验 Linear 所需配置是否完整。

        Args:
            None

        Returns:
            None

        Raises:
            ValueError: 当关键配置缺失时抛出。
        """

        required_fields = {
            "LINEAR_API_KEY": settings.LINEAR_API_KEY,
            "LINEAR_TEAM_ID": settings.LINEAR_TEAM_ID,
        }
        missing_fields = [field_name for field_name, field_value in required_fields.items() if not field_value]
        if missing_fields:
            raise ValueError(f"Linear 反馈配置缺失：{', '.join(missing_fields)}")

    async def _upload_screenshot_to_linear(self, screenshot_file: UploadFile) -> str:
        """
        上传截图到 Linear 私有存储。

        Args:
            screenshot_file: 用户上传的截图文件。

        Returns:
            Linear 托管后的资源地址。

        Raises:
            ValueError: 当文件不满足要求时抛出。
            RuntimeError: 当上传流程失败时抛出。
        """

        content_type = screenshot_file.content_type or ""
        if content_type not in ALLOWED_SCREENSHOT_CONTENT_TYPES:
            raise ValueError("仅支持 PNG、JPEG、WEBP 或 GIF 截图。")

        file_bytes = await screenshot_file.read()
        if not file_bytes:
            raise ValueError("截图文件不能为空。")
        if len(file_bytes) > MAX_SCREENSHOT_SIZE_BYTES:
            raise ValueError("截图大小不能超过 10MB。")

        upload_data = await self._request_linear_file_upload(
            content_type=content_type,
            filename=screenshot_file.filename or "feedback-screenshot",
            size=len(file_bytes),
        )
        await self._put_file_to_linear_storage(
            upload_url=upload_data["uploadUrl"],
            headers=upload_data["headers"],
            content_type=content_type,
            file_bytes=file_bytes,
        )
        return upload_data["assetUrl"]

    async def _request_linear_file_upload(
        self,
        *,
        content_type: str,
        filename: str,
        size: int,
    ) -> dict[str, Any]:
        """
        请求 Linear 生成预签名上传地址。

        Args:
            content_type: 文件 MIME 类型。
            filename: 文件名。
            size: 文件大小。

        Returns:
            上传地址和响应头信息。

        Raises:
            RuntimeError: 当 Linear 返回失败时抛出。
        """

        query = """
        mutation RequestFileUpload($contentType: String!, $filename: String!, $size: Int!) {
          fileUpload(contentType: $contentType, filename: $filename, size: $size) {
            success
            uploadFile {
              uploadUrl
              assetUrl
              headers {
                key
                value
              }
            }
          }
        }
        """
        data = await self._execute_graphql(
            query=query,
            variables={
                "contentType": content_type,
                "filename": filename,
                "size": size,
            },
        )
        result = data["fileUpload"]
        if not result["success"] or not result["uploadFile"]:
            raise RuntimeError("Linear 未返回有效的文件上传地址。")
        return result["uploadFile"]

    async def _put_file_to_linear_storage(
        self,
        *,
        upload_url: str,
        headers: list[dict[str, str]],
        content_type: str,
        file_bytes: bytes,
    ) -> None:
        """
        把文件内容上传到 Linear 私有存储。

        Args:
            upload_url: 预签名上传地址。
            headers: Linear 要求透传的请求头。
            content_type: 文件 MIME 类型。
            file_bytes: 文件二进制内容。

        Returns:
            None

        Raises:
            RuntimeError: 当上传失败时抛出。
        """

        upload_headers = {
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=31536000",
        }
        for item in headers:
            upload_headers[item["key"]] = item["value"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                upload_url,
                headers=upload_headers,
                content=file_bytes,
            )
            response.raise_for_status()

    async def _create_linear_issue(
        self,
        *,
        payload: UserFeedbackCreatePayload,
        user: User,
        screenshot_asset_url: str | None,
    ) -> dict[str, str]:
        """
        创建 Linear Issue。

        Args:
            payload: 用户反馈载荷。
            user: 当前用户。
            screenshot_asset_url: 截图资源地址。

        Returns:
            包含 Issue 主键和短标识的字典。

        Raises:
            RuntimeError: 当创建 Issue 失败时抛出。
        """

        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
            }
          }
        }
        """
        label_ids = self._build_label_ids(payload.category)
        issue_input: dict[str, Any] = {
            "teamId": settings.LINEAR_TEAM_ID,
            "title": self._build_issue_title(payload.category, payload.summary),
            "description": self._build_issue_description(
                payload=payload,
                user=user,
                screenshot_asset_url=screenshot_asset_url,
            ),
        }
        # 仅在有合法标签 UUID 时才传入，避免空列表或非 UUID 字符串触发 Linear 校验失败
        if label_ids:
            issue_input["labelIds"] = label_ids

        # Project 在 Linear 中是可选归属；只有配置时才显式传入。
        if settings.LINEAR_PROJECT_ID:
            issue_input["projectId"] = settings.LINEAR_PROJECT_ID

        data = await self._execute_graphql(
            query=query,
            variables={
                "input": issue_input,
            },
        )

        issue_create = data["issueCreate"]
        if not issue_create["success"] or not issue_create["issue"]:
            raise RuntimeError("Linear Issue 创建失败。")
        return issue_create["issue"]

    async def _create_page_attachment(
        self,
        *,
        issue_id: str,
        page_url: str,
        payload: UserFeedbackCreatePayload,
    ) -> None:
        """
        把当前页面链接作为 attachment 追加到 Linear Issue。

        Args:
            issue_id: Linear Issue UUID。
            page_url: 页面 URL。
            payload: 用户反馈载荷。

        Returns:
            None

        Raises:
            RuntimeError: 当 attachment 创建失败时抛出。
        """

        query = """
        mutation CreateAttachment($input: AttachmentCreateInput!) {
          attachmentCreate(input: $input) {
            success
            attachment {
              id
            }
          }
        }
        """
        data = await self._execute_graphql(
            query=query,
            variables={
                "input": {
                    "issueId": issue_id,
                    "title": "Source Page",
                    "subtitle": payload.context_type.value,
                    "url": page_url,
                    "metadata": {
                        "contextType": payload.context_type.value,
                        "roadmapId": payload.roadmap_id or "",
                        "conceptId": payload.concept_id or "",
                        "taskId": payload.task_id or "",
                    },
                }
            },
        )
        result = data["attachmentCreate"]
        if not result["success"]:
            raise RuntimeError("Linear 页面 attachment 创建失败。")

    async def _execute_graphql(
        self,
        *,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """
        执行一次 Linear GraphQL 请求。

        Args:
            query: GraphQL 查询或变更语句。
            variables: GraphQL 变量。

        Returns:
            GraphQL `data` 字段。

        Raises:
            RuntimeError: 当 GraphQL 返回错误时抛出。
        """

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LINEAR_GRAPHQL_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": settings.LINEAR_API_KEY or "",
                },
                json={
                    "query": query,
                    "variables": variables,
                },
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("errors"):
            first_error = payload["errors"][0]
            error_message = first_error.get("message", "Linear GraphQL 请求失败。")
            raise RuntimeError(error_message)
        data = payload.get("data")
        if not data:
            raise RuntimeError("Linear GraphQL 未返回 data 字段。")
        return data

    def _build_label_ids(self, category: FeedbackCategory) -> list[str]:
        """
        构建 Issue 标签 ID 列表。

        仅将通过 UUID 格式校验的 ID 放入列表，非 UUID 字符串（如未配置时的
        名称字符串）会被静默跳过，不阻断 Issue 创建流程。

        Args:
            category: 反馈分类。

        Returns:
            通过校验的标签 UUID 列表，可能为空。

        Raises:
            None
        """

        category_label_map = {
            FeedbackCategory.BUG: settings.LINEAR_LABEL_BUG,
            FeedbackCategory.IMPROVEMENT: settings.LINEAR_LABEL_IMPROVEMENT,
            FeedbackCategory.QUESTION: settings.LINEAR_LABEL_QUESTION,
            FeedbackCategory.NEW_FEATURE: settings.LINEAR_LABEL_NEW_FEATURE,
        }
        candidates = [
            settings.LINEAR_LABEL_USER_FEEDBACK,
            category_label_map.get(category),
        ]
        # 仅保留格式合法的 UUID，防止把名称字符串传给 Linear 造成校验失败
        return [lid for lid in candidates if lid and _UUID_PATTERN.match(lid)]

    def _build_issue_title(self, category: FeedbackCategory, summary: str) -> str:
        """
        构建 Linear Issue 标题。

        Args:
            category: 反馈分类。
            summary: 用户输入的摘要。

        Returns:
            格式化后的 Issue 标题。

        Raises:
            None
        """

        category_label = {
            FeedbackCategory.BUG: "Bug",
            FeedbackCategory.IMPROVEMENT: "Improvement",
            FeedbackCategory.QUESTION: "Question",
            FeedbackCategory.NEW_FEATURE: "New Feature",
        }[category]
        return f"[User Feedback][{category_label}] {summary}"

    def _build_issue_description(
        self,
        *,
        payload: UserFeedbackCreatePayload,
        user: User,
        screenshot_asset_url: str | None,
    ) -> str:
        """
        生成 Linear Issue 描述。

        Args:
            payload: 用户反馈载荷。
            user: 当前用户。
            screenshot_asset_url: 截图资源地址。

        Returns:
            Markdown 格式的描述文本。

        Raises:
            None
        """

        context_lines = [
            f"- Trigger: `{payload.context_type.value}`",
            f"- Page URL: {payload.page_url}",
            f"- Username: `{user.username}`",
            f"- User ID: `{user.id}`",
            f"- Email: `{user.email}`",
        ]
        if payload.roadmap_id:
            context_lines.append(f"- Roadmap ID: `{payload.roadmap_id}`")
        if payload.concept_id:
            context_lines.append(f"- Concept ID: `{payload.concept_id}`")
        if payload.task_id:
            context_lines.append(f"- Task ID: `{payload.task_id}`")

        sections = [
            "## Rating",
            f"{payload.rating}/5",
            "",
            "## Category",
            payload.category.value,
            "",
            "## User Context",
            *context_lines,
            "",
            "## Reproduction Steps / Feedback Details",
            payload.details,
        ]

        if screenshot_asset_url:
            sections.extend(
                [
                    "",
                    "## Screenshot",
                    f"![feedback-screenshot]({screenshot_asset_url})",
                ]
            )

        return "\n".join(sections)

    def _build_issue_url(self, issue_identifier: str) -> str | None:
        """
        根据配置拼装 Linear Issue URL。

        Args:
            issue_identifier: Issue 短标识。

        Returns:
            可访问的 Issue URL；若未配置工作区地址则返回 None。

        Raises:
            None
        """

        if not settings.LINEAR_WORKSPACE_URL:
            return None
        return f"{settings.LINEAR_WORKSPACE_URL.rstrip('/')}/issue/{issue_identifier}"


_linear_feedback_service_instance: LinearFeedbackService | None = None


def get_linear_feedback_service() -> LinearFeedbackService:
    """
    获取 LinearFeedbackService 单例。

    Args:
        None

    Returns:
        LinearFeedbackService 实例。

    Raises:
        None
    """

    global _linear_feedback_service_instance
    if _linear_feedback_service_instance is None:
        _linear_feedback_service_instance = LinearFeedbackService()
    return _linear_feedback_service_instance
