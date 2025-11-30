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
from sqlalchemy import select
from sqlmodel import SQLModel
import structlog

from app.models.database import (
    RoadmapTask,
    RoadmapMetadata,
    TutorialMetadata,
    IntentAnalysisMetadata,
    ResourceRecommendationMetadata,
    QuizMetadata,
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
    ) -> RoadmapTask:
        """
        创建路线图生成任务
        
        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            user_request: 用户请求（字典格式）
            
        Returns:
            创建的任务记录
        """
        task = RoadmapTask(
            task_id=task_id,
            user_id=user_id,
            user_request=user_request,
            status="pending",
            current_step="init",
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        
        logger.info("roadmap_task_created", task_id=task_id, user_id=user_id)
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
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        current_step: str,
        roadmap_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[RoadmapTask]:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态
            current_step: 当前步骤
            roadmap_id: 路线图 ID（可选）
            error_message: 错误信息（可选）
            
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
        
        # 当任务完成或失败时，设置 completed_at
        if status in ("completed", "failed"):
            task.completed_at = beijing_now()
        
        await self.session.commit()
        await self.session.refresh(task)
        
        logger.info(
            "roadmap_task_updated",
            task_id=task_id,
            status=status,
            current_step=current_step,
        )
        return task
    
    async def save_roadmap_metadata(
        self,
        roadmap_id: str,
        user_id: str,
        task_id: str,
        framework: RoadmapFramework,
    ) -> RoadmapMetadata:
        """
        保存路线图元数据（如果存在则更新，不存在则插入）
        
        Args:
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            task_id: 任务 ID
            framework: 路线图框架
            
        Returns:
            保存的元数据记录
        """
        # 检查是否已存在
        existing = await self.get_roadmap_metadata(roadmap_id)
        
        if existing:
            # 更新现有记录
            existing.user_id = user_id
            existing.task_id = task_id
            existing.title = framework.title
            existing.total_estimated_hours = framework.total_estimated_hours
            existing.recommended_completion_weeks = framework.recommended_completion_weeks
            existing.framework_data = framework.model_dump()
            await self.session.commit()
            await self.session.refresh(existing)
            logger.info("roadmap_metadata_updated", roadmap_id=roadmap_id, user_id=user_id)
            return existing
        else:
            # 创建新记录
            metadata = RoadmapMetadata(
                roadmap_id=roadmap_id,
                user_id=user_id,
                task_id=task_id,
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
        保存需求分析结果元数据
        
        Args:
            task_id: 任务 ID
            intent_analysis: 需求分析输出
            
        Returns:
            保存的元数据记录
        """
        metadata = IntentAnalysisMetadata(
            task_id=task_id,
            parsed_goal=intent_analysis.parsed_goal,
            key_technologies=intent_analysis.key_technologies,
            difficulty_profile=intent_analysis.difficulty_profile,
            time_constraint=intent_analysis.time_constraint,
            recommended_focus=intent_analysis.recommended_focus,
            full_analysis_data=intent_analysis.model_dump(),
        )
        self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        
        logger.info(
            "intent_analysis_metadata_saved",
            task_id=task_id,
            key_technologies_count=len(intent_analysis.key_technologies),
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

