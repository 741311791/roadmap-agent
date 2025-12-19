"""
路线图 Repository

负责所有 Agent 产出的元数据存储：
- RoadmapTask: 任务状态
- RoadmapMetadata: A2 课程架构师产出
- TutorialMetadata: A4 教程生成器产出
- IntentAnalysisMetadata: A1 需求分析师产出
- ResourceRecommendationMetadata: A5 资源推荐师产出
- QuizMetadata: A6 测验生成器产出
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import SQLModel
import structlog

from app.models.database import (
    RoadmapTask,
    RoadmapMetadata,
    TutorialMetadata,
    IntentAnalysisMetadata,
    ResourceRecommendationMetadata,
    QuizMetadata,
    UserProfile,
    ExecutionLog,
    beijing_now,
)
from app.models.domain import (
    RoadmapFramework,
    TutorialGenerationOutput,
    IntentAnalysisOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)

logger = structlog.get_logger()


class RoadmapRepository:
    """路线图数据访问层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_task(
        self,
        task_id: str,
        user_id: str,
        user_request: dict,
        task_type: str = "creation",
        concept_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> RoadmapTask:
        """
        创建路线图生成任务
        
        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            user_request: 用户请求（字典格式）
            task_type: 任务类型（'creation', 'retry_tutorial', 'retry_resources', 'retry_quiz', 'retry_batch'）
            concept_id: 概念 ID（重试任务需要）
            content_type: 内容类型（重试任务需要）
            
        Returns:
            创建的任务记录
        """
        task = RoadmapTask(
            task_id=task_id,
            user_id=user_id,
            user_request=user_request,
            status="pending",
            current_step="init",
            task_type=task_type,
            concept_id=concept_id,
            content_type=content_type,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        
        logger.info("roadmap_task_created", 
                   task_id=task_id, 
                   user_id=user_id,
                   task_type=task_type)
        return task
    
    async def get_task(self, task_id: str) -> Optional[RoadmapTask]:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_task_by_roadmap_id(self, roadmap_id: str) -> Optional[RoadmapTask]:
        """
        通过 roadmap_id 获取任务（任何状态）
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            任务记录（按创建时间倒序，返回最新的），如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_active_task_by_roadmap_id(self, roadmap_id: str) -> Optional[RoadmapTask]:
        """
        通过 roadmap_id 获取活跃任务
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            活跃任务记录（状态为 processing 或 pending），如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.roadmap_id == roadmap_id,
                RoadmapTask.status.in_(["pending", "processing", "human_review_pending"])
            )
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_active_tasks_by_roadmap_id(self, roadmap_id: str) -> list[RoadmapTask]:
        """
        获取路线图的所有活跃任务（包括创建任务和重试任务）
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            活跃任务列表（按创建时间降序排序）
        """
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.roadmap_id == roadmap_id,
                RoadmapTask.status.in_(["pending", "processing", "human_review_pending"])
            )
            .order_by(RoadmapTask.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_active_retry_task_by_roadmap_id(self, roadmap_id: str) -> Optional[RoadmapTask]:
        """
        通过 roadmap_id 获取正在进行的重试任务
        
        用于前端检测是否有正在进行的重试任务，以便用户切换 tab 返回时恢复订阅。
        
        重试任务的特征：
        - roadmap_id 匹配
        - status 为 "processing"
        - user_request.type 为 "retry_failed"
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            正在进行的重试任务记录，如果不存在则返回 None
        """
        from sqlalchemy import cast, String
        
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.roadmap_id == roadmap_id,
                RoadmapTask.status == "processing",
                # JSON 字段查询：检查 user_request.type == "retry_failed"
                cast(RoadmapTask.user_request["type"], String) == '"retry_failed"'
            )
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_in_progress_tasks_by_user(self, user_id: str) -> List[RoadmapTask]:
        """
        获取用户所有进行中的任务
        
        用于在首页显示正在生成中的路线图。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            进行中的任务列表（状态为 pending、processing、human_review_pending 或 failed）
        """
        result = await self.session.execute(
            select(RoadmapTask)
            .where(
                RoadmapTask.user_id == user_id,
                RoadmapTask.status.in_(["pending", "processing", "human_review_pending", "failed"])
            )
            .order_by(RoadmapTask.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_tasks_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RoadmapTask]:
        """
        获取用户的所有任务，可按状态和任务类型筛选
        
        Args:
            user_id: 用户 ID
            status: 任务状态筛选（可选）：pending, processing, completed, failed
            task_type: 任务类型筛选（可选）：creation, retry_tutorial, retry_resources, retry_quiz, retry_batch
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            任务列表（按创建时间降序）
        """
        query = select(RoadmapTask).where(RoadmapTask.user_id == user_id)
        
        if status:
            query = query.where(RoadmapTask.status == status)
        
        if task_type:
            query = query.where(RoadmapTask.task_type == task_type)
        
        query = query.order_by(RoadmapTask.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        current_step: str,
        roadmap_id: Optional[str] = None,
        error_message: Optional[str] = None,
        failed_concepts: Optional[dict] = None,
        execution_summary: Optional[dict] = None,
    ) -> Optional[RoadmapTask]:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态 (pending, processing, completed, partial_failure, failed)
            current_step: 当前步骤
            roadmap_id: 路线图 ID（可选）
            error_message: 错误信息（可选）
            failed_concepts: 失败概念详情（可选）
            execution_summary: 执行摘要（可选）
            
        Returns:
            更新后的任务记录
        """
        task = await self.get_task(task_id)
        if not task:
            return None
        
        task.status = status
        task.current_step = current_step
        # 每次更新状态时都更新 updated_at
        task.updated_at = beijing_now()
        
        if roadmap_id:
            task.roadmap_id = roadmap_id
        if error_message:
            task.error_message = error_message
        if failed_concepts is not None:
            task.failed_concepts = failed_concepts
        if execution_summary is not None:
            task.execution_summary = execution_summary
        
        # 当任务完成（包括部分失败）或失败时，设置 completed_at
        if status in ("completed", "partial_failure", "failed"):
            task.completed_at = beijing_now()
        
        await self.session.commit()
        await self.session.refresh(task)
        
        logger.info(
            "roadmap_task_updated",
            task_id=task_id,
            status=status,
            current_step=current_step,
            has_failed_concepts=failed_concepts is not None,
            has_execution_summary=execution_summary is not None,
        )
        return task
    
    async def save_roadmap_metadata(
        self,
        roadmap_id: str,
        user_id: str,
        framework: RoadmapFramework,
    ) -> RoadmapMetadata:
        """
        保存路线图元数据（如果存在则更新，不存在则插入）
        
        Args:
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            framework: 路线图框架
            
        Returns:
            保存的元数据记录
        """
        # 检查是否已存在
        existing = await self.get_roadmap_metadata(roadmap_id)
        
        if existing:
            # 更新现有记录
            existing.user_id = user_id
            existing.title = framework.title
            existing.total_estimated_hours = framework.total_estimated_hours
            existing.recommended_completion_weeks = framework.recommended_completion_weeks
            existing.framework_data = framework.model_dump()
            # 关键修复：显式标记 JSON 字段已修改
            # SQLAlchemy 默认无法检测 JSON 列的变更，需要手动标记
            flag_modified(existing, "framework_data")
            await self.session.commit()
            await self.session.refresh(existing)
            logger.info("roadmap_metadata_updated", roadmap_id=roadmap_id, user_id=user_id)
            return existing
        else:
            # 创建新记录
            metadata = RoadmapMetadata(
                roadmap_id=roadmap_id,
                user_id=user_id,
                title=framework.title,
                total_estimated_hours=framework.total_estimated_hours,
                recommended_completion_weeks=framework.recommended_completion_weeks,
                framework_data=framework.model_dump(),
            )
            self.session.add(metadata)
            await self.session.commit()
            await self.session.refresh(metadata)
            logger.info("roadmap_metadata_saved", roadmap_id=roadmap_id, user_id=user_id)
            return metadata
    
    async def get_roadmap_metadata(self, roadmap_id: str) -> Optional[RoadmapMetadata]:
        """
        获取路线图元数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            元数据记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none()
    
    async def roadmap_id_exists(self, roadmap_id: str) -> bool:
        """
        检查 roadmap_id 是否已存在于数据库中
        
        Args:
            roadmap_id: 要检查的路线图 ID
            
        Returns:
            True 如果存在，False 如果不存在
        """
        result = await self.session.execute(
            select(RoadmapMetadata.roadmap_id).where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_roadmaps_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RoadmapMetadata]:
        """
        获取用户的所有路线图列表（排除已删除的）
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            路线图元数据列表（按创建时间降序排列，最新的在前，排除已软删除的）
        """
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(
                RoadmapMetadata.user_id == user_id,
                RoadmapMetadata.deleted_at.is_(None)  # 排除已删除的
            )
            .order_by(RoadmapMetadata.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_deleted_roadmaps(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RoadmapMetadata]:
        """
        获取用户回收站中的路线图列表
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            已删除的路线图元数据列表（按删除时间降序排列）
        """
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(
                RoadmapMetadata.user_id == user_id,
                RoadmapMetadata.deleted_at.isnot(None)  # 只查询已删除的
            )
            .order_by(RoadmapMetadata.deleted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def soft_delete_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        软删除路线图（移至回收站）
        
        Args:
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            
        Returns:
            更新后的路线图元数据，如果不存在或用户 ID 不匹配则返回 None
        """
        metadata = await self.get_roadmap_metadata(roadmap_id)
        if not metadata or metadata.user_id != user_id:
            logger.warning(
                "soft_delete_failed_not_found_or_unauthorized",
                roadmap_id=roadmap_id,
                user_id=user_id,
            )
            return None
        
        # 设置删除时间和删除者
        metadata.deleted_at = beijing_now()
        metadata.deleted_by = user_id
        
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "roadmap_soft_deleted",
            roadmap_id=roadmap_id,
            user_id=user_id,
            deleted_at=metadata.deleted_at,
        )
        return metadata
    
    async def restore_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        从回收站恢复路线图
        
        Args:
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            
        Returns:
            恢复后的路线图元数据，如果不存在或用户 ID 不匹配则返回 None
        """
        metadata = await self.get_roadmap_metadata(roadmap_id)
        if not metadata or metadata.user_id != user_id:
            logger.warning(
                "restore_failed_not_found_or_unauthorized",
                roadmap_id=roadmap_id,
                user_id=user_id,
            )
            return None
        
        # 清除删除标记
        metadata.deleted_at = None
        metadata.deleted_by = None
        
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "roadmap_restored",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        return metadata
    
    async def permanent_delete_roadmap(
        self,
        roadmap_id: str,
    ) -> bool:
        """
        永久删除路线图（从数据库中删除）
        
        注意：此操作不可逆，会删除所有关联数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            True 如果删除成功，False 如果路线图不存在
        """
        metadata = await self.get_roadmap_metadata(roadmap_id)
        if not metadata:
            logger.warning(
                "permanent_delete_failed_not_found",
                roadmap_id=roadmap_id,
            )
            return False
        
        # 删除元数据（级联删除会处理关联的教程、资源、测验元数据）
        await self.session.delete(metadata)
        await self.session.commit()
        
        logger.info(
            "roadmap_permanently_deleted",
            roadmap_id=roadmap_id,
        )
        return True
    
    async def get_expired_deleted_roadmaps(
        self,
        days: int = 30,
    ) -> List[RoadmapMetadata]:
        """
        获取超过指定天数的已删除路线图（用于自动清理）
        
        Args:
            days: 删除后经过的天数，默认 30 天
            
        Returns:
            符合条件的路线图元数据列表
        """
        from datetime import timedelta
        
        cutoff_date = beijing_now() - timedelta(days=days)
        
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(
                RoadmapMetadata.deleted_at.isnot(None),
                RoadmapMetadata.deleted_at < cutoff_date
            )
            .order_by(RoadmapMetadata.deleted_at.asc())
        )
        return list(result.scalars().all())
    
    async def save_tutorial_metadata(
        self,
        tutorial_output: TutorialGenerationOutput,
        roadmap_id: str,
    ) -> TutorialMetadata:
        """
        保存教程元数据（支持版本管理）
        
        Args:
            tutorial_output: 教程生成输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的教程元数据记录
            
        注意：
        - 新保存的教程默认为最新版本（is_latest=True）
        - 保存前会将该概念的旧版本标记为非最新
        """
        # 将该概念的旧版本标记为非最新
        await self._mark_concept_tutorials_not_latest(
            roadmap_id=roadmap_id,
            concept_id=tutorial_output.concept_id,
        )
        
        metadata = TutorialMetadata(
            tutorial_id=tutorial_output.tutorial_id,
            concept_id=tutorial_output.concept_id,
            roadmap_id=roadmap_id,
            title=tutorial_output.title,
            summary=tutorial_output.summary,
            content_url=tutorial_output.content_url,
            content_status=tutorial_output.content_status,
            content_version=tutorial_output.content_version,
            is_latest=True,  # 新版本默认为最新
            estimated_completion_time=tutorial_output.estimated_completion_time,
            generated_at=tutorial_output.generated_at,
        )
        self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "tutorial_metadata_saved",
            tutorial_id=tutorial_output.tutorial_id,
            concept_id=tutorial_output.concept_id,
            roadmap_id=roadmap_id,
            content_version=tutorial_output.content_version,
            is_latest=True,
        )
        return metadata
    
    async def _mark_concept_tutorials_not_latest(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        将指定概念的所有教程版本标记为非最新
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            更新的记录数
        """
        from sqlalchemy import update
        
        result = await self.session.execute(
            update(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.is_latest == True,
            )
            .values(is_latest=False)
        )
        
        updated_count = result.rowcount
        if updated_count > 0:
            logger.debug(
                "tutorial_versions_marked_not_latest",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                updated_count=updated_count,
            )
        
        return updated_count
    
    async def get_latest_tutorial(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定概念的最新教程版本
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            最新版本的教程元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(TutorialMetadata).where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.is_latest == True,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_tutorial_by_version(
        self,
        roadmap_id: str,
        concept_id: str,
        version: int,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定概念的特定版本教程
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            version: 版本号
            
        Returns:
            教程元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(TutorialMetadata).where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.content_version == version,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_next_tutorial_version(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        获取指定概念的下一个教程版本号
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            下一个版本号（如果没有现有版本，返回 1）
        """
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(func.max(TutorialMetadata.content_version)).where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
            )
        )
        max_version = result.scalar_one_or_none()
        
        return (max_version or 0) + 1
    
    async def get_tutorial_history(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> List[TutorialMetadata]:
        """
        获取指定概念的所有教程版本历史
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            教程元数据列表（按版本号降序排列，最新版本在前）
        """
        result = await self.session.execute(
            select(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
            )
            .order_by(TutorialMetadata.content_version.desc())
        )
        return list(result.scalars().all())
    
    async def get_tutorials_by_roadmap(
        self,
        roadmap_id: str,
        latest_only: bool = True,
    ) -> List[TutorialMetadata]:
        """
        获取路线图的所有教程
        
        Args:
            roadmap_id: 路线图 ID
            latest_only: 是否只返回最新版本（默认 True）
            
        Returns:
            教程元数据列表
        """
        query = select(TutorialMetadata).where(
            TutorialMetadata.roadmap_id == roadmap_id
        )
        
        if latest_only:
            query = query.where(TutorialMetadata.is_latest == True)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def save_tutorials_batch(
        self,
        tutorial_refs: dict[str, TutorialGenerationOutput],
        roadmap_id: str,
    ) -> list[TutorialMetadata]:
        """
        批量保存教程元数据
        
        Args:
            tutorial_refs: 教程引用字典（concept_id -> TutorialGenerationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的教程元数据记录列表
        """
        metadata_list = []
        for concept_id, tutorial_output in tutorial_refs.items():
            metadata = await self.save_tutorial_metadata(tutorial_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "tutorials_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        return metadata_list
    
    # ============================================================
    # A1: 需求分析师产出 (IntentAnalysisMetadata)
    # ============================================================
    
    async def save_intent_analysis_metadata(
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
            content_format_weights=intent_analysis.content_format_weights.model_dump() if intent_analysis.content_format_weights else None,
            # 语言偏好
            language_preferences=intent_analysis.language_preferences.model_dump() if intent_analysis.language_preferences else None,
            # 完整数据
            full_analysis_data=intent_analysis.model_dump(),
        )
        self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "intent_analysis_metadata_saved",
            task_id=task_id,
            roadmap_id=intent_analysis.roadmap_id,
            key_technologies_count=len(intent_analysis.key_technologies),
            learning_path_type=intent_analysis.estimated_learning_path_type,
            primary_language=intent_analysis.language_preferences.primary_language if intent_analysis.language_preferences else None,
        )
        return metadata
    
    async def get_intent_analysis_metadata(
        self,
        task_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        获取需求分析结果元数据
        
        Args:
            task_id: 任务 ID
            
        Returns:
            元数据记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(IntentAnalysisMetadata).where(
                IntentAnalysisMetadata.task_id == task_id
            )
        )
        return result.scalar_one_or_none()
    
    # ============================================================
    # A5: 资源推荐师产出 (ResourceRecommendationMetadata)
    # ============================================================
    
    async def save_resource_recommendation_metadata(
        self,
        resource_output: ResourceRecommendationOutput,
        roadmap_id: str,
    ) -> ResourceRecommendationMetadata:
        """
        保存资源推荐元数据（如果已存在则替换）
        
        Args:
            resource_output: 资源推荐输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录
        """
        # 删除旧的资源推荐记录（如果存在）
        from sqlalchemy import delete
        await self.session.execute(
            delete(ResourceRecommendationMetadata).where(
                ResourceRecommendationMetadata.concept_id == resource_output.concept_id,
                ResourceRecommendationMetadata.roadmap_id == roadmap_id,
            )
        )
        
        metadata = ResourceRecommendationMetadata(
            id=resource_output.id,  # 使用 output 中的 ID，确保与 Concept 中的 resources_id 一致
            concept_id=resource_output.concept_id,
            roadmap_id=roadmap_id,
            resources=[r.model_dump() for r in resource_output.resources],
            resources_count=len(resource_output.resources),
            search_queries_used=resource_output.search_queries_used,
            generated_at=resource_output.generated_at,
        )
        self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "resource_recommendation_metadata_saved",
            concept_id=resource_output.concept_id,
            roadmap_id=roadmap_id,
            resources_count=len(resource_output.resources),
        )
        return metadata
    
    async def save_resources_batch(
        self,
        resource_refs: dict[str, ResourceRecommendationOutput],
        roadmap_id: str,
    ) -> List[ResourceRecommendationMetadata]:
        """
        批量保存资源推荐元数据
        
        Args:
            resource_refs: 资源推荐字典（concept_id -> ResourceRecommendationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        for concept_id, resource_output in resource_refs.items():
            metadata = await self.save_resource_recommendation_metadata(
                resource_output, roadmap_id
            )
            metadata_list.append(metadata)
        
        logger.info(
            "resources_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        return metadata_list
    
    async def get_resource_recommendations_by_roadmap(
        self,
        roadmap_id: str,
    ) -> List[ResourceRecommendationMetadata]:
        """
        获取路线图的所有资源推荐
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            资源推荐元数据列表
        """
        result = await self.session.execute(
            select(ResourceRecommendationMetadata).where(
                ResourceRecommendationMetadata.roadmap_id == roadmap_id
            )
        )
        return list(result.scalars().all())
    
    async def get_resources_by_concept(
        self,
        concept_id: str,
        roadmap_id: str,
    ) -> Optional[ResourceRecommendationMetadata]:
        """
        获取指定概念的资源推荐
        
        Args:
            concept_id: 概念 ID
            roadmap_id: 路线图 ID
            
        Returns:
            资源推荐元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(ResourceRecommendationMetadata).where(
                ResourceRecommendationMetadata.concept_id == concept_id,
                ResourceRecommendationMetadata.roadmap_id == roadmap_id,
            )
        )
        return result.scalar_one_or_none()
    
    # ============================================================
    # A6: 测验生成器产出 (QuizMetadata)
    # ============================================================
    
    async def save_quiz_metadata(
        self,
        quiz_output: QuizGenerationOutput,
        roadmap_id: str,
    ) -> QuizMetadata:
        """
        保存测验元数据（如果已存在则替换）
        
        Args:
            quiz_output: 测验生成输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录
        """
        # 删除旧的测验记录（如果存在）
        from sqlalchemy import delete
        await self.session.execute(
            delete(QuizMetadata).where(
                QuizMetadata.concept_id == quiz_output.concept_id,
                QuizMetadata.roadmap_id == roadmap_id,
            )
        )
        
        # 统计难度分布
        easy_count = sum(1 for q in quiz_output.questions if q.difficulty == "easy")
        medium_count = sum(1 for q in quiz_output.questions if q.difficulty == "medium")
        hard_count = sum(1 for q in quiz_output.questions if q.difficulty == "hard")
        
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
        self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "quiz_metadata_saved",
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            roadmap_id=roadmap_id,
            total_questions=quiz_output.total_questions,
        )
        return metadata
    
    async def save_quizzes_batch(
        self,
        quiz_refs: dict[str, QuizGenerationOutput],
        roadmap_id: str,
    ) -> List[QuizMetadata]:
        """
        批量保存测验元数据
        
        Args:
            quiz_refs: 测验字典（concept_id -> QuizGenerationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        for concept_id, quiz_output in quiz_refs.items():
            metadata = await self.save_quiz_metadata(quiz_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "quizzes_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        return metadata_list
    
    async def get_quizzes_by_roadmap(
        self,
        roadmap_id: str,
    ) -> List[QuizMetadata]:
        """
        获取路线图的所有测验
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            测验元数据列表
        """
        result = await self.session.execute(
            select(QuizMetadata).where(QuizMetadata.roadmap_id == roadmap_id)
        )
        return list(result.scalars().all())
    
    async def get_quiz_by_concept(
        self,
        concept_id: str,
        roadmap_id: str,
    ) -> Optional[QuizMetadata]:
        """
        获取指定概念的测验
        
        Args:
            concept_id: 概念 ID
            roadmap_id: 路线图 ID
            
        Returns:
            测验元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(QuizMetadata).where(
                QuizMetadata.concept_id == concept_id,
                QuizMetadata.roadmap_id == roadmap_id,
            )
        )
        return result.scalar_one_or_none()
    
    # ============================================================
    # User Profile (用户画像)
    # ============================================================
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户画像，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def save_user_profile(
        self,
        user_id: str,
        profile_data: dict,
    ) -> UserProfile:
        """
        保存或更新用户画像
        
        Args:
            user_id: 用户 ID
            profile_data: 用户画像数据
            
        Returns:
            保存的用户画像记录
        """
        existing = await self.get_user_profile(user_id)
        
        if existing:
            # 更新现有记录
            for key, value in profile_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = beijing_now()
            await self.session.commit()
            await self.session.refresh(existing)
            
            logger.info("user_profile_updated", user_id=user_id)
            return existing
        else:
            # 创建新记录
            profile = UserProfile(
                user_id=user_id,
                industry=profile_data.get('industry'),
                current_role=profile_data.get('current_role'),
                tech_stack=profile_data.get('tech_stack', []),
                primary_language=profile_data.get('primary_language', 'zh'),
                secondary_language=profile_data.get('secondary_language'),
                weekly_commitment_hours=profile_data.get('weekly_commitment_hours', 10),
                learning_style=profile_data.get('learning_style', []),
                ai_personalization=profile_data.get('ai_personalization', True),
                created_at=beijing_now(),
                updated_at=beijing_now(),
            )
            self.session.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)
            
            logger.info("user_profile_created", user_id=user_id)
            return profile
    
    # ============================================================
    # Execution Logs (执行日志)
    # ============================================================
    
    async def count_execution_logs_by_trace(
        self,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """
        统计指定 task_id 的执行日志总数
        
        Args:
            task_id: 追踪 ID（对应 task_id）
            level: 过滤日志级别（可选）
            category: 过滤日志分类（可选）
            
        Returns:
            满足条件的日志总数
        """
        query = select(func.count(ExecutionLog.id)).where(ExecutionLog.task_id == task_id)
        
        if level:
            query = query.where(ExecutionLog.level == level)
        if category:
            query = query.where(ExecutionLog.category == category)
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_execution_logs_by_trace(
        self,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExecutionLog]:
        """
        获取指定 task_id 的执行日志
        
        Args:
            task_id: 追踪 ID（对应 task_id）
            level: 过滤日志级别（可选）
            category: 过滤日志分类（可选）
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            执行日志列表（按时间降序）
        """
        query = select(ExecutionLog).where(ExecutionLog.task_id == task_id)
        
        if level:
            query = query.where(ExecutionLog.level == level)
        if category:
            query = query.where(ExecutionLog.category == category)
        
        query = query.order_by(ExecutionLog.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_execution_logs_summary(
        self,
        task_id: str,
    ) -> dict:
        """
        获取执行日志摘要统计
        
        Args:
            task_id: 追踪 ID
            
        Returns:
            包含统计信息的字典
        """
        # 统计各级别日志数量
        level_counts = await self.session.execute(
            select(
                ExecutionLog.level,
                func.count(ExecutionLog.id).label('count')
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.level)
        )
        level_stats = {row[0]: row[1] for row in level_counts.fetchall()}
        
        # 统计各分类日志数量
        category_counts = await self.session.execute(
            select(
                ExecutionLog.category,
                func.count(ExecutionLog.id).label('count')
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.category)
        )
        category_stats = {row[0]: row[1] for row in category_counts.fetchall()}
        
        # 计算总耗时
        duration_result = await self.session.execute(
            select(func.sum(ExecutionLog.duration_ms))
            .where(ExecutionLog.task_id == task_id)
            .where(ExecutionLog.duration_ms.isnot(None))
        )
        total_duration_ms = duration_result.scalar_one_or_none() or 0
        
        # 获取时间范围
        time_range_result = await self.session.execute(
            select(
                func.min(ExecutionLog.created_at).label('first'),
                func.max(ExecutionLog.created_at).label('last'),
            )
            .where(ExecutionLog.task_id == task_id)
        )
        time_range = time_range_result.fetchone()
        
        return {
            "task_id": task_id,
            "level_stats": level_stats,
            "category_stats": category_stats,
            "total_duration_ms": total_duration_ms,
            "first_log_at": time_range[0].isoformat() if time_range and time_range[0] else None,
            "last_log_at": time_range[1].isoformat() if time_range and time_range[1] else None,
            "total_logs": sum(level_stats.values()),
        }
    
    async def get_error_logs_by_trace(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[ExecutionLog]:
        """
        获取指定 task_id 的错误日志
        
        Args:
            task_id: 追踪 ID
            limit: 返回数量限制
            
        Returns:
            错误日志列表（按时间降序）
        """
        result = await self.session.execute(
            select(ExecutionLog)
            .where(
                ExecutionLog.task_id == task_id,
                ExecutionLog.level == "error",
            )
            .order_by(ExecutionLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

