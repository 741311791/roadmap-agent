"""
学习进度数据访问层

负责 Concept 学习进度和 Quiz 答题记录的数据库操作。
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional, List
from app.models.database import ConceptProgress, QuizAttempt, beijing_now
import uuid


class ProgressRepository:
    """学习进度数据访问层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ============================================================
    # Concept Progress 相关方法
    # ============================================================
    
    async def get_concept_progress(
        self, 
        user_id: str, 
        roadmap_id: str, 
        concept_id: str
    ) -> Optional[ConceptProgress]:
        """获取单个Concept进度"""
        statement = select(ConceptProgress).where(
            ConceptProgress.user_id == user_id,
            ConceptProgress.roadmap_id == roadmap_id,
            ConceptProgress.concept_id == concept_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_roadmap_progress(
        self, 
        user_id: str, 
        roadmap_id: str
    ) -> List[ConceptProgress]:
        """获取某个路线图的所有Concept进度"""
        statement = select(ConceptProgress).where(
            ConceptProgress.user_id == user_id,
            ConceptProgress.roadmap_id == roadmap_id
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def upsert_concept_progress(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        is_completed: bool
    ) -> ConceptProgress:
        """更新或创建Concept进度"""
        existing = await self.get_concept_progress(user_id, roadmap_id, concept_id)
        
        if existing:
            # 更新现有记录
            existing.is_completed = is_completed
            existing.completed_at = beijing_now() if is_completed else None
            existing.updated_at = beijing_now()
            self.session.add(existing)
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
            self.session.add(existing)
        
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
    
    # ============================================================
    # Quiz Attempt 相关方法
    # ============================================================
    
    async def create_quiz_attempt(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        quiz_id: str,
        total_questions: int,
        correct_answers: int,
        score_percentage: float,
        incorrect_question_indices: List[int]
    ) -> QuizAttempt:
        """记录Quiz答题"""
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
        self.session.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)
        return attempt
    
    async def get_quiz_attempts(
        self,
        user_id: str,
        concept_id: str
    ) -> List[QuizAttempt]:
        """获取某个Concept的所有Quiz记录"""
        statement = select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.concept_id == concept_id
        ).order_by(QuizAttempt.attempted_at.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())




