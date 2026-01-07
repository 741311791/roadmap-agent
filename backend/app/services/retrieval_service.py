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
        获取完整的路线图数据（包含概念状态）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图数据或None
        """
        # 获取路线图元数据
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not metadata:
            return None
        
        # 获取所有概念元数据（合并状态）
        concept_metas = await self.concept_crud.get_by_roadmap(session, roadmap_id)
        
        # 构建 concept_id -> ConceptMetadata 映射
        concept_meta_map = {cm.concept_id: cm for cm in concept_metas}
        
        # 从 framework_data 构建响应，合并概念状态
        framework_data = metadata.framework_data.copy()
        
        # 合并 concept_metadata 的 overall_status 到 framework_data
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    if concept_id and concept_id in concept_meta_map:
                        concept_meta = concept_meta_map[concept_id]
                        # 使用真实的概念状态
                        concept["content_status"] = concept_meta.tutorial_status
                        concept["resources_status"] = concept_meta.resources_status
                        concept["quiz_status"] = concept_meta.quiz_status
                        concept["overall_status"] = concept_meta.overall_status
                        
                        # 更新 ID 引用
                        if concept_meta.tutorial_id:
                            concept["tutorial_id"] = concept_meta.tutorial_id
                        if concept_meta.resources_id:
                            concept["resources_id"] = concept_meta.resources_id
                        if concept_meta.quiz_id:
                            concept["quiz_id"] = concept_meta.quiz_id
        
        return framework_data
    
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

