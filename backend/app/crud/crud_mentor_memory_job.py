"""
AI 伴学助手记忆任务 CRUD 操作
"""
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import MentorMemoryJob, beijing_now


class MentorMemoryJobCreate(BaseModel):
    """AI 伴学助手记忆任务创建 Schema"""


class MentorMemoryJobUpdate(BaseModel):
    """AI 伴学助手记忆任务更新 Schema"""


class MentorMemoryJobCRUD(
    BaseCRUD[MentorMemoryJob, MentorMemoryJobCreate, MentorMemoryJobUpdate]
):
    """
    AI 伴学助手记忆任务 CRUD
    """

    async def get_by_job_id(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> Optional[MentorMemoryJob]:
        """
        根据任务 ID 查询任务
        """
        result = await session.execute(
            select(MentorMemoryJob).where(MentorMemoryJob.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_message_id(
        self,
        session: AsyncSession,
        message_id: str,
    ) -> Optional[MentorMemoryJob]:
        """
        根据消息 ID 查询任务
        """
        result = await session.execute(
            select(MentorMemoryJob).where(MentorMemoryJob.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_failed_jobs(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
    ) -> list[MentorMemoryJob]:
        """
        查询失败或死信任务
        """
        result = await session.execute(
            select(MentorMemoryJob)
            .where(MentorMemoryJob.status.in_(["failed", "dead_letter"]))
            .order_by(desc(MentorMemoryJob.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_job(
        self,
        session: AsyncSession,
        *,
        job_id: str | None = None,
        message_id: str,
        user_id: str,
        session_id: str,
        payload: dict,
        celery_task_id: str | None = None,
    ) -> MentorMemoryJob:
        """
        创建记忆任务记录
        """
        existing = await self.get_by_message_id(session, message_id)
        if existing is not None:
            return existing

        obj_in = {
            "message_id": message_id,
            "user_id": user_id,
            "session_id": session_id,
            "payload": payload,
            "celery_task_id": celery_task_id,
            "status": "pending",
        }
        if job_id is not None:
            obj_in["job_id"] = job_id

        return await self.create(
            session,
            obj_in=obj_in,
        )

    async def mark_processing(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        celery_task_id: str | None = None,
        retry_count: int | None = None,
    ) -> Optional[MentorMemoryJob]:
        """
        标记任务为处理中
        """
        job = await self.get_by_job_id(session, job_id)
        if not job:
            return None

        job.status = "processing"
        job.started_at = beijing_now()
        job.updated_at = beijing_now()
        if celery_task_id is not None:
            job.celery_task_id = celery_task_id
        if retry_count is not None:
            job.retry_count = retry_count
        await session.flush()
        return job

    async def reset_for_replay(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        celery_task_id: str | None,
    ) -> Optional[MentorMemoryJob]:
        """
        为手动重放重置任务状态
        """
        job = await self.get_by_job_id(session, job_id)
        if not job:
            return None

        job.status = "pending"
        job.celery_task_id = celery_task_id
        job.last_error = None
        job.started_at = None
        job.finished_at = None
        job.updated_at = beijing_now()
        await session.flush()
        return job

    async def mark_succeeded(
        self,
        session: AsyncSession,
        *,
        job_id: str,
    ) -> Optional[MentorMemoryJob]:
        """
        标记任务为成功
        """
        job = await self.get_by_job_id(session, job_id)
        if not job:
            return None

        job.status = "succeeded"
        job.finished_at = beijing_now()
        job.updated_at = beijing_now()
        job.last_error = None
        await session.flush()
        return job

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        last_error: str,
        retry_count: int,
        dead_letter: bool = False,
    ) -> Optional[MentorMemoryJob]:
        """
        标记任务为失败或死信
        """
        job = await self.get_by_job_id(session, job_id)
        if not job:
            return None

        job.status = "dead_letter" if dead_letter else "failed"
        job.last_error = last_error
        job.retry_count = retry_count
        job.finished_at = beijing_now()
        job.updated_at = beijing_now()
        await session.flush()
        return job


mentor_memory_job_crud = MentorMemoryJobCRUD(MentorMemoryJob)


def get_mentor_memory_job_crud() -> MentorMemoryJobCRUD:
    """
    获取 AI 伴学助手记忆任务 CRUD 单例
    """
    return mentor_memory_job_crud
