"""
工作流大脑 - 统一协调者

职责:
1. 状态管理 (State Management)
2. Checkpoint 协调 (Checkpoint Coordination)
3. 数据库操作 (DB Operations)
4. 日志管理 (Logging)
5. 通知发布 (Notification)

设计思想:
- Runner 只负责执行 Agent 并返回纯结果
- WorkflowBrain 统一管理所有状态变更和持久化操作
- 确保事务原子性和数据一致性
"""
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
import structlog

from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.services.notification_service import NotificationService
from app.services.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager
from app.core.orchestrator.base import RoadmapState, ensure_unique_roadmap_id

if TYPE_CHECKING:
    from app.models.domain import (
        IntentAnalysisOutput,
        RoadmapFramework,
    )

logger = structlog.get_logger()


@dataclass
class NodeContext:
    """
    节点执行上下文
    
    包含节点执行期间的关键信息，用于跟踪和日志记录。
    """
    node_name: str
    task_id: str
    roadmap_id: str | None
    start_time: float
    state_snapshot: dict


class WorkflowBrain:
    """
    工作流大脑
    
    统一管理工作流执行过程中的所有状态变更和持久化操作。
    
    核心功能:
    - 状态管理: 维护 live_step 缓存
    - 数据库操作: 统一事务管理，确保原子性
    - 日志记录: 结构化日志和执行历史
    - 通知发布: WebSocket 进度推送
    - 错误处理: 统一的异常处理和状态回滚
    
    使用示例:
        ```python
        brain = WorkflowBrain(
            state_manager=state_manager,
            notification_service=notification_service,
            execution_logger=execution_logger,
        )
        
        async with brain.node_execution("intent_analysis", state):
            # 执行 Agent 逻辑
            result = await agent.execute(...)
            
            # 保存结果（使用统一事务）
            await brain.save_intent_analysis(task_id, result, roadmap_id)
            
            # 返回状态更新
            return {"intent_analysis": result, ...}
        ```
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        notification_service: NotificationService,
        execution_logger: ExecutionLogger,
    ):
        """
        初始化 WorkflowBrain
        
        Args:
            state_manager: 状态管理器，维护 live_step 缓存
            notification_service: 通知服务，发布 WebSocket 消息
            execution_logger: 执行日志服务，记录结构化日志
        """
        self.state_manager = state_manager
        self.notification_service = notification_service
        self.execution_logger = execution_logger
        self._current_context: NodeContext | None = None
    
    @asynccontextmanager
    async def node_execution(
        self,
        node_name: str,
        state: RoadmapState,
    ):
        """
        节点执行上下文管理器
        
        自动处理节点执行的完整生命周期：
        - 执行前: 更新状态、记录日志、发布通知
        - 执行后: 记录完成日志、发布完成通知
        - 异常时: 错误处理、状态更新、错误通知
        
        Args:
            node_name: 节点名称（如 "intent_analysis", "curriculum_design"）
            state: 当前工作流状态
        
        Yields:
            NodeContext: 节点执行上下文
        
        Example:
            ```python
            async with brain.node_execution("intent_analysis", state):
                result = await agent.execute(...)
                await brain.save_intent_analysis(...)
                return {"intent_analysis": result}
            ```
        """
        from langgraph.errors import GraphInterrupt
        
        ctx = await self._before_node(node_name, state)
        try:
            yield ctx
            await self._after_node(ctx, state)
        except (GraphInterrupt, Exception) as e:
            # 检查是否是 GraphInterrupt（LangGraph 暂停机制）
            if isinstance(e, GraphInterrupt) or type(e).__name__ == "Interrupt":
                # GraphInterrupt/Interrupt 是 LangGraph 的正常暂停机制（用于 human_review），不是错误
                # 不调用 _on_error，直接重新抛出让 LangGraph 处理
                logger.info(
                    "workflow_brain_graph_interrupt",
                    node_name=ctx.node_name,
                    task_id=ctx.task_id,
                    message="工作流暂停等待人工审核（正常流程）",
                )
                self._current_context = None
                raise
            else:
                # 真正的错误
                await self._on_error(ctx, state, e)
                raise
    
    async def _before_node(self, node_name: str, state: RoadmapState) -> NodeContext:
        """
        节点执行前的统一处理
        
        执行顺序:
        1. 创建执行上下文
        2. 更新 live_step 缓存
        3. 更新数据库 task 状态
        4. 记录开始日志
        5. 发布进度通知
        
        Args:
            node_name: 节点名称
            state: 工作流状态
            
        Returns:
            NodeContext: 执行上下文
        """
        task_id = state["task_id"]
        roadmap_id = state.get("roadmap_id")
        
        # 创建执行上下文
        ctx = NodeContext(
            node_name=node_name,
            task_id=task_id,
            roadmap_id=roadmap_id,
            start_time=time.time(),
            state_snapshot=dict(state),
        )
        self._current_context = ctx
        
        logger.info(
            "workflow_brain_before_node",
            node_name=node_name,
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 1. 更新 live_step 缓存
        self.state_manager.set_live_step(task_id, node_name)
        
        # 2. 更新数据库状态（使用统一事务）
        try:
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                await repo.update_task_status(
                    task_id=task_id,
                    status="processing",
                    current_step=node_name,
                    roadmap_id=roadmap_id,
                )
                await session.commit()
                
                logger.debug(
                    "workflow_brain_task_status_updated",
                    task_id=task_id,
                    current_step=node_name,
                )
        except Exception as e:
            logger.error(
                "workflow_brain_task_status_update_failed",
                task_id=task_id,
                node_name=node_name,
                error=str(e),
            )
            # 不抛出异常，继续执行
        
        # 3. 记录开始日志
        await self.execution_logger.log_workflow_start(
            task_id=task_id,
            step=node_name,
            message=f"开始执行: {node_name}",
            roadmap_id=roadmap_id,
        )
        
        # 4. 发布进度通知
        await self.notification_service.publish_progress(
            task_id=task_id,
            step=node_name,
            status="processing",
            message=f"正在执行: {node_name}...",
        )
        
        return ctx
    
    async def _after_node(self, ctx: NodeContext, state: RoadmapState):
        """
        节点执行后的统一处理
        
        执行顺序:
        1. 计算执行时长
        2. 记录完成日志
        3. 发布完成通知
        4. 清理执行上下文
        
        Args:
            ctx: 节点执行上下文
            state: 工作流状态
        """
        duration_ms = int((time.time() - ctx.start_time) * 1000)
        
        logger.info(
            "workflow_brain_after_node",
            node_name=ctx.node_name,
            task_id=ctx.task_id,
            duration_ms=duration_ms,
        )
        
        # 1. 记录完成日志
        await self.execution_logger.log_workflow_complete(
            task_id=ctx.task_id,
            step=ctx.node_name,
            message=f"完成执行: {ctx.node_name}",
            duration_ms=duration_ms,
            roadmap_id=ctx.roadmap_id,
        )
        
        # 2. 发布完成通知
        await self.notification_service.publish_progress(
            task_id=ctx.task_id,
            step=ctx.node_name,
            status="completed",
            message=f"完成: {ctx.node_name}",
        )
        
        # 3. 清理执行上下文
        self._current_context = None
    
    async def _on_error(self, ctx: NodeContext, state: RoadmapState, error: Exception):
        """
        节点执行失败的统一处理
        
        执行顺序:
        1. 更新数据库状态为 "failed"
        2. 记录错误日志（包含堆栈信息）
        3. 发布错误通知
        4. 清理执行上下文
        
        Args:
            ctx: 节点执行上下文
            state: 工作流状态
            error: 异常对象
        """
        duration_ms = int((time.time() - ctx.start_time) * 1000)
        
        logger.error(
            "workflow_brain_on_error",
            node_name=ctx.node_name,
            task_id=ctx.task_id,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=duration_ms,
        )
        
        # 1. 更新数据库状态为失败
        try:
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                await repo.update_task_status(
                    task_id=ctx.task_id,
                    status="failed",
                    current_step=ctx.node_name,
                    error_message=str(error),
                )
                await session.commit()
                
                logger.debug(
                    "workflow_brain_task_status_updated_to_failed",
                    task_id=ctx.task_id,
                    node_name=ctx.node_name,
                )
        except Exception as db_error:
            logger.error(
                "workflow_brain_failed_to_update_task_status",
                task_id=ctx.task_id,
                error=str(db_error),
            )
        
        # 2. 记录错误日志
        await self.execution_logger.error(
            task_id=ctx.task_id,
            category="workflow",
            message=f"节点执行失败: {ctx.node_name}",
            step=ctx.node_name,
            duration_ms=duration_ms,
            details={
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
        
        # 3. 发布错误通知
        await self.notification_service.publish_progress(
            task_id=ctx.task_id,
            step=ctx.node_name,
            status="failed",
            message=f"执行失败: {ctx.node_name}",
            extra_data={"error": str(error)},
        )
        
        # 4. 清理执行上下文
        self._current_context = None
    
    # ========================================
    # 特定节点的数据保存方法
    # ========================================
    
    async def ensure_unique_roadmap_id(self, roadmap_id: str) -> str:
        """
        确保 roadmap_id 在数据库中是唯一的
        
        如果 roadmap_id 已存在，则重新生成后缀直到唯一。
        
        Args:
            roadmap_id: IntentAnalyzerAgent 生成的 roadmap_id
            
        Returns:
            唯一的 roadmap_id
        """
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            unique_id = await ensure_unique_roadmap_id(roadmap_id, repo)
            
            logger.info(
                "workflow_brain_roadmap_id_ensured",
                original_id=roadmap_id,
                unique_id=unique_id,
                changed=roadmap_id != unique_id,
            )
            
            return unique_id
    
    async def save_intent_analysis(
        self,
        task_id: str,
        intent_analysis: "IntentAnalysisOutput",
        unique_roadmap_id: str,
    ):
        """
        保存需求分析结果（事务性操作）
        
        在同一事务中执行:
        1. 保存 IntentAnalysisMetadata
        2. 更新 task 的 roadmap_id
        
        Args:
            task_id: 任务 ID
            intent_analysis: 需求分析结果
            unique_roadmap_id: 唯一的路线图 ID
        """
        logger.info(
            "workflow_brain_save_intent_analysis",
            task_id=task_id,
            roadmap_id=unique_roadmap_id,
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中执行所有操作
            await repo.save_intent_analysis_metadata(task_id, intent_analysis)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="intent_analysis",
                roadmap_id=unique_roadmap_id,
            )
            
            await session.commit()
            
            logger.info(
                "workflow_brain_intent_analysis_saved",
                task_id=task_id,
                roadmap_id=unique_roadmap_id,
            )
    
    async def save_roadmap_framework(
        self,
        task_id: str,
        roadmap_id: str,
        user_id: str,
        framework: "RoadmapFramework",
    ):
        """
        保存路线图框架（事务性操作）
        
        在同一事务中执行:
        1. 保存 RoadmapMetadata
        2. 更新 task 状态
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            user_id: 用户 ID
            framework: 路线图框架
        """
        logger.info(
            "workflow_brain_save_roadmap_framework",
            task_id=task_id,
            roadmap_id=roadmap_id,
            stages_count=len(framework.stages) if framework else 0,
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中执行所有操作
            await repo.save_roadmap_metadata(roadmap_id, user_id, framework)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="curriculum_design",
            )
            
            await session.commit()
            
            logger.info(
                "workflow_brain_roadmap_framework_saved",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
    
    async def save_content_results(
        self,
        task_id: str,
        roadmap_id: str,
        tutorial_refs: dict,
        resource_refs: dict,
        quiz_refs: dict,
        failed_concepts: list,
    ):
        """
        保存内容生成结果（批量事务操作）
        
        在同一事务中执行:
        1. 批量保存 TutorialMetadata
        2. 批量保存 ResourceRecommendationMetadata
        3. 批量保存 QuizMetadata
        4. 更新 roadmap_metadata 的 framework_data（更新 Concept 引用）
        5. 更新 task 最终状态
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            tutorial_refs: 教程引用字典 {concept_id: TutorialGenerationOutput}
            resource_refs: 资源引用字典 {concept_id: ResourceRecommendationOutput}
            quiz_refs: 测验引用字典 {concept_id: QuizGenerationOutput}
            failed_concepts: 失败的概念 ID 列表
        """
        logger.info(
            "workflow_brain_save_content_results",
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorial_count=len(tutorial_refs),
            resource_count=len(resource_refs),
            quiz_count=len(quiz_refs),
            failed_count=len(failed_concepts),
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中批量保存元数据
            if tutorial_refs:
                await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
            if resource_refs:
                await repo.save_resources_batch(resource_refs, roadmap_id)
            if quiz_refs:
                await repo.save_quizzes_batch(quiz_refs, roadmap_id)
            
            # ============================================================
            # BUG FIX: 更新 roadmap_metadata 的 framework_data
            # ============================================================
            # 读取当前的 framework，更新 Concept 中的内容引用，然后保存回数据库
            logger.info(
                "workflow_brain_reading_roadmap_metadata",
                roadmap_id=roadmap_id,
            )
            roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
            logger.info(
                "workflow_brain_roadmap_metadata_read",
                roadmap_id=roadmap_id,
                found=roadmap_metadata is not None,
                has_framework_data=bool(roadmap_metadata.framework_data) if roadmap_metadata else False,
            )
            if roadmap_metadata and roadmap_metadata.framework_data:
                try:
                    # ========================================================
                    # DEBUG: 记录更新前的 framework 状态（抽样检查第一个 concept）
                    # ========================================================
                    original_framework = roadmap_metadata.framework_data
                    sample_concept_before = None
                    if original_framework.get("stages"):
                        first_stage = original_framework["stages"][0]
                        if first_stage.get("modules"):
                            first_module = first_stage["modules"][0]
                            if first_module.get("concepts"):
                                sample_concept_before = first_module["concepts"][0].copy()
                    
                    logger.info(
                        "workflow_brain_framework_before_update",
                        roadmap_id=roadmap_id,
                        sample_concept_id=sample_concept_before.get("concept_id") if sample_concept_before else None,
                        sample_content_status=sample_concept_before.get("content_status") if sample_concept_before else None,
                        sample_content_ref=sample_concept_before.get("content_ref") if sample_concept_before else None,
                        sample_quiz_id=sample_concept_before.get("quiz_id") if sample_concept_before else None,
                    )
                    
                    # 使用辅助方法更新 framework 中的 Concept 状态
                    updated_framework = self._update_framework_with_content_refs(
                        framework_data=roadmap_metadata.framework_data,
                        tutorial_refs=tutorial_refs,
                        resource_refs=resource_refs,
                        quiz_refs=quiz_refs,
                        failed_concepts=failed_concepts,
                    )
                    
                    # ========================================================
                    # DEBUG: 记录更新后的 framework 状态（抽样检查第一个 concept）
                    # ========================================================
                    sample_concept_after = None
                    if updated_framework.get("stages"):
                        first_stage = updated_framework["stages"][0]
                        if first_stage.get("modules"):
                            first_module = first_stage["modules"][0]
                            if first_module.get("concepts"):
                                sample_concept_after = first_module["concepts"][0]
                    
                    logger.info(
                        "workflow_brain_framework_after_update",
                        roadmap_id=roadmap_id,
                        sample_concept_id=sample_concept_after.get("concept_id") if sample_concept_after else None,
                        sample_content_status=sample_concept_after.get("content_status") if sample_concept_after else None,
                        sample_content_ref=sample_concept_after.get("content_ref") if sample_concept_after else None,
                        sample_quiz_id=sample_concept_after.get("quiz_id") if sample_concept_after else None,
                    )
                    
                    # 保存更新后的 framework
                    from app.models.domain import RoadmapFramework
                    framework_obj = RoadmapFramework.model_validate(updated_framework)
                    
                    # ========================================================
                    # DEBUG: 验证 Pydantic 模型转换后的状态
                    # ========================================================
                    framework_dict_after_pydantic = framework_obj.model_dump()
                    sample_concept_pydantic = None
                    if framework_dict_after_pydantic.get("stages"):
                        first_stage = framework_dict_after_pydantic["stages"][0]
                        if first_stage.get("modules"):
                            first_module = first_stage["modules"][0]
                            if first_module.get("concepts"):
                                sample_concept_pydantic = first_module["concepts"][0]
                    
                    logger.info(
                        "workflow_brain_framework_after_pydantic_validate",
                        roadmap_id=roadmap_id,
                        sample_concept_id=sample_concept_pydantic.get("concept_id") if sample_concept_pydantic else None,
                        sample_content_status=sample_concept_pydantic.get("content_status") if sample_concept_pydantic else None,
                        sample_content_ref=sample_concept_pydantic.get("content_ref") if sample_concept_pydantic else None,
                        sample_quiz_id=sample_concept_pydantic.get("quiz_id") if sample_concept_pydantic else None,
                    )
                    
                    await repo.save_roadmap_metadata(
                        roadmap_id=roadmap_id,
                        user_id=roadmap_metadata.user_id,
                        framework=framework_obj,
                    )
                    
                    # ========================================================
                    # DEBUG: 保存后立即重新读取，验证数据是否真的被保存
                    # ========================================================
                    verification_metadata = await repo.get_roadmap_metadata(roadmap_id)
                    if verification_metadata and verification_metadata.framework_data:
                        verify_sample = None
                        if verification_metadata.framework_data.get("stages"):
                            first_stage = verification_metadata.framework_data["stages"][0]
                            if first_stage.get("modules"):
                                first_module = first_stage["modules"][0]
                                if first_module.get("concepts"):
                                    verify_sample = first_module["concepts"][0]
                        
                        logger.info(
                            "workflow_brain_framework_verification_after_save",
                            roadmap_id=roadmap_id,
                            sample_concept_id=verify_sample.get("concept_id") if verify_sample else None,
                            sample_content_status=verify_sample.get("content_status") if verify_sample else None,
                            sample_content_ref=verify_sample.get("content_ref") if verify_sample else None,
                            sample_quiz_id=verify_sample.get("quiz_id") if verify_sample else None,
                            verification_success=verify_sample.get("content_status") == "completed" if verify_sample else False,
                        )
                    else:
                        logger.error(
                            "workflow_brain_framework_verification_failed",
                            roadmap_id=roadmap_id,
                            message="无法重新读取保存后的元数据",
                        )
                    
                    logger.info(
                        "workflow_brain_framework_updated_with_content_refs",
                        roadmap_id=roadmap_id,
                        tutorial_count=len(tutorial_refs),
                        resource_count=len(resource_refs),
                        quiz_count=len(quiz_refs),
                    )
                except Exception as e:
                    logger.error(
                        "workflow_brain_framework_update_failed",
                        roadmap_id=roadmap_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # 重新抛出异常，不要吞掉
                    raise
            else:
                logger.warning(
                    "workflow_brain_framework_not_found",
                    roadmap_id=roadmap_id,
                    message="无法更新 framework_data，元数据不存在",
                )
            
            # 更新最终状态
            # 如果全部成功：status=completed, current_step=completed
            # 如果部分失败：status=partial_failure, current_step=content_generation（标记失败发生在哪一步）
            final_status = "partial_failure" if failed_concepts else "completed"
            final_step = "content_generation" if failed_concepts else "completed"
            
            await repo.update_task_status(
                task_id=task_id,
                status=final_status,
                current_step=final_step,
                failed_concepts={
                    "count": len(failed_concepts),
                    "concept_ids": failed_concepts,
                } if failed_concepts else None,
                execution_summary={
                    "tutorial_count": len(tutorial_refs),
                    "resource_count": len(resource_refs),
                    "quiz_count": len(quiz_refs),
                    "failed_count": len(failed_concepts),
                },
            )
            
            await session.commit()
            
            logger.info(
                "workflow_brain_content_results_saved",
                task_id=task_id,
                roadmap_id=roadmap_id,
                final_status=final_status,
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
        更新 framework 中所有 Concept 的内容引用字段
        
        遍历 framework_data 中的所有 Concept，根据生成结果更新：
        - content_status, content_ref, content_summary（教程）
        - resources_status, resources_id, resources_count（资源）
        - quiz_status, quiz_id, quiz_questions_count（测验）
        
        Args:
            framework_data: 原始 framework 字典数据
            tutorial_refs: 教程引用字典 {concept_id: TutorialGenerationOutput}
            resource_refs: 资源引用字典 {concept_id: ResourceRecommendationOutput}
            quiz_refs: 测验引用字典 {concept_id: QuizGenerationOutput}
            failed_concepts: 失败的概念 ID 列表
            
        Returns:
            更新后的 framework 字典
        """
        # 遍历三层结构：Stage -> Module -> Concept
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    if not concept_id:
                        continue
                    
                    # 更新教程相关字段
                    if concept_id in tutorial_refs:
                        tutorial_output = tutorial_refs[concept_id]
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorial_output.content_url
                        concept["content_summary"] = tutorial_output.summary
                    elif concept_id in failed_concepts:
                        # 失败的概念标记为 failed
                        if "content_status" not in concept or concept["content_status"] == "pending":
                            concept["content_status"] = "failed"
                    
                    # 更新资源相关字段
                    if concept_id in resource_refs:
                        resource_output = resource_refs[concept_id]
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource_output.id
                        concept["resources_count"] = len(resource_output.resources)
                    elif concept_id in failed_concepts:
                        if "resources_status" not in concept or concept["resources_status"] == "pending":
                            concept["resources_status"] = "failed"
                    
                    # 更新测验相关字段
                    if concept_id in quiz_refs:
                        quiz_output = quiz_refs[concept_id]
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz_output.quiz_id
                        concept["quiz_questions_count"] = quiz_output.total_questions
                    elif concept_id in failed_concepts:
                        if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                            concept["quiz_status"] = "failed"
        
        return framework_data
    
    async def update_task_to_pending_review(
        self,
        task_id: str,
        roadmap_id: str | None,
    ):
        """
        将任务状态更新为 "human_review_pending"
        
        用于 ReviewRunner：标记任务正在等待人工审核。
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
        """
        logger.info(
            "workflow_brain_update_to_pending_review",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="human_review_pending",
                current_step="human_review",
                roadmap_id=roadmap_id,
            )
            await session.commit()
            
            logger.debug(
                "workflow_brain_task_status_updated_to_pending_review",
                task_id=task_id,
            )
    
    async def update_task_after_review(
        self,
        task_id: str,
    ):
        """
        人工审核后将任务状态恢复为 "processing"
        
        用于 ReviewRunner：审核完成后恢复正常处理流程。
        
        Args:
            task_id: 任务 ID
        """
        logger.info(
            "workflow_brain_update_after_review",
            task_id=task_id,
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="human_review_completed",
            )
            await session.commit()
            
            logger.debug(
                "workflow_brain_task_status_updated_after_review",
                task_id=task_id,
            )

