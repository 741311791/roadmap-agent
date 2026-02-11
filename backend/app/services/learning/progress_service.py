"""
学习进度服务
"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_progress import ProgressCRUD
from app.models.database import ConceptProgress, QuizAttempt


class ProgressService:
    """学习进度业务逻辑"""
    
    def __init__(self):
        self.progress_crud = ProgressCRUD(ConceptProgress)
    
    async def update_concept_progress(
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
        progress = await self.progress_crud.upsert_concept_progress(
            session=session,
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            is_completed=is_completed,
        )
        return progress
    
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
        progress_list = await self.progress_crud.get_roadmap_progress(
            session=session,
            user_id=user_id,
            roadmap_id=roadmap_id,
        )
        return progress_list
    
    async def submit_quiz_attempt(
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
        提交Quiz答题记录
        
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
        attempt = await self.progress_crud.create_quiz_attempt(
            session=session,
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            quiz_id=quiz_id,
            total_questions=total_questions,
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            incorrect_question_indices=incorrect_question_indices,
        )
        return attempt


def get_progress_service() -> ProgressService:
    """获取ProgressService实例"""
    return ProgressService()

