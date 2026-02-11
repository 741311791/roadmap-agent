"""
路线图检索服务
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.crud.crud_concept import ConceptCRUD
from app.models.database import RoadmapMetadata, RoadmapTask, ConceptMetadata


class RetrievalService:
    """路线图检索业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
        self.concept_crud = ConceptCRUD(ConceptMetadata)
    
    async def get_roadmap_with_status(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[dict]:
        """
        获取完整的路线图数据（包含概念状态和任务状态）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图详情数据（符合RoadmapDetailResponse格式）或None
        """
        # 1. 获取路线图元数据
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not metadata:
            return None
        
        # 2. 获取关联的任务（用于获取状态）
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        latest_task = result.scalar_one_or_none()
        
        # 3. 确定路线图状态和学习目标
        if latest_task:
            task_status = latest_task.status
            user_request = latest_task.user_request or {}
            learning_goal = user_request.get("preferences", {}).get("learning_goal", "")
        else:
            task_status = "draft"
            learning_goal = ""
        
        # 4. 获取所有概念元数据（合并状态）
        concept_metas = await self.concept_crud.get_by_roadmap(session, roadmap_id)
        concept_meta_map = {cm.concept_id: cm for cm in concept_metas}
        
        # 5. 从 framework_data 构建响应，合并概念状态
        framework_data = metadata.framework_data.copy() if metadata.framework_data else {}
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    if concept_id and concept_id in concept_meta_map:
                        concept_meta = concept_meta_map[concept_id]
                        concept["content_status"] = concept_meta.tutorial_status
                        concept["resources_status"] = concept_meta.resources_status
                        concept["quiz_status"] = concept_meta.quiz_status
                        concept["overall_status"] = concept_meta.overall_status
                        
                        if concept_meta.tutorial_id:
                            concept["tutorial_id"] = concept_meta.tutorial_id
                        if concept_meta.resources_id:
                            concept["resources_id"] = concept_meta.resources_id
                        if concept_meta.quiz_id:
                            concept["quiz_id"] = concept_meta.quiz_id
        
        # 6. 返回符合 RoadmapDetailResponse 格式的数据
        return {
            "roadmap_id": roadmap_id,
            "user_id": metadata.user_id,
            "learning_goal": learning_goal,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else "",
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else "",
            "framework": framework_data,
            "status": task_status,  # ✅ 从 Task 获取状态，而非 metadata
            "title": metadata.title,
            "description": getattr(metadata, 'description', None),
        }
    
    async def get_active_task_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapTask]:
        """
        获取路线图的活跃任务
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            活跃任务或None
        """
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .where(RoadmapTask.status.in_(["processing", "human_review_pending"]))
            .order_by(RoadmapTask.created_at.desc())
        )
        return result.scalars().first()


def get_retrieval_service() -> RetrievalService:
    """获取RetrievalService实例"""
    return RetrievalService()

