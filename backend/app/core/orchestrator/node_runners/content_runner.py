"""
内容生成节点执行器（重构版 - 使用 WorkflowBrain）

负责执行内容生成节点（Step 5: Content Generation）
并行执行教程生成、资源推荐、测验生成三个Agent

重构改进:
- 使用 WorkflowBrain 统一管理状态、日志、通知
- 使用 brain.save_content_results() 批量保存结果
- 代码行数减少 ~70%
"""
import asyncio
import structlog
import time

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
from app.services.execution_logger import execution_logger, LogCategory
from ..base import RoadmapState, WorkflowConfig
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ContentRunner:
    """
    内容生成节点执行器（重构版）
    
    职责：
    1. 并行执行 TutorialGeneratorAgent、ResourceRecommenderAgent、QuizGeneratorAgent
    2. 使用信号量控制并发数量
    3. 处理部分失败场景
    4. 批量保存结果
    
    不再负责:
    - 数据库操作（由 WorkflowBrain 处理）
    - 日志记录（由 WorkflowBrain 处理）
    - 通知发布（由 WorkflowBrain 处理）
    - 状态管理（由 WorkflowBrain 处理）
    """
    
    def __init__(
        self,
        brain: WorkflowBrain,
        config: WorkflowConfig,
        agent_factory: AgentFactory,
    ):
        """
        Args:
            brain: WorkflowBrain 实例（统一协调者）
            config: WorkflowConfig 实例
            agent_factory: AgentFactory 实例
        """
        self.brain = brain
        self.config = config
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行内容生成节点（重构版 - 使用 WorkflowBrain）
        
        简化后的逻辑:
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 并行调用三个 Agent
        3. 使用 brain.save_content_results() 批量保存结果
        4. 返回纯结果
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("content_generation", state):
            framework = state.get("roadmap_framework")
            if not framework:
                raise ValueError("路线图框架不存在，无法生成内容")
            
            # 提取所有概念（三层结构：Stage -> Module -> Concept）
            all_concepts: list[Concept] = []
            for stage in framework.stages:
                for module in stage.modules:
                    all_concepts.extend(module.concepts)
            
            logger.info(
                "content_runner_started",
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
                total_concepts=len(all_concepts),
            )
            
            # 并行生成内容
            tutorial_refs, resource_refs, quiz_refs, failed_concepts = await self._generate_content_parallel(
                state=state,
                concepts=all_concepts,
            )
            
            # 检查失败率，如果过高则中断执行
            total_concepts = len(all_concepts)
            failed_count = len(failed_concepts)
            success_count = total_concepts - failed_count
            failure_rate = failed_count / total_concepts if total_concepts > 0 else 0
            
            # 失败率阈值：如果超过50%的概念生成失败，或者全部失败，则中断执行
            FAILURE_THRESHOLD = 0.5
            
            if failure_rate >= FAILURE_THRESHOLD or failed_count == total_concepts:
                error_message = (
                    f"Content generation failed: {failed_count}/{total_concepts} concepts failed "
                    f"(failure rate: {failure_rate:.1%}). Threshold: {FAILURE_THRESHOLD:.1%}"
                )
                
                # 记录致命错误日志
                await execution_logger.error(
                    task_id=state["task_id"],
                    category=LogCategory.WORKFLOW,
                    step="content_generation",
                    roadmap_id=state.get("roadmap_id"),
                    message=f"❌ Content generation aborted: failure rate too high ({failure_rate:.1%})",
                    details={
                        "log_type": "content_generation_aborted",
                        "total_concepts": total_concepts,
                        "failed_concepts": failed_count,
                        "success_concepts": success_count,
                        "failure_rate": failure_rate,
                        "threshold": FAILURE_THRESHOLD,
                        "failed_concept_ids": failed_concepts,
                    },
                )
                
                logger.error(
                    "content_runner_aborted",
                    task_id=state["task_id"],
                    total_concepts=total_concepts,
                    failed_count=failed_count,
                    failure_rate=failure_rate,
                )
                
                # 抛出异常中断工作流
                raise RuntimeError(error_message)
            
            # 如果有部分失败但未超过阈值，记录警告日志
            if failed_count > 0:
                await execution_logger.warning(
                    task_id=state["task_id"],
                    category=LogCategory.WORKFLOW,
                    step="content_generation",
                    roadmap_id=state.get("roadmap_id"),
                    message=f"⚠️ Content generation completed with {failed_count} failures (failure rate: {failure_rate:.1%})",
                    details={
                        "log_type": "content_generation_partial_failure",
                        "total_concepts": total_concepts,
                        "failed_concepts": failed_count,
                        "success_concepts": success_count,
                        "failure_rate": failure_rate,
                        "failed_concept_ids": failed_concepts,
                    },
                )
            
            # 批量保存结果（由 brain 统一事务管理）
            await self.brain.save_content_results(
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
                tutorial_refs=tutorial_refs,
                resource_refs=resource_refs,
                quiz_refs=quiz_refs,
                failed_concepts=failed_concepts,
            )
            
            # 记录生成结果日志（业务逻辑日志）
            logger.info(
                "content_runner_completed",
                task_id=state["task_id"],
                roadmap_id=state.get("roadmap_id"),
                tutorial_count=len(tutorial_refs),
                resource_count=len(resource_refs),
                quiz_count=len(quiz_refs),
                failed_count=len(failed_concepts),
                failure_rate=failure_rate,
            )
            
            # 返回纯状态更新
            return {
                "tutorial_refs": tutorial_refs,
                "resource_refs": resource_refs,
                "quiz_refs": quiz_refs,
                "failed_concepts": failed_concepts,
                "current_step": "content_generation",
                "execution_history": [
                    f"内容生成完成: {len(tutorial_refs)} 个教程, "
                    f"{len(resource_refs)} 个资源, "
                    f"{len(quiz_refs)} 个测验"
                ],
            }
    
    async def _generate_content_parallel(
        self,
        state: RoadmapState,
        concepts: list[Concept],
    ) -> tuple[
        dict[str, TutorialGenerationOutput],
        dict[str, ResourceRecommendationOutput],
        dict[str, QuizGenerationOutput],
        list[str],
    ]:
        """
        并行生成教程、资源、测验
        
        Args:
            state: 工作流状态
            concepts: 概念列表
            
        Returns:
            (tutorial_refs, resource_refs, quiz_refs, failed_concepts)
        """
        # 创建信号量（控制并发数）
        max_concurrent = self.config.parallel_tutorial_limit
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 并发执行所有概念的内容生成
        tasks = [
            self._generate_single_concept(
                state=state,
                concept=concept,
                semaphore=semaphore,
            )
            for concept in concepts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        tutorial_refs: dict[str, TutorialGenerationOutput] = {}
        resource_refs: dict[str, ResourceRecommendationOutput] = {}
        quiz_refs: dict[str, QuizGenerationOutput] = {}
        failed_concepts: list[str] = []
        
        for i, result in enumerate(results):
            concept_id = concepts[i].concept_id
            
            if isinstance(result, Exception):
                # 异常情况
                logger.error(
                    "content_runner_concept_failed",
                    concept_id=concept_id,
                    error=str(result),
                )
                failed_concepts.append(concept_id)
            elif result:
                # 成功情况
                tutorial, resource, quiz = result
                if tutorial:
                    tutorial_refs[concept_id] = tutorial
                if resource:
                    resource_refs[concept_id] = resource
                if quiz:
                    quiz_refs[concept_id] = quiz
        
        return tutorial_refs, resource_refs, quiz_refs, failed_concepts
    
    async def _generate_single_concept(
        self,
        state: RoadmapState,
        concept: Concept,
        semaphore: asyncio.Semaphore,
    ) -> tuple[
        TutorialGenerationOutput | None,
        ResourceRecommendationOutput | None,
        QuizGenerationOutput | None,
    ] | None:
        """
        为单个概念生成教程、资源、测验
        
        Args:
            state: 工作流状态
            concept: 概念
            semaphore: 信号量（控制并发）
            
        Returns:
            (tutorial, resource, quiz) 或 None（失败时）
        """
        async with semaphore:
            concept_start_time = time.time()
            task_id = state["task_id"]
            roadmap_id = state.get("roadmap_id")
            concept_id = concept.concept_id
            concept_name = concept.name
            
            try:
                # 创建三个 Agent
                tutorial_agent = self.agent_factory.create_tutorial_generator()
                resource_agent = self.agent_factory.create_resource_recommender()
                quiz_agent = self.agent_factory.create_quiz_generator()
                
                # 准备输入
                tutorial_input = TutorialGenerationInput(
                    concept=concept,
                    user_preferences=state["user_request"].preferences,
                    context={
                        "intent_analysis": state.get("intent_analysis"),
                        "roadmap_id": roadmap_id,
                    },
                )
                resource_input = ResourceRecommendationInput(
                    concept=concept,
                    user_preferences=state["user_request"].preferences,
                    context={
                        "intent_analysis": state.get("intent_analysis"),
                        "roadmap_id": roadmap_id,
                    },
                )
                quiz_input = QuizGenerationInput(
                    concept=concept,
                    user_preferences=state["user_request"].preferences,
                    context={
                        "intent_analysis": state.get("intent_analysis"),
                        "roadmap_id": roadmap_id,
                    },
                )
                
                # 记录开始生成日志（新增）
                await execution_logger.info(
                    task_id=task_id,
                    category=LogCategory.WORKFLOW,
                    step="content_generation",
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    message=f"🚀 Generating content for concept: {concept_name}",
                    details={
                        "log_type": "content_generation_start",
                        "concept": {
                            "id": concept_id,
                            "name": concept_name,
                            "difficulty": concept.difficulty,
                        },
                    },
                )
                
                # 并行执行三个 Agent
                tutorial, resource, quiz = await asyncio.gather(
                    tutorial_agent.execute(tutorial_input),
                    resource_agent.execute(resource_input),
                    quiz_agent.execute(quiz_input),
                    return_exceptions=False,  # 让异常传播到上层
                )
                
                # 计算总耗时
                total_duration_ms = int((time.time() - concept_start_time) * 1000)
                
                logger.debug(
                    "content_runner_concept_completed",
                    concept_id=concept_id,
                    has_tutorial=tutorial is not None,
                    has_resource=resource is not None,
                    has_quiz=quiz is not None,
                )
                
                # 记录概念完成日志（新增）
                await execution_logger.info(
                    task_id=task_id,
                    category=LogCategory.WORKFLOW,
                    step="content_generation",
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    message=f"🎉 All content generated for concept: {concept_name}",
                    details={
                        "log_type": "concept_completed",
                        "concept_id": concept_id,
                        "concept_name": concept_name,
                        "completed_content": [
                            "tutorial" if tutorial else None,
                            "resources" if resource else None,
                            "quiz" if quiz else None,
                        ],
                        "content_summary": {
                            "tutorial_chars": len(tutorial.content) if tutorial and hasattr(tutorial, 'content') else 0,
                            "resource_count": len(resource.resources) if resource and hasattr(resource, 'resources') else 0,
                            "quiz_questions": len(quiz.questions) if quiz and hasattr(quiz, 'questions') else 0,
                        },
                        "total_duration_ms": total_duration_ms,
                    },
                    duration_ms=total_duration_ms,
                )
                
                return tutorial, resource, quiz
                
            except Exception as e:
                logger.error(
                    "content_runner_concept_failed_exception",
                    concept_id=concept_id,
                    error=str(e),
                )
                
                # 记录失败日志（新增）
                await execution_logger.error(
                    task_id=task_id,
                    category=LogCategory.AGENT,
                    step="content_generation",
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                    message=f"❌ Content generation failed for concept: {concept_name}",
                    details={
                        "log_type": "content_generation_failed",
                        "concept_id": concept_id,
                        "concept_name": concept_name,
                        "error": str(e)[:500],  # 限制错误消息长度
                        "error_type": type(e).__name__,
                    },
                )
                
                raise  # 传播异常到 gather
