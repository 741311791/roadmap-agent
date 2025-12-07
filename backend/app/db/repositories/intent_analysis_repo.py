"""
需求分析 Repository

负责 IntentAnalysisMetadata 表的数据访问操作。

职责范围：
- 需求分析元数据的 CRUD 操作
- 需求分析查询（根据任务、路线图等）

不包含：
- 需求分析逻辑（在 Agent 层）
- 技能差距计算（在 Service 层）
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import IntentAnalysisMetadata
from app.models.domain import IntentAnalysisOutput
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class IntentAnalysisRepository(BaseRepository[IntentAnalysisMetadata]):
    """
    需求分析数据访问层
    
    管理用户需求分析结果元数据。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, IntentAnalysisMetadata)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_task_id(self, task_id: str) -> Optional[IntentAnalysisMetadata]:
        """
        获取需求分析结果元数据
        
        Args:
            task_id: 任务 ID
            
        Returns:
            元数据记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(IntentAnalysisMetadata)
            .where(IntentAnalysisMetadata.task_id == task_id)
        )
        
        analysis = result.scalar_one_or_none()
        
        if analysis:
            logger.debug(
                "intent_analysis_found",
                task_id=task_id,
                roadmap_id=analysis.roadmap_id,
            )
        
        return analysis
    
    async def get_by_roadmap_id(
        self,
        roadmap_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        根据路线图 ID 查询需求分析
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            元数据记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(IntentAnalysisMetadata)
            .where(IntentAnalysisMetadata.roadmap_id == roadmap_id)
        )
        
        return result.scalar_one_or_none()
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_intent_analysis(
        self,
        task_id: str,
        intent_analysis: IntentAnalysisOutput,
    ) -> IntentAnalysisMetadata:
        """
        保存需求分析结果元数据（支持增强版字段）
        
        Args:
            task_id: 任务 ID
            intent_analysis: 需求分析输出
            
        Returns:
            保存的元数据记录
        """
        metadata = IntentAnalysisMetadata(
            task_id=task_id,
            # 路线图 ID（在需求分析完成后生成）
            roadmap_id=intent_analysis.roadmap_id,
            # 原有字段
            parsed_goal=intent_analysis.parsed_goal,
            key_technologies=intent_analysis.key_technologies,
            difficulty_profile=intent_analysis.difficulty_profile,
            time_constraint=intent_analysis.time_constraint,
            recommended_focus=intent_analysis.recommended_focus,
            # 新增字段
            user_profile_summary=intent_analysis.user_profile_summary or "",
            skill_gap_analysis=intent_analysis.skill_gap_analysis or [],
            personalized_suggestions=intent_analysis.personalized_suggestions or [],
            estimated_learning_path_type=intent_analysis.estimated_learning_path_type,
            content_format_weights=(
                intent_analysis.content_format_weights.model_dump()
                if intent_analysis.content_format_weights
                else None
            ),
            # 语言偏好
            language_preferences=(
                intent_analysis.language_preferences.model_dump()
                if intent_analysis.language_preferences
                else None
            ),
            # 完整数据
            full_analysis_data=intent_analysis.model_dump(),
        )
        
        await self.create(metadata, flush=True)
        
        logger.info(
            "intent_analysis_metadata_saved",
            task_id=task_id,
            roadmap_id=intent_analysis.roadmap_id,
            key_technologies_count=len(intent_analysis.key_technologies),
            learning_path_type=intent_analysis.estimated_learning_path_type,
            primary_language=(
                intent_analysis.language_preferences.primary_language
                if intent_analysis.language_preferences
                else None
            ),
        )
        
        return metadata
    
    async def update_roadmap_id(
        self,
        task_id: str,
        roadmap_id: str,
    ) -> bool:
        """
        更新需求分析的 roadmap_id
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            
        Returns:
            True 如果更新成功，False 如果记录不存在
        """
        # 首先获取记录的 ID
        analysis = await self.get_by_task_id(task_id)
        if not analysis:
            return False
        
        return await self.update_by_id(
            analysis.id,
            roadmap_id=roadmap_id,
        )
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_by_task_id(self, task_id: str) -> bool:
        """
        删除任务的需求分析元数据
        
        Args:
            task_id: 任务 ID
            
        Returns:
            True 如果删除成功，False 如果记录不存在
        """
        analysis = await self.get_by_task_id(task_id)
        if not analysis:
            return False
        
        deleted = await self.delete_by_id(analysis.id)
        
        if deleted:
            logger.info("intent_analysis_deleted", task_id=task_id)
        
        return deleted
