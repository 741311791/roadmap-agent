"""
Celery 任务模块

包含所有异步任务定义。

架构重构（v2.0）：
- 业务逻辑集中在 Service 层（WorkflowExecutionService）
- Task 层仅负责异步调度
"""
# 导入所有任务，确保 Celery Worker 能够发现和注册它们
from app.tasks.log_tasks import batch_write_logs
from app.tasks.maintenance_tasks import (
    cleanup_old_checkpoints,
    monitor_checkpoint_size,
)
from app.tasks.roadmap_generation_tasks import generate_roadmap
from app.tasks.workflow_resume_tasks import (
    resume_after_review,
    resume_from_checkpoint,
)
from app.tasks.cover_image_tasks import (
    generate_cover_image_task,
    batch_generate_cover_images_task,
)
from app.tasks.content_utils import retry_single_content
from app.tasks.content_generation_tasks import (
    generate_all_content_task,
    # ✅ 已删除废弃任务：generate_concept_content_task, finalize_content_generation
    # 改为使用 LangGraph 子图自动编排
)

__all__ = [
    "batch_write_logs",
    "cleanup_old_checkpoints",
    "monitor_checkpoint_size",
    "generate_roadmap",
    "resume_after_review",
    "resume_from_checkpoint",
    "generate_cover_image_task",
    "batch_generate_cover_images_task",
    "retry_single_content",
    "generate_all_content_task",
    # ✅ 已删除：generate_concept_content_task, finalize_content_generation
]

