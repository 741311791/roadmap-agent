"""
路线图框架验证工具

提供 framework_data 结构验证功能，包括 concept_id 唯一性检测。
"""
from typing import Tuple, List
import structlog

from app.models.domain import RoadmapFramework

logger = structlog.get_logger()


def validate_concept_ids_uniqueness(framework: RoadmapFramework) -> Tuple[bool, List[str]]:
    """
    检测 framework 中所有 concept_id 的唯一性
    
    Args:
        framework: 路线图框架对象
        
    Returns:
        (是否通过, 重复的 concept_id 列表)
        
    Examples:
        >>> is_valid, duplicates = validate_concept_ids_uniqueness(framework)
        >>> if not is_valid:
        >>>     logger.error("concept_id_duplicates_found", duplicates=duplicates)
    """
    concept_ids = []
    
    # 遍历所有 Stage -> Module -> Concept，收集所有 concept_id
    for stage in framework.stages:
        for module in stage.modules:
            for concept in module.concepts:
                concept_ids.append(concept.concept_id)
    
    # 查找重复的 concept_id
    seen = set()
    duplicates = []
    for cid in concept_ids:
        if cid in seen:
            if cid not in duplicates:  # 避免重复添加
                duplicates.append(cid)
        else:
            seen.add(cid)
    
    is_valid = len(duplicates) == 0
    
    if not is_valid:
        logger.warning(
            "concept_id_uniqueness_check_failed",
            roadmap_id=framework.roadmap_id,
            duplicate_count=len(duplicates),
            duplicates=duplicates,
        )
    else:
        logger.info(
            "concept_id_uniqueness_check_passed",
            roadmap_id=framework.roadmap_id,
            total_concepts=len(concept_ids),
        )
    
    return is_valid, duplicates


def validate_and_raise_if_invalid(framework: RoadmapFramework) -> None:
    """
    验证 framework 的 concept_id 唯一性，如果检测到重复则抛出异常
    
    Args:
        framework: 路线图框架对象
        
    Raises:
        ValueError: 如果检测到重复的 concept_id
        
    Examples:
        >>> try:
        >>>     validate_and_raise_if_invalid(framework)
        >>> except ValueError as e:
        >>>     # 处理验证失败的情况
        >>>     pass
    """
    is_valid, duplicates = validate_concept_ids_uniqueness(framework)
    
    if not is_valid:
        error_message = (
            f"Framework validation failed: Duplicate concept_id(s) found: {', '.join(duplicates)}. "
            f"Each concept_id must be unique across the entire roadmap."
        )
        logger.error(
            "framework_validation_failed",
            roadmap_id=framework.roadmap_id,
            duplicates=duplicates,
            error=error_message,
        )
        raise ValueError(error_message)

