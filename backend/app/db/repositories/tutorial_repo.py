"""
教程 Repository

负责 TutorialMetadata 表的数据访问操作。

职责范围：
- 教程元数据的 CRUD 操作
- 教程版本管理（latest标记、历史版本查询）
- 教程查询（根据路线图、概念等）

不包含：
- 教程内容的生成（在 Agent 层）
- 教程文件的上传下载（在 Tool 层）
- 业务统计逻辑（在 Service 层）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.models.database import TutorialMetadata
from app.models.domain import TutorialGenerationOutput
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class TutorialRepository(BaseRepository[TutorialMetadata]):
    """
    教程数据访问层
    
    管理教程元数据和版本。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TutorialMetadata)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_tutorial_id(self, tutorial_id: str) -> Optional[TutorialMetadata]:
        """
        根据 tutorial_id 查询教程元数据
        
        Args:
            tutorial_id: 教程 ID
            
        Returns:
            教程元数据，如果不存在则返回 None
        """
        return await self.get_by_id(tutorial_id)
    
    async def get_latest_tutorial(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定概念的最新教程版本
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            最新版本的教程元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.is_latest == True,
            )
        )
        
        tutorial = result.scalar_one_or_none()
        
        if tutorial:
            logger.debug(
                "latest_tutorial_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                tutorial_id=tutorial.tutorial_id,
                version=tutorial.content_version,
            )
        
        return tutorial
    
    async def get_tutorial_by_version(
        self,
        roadmap_id: str,
        concept_id: str,
        version: int,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定概念的特定版本教程
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            version: 版本号
            
        Returns:
            教程元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.content_version == version,
            )
        )
        
        return result.scalar_one_or_none()
    
    async def get_tutorial_history(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> List[TutorialMetadata]:
        """
        获取指定概念的所有教程版本历史
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            教程元数据列表（按版本号降序排列，最新版本在前）
        """
        result = await self.session.execute(
            select(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
            )
            .order_by(TutorialMetadata.content_version.desc())
        )
        
        tutorials = list(result.scalars().all())
        
        logger.debug(
            "tutorial_history_retrieved",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            version_count=len(tutorials),
        )
        
        return tutorials
    
    async def list_by_roadmap(
        self,
        roadmap_id: str,
        latest_only: bool = True,
    ) -> List[TutorialMetadata]:
        """
        获取路线图的所有教程
        
        Args:
            roadmap_id: 路线图 ID
            latest_only: 是否只返回最新版本（默认 True）
            
        Returns:
            教程元数据列表
        """
        query = select(TutorialMetadata).where(
            TutorialMetadata.roadmap_id == roadmap_id
        )
        
        if latest_only:
            query = query.where(TutorialMetadata.is_latest == True)
        
        result = await self.session.execute(query)
        tutorials = list(result.scalars().all())
        
        logger.debug(
            "tutorials_listed_by_roadmap",
            roadmap_id=roadmap_id,
            count=len(tutorials),
            latest_only=latest_only,
        )
        
        return tutorials
    
    async def get_next_version(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        获取指定概念的下一个教程版本号
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            下一个版本号（如果没有现有版本，返回 1）
        """
        result = await self.session.execute(
            select(func.max(TutorialMetadata.content_version))
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
            )
        )
        
        max_version = result.scalar_one_or_none()
        next_version = (max_version or 0) + 1
        
        logger.debug(
            "next_tutorial_version_calculated",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            next_version=next_version,
        )
        
        return next_version
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_tutorial(
        self,
        tutorial_output: TutorialGenerationOutput,
        roadmap_id: str,
    ) -> TutorialMetadata:
        """
        保存教程元数据（支持版本管理）
        
        Args:
            tutorial_output: 教程生成输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的教程元数据记录
            
        注意：
        - 新保存的教程默认为最新版本（is_latest=True）
        - 保存前会将该概念的旧版本标记为非最新
        """
        # 将该概念的旧版本标记为非最新
        await self._mark_concept_tutorials_not_latest(
            roadmap_id=roadmap_id,
            concept_id=tutorial_output.concept_id,
        )
        
        # 创建新教程元数据
        metadata = TutorialMetadata(
            tutorial_id=tutorial_output.tutorial_id,
            concept_id=tutorial_output.concept_id,
            roadmap_id=roadmap_id,
            title=tutorial_output.title,
            summary=tutorial_output.summary,
            content_url=tutorial_output.content_url,
            content_status=tutorial_output.content_status,
            content_version=tutorial_output.content_version,
            is_latest=True,  # 新版本默认为最新
            estimated_completion_time=tutorial_output.estimated_completion_time,
            generated_at=tutorial_output.generated_at,
        )
        
        await self.create(metadata, flush=True)
        
        logger.info(
            "tutorial_metadata_saved",
            tutorial_id=tutorial_output.tutorial_id,
            concept_id=tutorial_output.concept_id,
            roadmap_id=roadmap_id,
            content_version=tutorial_output.content_version,
            is_latest=True,
        )
        
        return metadata
    
    async def save_tutorials_batch(
        self,
        tutorial_refs: dict[str, TutorialGenerationOutput],
        roadmap_id: str,
    ) -> List[TutorialMetadata]:
        """
        批量保存教程元数据
        
        Args:
            tutorial_refs: 教程引用字典（concept_id -> TutorialGenerationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的教程元数据记录列表
        """
        metadata_list = []
        
        for concept_id, tutorial_output in tutorial_refs.items():
            metadata = await self.save_tutorial(tutorial_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "tutorials_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list
    
    async def update_content_status(
        self,
        tutorial_id: str,
        status: str,
    ) -> bool:
        """
        更新教程内容状态
        
        Args:
            tutorial_id: 教程 ID
            status: 新状态（pending, completed, failed）
            
        Returns:
            True 如果更新成功，False 如果教程不存在
        """
        return await self.update_by_id(
            tutorial_id,
            content_status=status,
        )
    
    async def _mark_concept_tutorials_not_latest(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        将指定概念的所有教程版本标记为非最新
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            更新的记录数
        """
        result = await self.session.execute(
            update(TutorialMetadata)
            .where(
                TutorialMetadata.roadmap_id == roadmap_id,
                TutorialMetadata.concept_id == concept_id,
                TutorialMetadata.is_latest == True,
            )
            .values(is_latest=False)
        )
        
        updated_count = result.rowcount
        
        if updated_count > 0:
            logger.debug(
                "tutorial_versions_marked_not_latest",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                updated_count=updated_count,
            )
        
        return updated_count
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_tutorial(self, tutorial_id: str) -> bool:
        """
        删除教程元数据
        
        Args:
            tutorial_id: 教程 ID
            
        Returns:
            True 如果删除成功，False 如果教程不存在
        """
        deleted = await self.delete_by_id(tutorial_id)
        
        if deleted:
            logger.info("tutorial_metadata_deleted", tutorial_id=tutorial_id)
        
        return deleted
    
    async def delete_tutorials_by_roadmap(self, roadmap_id: str) -> int:
        """
        删除路线图的所有教程
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            删除的记录数
        """
        result = await self.session.execute(
            delete(TutorialMetadata).where(TutorialMetadata.roadmap_id == roadmap_id)
        )
        
        deleted_count = result.rowcount
        
        logger.info(
            "tutorials_deleted_by_roadmap",
            roadmap_id=roadmap_id,
            deleted_count=deleted_count,
        )
        
        return deleted_count
