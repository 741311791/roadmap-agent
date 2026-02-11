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
import structlog
from typing import Optional
from datetime import datetime

from app.core.orchestrator_factory import OrchestratorFactory
from app.services.shared.notification_service import notification_service
from app.models.constants import TaskStatus
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
            
            # ===== 步骤2: 更新任务状态为 processing =====
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step="queued",
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # ===== 步骤3: 发送 WebSocket 通知 =====
            await notification_service.publish_progress(
                task_id=task_id,
                step="queued",
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
            current_step = final_state.get("current_step", "completed")
            
            # 判断任务状态
            if current_step == "human_review":
                # 工作流在人工审核处暂停
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == "completed":
                # 工作流完成
                status = TaskStatus.COMPLETED
                success = True
                logger.info(
                    "workflow_completed",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            else:
                # 其他情况视为部分完成
                status = TaskStatus.PARTIAL_FAILURE
                success = False
                logger.warning(
                    "workflow_incomplete",
                    task_id=task_id,
                    current_step=current_step,
                )
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
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
            
        finally:
            # 清理 Orchestrator Factory
            if factory:
                await factory.cleanup()
    
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
                    task.current_step = result.get("current_step", "completed")
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
            # 更新任务状态为 processing
            task_crud = get_task_crud()
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step="resuming",
                )
                # ✅ 不需要手动 commit，get_celery_session() 自动处理
            
            # 发送 WebSocket 通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="resuming",
                status=TaskStatus.PROCESSING.value,
                message="Resuming workflow after review...",
            )
            
            # 创建 Orchestrator Factory
            factory = OrchestratorFactory()
            await factory.initialize()
            
            # 创建工作流执行器
            executor = factory.create_workflow_executor()
            
            # 从 checkpoint 恢复工作流（人工审核后）
            final_state = await executor.resume_after_human_review(
                task_id=task_id,
                approved=approved,
                feedback=feedback,
            )
            
            # 检查最终状态
            roadmap_id = final_state.get("roadmap_id")
            current_step = final_state.get("current_step", "completed")
            
            # 判断任务状态
            if current_step == "human_review":
                # 用户拒绝后，工作流再次暂停在人工审核
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review_again",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == "completed":
                # 工作流完成
                status = TaskStatus.COMPLETED
                success = True
                logger.info(
                    "workflow_completed_after_review",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
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
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
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
            
        finally:
            # 清理 Orchestrator Factory
            if factory:
                await factory.cleanup()
    
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
            task_crud = get_task_crud()
            async with get_celery_session() as session:
                await task_crud.update_task_status(
                    session=session,
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    current_step="resuming",
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
                step="resuming",
                status=TaskStatus.PROCESSING.value,
                message=message,
                details={"mode": mode, "checkpoint_id": checkpoint_id},
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
            
            # 直接调用 graph.ainvoke，不传入初始状态
            final_state = await executor.graph.ainvoke(None, config=config)
            
            # 检查最终状态
            roadmap_id = final_state.get("roadmap_id")
            current_step = final_state.get("current_step", "completed")
            
            # 判断任务状态
            if current_step == "human_review":
                # 工作流在人工审核处暂停
                status = TaskStatus.HUMAN_REVIEW
                success = True
                logger.info(
                    "workflow_paused_for_review_from_checkpoint",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            elif current_step == "completed":
                # 工作流完成
                status = TaskStatus.COMPLETED
                success = True
                logger.info(
                    "workflow_completed_from_checkpoint",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
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
            
            return {
                "success": success,
                "roadmap_id": roadmap_id,
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
            
        finally:
            # 清理 Orchestrator Factory
            if factory:
                await factory.cleanup()


# 依赖注入工厂
def get_workflow_execution_service() -> WorkflowExecutionService:
    """获取 WorkflowExecutionService 实例（依赖注入）"""
    return WorkflowExecutionService()

