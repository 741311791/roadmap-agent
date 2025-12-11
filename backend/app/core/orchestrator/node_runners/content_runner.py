"""
内容生成节点执行器

负责执行内容生成节点（Step 5: Content Generation）
并行执行教程生成、资源推荐、测验生成三个Agent
"""
import time
import asyncio
import structlog

from app.agents.factory import AgentFactory
from app.models.domain import (
    Concept,
    TutorialGenerationInput,
    TutorialGenerationOutput,
    ResourceRecommendationInput,
    ResourceRecommendationOutput,
    QuizGenerationInput,
    QuizGenerationOutput,
)
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger, LogCategory
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.session import AsyncSessionLocal
from app.config.settings import settings
from app.core.error_handler import error_handler
from ..base import RoadmapState, WorkflowConfig
from ..state_manager import StateManager

logger = structlog.get_logger()


class ContentRunner:
    """
    内容生成节点执行器
    
    职责：
    1. 并行执行 TutorialGeneratorAgent、ResourceRecommenderAgent、QuizGeneratorAgent
    2. 使用信号量控制并发数量
    3. 发布进度通知
    4. 记录执行日志
    5. 错误处理（部分失败不影响整体，通过统一 ErrorHandler）
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        config: WorkflowConfig,
        agent_factory: AgentFactory,
    ):
        """
        Args:
            state_manager: StateManager 实例
            config: WorkflowConfig 实例
            agent_factory: AgentFactory 实例
        """
        self.state_manager = state_manager
        self.config = config
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行内容生成节点
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        start_time = time.time()
        task_id = state["task_id"]
        
        # 设置当前步骤
        self.state_manager.set_live_step(task_id, "content_generation")
        
        # 获取 roadmap_id
        roadmap_id = state.get("roadmap_id")
        
        logger.info(
            "workflow_step_started",
            step="content_generation",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 记录执行日志（包含 roadmap_id）
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="content_generation",
            message="开始生成内容",
            roadmap_id=roadmap_id,
        )
        
        # 更新数据库状态
        await self._update_task_status(task_id, "content_generation", roadmap_id)
        
        framework = state.get("roadmap_framework")
        if not framework:
            raise ValueError("路线图框架不存在，无法生成内容")
        
        # 提取所有概念
        concepts_with_context = self._extract_concepts_from_roadmap(framework)
        
        # 计算启用的 Agent
        enabled_agents = []
        if not self.config.skip_tutorial_generation:
            enabled_agents.append("教程生成")
        if not self.config.skip_resource_recommendation:
            enabled_agents.append("资源推荐")
        if not self.config.skip_quiz_generation:
            enabled_agents.append("测验生成")
        
        # 发布进度通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="content_generation",
            status="processing",
            message=f"开始生成内容（共 {len(concepts_with_context)} 个概念，启用: {', '.join(enabled_agents)}）...",
            extra_data={
                "total_concepts": len(concepts_with_context),
                "enabled_agents": enabled_agents,
            },
        )
        
        logger.info(
            "content_generation_started",
            concepts_count=len(concepts_with_context),
            enabled_agents=enabled_agents,
            task_id=task_id,
        )
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution("content_generation", task_id, "内容生成") as ctx:
            new_tutorial_refs, new_resource_refs, new_quiz_refs, new_failed_concepts = (
                await self._generate_all_content(state, concepts_with_context)
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 统计结果
            tutorial_success = len(new_tutorial_refs)
            resource_success = len(new_resource_refs)
            quiz_success = len(new_quiz_refs)
            failed_count = len(new_failed_concepts)
            
            logger.info(
                "workflow_step_completed",
                step="content_generation",
                task_id=task_id,
                tutorial_success=tutorial_success,
                resource_success=resource_success,
                quiz_success=quiz_success,
                failed_count=failed_count,
            )
            
            # 记录执行日志
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="content_generation",
                message=f"内容生成完成（成功: {tutorial_success + resource_success + quiz_success}, 失败: {failed_count}）",
                duration_ms=duration_ms,
                roadmap_id=state.get("roadmap_id"),
                details={
                    "tutorial_success": tutorial_success,
                    "resource_success": resource_success,
                    "quiz_success": quiz_success,
                    "failed_count": failed_count,
                    "failed_concepts": new_failed_concepts[:5],
                },
            )
            
            # 发布步骤完成通知
            await notification_service.publish_progress(
                task_id=task_id,
                step="content_generation",
                status="completed",
                message=f"内容生成完成",
                extra_data={
                    "tutorial_success": tutorial_success,
                    "resource_success": resource_success,
                    "quiz_success": quiz_success,
                    "failed_count": failed_count,
                },
            )
            
            # 更新task状态为completed
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                final_status = "partial_failure" if failed_count > 0 else "completed"
                await repo.update_task_status(
                    task_id=task_id,
                    status=final_status,
                    current_step="content_generation",
                    failed_concepts={
                        "count": failed_count,
                        "concept_ids": new_failed_concepts,
                    } if failed_count > 0 else None,
                    execution_summary={
                        "tutorial_count": tutorial_success,
                        "resource_count": resource_success,
                        "quiz_count": quiz_success,
                        "failed_count": failed_count,
                    },
                )
                await session.commit()
            
            # 存储结果到上下文
            ctx["result"] = {
                "tutorial_refs": new_tutorial_refs,
                "resource_refs": new_resource_refs,
                "quiz_refs": new_quiz_refs,
                "failed_concepts": new_failed_concepts,
                "current_step": "content_generation",
                "execution_history": ["内容生成完成"],
            }
        
        # 返回状态更新
        return ctx["result"]
    
    def _extract_concepts_from_roadmap(self, framework) -> list[tuple[Concept, dict]]:
        """
        从路线图框架中提取所有概念及其上下文
        
        Returns:
            [(concept, context), ...]
        """
        concepts_with_context = []
        
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    context = {
                        "roadmap_id": framework.roadmap_id,
                        "stage_id": stage.stage_id,
                        "stage_name": stage.name,
                        "module_id": module.module_id,
                        "module_name": module.name,
                        "difficulty": concept.difficulty,
                    }
                    concepts_with_context.append((concept, context))
        
        return concepts_with_context
    
    def _update_framework_concept_statuses(
        self,
        framework,
        tutorial_refs: dict,
        resource_refs: dict,
        quiz_refs: dict,
        failed_concepts: list,
    ):
        """
        更新 framework 中 Concept 的状态字段
        
        Args:
            framework: RoadmapFramework 对象
            tutorial_refs: 教程引用字典
            resource_refs: 资源引用字典
            quiz_refs: 测验引用字典
            failed_concepts: 失败的概念ID列表
        """
        if not framework:
            return
        
        logger.info(
            "updating_framework_concept_statuses",
            tutorial_count=len(tutorial_refs),
            resource_count=len(resource_refs),
            quiz_count=len(quiz_refs),
            failed_count=len(failed_concepts),
        )
        
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    concept_id = concept.concept_id
                    
                    # 更新教程状态
                    if concept_id in tutorial_refs:
                        tutorial_output = tutorial_refs[concept_id]
                        concept.content_status = "completed"
                        # 更新教程引用信息
                        if hasattr(tutorial_output, 'tutorial_id'):
                            concept.content_ref = tutorial_output.tutorial_id
                        # 注意：TutorialGenerationOutput 的字段是 summary，不是 content_summary
                        if hasattr(tutorial_output, 'summary') and tutorial_output.summary:
                            concept.content_summary = tutorial_output.summary
                    elif concept_id in failed_concepts:
                        concept.content_status = "failed"
                    
                    # 更新资源推荐状态
                    if concept_id in resource_refs:
                        resource_output = resource_refs[concept_id]
                        concept.resources_status = "completed"
                        # 更新资源引用信息
                        # 注意：ResourceRecommendationOutput 的字段是 id，不是 resources_id
                        if hasattr(resource_output, 'id'):
                            concept.resources_id = resource_output.id
                        if hasattr(resource_output, 'resources'):
                            concept.resources_count = len(resource_output.resources)
                    
                    # 更新测验状态
                    if concept_id in quiz_refs:
                        quiz_output = quiz_refs[concept_id]
                        concept.quiz_status = "completed"
                        # 更新测验引用信息
                        if hasattr(quiz_output, 'quiz_id'):
                            concept.quiz_id = quiz_output.quiz_id
                        if hasattr(quiz_output, 'questions'):
                            concept.quiz_questions_count = len(quiz_output.questions)
        
        logger.info("framework_concept_statuses_updated")
    
    async def _generate_all_content(
        self, state: RoadmapState, concepts_with_context: list[tuple[Concept, dict]]
    ):
        """
        为所有概念并行生成内容
        
        Returns:
            (new_tutorial_refs, new_resource_refs, new_quiz_refs, new_failed_concepts)
        """
        task_id = state["task_id"]
        user_preferences = state["user_request"].preferences
        
        # 获取已有数据
        existing_tutorial_refs = state.get("tutorial_refs", {})
        existing_resource_refs = state.get("resource_refs", {})
        existing_quiz_refs = state.get("quiz_refs", {})
        
        # 新生成的数据
        new_tutorial_refs = {}
        new_resource_refs = {}
        new_quiz_refs = {}
        new_failed_concepts = []
        
        # 创建 Agents
        tutorial_generator = (
            self.agent_factory.create_tutorial_generator()
            if not self.config.skip_tutorial_generation
            else None
        )
        resource_recommender = (
            self.agent_factory.create_resource_recommender()
            if not self.config.skip_resource_recommendation
            else None
        )
        quiz_generator = (
            self.agent_factory.create_quiz_generator() if not self.config.skip_quiz_generation else None
        )
        
        # 信号量控制并发
        semaphore = asyncio.Semaphore(self.config.parallel_tutorial_limit)
        
        async def generate_content_for_concept(concept: Concept, context: dict):
            """为单个概念并行生成所有内容"""
            async with semaphore:
                results = {
                    "concept_id": concept.concept_id,
                    "tutorial": None,
                    "resources": None,
                    "quiz": None,
                }
                
                # 并行执行三个 Agent
                tasks = []
                
                # A4: 教程生成
                if (
                    tutorial_generator
                    and concept.concept_id not in existing_tutorial_refs
                ):
                    tasks.append(
                        self._generate_tutorial(
                            tutorial_generator,
                            concept,
                            context,
                            user_preferences,
                            task_id,
                        )
                    )
                else:
                    tasks.append(asyncio.coroutine(lambda: None)())
                
                # A5: 资源推荐
                if (
                    resource_recommender
                    and concept.concept_id not in existing_resource_refs
                ):
                    tasks.append(
                        self._generate_resources(
                            resource_recommender, concept, context, user_preferences, task_id
                        )
                    )
                else:
                    tasks.append(asyncio.coroutine(lambda: None)())
                
                # A6: 测验生成
                if quiz_generator and concept.concept_id not in existing_quiz_refs:
                    tasks.append(
                        self._generate_quiz(
                            quiz_generator, concept, context, user_preferences, task_id
                        )
                    )
                else:
                    tasks.append(asyncio.coroutine(lambda: None)())
                
                # 等待所有任务完成
                tutorial_result, resource_result, quiz_result = await asyncio.gather(
                    *tasks, return_exceptions=True
                )
                
                results["tutorial"] = tutorial_result
                results["resources"] = resource_result
                results["quiz"] = quiz_result
                
                return results
        
        # 并行处理所有概念
        concept_tasks = [
            generate_content_for_concept(concept, context)
            for concept, context in concepts_with_context
        ]
        
        all_results = await asyncio.gather(*concept_tasks, return_exceptions=True)
        
        # 整理结果
        for result in all_results:
            if isinstance(result, Exception):
                logger.error(
                    "content_generation_error",
                    task_id=task_id,
                    error=str(result),
                )
                continue
            
            concept_id = result["concept_id"]
            
            # 教程
            if result["tutorial"] and not isinstance(result["tutorial"], Exception):
                new_tutorial_refs[concept_id] = result["tutorial"]
            elif isinstance(result["tutorial"], Exception):
                new_failed_concepts.append(concept_id)
            
            # 资源
            if result["resources"] and not isinstance(result["resources"], Exception):
                new_resource_refs[concept_id] = result["resources"]
            
            # 测验
            if result["quiz"] and not isinstance(result["quiz"], Exception):
                new_quiz_refs[concept_id] = result["quiz"]
        
        # 更新 framework 中的 Concept 状态
        self._update_framework_concept_statuses(
            state.get("roadmap_framework"),
            new_tutorial_refs,
            new_resource_refs,
            new_quiz_refs,
            new_failed_concepts
        )
        
        return new_tutorial_refs, new_resource_refs, new_quiz_refs, new_failed_concepts
    
    async def _generate_tutorial(
        self, agent, concept, context, user_preferences, task_id
    ):
        """生成教程"""
        try:
            input_data = TutorialGenerationInput(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            result = await agent.execute(input_data)
            logger.info(
                "tutorial_generation_success",
                concept_id=concept.concept_id,
                task_id=task_id,
            )
            return result
        except Exception as e:
            logger.error(
                "tutorial_generation_failed",
                concept_id=concept.concept_id,
                task_id=task_id,
                error=str(e),
            )
            return e
    
    async def _generate_resources(self, agent, concept, context, user_preferences, task_id):
        """生成资源推荐"""
        try:
            input_data = ResourceRecommendationInput(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            result = await agent.execute(input_data)
            logger.info(
                "resource_recommendation_success",
                concept_id=concept.concept_id,
                task_id=task_id,
            )
            return result
        except Exception as e:
            logger.error(
                "resource_recommendation_failed",
                concept_id=concept.concept_id,
                task_id=task_id,
                error=str(e),
            )
            return e
    
    async def _generate_quiz(self, agent, concept, context, user_preferences, task_id):
        """生成测验"""
        try:
            input_data = QuizGenerationInput(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            result = await agent.execute(input_data)
            logger.info(
                "quiz_generation_success",
                concept_id=concept.concept_id,
                task_id=task_id,
            )
            return result
        except Exception as e:
            logger.error(
                "quiz_generation_failed",
                concept_id=concept.concept_id,
                task_id=task_id,
                error=str(e),
            )
            return e
    
    async def _update_task_status(self, task_id: str, current_step: str, roadmap_id: str | None):
        """
        更新任务状态到数据库
        
        Args:
            task_id: 任务 ID
            current_step: 当前步骤
            roadmap_id: 路线图 ID
        """
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step=current_step,
                roadmap_id=roadmap_id,
            )
            await session.commit()
            
            logger.debug(
                "task_status_updated",
                task_id=task_id,
                current_step=current_step,
                roadmap_id=roadmap_id,
            )

