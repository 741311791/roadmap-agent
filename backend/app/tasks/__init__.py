"""
Celery 任务模块

包含所有异步任务定义。
"""
# 导入所有任务，确保 Celery Worker 能够发现和注册它们
from app.tasks.log_tasks import batch_write_logs

__all__ = ["batch_write_logs"]

