"""
失败重试相关端点

包含以下功能：
- 重试失败的内容生成
- 重新生成特定概念的内容
- 通过 task_id 重试任务
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog
import uuid

from app.models.domain import LearningPreferences
from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.repositories.task_repo import TaskRepository
from .utils import get_failed_content_items

router = APIRouter(prefix="/roadmaps", tags=["retry"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


class RetryFailedRequest(BaseModel):
    """重试失败内容请求"""
    user_id: str = Field(..., description="用户ID")
    content_types: list[str] = Field(
        default=["tutorial", "resources", "quiz"],
        description="要重试的内容类型列表"
    )
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


class RegenerateContentRequest(BaseModel):
    """重新生成内容请求"""
    user_id: str = Field(..., description="用户ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


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
        background_tasks: FastAPI后台任务
        db: 数据库会话
        
    Returns:
        task_id 用于 WebSocket 订阅进度
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "roadmap_id": "python-web-dev-2024",
            "status": "processing",
            "items_to_retry": {
                "tutorial": 3,
                "resources": 2,
                "quiz": 1
            },
            "total_items": 6,
            "message": "开始重试 6 个失败项目"
        }
        ```
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
    failed_items = get_failed_content_items(roadmap_metadata.framework_data)
    
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
    
    # 4. 创建重试任务
    retry_task_id = str(uuid.uuid4())
    
    # 5. 启动后台重试任务
    from app.services.retry_service import execute_retry_failed_task
    background_tasks.add_task(
        execute_retry_failed_task,
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


@router.post("/{roadmap_id}/concepts/{concept_id}/regenerate")
async def regenerate_concept_content(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定概念的所有内容（教程+资源+测验）
    
    用于用户不满意当前内容，想要完全重新生成的场景
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户 ID 和学习偏好
        db: 数据库会话
        
    Returns:
        重新生成的结果
        
    Raises:
        HTTPException: 404 - 路线图或概念不存在
        
    Example:
        ```json
        {
            "success": true,
            "concept_id": "flask-basics",
            "regenerated": {
                "tutorial": true,
                "resources": true,
                "quiz": true
            },
            "message": "内容重新生成成功"
        }
        ```
    """
    logger.info(
        "regenerate_concept_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=request.user_id,
    )
    
    # 实现逻辑：调用service层进行重新生成
    # 这里是简化版本，完整实现在roadmap_service中
    repo = RoadmapRepository(db)
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # TODO: 实现完整的重新生成逻辑
    # 当前返回占位响应
    return {
        "success": True,
        "concept_id": concept_id,
        "message": "内容重新生成功能正在开发中",
    }


# ============================================================
# 基于 Task ID 的重试端点
# ============================================================

@tasks_router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    user_id: str = Query(..., description="用户ID"),
    force_checkpoint: bool = Query(False, description="强制使用 checkpoint 恢复"),
    db: AsyncSession = Depends(get_db),
):
    """
    智能重试失败的任务（Celery 异步）
    
    两种重试策略：
    1. **Checkpoint 恢复**（粗粒度）：
       - 适用于工作流早期阶段失败（intent_analysis, curriculum_design, validation, edit等）
       - 从 LangGraph checkpoint 恢复，继续执行工作流
       - 保留所有中间状态
    
    2. **内容重试**（细粒度）：
       - 适用于内容生成阶段部分失败
       - 扫描 framework_data，只重新生成失败的 Concept 内容
       - 节省 API 调用成本
    
    自动判断逻辑：
    - 如果存在 checkpoint 且任务失败在内容生成之前 → Checkpoint 恢复
    - 如果有失败的 Concept 内容 → 内容重试
    - 如果 force_checkpoint=true → 强制使用 Checkpoint 恢复
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        force_checkpoint: 强制使用 checkpoint 恢复
        db: 数据库会话
        
    Returns:
        重试任务的信息
        
    Raises:
        HTTPException: 404 - 任务不存在
        HTTPException: 400 - 无法重试（没有 checkpoint 也没有失败内容）
    """
    from app.tasks.workflow_resume_tasks import resume_from_checkpoint
    from app.tasks.content_generation_tasks import retry_failed_content_task
    
    logger.info(
        "retry_task_requested",
        task_id=task_id,
        user_id=user_id,
        force_checkpoint=force_checkpoint,
    )
    
    # 1. 查询任务记录
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_task_id(task_id)
    
    if not task:
        logger.warning("task_not_found", task_id=task_id)
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 不存在"
        )
    
    # 2. 检查 checkpoint 是否存在
    from app.core.orchestrator_factory import OrchestratorFactory
    
    checkpoint_exists = False
    checkpoint_step = None
    
    try:
        checkpointer = OrchestratorFactory.get_checkpointer()
        config = {"configurable": {"thread_id": task_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if checkpoint_tuple and checkpoint_tuple.checkpoint:
            checkpoint_exists = True
            channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
            checkpoint_step = channel_values.get("current_step")
            
            logger.info(
                "checkpoint_found",
                task_id=task_id,
                checkpoint_step=checkpoint_step,
            )
    except Exception as e:
        logger.warning(
            "checkpoint_check_failed",
            task_id=task_id,
            error=str(e),
        )
    
    # 3. 判断重试策略
    EARLY_STAGE_STEPS = [
        "init", "queued", "intent_analysis", "curriculum_design",
        "structure_validation", "roadmap_edit", "human_review"
    ]
    
    # content_generation_queued 是一个特殊状态：
    # - Celery 任务已提交，但内容生成在独立进程中进行
    # - 从 checkpoint 恢复时，LangGraph 不会重新执行 ContentRunner
    # - 因此不应该使用 checkpoint 恢复，而应该走内容重试逻辑
    CONTENT_GENERATION_STEPS = ["content_generation_queued"]
    
    is_early_stage_failure = (
        task.current_step in EARLY_STAGE_STEPS or
        (checkpoint_step and checkpoint_step in EARLY_STAGE_STEPS)
    )
    
    is_content_generation_stage = (
        task.current_step in CONTENT_GENERATION_STEPS or
        (checkpoint_step and checkpoint_step in CONTENT_GENERATION_STEPS)
    )
    
    # 特殊处理：cancelled 状态的任务
    # 如果任务被手动取消，应该优先尝试从 checkpoint 恢复（如果存在）
    # 但如果停在 content_generation_queued，不使用 checkpoint 恢复
    is_cancelled = task.status == "cancelled"
    
    # 策略决策
    use_checkpoint_recovery = (
        checkpoint_exists and (
            force_checkpoint or
            (is_early_stage_failure and not is_content_generation_stage) or
            (is_cancelled and not is_content_generation_stage)  # cancelled 但不在内容生成阶段
        )
    )
    
    # ============================================================
    # 策略 1：从 Checkpoint 恢复（粗粒度）- 使用 Celery
    # ============================================================
    if use_checkpoint_recovery:
        logger.info(
            "using_checkpoint_recovery",
            task_id=task_id,
            checkpoint_step=checkpoint_step,
        )
        
        # 分发 Celery 任务从 checkpoint 恢复
        celery_task = resume_from_checkpoint.delay(task_id=task_id)
        
        logger.info(
            "checkpoint_recovery_dispatched",
            task_id=task_id,
            celery_task_id=celery_task.id,
        )
        
        return {
            "success": True,
            "recovery_type": "checkpoint",
            "task_id": task_id,
            "roadmap_id": task.roadmap_id,
            "checkpoint_step": checkpoint_step,
            "status": "recovering",
            "message": f"正在从 checkpoint 恢复（步骤：{checkpoint_step}）",
        }
    
    # ============================================================
    # 策略 2：内容重试（细粒度）- 使用 Celery
    # ============================================================
    
    # 检查是否有 roadmap_id
    if not task.roadmap_id:
        raise HTTPException(
            status_code=400,
            detail="任务尚未生成路线图，无法进行内容重试"
        )
    
    roadmap_id = task.roadmap_id
    roadmap_repo = RoadmapRepository(db)
    roadmap_metadata = await roadmap_repo.get_roadmap_metadata(roadmap_id)
    
    if not roadmap_metadata:
        raise HTTPException(
            status_code=404,
            detail=f"路线图 {roadmap_id} 不存在"
        )
    
    # 获取失败的内容项目（从 framework_data）
    failed_items = get_failed_content_items(roadmap_metadata.framework_data)
    
    # 筛选要重试的类型
    content_types = ["tutorial", "resources", "quiz"]
    items_to_retry = {}
    total_items = 0
    for content_type in content_types:
        if content_type in failed_items and failed_items[content_type]:
            items_to_retry[content_type] = failed_items[content_type]
            total_items += len(failed_items[content_type])
    
    # 如果 framework_data 中没有失败的项目，尝试从数据库查询
    # 这处理了 framework_data 未更新的情况
    if total_items == 0:
        logger.info(
            "no_failed_items_in_framework_checking_database",
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 获取所有概念
        all_concept_ids = []
        for stage in roadmap_metadata.framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    all_concept_ids.append(concept.get("concept_id"))
        
        # 查询已完成的教程
        completed_tutorials = await roadmap_repo.get_tutorials_by_roadmap(
            roadmap_id=roadmap_id,
            latest_only=True,
        )
        completed_concept_ids = {
            tutorial.concept_id 
            for tutorial in completed_tutorials 
            if tutorial.content_status == "completed"
        }
        
        # 找出缺失的概念
        missing_concept_ids = set(all_concept_ids) - completed_concept_ids
        
        if missing_concept_ids:
            logger.info(
                "found_missing_concepts_in_database",
                task_id=task_id,
                roadmap_id=roadmap_id,
                missing_count=len(missing_concept_ids),
                missing_concepts=list(missing_concept_ids)[:10],
            )
            
            # 构造重试项目列表
            items_to_retry["tutorial"] = []
            for stage in roadmap_metadata.framework_data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        concept_id = concept.get("concept_id")
                        if concept_id in missing_concept_ids:
                            items_to_retry["tutorial"].append({
                                "concept_id": concept_id,
                                "concept_data": concept,
                                "context": {
                                    "roadmap_id": roadmap_id,
                                    "stage_id": stage.get("stage_id"),
                                    "stage_name": stage.get("name"),
                                    "module_id": module.get("module_id"),
                                    "module_name": module.get("name"),
                                },
                            })
            
            total_items = len(items_to_retry.get("tutorial", []))
    
    if total_items == 0:
        # 特殊处理：cancelled 状态的任务，即使没有失败内容
        if is_cancelled:
            # 如果任务在 content_generation 阶段被取消，且已有路线图框架
            # 应该直接重新触发内容生成，复用已审核/编辑的框架
            # 而不是从头创建新任务（这会导致丢失用户的编辑）
            if roadmap_metadata and roadmap_metadata.framework_data:
                logger.info(
                    "cancelled_task_retry_content_generation",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
                
                # 提取所有概念（作为待生成内容）
                framework_data = roadmap_metadata.framework_data
                all_concepts = []
                
                for stage in framework_data.get("stages", []):
                    for module in stage.get("modules", []):
                        for concept in module.get("concepts", []):
                            all_concepts.append({
                                "concept_id": concept.get("concept_id"),
                                "concept_data": concept,
                            })
                
                if not all_concepts:
                    raise HTTPException(
                        status_code=400,
                        detail="路线图框架中没有概念，无法生成内容"
                    )
                
                logger.info(
                    "restarting_content_generation_for_cancelled_task",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    total_concepts=len(all_concepts),
                )
                
                # 从原任务提取 user_request
                user_request_dict = task.user_request or {}
                preferences_dict = user_request_dict.get("preferences", {})
                
                try:
                    preferences = LearningPreferences.model_validate(preferences_dict)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_preferences_using_defaults",
                        task_id=task_id,
                        error=str(e),
                    )
                    preferences = LearningPreferences(
                        learning_goal="Complete the roadmap",
                        time_commitment="1-2 hours per day",
                        difficulty_level="intermediate",
                        preferred_languages=["en"],
                    )
                
                # 更新任务状态为 processing，并确保 roadmap_id 被设置
                await task_repo.update_task_status(
                    task_id=task_id,
                    status="processing",
                    current_step="content_generation_queued",
                    roadmap_id=roadmap_id,  # ✅ 传递 roadmap_id，确保前端能获取到
                )
                await db.commit()
                
                # 发送 WebSocket 通知，告知前端任务已重新开始
                from app.services.notification_service import notification_service
                await notification_service.publish_progress(
                    task_id=task_id,
                    step="content_generation_queued",
                    status="processing",
                    message=f"Restarting content generation with existing framework ({len(all_concepts)} concepts)",
                    extra_data={
                        "roadmap_id": roadmap_id,
                        "total_concepts": len(all_concepts),
                        "recovery_type": "restart_content_generation",
                    },
                )
                
                # 直接调用内容生成 Celery 任务，复用现有框架
                from app.tasks.content_generation_tasks import generate_roadmap_content
                
                celery_task = generate_roadmap_content.delay(
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    roadmap_framework_data=framework_data,
                    user_preferences_data=preferences.model_dump(mode='json'),
                )
                
                logger.info(
                    "content_generation_restarted_for_cancelled_task",
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    celery_task_id=celery_task.id,
                    total_concepts=len(all_concepts),
                )
                
                return {
                    "success": True,
                    "recovery_type": "restart_content_generation",
                    "task_id": task_id,
                    "roadmap_id": roadmap_id,
                    "status": "processing",
                    "total_concepts": len(all_concepts),
                    "message": f"已重新开始内容生成（复用现有框架，共 {len(all_concepts)} 个概念）",
                }
        
        # 没有失败的内容，也没有可用的 checkpoint
        logger.warning(
            "no_retry_option_available",
            task_id=task_id,
            roadmap_id=roadmap_id,
            checkpoint_exists=checkpoint_exists,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "无法重试此任务：\n"
                "- 没有失败的 Concept 内容\n"
                f"- Checkpoint {'不存在' if not checkpoint_exists else '存在但任务已完成内容生成'}\n"
                "提示：如果任务在早期阶段失败，请使用 force_checkpoint=true 参数"
            )
        )
    
    logger.info(
        "using_content_retry",
        task_id=task_id,
        total_items=total_items,
    )
    
    # 从原任务的 user_request 中提取 preferences（如果有）
    user_request = task.user_request or {}
    preferences_dict = user_request.get("preferences", {})
    
    # 使用默认偏好或从任务中提取
    try:
        preferences = LearningPreferences.model_validate(preferences_dict)
    except Exception as e:
        logger.warning(
            "failed_to_parse_preferences",
            task_id=task_id,
            error=str(e)
        )
        # 使用默认偏好
        preferences = LearningPreferences(
            learning_goal="Complete the roadmap",
            time_commitment="1-2 hours per day",
            difficulty_level="intermediate",
            preferred_languages=["en"]
        )
    
    # 分发 Celery 任务进行内容重试
    # 传递 items_to_retry 避免 Worker 重复查询（解决主应用和Worker检测逻辑不一致的问题）
    celery_task = retry_failed_content_task.delay(
        roadmap_id=roadmap_id,
        task_id=task_id,
        user_id=user_id,
        preferences=preferences.model_dump(mode='json'),
        content_types=content_types,
        items_to_retry=items_to_retry,
    )
    
    logger.info(
        "content_retry_dispatched",
        task_id=task_id,
        roadmap_id=roadmap_id,
        celery_task_id=celery_task.id,
        total_items=total_items,
    )
    
    return {
        "success": True,
        "recovery_type": "content_retry",
        "task_id": task_id,
        "roadmap_id": roadmap_id,
        "status": "processing",
        "items_to_retry": {
            content_type: len(items) for content_type, items in items_to_retry.items()
        },
        "total_items": total_items,
        "message": f"开始重试 {total_items} 个失败项目",
    }
