"""
学习路线图相关 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncIterator
import structlog
import uuid
import traceback
import json

from app.models.domain import (
    UserRequest, 
    RoadmapFramework, 
    IntentAnalysisOutput,
    Concept,
    LearningPreferences,
)
from app.db.session import get_db, AsyncSessionLocal
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_orchestrator
from app.core.orchestrator import RoadmapOrchestrator
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.utils.async_helpers import merge_async_iterators
from app.config.settings import settings

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()


async def _execute_roadmap_generation_task(
    request: UserRequest,
    trace_id: str,
    orchestrator: RoadmapOrchestrator,
):
    """
    后台任务执行函数
    
    使用独立的数据库会话，避免请求结束后会话被关闭的问题
    """
    logger.info(
        "background_task_started",
        trace_id=trace_id,
        user_id=request.user_id,
    )
    
    # 为后台任务创建独立的数据库会话
    async with AsyncSessionLocal() as session:
        try:
            service = RoadmapService(session, orchestrator)
            
            logger.info(
                "background_task_executing_workflow",
                trace_id=trace_id,
            )
            
            result = await service.generate_roadmap(request, trace_id)
            
            logger.info(
                "background_task_completed",
                trace_id=trace_id,
                status=result.get("status"),
                roadmap_id=result.get("roadmap_id"),
            )
            
        except Exception as e:
            # 详细记录异常信息
            error_traceback = traceback.format_exc()
            logger.error(
                "background_task_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=error_traceback,
            )
            
            # 尝试更新任务状态为失败
            try:
                # 先回滚之前失败的事务
                await session.rollback()
                
                repo = RoadmapRepository(session)
                await repo.update_task_status(
                    task_id=trace_id,
                    status="failed",
                    current_step="failed",
                    error_message=f"{type(e).__name__}: {str(e)[:500]}",  # 限制错误信息长度
                )
                await session.commit()
                
                logger.info(
                    "background_task_status_updated_to_failed",
                    trace_id=trace_id,
                )
            except Exception as update_error:
                logger.error(
                    "background_task_status_update_failed",
                    trace_id=trace_id,
                    original_error=str(e),
                    update_error=str(update_error),
                )


@router.post("/generate", response_model=dict)
async def generate_roadmap(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    orchestrator: RoadmapOrchestrator = Depends(get_orchestrator),
):
    """
    生成学习路线图（异步任务）
    
    Returns:
        任务 ID，用于后续查询状态
    """
    trace_id = str(uuid.uuid4())
    
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        trace_id=trace_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    # 先创建初始任务记录（使用当前请求的会话）
    repo = RoadmapRepository(db)
    await repo.create_task(
        task_id=trace_id,
        user_id=request.user_id,
        user_request=request.model_dump(mode='json'),
    )
    await repo.update_task_status(
        task_id=trace_id,
        status="processing",
        current_step="queued",
    )
    
    # 在后台任务中执行工作流（使用独立的数据库会话）
    background_tasks.add_task(
        _execute_roadmap_generation_task,
        request,
        trace_id,
        orchestrator,
    )
    
    return {
        "task_id": trace_id,
        "status": "processing",
        "message": "路线图生成任务已启动，请通过 WebSocket 或轮询接口查询进度",
    }


@router.get("/{task_id}/status")
async def get_roadmap_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    orchestrator: RoadmapOrchestrator = Depends(get_orchestrator),
):
    """查询路线图生成状态"""
    service = RoadmapService(db, orchestrator)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return status


@router.get("/{roadmap_id}", response_model=RoadmapFramework)
async def get_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    orchestrator: RoadmapOrchestrator = Depends(get_orchestrator),
):
    """获取完整的路线图数据"""
    service = RoadmapService(db, orchestrator)
    roadmap = await service.get_roadmap(roadmap_id)
    
    if not roadmap:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    return roadmap


@router.post("/{task_id}/approve")
async def approve_roadmap(
    task_id: str,
    approved: bool,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
    orchestrator: RoadmapOrchestrator = Depends(get_orchestrator),
):
    """
    人工审核端点（Human-in-the-Loop）
    
    Args:
        task_id: 任务 ID
        approved: 是否批准
        feedback: 用户反馈（如果未批准）
    """
    service = RoadmapService(db, orchestrator)
    
    try:
        result = await service.handle_human_review(
            task_id=task_id,
            approved=approved,
            feedback=feedback,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("approve_roadmap_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="处理审核结果时发生错误")


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
    save_to_db: bool = True,  # 是否保存到数据库
) -> AsyncIterator[str]:
    """
    生成 SSE 格式的流式数据
    
    Args:
        request: 用户请求
        include_tutorials: 是否包含教程生成阶段
        save_to_db: 是否保存结果到数据库（默认 True）
        
    Yields:
        SSE 格式字符串：
        data: {"type": "chunk", "content": "...", "agent": "..."}
        data: {"type": "complete", "data": {...}, "agent": "..."}
        data: {"type": "tutorials_start", ...}  (如果 include_tutorials=True)
        data: {"type": "batch_start", ...}
        data: {"type": "tutorial_chunk", ...}
        data: {"type": "tutorial_complete", ...}
        data: {"type": "batch_complete", ...}
        data: {"type": "tutorials_done", ...}
        data: {"type": "done", "summary": {...}}
    """
    trace_id = str(uuid.uuid4())  # 生成任务 ID
    tutorial_refs = {}  # 收集生成的教程引用
    
    try:
        logger.info(
            "sse_stream_started",
            user_id=request.user_id,
            learning_goal=request.preferences.learning_goal[:50],
            include_tutorials=include_tutorials,
        )
        
        # 步骤 1: 需求分析（流式）
        intent_analyzer = IntentAnalyzerAgent()
        intent_result = None
        
        logger.info("sse_stream_intent_analysis_starting")
        async for event in intent_analyzer.analyze_stream(request):
            # 转发事件到 SSE 流
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 保存完成结果
            if event["type"] == "complete":
                intent_result = IntentAnalysisOutput.model_validate(event["data"])
                logger.info("sse_stream_intent_analysis_completed")
            elif event["type"] == "error":
                logger.error("sse_stream_intent_analysis_failed", error=event.get("error"))
                return
        
        if not intent_result:
            error_event = {
                "type": "error",
                "message": "需求分析失败：未能获取有效结果",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            return
        
        # 步骤 2: 框架设计（流式）
        architect = CurriculumArchitectAgent()
        framework_result = None
        
        logger.info("sse_stream_curriculum_design_starting")
        async for event in architect.design_stream(intent_result, request.preferences):
            # 转发事件到 SSE 流
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 保存完成结果
            if event["type"] == "complete":
                framework_result = event["data"]
                logger.info("sse_stream_curriculum_design_completed")
            elif event["type"] == "error":
                logger.error("sse_stream_curriculum_design_failed", error=event.get("error"))
                return
        
        if not framework_result:
            error_event = {
                "type": "error",
                "message": "框架设计失败：未能获取有效结果",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            return
        
        # 步骤 3: 教程生成（批次流式，可选）
        tutorials_summary = None
        if include_tutorials:
            logger.info("sse_stream_tutorials_generation_starting")
            
            framework_data = framework_result.get("framework", {})
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
                                    # 构建 TutorialGenerationOutput
                                    from app.models.domain import TutorialGenerationOutput
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
                    trace_id=trace_id,
                    user_id=request.user_id,
                    has_tutorials=bool(tutorial_refs),
                )
                
                async with AsyncSessionLocal() as session:
                    repo = RoadmapRepository(session)
                    
                    # 1. 创建任务记录
                    await repo.create_task(
                        task_id=trace_id,
                        user_id=request.user_id,
                        user_request=request.model_dump(mode='json'),
                    )
                    
                    # 2. 保存路线图元数据
                    framework_obj = RoadmapFramework.model_validate(framework_result.get("framework"))
                    await repo.save_roadmap_metadata(
                        roadmap_id=framework_obj.roadmap_id,
                        user_id=request.user_id,
                        task_id=trace_id,
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
                        task_id=trace_id,
                        status="completed",
                        current_step="completed",
                        roadmap_id=framework_obj.roadmap_id,
                    )
                    
                    await session.commit()
                    
                    logger.info(
                        "sse_stream_saved_to_db",
                        trace_id=trace_id,
                        roadmap_id=framework_obj.roadmap_id,
                        tutorials_count=len(tutorial_refs),
                    )
                    
                    # 在 done_event 中添加 task_id 和 roadmap_id
                    done_event["task_id"] = trace_id
                    done_event["roadmap_id"] = framework_obj.roadmap_id
                    
            except Exception as db_error:
                logger.error(
                    "sse_stream_save_to_db_failed",
                    trace_id=trace_id,
                    error=str(db_error),
                    error_type=type(db_error).__name__,
                )
                # 不影响流式返回，只记录错误
        
        yield f'data: {json.dumps(done_event, ensure_ascii=False)}\n\n'
        
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
        error_event = {
            "type": "error",
            "message": f"流式生成过程发生错误: {str(e)}",
            "agent": "system"
        }
        yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'


@router.post("/generate-stream")
async def generate_roadmap_stream(
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
        - batch_start: {"type": "batch_start", "batch_index": 1, "batch_size": 2, ...}
        - tutorial_start: {"type": "tutorial_start", "concept_id": "...", "concept_name": "..."}
        - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "...", "content": "..."}
        - tutorial_complete: {"type": "tutorial_complete", "concept_id": "...", "data": {...}}
        - tutorial_error: {"type": "tutorial_error", "concept_id": "...", "error": "..."}
        - batch_complete: {"type": "batch_complete", "batch_index": 1, "progress": {...}}
        - tutorials_done: {"type": "tutorials_done", "summary": {...}}
        
        完成：
        - done: {"type": "done", "summary": {...}}
        - error: {"type": "error", "message": "...", "agent": "..."}
    """
    logger.info(
        "generate_roadmap_stream_requested",
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
async def generate_full_roadmap_stream(
    request: UserRequest,
):
    """
    完整流式生成学习路线图（包含教程生成）
    
    这是 /generate-stream?include_tutorials=true 的便捷端点。
    使用 Server-Sent Events (SSE) 实时推送整个生成过程。
    
    流程：需求分析 → 框架设计 → 批次教程生成
    
    Args:
        request: 用户请求
        
    Returns:
        Server-Sent Events 流（包含所有阶段）
    """
    logger.info(
        "generate_full_roadmap_stream_requested",
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


# ============================================================
# 教程版本管理相关端点
# ============================================================

from pydantic import BaseModel, Field


class RegenerateTutorialRequest(BaseModel):
    """重新生成教程请求"""
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


@router.post("/{roadmap_id}/concepts/{concept_id}/regenerate")
async def regenerate_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateTutorialRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定概念的教程（创建新版本）
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户 ID 和学习偏好
        
    Returns:
        新生成的教程元数据（包含版本号）
        
    说明：
    - 重新生成会创建新版本，不会覆盖旧版本
    - 新版本会自动标记为最新（is_latest=True）
    - 旧版本会被标记为非最新（is_latest=False）
    """
    logger.info(
        "regenerate_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=request.user_id,
    )
    
    repo = RoadmapRepository(db)
    
    # 1. 检查路线图是否存在
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # 2. 从路线图框架中获取概念信息
    framework_data = roadmap_metadata.framework_data
    concept_data = None
    context = {"roadmap_id": roadmap_id}
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for c in module.get("concepts", []):
                if c.get("concept_id") == concept_id:
                    concept_data = c
                    context.update({
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    })
                    break
            if concept_data:
                break
        if concept_data:
            break
    
    if not concept_data:
        raise HTTPException(
            status_code=404, 
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中不存在"
        )
    
    # 3. 获取下一个版本号
    next_version = await repo.get_next_tutorial_version(roadmap_id, concept_id)
    context["content_version"] = next_version
    
    logger.info(
        "regenerate_tutorial_version_determined",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        next_version=next_version,
    )
    
    # 4. 构建 Concept 对象
    concept = Concept(
        concept_id=concept_data.get("concept_id"),
        name=concept_data.get("name"),
        description=concept_data.get("description", ""),
        estimated_hours=concept_data.get("estimated_hours", 1.0),
        prerequisites=concept_data.get("prerequisites", []),
        difficulty=concept_data.get("difficulty", "medium"),
        keywords=concept_data.get("keywords", []),
    )
    
    # 5. 生成教程
    try:
        generator = TutorialGeneratorAgent()
        tutorial_output = await generator.generate(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 6. 保存到数据库
        tutorial_metadata = await repo.save_tutorial_metadata(
            tutorial_output=tutorial_output,
            roadmap_id=roadmap_id,
        )
        await db.commit()
        
        logger.info(
            "regenerate_tutorial_success",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            tutorial_id=tutorial_output.tutorial_id,
            content_version=next_version,
            content_url=tutorial_output.content_url,
        )
        
        return {
            "success": True,
            "tutorial_id": tutorial_output.tutorial_id,
            "concept_id": concept_id,
            "roadmap_id": roadmap_id,
            "title": tutorial_output.title,
            "summary": tutorial_output.summary,
            "content_url": tutorial_output.content_url,
            "content_version": next_version,
            "is_latest": True,
            "generated_at": tutorial_output.generated_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(
            "regenerate_tutorial_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"教程生成失败: {str(e)}"
        )


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials")
async def get_tutorial_versions(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的所有教程版本历史
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        
    Returns:
        教程版本列表（按版本号降序，最新版本在前）
    """
    repo = RoadmapRepository(db)
    
    tutorials = await repo.get_tutorial_history(roadmap_id, concept_id)
    
    if not tutorials:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "total_versions": len(tutorials),
        "tutorials": [
            {
                "tutorial_id": t.tutorial_id,
                "title": t.title,
                "summary": t.summary,
                "content_url": t.content_url,
                "content_version": t.content_version,
                "is_latest": t.is_latest,
                "content_status": t.content_status,
                "generated_at": t.generated_at.isoformat() if t.generated_at else None,
            }
            for t in tutorials
        ]
    }


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/latest")
async def get_latest_tutorial(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的最新教程版本
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        
    Returns:
        最新版本的教程元数据
    """
    repo = RoadmapRepository(db)
    
    tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
    
    if not tutorial:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "tutorial_id": tutorial.tutorial_id,
        "title": tutorial.title,
        "summary": tutorial.summary,
        "content_url": tutorial.content_url,
        "content_version": tutorial.content_version,
        "is_latest": tutorial.is_latest,
        "content_status": tutorial.content_status,
        "estimated_completion_time": tutorial.estimated_completion_time,
        "generated_at": tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    }


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}")
async def get_tutorial_by_version(
    roadmap_id: str,
    concept_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的特定版本教程
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        version: 版本号
        
    Returns:
        指定版本的教程元数据
    """
    repo = RoadmapRepository(db)
    
    tutorial = await repo.get_tutorial_by_version(roadmap_id, concept_id, version)
    
    if not tutorial:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 的版本 v{version} 教程不存在"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "tutorial_id": tutorial.tutorial_id,
        "title": tutorial.title,
        "summary": tutorial.summary,
        "content_url": tutorial.content_url,
        "content_version": tutorial.content_version,
        "is_latest": tutorial.is_latest,
        "content_status": tutorial.content_status,
        "estimated_completion_time": tutorial.estimated_completion_time,
        "generated_at": tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    }


# ============================================================
# 资源和测验重新生成端点（复用现有 Generator Agent）
# ============================================================

from app.agents.resource_recommender import ResourceRecommenderAgent
from app.agents.quiz_generator import QuizGeneratorAgent


@router.post("/{roadmap_id}/concepts/{concept_id}/resources/regenerate")
async def regenerate_resources(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateTutorialRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定概念的学习资源
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户 ID 和学习偏好
        
    Returns:
        新生成的资源推荐
    """
    logger.info(
        "regenerate_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=request.user_id,
    )
    
    repo = RoadmapRepository(db)
    
    # 检查路线图是否存在
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # 从路线图框架中获取概念信息
    framework_data = roadmap_metadata.framework_data
    concept_data, context = _find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中不存在"
        )
    
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
    
    # 生成资源推荐
    try:
        from app.models.domain import ResourceRecommendationInput
        
        recommender = ResourceRecommenderAgent()
        resource_output = await recommender.recommend(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 保存到数据库
        await repo.save_resource_recommendation_metadata(resource_output, roadmap_id)
        await db.commit()
        
        logger.info(
            "regenerate_resources_success",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            resources_count=len(resource_output.resources),
        )
        
        return {
            "success": True,
            "id": resource_output.id,
            "concept_id": concept_id,
            "roadmap_id": roadmap_id,
            "resources_count": len(resource_output.resources),
            "resources": [r.model_dump() for r in resource_output.resources],
            "generated_at": resource_output.generated_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(
            "regenerate_resources_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"资源生成失败: {str(e)}")


@router.post("/{roadmap_id}/concepts/{concept_id}/quiz/regenerate")
async def regenerate_quiz(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateTutorialRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定概念的测验
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户 ID 和学习偏好
        
    Returns:
        新生成的测验
    """
    logger.info(
        "regenerate_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=request.user_id,
    )
    
    repo = RoadmapRepository(db)
    
    # 检查路线图是否存在
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # 从路线图框架中获取概念信息
    framework_data = roadmap_metadata.framework_data
    concept_data, context = _find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中不存在"
        )
    
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
    
    # 生成测验
    try:
        generator = QuizGeneratorAgent()
        quiz_output = await generator.generate(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 保存到数据库
        await repo.save_quiz_metadata(quiz_output, roadmap_id)
        await db.commit()
        
        logger.info(
            "regenerate_quiz_success",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            questions_count=quiz_output.total_questions,
        )
        
        return {
            "success": True,
            "quiz_id": quiz_output.quiz_id,
            "concept_id": concept_id,
            "roadmap_id": roadmap_id,
            "total_questions": quiz_output.total_questions,
            "questions": [q.model_dump() for q in quiz_output.questions],
            "generated_at": quiz_output.generated_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(
            "regenerate_quiz_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"测验生成失败: {str(e)}")


def _find_concept_in_framework(
    framework_data: dict,
    concept_id: str,
    roadmap_id: str,
) -> tuple[dict | None, dict]:
    """
    在路线图框架中查找概念
    
    Returns:
        (concept_data, context) 或 (None, {})
    """
    context = {"roadmap_id": roadmap_id}
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for c in module.get("concepts", []):
                if c.get("concept_id") == concept_id:
                    context.update({
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    })
                    return c, context
    
    return None, context


# ============================================================
# 内容修改端点（使用 Modifier Agent）
# ============================================================

from typing import List as TypingList
from app.agents.modification_analyzer import ModificationAnalyzerAgent
from app.agents.tutorial_modifier import TutorialModifierAgent
from app.agents.resource_modifier import ResourceModifierAgent
from app.agents.quiz_modifier import QuizModifierAgent
from app.models.domain import (
    TutorialModificationInput,
    ResourceModificationInput,
    QuizModificationInput,
    Resource,
    QuizQuestion,
    ModificationType,
    BatchModificationResult,
    SingleModificationResult,
)
import asyncio


class ModifyContentRequest(BaseModel):
    """内容修改请求"""
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")
    requirements: TypingList[str] = Field(..., description="具体修改要求列表")


class ChatModificationRequest(BaseModel):
    """聊天修改请求"""
    user_message: str = Field(..., description="用户的自然语言修改意见")
    context: dict | None = Field(None, description="当前上下文（如正在查看的 concept_id）")
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


@router.post("/{roadmap_id}/concepts/{concept_id}/tutorial/modify")
async def modify_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的教程内容
    
    使用 TutorialModifierAgent 增量修改现有教程。
    """
    logger.info(
        "modify_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    repo = RoadmapRepository(db)
    
    # 获取路线图和概念
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    framework_data = roadmap_metadata.framework_data
    concept_data, context = _find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 获取现有教程
    tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 没有教程，请先生成")
    
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
    
    # 添加版本信息到上下文
    context["content_version"] = tutorial.content_version
    
    try:
        modifier = TutorialModifierAgent()
        
        modification_input = TutorialModificationInput(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
            existing_content_url=tutorial.content_url,
            modification_requirements=request.requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        # 保存新版本到数据库
        from app.models.domain import TutorialGenerationOutput
        tutorial_output = TutorialGenerationOutput(
            concept_id=result.concept_id,
            tutorial_id=result.tutorial_id,
            title=result.title,
            summary=result.summary,
            content_url=result.content_url,
            content_status="completed",
            content_version=result.content_version,
            estimated_completion_time=result.estimated_completion_time,
            generated_at=result.generated_at,
        )
        await repo.save_tutorial_metadata(tutorial_output, roadmap_id)
        await db.commit()
        
        return {
            "success": True,
            "concept_id": result.concept_id,
            "tutorial_id": result.tutorial_id,
            "title": result.title,
            "summary": result.summary,
            "content_url": result.content_url,
            "content_version": result.content_version,
            "modification_summary": result.modification_summary,
            "changes_made": result.changes_made,
        }
        
    except Exception as e:
        logger.error(
            "modify_tutorial_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"教程修改失败: {str(e)}")


@router.post("/{roadmap_id}/concepts/{concept_id}/resources/modify")
async def modify_resources(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的学习资源
    
    使用 ResourceModifierAgent 调整现有资源推荐。
    """
    logger.info(
        "modify_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    repo = RoadmapRepository(db)
    
    # 获取路线图和概念
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    framework_data = roadmap_metadata.framework_data
    concept_data, context = _find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 获取现有资源（从数据库）
    resources_list = await repo.get_resource_recommendations_by_roadmap(roadmap_id)
    existing_resources_data = None
    for r in resources_list:
        if r.concept_id == concept_id:
            existing_resources_data = r
            break
    
    if not existing_resources_data:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 没有资源推荐，请先生成")
    
    # 构建 Concept 和现有资源列表
    concept = Concept(
        concept_id=concept_data.get("concept_id"),
        name=concept_data.get("name"),
        description=concept_data.get("description", ""),
        estimated_hours=concept_data.get("estimated_hours", 1.0),
        prerequisites=concept_data.get("prerequisites", []),
        difficulty=concept_data.get("difficulty", "medium"),
        keywords=concept_data.get("keywords", []),
    )
    
    existing_resources = [
        Resource(**r) for r in existing_resources_data.resources
    ]
    
    try:
        modifier = ResourceModifierAgent()
        
        modification_input = ResourceModificationInput(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
            existing_resources=existing_resources,
            modification_requirements=request.requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        # 保存到数据库
        from app.models.domain import ResourceRecommendationOutput
        resource_output = ResourceRecommendationOutput(
            id=result.id,
            concept_id=result.concept_id,
            resources=result.resources,
            search_queries_used=result.search_queries_used,
            generated_at=result.generated_at,
        )
        await repo.save_resource_recommendation_metadata(resource_output, roadmap_id)
        await db.commit()
        
        return {
            "success": True,
            "id": result.id,
            "concept_id": result.concept_id,
            "resources_count": len(result.resources),
            "resources": [r.model_dump() for r in result.resources],
            "modification_summary": result.modification_summary,
            "changes_made": result.changes_made,
        }
        
    except Exception as e:
        logger.error(
            "modify_resources_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"资源修改失败: {str(e)}")


@router.post("/{roadmap_id}/concepts/{concept_id}/quiz/modify")
async def modify_quiz(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的测验题目
    
    使用 QuizModifierAgent 调整现有测验。
    """
    logger.info(
        "modify_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    repo = RoadmapRepository(db)
    
    # 获取路线图和概念
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    framework_data = roadmap_metadata.framework_data
    concept_data, context = _find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 获取现有测验
    existing_quiz = await repo.get_quiz_by_concept(concept_id, roadmap_id)
    if not existing_quiz:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 没有测验，请先生成")
    
    # 构建 Concept 和现有题目列表
    concept = Concept(
        concept_id=concept_data.get("concept_id"),
        name=concept_data.get("name"),
        description=concept_data.get("description", ""),
        estimated_hours=concept_data.get("estimated_hours", 1.0),
        prerequisites=concept_data.get("prerequisites", []),
        difficulty=concept_data.get("difficulty", "medium"),
        keywords=concept_data.get("keywords", []),
    )
    
    existing_questions = [
        QuizQuestion(**q) for q in existing_quiz.questions
    ]
    
    try:
        modifier = QuizModifierAgent()
        
        modification_input = QuizModificationInput(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
            existing_questions=existing_questions,
            modification_requirements=request.requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        # 保存到数据库
        from app.models.domain import QuizGenerationOutput
        quiz_output = QuizGenerationOutput(
            concept_id=result.concept_id,
            quiz_id=result.quiz_id,
            questions=result.questions,
            total_questions=result.total_questions,
            generated_at=result.generated_at,
        )
        await repo.save_quiz_metadata(quiz_output, roadmap_id)
        await db.commit()
        
        return {
            "success": True,
            "quiz_id": result.quiz_id,
            "concept_id": result.concept_id,
            "total_questions": result.total_questions,
            "questions": [q.model_dump() for q in result.questions],
            "modification_summary": result.modification_summary,
            "changes_made": result.changes_made,
        }
        
    except Exception as e:
        logger.error(
            "modify_quiz_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"测验修改失败: {str(e)}")


# ============================================================
# 聊天式修改端点（流式返回）
# ============================================================

def _sse_event(event_type: str, data: dict) -> str:
    """构建 SSE 事件字符串"""
    event_data = {"type": event_type, **data}
    return f'data: {json.dumps(event_data, ensure_ascii=False)}\n\n'


async def _chat_modification_stream(
    roadmap_id: str,
    request: ChatModificationRequest,
) -> AsyncIterator[str]:
    """
    聊天式修改的流式处理
    
    流程：意图分析 → 并行执行修改 → 流式返回结果
    
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
    import time
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
            "message": "正在加载路线图数据...",
        })
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
            
            if not roadmap_metadata:
                yield _sse_event("error", {"message": f"路线图 {roadmap_id} 不存在"})
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
            "message": "正在分析用户修改意图...",
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
            reasoning_preview=analysis_result.analysis_reasoning[:100] if analysis_result.analysis_reasoning else "",
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
                "summary": "需要更多信息来执行修改",
                "results": [],
                "duration_ms": int((time.time() - start_time) * 1000),
            })
            return
        
        # 如果没有识别出意图
        if not analysis_result.intents:
            yield _sse_event("done", {
                "overall_success": False,
                "partial_success": False,
                "summary": "未能识别出修改意图",
                "results": [],
                "duration_ms": int((time.time() - start_time) * 1000),
            })
            return
        
        # 4. 执行修改
        results: TypingList[SingleModificationResult] = []
        
        logger.info(
            "chat_modification_executing",
            roadmap_id=roadmap_id,
            intents_count=len(analysis_result.intents),
            intent_types=[i.modification_type.value for i in analysis_result.intents],
        )
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            for idx, intent in enumerate(analysis_result.intents, 1):
                # 发送正在修改事件
                yield _sse_event("modifying", {
                    "modification_type": intent.modification_type.value,
                    "target_id": intent.target_id,
                    "target_name": intent.target_name,
                    "requirements": intent.specific_requirements,
                    "progress": {"current": idx, "total": len(analysis_result.intents)},
                })
                
                logger.info(
                    "chat_modification_executing_intent",
                    roadmap_id=roadmap_id,
                    intent_idx=idx,
                    modification_type=intent.modification_type.value,
                    target_id=intent.target_id,
                    target_name=intent.target_name,
                )
                
                try:
                    # 发送 Agent 进度事件：准备阶段
                    yield _sse_event("agent_progress", {
                        "agent": f"{intent.modification_type.value}_modifier",
                        "step": "preparing",
                        "details": f"准备修改 {intent.target_name}...",
                    })
                    
                    result = await _execute_single_modification(
                        repo=repo,
                        roadmap_id=roadmap_id,
                        framework_data=roadmap_metadata.framework_data,
                        intent=intent,
                        user_preferences=request.preferences,
                    )
                    results.append(result)
                    
                    logger.info(
                        "chat_modification_intent_completed",
                        roadmap_id=roadmap_id,
                        intent_idx=idx,
                        modification_type=intent.modification_type.value,
                        target_id=intent.target_id,
                        success=result.success,
                        new_version=result.new_version,
                    )
                    
                    # 发送单个修改完成事件
                    yield _sse_event("result", {
                        "modification_type": result.modification_type.value,
                        "target_id": result.target_id,
                        "target_name": result.target_name,
                        "success": result.success,
                        "modification_summary": result.modification_summary,
                        "new_version": result.new_version,
                        "error_message": result.error_message,
                    })
                    
                except Exception as e:
                    logger.error(
                        "chat_modification_intent_failed",
                        roadmap_id=roadmap_id,
                        intent_idx=idx,
                        modification_type=intent.modification_type.value,
                        target_id=intent.target_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    
                    error_result = SingleModificationResult(
                        modification_type=intent.modification_type,
                        target_id=intent.target_id,
                        target_name=intent.target_name,
                        success=False,
                        modification_summary="",
                        error_message=str(e),
                    )
                    results.append(error_result)
                    
                    # 发送错误事件
                    yield _sse_event("result", {
                        "modification_type": intent.modification_type.value,
                        "target_id": intent.target_id,
                        "target_name": intent.target_name,
                        "success": False,
                        "error_message": str(e),
                    })
            
            # 提交所有更改
            await session.commit()
        
        # 5. 发送完成事件
        success_count = sum(1 for r in results if r.success)
        overall_success = success_count == len(results) and len(results) > 0
        partial_success = 0 < success_count < len(results)
        
        total_duration = time.time() - start_time
        
        summary_parts = []
        for r in results:
            if r.success:
                summary_parts.append(f"{r.target_name}: {r.modification_summary}")
            else:
                summary_parts.append(f"{r.target_name}: 失败 - {r.error_message}")
        
        logger.info(
            "chat_modification_stream_completed",
            roadmap_id=roadmap_id,
            overall_success=overall_success,
            partial_success=partial_success,
            success_count=success_count,
            total_count=len(results),
            duration_seconds=total_duration,
        )
        
        yield _sse_event("done", {
            "overall_success": overall_success,
            "partial_success": partial_success,
            "summary": f"完成 {success_count}/{len(results)} 项修改。" + " ".join(summary_parts),
            "results": [
                {
                    "modification_type": r.modification_type.value,
                    "target_id": r.target_id,
                    "target_name": r.target_name,
                    "success": r.success,
                    "modification_summary": r.modification_summary,
                    "new_version": r.new_version,
                    "error_message": r.error_message,
                }
                for r in results
            ],
            "duration_ms": int(total_duration * 1000),
        })
        
    except Exception as e:
        logger.error(
            "chat_modification_stream_error",
            roadmap_id=roadmap_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        yield _sse_event("error", {"message": f"处理过程发生错误: {str(e)}"})


async def _execute_single_modification(
    repo: RoadmapRepository,
    roadmap_id: str,
    framework_data: dict,
    intent,  # SingleModificationIntent
    user_preferences: LearningPreferences,
) -> SingleModificationResult:
    """
    执行单个修改任务
    
    流程：
    1. 查找概念信息
    2. 获取现有内容
    3. 调用对应的 Modifier Agent
    4. 保存新版本
    """
    import time
    start_time = time.time()
    
    logger.info(
        "execute_single_modification_started",
        roadmap_id=roadmap_id,
        modification_type=intent.modification_type.value,
        target_id=intent.target_id,
        target_name=intent.target_name,
        requirements_count=len(intent.specific_requirements),
    )
    
    # 查找概念信息
    concept_data, context = _find_concept_in_framework(
        framework_data, intent.target_id, roadmap_id
    )
    
    if not concept_data:
        logger.warning(
            "execute_single_modification_concept_not_found",
            roadmap_id=roadmap_id,
            target_id=intent.target_id,
        )
        return SingleModificationResult(
            modification_type=intent.modification_type,
            target_id=intent.target_id,
            target_name=intent.target_name,
            success=False,
            modification_summary="",
            error_message=f"概念 {intent.target_id} 不存在",
        )
    
    concept = Concept(
        concept_id=concept_data.get("concept_id"),
        name=concept_data.get("name"),
        description=concept_data.get("description", ""),
        estimated_hours=concept_data.get("estimated_hours", 1.0),
        prerequisites=concept_data.get("prerequisites", []),
        difficulty=concept_data.get("difficulty", "medium"),
        keywords=concept_data.get("keywords", []),
    )
    
    logger.debug(
        "execute_single_modification_concept_found",
        concept_id=concept.concept_id,
        concept_name=concept.name,
    )
    
    # 根据类型执行修改
    if intent.modification_type == ModificationType.TUTORIAL:
        # 获取现有教程
        logger.info(
            "tutorial_modifier_fetching_existing",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
        )
        
        tutorial = await repo.get_latest_tutorial(roadmap_id, intent.target_id)
        if not tutorial:
            logger.warning(
                "tutorial_modifier_not_found",
                roadmap_id=roadmap_id,
                concept_id=intent.target_id,
            )
            return SingleModificationResult(
                modification_type=intent.modification_type,
                target_id=intent.target_id,
                target_name=intent.target_name,
                success=False,
                modification_summary="",
                error_message="教程不存在，请先生成",
            )
        
        logger.info(
            "tutorial_modifier_existing_found",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
            current_version=tutorial.content_version,
            content_url=tutorial.content_url,
        )
        
        context["content_version"] = tutorial.content_version
        
        modifier = TutorialModifierAgent()
        modification_input = TutorialModificationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_content_url=tutorial.content_url,
            modification_requirements=intent.specific_requirements,
        )
        
        logger.info(
            "tutorial_modifier_calling_agent",
            concept_id=intent.target_id,
            requirements=intent.specific_requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        logger.info(
            "tutorial_modifier_agent_completed",
            concept_id=intent.target_id,
            new_version=result.content_version,
            changes_count=len(result.changes_made),
        )
        
        # 保存新版本
        from app.models.domain import TutorialGenerationOutput
        tutorial_output = TutorialGenerationOutput(
            concept_id=result.concept_id,
            tutorial_id=result.tutorial_id,
            title=result.title,
            summary=result.summary,
            content_url=result.content_url,
            content_status="completed",
            content_version=result.content_version,
            estimated_completion_time=result.estimated_completion_time,
            generated_at=result.generated_at,
        )
        await repo.save_tutorial_metadata(tutorial_output, roadmap_id)
        
        duration = time.time() - start_time
        logger.info(
            "execute_single_modification_completed",
            modification_type="tutorial",
            concept_id=intent.target_id,
            new_version=result.content_version,
            duration_seconds=duration,
        )
        
        return SingleModificationResult(
            modification_type=intent.modification_type,
            target_id=intent.target_id,
            target_name=intent.target_name,
            success=True,
            modification_summary=result.modification_summary,
            new_version=result.content_version,
        )
    
    elif intent.modification_type == ModificationType.RESOURCES:
        # 获取现有资源
        logger.info(
            "resource_modifier_fetching_existing",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
        )
        
        resources_list = await repo.get_resource_recommendations_by_roadmap(roadmap_id)
        existing_resources_data = None
        for r in resources_list:
            if r.concept_id == intent.target_id:
                existing_resources_data = r
                break
        
        if not existing_resources_data:
            logger.warning(
                "resource_modifier_not_found",
                roadmap_id=roadmap_id,
                concept_id=intent.target_id,
            )
            return SingleModificationResult(
                modification_type=intent.modification_type,
                target_id=intent.target_id,
                target_name=intent.target_name,
                success=False,
                modification_summary="",
                error_message="资源推荐不存在，请先生成",
            )
        
        existing_resources = [Resource(**r) for r in existing_resources_data.resources]
        
        logger.info(
            "resource_modifier_existing_found",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
            existing_count=len(existing_resources),
        )
        
        modifier = ResourceModifierAgent()
        modification_input = ResourceModificationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_resources=existing_resources,
            modification_requirements=intent.specific_requirements,
        )
        
        logger.info(
            "resource_modifier_calling_agent",
            concept_id=intent.target_id,
            requirements=intent.specific_requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        logger.info(
            "resource_modifier_agent_completed",
            concept_id=intent.target_id,
            new_resources_count=len(result.resources),
            changes_count=len(result.changes_made),
        )
        
        # 保存
        from app.models.domain import ResourceRecommendationOutput
        resource_output = ResourceRecommendationOutput(
            id=result.id,
            concept_id=result.concept_id,
            resources=result.resources,
            search_queries_used=result.search_queries_used,
            generated_at=result.generated_at,
        )
        await repo.save_resource_recommendation_metadata(resource_output, roadmap_id)
        
        duration = time.time() - start_time
        logger.info(
            "execute_single_modification_completed",
            modification_type="resources",
            concept_id=intent.target_id,
            resources_count=len(result.resources),
            duration_seconds=duration,
        )
        
        return SingleModificationResult(
            modification_type=intent.modification_type,
            target_id=intent.target_id,
            target_name=intent.target_name,
            success=True,
            modification_summary=result.modification_summary,
        )
    
    elif intent.modification_type == ModificationType.QUIZ:
        # 获取现有测验
        logger.info(
            "quiz_modifier_fetching_existing",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
        )
        
        existing_quiz = await repo.get_quiz_by_concept(intent.target_id, roadmap_id)
        if not existing_quiz:
            logger.warning(
                "quiz_modifier_not_found",
                roadmap_id=roadmap_id,
                concept_id=intent.target_id,
            )
            return SingleModificationResult(
                modification_type=intent.modification_type,
                target_id=intent.target_id,
                target_name=intent.target_name,
                success=False,
                modification_summary="",
                error_message="测验不存在，请先生成",
            )
        
        existing_questions = [QuizQuestion(**q) for q in existing_quiz.questions]
        
        logger.info(
            "quiz_modifier_existing_found",
            roadmap_id=roadmap_id,
            concept_id=intent.target_id,
            existing_count=len(existing_questions),
        )
        
        modifier = QuizModifierAgent()
        modification_input = QuizModificationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_questions=existing_questions,
            modification_requirements=intent.specific_requirements,
        )
        
        logger.info(
            "quiz_modifier_calling_agent",
            concept_id=intent.target_id,
            requirements=intent.specific_requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        logger.info(
            "quiz_modifier_agent_completed",
            concept_id=intent.target_id,
            new_questions_count=result.total_questions,
            changes_count=len(result.changes_made),
        )
        
        # 保存
        from app.models.domain import QuizGenerationOutput
        quiz_output = QuizGenerationOutput(
            concept_id=result.concept_id,
            quiz_id=result.quiz_id,
            questions=result.questions,
            total_questions=result.total_questions,
            generated_at=result.generated_at,
        )
        await repo.save_quiz_metadata(quiz_output, roadmap_id)
        
        duration = time.time() - start_time
        logger.info(
            "execute_single_modification_completed",
            modification_type="quiz",
            concept_id=intent.target_id,
            questions_count=result.total_questions,
            duration_seconds=duration,
        )
        
        return SingleModificationResult(
            modification_type=intent.modification_type,
            target_id=intent.target_id,
            target_name=intent.target_name,
            success=True,
            modification_summary=result.modification_summary,
        )
    
    else:
        logger.warning(
            "execute_single_modification_unsupported_type",
            modification_type=intent.modification_type.value,
            target_id=intent.target_id,
        )
        return SingleModificationResult(
            modification_type=intent.modification_type,
            target_id=intent.target_id,
            target_name=intent.target_name,
            success=False,
            modification_summary="",
            error_message=f"不支持的修改类型: {intent.modification_type}",
        )


@router.post("/{roadmap_id}/chat-stream")
async def chat_modification_stream(
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
        - result: 单个修改完成
        - done: 全部完成 + 汇总
        - error: 错误信息
    """
    logger.info(
        "chat_modification_stream_requested",
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

