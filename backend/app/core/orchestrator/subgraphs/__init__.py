"""
子图模块

包含内容生成子图等独立的工作流子图。

LangGraph 1.0 最佳实践：
- 将并行任务（如内容生成）拆分为子图
- 使用 Send API 实现动态并行
- 子图自动继承父图的 Checkpointer
"""
from .content_generation import build_content_generation_subgraph

__all__ = ["build_content_generation_subgraph"]

