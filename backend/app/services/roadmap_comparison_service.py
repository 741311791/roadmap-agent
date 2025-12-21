"""
路线图比对服务

提供通用的路线图框架比对功能，支持识别新增、修改、删除的节点。
用于编辑历史记录和版本管理。
"""
from typing import Dict, List, Set
from pydantic import BaseModel
from app.models.domain import RoadmapFramework, Concept
import structlog

logger = structlog.get_logger(__name__)


class ConceptComparison(BaseModel):
    """
    概念比对结果
    
    记录单个概念的所有字段差异
    """
    concept_id: str
    changes: Dict[str, tuple] = {}  # 字段名 -> (旧值, 新值)
    
    @property
    def has_changes(self) -> bool:
        """是否有任何变化"""
        return len(self.changes) > 0


class ComparisonResult(BaseModel):
    """
    框架比对结果
    
    包含新增、修改、删除的概念 ID 列表
    """
    added_concept_ids: List[str] = []
    modified_concept_ids: List[str] = []
    deleted_concept_ids: List[str] = []
    concept_details: Dict[str, ConceptComparison] = {}  # concept_id -> 详细对比
    
    @property
    def total_changes(self) -> int:
        """总变更数量"""
        return len(self.added_concept_ids) + len(self.modified_concept_ids) + len(self.deleted_concept_ids)
    
    @property
    def all_changed_concept_ids(self) -> List[str]:
        """所有变更的概念 ID（新增+修改+删除）"""
        return self.added_concept_ids + self.modified_concept_ids + self.deleted_concept_ids


class RoadmapComparisonService:
    """
    路线图比对服务
    
    负责比对两个路线图框架，识别所有变更。
    比对的字段包括：
    - name (概念名称)
    - description (描述)
    - estimated_hours (预估学习时长)
    - prerequisites (前置概念列表)
    - difficulty (难度等级)
    - keywords (关键词标签)
    """
    
    def __init__(self):
        self.logger = logger.bind(service="roadmap_comparison")
    
    def compare_frameworks(
        self,
        origin: RoadmapFramework,
        modified: RoadmapFramework
    ) -> ComparisonResult:
        """
        比对两个路线图框架
        
        Args:
            origin: 原始框架
            modified: 修改后的框架
            
        Returns:
            ComparisonResult: 包含所有变更的比对结果
        """
        # 收集原始框架中的所有概念
        origin_concepts = self._extract_concepts(origin)
        modified_concepts = self._extract_concepts(modified)
        
        # 获取概念 ID 集合
        origin_ids = set(origin_concepts.keys())
        modified_ids = set(modified_concepts.keys())
        
        # 识别新增、删除的概念
        added_ids = list(modified_ids - origin_ids)
        deleted_ids = list(origin_ids - modified_ids)
        
        # 识别修改的概念
        common_ids = origin_ids & modified_ids
        modified_ids_list = []
        concept_details = {}
        
        for concept_id in common_ids:
            comparison = self._compare_concepts(
                origin_concepts[concept_id],
                modified_concepts[concept_id]
            )
            
            if comparison.has_changes:
                modified_ids_list.append(concept_id)
                concept_details[concept_id] = comparison
        
        result = ComparisonResult(
            added_concept_ids=sorted(added_ids),
            modified_concept_ids=sorted(modified_ids_list),
            deleted_concept_ids=sorted(deleted_ids),
            concept_details=concept_details,
        )
        
        self.logger.info(
            "framework_comparison_completed",
            added=len(added_ids),
            modified=len(modified_ids_list),
            deleted=len(deleted_ids),
            total_changes=result.total_changes,
        )
        
        return result
    
    def _extract_concepts(self, framework: RoadmapFramework) -> Dict[str, Concept]:
        """
        从框架中提取所有概念
        
        Args:
            framework: 路线图框架
            
        Returns:
            Dict[concept_id, Concept]: 概念 ID 到概念对象的映射
        """
        concepts = {}
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    concepts[concept.concept_id] = concept
        return concepts
    
    def _compare_concepts(
        self,
        origin: Concept,
        modified: Concept
    ) -> ConceptComparison:
        """
        比对两个概念的所有重要字段
        
        Args:
            origin: 原始概念
            modified: 修改后的概念
            
        Returns:
            ConceptComparison: 概念比对结果
        """
        changes = {}
        
        # 比对名称
        if origin.name != modified.name:
            changes["name"] = (origin.name, modified.name)
        
        # 比对描述
        if origin.description != modified.description:
            changes["description"] = (origin.description, modified.description)
        
        # 比对预估学习时长
        if origin.estimated_hours != modified.estimated_hours:
            changes["estimated_hours"] = (origin.estimated_hours, modified.estimated_hours)
        
        # 比对前置概念列表（需要排序后比较）
        origin_prereqs = sorted(origin.prerequisites)
        modified_prereqs = sorted(modified.prerequisites)
        if origin_prereqs != modified_prereqs:
            changes["prerequisites"] = (origin_prereqs, modified_prereqs)
        
        # 比对难度等级
        if origin.difficulty != modified.difficulty:
            changes["difficulty"] = (origin.difficulty, modified.difficulty)
        
        # 比对关键词标签（需要排序后比较）
        origin_keywords = sorted(origin.keywords)
        modified_keywords = sorted(modified.keywords)
        if origin_keywords != modified_keywords:
            changes["keywords"] = (origin_keywords, modified_keywords)
        
        return ConceptComparison(
            concept_id=origin.concept_id,
            changes=changes
        )
    
    def get_modified_node_ids_simple(
        self,
        origin: RoadmapFramework,
        modified: RoadmapFramework
    ) -> List[str]:
        """
        简化版本：只返回修改过的节点 ID 列表
        
        包括新增和修改的节点，不包括删除的节点。
        适用于前端高亮显示场景。
        
        Args:
            origin: 原始框架
            modified: 修改后的框架
            
        Returns:
            List[str]: 修改过的 concept_id 列表
        """
        result = self.compare_frameworks(origin, modified)
        # 合并新增和修改的节点 ID（删除的节点不高亮）
        return result.added_concept_ids + result.modified_concept_ids
