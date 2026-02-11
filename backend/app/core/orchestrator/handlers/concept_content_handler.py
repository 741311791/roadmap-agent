"""
单 Concept 内容 Handler

职责：
- 保存单个 Concept 的 Tutorial、Resource、Quiz 元数据
- 更新 ConceptMetadata 表的状态追踪
- 记录保存状态（成功/失败）
- 不更新 Framework（由最终汇总节点批量更新）

设计原则：
- 细粒度保存：每个 Concept 独立保存
- 容错性：部分失败不影响其他内容
- 状态追踪：记录每种内容的保存状态
- 数据一致性：同步更新 ConceptMetadata
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.domain import (
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)
from app.schemas.handler_io import ConceptContentSaveResult
from app.crud.crud_tutorial import get_tutorial_crud
from app.crud.crud_resource import get_resource_crud
from app.crud.crud_quiz import get_quiz_crud
from app.crud.crud_concept import get_concept_crud

logger = structlog.get_logger()


class ConceptContentHandler:
    """
    单 Concept 内容 Handler
    
    负责保存单个 Concept 的内容元数据，不更新 Framework。
    Framework 的更新由最终汇总节点批量处理。
    """
    
    def __init__(self):
        """初始化 Handler"""
        pass
    
    async def save_concept_content(
        self,
        session: AsyncSession,
        concept_id: str,
        roadmap_id: str,
        tutorial: TutorialGenerationOutput | None = None,
        resource: ResourceRecommendationOutput | None = None,
        quiz: QuizGenerationOutput | None = None,
    ) -> ConceptContentSaveResult:
        """
        保存单个 Concept 的内容元数据
        
        Args:
            session: 数据库会话
            concept_id: Concept ID
            roadmap_id: 路线图 ID
            tutorial: 教程生成输出（可选）
            resource: 资源推荐输出（可选）
            quiz: 测验生成输出（可选）
            
        Returns:
            保存状态（强类型 Pydantic Model）
        """
        # 初始化保存状态
        tutorial_status = "skipped"
        tutorial_output_dict = None
        resource_status = "skipped"
        resource_output_dict = None
        quiz_status = "skipped"
        quiz_output_dict = None
        
        saved_count = 0
        total_count = sum([
            tutorial is not None,
            resource is not None,
            quiz is not None,
        ])
        
        logger.info(
            "concept_content_handler_saving",
            concept_id=concept_id,
            roadmap_id=roadmap_id,
            has_tutorial=tutorial is not None,
            has_resource=resource is not None,
            has_quiz=quiz is not None,
        )
        
        # 保存 Tutorial
        if tutorial:
            try:
                tutorial_crud = get_tutorial_crud()
                await tutorial_crud.save_tutorial(
                    session=session,
                    tutorial_output=tutorial,  # ✅ 修正参数名
                    roadmap_id=roadmap_id,
                )
                tutorial_status = "success"
                tutorial_output_dict = tutorial.model_dump()
                saved_count += 1
                
                logger.info(
                    "tutorial_metadata_saved",
                    concept_id=concept_id,
                    tutorial_id=tutorial.tutorial_id,
                )
            except Exception as e:
                logger.error(
                    "tutorial_metadata_save_failed",
                    concept_id=concept_id,
                    error=str(e),
                    exc_info=True,
                )
                tutorial_status = "failed"
        
        # 保存 Resource
        if resource:
            try:
                resource_crud = get_resource_crud()
                await resource_crud.save_resource_recommendation(  # ✅ 修正方法名
                    session=session,
                    resource_output=resource,  # ✅ 修正参数名
                    roadmap_id=roadmap_id,
                )
                resource_status = "success"
                resource_output_dict = resource.model_dump()
                saved_count += 1
                
                logger.info(
                    "resource_metadata_saved",
                    concept_id=concept_id,
                    resource_id=resource.id,
                    resource_count=len(resource.resources),
                )
            except Exception as e:
                logger.error(
                    "resource_metadata_save_failed",
                    concept_id=concept_id,
                    error=str(e),
                    exc_info=True,
                )
                resource_status = "failed"
        
        # 保存 Quiz
        if quiz:
            try:
                quiz_crud = get_quiz_crud()
                await quiz_crud.save_quiz(
                    session=session,
                    quiz_output=quiz,  # ✅ 修正参数名
                    roadmap_id=roadmap_id,
                )
                quiz_status = "success"
                quiz_output_dict = quiz.model_dump()
                saved_count += 1
                
                logger.info(
                    "quiz_metadata_saved",
                    concept_id=concept_id,
                    quiz_id=quiz.quiz_id,
                    question_count=len(quiz.questions),
                )
            except Exception as e:
                logger.error(
                    "quiz_metadata_save_failed",
                    concept_id=concept_id,
                    error=str(e),
                    exc_info=True,
                )
                quiz_status = "failed"
        
        # 标记是否所有元数据都已保存
        metadata_saved = (saved_count == total_count and total_count > 0)
        
        # ✅ 更新 ConceptMetadata 表（状态追踪）
        try:
            concept_crud = get_concept_crud()
            
            # 确保 ConceptMetadata 记录存在
            concept_metadata = await concept_crud.get_by_concept_id(session, concept_id)
            if not concept_metadata:
                # 创建新记录
                concept_metadata = await concept_crud.create_or_update_metadata(
                    session=session,
                    concept_id=concept_id,
                    roadmap_id=roadmap_id,
                )
                # ⚠️ 立即 flush 确保后续查询能看到这条记录
                await session.flush()
            
            # 更新各内容项的状态
            if tutorial:
                await concept_crud.update_content_status(
                    session=session,
                    concept_id=concept_id,
                    content_type="tutorial",
                    status="completed" if tutorial_status == "success" else "failed",
                    content_id=tutorial.tutorial_id if tutorial_status == "success" else None,
                )
            
            if resource:
                await concept_crud.update_content_status(
                    session=session,
                    concept_id=concept_id,
                    content_type="resources",
                    status="completed" if resource_status == "success" else "failed",
                    content_id=resource.id if resource_status == "success" else None,
                )
            
            if quiz:
                await concept_crud.update_content_status(
                    session=session,
                    concept_id=concept_id,
                    content_type="quiz",
                    status="completed" if quiz_status == "success" else "failed",
                    content_id=quiz.quiz_id if quiz_status == "success" else None,
                )
            
            logger.info(
                "concept_metadata_status_updated",
                concept_id=concept_id,
                tutorial_status=tutorial_status,
                resource_status=resource_status,
                quiz_status=quiz_status,
            )
            
        except Exception as e:
            logger.error(
                "concept_metadata_update_failed",
                concept_id=concept_id,
                error=str(e),
                exc_info=True,
            )
        
        # ✅ 构造返回结果（ConceptContentSaveResult）
        save_result = ConceptContentSaveResult(
            concept_id=concept_id,
            tutorial=tutorial_status,
            tutorial_output=tutorial_output_dict,
            resource=resource_status,
            resource_output=resource_output_dict,
            quiz=quiz_status,
            quiz_output=quiz_output_dict,
            metadata_saved=metadata_saved,
        )
        
        logger.info(
            "concept_content_handler_completed",
            concept_id=concept_id,
            saved_count=saved_count,
            total_count=total_count,
            metadata_saved=metadata_saved,
        )
        
        return save_result

