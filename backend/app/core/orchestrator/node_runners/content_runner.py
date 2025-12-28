"""
内容生成节点执行器（Celery 迁移版）

负责执行内容生成节点（Step 5: Content Generation）
已迁移到 Celery 独立进程，避免阻塞 FastAPI 主应用。

架构变化：
- 旧方案: 在 FastAPI BackgroundTasks 中并行生成（阻塞事件循环）
- 新方案: 发送任务到 Celery 队列，由独立 Worker 进程执行

职责变化：
- 不再直接执行 Agent 并行生成
- 转而发送 Celery 任务到 content_generation 队列
- 立即返回，不等待内容生成完成
"""
import structlog

from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ContentRunner:
    """
    内容生成节点执行器（Celery 迁移版）
    
    职责（已简化）：
    1. 从 state 中提取必要数据
    2. 发送 Celery 任务到 content_generation 队列
    3. 立即返回，标记内容生成已启动
    
    已移除职责：
    - ❌ 不再直接执行 Agent 并行生成
    - ❌ 不再使用信号量控制并发
    - ❌ 不再处理部分失败场景
    - ❌ 不再批量保存结果
    
    新增优势：
    - ✅ FastAPI 进程不被阻塞
    - ✅ 内容生成在独立进程中执行
    - ✅ 支持任务重试和故障恢复
    - ✅ 更好的资源隔离和监控
    """
    
    def __init__(
        self,
        brain: WorkflowBrain,
    ):
        """
        Args:
            brain: WorkflowBrain 实例（统一协调者）
        """
        self.brain = brain
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行内容生成节点（Celery 迁移版）
        
        简化后的逻辑：
        1. 使用 brain.node_execution() 自动处理状态/日志/通知
        2. 提取 roadmap_framework 和 user_request
        3. 发送 Celery 任务（异步，立即返回）
        4. 返回状态更新（标记内容生成已启动）
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        # 使用 WorkflowBrain 统一管理执行生命周期
        async with self.brain.node_execution("content_generation", state):
            framework = state.get("roadmap_framework")
            if not framework:
                raise ValueError("路线图框架不存在，无法生成内容")
            
            roadmap_id = state.get("roadmap_id")
            if not roadmap_id:
                raise ValueError("roadmap_id 不存在，无法生成内容")
            
            task_id = state["task_id"]
            user_request = state["user_request"]
            
            logger.info(
                "content_runner_dispatching_celery_task",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
            
            # 发送 Celery 任务（异步，立即返回）
            from app.tasks.content_generation_tasks import generate_roadmap_content
            
            celery_task = generate_roadmap_content.delay(
                task_id=task_id,
                roadmap_id=roadmap_id,
                roadmap_framework_data=framework.model_dump(mode="json"),
                user_preferences_data=user_request.preferences.model_dump(mode="json"),
            )
            
            logger.info(
                "content_runner_celery_task_queued",
                task_id=task_id,
                roadmap_id=roadmap_id,
                celery_task_id=celery_task.id,
            )
            
            # 更新任务状态，记录 Celery task ID
            await self.brain.save_celery_task_id(
                task_id=task_id,
                celery_task_id=celery_task.id,
            )
            
            # 返回纯状态更新
            return {
                "content_generation_status": "queued",
                "celery_task_id": celery_task.id,
                "current_step": "content_generation_queued",
                "execution_history": [
                    f"内容生成任务已发送到 Celery 队列（Task ID: {celery_task.id}）"
                ],
            }
