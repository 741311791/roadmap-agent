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
from app.core.dependencies import get_workflow_executor
from app.core.orchestrator.executor import WorkflowExecutor
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
    task_id: str,
    orchestrator: WorkflowExecutor,
):
    """
    后台任务执行函数
    
    使用独立的数据库会话，避免请求结束后会话被关闭的问题
    
    Args:
        request: 用户请求
        task_id: 追踪 ID
        orchestrator: 编排器实例
    """
    logger.info(
        "background_task_started",
        task_id=task_id,
        user_id=request.user_id,
    )
    
    # 为后台任务创建独立的数据库会话
    async with AsyncSessionLocal() as session:
        try:
            service = RoadmapService(session, orchestrator)
            
            logger.info(
                "background_task_executing_workflow",
                task_id=task_id,
            )
            
            result = await service.generate_roadmap(
                request, task_id
            )
            
            logger.info(
                "background_task_completed",
                task_id=task_id,
                status=result.get("status"),
                roadmap_id=result.get("roadmap_id"),
            )
            
        except Exception as e:
            # 详细记录异常信息
            error_traceback = traceback.format_exc()
            logger.error(
                "background_task_failed",
                task_id=task_id,
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
                    task_id=task_id,
                    status="failed",
                    current_step="failed",
                    error_message=f"{type(e).__name__}: {str(e)[:500]}",  # 限制错误信息长度
                )
                await session.commit()
                
                logger.info(
                    "background_task_status_updated_to_failed",
                    task_id=task_id,
                )
            except Exception as update_error:
                logger.error(
                    "background_task_status_update_failed",
                    task_id=task_id,
                    original_error=str(e),
                    update_error=str(update_error),
                )


@router.post("/generate", response_model=dict)
async def generate_roadmap(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
):
    """
    生成学习路线图（异步任务）
    
    Returns:
        任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
    """
    task_id = str(uuid.uuid4())
    
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        task_id=task_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    # 先创建初始任务记录（使用当前请求的会话）
    repo = RoadmapRepository(db)
    await repo.create_task(
        task_id=task_id,
        user_id=request.user_id,
        user_request=request.model_dump(mode='json'),
    )
    await repo.update_task_status(
        task_id=task_id,
        status="processing",
        current_step="queued",
    )
    await db.commit()
    
    # 在后台任务中执行工作流（使用独立的数据库会话）
    background_tasks.add_task(
        _execute_roadmap_generation_task,
        request,
        task_id,
        orchestrator,
    )
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "路线图生成任务已启动，roadmap_id将在需求分析完成后通过WebSocket发送",
    }


@router.get("/{task_id}/status")
async def get_roadmap_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
):
    """查询路线图生成状态"""
    service = RoadmapService(db, orchestrator)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return status


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
):
    """
    获取完整的路线图数据
    
    Returns:
        - 如果路线图存在，返回完整的路线图框架数据
        - 如果路线图不存在但有活跃任务，返回生成中状态
        - 如果都不存在，返回 404
    """
    service = RoadmapService(db, orchestrator)
    roadmap = await service.get_roadmap(roadmap_id)
    
    if not roadmap:
        # 检查是否有活跃任务正在生成这个路线图
        repo = RoadmapRepository(db)
        active_task = await repo.get_active_task_by_roadmap_id(roadmap_id)
        
        if active_task:
            # 路线图正在生成中
            return {
                "status": "processing",
                "task_id": active_task.task_id,
                "current_step": active_task.current_step,
                "message": "路线图正在生成中",
                "created_at": active_task.created_at.isoformat() if active_task.created_at else None,
                "updated_at": active_task.updated_at.isoformat() if active_task.updated_at else None,
            }
        
        # 路线图不存在且没有活跃任务
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    return roadmap


@router.get("/{roadmap_id}/active-task")
async def get_roadmap_active_task(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取路线图当前的活跃任务
    
    用于前端轮询：查询该路线图是否有正在进行的任务
    - 如果有正在进行的任务，返回task_id和状态
    - 如果没有，返回null
    
    Args:
        roadmap_id: 路线图 ID
        
    Returns:
        活跃任务信息或null
    """
    repo = RoadmapRepository(db)
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # 获取关联的任务
    task = await repo.get_task(metadata.task_id) if metadata.task_id else None
    
    # 只有当任务状态为 processing 或 human_review_pending 时才算活跃
    if task and task.status in ['processing', 'human_review_pending']:
        return {
            "has_active_task": True,
            "task_id": task.task_id,
            "status": task.status,
            "current_step": task.current_step,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
    else:
        return {
            "has_active_task": False,
            "task_id": None,
            "status": None,
            "current_step": None,
        }


@router.get("/{roadmap_id}/active-retry-task")
async def get_roadmap_active_retry_task(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取路线图当前正在进行的重试任务
    
    用于前端检测是否有正在进行的重试任务：
    - 用户切换 tab 返回时，检查是否有正在进行的重试任务
    - 如果有，前端可以用返回的 task_id 重新订阅 WebSocket
    
    Args:
        roadmap_id: 路线图 ID
        
    Returns:
        正在进行的重试任务信息，包含：
        - has_active_retry_task: 是否有正在进行的重试任务
        - task_id: 重试任务 ID（用于 WebSocket 订阅）
        - current_step: 当前执行步骤
        - items_to_retry: 正在重试的内容类型及数量
        - created_at: 任务创建时间
    """
    repo = RoadmapRepository(db)
    
    # 检查路线图是否存在
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # 获取正在进行的重试任务
    retry_task = await repo.get_active_retry_task_by_roadmap_id(roadmap_id)
    
    if retry_task:
        # 从 user_request 中提取重试信息
        user_request = retry_task.user_request or {}
        items_to_retry = user_request.get("items_to_retry", {})
        content_types = user_request.get("content_types", [])
        
        return {
            "has_active_retry_task": True,
            "task_id": retry_task.task_id,
            "status": retry_task.status,
            "current_step": retry_task.current_step,
            "items_to_retry": items_to_retry,
            "content_types": content_types,
            "created_at": retry_task.created_at.isoformat() if retry_task.created_at else None,
            "updated_at": retry_task.updated_at.isoformat() if retry_task.updated_at else None,
        }
    else:
        return {
            "has_active_retry_task": False,
            "task_id": None,
            "status": None,
            "current_step": None,
            "items_to_retry": None,
            "content_types": None,
        }


@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status_quick(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    快速检查路线图状态，用于检测僵尸状态
    
    检测逻辑：
    1. 获取路线图的 task_id
    2. 检查任务是否还在运行
    3. 如果任务不在运行，但概念状态为 pending/generating，则为僵尸状态
    
    Args:
        roadmap_id: 路线图 ID
        
    Returns:
        {
            "roadmap_id": str,
            "has_active_task": bool,
            "task_status": str | None,
            "stale_concepts": [
                {
                    "concept_id": str,
                    "concept_name": str,
                    "content_type": "tutorial" | "resources" | "quiz",
                    "current_status": "pending" | "generating"
                }
            ]
        }
    """
    repo = RoadmapRepository(db)
    
    # 获取路线图元数据
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # 获取关联的任务状态
    task = await repo.get_task(metadata.task_id) if metadata.task_id else None
    has_active_task = task and task.status in ['pending', 'processing', 'human_review_pending']
    
    # 如果有活跃任务，说明正在正常生成，不是僵尸状态
    if has_active_task:
        return {
            "roadmap_id": roadmap_id,
            "has_active_task": True,
            "task_status": task.status,
            "stale_concepts": [],
        }
    
    # 检查是否有僵尸状态的概念
    framework_data = metadata.framework_data
    stale_concepts = []
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                concept_name = concept.get("name")
                
                # 检查三种内容类型的状态
                checks = [
                    ("tutorial", "content_status"),
                    ("resources", "resources_status"),
                    ("quiz", "quiz_status"),
                ]
                
                for content_type, status_key in checks:
                    status = concept.get(status_key)
                    
                    # pending 或 generating 但没有活跃任务 → 僵尸状态
                    if status in ["pending", "generating"]:
                        stale_concepts.append({
                            "concept_id": concept_id,
                            "concept_name": concept_name,
                            "content_type": content_type,
                            "current_status": status,
                        })
    
    return {
        "roadmap_id": roadmap_id,
        "has_active_task": False,
        "task_status": task.status if task else None,
        "stale_concepts": stale_concepts,
    }


@router.post("/{task_id}/approve")
async def approve_roadmap(
    task_id: str,
    approved: bool,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
    orchestrator: WorkflowExecutor = Depends(get_workflow_executor),
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
    task_id = str(uuid.uuid4())  # 生成任务 ID
    tutorial_refs = {}  # 收集生成的教程引用
    
    # 导入 execution_logger
    from app.services.execution_logger import execution_logger
    import time
    
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
            message="SSE流式路线图生成开始",
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
            message="开始需求分析",
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
                    message="需求分析完成",
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
                    message=f"需求分析失败: {event.get('error', 'Unknown error')}",
                    step="intent_analysis",
                )
                return
        
        if not intent_result:
            error_event = {
                "type": "error",
                "message": "需求分析失败：未能获取有效结果",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            # 记录错误
            await execution_logger.log_error(
                task_id=task_id,
                category="workflow",
                message="需求分析失败：未能获取有效结果",
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
            message="开始课程框架设计",
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
                    message="课程框架设计完成",
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
                    message=f"课程框架设计失败: {event.get('error', 'Unknown error')}",
                    step="curriculum_design",
                    roadmap_id=intent_result.roadmap_id,
                )
                return
        
        if not framework_result:
            error_event = {
                "type": "error",
                "message": "框架设计失败：未能获取有效结果",
                "agent": "system"
            }
            yield f'data: {json.dumps(error_event, ensure_ascii=False)}\n\n'
            # 记录错误
            await execution_logger.log_error(
                task_id=task_id,
                category="workflow",
                message="框架设计失败：未能获取有效结果",
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
                message="开始批量生成教程",
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
            
            # 记录教程生成完成
            tutorials_duration_ms = int((time.time() - tutorials_start_time) * 1000)
            await execution_logger.log_workflow_complete(
                task_id=task_id,
                step="tutorial_generation",
                message="批量教程生成完成",
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
                    message="开始保存路线图到数据库",
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
                        task_id=task_id,
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
                        message="路线图保存到数据库完成",
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
                    message=f"路线图保存到数据库失败: {str(db_error)}",
                    step="database_save",
                    details={"error_type": type(db_error).__name__}
                )
                # 不影响流式返回，只记录错误
        
        yield f'data: {json.dumps(done_event, ensure_ascii=False)}\n\n'
        
        # 记录整个流程完成
        await execution_logger.log_workflow_complete(
            task_id=task_id,
            step="sse_stream",
            message="SSE流式路线图生成完成",
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
        
        # 记录流程失败到execution_logs
        await execution_logger.log_error(
            task_id=task_id,
            category="workflow",
            message=f"SSE流式路线图生成失败: {str(e)}",
            step="sse_stream",
            details={
                "error_type": type(e).__name__,
                "error": str(e),
            }
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
# 断点续传相关端点
# ============================================================

from pydantic import BaseModel, Field
from typing import List as TypingList, Literal as TypingLiteral


class RetryFailedRequest(BaseModel):
    """断点续传请求"""
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")
    content_types: TypingList[TypingLiteral["tutorial", "resources", "quiz"]] = Field(
        default=["tutorial", "resources", "quiz"],
        description="要重试的内容类型列表"
    )


def _get_failed_content_items(framework_data: dict) -> dict:
    """
    获取失败的内容项目
    
    按内容类型分类收集失败的 concepts
    
    Args:
        framework_data: 路线图框架数据
        
    Returns:
        {
            "tutorial": [{"concept_id": "xxx", "concept_data": {...}, "context": {...}}, ...],
            "resources": [...],
            "quiz": [...]
        }
    """
    failed_items = {
        "tutorial": [],
        "resources": [],
        "quiz": [],
    }
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept_data in module.get("concepts", []):
                concept_id = concept_data.get("concept_id")
                context = {
                    "roadmap_id": framework_data.get("roadmap_id"),
                    "stage_id": stage.get("stage_id"),
                    "stage_name": stage.get("name"),
                    "module_id": module.get("module_id"),
                    "module_name": module.get("name"),
                }
                
                # 检查教程状态
                if concept_data.get("content_status") == "failed":
                    failed_items["tutorial"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
                
                # 检查资源状态
                if concept_data.get("resources_status") == "failed":
                    failed_items["resources"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
                
                # 检查测验状态
                if concept_data.get("quiz_status") == "failed":
                    failed_items["quiz"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
    
    return failed_items


@router.post("/{roadmap_id}/retry-failed")
async def retry_failed_content(
    roadmap_id: str,
    request: RetryFailedRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    断点续传：重新生成失败的内容
    
    精确到内容类型粒度，只重跑失败的部分：
    - content_status='failed' 的教程
    - resources_status='failed' 的资源推荐
    - quiz_status='failed' 的测验
    
    Args:
        roadmap_id: 路线图 ID
        request: 包含用户偏好和要重试的内容类型
        
    Returns:
        task_id 用于 WebSocket 订阅进度
    """
    logger.info(
        "retry_failed_content_requested",
        roadmap_id=roadmap_id,
        user_id=request.user_id,
        content_types=request.content_types,
    )
    
    repo = RoadmapRepository(db)
    
    # 1. 检查路线图是否存在
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # 2. 获取失败的内容项目
    failed_items = _get_failed_content_items(roadmap_metadata.framework_data)
    
    # 3. 根据请求筛选要重试的类型
    items_to_retry = {}
    total_items = 0
    for content_type in request.content_types:
        if content_type in failed_items and failed_items[content_type]:
            items_to_retry[content_type] = failed_items[content_type]
            total_items += len(failed_items[content_type])
    
    if total_items == 0:
        return {
            "status": "no_failed_items",
            "message": "没有需要重试的失败项目",
            "failed_counts": {
                "tutorial": len(failed_items["tutorial"]),
                "resources": len(failed_items["resources"]),
                "quiz": len(failed_items["quiz"]),
            }
        }
    
    # 4. 创建重试任务 ID
    retry_task_id = str(uuid.uuid4())
    
    # 5. 创建 RoadmapTask 数据库记录（支持用户切换 tab 返回时查询状态）
    await repo.create_task(
        task_id=retry_task_id,
        user_id=request.user_id,
        user_request={
            "type": "retry_failed",
            "roadmap_id": roadmap_id,
            "content_types": request.content_types,
            "items_to_retry": {
                content_type: len(items) for content_type, items in items_to_retry.items()
            },
            "preferences": request.preferences.model_dump(mode='json'),
        },
    )
    await repo.update_task_status(
        task_id=retry_task_id,
        status="processing",
        current_step="retry_started",
        roadmap_id=roadmap_id,
    )
    await db.commit()
    
    # 6. 启动后台重试任务
    background_tasks.add_task(
        _execute_retry_failed_task,
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        items_to_retry=items_to_retry,
        user_preferences=request.preferences,
        user_id=request.user_id,
    )
    
    return {
        "task_id": retry_task_id,
        "roadmap_id": roadmap_id,
        "status": "processing",
        "items_to_retry": {
            content_type: len(items) for content_type, items in items_to_retry.items()
        },
        "total_items": total_items,
        "message": f"开始重试 {total_items} 个失败项目",
    }


async def _execute_retry_failed_task(
    retry_task_id: str,
    roadmap_id: str,
    items_to_retry: dict,
    user_preferences: LearningPreferences,
    user_id: str,
):
    """
    后台执行重试失败任务
    
    Args:
        retry_task_id: 重试任务 ID（用于 WebSocket 订阅）
        roadmap_id: 路线图 ID
        items_to_retry: 要重试的项目 {"tutorial": [...], "resources": [...], "quiz": [...]}
        user_preferences: 用户偏好
        user_id: 用户 ID（用于日志记录）
    """
    from app.services.notification_service import notification_service
    from app.services.execution_logger import execution_logger
    from app.agents.tutorial_generator import TutorialGeneratorAgent
    from app.agents.resource_recommender import ResourceRecommenderAgent
    from app.agents.quiz_generator import QuizGeneratorAgent
    from app.models.domain import (
        Concept, 
        TutorialGenerationInput, 
        ResourceRecommendationInput, 
        QuizGenerationInput,
    )
    import time
    
    # 记录任务开始时间（用于计算总耗时）
    task_start_time = time.time()
    
    logger.info(
        "retry_failed_task_started",
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        items_count={k: len(v) for k, v in items_to_retry.items()},
    )
    
    # 记录 ExecutionLog：重试任务开始
    await execution_logger.log_workflow_start(
        task_id=retry_task_id,
        step="retry_started",
        message="开始重试失败内容",
        roadmap_id=roadmap_id,
        details={
            "user_id": user_id,
            "items_by_type": {k: len(v) for k, v in items_to_retry.items()},
            "total_items": sum(len(v) for v in items_to_retry.values()),
        },
    )
    
    # 发布重试开始事件
    await notification_service.publish_progress(
        task_id=retry_task_id,
        step="retry_started",
        status="processing",
        message="开始重试失败项目",
        extra_data={
            "roadmap_id": roadmap_id,
            "items_by_type": {k: len(v) for k, v in items_to_retry.items()},
        },
    )
    
    # 创建 Agents
    tutorial_generator = TutorialGeneratorAgent() if "tutorial" in items_to_retry else None
    resource_recommender = ResourceRecommenderAgent() if "resources" in items_to_retry else None
    quiz_generator = QuizGeneratorAgent() if "quiz" in items_to_retry else None
    
    # 统计结果
    success_count = 0
    failed_count = 0
    results = []
    
    # 并发限制
    semaphore = asyncio.Semaphore(settings.PARALLEL_TUTORIAL_LIMIT)
    
    async def retry_single_item(content_type: str, item: dict, current: int, total: int) -> dict:
        """重试单个项目"""
        nonlocal success_count, failed_count
        
        concept_id = item["concept_id"]
        concept_data = item["concept_data"]
        context = item["context"]
        item_start_time = time.time()
        
        # Agent 名称映射
        agent_name_map = {
            "tutorial": "TutorialGenerator",
            "resources": "ResourceRecommender",
            "quiz": "QuizGenerator",
        }
        agent_name = agent_name_map.get(content_type, "UnknownAgent")
        
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
        
        # 记录 ExecutionLog：单个项目开始
        await execution_logger.log_agent_start(
            task_id=retry_task_id,
            agent_name=agent_name,
            message=f"开始重试 {content_type} 内容",
            concept_id=concept_id,
            details={
                "concept_name": concept.name,
                "content_type": content_type,
                "current": current,
                "total": total,
            },
        )
        
        # 发布概念开始事件
        await notification_service.publish_concept_start(
            task_id=retry_task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            current=current,
            total=total,
        )
        
        try:
            async with semaphore:
                if content_type == "tutorial" and tutorial_generator:
                    input_data = TutorialGenerationInput(
                        concept=concept,
                        context=context,
                        user_preferences=user_preferences,
                    )
                    result = await tutorial_generator.execute(input_data)
                    output_data = {
                        "tutorial_id": result.tutorial_id,
                        "content_url": result.content_url,
                    }
                    
                elif content_type == "resources" and resource_recommender:
                    input_data = ResourceRecommendationInput(
                        concept=concept,
                        context=context,
                        user_preferences=user_preferences,
                    )
                    result = await resource_recommender.execute(input_data)
                    output_data = {
                        "resources_id": result.id,
                        "resources_count": len(result.resources),
                    }
                    
                elif content_type == "quiz" and quiz_generator:
                    input_data = QuizGenerationInput(
                        concept=concept,
                        context=context,
                        user_preferences=user_preferences,
                    )
                    result = await quiz_generator.execute(input_data)
                    output_data = {
                        "quiz_id": result.quiz_id,
                        "questions_count": result.total_questions,
                    }
                else:
                    raise ValueError(f"未知的内容类型: {content_type}")
                
                success_count += 1
                item_duration_ms = int((time.time() - item_start_time) * 1000)
                
                # 记录 ExecutionLog：单个项目成功
                await execution_logger.log_agent_complete(
                    task_id=retry_task_id,
                    agent_name=agent_name,
                    message=f"重试 {content_type} 内容成功",
                    duration_ms=item_duration_ms,
                    concept_id=concept_id,
                    details={
                        "concept_name": concept.name,
                        "content_type": content_type,
                        "output": output_data,
                    },
                )
                
                # 发布概念完成事件（使用标准事件）
                await notification_service.publish_concept_complete(
                    task_id=retry_task_id,
                    concept_id=concept_id,
                    concept_name=concept.name,
                    data=output_data,
                )
                
                return {
                    "concept_id": concept_id,
                    "content_type": content_type,
                    "success": True,
                    "result": result,
                }
                
        except Exception as e:
            failed_count += 1
            item_duration_ms = int((time.time() - item_start_time) * 1000)
            
            logger.error(
                "retry_item_failed",
                retry_task_id=retry_task_id,
                concept_id=concept_id,
                content_type=content_type,
                error=str(e),
            )
            
            # 记录 ExecutionLog：单个项目失败
            await execution_logger.log_agent_error(
                task_id=retry_task_id,
                agent_name=agent_name,
                message=f"重试 {content_type} 内容失败",
                error=str(e),
                concept_id=concept_id,
                details={
                    "concept_name": concept.name,
                    "content_type": content_type,
                    "duration_ms": item_duration_ms,
                },
            )
            
            # 发布概念失败事件（使用标准事件）
            await notification_service.publish_concept_failed(
                task_id=retry_task_id,
                concept_id=concept_id,
                concept_name=concept.name,
                error=str(e),
            )
            
            return {
                "concept_id": concept_id,
                "content_type": content_type,
                "success": False,
                "error": str(e),
            }
    
    # 收集所有重试任务
    all_tasks = []
    total_items = sum(len(items) for items in items_to_retry.values())
    current = 0
    
    for content_type, items in items_to_retry.items():
        for item in items:
            current += 1
            all_tasks.append(retry_single_item(content_type, item, current, total_items))
    
    # 并行执行
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    
    # 初始化 remaining_failed（防止后面引用时未定义）
    remaining_failed = {
        "tutorial": 0,
        "resources": 0,
        "quiz": 0,
    }
    
    # 更新数据库中的框架数据
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
        
        if roadmap_metadata:
            framework_data = roadmap_metadata.framework_data
            
            # 更新成功的概念状态
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    concept_id = result["concept_id"]
                    content_type = result["content_type"]
                    output = result.get("result")
                    
                    # 遍历框架更新对应概念的状态
                    for stage in framework_data.get("stages", []):
                        for module in stage.get("modules", []):
                            for concept in module.get("concepts", []):
                                if concept.get("concept_id") == concept_id:
                                    if content_type == "tutorial" and output:
                                        concept["content_status"] = "completed"
                                        concept["content_ref"] = output.content_url
                                        concept["content_summary"] = output.summary
                                    elif content_type == "resources" and output:
                                        concept["resources_status"] = "completed"
                                        concept["resources_id"] = output.id
                                        concept["resources_count"] = len(output.resources)
                                    elif content_type == "quiz" and output:
                                        concept["quiz_status"] = "completed"
                                        concept["quiz_id"] = output.quiz_id
                                        concept["quiz_questions_count"] = output.total_questions
            
            # 保存更新后的框架
            from app.models.domain import RoadmapFramework
            updated_framework = RoadmapFramework.model_validate(framework_data)
            await repo.save_roadmap_metadata(
                roadmap_id=roadmap_id,
                user_id=roadmap_metadata.user_id,
                task_id=roadmap_metadata.task_id,
                framework=updated_framework,
            )
            
            # 同时保存到各自的元数据表
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    content_type = result["content_type"]
                    output = result.get("result")
                    
                    if content_type == "tutorial" and output:
                        await repo.save_tutorial_metadata(output, roadmap_id)
                    elif content_type == "resources" and output:
                        await repo.save_resource_recommendation_metadata(output, roadmap_id)
                    elif content_type == "quiz" and output:
                        await repo.save_quiz_metadata(output, roadmap_id)
            
            await session.commit()
            
            # 计算更新后的失败统计
            remaining_failed = {
                "tutorial": 0,
                "resources": 0,
                "quiz": 0,
            }
            for stage in framework_data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        if concept.get("content_status") == "failed":
                            remaining_failed["tutorial"] += 1
                        if concept.get("resources_status") == "failed":
                            remaining_failed["resources"] += 1
                        if concept.get("quiz_status") == "failed":
                            remaining_failed["quiz"] += 1
    
    # 计算任务总耗时
    task_duration_ms = int((time.time() - task_start_time) * 1000)
    
    # 确定最终状态：如果有成功的项目则视为部分成功，否则为失败
    final_status = "completed" if success_count > 0 else "failed"
    
    # 更新 RoadmapTask 状态
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=retry_task_id,
            status=final_status,
            current_step="retry_completed",
            execution_summary={
                "success_count": success_count,
                "failed_count": failed_count,
                "remaining_failed": remaining_failed,
                "duration_ms": task_duration_ms,
            },
        )
        await session.commit()
    
    # 记录 ExecutionLog：重试任务完成
    await execution_logger.log_workflow_complete(
        task_id=retry_task_id,
        step="retry_completed",
        message=f"重试任务完成: {success_count} 成功, {failed_count} 失败",
        duration_ms=task_duration_ms,
        roadmap_id=roadmap_id,
        details={
            "success_count": success_count,
            "failed_count": failed_count,
            "remaining_failed": remaining_failed,
            "total_items": sum(len(v) for v in items_to_retry.values()),
            "final_status": final_status,
        },
    )
    
    # 发布重试完成事件（包含详细的统计数据）
    await notification_service.publish_completed(
        task_id=retry_task_id,
        roadmap_id=roadmap_id,
        tutorials_count=success_count,
        failed_count=failed_count,
    )
    
    # 发布进度通知，告知前端 framework 已更新
    await notification_service.publish_progress(
        task_id=retry_task_id,
        step="retry_completed",
        status=final_status,
        message=f"重试完成: {success_count} 成功, {failed_count} 失败",
        extra_data={
            "roadmap_id": roadmap_id,
            "success_count": success_count,
            "failed_count": failed_count,
            "remaining_failed": remaining_failed,
            "framework_updated": True,
        },
    )
    
    logger.info(
        "retry_failed_task_completed",
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        success_count=success_count,
        failed_count=failed_count,
        remaining_failed=remaining_failed,
        duration_ms=task_duration_ms,
    )


# ============================================================
# 教程版本管理相关端点
# ============================================================


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
# 资源和测验获取端点
# ============================================================

@router.get("/{roadmap_id}/concepts/{concept_id}/quiz")
async def get_concept_quiz(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的测验
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        
    Returns:
        测验数据，包含题目列表
    """
    repo = RoadmapRepository(db)
    
    quiz = await repo.get_quiz_by_concept(concept_id, roadmap_id)
    
    if not quiz:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有测验"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "quiz_id": quiz.quiz_id,
        "questions": quiz.questions,
        "total_questions": quiz.total_questions,
        "easy_count": quiz.easy_count,
        "medium_count": quiz.medium_count,
        "hard_count": quiz.hard_count,
        "generated_at": quiz.generated_at.isoformat() if quiz.generated_at else None,
    }


@router.get("/{roadmap_id}/concepts/{concept_id}/resources")
async def get_concept_resources(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的学习资源
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        
    Returns:
        资源推荐列表
    """
    repo = RoadmapRepository(db)
    
    resources = await repo.get_resources_by_concept(concept_id, roadmap_id)
    
    if not resources:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有资源推荐"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "resources_id": resources.id,
        "resources": resources.resources,
        "resources_count": resources.resources_count,
        "search_queries_used": resources.search_queries_used,
        "generated_at": resources.generated_at.isoformat() if resources.generated_at else None,
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


# ============================================================
# User Profile API (用户画像)
# ============================================================

from pydantic import BaseModel, Field
from typing import List, Optional as OptionalType


class TechStackItem(BaseModel):
    """技术栈项"""
    technology: str = Field(..., description="技术名称")
    proficiency: str = Field(..., description="熟练程度: beginner, intermediate, expert")


class UserProfileRequest(BaseModel):
    """用户画像请求体"""
    # 职业背景
    industry: OptionalType[str] = Field(None, description="所属行业")
    current_role: OptionalType[str] = Field(None, description="当前职位")
    # 技术栈
    tech_stack: List[TechStackItem] = Field(default=[], description="技术栈列表")
    # 语言偏好
    primary_language: str = Field(default="zh", description="主要语言")
    secondary_language: OptionalType[str] = Field(None, description="次要语言")
    # 学习习惯
    weekly_commitment_hours: int = Field(default=10, ge=1, le=168, description="每周学习时间")
    learning_style: List[str] = Field(default=[], description="学习风格: visual, text, audio, hands_on")
    # AI 个性化
    ai_personalization: bool = Field(default=True, description="是否启用 AI 个性化")


class UserProfileResponse(BaseModel):
    """用户画像响应体"""
    user_id: str
    industry: OptionalType[str] = None
    current_role: OptionalType[str] = None
    tech_stack: List[dict] = []
    primary_language: str = "zh"
    secondary_language: OptionalType[str] = None
    weekly_commitment_hours: int = 10
    learning_style: List[str] = []
    ai_personalization: bool = True
    created_at: OptionalType[str] = None
    updated_at: OptionalType[str] = None


# 创建独立的 users router
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户画像
    
    Args:
        user_id: 用户 ID
        
    Returns:
        用户画像数据，如果不存在则返回默认值
    """
    logger.info("get_user_profile_requested", user_id=user_id)
    
    repo = RoadmapRepository(db)
    profile = await repo.get_user_profile(user_id)
    
    if profile:
        return UserProfileResponse(
            user_id=profile.user_id,
            industry=profile.industry,
            current_role=profile.current_role,
            tech_stack=profile.tech_stack,
            primary_language=profile.primary_language,
            secondary_language=profile.secondary_language,
            weekly_commitment_hours=profile.weekly_commitment_hours,
            learning_style=profile.learning_style,
            ai_personalization=profile.ai_personalization,
            created_at=profile.created_at.isoformat() if profile.created_at else None,
            updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
        )
    else:
        # 返回默认画像
        return UserProfileResponse(
            user_id=user_id,
            tech_stack=[],
            learning_style=[],
        )


@users_router.put("/{user_id}/profile", response_model=UserProfileResponse)
async def save_user_profile(
    user_id: str,
    request: UserProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    保存或更新用户画像
    
    Args:
        user_id: 用户 ID
        request: 用户画像数据
        
    Returns:
        保存后的用户画像
    """
    logger.info(
        "save_user_profile_requested",
        user_id=user_id,
        tech_stack_count=len(request.tech_stack),
    )
    
    repo = RoadmapRepository(db)
    
    # 转换为字典格式
    profile_data = {
        "industry": request.industry,
        "current_role": request.current_role,
        "tech_stack": [item.model_dump() for item in request.tech_stack],
        "primary_language": request.primary_language,
        "secondary_language": request.secondary_language,
        "weekly_commitment_hours": request.weekly_commitment_hours,
        "learning_style": request.learning_style,
        "ai_personalization": request.ai_personalization,
    }
    
    profile = await repo.save_user_profile(user_id, profile_data)
    
    return UserProfileResponse(
        user_id=profile.user_id,
        industry=profile.industry,
        current_role=profile.current_role,
        tech_stack=profile.tech_stack,
        primary_language=profile.primary_language,
        secondary_language=profile.secondary_language,
        weekly_commitment_hours=profile.weekly_commitment_hours,
        learning_style=profile.learning_style,
        ai_personalization=profile.ai_personalization,
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


class RoadmapHistoryItem(BaseModel):
    """路线图历史项"""
    roadmap_id: str
    title: str
    created_at: str
    total_concepts: int
    completed_concepts: int
    topic: OptionalType[str] = None
    status: OptionalType[str] = None
    # 新增字段：用于支持未完成路线图的恢复
    task_id: OptionalType[str] = None
    task_status: OptionalType[str] = None  # processing, pending, human_review_pending 等
    current_step: OptionalType[str] = None  # intent_analysis, curriculum_design 等
    # 软删除相关字段
    deleted_at: OptionalType[str] = None
    deleted_by: OptionalType[str] = None


class RoadmapHistoryResponse(BaseModel):
    """用户路线图历史响应"""
    roadmaps: list[RoadmapHistoryItem]
    total: int
    # 新增字段：进行中的任务数量
    in_progress_count: int = 0


@users_router.get("/{user_id}/roadmaps", response_model=RoadmapHistoryResponse)
async def get_user_roadmaps(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户的路线图列表（只包括已生成完成的路线图）
    
    Args:
        user_id: 用户 ID
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        用户的路线图列表（从 roadmap_metadata 表查询）
    """
    logger.info("get_user_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    repo = RoadmapRepository(db)
    
    # 获取已保存的路线图
    roadmaps = await repo.get_roadmaps_by_user(user_id, limit=limit, offset=offset)
    
    roadmap_items = []
    
    # 转换已保存的路线图
    for roadmap in roadmaps:
        # 从 framework_data 中提取概念信息
        framework_data = roadmap.framework_data or {}
        stages = framework_data.get("stages", [])
        
        total_concepts = 0
        completed_concepts = 0
        
        for stage in stages:
            modules = stage.get("modules", [])
            for module in modules:
                concepts = module.get("concepts", [])
                total_concepts += len(concepts)
                # 统计已完成的概念
                for concept in concepts:
                    if concept.get("content_status") == "completed":
                        completed_concepts += 1
        
        # 从 user_request 中提取 topic
        task = await repo.get_task(roadmap.task_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        # 根据完成度确定状态
        if completed_concepts == total_concepts and total_concepts > 0:
            status = "completed"
        else:
            status = "learning"
        
        roadmap_items.append(RoadmapHistoryItem(
            roadmap_id=roadmap.roadmap_id,
            title=roadmap.title,
            created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
            total_concepts=total_concepts,
            completed_concepts=completed_concepts,
            topic=topic,
            status=status,
        ))
    
    return RoadmapHistoryResponse(
        roadmaps=roadmap_items,
        total=len(roadmap_items),
    )


@users_router.get("/{user_id}/roadmaps/trash", response_model=RoadmapHistoryResponse)
async def get_deleted_roadmaps(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户回收站中的路线图列表
    
    Args:
        user_id: 用户 ID
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        回收站中的路线图列表，按删除时间降序排列
    """
    logger.info("get_deleted_roadmaps_requested", user_id=user_id, limit=limit, offset=offset)
    
    repo = RoadmapRepository(db)
    
    # 获取已删除的路线图
    deleted_roadmaps = await repo.get_deleted_roadmaps(user_id, limit=limit, offset=offset)
    
    roadmap_items = []
    
    # 转换已删除的路线图
    for roadmap in deleted_roadmaps:
        # 从 framework_data 中提取概念信息
        framework_data = roadmap.framework_data or {}
        stages = framework_data.get("stages", [])
        
        total_concepts = 0
        completed_concepts = 0
        
        for stage in stages:
            modules = stage.get("modules", [])
            for module in modules:
                concepts = module.get("concepts", [])
                total_concepts += len(concepts)
                # 统计已完成的概念
                for concept in concepts:
                    if concept.get("content_status") == "completed":
                        completed_concepts += 1
        
        # 从 user_request 中提取 topic
        task = await repo.get_task(roadmap.task_id)
        topic = None
        if task and task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            topic = learning_goal.lower()[:50] if learning_goal else None
        
        roadmap_items.append(RoadmapHistoryItem(
            roadmap_id=roadmap.roadmap_id,
            title=roadmap.title,
            created_at=roadmap.created_at.isoformat() if roadmap.created_at else "",
            total_concepts=total_concepts,
            completed_concepts=completed_concepts,
            topic=topic,
            status="deleted",
            task_id=roadmap.task_id,
            task_status=None,
            current_step=None,
            deleted_at=roadmap.deleted_at.isoformat() if roadmap.deleted_at else None,
            deleted_by=roadmap.deleted_by,
        ))
    
    return RoadmapHistoryResponse(
        roadmaps=roadmap_items,
        total=len(roadmap_items),
        in_progress_count=0,
    )


# ============================================================
# 任务列表 API
# ============================================================

from typing import Optional as OptionalType


class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    status: str  # pending, processing, completed, failed
    current_step: str
    title: str  # 从 user_request 提取
    created_at: str
    updated_at: str
    completed_at: OptionalType[str] = None
    error_message: OptionalType[str] = None
    roadmap_id: OptionalType[str] = None  # 如果任务成功，关联的路线图ID


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskListItem]
    total: int
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int


@users_router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def get_user_tasks(
    user_id: str,
    status: OptionalType[str] = None,  # 筛选：pending, processing, completed, failed
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户的任务列表，支持按状态筛选
    
    Args:
        user_id: 用户 ID
        status: 任务状态筛选（可选）
        limit: 返回数量限制（默认50）
        offset: 分页偏移（默认0）
        
    Returns:
        任务列表及各状态统计
    """
    logger.info("get_user_tasks_requested", user_id=user_id, status=status, limit=limit, offset=offset)
    
    repo = RoadmapRepository(db)
    
    # 查询任务
    tasks = await repo.get_tasks_by_user(user_id, status=status, limit=limit, offset=offset)
    
    # 统计各状态数量（查询全部任务）
    all_tasks = await repo.get_tasks_by_user(user_id)
    stats = {
        "pending": sum(1 for t in all_tasks if t.status == "pending"),
        "processing": sum(1 for t in all_tasks if t.status == "processing"),
        "completed": sum(1 for t in all_tasks if t.status == "completed"),
        "failed": sum(1 for t in all_tasks if t.status == "failed"),
    }
    
    task_items = []
    for task in tasks:
        # 从 user_request 中提取标题
        title = "生成中的路线图"
        if task.user_request:
            learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
            if learning_goal:
                title = learning_goal[:100]
        
        task_items.append(TaskListItem(
            task_id=task.task_id,
            status=task.status,
            current_step=task.current_step,
            title=title,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=task.error_message,
            roadmap_id=task.roadmap_id,
        ))
    
    return TaskListResponse(
        tasks=task_items,
        total=len(task_items),
        pending_count=stats["pending"],
        processing_count=stats["processing"],
        completed_count=stats["completed"],
        failed_count=stats["failed"],
    )


# ============================================================
# Trace / 执行日志 API
# ============================================================

from typing import Optional

trace_router = APIRouter(prefix="/trace", tags=["trace"])


class ExecutionLogResponse(BaseModel):
    """执行日志响应"""
    id: str
    task_id: str
    roadmap_id: Optional[str] = None
    concept_id: Optional[str] = None
    level: str
    category: str
    step: Optional[str] = None
    agent_name: Optional[str] = None
    message: str
    details: Optional[dict] = None
    duration_ms: Optional[int] = None
    created_at: str


class ExecutionLogListResponse(BaseModel):
    """执行日志列表响应"""
    logs: list[ExecutionLogResponse]
    total: int
    offset: int
    limit: int


class TraceSummaryResponse(BaseModel):
    """追踪摘要响应"""
    task_id: str
    level_stats: dict[str, int]
    category_stats: dict[str, int]
    total_duration_ms: int
    first_log_at: Optional[str] = None
    last_log_at: Optional[str] = None
    total_logs: int


@trace_router.get("/{task_id}/logs", response_model=ExecutionLogListResponse)
async def get_trace_logs(
    task_id: str,
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的执行日志
    
    Args:
        task_id: 追踪 ID（通常等于 task_id）
        level: 过滤日志级别（debug, info, warning, error）
        category: 过滤日志分类（workflow, agent, tool, database）
        limit: 返回数量限制（默认 100，最大 500）
        offset: 分页偏移
        
    Returns:
        执行日志列表
    """
    # 限制最大返回数量
    limit = min(limit, 500)
    
    repo = RoadmapRepository(db)
    logs = await repo.get_execution_logs_by_trace(
        task_id=task_id,
        level=level,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    return ExecutionLogListResponse(
        logs=[
            ExecutionLogResponse(
                id=log.id,
                task_id=log.task_id,
                roadmap_id=log.roadmap_id,
                concept_id=log.concept_id,
                level=log.level,
                category=log.category,
                step=log.step,
                agent_name=log.agent_name,
                message=log.message,
                details=log.details,
                duration_ms=log.duration_ms,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=len(logs),  # 简化版本，不查询总数
        offset=offset,
        limit=limit,
    )


@trace_router.get("/{task_id}/summary", response_model=TraceSummaryResponse)
async def get_trace_summary(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的执行摘要
    
    Args:
        task_id: 追踪 ID
        
    Returns:
        执行摘要统计
    """
    repo = RoadmapRepository(db)
    summary = await repo.get_execution_logs_summary(task_id)
    
    return TraceSummaryResponse(**summary)


@trace_router.get("/{task_id}/errors", response_model=ExecutionLogListResponse)
async def get_trace_errors(
    task_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的错误日志
    
    Args:
        task_id: 追踪 ID
        limit: 返回数量限制（默认 50）
        
    Returns:
        错误日志列表
    """
    repo = RoadmapRepository(db)
    logs = await repo.get_error_logs_by_trace(task_id, limit=limit)
    
    return ExecutionLogListResponse(
        logs=[
            ExecutionLogResponse(
                id=log.id,
                task_id=log.task_id,
                roadmap_id=log.roadmap_id,
                concept_id=log.concept_id,
                level=log.level,
                category=log.category,
                step=log.step,
                agent_name=log.agent_name,
                message=log.message,
                details=log.details,
                duration_ms=log.duration_ms,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=len(logs),
        offset=0,
        limit=limit,
    )


# ============================================================
# 路线图删除与回收站相关端点
# ============================================================

@router.delete("/{roadmap_id}")
async def soft_delete_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    删除路线图
    
    根据 roadmap_id 格式自动判断删除方式：
    1. 如果是 "task-{uuid}" 格式：
       - 物理删除 roadmap_tasks 表中的任务记录
       - 适用于失败或进行中的任务（尚未生成完整路线图）
    
    2. 如果是普通格式（如 "python-guide-xxx"）：
       - 软删除 roadmap_metadata 表中的记录（设置 deleted_at 字段）
       - 关联的 roadmap_tasks 记录保留用于追踪
       - 可通过回收站恢复
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果路线图不存在或无权限
    """
    try:
        repo = RoadmapRepository(session)
        from app.models.database import RoadmapTask
        from sqlalchemy import delete
        
        # 检查是否是 task- 前缀的临时 ID
        if roadmap_id.startswith("task-"):
            # 提取真实的 task_id
            actual_task_id = roadmap_id[5:]  # 去掉 "task-" 前缀
            
            logger.info(
                "delete_in_progress_task_requested",
                task_id=actual_task_id,
                user_id=user_id,
            )
            
            # 获取任务信息以验证权限
            task = await repo.get_task(actual_task_id)
            
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail="Task not found"
                )
            
            # 验证用户权限
            if task.user_request and task.user_request.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized to delete this task"
                )
            
            # 删除任务记录（直接从数据库删除）
            stmt = delete(RoadmapTask).where(RoadmapTask.task_id == actual_task_id)
            await session.execute(stmt)
            await session.commit()
            
            logger.info(
                "in_progress_task_deleted",
                task_id=actual_task_id,
                user_id=user_id,
            )
            
            return {
                "success": True,
                "roadmap_id": roadmap_id,
                "task_id": actual_task_id,
                "deleted_at": None,
            }
        
        # 普通格式的 roadmap_id：先检查 metadata 是否存在
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        
        if metadata:
            # Metadata 存在：执行软删除
            if metadata.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized to delete this roadmap"
                )
            
            result = await repo.soft_delete_roadmap(roadmap_id, user_id)
            
            logger.info(
                "roadmap_soft_deleted_via_api",
                roadmap_id=roadmap_id,
                user_id=user_id,
            )
            
            return {
                "success": True,
                "roadmap_id": roadmap_id,
                "deleted_at": result.deleted_at.isoformat() if result.deleted_at else None,
            }
        else:
            # Metadata 不存在：查找对应的 task 并删除
            # 通过 roadmap_id 查找 task
            from sqlalchemy import select
            result = await session.execute(
                select(RoadmapTask).where(RoadmapTask.roadmap_id == roadmap_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found"
                )
            
            # 验证用户权限
            if task.user_request and task.user_request.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized to delete this task"
                )
            
            # 删除任务记录
            stmt = delete(RoadmapTask).where(RoadmapTask.task_id == task.task_id)
            await session.execute(stmt)
            await session.commit()
            
            logger.info(
                "failed_task_deleted_by_roadmap_id",
                roadmap_id=roadmap_id,
                task_id=task.task_id,
                user_id=user_id,
            )
            
            return {
                "success": True,
                "roadmap_id": roadmap_id,
                "task_id": task.task_id,
                "deleted_at": None,
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "soft_delete_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{roadmap_id}/restore")
async def restore_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    从回收站恢复路线图
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        
    Returns:
        恢复结果
        
    Raises:
        HTTPException: 如果路线图不存在或无权限
    """
    try:
        repo = RoadmapRepository(session)
        result = await repo.restore_roadmap(roadmap_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Roadmap not found or unauthorized"
            )
        
        logger.info(
            "roadmap_restored_via_api",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "roadmap_id": roadmap_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "restore_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{roadmap_id}/permanent")
async def permanent_delete_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    永久删除路线图（不可恢复）
    
    警告：此操作会从数据库中永久删除路线图及所有关联数据
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果路线图不存在或无权限
    """
    try:
        repo = RoadmapRepository(session)
        
        # 先验证权限
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata or metadata.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Roadmap not found or unauthorized"
            )
        
        # 执行永久删除
        success = await repo.permanent_delete_roadmap(roadmap_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Roadmap not found"
            )
        
        logger.info(
            "roadmap_permanently_deleted_via_api",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "roadmap_id": roadmap_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "permanent_delete_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

