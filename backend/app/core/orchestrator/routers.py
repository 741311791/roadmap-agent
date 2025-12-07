"""
工作流路由逻辑

包含条件路由函数，用于决定工作流的分支走向：
- route_after_validation: 结构验证后的路由
- route_after_human_review: 人工审核后的路由
"""
import structlog
from app.config.settings import settings
from .base import RoadmapState

logger = structlog.get_logger()


class WorkflowRouter:
    """
    工作流路由器
    
    负责根据状态和配置决定工作流的分支走向。
    """
    
    def __init__(self, config):
        """
        Args:
            config: WorkflowConfig实例
        """
        self.config = config
    
    def route_after_validation(self, state: RoadmapState) -> str:
        """
        验证后的路由逻辑
        
        路由规则：
        1. 验证失败且未达到最大重试次数 → 编辑路线图 (A2E)
        2. 验证失败且达到最大重试次数 → 人工审核（或跳过）
        3. 验证通过 → 人工审核（或跳过）→ 教程生成（或结束）
        
        Returns:
            下一个节点名称：
            - "edit_roadmap": 编辑路线图
            - "human_review": 人工审核
            - "tutorial_generation": 教程生成
            - "end": 结束
        """
        validation_result = state.get("validation_result")
        modification_count = state.get("modification_count", 0)
        
        # 验证失败，检查是否需要重试
        if not validation_result or not validation_result.is_valid:
            if modification_count < self.config.max_framework_retry:
                logger.info(
                    "validation_failed_retry",
                    attempt=modification_count + 1,
                    max_retries=self.config.max_framework_retry,
                    task_id=state["task_id"],
                    message="验证未通过，将使用 RoadmapEditor 进行修改",
                )
                return "edit_roadmap"
            else:
                logger.warning(
                    "validation_failed_max_retries_exceeded",
                    modification_count=modification_count,
                    max_retries=self.config.max_framework_retry,
                    task_id=state["task_id"],
                    message="已达到最大重试次数，继续后续流程",
                )
        
        # 验证通过或达到最大重试次数，进入下一阶段
        if not self.config.skip_human_review:
            return "human_review"
        elif not self.config.skip_tutorial_generation:
            return "tutorial_generation"
        else:
            return "end"
    
    def route_after_human_review(self, state: RoadmapState) -> str:
        """
        人工审核后的路由逻辑
        
        路由规则：
        1. 用户批准 → 教程生成（或结束）
        2. 用户拒绝 → 编辑路线图 (A2E)
        
        Returns:
            下一个节点名称：
            - "approved": 批准，继续教程生成
            - "modify": 拒绝，需要修改
            - "end": 结束
        """
        if state.get("human_approved", False):
            # 用户批准
            if self.config.skip_tutorial_generation:
                logger.info(
                    "tutorial_generation_skipped",
                    task_id=state["task_id"],
                )
                return "end"
            return "approved"
        else:
            # 用户拒绝，需要修改
            return "modify"

