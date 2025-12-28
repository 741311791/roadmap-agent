"""
路线图管理 API 端点

提供路线图的删除、恢复、永久删除等管理功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.database import (
    RoadmapTask, 
    IntentAnalysisMetadata, 
    ExecutionLog,
    StructureValidationRecord,
    RoadmapEditRecord,
    HumanReviewFeedback,
    EditPlanRecord,
)

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()


@router.delete("/{roadmap_id}")
async def delete_roadmap(
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
       - 同时删除关联的 intent_analysis_metadata 和 execution_logs
    
    2. 如果是普通格式（如 "python-guide-xxx"）：
       - 软删除 roadmap_metadata 表中的记录（设置 deleted_at 字段）
       - 关联的 roadmap_tasks 记录保留用于追踪
       - 可通过回收站恢复
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        session: 数据库会话
        
    Returns:
        {
            "success": bool,
            "roadmap_id": str,
            "task_id": str | None,
            "deleted_at": str | None
        }
        
    Raises:
        HTTPException: 404 - 路线图不存在
        HTTPException: 403 - 无权限删除
        HTTPException: 500 - 服务器错误
        
    Example (软删除):
        ```json
        {
            "success": true,
            "roadmap_id": "python-guide-xxx",
            "deleted_at": "2024-01-01T00:00:00Z"
        }
        ```
        
    Example (任务删除):
        ```json
        {
            "success": true,
            "roadmap_id": "task-550e8400-e29b-41d4-a716-446655440000",
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "deleted_at": null
        }
        ```
    """
    try:
        repo = RoadmapRepository(session)
        
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
            
            # 删除关联的元数据（按依赖顺序删除，避免外键约束冲突）
            # 注意：edit_plan_records 引用 human_review_feedbacks.id，所以必须先删除 edit_plan_records
            
            # 1. 删除 edit_plan_records（引用 human_review_feedbacks.id）
            stmt_edit_plan = delete(EditPlanRecord).where(
                EditPlanRecord.task_id == actual_task_id
            )
            edit_plan_result = await session.execute(stmt_edit_plan)
            
            # 2. 删除 human_review_feedbacks（被 edit_plan_records 引用）
            stmt_review_feedback = delete(HumanReviewFeedback).where(
                HumanReviewFeedback.task_id == actual_task_id
            )
            review_feedback_result = await session.execute(stmt_review_feedback)
            
            # 3. 删除 intent_analysis_metadata
            stmt_intent = delete(IntentAnalysisMetadata).where(
                IntentAnalysisMetadata.task_id == actual_task_id
            )
            intent_result = await session.execute(stmt_intent)
            
            # 4. 删除 structure_validation_records
            stmt_validation = delete(StructureValidationRecord).where(
                StructureValidationRecord.task_id == actual_task_id
            )
            validation_result = await session.execute(stmt_validation)
            
            # 5. 删除 roadmap_edit_records
            stmt_edit_records = delete(RoadmapEditRecord).where(
                RoadmapEditRecord.task_id == actual_task_id
            )
            edit_records_result = await session.execute(stmt_edit_records)
            
            # 6. 删除 execution_logs（无外键约束）
            stmt_logs = delete(ExecutionLog).where(
                ExecutionLog.task_id == actual_task_id
            )
            logs_result = await session.execute(stmt_logs)
            
            logger.debug(
                "task_related_records_deleted",
                task_id=actual_task_id,
                deleted_edit_plans=edit_plan_result.rowcount,
                deleted_review_feedbacks=review_feedback_result.rowcount,
                deleted_intent_analysis=intent_result.rowcount,
                deleted_validation_records=validation_result.rowcount,
                deleted_edit_records=edit_records_result.rowcount,
                deleted_execution_logs=logs_result.rowcount,
            )
            
            # 7. 最后删除任务记录
            stmt_task = delete(RoadmapTask).where(RoadmapTask.task_id == actual_task_id)
            await session.execute(stmt_task)
            
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
            
            # 删除所有关联记录（按依赖顺序，避免外键约束错误）
            # 注意：edit_plan_records 引用 human_review_feedbacks.id，必须先删除
            
            # 1. 删除 edit_plan_records（引用 human_review_feedbacks.id）
            edit_plan_stmt = delete(EditPlanRecord).where(
                EditPlanRecord.task_id == task.task_id
            )
            edit_plan_result = await session.execute(edit_plan_stmt)
            
            # 2. 删除 human_review_feedbacks（被 edit_plan_records 引用）
            review_feedback_stmt = delete(HumanReviewFeedback).where(
                HumanReviewFeedback.task_id == task.task_id
            )
            review_feedback_result = await session.execute(review_feedback_stmt)
            
            # 3. 删除 intent_analysis_metadata
            intent_stmt = delete(IntentAnalysisMetadata).where(
                IntentAnalysisMetadata.task_id == task.task_id
            )
            intent_result = await session.execute(intent_stmt)
            
            # 4. 删除 structure_validation_records
            validation_stmt = delete(StructureValidationRecord).where(
                StructureValidationRecord.task_id == task.task_id
            )
            validation_result = await session.execute(validation_stmt)
            
            # 5. 删除 roadmap_edit_records
            edit_records_stmt = delete(RoadmapEditRecord).where(
                RoadmapEditRecord.task_id == task.task_id
            )
            edit_records_result = await session.execute(edit_records_stmt)
            
            # 6. 删除 execution_logs
            logs_stmt = delete(ExecutionLog).where(
                ExecutionLog.task_id == task.task_id
            )
            logs_result = await session.execute(logs_stmt)
            
            logger.debug(
                "task_related_records_deleted",
                task_id=task.task_id,
                deleted_edit_plans=edit_plan_result.rowcount,
                deleted_review_feedbacks=review_feedback_result.rowcount,
                deleted_intent_analysis=intent_result.rowcount,
                deleted_validation_records=validation_result.rowcount,
                deleted_edit_records=edit_records_result.rowcount,
                deleted_execution_logs=logs_result.rowcount,
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
                deleted_validation_records=deleted_validation_count,
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
            "delete_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
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
    
    恢复已软删除的路线图（将 deleted_at 设置为 NULL）。
    只能恢复软删除的路线图，物理删除的任务无法恢复。
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        session: 数据库会话
        
    Returns:
        {
            "success": bool,
            "roadmap_id": str
        }
        
    Raises:
        HTTPException: 404 - 路线图不存在或未被删除
        HTTPException: 403 - 无权限恢复
        HTTPException: 500 - 服务器错误
        
    Example:
        ```json
        {
            "success": true,
            "roadmap_id": "python-guide-xxx"
        }
        ```
    """
    try:
        repo = RoadmapRepository(session)
        result = await repo.restore_roadmap(roadmap_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Roadmap not found or not deleted"
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
            error_type=type(e).__name__,
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
    
    ⚠️ 警告：此操作会从数据库中永久删除路线图及所有关联数据，无法恢复！
    
    删除内容包括：
    - roadmap_metadata 表中的路线图记录
    - 所有关联的 tutorials、resources、quizzes 记录
    - 所有关联的 tutorial_versions 记录
    - 可能的其他关联数据（取决于数据库外键级联设置）
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID（用于权限验证）
        session: 数据库会话
        
    Returns:
        {
            "success": bool,
            "roadmap_id": str
        }
        
    Raises:
        HTTPException: 404 - 路线图不存在
        HTTPException: 403 - 无权限删除
        HTTPException: 500 - 服务器错误
        
    Example:
        ```json
        {
            "success": true,
            "roadmap_id": "python-guide-xxx"
        }
        ```
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
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(e))
