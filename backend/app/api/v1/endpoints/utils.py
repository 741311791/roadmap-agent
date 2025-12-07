"""
API端点辅助工具函数
"""
from app.models.domain import Concept


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
