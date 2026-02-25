"""
Framework Diff Engine（路线图对比引擎）

负责比较新旧路线图框架，自动生成 modified_node_ids。
"""
from typing import List, Set, Dict, Any
import structlog

from app.models.domain import RoadmapFramework, Stage, Module, Concept

logger = structlog.get_logger()


class FrameworkDiff:
    """
    路线图框架对比引擎
    
    职责：
    - 比较新旧路线图框架
    - 识别修改、添加、删除的节点
    - 生成 modified_node_ids 列表
    - 生成修改总结
    """
    
    def __init__(
        self,
        old_framework: RoadmapFramework,
        new_framework: RoadmapFramework
    ):
        """
        初始化对比引擎
        
        Args:
            old_framework: 旧版路线图框架
            new_framework: 新版路线图框架
        """
        self.old_framework = old_framework
        self.new_framework = new_framework
        
        # 构建节点索引
        self.old_nodes = self._build_node_index(old_framework)
        self.new_nodes = self._build_node_index(new_framework)
    
    def _build_node_index(self, framework: RoadmapFramework) -> Dict[str, Any]:
        """
        构建节点索引
        
        Args:
            framework: 路线图框架
            
        Returns:
            节点索引字典 {node_id: node_data}
        """
        index = {}
        
        for stage in framework.stages:
            # 索引 Stage
            index[stage.stage_id] = {
                "type": "stage",
                "name": stage.name,
                "description": stage.description,
                "order": stage.order,
                "module_count": len(stage.modules),
            }
            
            for module in stage.modules:
                # 索引 Module
                index[module.module_id] = {
                    "type": "module",
                    "name": module.name,
                    "description": module.description,
                    "stage_id": stage.stage_id,
                    "concept_count": len(module.concepts),
                }
                
                for concept in module.concepts:
                    # 索引 Concept
                    index[concept.concept_id] = {
                        "type": "concept",
                        "name": concept.name,
                        "description": concept.description,
                        "difficulty": concept.difficulty,
                        "estimated_hours": concept.estimated_hours,
                        "module_id": module.module_id,
                        "stage_id": stage.stage_id,
                    }
        
        return index
    
    def compute_diff(self) -> Dict[str, Any]:
        """
        计算新旧框架的差异
        
        Returns:
            差异报告，包含：
            - modified_node_ids: 被修改的节点 ID 列表
            - added_node_ids: 新增的节点 ID 列表
            - deleted_node_ids: 删除的节点 ID 列表
            - change_summary: 修改总结
        """
        logger.info("framework_diff_computing")
        
        old_ids = set(self.old_nodes.keys())
        new_ids = set(self.new_nodes.keys())
        
        # 计算添加、删除、保留的节点
        added_ids = new_ids - old_ids
        deleted_ids = old_ids - new_ids
        common_ids = old_ids & new_ids
        
        # 在保留的节点中，找出被修改的
        modified_ids = set()
        for node_id in common_ids:
            if self._is_node_modified(node_id):
                modified_ids.add(node_id)
        
        # 生成修改总结
        change_summary = self._generate_summary(
            added_ids, deleted_ids, modified_ids
        )
        
        # 合并所有变更的节点 ID（修改 + 添加 + 删除）
        all_modified_ids = list(modified_ids | added_ids | deleted_ids)
        
        logger.info(
            "framework_diff_completed",
            modified_count=len(modified_ids),
            added_count=len(added_ids),
            deleted_count=len(deleted_ids),
            total_changes=len(all_modified_ids),
        )
        
        return {
            "modified_node_ids": all_modified_ids,
            "added_node_ids": list(added_ids),
            "deleted_node_ids": list(deleted_ids),
            "updated_node_ids": list(modified_ids),
            "change_summary": change_summary,
        }
    
    def _is_node_modified(self, node_id: str) -> bool:
        """
        判断节点是否被修改
        
        Args:
            node_id: 节点 ID
            
        Returns:
            是否被修改
        """
        old_node = self.old_nodes[node_id]
        new_node = self.new_nodes[node_id]
        
        node_type = old_node["type"]
        
        if node_type == "stage":
            return self._is_stage_modified(old_node, new_node)
        elif node_type == "module":
            return self._is_module_modified(old_node, new_node)
        elif node_type == "concept":
            return self._is_concept_modified(old_node, new_node)
        
        return False
    
    def _is_stage_modified(self, old: Dict, new: Dict) -> bool:
        """判断 Stage 是否被修改"""
        return (
            old["name"] != new["name"]
            or old["description"] != new["description"]
            or old["order"] != new["order"]
            or old["module_count"] != new["module_count"]
        )
    
    def _is_module_modified(self, old: Dict, new: Dict) -> bool:
        """判断 Module 是否被修改"""
        return (
            old["name"] != new["name"]
            or old["description"] != new["description"]
            or old["concept_count"] != new["concept_count"]
        )
    
    def _is_concept_modified(self, old: Dict, new: Dict) -> bool:
        """判断 Concept 是否被修改"""
        return (
            old["name"] != new["name"]
            or old["description"] != new["description"]
            or old["difficulty"] != new["difficulty"]
            or old["estimated_hours"] != new["estimated_hours"]
        )
    
    def _generate_summary(
        self,
        added_ids: Set[str],
        deleted_ids: Set[str],
        modified_ids: Set[str]
    ) -> str:
        """
        生成修改总结
        
        Args:
            added_ids: 新增的节点 ID
            deleted_ids: 删除的节点 ID
            modified_ids: 修改的节点 ID
            
        Returns:
            修改总结文本
        """
        summary_parts = []
        
        # 统计各类型节点的变更
        added_stages = [id for id in added_ids if id.startswith("stage-")]
        added_modules = [id for id in added_ids if id.startswith("mod-")]
        added_concepts = [id for id in added_ids if id.startswith("c-")]
        
        deleted_stages = [id for id in deleted_ids if id.startswith("stage-")]
        deleted_modules = [id for id in deleted_ids if id.startswith("mod-")]
        deleted_concepts = [id for id in deleted_ids if id.startswith("c-")]
        
        modified_stages = [id for id in modified_ids if id.startswith("stage-")]
        modified_modules = [id for id in modified_ids if id.startswith("mod-")]
        modified_concepts = [id for id in modified_ids if id.startswith("c-")]
        
        # 生成总结
        if added_stages:
            summary_parts.append(f"新增 {len(added_stages)} 个阶段")
        if added_modules:
            summary_parts.append(f"新增 {len(added_modules)} 个模块")
        if added_concepts:
            summary_parts.append(f"新增 {len(added_concepts)} 个概念")
        
        if deleted_stages:
            summary_parts.append(f"删除 {len(deleted_stages)} 个阶段")
        if deleted_modules:
            summary_parts.append(f"删除 {len(deleted_modules)} 个模块")
        if deleted_concepts:
            summary_parts.append(f"删除 {len(deleted_concepts)} 个概念")
        
        if modified_stages:
            summary_parts.append(f"修改 {len(modified_stages)} 个阶段")
        if modified_modules:
            summary_parts.append(f"修改 {len(modified_modules)} 个模块")
        if modified_concepts:
            summary_parts.append(f"修改 {len(modified_concepts)} 个概念")
        
        if not summary_parts:
            return "路线图未发生变化"
        
        return "、".join(summary_parts)
    
    def get_detailed_changes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取详细的变更信息
        
        Returns:
            详细变更信息，包含每个节点的具体变化
        """
        detailed_changes = {
            "stages": [],
            "modules": [],
            "concepts": [],
        }
        
        # 分析 Stage 变更
        for stage_id in set(self.old_nodes.keys()) | set(self.new_nodes.keys()):
            if not stage_id.startswith("stage-"):
                continue
            
            change = self._analyze_node_change(stage_id, "stage")
            if change:
                detailed_changes["stages"].append(change)
        
        # 分析 Module 变更
        for module_id in set(self.old_nodes.keys()) | set(self.new_nodes.keys()):
            if not module_id.startswith("mod-"):
                continue
            
            change = self._analyze_node_change(module_id, "module")
            if change:
                detailed_changes["modules"].append(change)
        
        # 分析 Concept 变更
        for concept_id in set(self.old_nodes.keys()) | set(self.new_nodes.keys()):
            if not concept_id.startswith("c-"):
                continue
            
            change = self._analyze_node_change(concept_id, "concept")
            if change:
                detailed_changes["concepts"].append(change)
        
        return detailed_changes
    
    def _analyze_node_change(
        self, node_id: str, node_type: str
    ) -> Dict[str, Any] | None:
        """
        分析单个节点的变更
        
        Args:
            node_id: 节点 ID
            node_type: 节点类型
            
        Returns:
            变更信息，如果无变更则返回 None
        """
        old_exists = node_id in self.old_nodes
        new_exists = node_id in self.new_nodes
        
        if not old_exists and new_exists:
            # 新增
            return {
                "node_id": node_id,
                "type": node_type,
                "change_type": "added",
                "old_value": None,
                "new_value": self.new_nodes[node_id],
            }
        elif old_exists and not new_exists:
            # 删除
            return {
                "node_id": node_id,
                "type": node_type,
                "change_type": "deleted",
                "old_value": self.old_nodes[node_id],
                "new_value": None,
            }
        elif old_exists and new_exists:
            # 可能修改
            if self._is_node_modified(node_id):
                return {
                    "node_id": node_id,
                    "type": node_type,
                    "change_type": "modified",
                    "old_value": self.old_nodes[node_id],
                    "new_value": self.new_nodes[node_id],
                    "changes": self._get_field_changes(
                        self.old_nodes[node_id],
                        self.new_nodes[node_id]
                    ),
                }
        
        return None
    
    def _get_field_changes(self, old: Dict, new: Dict) -> Dict[str, Dict]:
        """
        获取字段级别的变更
        
        Args:
            old: 旧节点数据
            new: 新节点数据
            
        Returns:
            字段变更字典
        """
        changes = {}
        
        for key in old.keys():
            if key == "type":
                continue
            
            if old.get(key) != new.get(key):
                changes[key] = {
                    "old": old.get(key),
                    "new": new.get(key),
                }
        
        return changes


def compute_modified_node_ids(
    old_framework: RoadmapFramework,
    new_framework: RoadmapFramework
) -> List[str]:
    """
    计算被修改的节点 ID 列表（便捷函数）
    
    Args:
        old_framework: 旧版路线图框架
        new_framework: 新版路线图框架
        
    Returns:
        被修改的节点 ID 列表
    """
    diff = FrameworkDiff(old_framework, new_framework)
    result = diff.compute_diff()
    return result["modified_node_ids"]


def generate_change_summary(
    old_framework: RoadmapFramework,
    new_framework: RoadmapFramework
) -> str:
    """
    生成修改总结（便捷函数）
    
    Args:
        old_framework: 旧版路线图框架
        new_framework: 新版路线图框架
        
    Returns:
        修改总结文本
    """
    diff = FrameworkDiff(old_framework, new_framework)
    result = diff.compute_diff()
    return result["change_summary"]
