"""
进度CRUD操作
"""
import uuid
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import ConceptProgress, QuizAttempt, beijing_now
from pydantic import BaseModel, Field


class ProgressCreate(BaseModel):
    """进度创建Schema"""
    user_id: str
    concept_id: str
    roadmap_id: str
    is_completed: bool = False


class ProgressUpdate(BaseModel):
    """进度更新Schema"""
    is_completed: Optional[bool] = None
    completed_at: Optional[str] = None


class ProgressCRUD(BaseCRUD[ConceptProgress, ProgressCreate, ProgressUpdate]):
    """
    学习进度CRUD操作
    
    继承BaseCRUD，扩展进度相关的特定方法
    """
    
    async def get_concept_progress(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[ConceptProgress]:
        """
        获取单个Concept进度
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            概念进度或None
        """
        result = await session.execute(
            select(ConceptProgress).where(
                ConceptProgress.user_id == user_id,
                ConceptProgress.roadmap_id == roadmap_id,
                ConceptProgress.concept_id == concept_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_roadmap_progress(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
    ) -> List[ConceptProgress]:
        """
        获取某个路线图的所有Concept进度
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            
        Returns:
            概念进度列表
        """
        result = await session.execute(
            select(ConceptProgress).where(
                ConceptProgress.user_id == user_id,
                ConceptProgress.roadmap_id == roadmap_id
            )
        )
        return list(result.scalars().all())
    
    async def upsert_concept_progress(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        is_completed: bool,
    ) -> ConceptProgress:
        """
        更新或创建Concept进度
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            is_completed: 是否完成
            
        Returns:
            概念进度
        """
        existing = await self.get_concept_progress(session, user_id, roadmap_id, concept_id)
        
        if existing:
            # 更新现有记录
            existing.is_completed = is_completed
            existing.completed_at = beijing_now() if is_completed else None
            existing.updated_at = beijing_now()
            session.add(existing)
        else:
            # 创建新记录
            existing = ConceptProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                is_completed=is_completed,
                completed_at=beijing_now() if is_completed else None
            )
            session.add(existing)
        
        await session.flush()
        await session.refresh(existing)
        return existing
    
    async def create_quiz_attempt(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        quiz_id: str,
        total_questions: int,
        correct_answers: int,
        score_percentage: float,
        incorrect_question_indices: List[int],
    ) -> QuizAttempt:
        """
        记录Quiz答题
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            quiz_id: 测验ID
            total_questions: 总题数
            correct_answers: 正确答案数
            score_percentage: 得分百分比
            incorrect_question_indices: 错误题目索引
            
        Returns:
            答题记录
        """
        attempt = QuizAttempt(
            id=str(uuid.uuid4()),
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            quiz_id=quiz_id,
            total_questions=total_questions,
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            incorrect_question_indices=incorrect_question_indices
        )
        session.add(attempt)
        await session.flush()
        await session.refresh(attempt)
        return attempt
    
    async def get_quiz_attempts(
        self,
        session: AsyncSession,
        user_id: str,
        concept_id: str,
    ) -> List[QuizAttempt]:
        """
        获取某个Concept的所有Quiz记录
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            concept_id: 概念ID
            
        Returns:
            答题记录列表
        """
        result = await session.execute(
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.concept_id == concept_id
            )
            .order_by(QuizAttempt.attempted_at.desc())
        )
        return list(result.scalars().all())


def get_progress_crud() -> ProgressCRUD:
    """获取ProgressCRUD实例"""
    return ProgressCRUD(ConceptProgress)
