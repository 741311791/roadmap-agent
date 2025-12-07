"""
工作流编排器模块（已重构）

将原有的巨型 orchestrator.py (1643行) 拆分为专注的模块：
- base.py: 基础定义（State、Config、工具函数）
- state_manager.py: 状态管理（live_step 缓存）
- builder.py: 工作流构建器（图结构定义）
- executor.py: 工作流执行器（execute、resume）
- routers.py: 路由逻辑（条件分支）
- node_runners/: 节点执行器（各个Agent的运行逻辑）

使用方式：
    from app.core.orchestrator_factory import get_workflow_executor
    
    executor = get_workflow_executor()
    result = await executor.execute(user_request, task_id)
"""
from .base import RoadmapState, WorkflowConfig, merge_dicts, ensure_unique_roadmap_id
from .state_manager import StateManager
from .executor import WorkflowExecutor
from .builder import WorkflowBuilder
from .routers import WorkflowRouter

__all__ = [
    "RoadmapState",
    "WorkflowConfig",
    "merge_dicts",
    "ensure_unique_roadmap_id",
    "StateManager",
    "WorkflowExecutor",
    "WorkflowBuilder",
    "WorkflowRouter",
]

