"""
工作流执行服务

负责完整的工作流执行业务逻辑，被 Celery 任务层调用。

架构重构说明：
- 旧架构：Celery Task 层直接实现业务逻辑（重复代码严重）
- 新架构：业务逻辑集中在 Service 层，Task 层仅负责异步调度

职责边界：
- Service 层：业务逻辑编排、状态管理、数据持久化、通知发送
- Task 层：异步任务调度、事件循环管理
"""
import asyncio
import time
import structlog
from typing import Optional
from datetime import datetime

from app.core.orchestrator_factory import OrchestratorFactory
from app.services.shared.notification_service import notification_service
from app.models.constants import TaskStatus, WorkflowStep
from app.models.domain import UserRequest, LearningPreferences
from app.db.celery_session import get_celery_session
from app.crud.crud_task import get_task_crud

logger = structlog.get_logger()


class WorkflowExecutionService:
    """
    工作流执行服务
    
    负责处理工作流的完整执行业务逻辑。
    """
    
    async def execute_roadmap_workflow(
        self,
        task_id: str,
        user_request: str,
        user_id: str,
        learning_preferences: Optional[dict],
        celery_task_id: str,
    ) -> dict:
        """
        执行路线图生成工作流
        
        完整的业务逻辑流程：
        1. 验证任务记录是否存在
        2. 更新任务状态为 processing
        3. 发送 WebSocket 通知
        4. 创建 OrchestratorFactory
        5. 执行工作流
        6. 判断最终状态（完成/人工审核/部分失败）
        7. 返回执行结果
        
        Args:
            task_id: 任务 ID
            user_request: 用户请求描述
            user_id: 用户 ID
            learning_preferences: 学习偏好（字典格式）
            celery_task_id: Celery 任务 ID
            
        Returns:
            dict: 执行结果
                - success: bool
                - roadmap_id: str（如果成功）
                - status: str（任务最终状态）
                - current_step: str
        """
        factory = None
        
        try:
            # ===== 步骤1: 验证任务记录是否存在 =====
            task_crud = get_task_crud()
            async with get_celery_session() as session:
                task = await task_crud.get_by_task_id(session, task_id)
                if not task:
                    error_msg = f"Task {task_id} not found in database"
                    logger.error("task_not_found", task_id=task_id)
                    raise ValueError(error_msg)
                
                logger.info(
                    "task_record_found",
                    task_id=task_id,
                    task_status=task.status,
                )
                
                # ===== 协作式取消检查：任务在入队期间已被取消 =====
                # 场景：用户在任务还在队列中等待时点击取消，cancel_task 将状态
                # 标记为 cancelled，此时任务被 revoke（但 revoke 只阻止未开始
                # 的任务）。若 worker 已经 dequeue 到任务但尚未开始，需在此处
                # 拦截，避免无意义地继续执行。
                if task.status == TaskStatus.CANCELLED.value:
                    logger.info(
                        "task_already_cancelled_before_start",
                        task_id=task_id,
                    )
                    return {
                        "success": False,
                        "status": TaskStatus.CANCELLED.value,
                        "current_step": task.current_step or WorkflowStep.QUEUED.value,
                        "error": "Task was cancelled before execution started",
                    }
            
            # ===== 步骤2: 更新任务状态为 processing =====
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step=WorkflowStep.QUEUED.value,
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # ===== 步骤3: 发送 WebSocket 通知 =====
            await notification_service.publish_progress(
                task_id=task_id,
                step=WorkflowStep.QUEUED.value,
                status=TaskStatus.PROCESSING.value,
            )
            
            # ===== 步骤4: 创建 Orchestrator Factory =====
            factory = OrchestratorFactory()
            await factory.initialize()
            
            # 创建工作流执行器
            executor = factory.create_workflow_executor()
            
            # ===== 步骤5: 构造 UserRequest 对象 =====
            user_request_obj = UserRequest(
                user_id=user_id,
                session_id=task_id,  # 使用 task_id 作为 session_id
                preferences=LearningPreferences(**learning_preferences) if learning_preferences else LearningPreferences(
                    learning_goal=user_request,
                    available_hours_per_week=10,
                    motivation="Personal interest",
                    current_level="beginner",
                    career_background="Not specified",
                ),
                additional_context=user_request,
            )
            
            # ===== 步骤5.5: 注入用户画像数据 =====
            # 从数据库加载用户画像并丰富 UserRequest
            from app.services.roadmaps.roadmap_service import RoadmapService
            user_request_obj = await RoadmapService._enrich_user_request_with_profile(user_request_obj)
            
            logger.info(
                "user_request_enriched",
                task_id=task_id,
                has_industry=bool(user_request_obj.preferences.industry),
                has_current_role=bool(user_request_obj.preferences.current_role),
                has_tech_stack=bool(user_request_obj.preferences.tech_stack),
            )
            
            # ===== 步骤6: 执行工作流 =====
            final_state = await executor.execute(
                user_request=user_request_obj,
                task_id=task_id,
            )
            
            # ===== 步骤7: 判断最终状态 =====
            roadmap_id = final_state.get("roadmap_id")
            current_step = final_state.get("current_step", WorkflowStep.COMPLETED.value)
            
            # 判断任务状态
            if current_step == WorkflowStep.HUMAN_REVIEW.value:
                # 工作流在人工审核处暂停
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == WorkflowStep.CONTENT_GENERATION_QUEUED.value:
                # ✅ 主工作流完成，内容生成已入队（独立 Worker 执行）
                # 这种情况不应该在 execute_workflow 中出现，仅在 resume_after_review 中
                status = TaskStatus.PROCESSING
                success = True
                logger.info(
                    "main_workflow_completed_content_queued_from_execute",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    current_step=current_step,
                    message="主工作流完成，内容生成已入队（独立 Worker 执行）",
                )
            elif current_step == WorkflowStep.STRUCTURE_VALIDATION.value and roadmap_id:
                # ✅ 主工作流在验证阶段正常结束
                # 场景1: 验证通过且SKIP_HUMAN_REVIEW=true
                # 场景2: 验证失败但达到最大重试次数且SKIP_HUMAN_REVIEW=true
                # 此时路线图框架已生成并保存，主工作流正常完成
                # TaskStatus应保持为PROCESSING（等待内容生成），不是COMPLETED
                status = TaskStatus.PROCESSING
                success = True
                logger.info(
                    "framework_generation_completed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    current_step=current_step,
                    message="主工作流完成（框架已生成），等待内容生成",
                )
            elif current_step == WorkflowStep.COMPLETED.value:
                # 整体任务完成（框架 + 内容生成都完成）
                status = TaskStatus.COMPLETED
                success = True
                logger.info(
                    "workflow_completed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            else:
                # 其他情况视为异常中断
                status = TaskStatus.PARTIAL_FAILURE
                success = False
                logger.warning(
                    "workflow_incomplete",
                    task_id=task_id,
                    current_step=current_step,
                    roadmap_id=roadmap_id,
                )
            
            roadmap_framework = final_state.get("roadmap_framework")
            roadmap_title = roadmap_framework.title if roadmap_framework else None
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
                "roadmap_title": roadmap_title,
                "status": status.value,
                "current_step": current_step,
            }
            
        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持
        # 只在应用关闭时清理（main.py 的 shutdown 事件）
    
    async def update_task_final_status(
        self,
        task_id: str,
        result: dict,
    ):
        """
        更新任务最终状态
        
        关键修复：Celery 任务执行完成后，必须更新数据库中的任务状态，
        否则前端会持续轮询状态而无法获取最终结果。
        
        Args:
            task_id: 任务 ID
            result: 执行结果字典
        """
        try:
            task_crud = get_task_crud()
            async with get_celery_session() as session:
                # 更新任务状态和 roadmap_id
                task = await task_crud.get_by_task_id(session, task_id)
                if task:
                    task.status = result.get("status", TaskStatus.COMPLETED.value)
                    task.current_step = result.get("current_step", WorkflowStep.COMPLETED.value)
                    task.roadmap_id = result.get("roadmap_id")
                    session.add(task)
                    # ✅ 不需要手动 commit，get_celery_session() 自动处理
                    
                    logger.info(
                        "task_final_status_updated",
                        task_id=task_id,
                        status=task.status,
                        roadmap_id=task.roadmap_id,
                    )
                else:
                    logger.error(
                        "task_not_found_for_status_update",
                        task_id=task_id,
                    )
        except Exception as e:
            logger.error(
                "failed_to_update_task_final_status",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
    
    async def mark_task_failed(
        self,
        task_id: str,
        error_message: str,
        exception: Exception | None = None,
    ):
        """
        标记任务为失败状态（简化版 - 委托给协调器）
        
        ⚠️ 重构说明：
        此方法现在委托给 SideEffectCoordinator.on_workflow_failed()
        保留此方法是为了兼容现有调用，未来可能移除。
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
            exception: 原始异常对象（可选）
        """
        try:
            # 委托给协调器（统一管理所有副作用）
            from app.core.orchestrator_factory import OrchestratorFactory
            
            # ✅ 确保工厂已初始化（Celery Worker 进程隔离）
            if not OrchestratorFactory._initialized:
                await OrchestratorFactory.initialize()
                logger.info(
                    "orchestrator_factory_initialized_in_error_handler",
                    task_id=task_id,
                )
            
            # 获取协调器实例
            # 注意：这是一个临时方案，未来应该直接注入协调器
            executor = OrchestratorFactory.create_workflow_executor()
            coordinator = executor.coordinator
            
            # 调用协调器处理失败
            await coordinator.on_workflow_failed(
                task_id=task_id,
                error=exception if exception else Exception(error_message),
            )
            
        except Exception as e:
            logger.error(
                "failed_to_mark_task_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
    
    async def resume_workflow_after_review(
        self,
        task_id: str,
        approved: bool,
        feedback: Optional[str],
        celery_task_id: str,
    ) -> dict:
        """
        人工审核后恢复工作流
        
        Args:
            task_id: 任务 ID
            approved: 用户是否批准
            feedback: 用户反馈
            celery_task_id: Celery 任务 ID
            
        Returns:
            dict: 执行结果
        """
        factory = None
        
        try:
            t_service_start = time.time()
            logger.info(
                "resume_workflow_after_review_service_start",
                task_id=task_id,
                approved=approved,
            )

            # 更新任务状态为 processing
            # ⚠️ 性能瓶颈点①：get_celery_session 使用 NullPool，每次都需要建立新 TCP 连接
            task_crud = get_task_crud()
            t_db_start = time.time()
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step=WorkflowStep.STARTING.value,
                )
            logger.info(
                "resume_db_status_update_done",
                task_id=task_id,
                duration_ms=int((time.time() - t_db_start) * 1000),
            )
            
            # 发送 WebSocket 通知
            t_ws_start = time.time()
            await notification_service.publish_progress(
                task_id=task_id,
                step=WorkflowStep.STARTING.value,
                status=TaskStatus.PROCESSING.value,
                message="Resuming workflow after review...",
            )
            logger.info(
                "resume_ws_notification_sent",
                task_id=task_id,
                duration_ms=int((time.time() - t_ws_start) * 1000),
            )
            
            # 创建 Orchestrator Factory
            t_factory_start = time.time()
            factory = OrchestratorFactory()
            await factory.initialize()
            logger.info(
                "resume_factory_initialized",
                task_id=task_id,
                duration_ms=int((time.time() - t_factory_start) * 1000),
            )
            
            # 创建工作流执行器
            executor = factory.create_workflow_executor()
            logger.info(
                "resume_pre_executor_total",
                task_id=task_id,
                total_duration_ms=int((time.time() - t_service_start) * 1000),
            )
            
            # 从 checkpoint 恢复工作流（人工审核后）
            # ✅ 添加重试机制（应对阿里云RDS网络抖动）
            max_retries = 3
            retry_delay = 5  # 秒
            
            for attempt in range(max_retries):
                try:
                    final_state = await executor.resume_after_human_review(
                        task_id=task_id,
                        approved=approved,
                        feedback=feedback,
                    )
                    break  # 成功则跳出循环
                except Exception as e:
                    error_msg = str(e)
                    is_timeout = "timeout" in error_msg.lower() or "could not receive data" in error_msg.lower()
                    
                    if is_timeout and attempt < max_retries - 1:
                        logger.warning(
                            "resume_workflow_retry",
                            task_id=task_id,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error=error_msg,
                            retry_in_seconds=retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                        continue  # 重试
                    else:
                        # 最后一次失败或非超时错误，抛出异常
                        raise
            
            # 检查最终状态
            roadmap_id = final_state.get("roadmap_id")
            current_step = final_state.get("current_step", WorkflowStep.CONTENT_GENERATION_QUEUED.value)
            human_approved = final_state.get("human_approved", False)
            
            # 判断任务状态（优先检查 human_approved 标志）
            if current_step == WorkflowStep.HUMAN_REVIEW.value and not human_approved:
                # 用户拒绝后，工作流再次暂停在人工审核
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review_again",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == WorkflowStep.CONTENT_GENERATION_QUEUED.value or human_approved:
                # ✅ 批准后主工作流结束，内容生成已入队（独立 Celery Worker）
                # ⚠️ 任务状态为 PROCESSING（等待内容生成），不是 COMPLETED
                status = TaskStatus.PROCESSING
                success = True
                logger.info(
                    "main_workflow_completed_content_queued",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    approved=human_approved,
                    current_step=current_step,
                    message="主工作流完成，内容生成已入队（独立 Worker 执行）",
                )
            else:
                # 其他情况视为部分完成
                status = TaskStatus.PARTIAL_FAILURE
                success = False
                logger.warning(
                    "workflow_incomplete_after_review",
                    task_id=task_id,
                    current_step=current_step,
                )
            
            roadmap_framework = final_state.get("roadmap_framework")
            roadmap_title = roadmap_framework.title if roadmap_framework else None
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
                "roadmap_title": roadmap_title,
                "status": status.value,
                "current_step": current_step,
            }
            
        except Exception as e:
            logger.error(
                "resume_after_review_execution_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持
        # 只在应用关闭时清理（main.py 的 shutdown 事件）
    
    async def resume_workflow_from_checkpoint(
        self,
        task_id: str,
        celery_task_id: str,
        checkpoint_id: Optional[str] = None,
    ) -> dict:
        """
        从 checkpoint 恢复工作流
        
        支持两种模式：
        1. 断点续传（checkpoint_id=None）：从最后一个checkpoint恢复
        2. 时间旅行（checkpoint_id指定）：从特定checkpoint恢复
        
        Args:
            task_id: 任务 ID
            celery_task_id: Celery 任务 ID
            checkpoint_id: 可选的checkpoint ID（用于时间旅行）
            
        Returns:
            dict: 执行结果
        """
        factory = None
        mode = "time_travel" if checkpoint_id else "resume"
        
        try:
            # 更新任务状态为 processing
            # ⚠️ 不传 current_step，保留 DB 中已有的步骤值（如 content_generation_queued）
            # 避免在内容生成重试场景中错误地将步骤覆盖为 "starting"
            task_crud = get_task_crud()
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # 发送 WebSocket 通知
            message = (
                f"Time Travel: Resuming from checkpoint {checkpoint_id[:8]}..."
                if checkpoint_id
                else "Resuming workflow from last checkpoint..."
            )
            await notification_service.publish_progress(
                task_id=task_id,
                step="resume_from_checkpoint",
                status=TaskStatus.PROCESSING.value,
                message=message,
                extra_data={"mode": mode, "checkpoint_id": checkpoint_id},
            )
            
            # 创建 Orchestrator Factory
            factory = OrchestratorFactory()
            await factory.initialize()
            
            # 创建工作流执行器
            executor = factory.create_workflow_executor()
            
            # 从 checkpoint 恢复工作流
            config = {"configurable": {"thread_id": task_id}}
            
            # 如果提供了checkpoint_id，添加到config（时间旅行模式）
            if checkpoint_id:
                config["configurable"]["checkpoint_id"] = checkpoint_id
                logger.info(
                    "time_travel_mode_enabled",
                    task_id=task_id,
                    checkpoint_id=checkpoint_id,
                )
            
            # ===== 关键：检测 checkpoint 是否存在 =====
            # 若任务在 starting 阶段失败，LangGraph 从未写入 checkpoint，
            # 此时 ainvoke(None) 会抛出 EmptyInputError，必须走全新执行路径。
            main_checkpoint = await executor.graph.aget_state(config)
            has_checkpoint = main_checkpoint is not None and bool(main_checkpoint.values)
            
            if not has_checkpoint:
                logger.info(
                    "no_checkpoint_found_falling_back_to_fresh_start",
                    task_id=task_id,
                    message="任务在 starting 阶段失败，无 checkpoint，重新全量执行",
                )
                # 从数据库读取原始 user_request，重建 UserRequest 对象
                async with get_celery_session() as session:
                    task_crud = get_task_crud()
                    task_record = await task_crud.get_by_task_id(session, task_id)
                
                if not task_record or not task_record.user_request:
                    raise ValueError(f"任务 {task_id} 没有存储 user_request，无法重新执行")
                
                req_data = task_record.user_request
                prefs_data = req_data.get("preferences", {})
                user_request_obj = UserRequest(
                    user_id=req_data.get("user_id", ""),
                    session_id=req_data.get("session_id", task_id),
                    preferences=LearningPreferences(**prefs_data) if prefs_data else LearningPreferences(
                        learning_goal=req_data.get("additional_context", ""),
                        available_hours_per_week=10,
                        motivation="Personal interest",
                        current_level="beginner",
                        career_background="Not specified",
                    ),
                    additional_context=req_data.get("additional_context"),
                )
                final_state = await executor.execute(
                    user_request=user_request_obj,
                    task_id=task_id,
                )
            else:
                # checkpoint 存在，从主图断点续传
                # 内容生成子图已移除 checkpointer（无状态模式），
                # 子图重试逻辑由 _get_framework_and_concepts_optimized 通过
                # Redis → 主图 Checkpoint → DB 三级策略自动处理
                logger.info(
                    "resuming_from_main_graph_checkpoint",
                    task_id=task_id,
                    mode=mode,
                )
                final_state = await executor.graph.ainvoke(None, config=config)
            
            # 检查最终状态
            roadmap_id = final_state.get("roadmap_id")
            current_step = final_state.get("current_step", WorkflowStep.COMPLETED.value)
            
            # 判断任务状态
            if current_step == WorkflowStep.HUMAN_REVIEW.value:
                # 工作流在人工审核处暂停
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review_from_checkpoint",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == WorkflowStep.COMPLETED.value:
                # 工作流完成
                status = TaskStatus.COMPLETED
                success = True
                logger.info(
                    "workflow_completed_from_checkpoint",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step in (
                WorkflowStep.CONTENT_GENERATION_QUEUED.value,
                WorkflowStep.CONTENT_GENERATION.value,
            ):
                # 内容生成已入队或进行中：主工作流已完成，独立 Celery Worker 负责后续
                # 此时任务保持 PROCESSING 状态，由内容生成任务更新最终状态
                status = TaskStatus.PROCESSING
                success = True
                logger.info(
                    "resume_triggered_content_generation",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    current_step=current_step,
                    message="内容生成已重新入队，等待独立 Worker 执行",
                )
            else:
                # 其他情况视为部分完成
                status = TaskStatus.PARTIAL_FAILURE
                success = False
                logger.warning(
                    "workflow_incomplete_from_checkpoint",
                    task_id=task_id,
                    current_step=current_step,
                )
            
            roadmap_framework = final_state.get("roadmap_framework")
            roadmap_title = roadmap_framework.title if roadmap_framework else None
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
                "roadmap_title": roadmap_title,
                "status": status.value,
                "current_step": current_step,
            }
            
        except Exception as e:
            logger.error(
                "resume_from_checkpoint_execution_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise
            
        # ⚠️ 不要在这里清理 Factory！
        # OrchestratorFactory 是全局单例，应该在应用生命周期内保持
        # 只在应用关闭时清理（main.py 的 shutdown 事件）


# 依赖注入工厂
def get_workflow_execution_service() -> WorkflowExecutionService:
    """获取 WorkflowExecutionService 实例（依赖注入）"""
    return WorkflowExecutionService()

