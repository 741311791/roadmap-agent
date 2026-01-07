"""
测验CRUD操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import BaseCRUD
from app.models.database import QuizMetadata
from app.schemas.quiz import QuizCreate, QuizUpdate

class QuizCRUD(BaseCRUD[QuizMetadata, QuizCreate, QuizUpdate]):
    """
    测验CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_quiz_id(
        self,
        session: AsyncSession,
        quiz_id: str,
    ) -> Optional[QuizMetadata]:
        """
        根据quiz_id获取测验
        
        Args:
            session: 数据库会话
            quiz_id: 测验ID
            
        Returns:
            测验元数据或None
        """
        result = await session.execute(
            select(QuizMetadata).where(
                QuizMetadata.quiz_id == quiz_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_concept(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[QuizMetadata]:
        """
        获取概念的测验
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            测验元数据或None
        """
        result = await session.execute(
            select(QuizMetadata)
            .where(QuizMetadata.roadmap_id == roadmap_id)
            .where(QuizMetadata.concept_id == concept_id)
            .where(QuizMetadata.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

# 工厂函数
def get_quiz_crud() -> QuizCRUD:
    """获取QuizCRUD实例"""
    return QuizCRUD(QuizMetadata)

