"""
路线图框架ID规范化工具

功能：
- 统一规范化Stage、Module、Concept的ID
- 移除LLM生成的非标准ID（如xxx-new）
- 确保ID编码符合规范：s-{stage_order}, m-{stage_order}-{module_index}, {roadmap_id}:c-{stage_order}-{module_index}-{concept_index}

Concept ID 格式设计说明：
- 包含 roadmap_id 前缀，确保全局唯一性，避免跨路线图的主键冲突
- 格式：{roadmap_id}:c-{stage_order}-{module_index}-{concept_index}
- 示例：python-intro-6e0864f7:c-1-1-1
"""
import structlog
from app.models.domain import RoadmapFramework, Stage, Module, Concept

logger = structlog.get_logger()


def normalize_framework_ids(framework: RoadmapFramework) -> RoadmapFramework:
    """
    规范化路线图框架中所有节点的ID
    
    规则：
    - Stage ID: s-{stage_order} (如 s-1, s-2)
    - Module ID: m-{stage_order}-{module_index} (如 m-1-1, m-1-2)
    - Concept ID: {roadmap_id}:c-{stage_order}-{module_index}-{concept_index} (如 python-6e0864f7:c-1-1-1)
    
    Args:
        framework: 原始路线图框架（可能包含非标准ID）
        
    Returns:
        ID已规范化的路线图框架
    """
    logger.info(
        "normalizing_framework_ids",
        roadmap_id=framework.roadmap_id,
        stages_count=len(framework.stages),
    )
    
    # 构建旧ID到新ID的映射
    id_mapping: dict[str, str] = {}
    
    # 规范化的新阶段列表
    normalized_stages: list[Stage] = []
    
    for stage in framework.stages:
        stage_order = stage.order
        new_stage_id = f"s-{stage_order}"
        
        # 记录Stage ID映射
        if stage.stage_id != new_stage_id:
            id_mapping[stage.stage_id] = new_stage_id
            logger.debug(
                "stage_id_normalized",
                old_id=stage.stage_id,
                new_id=new_stage_id,
            )
        
        # 规范化Module ID
        normalized_modules: list[Module] = []
        for module_idx, module in enumerate(stage.modules, start=1):
            new_module_id = f"m-{stage_order}-{module_idx}"
            
            # 记录Module ID映射
            if module.module_id != new_module_id:
                id_mapping[module.module_id] = new_module_id
                logger.debug(
                    "module_id_normalized",
                    old_id=module.module_id,
                    new_id=new_module_id,
                )
            
            # 规范化Concept ID
            normalized_concepts: list[Concept] = []
            for concept_idx, concept in enumerate(module.concepts, start=1):
                new_concept_id = f"{framework.roadmap_id}:c-{stage_order}-{module_idx}-{concept_idx}"
                
                # 记录Concept ID映射
                if concept.concept_id != new_concept_id:
                    id_mapping[concept.concept_id] = new_concept_id
                    logger.debug(
                        "concept_id_normalized",
                        old_id=concept.concept_id,
                        new_id=new_concept_id,
                    )
                
                # 创建规范化的Concept（暂时保留旧的prerequisites，稍后更新）
                normalized_concept = concept.model_copy(
                    update={"concept_id": new_concept_id}
                )
                normalized_concepts.append(normalized_concept)
            
            # 创建规范化的Module
            normalized_module = module.model_copy(
                update={
                    "module_id": new_module_id,
                    "concepts": normalized_concepts,
                }
            )
            normalized_modules.append(normalized_module)
        
        # 创建规范化的Stage
        normalized_stage = stage.model_copy(
            update={
                "stage_id": new_stage_id,
                "modules": normalized_modules,
            }
        )
        normalized_stages.append(normalized_stage)
    
    # 第二遍：更新所有Concept的prerequisites引用
    for stage in normalized_stages:
        for module in stage.modules:
            for concept in module.concepts:
                # 更新prerequisites中的旧ID为新ID
                updated_prerequisites = [
                    id_mapping.get(prereq_id, prereq_id)
                    for prereq_id in concept.prerequisites
                ]
                concept.prerequisites = updated_prerequisites
    
    # 创建规范化的RoadmapFramework
    normalized_framework = framework.model_copy(
        update={"stages": normalized_stages}
    )
    
    logger.info(
        "framework_ids_normalized",
        roadmap_id=framework.roadmap_id,
        total_id_changes=len(id_mapping),
    )
    
    return normalized_framework
