"""
路线图管理服务

处理路线图的生命周期管理：
- 软删除（移至回收站）
- 恢复（从回收站恢复）
- 永久删除
- 任务删除
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.models.database import (
    RoadmapMetadata, RoadmapTask, beijing_now,
    IntentAnalysisMetadata, ExecutionLog,
    StructureValidationRecord, RoadmapEditRecord,
    HumanReviewFeedback, EditPlanRecord,
)

logger = structlog.get_logger()


class ManagementService:
    """路线图管理业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
    
    async def delete_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
    ) -> dict:
        """
        删除路线图（自动判断任务删除或软删除）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            user_id: 用户ID
            
        Returns:
            删除结果
            
        Raises:
            ValueError: 权限错误或路线图不存在
        """
        # 检查是否是 task- 前缀的临时 ID
        if roadmap_id.startswith("task-"):
            return await self._delete_task(session, roadmap_id, user_id)
        else:
            return await self._soft_delete_roadmap(session, roadmap_id, user_id)
    
    async def _delete_task(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
    ) -> dict:
        """删除进行中的任务"""
        # 提取真实的 task_id
        actual_task_id = roadmap_id[5:]  # 去掉 "task-" 前缀
        
        logger.info(
            "delete_in_progress_task_requested",
            task_id=actual_task_id,
            user_id=user_id,
        )
        
        # 获取任务信息以验证权限
        task = await self.task_crud.get_by_task_id(session, actual_task_id)
        if not task:
            raise ValueError(f"任务 {actual_task_id} 不存在")
        
        if task.user_id != user_id:
            raise ValueError("无权限删除此任务")
        
        # 物理删除任务记录
        await session.execute(
            delete(RoadmapTask).where(RoadmapTask.task_id == actual_task_id)
        )
        
        # 删除关联的 intent_analysis_metadata
        await session.execute(
            delete(IntentAnalysisMetadata).where(IntentAnalysisMetadata.task_id == actual_task_id)
        )
        
        # 删除关联的 execution_logs
        await session.execute(
            delete(ExecutionLog).where(ExecutionLog.task_id == actual_task_id)
        )
        
        # 删除其他关联记录
        await session.execute(
            delete(StructureValidationRecord).where(StructureValidationRecord.task_id == actual_task_id)
        )
        await session.execute(
            delete(RoadmapEditRecord).where(RoadmapEditRecord.task_id == actual_task_id)
        )
        await session.execute(
            delete(HumanReviewFeedback).where(HumanReviewFeedback.task_id == actual_task_id)
        )
        await session.execute(
            delete(EditPlanRecord).where(EditPlanRecord.task_id == actual_task_id)
        )
        
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
    
    async def _soft_delete_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
    ) -> dict:
        """软删除路线图（移至回收站）"""
        logger.info(
            "soft_delete_roadmap_requested",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        # 获取路线图
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        if metadata.user_id != user_id:
            raise ValueError("无权限删除此路线图")
        
        if metadata.deleted_at:
            raise ValueError("路线图已被删除")
        
        # 软删除
        metadata.deleted_at = beijing_now()
        metadata.deleted_by = user_id
        session.add(metadata)
        await session.flush()
        
        logger.info(
            "roadmap_soft_deleted",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "roadmap_id": roadmap_id,
            "deleted_at": metadata.deleted_at.isoformat() if metadata.deleted_at else None,
        }
    
    async def restore_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
    ) -> dict:
        """
        恢复已删除的路线图
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            user_id: 用户ID
            
        Returns:
            恢复结果
            
        Raises:
            ValueError: 权限错误或路线图不存在
        """
        logger.info(
            "restore_roadmap_requested",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        # 获取已删除的路线图
        result = await session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
            .where(RoadmapMetadata.deleted_at.is_not(None))
        )
        metadata = result.scalars().first()
        
        if not metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在或未被删除")
        
        if metadata.user_id != user_id:
            raise ValueError("无权限恢复此路线图")
        
        # 恢复
        metadata.deleted_at = None
        metadata.deleted_by = None
        session.add(metadata)
        await session.flush()
        
        logger.info(
            "roadmap_restored",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "roadmap_id": roadmap_id,
            "message": "路线图已恢复",
        }
    
    async def permanently_delete_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
    ) -> dict:
        """
        永久删除路线图（物理删除）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            user_id: 用户ID
            
        Returns:
            删除结果
            
        Raises:
            ValueError: 权限错误或路线图不存在
        """
        logger.info(
            "permanently_delete_roadmap_requested",
            roadmap_id=roadmap_id,
            user_id=user_id,
        )
        
        # 先验证权限
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not metadata or metadata.user_id != user_id:
            raise ValueError("路线图不存在或无权限删除")
        
        # 物理删除所有相关记录
        # 1. 删除路线图元数据
        await session.execute(
            delete(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        
        # 2. 删除关联的任务
        await session.execute(
            delete(RoadmapTask).where(RoadmapTask.roadmap_id == roadmap_id)
        )
        
        # 3. 删除其他关联数据
        # 删除 ExecutionLog（通过 task_id）
        from app.models.database import ExecutionLog
        task_result = await session.execute(
            select(RoadmapTask.task_id).where(RoadmapTask.roadmap_id == roadmap_id)
        )
        task_ids = [row[0] for row in task_result.fetchall()]
        if task_ids:
            await session.execute(
                delete(ExecutionLog).where(ExecutionLog.task_id.in_(task_ids))
            )
        
        # 删除 ValidationRecord
        from app.models.database import ValidationRecord
        await session.execute(
            delete(ValidationRecord).where(ValidationRecord.roadmap_id == roadmap_id)
        )
        
        # 删除 EditRecord
        from app.models.database import EditRecord
        await session.execute(
            delete(EditRecord).where(EditRecord.roadmap_id == roadmap_id)
        )
        
        # 删除 IntentAnalysisRecord
        from app.models.database import IntentAnalysisRecord
        await session.execute(
            delete(IntentAnalysisRecord).where(IntentAnalysisRecord.roadmap_id == roadmap_id)
        )
        
        # 删除概念相关数据
        from app.models.database import (
            ConceptMetadata, TutorialMetadata, ResourceRecommendationMetadata, QuizMetadata, ConceptProgress
        )
        
        # 先获取所有概念ID
        concept_result = await session.execute(
            select(ConceptMetadata.concept_id).where(ConceptMetadata.roadmap_id == roadmap_id)
        )
        concept_ids = [row[0] for row in concept_result.fetchall()]
        
        if concept_ids:
            # 删除教程
            await session.execute(
                delete(TutorialMetadata).where(TutorialMetadata.concept_id.in_(concept_ids))
            )
            # 删除资源
            await session.execute(
                delete(ResourceRecommendationMetadata).where(ResourceRecommendationMetadata.concept_id.in_(concept_ids))
            )
            # 删除测验
            await session.execute(
                delete(QuizMetadata).where(QuizMetadata.concept_id.in_(concept_ids))
            )
            # 删除进度
            await session.execute(
                delete(ConceptProgress).where(ConceptProgress.concept_id.in_(concept_ids))
            )
        
        # 最后删除概念元数据
        await session.execute(
            delete(ConceptMetadata).where(ConceptMetadata.roadmap_id == roadmap_id)
        )
        
        logger.info(
            "roadmap_permanently_deleted",
            roadmap_id=roadmap_id,
            user_id=user_id,
            deleted_tables=[
                "RoadmapMetadata", "RoadmapTask", "ExecutionLog", "ValidationRecord",
                "EditRecord", "IntentAnalysisRecord", "ConceptMetadata", "TutorialMetadata",
                "ResourceRecommendationMetadata", "QuizMetadata", "ConceptProgress"
            ],
        )
        
        return {
            "success": True,
            "roadmap_id": roadmap_id,
            "message": "路线图已永久删除",
        }


def get_management_service() -> ManagementService:
    """获取ManagementService实例"""
    return ManagementService()

