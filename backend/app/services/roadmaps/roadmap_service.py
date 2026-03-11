"""
路线图生成服务

已重构：移除 RepositoryFactory 依赖，直接使用各个 CRUD 和 safe_session_with_retry()
"""
import uuid
import structlog

from app.models.domain import UserRequest, RoadmapFramework
from app.models.database import beijing_now
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.orchestrator.executor import WorkflowExecutor
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_tech_assessment import get_user_profile_crud
from app.services.shared.notification_service import notification_service
from app.schemas.task import TaskStatusDetailResponse
from app.schemas.roadmap import RoadmapDetail

logger = structlog.get_logger()


class RoadmapService:
    """路线图生成服务"""
    
    def __init__(self, orchestrator: "WorkflowExecutor"):
        """
        初始化路线图服务
        
        Args:
            orchestrator: 工作流执行器
        """
        self.orchestrator = orchestrator
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳（ISO 格式）"""
        return beijing_now().isoformat()
    
    @staticmethod
    async def _enrich_user_request_with_profile(user_request: UserRequest) -> UserRequest:
        """
        使用用户画像信息丰富用户请求（包括语言偏好）
        
        从数据库获取用户画像，将语言偏好注入到 LearningPreferences 中。
        
        Args:
            user_request: 原始用户请求
            
        Returns:
            丰富后的用户请求（包含语言偏好）
        """
        try:
            # 使用 CRUD 系统
            async with async_session_maker.begin() as session:
                user_profile_crud = get_user_profile_crud()
                user_profile = await user_profile_crud.get_by_user_id(session, user_request.user_id)
            
            if user_profile:
                # 创建更新后的偏好配置
                prefs_dict = user_request.preferences.model_dump()
                
                # 注入语言偏好（请求显式传入的值优先，画像仅作兜底）
                # 注意：primary_language 字段默认值为 "zh"，仅当请求未设置 preferred_language
                # 且 primary_language 仍为默认值时，才从画像补充；secondary_language 为 None 时才补充。
                # 与 industry/current_role 保持一致：请求有值则不覆盖。
                if not prefs_dict.get("preferred_language") and user_profile.primary_language:
                    prefs_dict["primary_language"] = user_profile.primary_language
                    prefs_dict["preferred_language"] = user_profile.primary_language
                
                if prefs_dict.get("secondary_language") is None and user_profile.secondary_language:
                    prefs_dict["secondary_language"] = user_profile.secondary_language
                
                # 注入其他用户画像信息（如果请求中没有提供）
                if not prefs_dict.get("industry") and user_profile.industry:
                    prefs_dict["industry"] = user_profile.industry
                if not prefs_dict.get("current_role") and user_profile.current_role:
                    prefs_dict["current_role"] = user_profile.current_role
                if not prefs_dict.get("tech_stack") and user_profile.tech_stack:
                    prefs_dict["tech_stack"] = user_profile.tech_stack
                
                # 重建 UserRequest
                from app.models.domain import LearningPreferences
                enriched_prefs = LearningPreferences.model_validate(prefs_dict)
                
                enriched_request = UserRequest(
                    user_id=user_request.user_id,
                    session_id=user_request.session_id,
                    preferences=enriched_prefs,
                    additional_context=user_request.additional_context,
                )
                
                logger.info(
                    "user_request_enriched_with_profile",
                    user_id=user_request.user_id,
                    primary_language=enriched_prefs.primary_language,
                    secondary_language=enriched_prefs.secondary_language,
                    has_industry=bool(enriched_prefs.industry),
                )
                
                return enriched_request
            
            logger.debug(
                "no_user_profile_found",
                user_id=user_request.user_id,
            )
            return user_request
            
        except Exception as e:
            logger.warning(
                "enrich_user_request_failed",
                user_id=user_request.user_id,
                error=str(e),
            )
            # 出错时返回原始请求
            return user_request
    
    async def generate_roadmap(
        self,
        user_request: UserRequest,
        task_id: str | None = None,
    ) -> dict:
        """
        生成学习路线图（已废弃）
        
        ⚠️ **已废弃**: 此方法已被移除，请使用新架构：
        
        正确的调用链：
        1. API Layer: 调用 GenerationService.create_and_verify_task()
        2. Service Layer: WorkflowExecutionService.execute_roadmap_workflow()
        3. Task Layer: Celery 异步执行
        
        Args:
            user_request: 用户请求
            task_id: 追踪 ID
            
        Raises:
            NotImplementedError: 此方法已被废弃
        """
        raise NotImplementedError(
            "RoadmapService.generate_roadmap() 已被完全移除。\n"
            "请使用新架构：\n"
            "1. GenerationService.create_and_verify_task() - 创建任务\n"
            "2. WorkflowExecutionService.execute_roadmap_workflow() - 执行工作流\n"
            "参考: doc/20260111_Service与Task层架构重构完成总结.md"
        )
    
    async def get_task_status(self, task_id: str) -> TaskStatusDetailResponse | None:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务状态 Schema，如果不存在则返回 None
        """
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
        
        if not task:
            return None
        
        # 如果任务正在处理中，从 AsyncPostgresSaver 获取实时状态
        current_step = task.current_step
        if task.status == "processing":
            try:
                realtime_step = await self._get_realtime_step_from_checkpointer(task_id)
                if realtime_step:
                    current_step = realtime_step
            except Exception as e:
                # 如果获取实时状态失败，使用数据库中的状态
                logger.warning(
                    "get_realtime_step_failed",
                    task_id=task_id,
                    error=str(e),
                )
        
        # 从 user_request JSON 中提取 turbo_mode（默认 True，与 UserRequest 模型默认值保持一致）
        user_request_data = task.user_request or {}
        turbo_mode = user_request_data.get("turbo_mode", True) if isinstance(user_request_data, dict) else True
        
        return TaskStatusDetailResponse(
            task_id=task.task_id,
            status=task.status,
            current_step=current_step,
            roadmap_id=task.roadmap_id,
            created_at=task.created_at.isoformat() if task.created_at else None,
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
            error_message=task.error_message,
            turbo_mode=turbo_mode,
            user_request=task.user_request if isinstance(task.user_request, dict) else None,
        )
    
    async def _get_realtime_step_from_checkpointer(self, task_id: str) -> str | None:
        """
        从 AsyncPostgresSaver 获取工作流的实时步骤
        
        Args:
            task_id: 任务 ID（同时也是 LangGraph 的 thread_id）
            
        Returns:
            当前步骤名称，如果获取失败则返回 None
        """
        try:
            config = {"configurable": {"thread_id": task_id}}
            checkpoint_tuple = await self.orchestrator.checkpointer.aget_tuple(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                current_step = channel_values.get("current_step")
                
                logger.debug(
                    "checkpointer_realtime_step",
                    task_id=task_id,
                    current_step=current_step,
                    has_channel_values=bool(channel_values),
                    channel_keys=list(channel_values.keys()) if channel_values else [],
                )
                
                return current_step
            else:
                logger.debug(
                    "checkpointer_no_checkpoint",
                    task_id=task_id,
                    has_tuple=checkpoint_tuple is not None,
                    has_checkpoint=checkpoint_tuple.checkpoint is not None if checkpoint_tuple else False,
                )
            
            return None
        except Exception as e:
            logger.warning(
                "checkpointer_get_step_failed",
                task_id=task_id,
                error=str(e),
            )
            return None
    
    async def get_roadmap(self, roadmap_id: str) -> RoadmapDetail | None:
        """
        获取完整的路线图数据（合并 concept_metadata 的 overall_status）
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            路线图框架字典（包含 concept_metadata 状态），如果不存在则返回 None
        """
        async with async_session_maker() as session:
            roadmap_crud = get_roadmap_crud()
            metadata = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
            
            if not metadata:
                return None
            
            # 获取所有 concept_metadata
            from app.crud.crud_concept import get_concept_crud
            concept_crud = get_concept_crud()
            concept_metas = await concept_crud.get_by_roadmap_id(session, roadmap_id)
        
        # 构建 concept_id -> ConceptMetadata 映射
        concept_meta_map = {cm.concept_id: cm for cm in concept_metas}
        
        # 从 JSON 数据重建 RoadmapFramework
        framework_data = metadata.framework_data.copy()
        
        # 合并 concept_metadata 的 overall_status 到 framework_data
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    if concept_id and concept_id in concept_meta_map:
                        concept_meta = concept_meta_map[concept_id]
                        # 使用 concept_metadata 中的真实状态覆盖 framework_data 中的状态
                        concept["content_status"] = concept_meta.tutorial_status
                        concept["resources_status"] = concept_meta.resources_status
                        concept["quiz_status"] = concept_meta.quiz_status
                        concept["overall_status"] = concept_meta.overall_status
                        
                        # 同时更新 ID 引用（确保一致性）
                        if concept_meta.tutorial_id:
                            concept["tutorial_id"] = concept_meta.tutorial_id
                        if concept_meta.resources_id:
                            concept["resources_id"] = concept_meta.resources_id
                        if concept_meta.quiz_id:
                            concept["quiz_id"] = concept_meta.quiz_id
        
        logger.info(
            "roadmap_enriched_with_concept_metadata",
            roadmap_id=roadmap_id,
            concept_count=len(concept_meta_map),
        )
        
        return RoadmapDetail(
            roadmap_id=metadata.roadmap_id,
            title=metadata.title,
            description=metadata.description,
            cover_image_url=metadata.cover_image_url,
            framework_data=framework_data,
            user_id=metadata.user_id,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
        )
    
    async def handle_human_review(
        self,
        task_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> dict:
        """
        处理人工审核结果（已废弃）
        
        ⚠️ **已废弃**: 此方法已被移除，请使用新架构：
        
        正确的调用链：
        1. API Layer: 触发人工审核恢复
        2. Task Layer: workflow_resume_tasks.resume_after_review()
        3. Service Layer: WorkflowExecutionService.resume_workflow_after_review()
        
        Args:
            task_id: 任务 ID
            approved: 是否批准
            feedback: 用户反馈
            
        Raises:
            NotImplementedError: 此方法已被废弃
        """
        raise NotImplementedError(
            "RoadmapService.handle_human_review() 已被完全移除。\n"
            "请使用新架构：\n"
            "1. 调用 Celery 任务: workflow_resume_tasks.resume_after_review()\n"
            "2. 底层执行: WorkflowExecutionService.resume_workflow_after_review()\n"
            "参考: doc/20260111_Service与Task层架构重构完成总结.md"
        )
