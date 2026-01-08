"""
概念CRUD操作

扩展了以下Repository方法：
- 元数据查询（get_by_roadmap_id, get_completed_concepts等）
- 状态更新（update_content_status）
- 批量操作（batch_initialize_concepts）
"""
from typing import Optional, Tuple, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes
import structlog

from app.crud.base import BaseCRUD
from app.models.database import ConceptMetadata, RoadmapMetadata, beijing_now
from app.schemas.concept import ConceptCreate, ConceptUpdate

logger = structlog.get_logger()

class ConceptCRUD(BaseCRUD[ConceptMetadata, ConceptCreate, ConceptUpdate]):
    """
    概念CRUD操作
    
    继承BaseCRUD,自动获得通用的CRUD方法
    
    扩展功能：
    - 从RoadmapMetadata.framework_data中操作概念数据
    - 更新概念状态（tutorial/resources/quiz）
    """
    
    async def get_by_concept_id(
        self,
        session: AsyncSession,
        concept_id: str,
    ) -> Optional[ConceptMetadata]:
        """
        根据concept_id获取概念
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            
        Returns:
            概念元数据或None
        """
        result = await session.execute(
            select(ConceptMetadata).where(
                ConceptMetadata.concept_id == concept_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConceptMetadata]:
        """
        获取路线图下的所有概念
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            概念列表
        """
        result = await session.execute(
            select(ConceptMetadata)
            .where(ConceptMetadata.roadmap_id == roadmap_id)
            .order_by(ConceptMetadata.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ===== 从framework_data操作概念 =====
    
    async def get_concept_from_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[Tuple[dict, dict, RoadmapMetadata]]:
        """
        从路线图的framework_data中获取指定概念
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            (concept_dict, context_dict, roadmap_metadata) 或 None
            
        Example:
            ```python
            concept, context, roadmap = await crud.get_concept_from_roadmap(
                session, "roadmap-123", "concept-456"
            )
            # concept: {"concept_id": "concept-456", "name": "...", ...}
            # context: {"stage_idx": 0, "module_idx": 1, "concept_idx": 2}
            # roadmap: RoadmapMetadata实例
            ```
        """
        # 获取路线图元数据
        result = await session.execute(
            select(RoadmapMetadata).where(
                RoadmapMetadata.roadmap_id == roadmap_id
            )
        )
        roadmap_metadata = result.scalar_one_or_none()
        
        if not roadmap_metadata:
            logger.warning(
                "roadmap_not_found",
                roadmap_id=roadmap_id,
            )
            return None
        
        framework_data = roadmap_metadata.framework_data
        
        # 遍历查找概念
        for stage_idx, stage in enumerate(framework_data.get("stages", [])):
            for module_idx, module in enumerate(stage.get("modules", [])):
                for concept_idx, concept in enumerate(module.get("concepts", [])):
                    if concept.get("concept_id") == concept_id:
                        # 构建上下文
                        context = {
                            "stage": stage,
                            "module": module,
                            "stage_idx": stage_idx,
                            "module_idx": module_idx,
                            "concept_idx": concept_idx,
                            "roadmap_id": roadmap_id,
                            "stage_name": stage.get("name"),
                            "module_name": module.get("name"),
                        }
                        logger.info(
                            "concept_found_in_framework",
                            roadmap_id=roadmap_id,
                            concept_id=concept_id,
                            stage_idx=stage_idx,
                            module_idx=module_idx,
                            concept_idx=concept_idx,
                        )
                        return concept, context, roadmap_metadata
        
        logger.warning(
            "concept_not_found_in_framework",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
        return None
    
    async def update_concept_status(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        content_type: str,
        status: str,
        result: Optional[dict] = None,
    ) -> bool:
        """
        更新概念的内容生成状态
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            content_type: 内容类型 (tutorial/resources/quiz)
            status: 状态 (pending/generating/completed/failed)
            result: 生成结果（completed时提供）
            
        Returns:
            是否成功
            
        Example:
            ```python
            # 开始生成
            await crud.update_concept_status(
                session, "roadmap-123", "concept-456",
                "tutorial", "generating"
            )
            
            # 完成生成
            await crud.update_concept_status(
                session, "roadmap-123", "concept-456",
                "tutorial", "completed",
                result={"content_url": "...", "summary": "..."}
            )
            ```
        """
        # 获取路线图
        roadmap_result = await session.execute(
            select(RoadmapMetadata).where(
                RoadmapMetadata.roadmap_id == roadmap_id
            )
        )
        roadmap_metadata = roadmap_result.scalar_one_or_none()
        
        if not roadmap_metadata:
            logger.error(
                "roadmap_not_found_for_status_update",
                roadmap_id=roadmap_id,
            )
            return False
        
        framework_data = roadmap_metadata.framework_data
        
        # 查找并更新概念
        updated = False
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        # 更新状态字段
                        if content_type == "tutorial":
                            concept["content_status"] = status
                            if status == "completed" and result:
                                concept["content_ref"] = result.get("content_url")
                                concept["content_summary"] = result.get("summary")
                                concept["tutorial_id"] = result.get("tutorial_id")
                        elif content_type == "resources":
                            concept["resources_status"] = status
                            if status == "completed" and result:
                                concept["resources_id"] = result.get("resources_id")
                                concept["resources_count"] = result.get("resources_count", 0)
                        elif content_type == "quiz":
                            concept["quiz_status"] = status
                            if status == "completed" and result:
                                concept["quiz_id"] = result.get("quiz_id")
                                concept["quiz_questions_count"] = result.get("questions_count", 0)
                        
                        updated = True
                        logger.info(
                            "concept_status_updated",
                            roadmap_id=roadmap_id,
                            concept_id=concept_id,
                            content_type=content_type,
                            status=status,
                        )
                        break
        
        if not updated:
            logger.error(
                "concept_not_found_for_status_update",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return False
        
        # 标记framework_data已修改（对JSONB字段必须这样做）
        attributes.flag_modified(roadmap_metadata, "framework_data")
        roadmap_metadata.framework_data = framework_data
        
        session.add(roadmap_metadata)
        await session.flush()
        
        return True
    
    # ========== Week 4扩展方法 ==========
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[ConceptMetadata]:
        """
        查询某roadmap的所有Concept元数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            ConceptMetadata对象列表
        """
        result = await session.execute(
            select(ConceptMetadata)
            .where(ConceptMetadata.roadmap_id == roadmap_id)
            .order_by(ConceptMetadata.created_at)
        )
        return list(result.scalars().all())
    
    async def get_completed_concepts(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[ConceptMetadata]:
        """
        查询某roadmap中所有完成的Concept
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            状态为completed的ConceptMetadata对象列表
        """
        result = await session.execute(
            select(ConceptMetadata)
            .where(
                ConceptMetadata.roadmap_id == roadmap_id,
                ConceptMetadata.overall_status == "completed"
            )
        )
        return list(result.scalars().all())
    
    async def get_failed_concepts(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[ConceptMetadata]:
        """
        查询某roadmap中所有失败或部分失败的Concept
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            状态为failed或partial_failed的ConceptMetadata对象列表
        """
        result = await session.execute(
            select(ConceptMetadata)
            .where(
                ConceptMetadata.roadmap_id == roadmap_id,
                ConceptMetadata.overall_status.in_(["failed", "partial_failed"])
            )
        )
        return list(result.scalars().all())
    
    async def create_or_update_metadata(
        self,
        session: AsyncSession,
        concept_id: str,
        roadmap_id: str,
        **fields
    ) -> ConceptMetadata:
        """
        创建或更新Concept元数据（Upsert）
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            roadmap_id: 路线图ID
            **fields: 其他字段
            
        Returns:
            ConceptMetadata对象
        """
        existing = await self.get_by_concept_id(session, concept_id)
        
        if existing:
            # 更新现有记录
            for key, value in fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = beijing_now()
            session.add(existing)
            logger.debug(
                "concept_metadata_updated",
                concept_id=concept_id,
                fields=list(fields.keys())
            )
            return existing
        else:
            # 创建新记录
            from app.models.database import beijing_now
            metadata = ConceptMetadata(
                concept_id=concept_id,
                roadmap_id=roadmap_id,
                **fields
            )
            session.add(metadata)
            logger.debug(
                "concept_metadata_created",
                concept_id=concept_id,
                roadmap_id=roadmap_id
            )
            return metadata
    
    async def update_content_status(
        self,
        session: AsyncSession,
        concept_id: str,
        content_type: str,
        status: str,
        content_id: Optional[str] = None,
    ) -> ConceptMetadata:
        """
        更新单项内容状态，并自动检查是否全部完成
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            content_type: 内容类型 ('tutorial', 'resources', 'quiz')
            status: 新状态
            content_id: 内容ID（可选）
            
        Returns:
            更新后的ConceptMetadata对象
            
        Raises:
            ValueError: 如果concept_id不存在
        """
        from app.models.database import beijing_now
        
        metadata = await self.get_by_concept_id(session, concept_id)
        
        if not metadata:
            raise ValueError(f"ConceptMetadata not found for concept_id: {concept_id}")
        
        # 更新对应的状态字段
        status_field = f"{content_type}_status"
        id_field = f"{content_type}_id"
        completed_at_field = f"{content_type}_completed_at"
        
        setattr(metadata, status_field, status)
        
        if content_id:
            setattr(metadata, id_field, content_id)
        
        if status == "completed":
            setattr(metadata, completed_at_field, beijing_now())
        
        # 检查三项是否全部完成
        if (metadata.tutorial_status == "completed" and
            metadata.resources_status == "completed" and
            metadata.quiz_status == "completed"):
            metadata.overall_status = "completed"
            metadata.all_content_completed_at = beijing_now()
            logger.info(
                "concept_all_content_completed",
                concept_id=concept_id,
                roadmap_id=metadata.roadmap_id
            )
        elif (metadata.tutorial_status in ["completed", "failed"] and
              metadata.resources_status in ["completed", "failed"] and
              metadata.quiz_status in ["completed", "failed"] and
              (metadata.tutorial_status == "failed" or
               metadata.resources_status == "failed" or
               metadata.quiz_status == "failed")):
            metadata.overall_status = "partial_failed"
        elif status == "generating":
            if metadata.overall_status == "pending":
                metadata.overall_status = "generating"
        
        metadata.updated_at = beijing_now()
        session.add(metadata)
        
        logger.debug(
            "concept_content_status_updated",
            concept_id=concept_id,
            content_type=content_type,
            status=status,
            overall_status=metadata.overall_status
        )
        
        return metadata
    
    async def batch_initialize_concepts(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_ids: List[str],
    ):
        """
        批量初始化Concept元数据（在framework生成后调用）
        
        使用批量插入优化性能，避免N次INSERT
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_ids: 概念ID列表
        """
        from app.models.database import beijing_now
        
        if not concept_ids:
            logger.warning("batch_initialize_concepts_empty_list", roadmap_id=roadmap_id)
            return
        
        # 检查是否已存在
        result = await session.execute(
            select(ConceptMetadata.concept_id).where(
                ConceptMetadata.roadmap_id == roadmap_id,
                ConceptMetadata.concept_id.in_(concept_ids)
            )
        )
        existing_ids = set(result.scalars().all())
        
        # 过滤出需要新建的concept_id
        new_concept_ids = [cid for cid in concept_ids if cid not in existing_ids]
        
        if not new_concept_ids:
            logger.info(
                "batch_initialize_concepts_all_exist",
                roadmap_id=roadmap_id,
                total_count=len(concept_ids)
            )
            return
        
        # 批量插入
        now = beijing_now()
        metadata_list = [
            ConceptMetadata(
                concept_id=cid,
                roadmap_id=roadmap_id,
                tutorial_status="pending",
                resources_status="pending",
                quiz_status="pending",
                overall_status="pending",
                created_at=now,
                updated_at=now
            )
            for cid in new_concept_ids
        ]
        
        session.add_all(metadata_list)
        
        logger.info(
            "batch_initialize_concepts_completed",
            roadmap_id=roadmap_id,
            new_count=len(new_concept_ids),
            skipped_count=len(existing_ids)
        )


# 工厂函数
def get_concept_crud() -> ConceptCRUD:
    """获取ConceptCRUD实例"""
    return ConceptCRUD(ConceptMetadata)
