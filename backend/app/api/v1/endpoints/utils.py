"""
API端点辅助工具函数
"""
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.domain import Concept

logger = structlog.get_logger()


def get_failed_content_items(framework_data: dict) -> dict:
    """
    获取失败的内容项目
    
    按内容类型分类收集失败的 concepts
    
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
                concept_id = concept_data.get("concept_id")
                context = {
                    "roadmap_id": framework_data.get("roadmap_id"),
                    "stage_id": stage.get("stage_id"),
                    "stage_name": stage.get("name"),
                    "module_id": module.get("module_id"),
                    "module_name": module.get("name"),
                }
                
                # 检查教程状态
                if concept_data.get("content_status") == "failed":
                    failed_items["tutorial"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
                
                # 检查资源状态
                if concept_data.get("resources_status") == "failed":
                    failed_items["resources"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
                
                # 检查测验状态
                if concept_data.get("quiz_status") == "failed":
                    failed_items["quiz"].append({
                        "concept_id": concept_id,
                        "concept_data": concept_data,
                        "context": context,
                    })
    
    return failed_items


def find_concept_in_framework(
    framework_data: dict,
    concept_id: str,
    roadmap_id: str,
) -> tuple[dict | None, dict]:
    """
    在路线图框架中查找概念
    
    Args:
        framework_data: 路线图框架数据
        concept_id: 概念ID
        roadmap_id: 路线图ID
        
    Returns:
        (concept_data, context) 或 (None, {})
    """
    context = {"roadmap_id": roadmap_id}
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for c in module.get("concepts", []):
                if c.get("concept_id") == concept_id:
                    context.update({
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    })
                    return c, context
    
    return None, context


def extract_concepts_from_framework(
    framework_data: dict,
) -> list[tuple[Concept, dict]]:
    """
    从路线图框架数据中提取所有 Concepts 及其上下文
    
    Args:
        framework_data: 路线图框架数据（字典格式）
        
    Returns:
        (Concept, context) 元组的列表
    """
    concepts_with_context = []
    roadmap_id = framework_data.get("roadmap_id", "unknown")
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept_data in module.get("concepts", []):
                # 构建 Concept 对象
                concept = Concept(
                    concept_id=concept_data.get("concept_id"),
                    name=concept_data.get("name"),
                    description=concept_data.get("description", ""),
                    estimated_hours=concept_data.get("estimated_hours", 1.0),
                    prerequisites=concept_data.get("prerequisites", []),
                    difficulty=concept_data.get("difficulty", "medium"),
                    keywords=concept_data.get("keywords", []),
                )
                
                # 构建上下文
                context = {
                    "roadmap_id": roadmap_id,
                    "stage_id": stage.get("stage_id"),
                    "stage_name": stage.get("name"),
                    "module_id": module.get("module_id"),
                    "module_name": module.get("name"),
                }
                
                concepts_with_context.append((concept, context))
    
    return concepts_with_context


async def get_failed_content_items_v2(
    roadmap_id: str,
    session: AsyncSession,
) -> dict:
    """
    基于 concept_metadata 表获取失败的内容项目 (细粒度)
    
    与 get_failed_content_items 的区别:
    - 旧版本: 扫描 framework_data,按 Concept 整体判断
    - 新版本: 查询 concept_metadata 表,按内容类型分别判断
    
    Args:
        roadmap_id: 路线图 ID
        session: 数据库会话
        
    Returns:
        {
            "tutorial": [{"concept_id": "xxx", "concept_data": {...}, "context": {...}}, ...],
            "resources": [...],
            "quiz": [...]
        }
    """
    from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    failed_items = {
        "tutorial": [],
        "resources": [],
        "quiz": [],
    }
    
    # 1. 查询所有 concept_metadata
    concept_meta_repo = ConceptMetadataRepository(session)
    all_metadata = await concept_meta_repo.get_by_roadmap_id(roadmap_id)
    
    if not all_metadata:
        logger.warning(
            "no_concept_metadata_found",
            roadmap_id=roadmap_id,
            message="concept_metadata 表为空,可能是老数据,降级到旧逻辑"
        )
        return failed_items
    
    # 2. 获取 framework_data (用于提取 concept_data 和 context)
    roadmap_repo = RoadmapRepository(session)
    roadmap_metadata = await roadmap_repo.get_roadmap_metadata(roadmap_id)
    
    if not roadmap_metadata or not roadmap_metadata.framework_data:
        logger.error("framework_data_not_found", roadmap_id=roadmap_id)
        return failed_items
    
    framework_data = roadmap_metadata.framework_data
    
    # 3. 构建 concept_id -> concept_data/context 映射
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
    
    # 4. 遍历 concept_metadata,按状态分类
    for meta in all_metadata:
        concept_id = meta.concept_id
        
        # 跳过没有在 framework 中的概念 (理论上不应该发生)
        if concept_id not in concept_lookup:
            logger.warning("concept_not_in_framework", concept_id=concept_id, roadmap_id=roadmap_id)
            continue
        
        lookup_data = concept_lookup[concept_id]
        
        # Tutorial 失败
        if meta.tutorial_status == "failed":
            failed_items["tutorial"].append({
                "concept_id": concept_id,
                "concept_data": lookup_data["concept_data"],
                "context": lookup_data["context"],
            })
        
        # Resources 失败
        if meta.resources_status == "failed":
            failed_items["resources"].append({
                "concept_id": concept_id,
                "concept_data": lookup_data["concept_data"],
                "context": lookup_data["context"],
            })
        
        # Quiz 失败
        if meta.quiz_status == "failed":
            failed_items["quiz"].append({
                "concept_id": concept_id,
                "concept_data": lookup_data["concept_data"],
                "context": lookup_data["context"],
            })
    
    logger.info(
        "failed_content_items_v2_collected",
        roadmap_id=roadmap_id,
        tutorial_failed=len(failed_items["tutorial"]),
        resources_failed=len(failed_items["resources"]),
        quiz_failed=len(failed_items["quiz"]),
    )
    
    return failed_items
