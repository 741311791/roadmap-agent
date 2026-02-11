"""
技术评估相关CRUD操作

提供技术栈评估和相关问题的数据库操作。

扩展了以下Repository方法：
- 评估查询（get_assessment, technology_exists等）
- 技术栈管理（get_available_technologies等）
- 批量操作（get_existing_combinations等）
"""
from typing import Optional, List, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, distinct, func
import structlog

from app.crud.base import BaseCRUD
from app.models.database import TechStackAssessment, UserProfile, beijing_now

logger = structlog.get_logger()


class TechAssessmentCRUD(BaseCRUD[TechStackAssessment, dict, dict]):
    """
    技术评估CRUD
    
    职责：
    - 技术栈评估的增删改查
    - 根据用户ID查询评估记录
    - 评估状态管理
    """
    
    async def get_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> List[TechStackAssessment]:
        """
        根据用户ID获取所有评估记录
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            
        Returns:
            评估记录列表
        """
        stmt = select(TechStackAssessment).where(
            TechStackAssessment.user_id == user_id
        ).order_by(TechStackAssessment.created_at.desc())
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_assessment_id(
        self,
        session: AsyncSession,
        assessment_id: str,
    ) -> Optional[TechStackAssessment]:
        """
        根据评估ID获取评估记录
        
        Args:
            session: 数据库会话
            assessment_id: 评估ID
            
        Returns:
            评估记录或None
        """
        stmt = select(TechStackAssessment).where(
            TechStackAssessment.assessment_id == assessment_id
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        session: AsyncSession,
        assessment_id: str,
        status: str,
        result_data: Optional[dict] = None,
    ) -> Optional[TechStackAssessment]:
        """
        更新评估状态
        
        Args:
            session: 数据库会话
            assessment_id: 评估ID
            status: 新状态
            result_data: 评估结果数据
            
        Returns:
            更新后的评估记录
        """
        assessment = await self.get_by_assessment_id(session, assessment_id)
        if not assessment:
            return None
        
        assessment.status = status
        if result_data:
            assessment.result = result_data
        
        session.add(assessment)
        await session.flush()
        await session.refresh(assessment)
        
        return assessment
    
    # ========== Week 4扩展方法 ==========
    
    async def get_assessment(
        self,
        session: AsyncSession,
        technology: str,
        proficiency_level: str,
    ) -> Optional[TechStackAssessment]:
        """
        获取指定技术栈和级别的测验题目
        
        Args:
            session: 数据库会话
            technology: 技术栈名称（python, react等）
            proficiency_level: 能力级别（beginner, intermediate, expert）
            
        Returns:
            测验记录或None
        """
        result = await session.execute(
            select(TechStackAssessment).where(
                and_(
                    TechStackAssessment.technology == technology,
                    TechStackAssessment.proficiency_level == proficiency_level,
                )
            )
        )
        
        assessment = result.scalar_one_or_none()
        
        if assessment:
            logger.debug(
                "tech_assessment_found",
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=assessment.total_questions,
            )
        else:
            logger.debug(
                "tech_assessment_not_found",
                technology=technology,
                proficiency_level=proficiency_level,
            )
        
        return assessment
    
    async def get_by_tech_and_level(
        self,
        session: AsyncSession,
        technology: str,
        proficiency_level: str,
    ) -> Optional[TechStackAssessment]:
        """
        根据技术栈和级别获取测验题目（get_assessment的别名方法）
        
        Args:
            session: 数据库会话
            technology: 技术栈名称（python, react等）
            proficiency_level: 能力级别（beginner, intermediate, expert）
            
        Returns:
            测验记录或None
        """
        return await self.get_assessment(session, technology, proficiency_level)
    
    async def assessment_exists(
        self,
        session: AsyncSession,
        technology: str,
        proficiency_level: str,
    ) -> bool:
        """
        检查测验是否已存在
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            proficiency_level: 能力级别
            
        Returns:
            是否存在
        """
        assessment = await self.get_assessment(session, technology, proficiency_level)
        return assessment is not None
    
    async def create_assessment(
        self,
        session: AsyncSession,
        assessment_id: str,
        technology: str,
        proficiency_level: str,
        questions: list,
        total_questions: int,
    ) -> TechStackAssessment:
        """
        创建新的测验记录（Upsert逻辑）
        
        如果(technology, proficiency_level)已存在则更新，否则创建
        
        Args:
            session: 数据库会话
            assessment_id: 评估ID
            technology: 技术栈名称
            proficiency_level: 能力级别
            questions: 题目列表
            total_questions: 题目总数
            
        Returns:
            测验记录
        """
        # 检查是否已存在
        existing = await self.get_assessment(session, technology, proficiency_level)
        
        if existing:
            # 更新现有记录
            existing.questions = questions
            existing.total_questions = total_questions
            existing.updated_at = beijing_now()
            
            session.add(existing)
            await session.flush()
            await session.refresh(existing)
            
            logger.info(
                "tech_assessment_updated",
                assessment_id=existing.assessment_id,
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=total_questions,
            )
            
            return existing
        else:
            # 创建新记录
            assessment = TechStackAssessment(
                assessment_id=assessment_id,
                technology=technology,
                proficiency_level=proficiency_level,
                questions=questions,
                total_questions=total_questions,
            )
            
            session.add(assessment)
            await session.flush()
            await session.refresh(assessment)
            
            logger.info(
                "tech_assessment_created",
                assessment_id=assessment_id,
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=total_questions,
            )
            
            return assessment
    
    async def technology_exists(
        self,
        session: AsyncSession,
        technology: str,
    ) -> bool:
        """
        检查某个技术栈是否已有题库（至少一个级别）
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            
        Returns:
            是否存在
        """
        result = await session.execute(
            select(TechStackAssessment.technology)
            .where(TechStackAssessment.technology == technology)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_available_technologies(
        self,
        session: AsyncSession,
    ) -> List[str]:
        """
        获取所有有测验题目的技术栈列表（去重）
        
        Args:
            session: 数据库会话
            
        Returns:
            技术栈名称列表（已排序）
        """
        result = await session.execute(
            select(distinct(TechStackAssessment.technology)).order_by(
                TechStackAssessment.technology
            )
        )
        
        technologies = [row[0] for row in result.all()]
        
        logger.debug(
            "available_technologies_retrieved",
            count=len(technologies),
            technologies=technologies,
        )
        
        return technologies
    
    async def get_existing_combinations(
        self,
        session: AsyncSession,
    ) -> Set[Tuple[str, str]]:
        """
        批量获取所有已存在的(technology, proficiency_level)组合
        
        用于启动时一次性检查哪些测验已存在，避免N+1查询
        
        Args:
            session: 数据库会话
            
        Returns:
            已存在的(technology, proficiency_level)元组集合
        """
        result = await session.execute(
            select(
                TechStackAssessment.technology,
                TechStackAssessment.proficiency_level,
            )
        )
        
        combinations = {(row[0], row[1]) for row in result.all()}
        
        logger.debug(
            "existing_combinations_retrieved",
            count=len(combinations),
        )
        
        return combinations
    
    async def list_all_assessments(
        self,
        session: AsyncSession,
    ) -> List[TechStackAssessment]:
        """
        列出所有测验记录
        
        Args:
            session: 数据库会话
            
        Returns:
            所有测验记录列表
        """
        result = await session.execute(
            select(TechStackAssessment).order_by(
                TechStackAssessment.technology,
                TechStackAssessment.proficiency_level,
            )
        )
        
        assessments = list(result.scalars().all())
        
        logger.debug("tech_assessments_listed", count=len(assessments))
        
        return assessments


# 单例模式
_tech_assessment_crud_instance: Optional[TechAssessmentCRUD] = None


def get_tech_assessment_crud() -> TechAssessmentCRUD:
    """获取TechAssessmentCRUD单例"""
    global _tech_assessment_crud_instance
    if _tech_assessment_crud_instance is None:
        _tech_assessment_crud_instance = TechAssessmentCRUD(TechStackAssessment)
    return _tech_assessment_crud_instance


class UserProfileCRUD(BaseCRUD[UserProfile, dict, dict]):
    """
    用户画像CRUD
    
    职责：
    - 用户画像的增删改查
    - 根据用户ID查询/更新画像
    """
    
    async def get_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> Optional[UserProfile]:
        """
        根据用户ID获取用户画像
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            
        Returns:
            用户画像或None
        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert_profile(
        self,
        session: AsyncSession,
        user_id: str,
        profile_data: dict,
    ) -> UserProfile:
        """
        创建或更新用户画像
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            profile_data: 画像数据
            
        Returns:
            用户画像
        """
        profile = await self.get_by_user_id(session, user_id)
        
        if profile:
            # 更新现有画像
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            # 创建新画像
            profile = UserProfile(user_id=user_id, **profile_data)
            session.add(profile)
        
        await session.flush()
        await session.refresh(profile)
        
        return profile


# 单例模式
_user_profile_crud_instance: Optional[UserProfileCRUD] = None


def get_user_profile_crud() -> UserProfileCRUD:
    """获取UserProfileCRUD单例"""
    global _user_profile_crud_instance
    if _user_profile_crud_instance is None:
        _user_profile_crud_instance = UserProfileCRUD(UserProfile)
    return _user_profile_crud_instance

