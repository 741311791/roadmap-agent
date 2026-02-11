"""
标记内容完成工具

用于标记用户已完成学习某个概念。
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.crud.crud_progress import ProgressCRUD, get_progress_crud
from app.db.session import async_session_maker
from app.models.database import ConceptProgress, beijing_now

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
    标记内容完成工具（已适配统一工具框架）
    
    功能：
    - 标记用户已完成学习某个概念
    - 支持取消完成状态
    - 更新学习进度记录
    - 自动生成 LLM Function Schema
    """
    
    def __init__(self):
        super().__init__(
            tool_id="mark_content_complete_v2",
            name="mark_content_complete",
            description="Mark a concept as completed or incomplete. Use this when the user explicitly says they finished learning a topic.",
            args_schema=MarkContentCompleteInput,
        )
        self.progress_crud = get_progress_crud()
    
    async def execute(self, input_data: MarkContentCompleteInput) -> MarkContentCompleteOutput:
        """
        标记概念完成状态
        
        Args:
            input_data: 标记参数
            
        Returns:
            标记结果
        """
        try:
            # 使用ProgressCRUD更新学习进度
            async with async_session_maker.begin() as session:
                from sqlalchemy import select
                
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
                # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
                
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
