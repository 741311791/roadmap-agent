"""
产品路书公开页 CRUD 操作
"""
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import (
    PlanningItem,
    PlanningVote,
    RoadmapFeature,
    RoadmapMilestone,
)


class PlanningItemCreate(BaseModel):
    """待规划需求创建 Schema"""
    title: str
    description: str | None = None
    submitter_email: str | None = None


class PlanningItemUpdate(BaseModel):
    """待规划需求更新 Schema"""
    title: str | None = None
    description: str | None = None
    submitter_email: str | None = None
    vote_count: int | None = None
    status: str | None = None


class RoadmapPublicCRUD(
    BaseCRUD[PlanningItem, PlanningItemCreate, PlanningItemUpdate]
):
    """
    产品路书公开页 CRUD
    """

    async def get_all_milestones(
        self,
        session: AsyncSession,
    ) -> list[RoadmapMilestone]:
        """
        查询所有里程碑
        """
        result = await session.execute(
            select(RoadmapMilestone).order_by(RoadmapMilestone.sort_order.asc(), RoadmapMilestone.id.asc())
        )
        return list(result.scalars().all())

    async def get_features_by_milestone_ids(
        self,
        session: AsyncSession,
        milestone_ids: list[int],
    ) -> list[RoadmapFeature]:
        """
        根据里程碑 ID 列表查询功能卡片
        """
        if not milestone_ids:
            return []

        result = await session.execute(
            select(RoadmapFeature)
            .where(RoadmapFeature.milestone_id.in_(milestone_ids))
            .order_by(RoadmapFeature.sort_order.asc(), RoadmapFeature.id.asc())
        )
        return list(result.scalars().all())

    async def get_upcoming_features(
        self,
        session: AsyncSession,
    ) -> list[RoadmapFeature]:
        """
        查询尚未开始的规划中功能
        """
        result = await session.execute(
            select(RoadmapFeature)
            .where(RoadmapFeature.status == "planned")
            .where(RoadmapFeature.milestone_id.is_(None))
            .order_by(RoadmapFeature.sort_order.asc(), RoadmapFeature.id.asc())
        )
        return list(result.scalars().all())

    async def get_planning_item_by_id(
        self,
        session: AsyncSession,
        item_id: int,
    ) -> Optional[PlanningItem]:
        """
        根据 ID 查询待规划需求
        """
        result = await session.execute(
            select(PlanningItem).where(PlanningItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_planning_items(
        self,
        session: AsyncSession,
        *,
        limit: int | None = None,
    ) -> list[PlanningItem]:
        """
        查询待规划需求列表
        """
        stmt = (
            select(PlanningItem)
            .where(PlanningItem.status == "open")
            .order_by(desc(PlanningItem.vote_count), PlanningItem.created_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_planning_item(
        self,
        session: AsyncSession,
        *,
        title: str,
        description: str | None = None,
        submitter_email: str | None = None,
    ) -> PlanningItem:
        """
        创建待规划需求
        """
        return await self.create(
            session,
            obj_in=PlanningItemCreate(
                title=title,
                description=description,
                submitter_email=submitter_email,
            ),
        )

    async def upsert_vote(
        self,
        session: AsyncSession,
        *,
        item_id: int,
        fingerprint: str,
    ) -> tuple[PlanningItem | None, bool]:
        """
        写入投票记录并在首次投票时递增票数

        Returns:
            (需求对象, 是否已投过票)
        """
        item = await self.get_planning_item_by_id(session, item_id)
        if item is None:
            return None, False

        try:
            async with session.begin_nested():
                vote = PlanningVote(
                    planning_item_id=item_id,
                    voter_fingerprint=fingerprint,
                )
                session.add(vote)
                await session.flush()
        except IntegrityError:
            refreshed_item = await self.get_planning_item_by_id(session, item_id)
            return refreshed_item, True

        item.vote_count += 1
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item, False


roadmap_public_crud = RoadmapPublicCRUD(PlanningItem)


def get_roadmap_public_crud() -> RoadmapPublicCRUD:
    """
    获取产品路书公开页 CRUD 单例
    """
    return roadmap_public_crud
