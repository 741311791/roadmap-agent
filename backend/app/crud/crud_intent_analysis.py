"""
意图分析CRUD操作

提供意图分析记录的数据库操作。
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.crud.base import BaseCRUD
from app.models.database import IntentAnalysisMetadata

if TYPE_CHECKING:
    from app.models.domain import IntentAnalysisOutput

logger = structlog.get_logger()


class IntentAnalysisCRUD(BaseCRUD[IntentAnalysisMetadata, dict, dict]):
    """
    意图分析CRUD
    
    职责：
    - 意图分析记录的增删改查
    - 根据任务ID查询分析记录
    """
    
    async def save_intent_analysis(
        self,
        session: AsyncSession,
        roadmap_id: str,
        intent_analysis: "IntentAnalysisOutput",
    ) -> IntentAnalysisMetadata:
        """
        保存意图分析结果
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            intent_analysis: 意图分析输出对象
            
        Returns:
            创建的意图分析元数据记录
        """
        # 检查是否已存在（避免重复）
        existing = await self.get_by_roadmap_id(session, roadmap_id)
        if existing:
            logger.warning(
                "intent_analysis_already_exists",
                intent_id=existing.intent_id,
                roadmap_id=roadmap_id,
            )
            return existing
        
        # 创建新记录
        metadata = IntentAnalysisMetadata(
            roadmap_id=roadmap_id,
            parsed_goal=intent_analysis.parsed_goal,
            key_technologies=intent_analysis.key_technologies,
            difficulty_profile=intent_analysis.difficulty_profile,
            time_constraint=intent_analysis.time_constraint,
            recommended_focus=intent_analysis.recommended_focus,
            user_profile_summary=intent_analysis.user_profile_summary or "",
            skill_gap_analysis=intent_analysis.skill_gap_analysis or [],
            personalized_suggestions=intent_analysis.personalized_suggestions or [],
            estimated_learning_path_type=intent_analysis.estimated_learning_path_type,
            content_format_weights=(
                intent_analysis.content_format_weights.model_dump() 
                if intent_analysis.content_format_weights 
                else None
            ),
            full_analysis_data=intent_analysis.model_dump(),
        )
        
        session.add(metadata)
        await session.flush()
        
        logger.info(
            "intent_analysis_saved",
            intent_id=metadata.intent_id,
            roadmap_id=roadmap_id,
            key_technologies_count=len(intent_analysis.key_technologies),
        )
        
        return metadata
    
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        根据路线图ID获取意图分析
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            意图分析记录或None
        """
        stmt = select(IntentAnalysisMetadata).where(
            IntentAnalysisMetadata.roadmap_id == roadmap_id
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# 单例模式
_intent_analysis_crud_instance: Optional[IntentAnalysisCRUD] = None


def get_intent_analysis_crud() -> IntentAnalysisCRUD:
    """获取IntentAnalysisCRUD单例"""
    global _intent_analysis_crud_instance
    if _intent_analysis_crud_instance is None:
        _intent_analysis_crud_instance = IntentAnalysisCRUD(IntentAnalysisMetadata)
    return _intent_analysis_crud_instance

