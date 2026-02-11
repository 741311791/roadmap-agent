"""
教程CRUD操作
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import TutorialMetadata, beijing_now
from app.schemas.tutorial import TutorialCreate, TutorialUpdate

logger = structlog.get_logger()


def _ensure_naive_datetime(dt: datetime) -> datetime:
    """
    确保datetime对象无时区信息（防御性函数）
    
    如果输入的datetime带有时区信息，转换为北京时间并移除时区。
    如果已经无时区信息，直接返回。
    
    Args:
        dt: 待处理的datetime对象
        
    Returns:
        无时区信息的datetime对象
    """
    if dt.tzinfo is None:
        # 已经无时区，直接返回
        return dt
    
    # 有时区信息，转换为北京时间（UTC+8）并移除时区
    from datetime import timezone, timedelta
    BEIJING_TZ = timezone(timedelta(hours=8))
    beijing_time = dt.astimezone(BEIJING_TZ)
    return beijing_time.replace(tzinfo=None)

class TutorialCRUD(BaseCRUD[TutorialMetadata, TutorialCreate, TutorialUpdate]):
    """
    教程CRUD操作
    
    继承BaseCRUD，自动获得通用的CRUD方法
    """
    
    async def get_by_tutorial_id(
        self,
        session: AsyncSession,
        tutorial_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        根据tutorial_id获取教程
        
        Args:
            session: 数据库会话
            tutorial_id: 教程ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata).where(
                TutorialMetadata.tutorial_id == tutorial_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_concept(
        self,
        session: AsyncSession,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取概念的教程（最新版本）
        
        Args:
            session: 数据库会话
            concept_id: 概念ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.concept_id == concept_id)
            .order_by(TutorialMetadata.content_version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_latest_by_concept(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """
        获取指定路线图和概念的最新教程
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            教程元数据或None
        """
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == roadmap_id)
            .where(TutorialMetadata.concept_id == concept_id)
            .where(TutorialMetadata.is_latest == True)
        )
        return result.scalar_one_or_none()
    
    async def _mark_concept_tutorials_not_latest(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> int:
        """
        将指定概念的所有教程版本标记为非最新
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            更新的记录数
        """
        result = await session.execute(
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
                "concept_tutorials_marked_not_latest",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                count=updated_count,
            )
        
        return updated_count
    
    async def save_tutorial(
        self,
        session: AsyncSession,
        tutorial_output: "TutorialGenerationOutput",
        roadmap_id: str,
    ) -> TutorialMetadata:
        """
        保存教程元数据（支持版本管理）
        
        Args:
            session: 数据库会话
            tutorial_output: 教程生成输出
            roadmap_id: 路线图ID
            
        Returns:
            保存的教程元数据记录
            
        注意：
        - 新保存的教程默认为最新版本（is_latest=True）
        - 保存前会将该概念的旧版本标记为非最新
        """
        # 将该概念的旧版本标记为非最新
        await self._mark_concept_tutorials_not_latest(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=tutorial_output.concept_id,
        )
        
        # 检查是否已存在相同tutorial_id的记录（处理重试/重新生成场景）
        existing = await self.get(session, tutorial_output.tutorial_id)
        
        if existing:
            # 如果已存在，更新现有记录
            existing.title = tutorial_output.title
            existing.summary = tutorial_output.summary
            existing.content_url = tutorial_output.content_url
            existing.content_status = tutorial_output.content_status
            existing.content_version = tutorial_output.content_version
            existing.is_latest = True
            existing.estimated_completion_time = tutorial_output.estimated_completion_time
            existing.created_at = _ensure_naive_datetime(tutorial_output.created_at)
            
            await session.flush()
            metadata = existing
            
            logger.info(
                "tutorial_metadata_updated",
                tutorial_id=tutorial_output.tutorial_id,
                concept_id=tutorial_output.concept_id,
                roadmap_id=roadmap_id,
            )
        else:
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
                created_at=_ensure_naive_datetime(tutorial_output.created_at),
            )
            
            session.add(metadata)
            await session.flush()
        
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
        session: AsyncSession,
        tutorial_refs: dict[str, "TutorialGenerationOutput"],
        roadmap_id: str,
    ) -> List[TutorialMetadata]:
        """
        批量保存教程元数据
        
        Args:
            session: 数据库会话
            tutorial_refs: 教程引用字典（concept_id -> TutorialGenerationOutput）
            roadmap_id: 路线图ID
            
        Returns:
            保存的教程元数据记录列表
        """
        metadata_list = []
        
        for concept_id, tutorial_output in tutorial_refs.items():
            metadata = await self.save_tutorial(session, tutorial_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "tutorials_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list

# 单例模式
_tutorial_crud_instance: Optional[TutorialCRUD] = None

def get_tutorial_crud() -> TutorialCRUD:
    """获取TutorialCRUD单例"""
    global _tutorial_crud_instance
    if _tutorial_crud_instance is None:
        _tutorial_crud_instance = TutorialCRUD(TutorialMetadata)
    return _tutorial_crud_instance

