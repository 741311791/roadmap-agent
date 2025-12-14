"""
获取概念教程工具

用于获取指定概念的教程内容。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.db.repository_factory import get_repository_factory

logger = structlog.get_logger()


class GetConceptTutorialInput(BaseModel):
    """获取概念教程工具输入"""
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")


class GetConceptTutorialOutput(BaseModel):
    """获取概念教程工具输出"""
    success: bool = Field(..., description="是否成功")
    tutorial_id: Optional[str] = Field(None, description="教程 ID")
    title: Optional[str] = Field(None, description="教程标题")
    summary: Optional[str] = Field(None, description="教程摘要")
    content_url: Optional[str] = Field(None, description="教程内容 URL")
    estimated_completion_time: Optional[int] = Field(None, description="预估完成时间（分钟）")
    message: str = Field(..., description="结果消息")


class GetConceptTutorialTool(BaseTool[GetConceptTutorialInput, GetConceptTutorialOutput]):
    """
    获取概念教程工具
    
    功能：
    - 从数据库获取概念的教程元数据
    - 返回教程摘要、URL等关键信息
    """
    
    def __init__(self):
        super().__init__(tool_id="get_concept_tutorial_v1")
        self.repo_factory = get_repository_factory()
    
    async def execute(self, input_data: GetConceptTutorialInput) -> GetConceptTutorialOutput:
        """
        获取概念教程
        
        Args:
            input_data: 查询参数
            
        Returns:
            教程信息
        """
        try:
            async with self.repo_factory.create_session() as session:
                tutorial_repo = self.repo_factory.create_tutorial_repo(session)
                
                # 获取最新版本的教程
                tutorial = await tutorial_repo.get_latest_tutorial(
                    roadmap_id=input_data.roadmap_id,
                    concept_id=input_data.concept_id,
                )
                
                if not tutorial:
                    logger.info(
                        "concept_tutorial_not_found",
                        roadmap_id=input_data.roadmap_id,
                        concept_id=input_data.concept_id,
                    )
                    
                    return GetConceptTutorialOutput(
                        success=False,
                        message="该概念的教程尚未生成",
                    )
                
                logger.info(
                    "concept_tutorial_found",
                    tutorial_id=tutorial.tutorial_id,
                    concept_id=input_data.concept_id,
                )
                
                return GetConceptTutorialOutput(
                    success=True,
                    tutorial_id=tutorial.tutorial_id,
                    title=tutorial.title,
                    summary=tutorial.summary,
                    content_url=tutorial.content_url,
                    estimated_completion_time=tutorial.estimated_completion_time,
                    message="成功获取教程信息",
                )
        
        except Exception as e:
            logger.error(
                "get_concept_tutorial_failed",
                error=str(e),
                roadmap_id=input_data.roadmap_id,
                concept_id=input_data.concept_id,
            )
            
            return GetConceptTutorialOutput(
                success=False,
                message=f"获取教程失败: {str(e)}",
            )
