"""业务逻辑层"""

from app.services.notification_service import notification_service, TaskEvent, StepName
from app.services.roadmap_service import RoadmapService
# 延迟导入 task_recovery_service 避免循环依赖
# from app.services.task_recovery_service import (
#     task_recovery_service,
#     TaskRecoveryService,
#     recover_interrupted_tasks_on_startup,
# )
from app.services.execution_logger import ExecutionLogger

__all__ = [
    # 通知服务
    "notification_service",
    "TaskEvent",
    "StepName",
    # 路线图服务
    "RoadmapService",
    # 任务恢复服务（延迟导入，避免循环依赖）
    # "task_recovery_service",
    # "TaskRecoveryService",
    # "recover_interrupted_tasks_on_startup",
    # 执行日志
    "ExecutionLogger",
]

# 延迟导入函数，避免循环依赖
def get_task_recovery_service():
    """延迟导入任务恢复服务"""
    from app.services.task_recovery_service import task_recovery_service
    return task_recovery_service

def get_recover_interrupted_tasks_on_startup():
    """延迟导入恢复函数"""
    from app.services.task_recovery_service import recover_interrupted_tasks_on_startup
    return recover_interrupted_tasks_on_startup
