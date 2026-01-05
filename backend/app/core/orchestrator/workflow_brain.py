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

from app.db.session import AsyncSessionLocal, safe_session
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.services.notification_service import NotificationService
from app.services.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager
from app.core.orchestrator.base import RoadmapState, ensure_unique_roadmap_id

if TYPE_CHECKING:
    from app.models.domain import (
        IntentAnalysisOutput,
        RoadmapFramework,
        ValidationOutput,
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
        skip_before: bool = False,
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
            skip_before: 是否跳过 _before_node 逻辑（用于从 interrupt 恢复时避免重复执行）
        
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
        
        # 根据 skip_before 参数决定是否执行 _before_node
        if skip_before:
            # 从 interrupt 恢复时，创建轻量级上下文，跳过状态更新和日志
            import time
            ctx = NodeContext(
                node_name=node_name,
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
                start_time=time.time(),
                state_snapshot=dict(state),
            )
            self._current_context = ctx
            logger.debug(
                "workflow_brain_skip_before_node",
                node_name=node_name,
                task_id=state["task_id"],
                message="跳过 _before_node（从 interrupt 恢复）",
            )
        else:
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
        # 从 state 中提取 edit_source（用于前端区分分支）
        extra_data = {}
        edit_source = state.get("edit_source")
        if edit_source:
            extra_data["edit_source"] = edit_source
        
        await self.notification_service.publish_progress(
            task_id=task_id,
            step=node_name,
            status="processing",
            message=f"正在执行: {node_name}...",
            extra_data=extra_data if extra_data else None,
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
        # 从 state 中提取 edit_source（用于前端区分分支）
        extra_data = {}
        edit_source = state.get("edit_source")
        if edit_source:
            extra_data["edit_source"] = edit_source
        
        await self.notification_service.publish_progress(
            task_id=ctx.task_id,
            step=ctx.node_name,
            status="completed",
            message=f"完成: {ctx.node_name}",
            extra_data=extra_data if extra_data else None,
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
        
        # 3. 发布失败通知（使用 publish_failed 获取完整错误信息）
        await self.notification_service.publish_failed(
            task_id=ctx.task_id,
            error=str(error),
            step=ctx.node_name,
            exception=error,  # 传递异常对象以获取完整堆栈
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
        
        注意：由于 Repository 方法内部已经 commit，这里实际上是两个独立的事务。
        虽然不是严格的原子操作，但对于这个场景是可接受的，因为：
        1. save_intent_analysis_metadata 先执行，即使后续失败，数据也已保存
        2. update_task_status 更新任务状态，标记 roadmap_id
        
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
        
        # 第一步：保存 Intent Analysis 元数据
        # 注意：repo 方法只调用 flush()，需要手动 commit
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.save_intent_analysis_metadata(task_id, intent_analysis)
            await session.commit()  # ✅ 必须手动 commit 才能持久化
        
        # 第二步：更新任务状态和 roadmap_id
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
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
            intent_analysis_committed=True,
            task_status_updated=True,
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
        
        注意：由于 Repository 方法内部已经 commit，这里实际上是两个独立的事务。
        
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
        
        # 第一步：保存路线图框架
        # 注意：repo 方法只调用 flush()，需要手动 commit
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.save_roadmap_metadata(roadmap_id, user_id, framework)
            await session.commit()  # ✅ 必须手动 commit 才能持久化
        
        # 第二步：更新任务状态
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
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
            framework_committed=True,
            task_status_updated=True,
        )
        
        # 异步触发封面图生成（不阻塞主流程）
        try:
            from app.services.cover_image_service import CoverImageService
            async with AsyncSessionLocal() as session:
                cover_service = CoverImageService(session)
                # 使用路线图标题作为提示词
                prompt = framework.title if framework else None
                await cover_service.generate_cover_image(
                    roadmap_id=roadmap_id,
                    prompt=prompt
                )
        except Exception as e:
            # 封面图生成失败不影响主流程
            logger.warning(
                "workflow_brain_cover_image_generation_failed",
                task_id=task_id,
                roadmap_id=roadmap_id,
                error=str(e),
            )
    
    async def save_validation_result(
        self,
        task_id: str,
        roadmap_id: str,
        validation_result: "ValidationOutput",
        validation_round: int,
    ):
        """
        保存结构验证结果到数据库
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            validation_result: 验证结果对象（包含新字段）
            validation_round: 验证轮次
        """
        from app.models.domain import ValidationOutput
        
        logger.info(
            "workflow_brain_save_validation_result",
            task_id=task_id,
            roadmap_id=roadmap_id,
            validation_round=validation_round,
            is_valid=validation_result.is_valid,
        )
        
        async with AsyncSessionLocal() as session:
            from app.db.repositories.validation_repo import ValidationRepository
            
            validation_repo = ValidationRepository(session)
            
            # 统计问题数量
            critical_count = len([i for i in validation_result.issues if i.severity == "critical"])
            warning_count = len([i for i in validation_result.issues if i.severity == "warning"])
            suggestion_count = len(validation_result.improvement_suggestions)
            
            # 创建验证记录（传递所有新字段）
            await validation_repo.create_validation_record(
                task_id=task_id,
                roadmap_id=roadmap_id,
                is_valid=validation_result.is_valid,
                overall_score=validation_result.overall_score,
                issues=[i.model_dump() for i in validation_result.issues],
                dimension_scores=[s.model_dump() for s in validation_result.dimension_scores],
                improvement_suggestions=[s.model_dump() for s in validation_result.improvement_suggestions],
                validation_summary=validation_result.validation_summary,
                validation_round=validation_round,
                critical_count=critical_count,
                warning_count=warning_count,
                suggestion_count=suggestion_count,
            )
            
            await session.commit()
            
            logger.info(
                "workflow_brain_validation_result_saved",
                task_id=task_id,
                roadmap_id=roadmap_id,
                validation_round=validation_round,
                suggestion_count=suggestion_count,
            )
    
    async def save_edit_result(
        self,
        task_id: str,
        roadmap_id: str,
        origin_framework: "RoadmapFramework",
        modified_framework: "RoadmapFramework",
        edit_round: int,
    ):
        """
        保存路线图编辑结果到数据库
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            origin_framework: 编辑前的框架
            modified_framework: 编辑后的框架
            edit_round: 编辑轮次
        """
        logger.info(
            "workflow_brain_save_edit_result",
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_round=edit_round,
        )
        
        # 计算修改的节点 ID
        modified_node_ids = self._compute_modified_node_ids(
            origin_framework,
            modified_framework
        )
        
        async with AsyncSessionLocal() as session:
            from app.db.repositories.edit_repo import EditRepository
            
            edit_repo = EditRepository(session)
            
            # 创建编辑记录
            await edit_repo.create_edit_record(
                task_id=task_id,
                roadmap_id=roadmap_id,
                origin_framework_data=origin_framework.model_dump(),
                modified_framework_data=modified_framework.model_dump(),
                modification_summary=f"AI 根据第 {edit_round} 轮验证结果优化了路线图结构",
                modified_node_ids=modified_node_ids,
                edit_round=edit_round,
            )
            
            await session.commit()
            
            logger.info(
                "workflow_brain_edit_result_saved",
                task_id=task_id,
                roadmap_id=roadmap_id,
                edit_round=edit_round,
                modified_nodes_count=len(modified_node_ids),
            )
    
    def _compute_modified_node_ids(
        self,
        origin_framework: "RoadmapFramework",
        modified_framework: "RoadmapFramework"
    ) -> list[str]:
        """
        计算修改过的节点 ID（concept_id）
        
        使用通用路线图比对服务进行完整的字段比对。
        
        Args:
            origin_framework: 原始框架
            modified_framework: 修改后的框架
            
        Returns:
            修改过的 concept_id 列表（包括新增和修改的节点）
        """
        from app.services.roadmap_comparison_service import RoadmapComparisonService
        
        # 使用通用比对服务
        comparison_service = RoadmapComparisonService()
        modified_ids = comparison_service.get_modified_node_ids_simple(
            origin_framework,
            modified_framework
        )
        
        logger.debug(
            "compute_modified_node_ids",
            changed_count=len(modified_ids),
            method="roadmap_comparison_service",
        )
        
        return modified_ids
    
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
        保存内容生成结果（分批事务操作，减少连接持有时间）
        
        重构后的策略：将大事务拆分为多个小事务，每批独立提交
        1. 分批保存 TutorialMetadata（每批独立事务）
        2. 分批保存 ResourceRecommendationMetadata（每批独立事务）
        3. 分批保存 QuizMetadata（每批独立事务）
        4. 更新 roadmap_metadata 的 framework_data（独立事务）
        5. 更新 task 最终状态（独立事务）
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            tutorial_refs: 教程引用字典 {concept_id: TutorialGenerationOutput}
            resource_refs: 资源引用字典 {concept_id: ResourceRecommendationOutput}
            quiz_refs: 测验引用字典 {concept_id: QuizGenerationOutput}
            failed_concepts: 失败的概念 ID 列表
        
        特别说明:
            - 使用短生命周期会话，减少连接占用时间
            - 分批保存，每批10个概念，独立事务
            - 处理客户端断开连接（GeneratorExit）和数据库连接超时异常
            - 使用带重试的会话管理器应对连接池压力
        """
        from app.db.session import safe_session_with_retry
        
        logger.info(
            "workflow_brain_save_content_results",
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorial_count=len(tutorial_refs),
            resource_count=len(resource_refs),
            quiz_count=len(quiz_refs),
            failed_count=len(failed_concepts),
        )
        
        try:
            # ============================================================
            # Phase 1: 按内容类型批量保存元数据（每种类型一个事务）
            # ============================================================
            # 性能优化：将分散的小事务合并为更少的大事务
            # - 30 个概念原来需要 9 个事务 -> 现在只需 3 个事务（减少 67%）
            # - 批量操作已在 Repository 层实现，无需在此处分批
            
            # 1.1 一次性保存所有教程（单个事务）
            if tutorial_refs:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
                    await session.commit()
                logger.debug(
                    "workflow_brain_tutorials_saved",
                    roadmap_id=roadmap_id,
                    count=len(tutorial_refs),
                )
            
            # 1.2 一次性保存所有资源（单个事务）
            if resource_refs:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_resources_batch(resource_refs, roadmap_id)
                    await session.commit()
                logger.debug(
                    "workflow_brain_resources_saved",
                    roadmap_id=roadmap_id,
                    count=len(resource_refs),
                )
            
            # 1.3 一次性保存所有测验（单个事务）
            if quiz_refs:
                async with safe_session_with_retry() as session:
                    repo = RoadmapRepository(session)
                    await repo.save_quizzes_batch(quiz_refs, roadmap_id)
                    await session.commit()
                logger.debug(
                    "workflow_brain_quizzes_saved",
                    roadmap_id=roadmap_id,
                    count=len(quiz_refs),
                )
            
            logger.info(
                "workflow_brain_metadata_batches_saved",
                task_id=task_id,
                roadmap_id=roadmap_id,
                tutorial_count=len(tutorial_refs),
                resource_count=len(resource_refs),
                quiz_count=len(quiz_refs),
            )
            
            # ============================================================
            # Phase 2: 更新 framework_data（独立事务）
            # ============================================================
            async with safe_session_with_retry() as session:
                repo = RoadmapRepository(session)
                
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
                    # 使用辅助方法更新 framework 中的 Concept 状态
                    updated_framework = self._update_framework_with_content_refs(
                        framework_data=roadmap_metadata.framework_data,
                        tutorial_refs=tutorial_refs,
                        resource_refs=resource_refs,
                        quiz_refs=quiz_refs,
                        failed_concepts=failed_concepts,
                    )
                    
                    # 保存更新后的 framework
                    from app.models.domain import RoadmapFramework
                    framework_obj = RoadmapFramework.model_validate(updated_framework)
                    
                    await repo.save_roadmap_metadata(
                        roadmap_id=roadmap_id,
                        user_id=roadmap_metadata.user_id,
                        framework=framework_obj,
                    )
                    
                    await session.commit()
                    
                    logger.info(
                        "workflow_brain_framework_updated_with_content_refs",
                        roadmap_id=roadmap_id,
                        tutorial_count=len(tutorial_refs),
                        resource_count=len(resource_refs),
                        quiz_count=len(quiz_refs),
                    )
                else:
                    logger.warning(
                        "workflow_brain_framework_not_found",
                        roadmap_id=roadmap_id,
                        message="无法更新 framework_data，元数据不存在",
                    )
            
            # ============================================================
            # Phase 3: 更新 task 最终状态（独立事务）
            # ============================================================
            final_status = "partial_failure" if failed_concepts else "completed"
            final_step = "content_generation" if failed_concepts else "completed"
            
            async with safe_session_with_retry() as session:
                repo = RoadmapRepository(session)
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
            
            # ============================================================
            # Phase 4: 发布工作流完成通知（无需数据库连接）
            # ============================================================
            tutorial_count = len(tutorial_refs)
            failed_count = len(failed_concepts)
            
            await self.notification_service.publish_completed(
                task_id=task_id,
                roadmap_id=roadmap_id,
                tutorials_count=tutorial_count,
                failed_count=failed_count,
            )
            
            logger.info(
                "workflow_brain_workflow_completed_notification_sent",
                task_id=task_id,
                roadmap_id=roadmap_id,
                tutorial_count=tutorial_count,
                failed_count=failed_count,
            )
        
        except GeneratorExit:
            # 客户端断开连接（SSE 流中断）
            logger.warning(
                "workflow_brain_save_content_client_disconnected",
                task_id=task_id,
                roadmap_id=roadmap_id,
                message="客户端断开连接，内容保存操作被中断",
            )
            raise
            
        except Exception as e:
            # 数据库错误（包括连接超时）
            logger.error(
                "workflow_brain_save_content_failed",
                task_id=task_id,
                roadmap_id=roadmap_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
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
        roadmap_title: str | None = None,
        stages_count: int = 0,
    ):
        """
        将任务状态更新为 "human_review_pending"
        
        用于 ReviewRunner：标记任务正在等待人工审核。
        同时发送 human_review_required WebSocket 事件，通知前端显示审核对话框。
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            roadmap_title: 路线图标题（用于前端显示）
            stages_count: 阶段数量（用于前端显示）
        """
        logger.info(
            "workflow_brain_update_to_pending_review",
            task_id=task_id,
            roadmap_id=roadmap_id,
            roadmap_title=roadmap_title,
            stages_count=stages_count,
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
        
        # 发送 human_review_required WebSocket 事件
        # 关键：这会通知前端显示审核对话框（无论是首次进入还是从编辑循环返回）
        await self.notification_service.publish_human_review_required(
            task_id=task_id,
            roadmap_id=roadmap_id or "",
            roadmap_title=roadmap_title or "Untitled Roadmap",
            stages_count=stages_count,
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
    
    async def save_celery_task_id(
        self,
        task_id: str,
        celery_task_id: str,
    ):
        """
        保存 Celery 任务 ID 到数据库
        
        用于 ContentRunner：记录内容生成任务的 Celery task ID，
        以便后续查询任务状态或取消任务。
        
        Args:
            task_id: 追踪 ID
            celery_task_id: Celery 任务 ID
        """
        logger.info(
            "workflow_brain_save_celery_task_id",
            task_id=task_id,
            celery_task_id=celery_task_id,
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_celery_id(
                task_id=task_id,
                celery_task_id=celery_task_id,
            )
            await session.commit()
            
            logger.debug(
                "workflow_brain_celery_task_id_saved",
                task_id=task_id,
                celery_task_id=celery_task_id,
            )

