"""
学习笔记 Repository

负责 LearningNote 表的数据访问操作。

职责范围：
- 笔记的 CRUD 操作
- 按概念/路线图查询笔记
- 标签搜索
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.database import LearningNote, beijing_now
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class NoteRepository(BaseRepository[LearningNote]):
    """
    学习笔记数据访问层
    
    管理用户的学习笔记记录。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, LearningNote)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_note(self, note_id: str) -> Optional[LearningNote]:
        """
        根据 note_id 查询笔记
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            笔记记录，如果不存在则返回 None
        """
        return await self.get_by_id(note_id)
    
    async def get_notes_by_concept(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LearningNote]:
        """
        查询用户在指定概念下的所有笔记
        
        按更新时间倒序排列（最新的在前）。
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表
        """
        result = await self.session.execute(
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id,
                LearningNote.concept_id == concept_id,
            )
            .order_by(LearningNote.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        notes = list(result.scalars().all())
        
        logger.debug(
            "concept_notes_listed",
            user_id=user_id,
            concept_id=concept_id,
            count=len(notes),
        )
        
        return notes
    
    async def get_notes_by_roadmap(
        self,
        user_id: str,
        roadmap_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LearningNote]:
        """
        查询用户在指定路线图下的所有笔记
        
        按更新时间倒序排列（最新的在前）。
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表
        """
        result = await self.session.execute(
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id,
            )
            .order_by(LearningNote.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        notes = list(result.scalars().all())
        
        logger.debug(
            "roadmap_notes_listed",
            user_id=user_id,
            roadmap_id=roadmap_id,
            count=len(notes),
        )
        
        return notes
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def create_note(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        content: str,
        title: Optional[str] = None,
        source: str = "manual",
        tags: Optional[List[str]] = None,
    ) -> LearningNote:
        """
        创建新的学习笔记
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            content: 笔记内容
            title: 笔记标题（可选）
            source: 笔记来源 (manual/ai_generated/chat_extracted)
            tags: 标签列表
            
        Returns:
            创建的笔记记录
        """
        note = LearningNote(
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content=content,
            title=title,
            source=source,
            tags=tags or [],
        )
        
        created = await self.create(note)
        
        logger.info(
            "learning_note_created",
            note_id=created.note_id,
            user_id=user_id,
            concept_id=concept_id,
            source=source,
            content_length=len(content),
        )
        
        return created
    
    async def update_note(
        self,
        note_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        更新笔记内容
        
        Args:
            note_id: 笔记 ID
            content: 笔记内容
            title: 笔记标题
            tags: 标签列表
            
        Returns:
            是否更新成功
        """
        update_fields = {"updated_at": beijing_now()}
        
        if content is not None:
            update_fields["content"] = content
        if title is not None:
            update_fields["title"] = title
        if tags is not None:
            update_fields["tags"] = tags
        
        success = await self.update_by_id(note_id, **update_fields)
        
        if success:
            logger.info(
                "learning_note_updated",
                note_id=note_id,
                updated_fields=list(update_fields.keys()),
            )
        
        return success
    
    async def delete_note(self, note_id: str) -> bool:
        """
        删除笔记
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            是否删除成功
        """
        success = await self.delete_by_id(note_id)
        
        if success:
            logger.info("learning_note_deleted", note_id=note_id)
        
        return success
    
    # ============================================================
    # 统计方法
    # ============================================================
    
    async def count_notes_by_concept(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        统计用户在指定概念下的笔记数量
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            笔记数量
        """
        result = await self.session.execute(
            select(func.count(LearningNote.note_id))
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id,
                LearningNote.concept_id == concept_id,
            )
        )
        
        return result.scalar_one()
    
    async def count_notes_by_roadmap(
        self,
        user_id: str,
        roadmap_id: str,
    ) -> int:
        """
        统计用户在指定路线图下的笔记数量
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            
        Returns:
            笔记数量
        """
        result = await self.session.execute(
            select(func.count(LearningNote.note_id))
            .where(
                LearningNote.user_id == user_id,
                LearningNote.roadmap_id == roadmap_id,
            )
        )
        
        return result.scalar_one()
