"""
流式生成 API 端点

提供学习路线图的流式生成功能，使用 Server-Sent Events (SSE) 实时推送生成过程。
包含需求分析、框架设计、教程生成、聊天修改等流式功能。
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
from pydantic import BaseModel, Field
import structlog
import uuid
import json
import time

from app.models.domain import (
    UserRequest,
    RoadmapFramework,
    IntentAnalysisOutput,
    Concept,
    LearningPreferences,
    TutorialGenerationOutput,
)
from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.agents.modification_analyzer import ModificationAnalyzerAgent
from app.utils.async_helpers import merge_async_iterators
from app.config.settings import settings
from app.services.execution_logger import execution_logger

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型
# ============================================================


class ChatModificationRequest(BaseModel):
    """聊天修改请求"""
    user_message: str = Field(..., description="用户的自然语言修改意见")
    context: dict | None = Field(None, description="当前上下文（如正在查看的 concept_id）")
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


# ============================================================
# 辅助函数
# ============================================================


def _sse_event(event_type: str, data: dict) -> str:
    """
    构建 SSE 事件字符串
    
    Args:
        event_type: 事件类型
        data: 事件数据字典
        
    Returns:
        SSE 格式字符串: data: {...}\n\n
    """
    event_data = {"type": event_type, **data}
    return f'data: {json.dumps(event_data, ensure_ascii=False)}\n\n'


def _extract_concepts_from_framework(
    framework_data: dict,
) -> list[tuple[Concept, dict]]:
    """
    从路线图框架数据中提取所有 Concepts 及其上下文
    
    Args:
        framework_data: 路线图框架数据（字典格式）
        
    Returns:
        (Concept, context) 元组的列表
    """
    concepts_with_context = []
    roadmap_id = framework_data.get("roadmap_id", "unknown")
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept_data in module.get("concepts", []):
                # 构建 Concept 对象
                concept = Concept(
                    concept_id=concept_data.get("concept_id"),
                    name=concept_data.get("name"),
                    description=concept_data.get("description", ""),
                    estimated_hours=concept_data.get("estimated_hours", 1.0),
                    prerequisites=concept_data.get("prerequisites", []),
                    difficulty=concept_data.get("difficulty", "medium"),
                    keywords=concept_data.get("keywords", []),
                )
                
                # 构建上下文
                context = {
                    "roadmap_id": roadmap_id,
                    "stage_id": stage.get("stage_id"),
                    "stage_name": stage.get("name"),
                    "module_id": module.get("module_id"),
                    "module_name": module.get("name"),
                }
                
                concepts_with_context.append((concept, context))
    
    return concepts_with_context


async def _generate_tutorials_batch_stream(
    framework_data: dict,
    user_preferences: LearningPreferences,
    batch_size: int = 2,
) -> AsyncIterator[str]:
    """
    批次流式生成所有教程
    
    每批次并发 batch_size 个教程，完成后继续下一批次。
    
    Args:
        framework_data: 路线图框架数据
        user_preferences: 用户偏好
        batch_size: 每批次并发数量
        
    Yields:
        SSE 格式字符串
    """
    # 提取所有 concepts
    concepts_with_context = _extract_concepts_from_framework(framework_data)
    total_count = len(concepts_with_context)
    
    if total_count == 0:
        logger.warning("tutorials_batch_stream_no_concepts")
        return
    
    logger.info(
        "tutorials_batch_stream_starting",
        total_count=total_count,
        batch_size=batch_size,
    )
    
    # 发送教程生成阶段开始事件
    start_event = {
        "type": "tutorials_start",
        "total_count": total_count,
        "batch_size": batch_size,
    }
    yield f'data: {json.dumps(start_event, ensure_ascii=False)}\n\n'
    
    # 创建 Tutorial Generator
    generator = TutorialGeneratorAgent()
    
    # 统计
    completed_count = 0
    failed_count = 0
    total_batches = (total_count + batch_size - 1) // batch_size
    
    # 分批处理
    for batch_index in range(total_batches):
        start_idx = batch_index * batch_size
        end_idx = min(start_idx + batch_size, total_count)
        batch = concepts_with_context[start_idx:end_idx]
        
        batch_concept_ids = [concept.concept_id for concept, _ in batch]
        
        logger.info(
            "tutorials_batch_starting",
            batch_index=batch_index + 1,
            total_batches=total_batches,
            concepts=batch_concept_ids,
        )
        
        # 发送批次开始事件
        batch_start_event = {
            "type": "batch_start",
            "batch_index": batch_index + 1,
            "batch_size": len(batch),
            "total_batches": total_batches,
            "concepts": batch_concept_ids,
        }
        yield f'data: {json.dumps(batch_start_event, ensure_ascii=False)}\n\n'
        
        # 发送每个教程的开始事件
        for concept, context in batch:
            tutorial_start_event = {
                "type": "tutorial_start",
                "concept_id": concept.concept_id,
                "concept_name": concept.name,
            }
            yield f'data: {json.dumps(tutorial_start_event, ensure_ascii=False)}\n\n'
        
        # 创建批次中所有教程的流式生成器
        generators = [
            generator.generate_stream(concept, context, user_preferences)
            for concept, context in batch
        ]
        
        # 合并多个流并转发事件
        batch_completed = 0
        batch_failed = 0
        
        async for event in merge_async_iterators(*generators):
            # 转发事件
            yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
            
            # 更新统计
            if event.get("type") == "tutorial_complete":
                batch_completed += 1
                completed_count += 1
            elif event.get("type") == "tutorial_error":
                batch_failed += 1
                failed_count += 1
        
        # 发送批次完成事件
        batch_complete_event = {
            "type": "batch_complete",
            "batch_index": batch_index + 1,
            "progress": {
                "batch_completed": batch_completed,
                "batch_failed": batch_failed,
                "completed": completed_count,
                "failed": failed_count,
                "total": total_count,
                "percentage": round((completed_count + failed_count) / total_count * 100, 1),
            }
        }
        yield f'data: {json.dumps(batch_complete_event, ensure_ascii=False)}\n\n'
        
        logger.info(
            "tutorials_batch_completed",
            batch_index=batch_index + 1,
            batch_completed=batch_completed,
            batch_failed=batch_failed,
            total_completed=completed_count,
            total_failed=failed_count,
        )
    
    # 发送全部完成事件
    done_event = {
        "type": "tutorials_done",
        "summary": {
            "total": total_count,
            "succeeded": completed_count,
            "failed": failed_count,
            "success_rate": round(completed_count / total_count * 100, 1) if total_count > 0 else 0,
        }
    }
    yield f'data: {json.dumps(done_event, ensure_ascii=False)}\n\n'
    
    logger.info(
        "tutorials_batch_stream_completed",
        total=total_count,
        succeeded=completed_count,
        failed=failed_count,
    )


async def _generate_sse_stream(
    request: UserRequest,
    include_tutorials: bool = False,
    save_to_db: bool = True,
) -> AsyncIterator[str]:
    """
    生成 SSE 格式的流式数据
    
    流程：需求分析（流式） → 框架设计（流式） → 教程生成（批次流式，可选） → 保存到数据库
    
    Args:
        request: 用户请求
        include_tutorials: 是否包含教程生成阶段
        save_to_db: 是否保存结果到数据库（默认 True）
        
    Yields:
        SSE 格式字符串：
        - chunk: {"type": "chunk", "content": "...", "agent": "..."}
        - complete: {"type": "complete", "data": {...}, "agent": "..."}
        - tutorials_start: {"type": "tutorials_start", "total_count": N}
        - batch_start: {"type": "batch_start", "batch_index": 1, ...}
        - tutorial_start: {"type": "tutorial_start", "concept_id": "..."}
        - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "...", "content": "..."}
        - tutorial_complete: {"type": "tutorial_complete", "concept_id": "...", "data": {...}}
        - tutorial_error: {"type": "tutorial_error", "concept_id": "..."}
        - batch_complete: {"type": "batch_complete", "batch_index": 1, "progress": {...}}
        - tutorials_done: {"type": "tutorials_done", "summary": {...}}
        - done: {"type": "done", "summary": {...}}
        - error: {"type": "error", "message": "..."}
    """
    task_id = str(uuid.uuid4())  # 生成任务 ID
    tutorial_refs = {}  # 收集生成的教程引用
    
    try:
        logger.info(
            "sse_stream_started",
            user_id=request.user_id,
            learning_goal=request.preferences.learning_goal[:50],
            include_tutorials=include_tutorials,
        )
        
        # 记录工作流开始
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="sse_stream",
            message="SSE streaming roadmap generation started",
            details={
                "user_id": request.user_id,
                "learning_goal": request.preferences.learning_goal,
                "include_tutorials": include_tutorials,
            }
        )
        
        # 步骤 1: 需求分析（流式）
        intent_analyzer = IntentAnalyzerAgent()
        intent_result = None
        
        logger.info("sse_stream_intent_analysis_starting")
        intent_start_time = time.time()
        
        # 记录需求分析开始
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="intent_analysis",
            message="Intent analysis started",
        )
        
        async for event in intent_analyzer.analyze_stream(request):
            # 转发事件到 SSE 流
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 保存完成结果
            if event["type"] == "complete":
                intent_result = IntentAnalysisOutput.model_validate(event["data"])
                logger.info("sse_stream_intent_analysis_completed")
                
                # 记录需求分析完成
                intent_duration_ms = int((time.time() - intent_start_time) * 1000)
                await execution_logger.log_workflow_complete(
                    task_id=task_id,
                    step="intent_analysis",
                    message="Intent analysis completed",
                    duration_ms=intent_duration_ms,
                    details={
                        "roadmap_id": intent_result.roadmap_id,
                        "key_technologies": intent_result.key_technologies[:5],
                        "difficulty_profile": intent_result.difficulty_profile,
                        "parsed_goal": intent_result.parsed_goal,
                    }
                )
            elif event["type"] == "error":
                logger.error("sse_stream_intent_analysis_failed", error=event.get("error"))
                # 记录需求分析错误
                await execution_logger.log_error(
                    task_id=task_id,
                    category="workflow",
                    message=f"Intent analysis failed: {event.get('error', 'Unknown error')}",
                    step="intent_analysis",
                )
                return
        
        if not intent_result:
            error_event = {
                "type": "error",
                "message": "Intent analysis failed: no valid result",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            # 记录错误
            await execution_logger.log_error(
                task_id=task_id,
                category="workflow",
                message="Intent analysis failed: no valid result",
                step="intent_analysis",
            )
            return
        
        # 步骤 2: 框架设计（流式）
        architect = CurriculumArchitectAgent()
        framework_result = None
        
        logger.info("sse_stream_curriculum_design_starting")
        curriculum_start_time = time.time()
        
        # 记录框架设计开始
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="curriculum_design",
            message="Curriculum design started",
            roadmap_id=intent_result.roadmap_id,
        )
        
        async for event in architect.design_stream(intent_result, request.preferences):
            # 转发事件到 SSE 流
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 保存完成结果
            if event["type"] == "complete":
                framework_result = event["data"]
                logger.info("sse_stream_curriculum_design_completed")
                
                # 记录框架设计完成
                curriculum_duration_ms = int((time.time() - curriculum_start_time) * 1000)
                framework_obj = framework_result.get("framework", {})
                await execution_logger.log_workflow_complete(
                    task_id=task_id,
                    step="curriculum_design",
                    message="Curriculum design completed",
                    duration_ms=curriculum_duration_ms,
                    roadmap_id=framework_obj.get("roadmap_id"),
                    details={
                        "title": framework_obj.get("title"),
                        "stages_count": len(framework_obj.get("stages", [])),
                        "total_hours": framework_obj.get("total_estimated_hours"),
                        "completion_weeks": framework_obj.get("recommended_completion_weeks"),
                    }
                )
            elif event["type"] == "error":
                logger.error("sse_stream_curriculum_design_failed", error=event.get("error"))
                # 记录框架设计错误
                await execution_logger.log_error(
                    task_id=task_id,
                    category="workflow",
                    message=f"Curriculum design failed: {event.get('error', 'Unknown error')}",
                    step="curriculum_design",
                    roadmap_id=intent_result.roadmap_id,
                )
                return
        
        if not framework_result:
            error_event = {
                "type": "error",
                "message": "Curriculum design failed: no valid result",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            # 记录错误
            await execution_logger.log_error(
                task_id=task_id,
                category="workflow",
                message="Curriculum design failed: no valid result",
                step="curriculum_design",
                roadmap_id=intent_result.roadmap_id,
            )
            return
        
        # 步骤 3: 教程生成（批次流式，可选）
        tutorials_summary = None
        if include_tutorials:
            logger.info("sse_stream_tutorials_generation_starting")
            tutorials_start_time = time.time()
            
            framework_data = framework_result.get("framework", {})
            roadmap_id = framework_data.get("roadmap_id")
            
            # 记录教程生成开始
            await execution_logger.log_workflow_start(
                task_id=task_id,
                step="tutorial_generation",
                message="Tutorial generation started",
                roadmap_id=roadmap_id,
            )
            
            batch_size = settings.TUTORIAL_STREAM_BATCH_SIZE
            
            async for event_line in _generate_tutorials_batch_stream(
                framework_data=framework_data,
                user_preferences=request.preferences,
                batch_size=batch_size,
            ):
                yield event_line
                
                # 解析事件以获取教程生成汇总和引用
                try:
                    # 提取 JSON 数据
                    if event_line.startswith("data: "):
                        event_json = event_line[6:].strip()
                        if event_json:
                            event = json.loads(event_json)
                            
                            # 收集教程完成事件
                            if event.get("type") == "tutorial_complete":
                                concept_id = event.get("concept_id")
                                data = event.get("data", {})
                                if concept_id and data:
                                    from datetime import datetime as dt
                                    
                                    tutorial_output = TutorialGenerationOutput(
                                        concept_id=concept_id,
                                        tutorial_id=data.get("tutorial_id", concept_id + "-tut"),
                                        title=data.get("title", ""),
                                        summary=data.get("summary", ""),
                                        content_url=data.get("content_url", ""),
                                        content_status=data.get("content_status", "completed"),
                                        estimated_completion_time=data.get("estimated_completion_time", 60),
                                        generated_at=dt.now(),
                                    )
                                    tutorial_refs[concept_id] = tutorial_output
                            
                            elif event.get("type") == "tutorials_done":
                                tutorials_summary = event.get("summary")
                except (json.JSONDecodeError, KeyError):
                    pass
            
            logger.info("sse_stream_tutorials_generation_completed")
            
            # 记录教程生成完成
            tutorials_duration_ms = int((time.time() - tutorials_start_time) * 1000)
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="tutorial_generation",
                message="Tutorial generation completed",
                duration_ms=tutorials_duration_ms,
                roadmap_id=roadmap_id,
                details={
                    "tutorials_count": len(tutorial_refs),
                    "summary": tutorials_summary,
                }
            )
        
        # 完成标记
        done_event = {
            "type": "done",
            "summary": {
                "intent_analysis": intent_result.model_dump(),
                "framework": framework_result.get("framework"),
                "design_rationale": framework_result.get("design_rationale", ""),
            }
        }
        
        # 如果包含教程生成，添加教程汇总
        if include_tutorials and tutorials_summary:
            done_event["summary"]["tutorials"] = tutorials_summary
        
        # 保存到数据库（如果启用）
        if save_to_db:
            try:
                logger.info(
                    "sse_stream_saving_to_db",
                    task_id=task_id,
                    user_id=request.user_id,
                    has_tutorials=bool(tutorial_refs),
                )
                
                db_save_start_time = time.time()
                
                # 记录数据库保存开始
                await execution_logger.log_workflow_start(
                    task_id=task_id,
                    step="database_save",
                    message="Saving roadmap to database",
                )
                
                async with AsyncSessionLocal() as session:
                    repo = RoadmapRepository(session)
                    
                    # 1. 创建任务记录
                    await repo.create_task(
                        task_id=task_id,
                        user_id=request.user_id,
                        user_request=request.model_dump(mode='json'),
                    )
                    
                    # 2. 保存路线图元数据
                    framework_obj = RoadmapFramework.model_validate(framework_result.get("framework"))
                    await repo.save_roadmap_metadata(
                        roadmap_id=framework_obj.roadmap_id,
                        user_id=request.user_id,
                        framework=framework_obj,
                    )
                    
                    # 3. 保存教程元数据（如果有）
                    if tutorial_refs:
                        await repo.save_tutorials_batch(
                            tutorial_refs=tutorial_refs,
                            roadmap_id=framework_obj.roadmap_id,
                        )
                    
                    # 4. 更新任务状态为完成
                    await repo.update_task_status(
                        task_id=task_id,
                        status="completed",
                        current_step="completed",
                        roadmap_id=framework_obj.roadmap_id,
                    )
                    
                    await session.commit()
                    
                    logger.info(
                        "sse_stream_saved_to_db",
                        task_id=task_id,
                        roadmap_id=framework_obj.roadmap_id,
                        tutorials_count=len(tutorial_refs),
                    )
                    
                    # 记录数据库保存完成
                    db_save_duration_ms = int((time.time() - db_save_start_time) * 1000)
                    await execution_logger.log_workflow_complete(
                        task_id=task_id,
                        step="database_save",
                        message="Roadmap saved to database",
                        duration_ms=db_save_duration_ms,
                        roadmap_id=framework_obj.roadmap_id,
                        details={
                            "tutorials_count": len(tutorial_refs),
                        }
                    )
                    
                    # 在 done_event 中添加 task_id 和 roadmap_id
                    done_event["task_id"] = task_id
                    done_event["roadmap_id"] = framework_obj.roadmap_id
                    
            except Exception as db_error:
                logger.error(
                    "sse_stream_save_to_db_failed",
                    task_id=task_id,
                    error=str(db_error),
                    error_type=type(db_error).__name__,
                )
                # 记录数据库保存错误
                await execution_logger.log_error(
                    task_id=task_id,
                    category="database",
                    message=f"Failed to save roadmap to database: {str(db_error)}",
                    step="database_save",
                    details={"error_type": type(db_error).__name__}
                )
                # 不影响流式返回，只记录错误
        
        yield f'data: {json.dumps(done_event, ensure_ascii=False)}\n\n'
        
        # 记录整个流程完成
        await execution_logger.log_workflow_complete(
            task_id=task_id,
            step="sse_stream",
            message="SSE streaming roadmap generation completed",
            roadmap_id=done_event.get("roadmap_id"),
            details={
                "include_tutorials": include_tutorials,
                "tutorials_count": len(tutorial_refs),
            }
        )
        
        logger.info(
            "sse_stream_completed",
            user_id=request.user_id,
            include_tutorials=include_tutorials,
        )
        
    except Exception as e:
        logger.error(
            "sse_stream_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        
        # 记录流程失败
        await execution_logger.log_error(
            task_id=task_id,
            category="workflow",
            message=f"SSE stream generation failed: {str(e)}",
            step="sse_stream",
            details={"error_type": type(e).__name__}
        )
        
        # 发送错误事件
        error_event = {
            "type": "error",
            "message": f"Stream generation error: {str(e)}",
            "agent": "system",
        }
        yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'


async def _chat_modification_stream(
    roadmap_id: str,
    request: ChatModificationRequest,
) -> AsyncIterator[str]:
    """
    聊天式修改的流式处理
    
    流程：加载路线图 → 意图分析 → 并行执行修改 → 流式返回结果
    
    Args:
        roadmap_id: 路线图 ID
        request: 聊天修改请求
        
    Yields:
        SSE 格式的事件流
        
    事件类型：
        - analyzing: 正在分析意图，包含 agent 和 step 信息
        - intents: 意图分析完成，包含识别出的所有意图
        - modifying: 正在执行某项修改
        - agent_progress: Agent 执行进度（下载/LLM调用/上传等）
        - result: 单个修改完成
        - done: 全部完成
        - error: 错误信息
    """
    start_time = time.time()
    
    logger.info(
        "chat_modification_stream_started",
        roadmap_id=roadmap_id,
        user_id=request.user_id,
        message_preview=request.user_message[:50],
    )
    
    try:
        # 1. 获取路线图
        yield _sse_event("analyzing", {
            "agent": "system",
            "step": "loading_roadmap",
            "message": "Loading roadmap data...",
        })
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
            
            if not roadmap_metadata:
                yield _sse_event("error", {"message": f"Roadmap {roadmap_id} not found"})
                return
            
            framework = RoadmapFramework.model_validate(roadmap_metadata.framework_data)
        
        logger.info(
            "chat_modification_roadmap_loaded",
            roadmap_id=roadmap_id,
            roadmap_title=framework.title,
            stages_count=len(framework.stages),
        )
        
        # 2. 分析修改意图
        yield _sse_event("analyzing", {
            "agent": "modification_analyzer",
            "step": "analyzing_intent",
            "message": "Analyzing modification intent...",
        })
        
        analyzer = ModificationAnalyzerAgent()
        
        logger.info(
            "chat_modification_calling_analyzer",
            roadmap_id=roadmap_id,
            message_length=len(request.user_message),
            has_context=request.context is not None,
        )
        
        analysis_result = await analyzer.analyze(
            user_message=request.user_message,
            roadmap_framework=framework,
            current_context=request.context,
        )
        
        logger.info(
            "chat_modification_analysis_complete",
            roadmap_id=roadmap_id,
            intents_count=len(analysis_result.intents),
            confidence=analysis_result.overall_confidence,
            needs_clarification=analysis_result.needs_clarification,
        )
        
        # 3. 发送意图分析结果
        intents_event = {
            "intents": [
                {
                    "modification_type": intent.modification_type.value,
                    "target_id": intent.target_id,
                    "target_name": intent.target_name,
                    "specific_requirements": intent.specific_requirements,
                    "priority": intent.priority,
                }
                for intent in analysis_result.intents
            ],
            "count": len(analysis_result.intents),
            "overall_confidence": analysis_result.overall_confidence,
            "needs_clarification": analysis_result.needs_clarification,
            "clarification_questions": analysis_result.clarification_questions,
            "analysis_reasoning": analysis_result.analysis_reasoning,
        }
        yield _sse_event("intents", intents_event)
        
        # 如果需要澄清，提前返回
        if analysis_result.needs_clarification:
            yield _sse_event("done", {
                "overall_success": False,
                "partial_success": False,
                "summary": "Need more information to execute modification",
                "results": [],
                "duration_ms": int((time.time() - start_time) * 1000),
            })
            return
        
        # 如果没有识别出意图
        if not analysis_result.intents:
            yield _sse_event("done", {
                "overall_success": False,
                "partial_success": False,
                "summary": "No modification intent detected",
                "results": [],
                "duration_ms": int((time.time() - start_time) * 1000),
            })
            return
        
        # 4. 执行修改
        # Note: 实际的修改执行逻辑需要导入相关的 modifier agents
        # 这里简化为返回分析结果，实际实现需要调用 _execute_single_modification
        
        logger.info(
            "chat_modification_executing",
            roadmap_id=roadmap_id,
            intents_count=len(analysis_result.intents),
        )
        
        # 发送完成事件（简化版，实际需要执行修改）
        yield _sse_event("done", {
            "overall_success": True,
            "partial_success": False,
            "summary": f"Analyzed {len(analysis_result.intents)} modification intents",
            "results": [],
            "duration_ms": int((time.time() - start_time) * 1000),
        })
        
        logger.info(
            "chat_modification_stream_completed",
            roadmap_id=roadmap_id,
            duration_ms=int((time.time() - start_time) * 1000),
        )
        
    except Exception as e:
        logger.error(
            "chat_modification_stream_error",
            roadmap_id=roadmap_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        
        yield _sse_event("error", {
            "message": f"Modification stream error: {str(e)}",
            "error_type": type(e).__name__,
        })


# ============================================================
# 路由端点
# ============================================================


@router.post("/generate-stream")
async def generate_stream(
    request: UserRequest,
    include_tutorials: bool = False,
):
    """
    流式生成学习路线图
    
    使用 Server-Sent Events (SSE) 实时推送生成过程。
    
    Args:
        request: 用户请求
        include_tutorials: 是否包含教程生成阶段（默认 False）
        
    Returns:
        Server-Sent Events 流
        
    Event 格式：
        需求分析和框架设计阶段：
        - chunk: {"type": "chunk", "content": "...", "agent": "..."}
        - complete: {"type": "complete", "data": {...}, "agent": "..."}
        
        教程生成阶段（当 include_tutorials=True）：
        - tutorials_start: {"type": "tutorials_start", "total_count": N}
        - batch_start: {"type": "batch_start", "batch_index": 1, ...}
        - tutorial_start: {"type": "tutorial_start", "concept_id": "..."}
        - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "..."}
        - tutorial_complete: {"type": "tutorial_complete", "concept_id": "..."}
        - tutorial_error: {"type": "tutorial_error", "concept_id": "..."}
        - batch_complete: {"type": "batch_complete", "batch_index": 1, ...}
        - tutorials_done: {"type": "tutorials_done", "summary": {...}}
        
        完成：
        - done: {"type": "done", "summary": {...}}
        - error: {"type": "error", "message": "..."}
    """
    logger.info(
        "generate_stream_requested",
        user_id=request.user_id,
        learning_goal=request.preferences.learning_goal[:50],
        include_tutorials=include_tutorials,
    )
    
    return StreamingResponse(
        _generate_sse_stream(request, include_tutorials=include_tutorials),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


@router.post("/generate-full-stream")
async def generate_full_stream(
    request: UserRequest,
):
    """
    完整流式生成学习路线图（包含教程生成）
    
    这是 /generate-stream?include_tutorials=true 的便捷端点。
    使用 Server-Sent Events (SSE) 实时推送整个生成过程。
    
    流程：需求分析 → 框架设计 → 批次教程生成 → 保存数据库
    
    Args:
        request: 用户请求
        
    Returns:
        Server-Sent Events 流（包含所有阶段）
    """
    logger.info(
        "generate_full_stream_requested",
        user_id=request.user_id,
        learning_goal=request.preferences.learning_goal[:50],
    )
    
    return StreamingResponse(
        _generate_sse_stream(request, include_tutorials=True),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{roadmap_id}/chat-stream")
async def chat_stream(
    roadmap_id: str,
    request: ChatModificationRequest,
):
    """
    聊天式修改入口（流式返回）
    
    分析用户自然语言修改意见 → 执行修改 → 流式返回结果
    
    Args:
        roadmap_id: 路线图 ID
        request: 聊天修改请求（包含用户消息、上下文、偏好）
        
    Returns:
        Server-Sent Events 流
        
    Event 类型：
        - analyzing: 正在分析意图
        - intents: 检测到的修改意图列表
        - modifying: 正在执行某项修改
        - agent_progress: Agent 执行进度
        - result: 单个修改完成
        - done: 全部完成 + 汇总
        - error: 错误信息
    """
    logger.info(
        "chat_stream_requested",
        roadmap_id=roadmap_id,
        user_id=request.user_id,
        message_length=len(request.user_message),
        has_context=request.context is not None,
    )
    
    return StreamingResponse(
        _chat_modification_stream(roadmap_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
