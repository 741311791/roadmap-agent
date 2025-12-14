"""
笔记记录工具

用于保存用户的学习笔记到数据库。
"""
from typing import Optional, List
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.db.repository_factory import get_repository_factory

logger = structlog.get_logger()


class NoteRecorderInput(BaseModel):
    """笔记记录工具输入"""
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")
    content: str = Field(..., description="笔记内容（Markdown格式）")
    title: Optional[str] = Field(None, description="笔记标题")
    tags: List[str] = Field(default=[], description="标签列表")
    source: str = Field(default="ai_generated", description="笔记来源")


class NoteRecorderOutput(BaseModel):
    """笔记记录工具输出"""
    success: bool = Field(..., description="是否成功")
    note_id: Optional[str] = Field(None, description="笔记 ID")
    message: str = Field(..., description="结果消息")


class NoteRecorderTool(BaseTool[NoteRecorderInput, NoteRecorderOutput]):
    """
    笔记记录工具
    
    功能：
    - 保存学习笔记到数据库
    - 支持AI生成和手动创建的笔记
    - 支持标签分类
    """
    
    def __init__(self):
        super().__init__(tool_id="note_recorder_v1")
        self.repo_factory = get_repository_factory()
    
    async def execute(self, input_data: NoteRecorderInput) -> NoteRecorderOutput:
        """
        保存学习笔记
        
        Args:
            input_data: 笔记内容
            
        Returns:
            保存结果
        """
        try:
            async with self.repo_factory.create_session() as session:
                note_repo = self.repo_factory.create_note_repo(session)
                
                note = await note_repo.create_note(
                    user_id=input_data.user_id,
                    roadmap_id=input_data.roadmap_id,
                    concept_id=input_data.concept_id,
                    content=input_data.content,
                    title=input_data.title,
                    source=input_data.source,
                    tags=input_data.tags,
                )
                
                await session.commit()
                
                logger.info(
                    "note_recorder_success",
                    note_id=note.note_id,
                    user_id=input_data.user_id,
                    concept_id=input_data.concept_id,
                )
                
                return NoteRecorderOutput(
                    success=True,
                    note_id=note.note_id,
                    message="笔记已成功保存",
                )
        
        except Exception as e:
            logger.error(
                "note_recorder_failed",
                error=str(e),
                user_id=input_data.user_id,
                concept_id=input_data.concept_id,
            )
            
            return NoteRecorderOutput(
                success=False,
                note_id=None,
                message=f"笔记保存失败: {str(e)}",
            )
