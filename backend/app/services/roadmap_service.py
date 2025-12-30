"""
路线图生成服务
"""
import uuid
import structlog

from app.models.domain import UserRequest, RoadmapFramework
from app.models.database import beijing_now
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory
from app.services.notification_service import notification_service

logger = structlog.get_logger()


class RoadmapService:
    """路线图生成服务"""
    
    def __init__(self, repo_factory: RepositoryFactory, orchestrator: WorkflowExecutor):
        self.repo_factory = repo_factory
        self.orchestrator = orchestrator
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳（ISO 格式）"""
        return beijing_now().isoformat()
    
    async def _enrich_user_request_with_profile(self, user_request: UserRequest) -> UserRequest:
        """
        使用用户画像信息丰富用户请求（包括语言偏好）
        
        从数据库获取用户画像，将语言偏好注入到 LearningPreferences 中。
        
        Args:
            user_request: 原始用户请求
            
        Returns:
            丰富后的用户请求（包含语言偏好）
        """
        try:
            # 使用新的Repository系统
            async with self.repo_factory.create_session() as session:
                user_profile_repo = self.repo_factory.create_user_profile_repo(session)
                user_profile = await user_profile_repo.get_by_user_id(user_request.user_id)
            
            if user_profile:
                # 创建更新后的偏好配置
                prefs_dict = user_request.preferences.model_dump()
                
                # 注入语言偏好（优先使用用户画像中的设置）
                if user_profile.primary_language:
                    prefs_dict["primary_language"] = user_profile.primary_language
                    # 向后兼容：同时设置 preferred_language
                    if not prefs_dict.get("preferred_language"):
                        prefs_dict["preferred_language"] = user_profile.primary_language
                
                if user_profile.secondary_language:
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
        生成学习路线图（异步任务）
        
        **已废弃**: 此方法已被 Celery 任务 `roadmap_generation_tasks.generate_roadmap` 替代。
        保留此方法仅用于向后兼容和测试目的。
        
        Args:
            user_request: 用户请求
            task_id: 追踪 ID（必须提供，由 API 层创建）
            
        Returns:
            包含 task_id 和初始状态的字典
        """
        # 使用用户画像丰富请求（注入语言偏好等）
        enriched_request = await self._enrich_user_request_with_profile(user_request)
        
        if task_id is None:
            task_id = str(uuid.uuid4())
            # 如果没有提供 task_id，则创建任务记录
            async with self.repo_factory.create_session() as session:
                task_repo = self.repo_factory.create_task_repo(session)
                await task_repo.create_task(
                    task_id=task_id,
                    user_id=enriched_request.user_id,
                    user_request=enriched_request.model_dump(mode='json'),
                )
                await session.commit()
        
        # 更新任务状态为处理中
        logger.info(
            "roadmap_service_starting",
            task_id=task_id,
            user_id=enriched_request.user_id,
            primary_language=enriched_request.preferences.primary_language,
            secondary_language=enriched_request.preferences.secondary_language,
        )
        
        async with self.repo_factory.create_session() as session:
            task_repo = self.repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="intent_analysis",
            )
            await session.commit()
        
        # 发布任务开始通知（WebSocket 会收到此事件）
        await notification_service.publish_progress(
            task_id=task_id,
            step="starting",
            status="processing",
            message="路线图生成任务已启动",
            extra_data={
                "learning_goal": enriched_request.preferences.learning_goal[:100],
                "primary_language": enriched_request.preferences.primary_language,
                "secondary_language": enriched_request.preferences.secondary_language,
            },
        )
        
        try:
            logger.info(
                "roadmap_service_executing_workflow",
                task_id=task_id,
            )
            
            # 执行工作流（使用丰富后的请求）
            final_state = await self.orchestrator.execute(
                enriched_request, task_id
            )
            
            # 检查工作流是否在 human_review 处被 interrupt() 暂停
            is_interrupted = "__interrupt__" in final_state
            current_step = final_state.get("current_step", "unknown")
            
            logger.info(
                "roadmap_service_workflow_returned",
                task_id=task_id,
                current_step=current_step,
                is_interrupted=is_interrupted,
                has_framework=bool(final_state.get("roadmap_framework")),
            )
            
            if is_interrupted:
                # 工作流在 human_review 处被中断，等待人工审核
                logger.info(
                    "roadmap_service_awaiting_human_review",
                    task_id=task_id,
                    interrupt_info=str(final_state.get("__interrupt__"))[:200],
                )
                
                # 先保存路线图框架（如果存在），方便用户审核
                if final_state.get("roadmap_framework"):
                    framework: RoadmapFramework = final_state["roadmap_framework"]
                    async with self.repo_factory.create_session() as session:
                        roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
                        await roadmap_repo.save_roadmap(
                            roadmap_id=framework.roadmap_id,
                            user_id=enriched_request.user_id,
                            framework=framework,
                        )
                        await session.commit()
                
                # 更新任务状态为等待人工审核
                async with self.repo_factory.create_session() as session:
                    task_repo = self.repo_factory.create_task_repo(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="human_review_pending",
                        current_step="human_review",
                        roadmap_id=final_state.get("roadmap_framework").roadmap_id if final_state.get("roadmap_framework") else None,
                    )
                    await session.commit()
                
                return {
                    "task_id": task_id,
                    "status": "human_review_pending",
                    "roadmap_id": final_state.get("roadmap_framework").roadmap_id if final_state.get("roadmap_framework") else None,
                    "message": "工作流已暂停，等待人工审核",
                }
            
            # ============================================================
            # 工作流正常完成
            # ============================================================
            # 注意：
            # - 内容元数据（tutorial/resource/quiz）已由 ContentRunner 
            #   通过 brain.save_content_results() 保存
            # - 任务状态已由 brain.save_content_results() 更新
            # - 完成通知已由 brain.save_content_results() 发布
            # - 此处只处理 framework 不存在的异常情况
            # ============================================================
            async with self.repo_factory.create_session() as session:
                if final_state.get("roadmap_framework"):
                    framework: RoadmapFramework = final_state["roadmap_framework"]
                    
                    # 获取内容生成结果（用于日志）
                    tutorial_refs = final_state.get("tutorial_refs", {})
                    failed_concept_ids = final_state.get("failed_concepts", [])
                    
                    logger.info(
                        "roadmap_service_workflow_completed",
                        task_id=task_id,
                        roadmap_id=framework.roadmap_id,
                        tutorial_count=len(tutorial_refs),
                        failed_count=len(failed_concept_ids),
                    )
                    
                    # 注意：完成通知已在 brain.save_content_results() 中发布
                    # 不再重复发布，避免前端收到多次完成事件
                else:
                    # 如果没有生成框架，标记为失败
                    task_repo = self.repo_factory.create_task_repo(session)
                    await task_repo.update_task_status(
                        task_id=task_id,
                        status="failed",
                        current_step="failed",
                        error_message="路线图框架生成失败",
                    )
                    await session.commit()
                    # 发布失败通知
                    await notification_service.publish_failed(
                        task_id=task_id,
                        error="路线图框架生成失败",
                    )
            
            logger.info("roadmap_generation_completed", task_id=task_id)
            
        except Exception as e:
            # 更新任务状态为失败
            async with self.repo_factory.create_session() as session:
                task_repo = self.repo_factory.create_task_repo(session)
                await task_repo.update_task_status(
                    task_id=task_id,
                    status="failed",
                    current_step="failed",
                    error_message=str(e),
                )
                await session.commit()
            # 发布失败通知
            await notification_service.publish_failed(
                task_id=task_id,
                error=str(e),
            )
            logger.error("roadmap_generation_failed", task_id=task_id, error=str(e))
            raise
        
        # 确定最终状态
        if not final_state.get("roadmap_framework"):
            final_status = "failed"
        elif final_state.get("failed_concepts"):
            final_status = "partial_failure"
        else:
            final_status = "completed"
        
        return {
            "task_id": task_id,
            "status": final_status,
            "roadmap_id": final_state.get("roadmap_framework").roadmap_id if final_state.get("roadmap_framework") else None,
            "failed_count": len(final_state.get("failed_concepts", [])),
        }
    
    async def get_task_status(self, task_id: str) -> dict | None:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务状态字典，如果不存在则返回 None
        """
        async with self.repo_factory.create_session() as session:
            task_repo = self.repo_factory.create_task_repo(session)
            task = await task_repo.get_by_task_id(task_id)
        
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
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "current_step": current_step,
            "roadmap_id": task.roadmap_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "error_message": task.error_message,
        }
    
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
    
    async def get_roadmap(self, roadmap_id: str) -> RoadmapFramework | None:
        """
        获取完整的路线图数据
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            路线图框架，如果不存在则返回 None
        """
        async with self.repo_factory.create_session() as session:
            roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
            metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
        
        if not metadata:
            return None
        
        # 从 JSON 数据重建 RoadmapFramework
        return RoadmapFramework.model_validate(metadata.framework_data)
    
    async def handle_human_review(  # DEPRECATED: 使用 workflow_resume_tasks.resume_after_review 替代
        self,
        task_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> dict:
        """
        处理人工审核结果（Human-in-the-Loop）
        
        Args:
            task_id: 任务 ID
            approved: 是否批准
            feedback: 用户反馈（如果未批准）
            
        Returns:
            处理结果
        """
        # 获取任务状态
        async with self.repo_factory.create_session() as session:
            task_repo = self.repo_factory.create_task_repo(session)
            task = await task_repo.get_by_task_id(task_id)
        
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        
        if task.status != "human_review_pending" or task.current_step != "human_review":
            raise ValueError(f"任务 {task_id} 当前不在人工审核阶段（当前状态: {task.status}, 步骤: {task.current_step}）")
        
        try:
            # 恢复工作流（使用 Command(resume=...) 继续执行）
            final_state = await self.orchestrator.resume_after_human_review(
                task_id=task_id,
                approved=approved,
                feedback=feedback,
            )
            
            # ============================================================
            # 人工审核后处理
            # ============================================================
            # 注意：内容元数据（tutorial/resource/quiz）已由 ContentRunner
            # 通过 brain.save_content_results() 保存，此处只保存非内容类元数据
            # ============================================================
            async with self.repo_factory.create_session() as session:
                if approved:
                    # 用户批准
                    if final_state.get("roadmap_framework"):
                        framework: RoadmapFramework = final_state["roadmap_framework"]
                        
                        # 注意：
                        # - 需求分析元数据已由 brain.save_intent_analysis() 在 intent_runner 中保存
                        # - 此处需要判断内容生成是否已启动
                        
                        # 检查内容生成状态
                        content_generation_status = final_state.get("content_generation_status")
                        celery_task_id = final_state.get("celery_task_id")
                        
                        # 调试：输出 final_state 的关键字段
                        logger.info(
                            "human_review_checking_content_generation_status",
                            task_id=task_id,
                            roadmap_id=framework.roadmap_id,
                            content_generation_status=content_generation_status,
                            celery_task_id=celery_task_id,
                            has_tutorial_refs=bool(final_state.get("tutorial_refs")),
                            current_step=final_state.get("current_step"),
                        )
                        
                        if content_generation_status == "queued" and celery_task_id:
                            # 内容生成任务已发送到 Celery，正在异步执行中
                            # 不要标记为 completed，等待 Celery 任务完成后更新状态
                            logger.info(
                                "human_review_content_generation_queued",
                                task_id=task_id,
                                roadmap_id=framework.roadmap_id,
                                celery_task_id=celery_task_id,
                            )
                            # 任务状态会由 Celery 任务完成后更新，此处不做任何操作
                        elif not final_state.get("tutorial_refs"):
                            # 工作流未执行内容生成（可能是跳过了），需要手动更新状态
                            task_repo = self.repo_factory.create_task_repo(session)
                            await task_repo.update_task_status(
                                task_id=task_id,
                                status="completed",
                                current_step="completed",
                                roadmap_id=framework.roadmap_id,
                            )
                            await session.commit()
                            
                            # 手动发布完成通知（因为 ContentRunner 未执行）
                            await notification_service.publish_completed(
                                task_id=task_id,
                                roadmap_id=framework.roadmap_id,
                                tutorials_count=0,
                                failed_count=0,
                            )
                            
                            logger.info(
                                "human_review_completed_without_content",
                                task_id=task_id,
                                roadmap_id=framework.roadmap_id,
                            )
                        else:
                            # 正常情况：完成通知已在 brain.save_content_results() 中发布
                            tutorial_refs = final_state.get("tutorial_refs", {})
                            failed_concepts = final_state.get("failed_concepts", [])
                            
                            logger.info(
                                "human_review_workflow_completed",
                                task_id=task_id,
                                roadmap_id=framework.roadmap_id,
                                tutorials_count=len(tutorial_refs),
                                failed_count=len(failed_concepts),
                            )
                    else:
                        # 如果没有生成框架，标记为失败
                        task_repo = self.repo_factory.create_task_repo(session)
                        await task_repo.update_task_status(
                            task_id=task_id,
                            status="failed",
                            current_step="failed",
                            error_message="路线图框架生成失败",
                        )
                        await session.commit()
                        
                        # 发布失败通知
                        await notification_service.publish_failed(
                            task_id=task_id,
                            error="路线图框架生成失败",
                        )
                else:
                    # 用户拒绝：工作流会进入 edit_plan_analysis → roadmap_edit → human_review 修改分支
                    # 注意：不再需要手动更新 current_step
                    # - 工作流节点会通过 WorkflowBrain.node_execution() 自动更新状态
                    # - 如果在这里错误地设置 current_step，会导致数据库状态与实际工作流状态不一致
                    # 
                    # 原代码（已删除）：
                    # await task_repo.update_task_status(
                    #     task_id=task_id,
                    #     status="processing",
                    #     current_step="curriculum_design",  # ❌ 旧逻辑，不再适用
                    # )
                    pass  # 工作流会自动管理状态
            
            logger.info(
                "human_review_processed",
                task_id=task_id,
                approved=approved,
            )
            
            return {
                "task_id": task_id,
                "approved": approved,
                "message": "审核结果已提交，工作流将继续执行" if approved else "已记录修改要求，将根据反馈修改路线图",
            }
            
        except Exception as e:
            logger.error("human_review_processing_failed", task_id=task_id, error=str(e))
            raise
