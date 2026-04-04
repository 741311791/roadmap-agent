"""
用户反馈 API 端点。
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.v1.deps import CurrentActiveUser, CurrentSessionTransaction
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.feedback import (
    FeedbackCategory,
    FeedbackContextType,
    UserFeedbackCreatePayload,
    UserFeedbackSubmitResponse,
)
from app.services.shared.linear_feedback_service import get_linear_feedback_service

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()


@router.post("/feedback", response_model=ResponseSchemaModel[UserFeedbackSubmitResponse])
async def submit_user_feedback(
    db: CurrentSessionTransaction,
    current_user: CurrentActiveUser,
    rating: Annotated[int, Form(ge=1, le=5, description="评分，范围 1-5")],
    category: Annotated[FeedbackCategory, Form(description="反馈分类")],
    summary: Annotated[str, Form(min_length=1, max_length=200, description="反馈摘要")],
    details: Annotated[str, Form(min_length=1, max_length=5000, description="详细反馈或复现步骤")],
    page_url: Annotated[str, Form(min_length=1, max_length=2000, description="页面 URL")],
    context_type: Annotated[FeedbackContextType, Form(description="触发场景")],
    roadmap_id: Annotated[str | None, Form(max_length=255)] = None,
    concept_id: Annotated[str | None, Form(max_length=255)] = None,
    task_id: Annotated[str | None, Form(max_length=255)] = None,
    screenshot_file: Annotated[UploadFile | None, File(description="截图文件")] = None,
) -> ResponseSchemaModel[UserFeedbackSubmitResponse]:
    """
    提交产品反馈到 Linear。

    Args:
        db: 事务数据库会话。
        current_user: 当前活跃用户。
        rating: 用户评分。
        category: 反馈分类。
        summary: 反馈标题。
        details: 反馈详情或复现步骤。
        page_url: 当前页面 URL。
        context_type: 触发场景。
        roadmap_id: 路线图 ID。
        concept_id: Concept ID。
        task_id: 任务 ID。
        screenshot_file: 截图文件。

    Returns:
        提交成功后的反馈结果。

    Raises:
        HTTPException: 当参数非法、配置缺失或 Linear 提交失败时抛出。
    """

    payload = UserFeedbackCreatePayload(
        rating=rating,
        category=category,
        summary=summary.strip(),
        details=details.strip(),
        page_url=page_url.strip(),
        context_type=context_type,
        roadmap_id=roadmap_id.strip() if roadmap_id else None,
        concept_id=concept_id.strip() if concept_id else None,
        task_id=task_id.strip() if task_id else None,
    )

    logger.info(
        "submit_user_feedback_requested",
        user_id=current_user.id,
        category=payload.category.value,
        context_type=payload.context_type.value,
        has_screenshot=bool(screenshot_file and screenshot_file.filename),
    )

    feedback_service = get_linear_feedback_service()
    try:
        result = await feedback_service.submit_feedback(
            db,
            user=current_user,
            payload=payload,
            screenshot_file=screenshot_file,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "submit_user_feedback_failed",
            user_id=current_user.id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交反馈失败，请稍后重试。",
        ) from exc

    return response_base.success(data=result)
