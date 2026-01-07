"""
学习笔记 CRUD 操作

纯数据访问层，遵循企业级架构规范
"""
from typing import List, Optional
from sqlalchemy import select, desc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import LearningNote
from app.schemas.mentor import LearningNoteCreate, LearningNoteUpdate

logger = structlog.get_logger()


class NoteCRUD(BaseCRUD[LearningNote, LearningNoteCreate, LearningNoteUpdate]):
    """学习笔记 CRUD 操作"""
    
    async def get_by_id(
        self,
        session: AsyncSession,
        note_id: str
    ) -> Optional[LearningNote]:
        """
        根据笔记ID获取笔记
        
        Args:
            session: 数据库会话
            note_id: 笔记ID
            
        Returns:
            LearningNote 或 None
        """
        stmt = select(LearningNote).where(LearningNote.note_id == note_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_concept(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[LearningNote]:
        """
        获取指定概念的所有笔记
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表（按更新时间倒序）
        """
        stmt = (
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id,
                LearningNote.concept_id == concept_id
            )
            .order_by(desc(LearningNote.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_roadmap(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[LearningNote]:
        """
        获取指定路线图的所有笔记
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表（按更新时间倒序）
        """
        stmt = (
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id
            )
            .order_by(desc(LearningNote.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_note(
        self,
        session: AsyncSession,
        note_id: str,
        update_data: LearningNoteUpdate
    ) -> Optional[LearningNote]:
        """
        更新学习笔记
        
        Args:
            session: 数据库会话
            note_id: 笔记ID
            update_data: 更新数据
            
        Returns:
            更新后的 LearningNote
        """
        note = await self.get_by_id(session, note_id)
        if not note:
            return None
        
        # 只更新提供的字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(note, field, value)
        
        from app.models.database import beijing_now
        note.updated_at = beijing_now()
        
        await session.flush()
        return note


# 单例实例
note_crud = NoteCRUD(LearningNote)
