"""
内容生成Handler

处理ContentNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_tutorial import get_tutorial_crud
from app.crud.crud_resource import get_resource_crud
from app.crud.crud_quiz import get_quiz_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_task import get_task_crud
from app.schemas.handler_io import ContentHandlerInput

logger = structlog.get_logger()


class ContentHandler(NodeOutputHandler[ContentHandlerInput]):
    """
    内容生成汇总 Handler（重构版）
    
    职责（重构后）：
    1. 汇总所有 Concept 的保存结果
    2. 统一更新整个 Framework（批量）
    3. 更新 Task 最终状态
    4. 发送工作流完成通知
    
    不再负责：
    - 保存单个元数据（由 ConceptContentHandler 负责）
    
    向后兼容：
    - 保留原有的 _handle_output 方法用于 legacy 流程
    - 新流程使用 update_framework_batch 方法
    """
    
    input_model_class = ContentHandlerInput
    
    def get_node_name(self) -> str:
        return "content_generation"
    
    async def _handle_output(
        self,
        output: ContentHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理内容生成输出（具体实现）
        
        Args:
            output: 内容生成 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        # 新架构：使用 update_framework_batch 方法
        roadmap_id = output.roadmap_id
        concept_results = output.concept_results
        
        # 直接调用 update_framework_batch 方法
        await self.update_framework_batch(
            session=session,
            roadmap_id=roadmap_id,
            concept_results=concept_results,
        )
        
        # 更新 Task 最终状态
        all_saved = all(
            result.get("save_status", {}).get("metadata_saved", False)
            for result in concept_results
        )
        final_status = "completed" if all_saved else "partial_failure"
        
        await self.update_task_final_status(
            session=session,
            task_id=task_id,
            status=final_status,
        )
        
        return None
    
    async def on_complete(
        self,
        task_id: str,
        output: dict,
        duration_ms: int,
    ) -> None:
        """
        内容生成完成后的处理
        
        发送工作流完成通知
        """
        await super().on_complete(task_id, output, duration_ms)
        
        # 发送工作流完成通知
        roadmap_id = output.get("roadmap_id")
        tutorial_refs = output.get("tutorial_refs", {})
        failed_concepts = output.get("failed_concepts", [])
        
        await self.notification_service.publish_completed(
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorials_count=len(tutorial_refs),
            failed_count=len(failed_concepts),
        )
    
    def _update_framework_with_content_refs(
        self,
        framework_data: dict,
        tutorial_refs: dict,
        resource_refs: dict,
        quiz_refs: dict,
        failed_concepts: list,
    ) -> dict:
        """
        更新framework中所有Concept的内容引用字段
        
        Args:
            framework_data: 原始framework字典
            tutorial_refs: 教程引用字典
            resource_refs: 资源引用字典
            quiz_refs: 测验引用字典
            failed_concepts: 失败的概念ID列表
        
        Returns:
            更新后的framework字典
        """
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    if not concept_id:
                        continue
                    
                    # 更新教程相关字段
                    if concept_id in tutorial_refs:
                        tutorial_output = tutorial_refs[concept_id]  # ← dict (已序列化)
                        concept["content_status"] = "completed"
                        concept["tutorial_id"] = tutorial_output.get("tutorial_id")
                        concept["content_ref"] = tutorial_output.get("content_url")
                        concept["content_summary"] = tutorial_output.get("summary")
                    elif concept_id in failed_concepts:
                        if "content_status" not in concept or concept["content_status"] == "pending":
                            concept["content_status"] = "failed"
                    
                    # 更新资源相关字段
                    if concept_id in resource_refs:
                        resource_output = resource_refs[concept_id]  # ← dict (已序列化)
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource_output.get("id")
                        concept["resources_count"] = len(resource_output.get("resources", []))
                    elif concept_id in failed_concepts:
                        if "resources_status" not in concept or concept["resources_status"] == "pending":
                            concept["resources_status"] = "failed"
                    
                    # 更新测验相关字段
                    if concept_id in quiz_refs:
                        quiz_output = quiz_refs[concept_id]  # ← dict (已序列化)
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz_output.get("quiz_id")
                        concept["quiz_questions_count"] = quiz_output.get("total_questions")
                    elif concept_id in failed_concepts:
                        if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                            concept["quiz_status"] = "failed"
        
        return framework_data
    
    # ========== 新增方法：用于两层 Fan-Out/Fan-In 架构 ==========
    
    async def update_framework_batch(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_results: list[dict],
    ) -> None:
        """
        批量更新 Framework 中所有 Concept 的引用（重构版）
        
        此方法用于新的两层 Fan-Out/Fan-In 架构。
        单个 Concept 的元数据已在子图的 Fan-In 节点中保存，
        此方法只负责批量更新 Framework。
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            concept_results: 所有 Concept 的保存结果列表
        """
        roadmap_crud = get_roadmap_crud()
        roadmap_metadata = await roadmap_crud.get_by_roadmap_id(
            session,
            roadmap_id,
        )
        
        if not roadmap_metadata or not roadmap_metadata.framework_data:
            logger.warning(
                "framework_update_skipped_no_data",
                roadmap_id=roadmap_id,
            )
            return
        
        # 构建引用字典
        tutorial_refs = {}
        resource_refs = {}
        quiz_refs = {}
        failed_concepts = []
        
        for result in concept_results:
            save_status = result.get("save_status", {})
            concept_id = save_status.get("concept_id")
            
            if not concept_id:
                continue
            
            # 构建引用字典
            if save_status.get("tutorial") == "success":
                tutorial_refs[concept_id] = save_status.get("tutorial_output")
            
            if save_status.get("resource") == "success":
                resource_refs[concept_id] = save_status.get("resource_output")
            
            if save_status.get("quiz") == "success":
                quiz_refs[concept_id] = save_status.get("quiz_output")
            
            # 记录失败的 Concept
            if not save_status.get("metadata_saved", False):
                failed_concepts.append(concept_id)
        
        logger.info(
            "framework_batch_update_started",
            roadmap_id=roadmap_id,
            tutorial_count=len(tutorial_refs),
            resource_count=len(resource_refs),
            quiz_count=len(quiz_refs),
            failed_count=len(failed_concepts),
        )
        
        # 更新 Framework
        updated_framework = self._update_framework_with_content_refs(
            framework_data=roadmap_metadata.framework_data,
            tutorial_refs=tutorial_refs,
            resource_refs=resource_refs,
            quiz_refs=quiz_refs,
            failed_concepts=failed_concepts,
        )
        
        from app.models.domain import RoadmapFramework
        framework_obj = RoadmapFramework.model_validate(updated_framework)
        
        
        await roadmap_crud.save_roadmap_metadata(
            session=session,
            roadmap_id=roadmap_id,
            user_id=roadmap_metadata.user_id,
            framework=framework_obj,
        )
        
        logger.info(
            "framework_batch_update_completed",
            roadmap_id=roadmap_id,
        )
    
    async def update_task_final_status(
        self,
        session: AsyncSession,
        task_id: str,
        status: str,
    ) -> None:
        """
        更新 Task 最终状态
        
        Args:
            session: 数据库会话
            task_id: 任务 ID
            status: 最终状态（completed/partial_failure）
        """
        task_crud = get_task_crud()
        
        final_step = "completed" if status == "completed" else "content_generation"
        
        await task_crud.update_task_status(
            session=session,
            task_id=task_id,
            status=status,
            current_step=final_step,
        )
        
        logger.info(
            "task_final_status_updated",
            task_id=task_id,
            status=status,
            final_step=final_step,
        )

