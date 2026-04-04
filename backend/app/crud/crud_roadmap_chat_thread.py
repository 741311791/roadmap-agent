"""
Deer-Flow 路线图聊天线程 CRUD
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import RoadmapChatThread, beijing_now


class RoadmapChatThreadCreate(BaseModel):
    """
    路线图聊天线程创建 Schema
    """


class RoadmapChatThreadUpdate(BaseModel):
    """
    路线图聊天线程更新 Schema
    """


class RoadmapChatThreadCRUD(
    BaseCRUD[RoadmapChatThread, RoadmapChatThreadCreate, RoadmapChatThreadUpdate]
):
    """
    Deer-Flow 路线图聊天线程数据访问层。
    """

    async def get_by_thread_id(
        self,
        session: AsyncSession,
        *,
        thread_id: str,
    ) -> RoadmapChatThread | None:
        """
        根据线程 ID 获取映射记录。

        Args:
            session: 数据库会话。
            thread_id: 线程 ID。

        Returns:
            映射记录或 None。

        Raises:
            None
        """

        stmt = select(RoadmapChatThread).where(RoadmapChatThread.thread_id == thread_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_threads(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str | None = None,
        scope: str | None = None,
        concept_id: str | None = None,
        standalone_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RoadmapChatThread]:
        """
        查询用户线程列表。

        Args:
            session: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID；与 standalone_only 互斥。
            scope: 查询作用域。
            concept_id: 概念 ID。
            standalone_only: 为 True 时仅返回独立 DeerFlow 线程（roadmap_id 与 concept_id 均为空）。
            limit: 分页大小。
            offset: 分页偏移。

        Returns:
            线程列表。

        Raises:
            None
        """

        stmt = select(RoadmapChatThread).where(RoadmapChatThread.user_id == user_id)

        if standalone_only:
            stmt = stmt.where(RoadmapChatThread.roadmap_id.is_(None)).where(
                RoadmapChatThread.concept_id.is_(None)
            )
        else:
            if roadmap_id is not None:
                stmt = stmt.where(RoadmapChatThread.roadmap_id == roadmap_id)
            else:
                # 伴学列表未指定路线图时，排除独立实验室线程，避免混入
                stmt = stmt.where(RoadmapChatThread.roadmap_id.is_not(None))

            if scope == "roadmap":
                stmt = stmt.where(RoadmapChatThread.concept_id.is_(None))
            elif scope == "concept":
                stmt = stmt.where(RoadmapChatThread.concept_id == concept_id)

        stmt = stmt.order_by(desc(RoadmapChatThread.updated_at)).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_threads(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str | None = None,
        scope: str | None = None,
        concept_id: str | None = None,
        standalone_only: bool = False,
    ) -> int:
        """
        统计用户线程数量。

        Args:
            session: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            scope: 查询作用域。
            concept_id: 概念 ID。
            standalone_only: 为 True 时仅统计独立 DeerFlow 线程。

        Returns:
            线程总数。

        Raises:
            None
        """

        stmt = select(func.count()).select_from(RoadmapChatThread).where(RoadmapChatThread.user_id == user_id)
        if standalone_only:
            stmt = stmt.where(RoadmapChatThread.roadmap_id.is_(None)).where(
                RoadmapChatThread.concept_id.is_(None)
            )
        else:
            if roadmap_id is not None:
                stmt = stmt.where(RoadmapChatThread.roadmap_id == roadmap_id)
            else:
                stmt = stmt.where(RoadmapChatThread.roadmap_id.is_not(None))
            if scope == "roadmap":
                stmt = stmt.where(RoadmapChatThread.concept_id.is_(None))
            elif scope == "concept":
                stmt = stmt.where(RoadmapChatThread.concept_id == concept_id)

        result = await session.execute(stmt)
        return result.scalar() or 0

    async def create_thread(
        self,
        session: AsyncSession,
        *,
        thread_id: str,
        user_id: str,
        roadmap_id: str | None = None,
        stage_id: str | None = None,
        task_id: str | None = None,
        concept_id: str | None = None,
        title: str | None = None,
        assistant_id: str | None = None,
        model_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> RoadmapChatThread:
        """
        创建 Deer-Flow 线程映射。

        Args:
            session: 数据库会话。
            thread_id: 线程 ID。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            stage_id: 阶段 ID。
            task_id: 任务 ID。
            concept_id: 概念 ID。
            title: 线程标题。
            assistant_id: assistant ID。
            model_id: 模型 ID。
            metadata_json: 扩展元数据。

        Returns:
            新建线程记录。

        Raises:
            None
        """

        return await self.create(
            session,
            obj_in={
                "thread_id": thread_id,
                "user_id": user_id,
                "roadmap_id": roadmap_id,
                "stage_id": stage_id,
                "task_id": task_id,
                "concept_id": concept_id,
                "title": title,
                "assistant_id": assistant_id,
                "model_id": model_id,
                "metadata_json": metadata_json,
            },
        )

    async def update_thread_state(
        self,
        session: AsyncSession,
        *,
        thread_id: str,
        title: str | None = None,
        assistant_id: str | None = None,
        model_id: str | None = None,
        message_count: int | None = None,
        last_message_preview: str | None = None,
        last_message_at: datetime | None = None,
        metadata_json: dict | None = None,
    ) -> RoadmapChatThread | None:
        """
        更新线程同步状态。

        Args:
            session: 数据库会话。
            thread_id: 线程 ID。
            title: 线程标题。
            assistant_id: assistant ID。
            model_id: 模型 ID。
            message_count: 消息数量。
            last_message_preview: 最后一条消息预览。
            last_message_at: 最后消息时间。
            metadata_json: 扩展元数据。

        Returns:
            更新后的线程记录；不存在时返回 None。

        Raises:
            None
        """

        thread = await self.get_by_thread_id(session, thread_id=thread_id)
        if thread is None:
            return None

        if title is not None:
            thread.title = title
        if assistant_id is not None:
            thread.assistant_id = assistant_id
        if model_id is not None:
            thread.model_id = model_id
        if message_count is not None:
            thread.message_count = message_count
        if last_message_preview is not None:
            thread.last_message_preview = last_message_preview
        if last_message_at is not None:
            thread.last_message_at = last_message_at
        if metadata_json is not None:
            thread.metadata_json = metadata_json

        thread.updated_at = beijing_now()
        session.add(thread)
        await session.flush()
        await session.refresh(thread)
        return thread

    async def delete_thread(
        self,
        session: AsyncSession,
        *,
        thread_id: str,
    ) -> RoadmapChatThread | None:
        """
        删除线程映射。

        Args:
            session: 数据库会话。
            thread_id: 线程 ID。

        Returns:
            被删除的线程记录；不存在时返回 None。

        Raises:
            None
        """

        thread = await self.get_by_thread_id(session, thread_id=thread_id)
        if thread is None:
            return None

        await session.execute(delete(RoadmapChatThread).where(RoadmapChatThread.thread_id == thread_id))
        await session.flush()
        return thread


roadmap_chat_thread_crud = RoadmapChatThreadCRUD(RoadmapChatThread)


def get_roadmap_chat_thread_crud() -> RoadmapChatThreadCRUD:
    """
    获取 Deer-Flow 路线图聊天线程 CRUD 单例。

    Args:
        None

    Returns:
        RoadmapChatThreadCRUD 实例。

    Raises:
        None
    """

    return roadmap_chat_thread_crud
