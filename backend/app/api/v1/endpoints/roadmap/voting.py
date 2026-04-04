"""
产品路书投票与想法提交 API
"""
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.core.response_schema import ResponseSchemaModel, response_base
from app.crud.crud_roadmap_public import RoadmapPublicCRUD, get_roadmap_public_crud
from app.models.domain import (
    PlanningItemCreateRequest,
    PlanningItemVoteResponse,
    PublicPlanningItem,
    PublicPlanningItemListResponse,
)

router = APIRouter(prefix="/roadmap", tags=["roadmap-public"])


def _build_planning_item_response(item) -> PublicPlanningItem:
    """
    将待规划需求 ORM 转换为公开响应模型
    """
    return PublicPlanningItem(
        id=item.id,
        title=item.title,
        description=item.description,
        vote_count=item.vote_count,
        status=item.status,
        created_at=item.created_at,
    )


def _build_vote_fingerprint(request: Request) -> str:
    """
    生成访客投票指纹
    """
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    raw_fingerprint = f"{client_host}|{user_agent}"
    return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()


@router.get("/planning-items", response_model=ResponseSchemaModel[PublicPlanningItemListResponse])
async def list_planning_items(
    db: CurrentSession,
    crud: RoadmapPublicCRUD = Depends(get_roadmap_public_crud),
) -> ResponseSchemaModel[PublicPlanningItemListResponse]:
    """
    获取待规划需求投票榜单
    """
    items = await crud.get_planning_items(db)
    response = PublicPlanningItemListResponse(
        items=[_build_planning_item_response(item) for item in items],
        total=len(items),
    )
    return response_base.success(data=response)


@router.post("/planning-items", response_model=ResponseSchemaModel[PublicPlanningItem])
async def create_planning_item(
    request_body: PlanningItemCreateRequest,
    db: CurrentSessionTransaction,
    crud: RoadmapPublicCRUD = Depends(get_roadmap_public_crud),
) -> ResponseSchemaModel[PublicPlanningItem]:
    """
    提交新的待规划需求
    """
    item = await crud.create_planning_item(
        db,
        title=request_body.title,
        description=request_body.description,
        submitter_email=request_body.submitter_email,
    )
    return response_base.success(data=_build_planning_item_response(item))


@router.post("/planning-items/{item_id}/vote", response_model=ResponseSchemaModel[PlanningItemVoteResponse])
async def vote_planning_item(
    item_id: int,
    request: Request,
    db: CurrentSessionTransaction,
    crud: RoadmapPublicCRUD = Depends(get_roadmap_public_crud),
) -> ResponseSchemaModel[PlanningItemVoteResponse]:
    """
    为待规划需求投票
    """
    fingerprint = _build_vote_fingerprint(request)
    item, already_voted = await crud.upsert_vote(
        db,
        item_id=item_id,
        fingerprint=fingerprint,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planning item not found",
        )

    if already_voted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted for this planning item",
        )

    return response_base.success(
        data=PlanningItemVoteResponse(
            item_id=item.id,
            vote_count=item.vote_count,
            already_voted=False,
        )
    )
