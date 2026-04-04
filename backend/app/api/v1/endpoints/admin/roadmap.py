"""
产品路书管理 API
"""
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSessionTransaction
from app.core.auth.deps import current_superuser
from app.core.response_schema import ResponseSchemaModel, response_base
from app.models.database import User
from app.models.domain import RoadmapSyncResponse
from app.services.roadmap.linear_sync_service import (
    LinearSyncService,
    get_linear_sync_service,
)

router = APIRouter(prefix="/roadmap", tags=["admin-roadmap"])
logger = structlog.get_logger()


@router.post("/sync", response_model=ResponseSchemaModel[RoadmapSyncResponse])
async def sync_public_roadmap(
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    service: LinearSyncService = Depends(get_linear_sync_service),
) -> ResponseSchemaModel[RoadmapSyncResponse]:
    """
    手动触发产品路书同步
    """
    result = await service.sync_all(db)
    logger.info(
        "admin_sync_public_roadmap",
        admin_id=current_user.id,
        milestone_count=result.milestone_count,
        feature_count=result.feature_count,
        upcoming_feature_count=result.upcoming_feature_count,
    )
    return response_base.success(data=result)
