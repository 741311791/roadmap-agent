"""
标记内容完成工具

用于标记用户已完成学习某个概念。
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.db.repository_factory import get_repository_factory

logger = structlog.get_logger()


class MarkContentCompleteInput(BaseModel):
    """标记内容完成工具输入"""
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")
    is_completed: bool = Field(default=True, description="是否完成（True=完成，False=取消完成）")


class MarkContentCompleteOutput(BaseModel):
    """标记内容完成工具输出"""
    success: bool = Field(..., description="是否成功")
    concept_id: Optional[str] = Field(None, description="概念 ID")
    is_completed: bool = Field(default=False, description="当前完成状态")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    message: str = Field(..., description="结果消息")


class MarkContentCompleteTool(BaseTool[MarkContentCompleteInput, MarkContentCompleteOutput]):
    """
    标记内容完成工具
    
    功能：
    - 标记用户已完成学习某个概念
    - 支持取消完成状态
    - 更新学习进度记录
    """
    
    def __init__(self):
        super().__init__(tool_id="mark_content_complete_v1")
        self.repo_factory = get_repository_factory()
    
    async def execute(self, input_data: MarkContentCompleteInput) -> MarkContentCompleteOutput:
        """
        标记概念完成状态
        
        Args:
            input_data: 标记参数
            
        Returns:
            标记结果
        """
        try:
            # 使用 progress_repo 来更新学习进度
            # progress_repo 应该已经在 progress.py endpoint 中实现了
            async with self.repo_factory.create_session() as session:
                from app.db.repositories.progress_repo import ProgressRepository
                from app.models.database import ConceptProgress, beijing_now
                from sqlalchemy import select
                
                progress_repo = ProgressRepository(session)
                
                # 查找或创建进度记录
                result = await session.execute(
                    select(ConceptProgress).where(
                        ConceptProgress.user_id == input_data.user_id,
                        ConceptProgress.roadmap_id == input_data.roadmap_id,
                        ConceptProgress.concept_id == input_data.concept_id,
                    )
                )
                progress = result.scalar_one_or_none()
                
                now = beijing_now()
                
                if progress:
                    # 更新现有记录
                    progress.is_completed = input_data.is_completed
                    progress.completed_at = now if input_data.is_completed else None
                    progress.updated_at = now
                else:
                    # 创建新记录
                    progress = ConceptProgress(
                        user_id=input_data.user_id,
                        roadmap_id=input_data.roadmap_id,
                        concept_id=input_data.concept_id,
                        is_completed=input_data.is_completed,
                        completed_at=now if input_data.is_completed else None,
                    )
                    session.add(progress)
                
                await session.commit()
                
                status_text = "完成" if input_data.is_completed else "未完成"
                logger.info(
                    "content_complete_marked",
                    user_id=input_data.user_id,
                    concept_id=input_data.concept_id,
                    is_completed=input_data.is_completed,
                )
                
                return MarkContentCompleteOutput(
                    success=True,
                    concept_id=input_data.concept_id,
                    is_completed=input_data.is_completed,
                    completed_at=progress.completed_at,
                    message=f"已将概念标记为{status_text}",
                )
        
        except Exception as e:
            logger.error(
                "mark_content_complete_failed",
                error=str(e),
                user_id=input_data.user_id,
                concept_id=input_data.concept_id,
            )
            
            return MarkContentCompleteOutput(
                success=False,
                message=f"标记失败: {str(e)}",
            )
