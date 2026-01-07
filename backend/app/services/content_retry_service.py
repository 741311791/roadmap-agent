"""
内容重试服务

负责处理:
- 失败内容项目检测
- Concept状态元数据查询
- Framework数据解析
"""
from typing import Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.domain import Concept
from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.crud.crud_roadmap import RoadmapCRUD
from app.models.database import ConceptMetadata, RoadmapMetadata

logger = structlog.get_logger()


class ContentRetryService:
    """内容重试业务逻辑"""
    
    def __init__(self):
        self.concept_crud = get_concept_crud()
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
    
    async def get_failed_content_items_v2(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Dict[str, List[Dict]]:
        """
        基于concept_metadata表获取失败的内容项目（细粒度）
        
        与旧版本的区别:
        - 旧版: 扫描framework_data,按Concept整体判断
        - 新版: 查询concept_metadata表,按内容类型分别判断
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            {
                "tutorial": [{"concept_id": "xxx", "concept_data": {...}, "context": {...}}, ...],
                "resources": [...],
                "quiz": [...]
            }
        """
        
        failed_items = {
            "tutorial": [],
            "resources": [],
            "quiz": [],
        }
        
        # 1. 查询所有concept_metadata
        all_metadata = await self.concept_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not all_metadata:
            logger.warning(
                "no_concept_metadata_found",
                roadmap_id=roadmap_id,
                message="concept_metadata表为空,可能是老数据"
            )
            return failed_items
        
        # 2. 获取framework_data（用于提取concept_data和context）
        roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        
        if not roadmap_metadata or not roadmap_metadata.framework_data:
            logger.error("framework_data_not_found", roadmap_id=roadmap_id)
            return failed_items
        
        framework_data = roadmap_metadata.framework_data
        
        # 3. 构建concept_id -> concept_data/context映射
        concept_lookup = {}
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept_data in module.get("concepts", []):
                    concept_id = concept_data.get("concept_id")
                    context = {
                        "roadmap_id": roadmap_id,
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    }
                    concept_lookup[concept_id] = {
                        "concept_data": concept_data,
                        "context": context,
                    }
        
        # 4. 遍历metadata，识别失败的内容类型
        for metadata in all_metadata:
            concept_id = metadata.concept_id
            concept_info = concept_lookup.get(concept_id)
            
            if not concept_info:
                logger.warning(
                    "concept_not_in_framework",
                    concept_id=concept_id,
                    roadmap_id=roadmap_id,
                )
                continue
            
            # 检查Tutorial
            if metadata.tutorial_status == "failed":
                failed_items["tutorial"].append({
                    "concept_id": concept_id,
                    "concept_data": concept_info["concept_data"],
                    "context": concept_info["context"],
                })
            
            # 检查Resources
            if metadata.resources_status == "failed":
                failed_items["resources"].append({
                    "concept_id": concept_id,
                    "concept_data": concept_info["concept_data"],
                    "context": concept_info["context"],
                })
            
            # 检查Quiz
            if metadata.quiz_status == "failed":
                failed_items["quiz"].append({
                    "concept_id": concept_id,
                    "concept_data": concept_info["concept_data"],
                    "context": concept_info["context"],
                })
        
        logger.info(
            "failed_content_items_v2_collected",
            roadmap_id=roadmap_id,
            tutorial_failed=len(failed_items["tutorial"]),
            resources_failed=len(failed_items["resources"]),
            quiz_failed=len(failed_items["quiz"]),
        )
        
        return failed_items
    
    def get_failed_content_items(self, framework_data: dict) -> Dict[str, List[Dict]]:
        """
        获取失败的内容项目（旧版本，不依赖数据库）
        
        按内容类型分类收集失败的concepts
        
        Args:
            framework_data: 路线图框架数据
            
        Returns:
            {
                "tutorial": [{"concept_id": "xxx", "concept_data": {...}, "context": {...}}, ...],
                "resources": [...],
                "quiz": [...]
            }
        """
        failed_items = {
            "tutorial": [],
            "resources": [],
            "quiz": [],
        }
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept_data in module.get("concepts", []):
                    concept = Concept(**concept_data)
                    context = {
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    }
                    
                    item = {
                        "concept_id": concept.concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    }
                    
                    if not concept.has_tutorial:
                        failed_items["tutorial"].append(item)
                    if not concept.has_resources:
                        failed_items["resources"].append(item)
                    if not concept.has_quiz:
                        failed_items["quiz"].append(item)
        
        return failed_items
    
    def extract_concepts_with_context(self, framework_data: dict) -> List[Tuple[Concept, Dict]]:
        """
        从framework_data中提取Concepts及其上下文
        
        Args:
            framework_data: 路线图框架数据
            
        Returns:
            [(Concept对象, context字典), ...]
        """
        concepts_with_context = []
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept_data in module.get("concepts", []):
                    concept = Concept(**concept_data)
                    context = {
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    }
                    concepts_with_context.append((concept, context))
        
        return concepts_with_context

