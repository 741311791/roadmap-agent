"""
获取路线图元数据工具

用于获取路线图的基本信息和结构。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.db.repository_factory import get_repository_factory

logger = structlog.get_logger()


class GetRoadmapMetadataInput(BaseModel):
    """获取路线图元数据工具输入"""
    roadmap_id: str = Field(..., description="路线图 ID")


class ConceptInfo(BaseModel):
    """概念简要信息"""
    concept_id: str
    name: str
    description: str
    difficulty: str


class GetRoadmapMetadataOutput(BaseModel):
    """获取路线图元数据工具输出"""
    success: bool = Field(..., description="是否成功")
    roadmap_id: Optional[str] = Field(None, description="路线图 ID")
    title: Optional[str] = Field(None, description="路线图标题")
    total_estimated_hours: Optional[float] = Field(None, description="预估总时长")
    recommended_completion_weeks: Optional[int] = Field(None, description="推荐完成周数")
    stages_count: int = Field(default=0, description="阶段数量")
    concepts_count: int = Field(default=0, description="概念数量")
    # 当前概念的上下文信息
    current_concept: Optional[ConceptInfo] = Field(None, description="当前概念信息")
    message: str = Field(..., description="结果消息")


class GetRoadmapMetadataTool(BaseTool[GetRoadmapMetadataInput, GetRoadmapMetadataOutput]):
    """
    获取路线图元数据工具
    
    功能：
    - 从数据库获取路线图的基本信息
    - 返回标题、阶段数量、概念数量等
    - 可选择性地获取特定概念的详细信息
    """
    
    def __init__(self):
        super().__init__(tool_id="get_roadmap_metadata_v1")
        self.repo_factory = get_repository_factory()
    
    async def execute(self, input_data: GetRoadmapMetadataInput) -> GetRoadmapMetadataOutput:
        """
        获取路线图元数据
        
        Args:
            input_data: 查询参数
            
        Returns:
            路线图元数据
        """
        try:
            async with self.repo_factory.create_session() as session:
                roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
                
                roadmap = await roadmap_repo.get_by_roadmap_id(input_data.roadmap_id)
                
                if not roadmap:
                    logger.info(
                        "roadmap_metadata_not_found",
                        roadmap_id=input_data.roadmap_id,
                    )
                    
                    return GetRoadmapMetadataOutput(
                        success=False,
                        message="路线图不存在",
                    )
                
                # 统计阶段和概念数量
                framework = roadmap.framework_data
                stages = framework.get("stages", [])
                stages_count = len(stages)
                concepts_count = sum(
                    len(module.get("concepts", []))
                    for stage in stages
                    for module in stage.get("modules", [])
                )
                
                logger.info(
                    "roadmap_metadata_found",
                    roadmap_id=input_data.roadmap_id,
                    title=roadmap.title,
                    stages_count=stages_count,
                    concepts_count=concepts_count,
                )
                
                return GetRoadmapMetadataOutput(
                    success=True,
                    roadmap_id=roadmap.roadmap_id,
                    title=roadmap.title,
                    total_estimated_hours=roadmap.total_estimated_hours,
                    recommended_completion_weeks=roadmap.recommended_completion_weeks,
                    stages_count=stages_count,
                    concepts_count=concepts_count,
                    message="成功获取路线图元数据",
                )
        
        except Exception as e:
            logger.error(
                "get_roadmap_metadata_failed",
                error=str(e),
                roadmap_id=input_data.roadmap_id,
            )
            
            return GetRoadmapMetadataOutput(
                success=False,
                message=f"获取路线图元数据失败: {str(e)}",
            )
    
    async def get_concept_info(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[ConceptInfo]:
        """
        获取指定概念的详细信息
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            概念信息，不存在则返回 None
        """
        try:
            async with self.repo_factory.create_session() as session:
                roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
                
                roadmap = await roadmap_repo.get_by_roadmap_id(roadmap_id)
                
                if not roadmap:
                    return None
                
                # 在框架中查找概念
                framework = roadmap.framework_data
                for stage in framework.get("stages", []):
                    for module in stage.get("modules", []):
                        for concept in module.get("concepts", []):
                            if concept.get("concept_id") == concept_id:
                                return ConceptInfo(
                                    concept_id=concept.get("concept_id"),
                                    name=concept.get("name", ""),
                                    description=concept.get("description", ""),
                                    difficulty=concept.get("difficulty", "medium"),
                                )
                
                return None
        
        except Exception as e:
            logger.error(
                "get_concept_info_failed",
                error=str(e),
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return None
