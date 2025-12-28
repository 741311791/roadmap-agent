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
    
    async def get_roadmaps_progress_batch(
        self,
        user_id: str,
        roadmap_ids: List[str],
    ) -> dict[str, List[ConceptProgress]]:
        """
        批量获取多个路线图的学习进度（解决 N+1 查询问题）
        
        单次查询获取所有路线图的进度，然后按 roadmap_id 分组返回。
        
        Args:
            user_id: 用户 ID
            roadmap_ids: 路线图 ID 列表
            
        Returns:
            字典，键为 roadmap_id，值为该路线图的进度列表
        """
        if not roadmap_ids:
            return {}
        
        statement = select(ConceptProgress).where(
            ConceptProgress.user_id == user_id,
            ConceptProgress.roadmap_id.in_(roadmap_ids)
        )
        result = await self.session.execute(statement)
        all_progress = list(result.scalars().all())
        
        # 按 roadmap_id 分组
        progress_by_roadmap: dict[str, List[ConceptProgress]] = {
            roadmap_id: [] for roadmap_id in roadmap_ids
        }
        for progress in all_progress:
            if progress.roadmap_id in progress_by_roadmap:
                progress_by_roadmap[progress.roadmap_id].append(progress)
        
        return progress_by_roadmap
    
    async def get_completed_counts_batch(
        self,
        user_id: str,
        roadmap_ids: List[str],
    ) -> dict[str, int]:
        """
        批量获取多个路线图的已完成概念数量（优化版）
        
        使用 COUNT + GROUP BY 直接在数据库中统计，避免加载大量数据到内存。
        
        Args:
            user_id: 用户 ID
            roadmap_ids: 路线图 ID 列表
            
        Returns:
            字典，键为 roadmap_id，值为已完成的概念数量
        """
        if not roadmap_ids:
            return {}
        
        from sqlalchemy import func
        
        statement = (
            select(
                ConceptProgress.roadmap_id,
                func.count(ConceptProgress.id).label("completed_count"),
            )
            .where(
                ConceptProgress.user_id == user_id,
                ConceptProgress.roadmap_id.in_(roadmap_ids),
                ConceptProgress.is_completed == True,
            )
            .group_by(ConceptProgress.roadmap_id)
        )
        result = await self.session.execute(statement)
        rows = result.fetchall()
        
        # 初始化所有路线图的计数为 0
        counts = {roadmap_id: 0 for roadmap_id in roadmap_ids}
        for row in rows:
            counts[row[0]] = row[1]
        
        return counts
    
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







