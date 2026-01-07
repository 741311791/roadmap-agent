"""
测验CRUD操作
"""
from typing import Optional, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import QuizMetadata
from app.schemas.quiz import QuizCreate, QuizUpdate

logger = structlog.get_logger()

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
    
    async def save_quiz(
        self,
        session: AsyncSession,
        quiz_output: "QuizGenerationOutput",
        roadmap_id: str,
    ) -> QuizMetadata:
        """
        保存测验元数据（幂等操作）
        
        Args:
            session: 数据库会话
            quiz_output: 测验生成输出
            roadmap_id: 路线图ID
            
        Returns:
            保存的元数据记录
        """
        # 统计难度分布
        easy_count = sum(1 for q in quiz_output.questions if q.difficulty == "easy")
        medium_count = sum(1 for q in quiz_output.questions if q.difficulty == "medium")
        hard_count = sum(1 for q in quiz_output.questions if q.difficulty == "hard")
        
        # 先检查是否已存在（通过主键quiz_id）
        existing = await self.get(session, quiz_output.quiz_id)
        
        if existing:
            # 更新现有记录
            existing.questions = [q.model_dump() for q in quiz_output.questions]
            existing.total_questions = quiz_output.total_questions
            existing.easy_count = easy_count
            existing.medium_count = medium_count
            existing.hard_count = hard_count
            existing.generated_at = quiz_output.generated_at
            
            await session.flush()
            
            logger.info(
                "quiz_metadata_updated",
                quiz_id=quiz_output.quiz_id,
                concept_id=quiz_output.concept_id,
                roadmap_id=roadmap_id,
                total_questions=quiz_output.total_questions,
            )
            
            return existing
        
        # 删除该概念的旧测验（每个概念只保留一个测验）
        await session.execute(
            delete(QuizMetadata).where(
                QuizMetadata.roadmap_id == roadmap_id,
                QuizMetadata.concept_id == quiz_output.concept_id,
            )
        )
        
        # 创建新记录
        metadata = QuizMetadata(
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            roadmap_id=roadmap_id,
            questions=[q.model_dump() for q in quiz_output.questions],
            total_questions=quiz_output.total_questions,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count,
            generated_at=quiz_output.generated_at,
        )
        
        session.add(metadata)
        await session.flush()
        
        logger.info(
            "quiz_metadata_created",
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            roadmap_id=roadmap_id,
            total_questions=quiz_output.total_questions,
        )
        
        return metadata
    
    async def save_quizzes_batch(
        self,
        session: AsyncSession,
        quiz_refs: dict[str, "QuizGenerationOutput"],
        roadmap_id: str,
    ) -> List[QuizMetadata]:
        """
        批量保存测验元数据
        
        Args:
            session: 数据库会话
            quiz_refs: 测验字典（concept_id -> QuizGenerationOutput）
            roadmap_id: 路线图ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        
        for concept_id, quiz_output in quiz_refs.items():
            metadata = await self.save_quiz(session, quiz_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "quizzes_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list

# 单例模式
_quiz_crud_instance: Optional[QuizCRUD] = None

def get_quiz_crud() -> QuizCRUD:
    """获取QuizCRUD单例"""
    global _quiz_crud_instance
    if _quiz_crud_instance is None:
        _quiz_crud_instance = QuizCRUD(QuizMetadata)
    return _quiz_crud_instance

