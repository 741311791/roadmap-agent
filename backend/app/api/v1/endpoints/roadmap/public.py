"""
产品路书公开数据查询 API
"""
from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentSession
from app.core.response_schema import ResponseSchemaModel, response_base
from app.crud.crud_roadmap_public import RoadmapPublicCRUD, get_roadmap_public_crud
from app.models.domain import (
    PublicRoadmapDataResponse,
    PublicRoadmapFeature,
    PublicRoadmapMilestone,
)

router = APIRouter(prefix="/roadmap", tags=["roadmap-public"])


def _build_feature_response(feature) -> PublicRoadmapFeature:
    """
    将功能 ORM 转换为公开响应模型
    """
    labels = feature.labels if isinstance(feature.labels, list) else []
    normalized_labels = [str(label) for label in labels]
    return PublicRoadmapFeature(
        id=feature.id,
        linear_id=feature.linear_id,
        milestone_id=feature.milestone_id,
        title=feature.title,
        description=feature.description,
        status=feature.status,
        demo_url=feature.demo_url,
        labels=normalized_labels,
        linear_url=feature.linear_url,
        sort_order=feature.sort_order,
    )


@router.get("/milestones", response_model=ResponseSchemaModel[PublicRoadmapDataResponse])
async def list_public_roadmap_data(
    db: CurrentSession,
    crud: RoadmapPublicCRUD = Depends(get_roadmap_public_crud),
) -> ResponseSchemaModel[PublicRoadmapDataResponse]:
    """
    获取公开产品路书时间轴数据
    """
    milestones = await crud.get_all_milestones(db)
    milestone_ids = [milestone.id for milestone in milestones if milestone.id is not None]
    feature_records = await crud.get_features_by_milestone_ids(db, milestone_ids)
    upcoming_features = await crud.get_upcoming_features(db)

    milestone_feature_map: dict[int, list[PublicRoadmapFeature]] = {}
    for feature in feature_records:
        if feature.milestone_id is None:
            continue
        milestone_feature_map.setdefault(feature.milestone_id, []).append(
            _build_feature_response(feature)
        )

    items = [
        PublicRoadmapMilestone(
            id=milestone.id,
            linear_id=milestone.linear_id,
            title=milestone.title,
            description=milestone.description,
            status=milestone.status,
            start_date=milestone.start_date,
            end_date=milestone.end_date,
            sort_order=milestone.sort_order,
            features=milestone_feature_map.get(milestone.id, []),
        )
        for milestone in milestones
        if milestone.id is not None
    ]

    response = PublicRoadmapDataResponse(
        milestones=items,
        upcoming_features=[_build_feature_response(feature) for feature in upcoming_features],
    )
    return response_base.success(data=response)
