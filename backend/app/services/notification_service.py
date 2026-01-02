"""
通知服务（基于 Redis Pub/Sub）

用于在工作流关键节点发布事件，WebSocket 端点订阅并推送给客户端。

事件类型：
- progress: 任务进度更新
- human_review_required: 人工审核请求
- completed: 任务完成
- failed: 任务失败

Concept 级别事件：
- concept_start: 概念内容生成开始
- concept_complete: 概念内容生成完成
- concept_failed: 概念内容生成失败
- batch_start: 批次处理开始
- batch_complete: 批次处理完成
"""
from typing import AsyncIterator, Optional
from datetime import datetime
import json
import asyncio
import structlog

from app.db.redis_client import redis_client
from app.models.database import beijing_now

logger = structlog.get_logger()


# Redis 频道前缀
CHANNEL_PREFIX = "roadmap:task:"


class TaskEvent:
    """任务事件类型常量"""
    # 阶段级别事件
    PROGRESS = "progress"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    COMPLETED = "completed"
    FAILED = "failed"
    
    # Concept 级别事件
    CONCEPT_START = "concept_start"
    CONCEPT_COMPLETE = "concept_complete"
    CONCEPT_FAILED = "concept_failed"
    CONCEPT_ALL_CONTENT_COMPLETE = "concept_all_content_complete"  # 🆕 三项内容全部完成
    BATCH_START = "batch_start"
    BATCH_COMPLETE = "batch_complete"
    
    # 重试任务事件
    RETRY_STARTED = "retry_started"
    RETRY_ITEM_COMPLETE = "retry_item_complete"
    RETRY_COMPLETED = "retry_completed"
    
    # 任务恢复事件
    TASK_RECOVERING = "task_recovering"


class StepName:
    """步骤名称常量"""
    QUEUED = "queued"
    INTENT_ANALYSIS = "intent_analysis"
    CURRICULUM_DESIGN = "curriculum_design"
    STRUCTURE_VALIDATION = "structure_validation"
    HUMAN_REVIEW = "human_review"
    ROADMAP_EDIT = "roadmap_edit"
    CONTENT_GENERATION = "content_generation"
    COMPLETED = "completed"
    FAILED = "failed"


class HumanReviewSubStatus:
    """人工审核子状态常量"""
    WAITING = "waiting"
    EDITING = "editing"


class NotificationService:
    """
    通知服务
    
    使用 Redis Pub/Sub 实现任务进度的实时推送。
    
    发布端：工作流 Orchestrator 在关键节点调用 publish_* 方法
    订阅端：WebSocket 端点调用 subscribe 方法获取事件流
    """
    
    def __init__(self):
        self._subscriptions: dict[str, asyncio.Task] = {}
    
    def _get_channel(self, task_id: str) -> str:
        """获取任务对应的 Redis 频道名"""
        return f"{CHANNEL_PREFIX}{task_id}"
    
    async def _ensure_connected(self):
        """确保 Redis 连接"""
        await redis_client.connect()
    
    async def publish_progress(
        self,
        task_id: str,
        step: str,
        status: str = "processing",
        message: Optional[str] = None,
        extra_data: Optional[dict] = None,
        sub_status: Optional[str] = None,
    ):
        """
        发布进度更新事件
        
        Args:
            task_id: 任务 ID
            step: 当前步骤（如 intent_analysis, curriculum_design）
            status: 状态（processing, completed 等）
            message: 可选的消息文本
            extra_data: 额外数据
            sub_status: 子状态（用于 human_review 步骤：waiting/editing）
        """
        event = {
            "type": TaskEvent.PROGRESS,
            "task_id": task_id,
            "step": step,
            "status": status,
            "timestamp": beijing_now().isoformat(),
        }
        
        if message:
            event["message"] = message
        if extra_data:
            event["data"] = extra_data
        if sub_status:
            event["sub_status"] = sub_status
        
        await self._publish(task_id, event)
    
    async def publish_human_review_required(
        self,
        task_id: str,
        roadmap_id: str,
        roadmap_title: str,
        stages_count: int,
    ):
        """
        发布人工审核请求事件
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            roadmap_title: 路线图标题
            stages_count: 阶段数量
        """
        event = {
            "type": TaskEvent.HUMAN_REVIEW_REQUIRED,
            "task_id": task_id,
            "roadmap_id": roadmap_id,
            "roadmap_title": roadmap_title,
            "stages_count": stages_count,
            "timestamp": beijing_now().isoformat(),
            "message": "路线图框架已生成，请审核",
        }
        
        await self._publish(task_id, event)
    
    async def publish_completed(
        self,
        task_id: str,
        roadmap_id: str,
        tutorials_count: Optional[int] = None,
        failed_count: Optional[int] = None,
    ):
        """
        发布任务完成事件
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            tutorials_count: 生成的教程数量
            failed_count: 失败的教程数量
        """
        event = {
            "type": TaskEvent.COMPLETED,
            "task_id": task_id,
            "roadmap_id": roadmap_id,
            "timestamp": beijing_now().isoformat(),
            "message": "路线图生成完成",
        }
        
        if tutorials_count is not None:
            event["tutorials_count"] = tutorials_count
        if failed_count is not None:
            event["failed_count"] = failed_count
        
        await self._publish(task_id, event)
        
        # 记录任务完成的详细日志（新增 - 用于前端展示）
        from app.services.execution_logger import execution_logger, LogCategory
        
        # 注意：这里无法获取完整的framework信息，所以只记录基本统计
        # 前端可以通过roadmap_id获取完整信息
        await execution_logger.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            step="completed",
            roadmap_id=roadmap_id,
            message="🎉 Roadmap generation completed successfully!",
            details={
                "log_type": "task_completed",
                "roadmap_id": roadmap_id,
                "roadmap_url": f"/roadmap/{roadmap_id}",
                "statistics": {
                    "tutorials_generated": tutorials_count if tutorials_count else 0,
                    "failed_concepts": failed_count if failed_count else 0,
                },
                "next_actions": [
                    {
                        "action": "view_roadmap",
                        "label": "View Roadmap",
                        "url": f"/roadmap/{roadmap_id}",
                        "primary": True,
                    },
                ],
            },
        )
    
    async def publish_failed(
        self,
        task_id: str,
        error: str,
        step: Optional[str] = None,
    ):
        """
        发布任务失败事件
        
        Args:
            task_id: 任务 ID
            error: 错误信息
            step: 失败的步骤
        """
        event = {
            "type": TaskEvent.FAILED,
            "task_id": task_id,
            "error": error,
            "timestamp": beijing_now().isoformat(),
            "message": f"任务失败: {error[:100]}",
        }
        
        if step:
            event["step"] = step
        
        await self._publish(task_id, event)
    
    async def notify_task_recovering(
        self,
        task_id: str,
        roadmap_id: Optional[str] = None,
        current_step: Optional[str] = None,
    ):
        """
        发布任务恢复事件
        
        当服务器重启后自动恢复被中断的任务时发送此事件。
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID（可选）
            current_step: 恢复时的步骤（从 checkpoint 获取）
        """
        event = {
            "type": TaskEvent.TASK_RECOVERING,
            "task_id": task_id,
            "timestamp": beijing_now().isoformat(),
            "message": "任务正在从服务器重启中恢复执行",
        }
        
        if roadmap_id:
            event["roadmap_id"] = roadmap_id
        if current_step:
            event["current_step"] = current_step
        
        await self._publish(task_id, event)
        
        logger.info(
            "task_recovering_notification_sent",
            task_id=task_id,
            roadmap_id=roadmap_id,
            current_step=current_step,
        )
    
    # ============================================================
    # Concept 级别事件发布方法
    # ============================================================
    
    async def publish_concept_start(
        self,
        task_id: str,
        concept_id: str,
        concept_name: str,
        current: int,
        total: int,
        content_type: str = "tutorial",
    ):
        """
        发布概念内容生成开始事件
        
        Args:
            task_id: 任务 ID
            concept_id: 概念 ID
            concept_name: 概念名称
            current: 当前进度（第几个）
            total: 总数
            content_type: 内容类型 (tutorial/resources/quiz)
        """
        percentage = round(current / total * 100, 1) if total > 0 else 0
        
        event = {
            "type": TaskEvent.CONCEPT_START,
            "task_id": task_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "content_type": content_type,
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
            },
            "timestamp": beijing_now().isoformat(),
            "message": f"开始生成内容: {concept_name}",
        }
        
        await self._publish(task_id, event)
    
    async def publish_concept_complete(
        self,
        task_id: str,
        concept_id: str,
        concept_name: str,
        data: Optional[dict] = None,
        content_type: str = "tutorial",
    ):
        """
        发布概念内容生成完成事件
        
        Args:
            task_id: 任务 ID
            concept_id: 概念 ID
            concept_name: 概念名称
            data: 生成的内容数据（如 tutorial_id, content_url 等）
            content_type: 内容类型 (tutorial/resources/quiz)
        """
        event = {
            "type": TaskEvent.CONCEPT_COMPLETE,
            "task_id": task_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "content_type": content_type,
            "timestamp": beijing_now().isoformat(),
            "message": f"内容生成完成: {concept_name}",
        }
        
        if data:
            event["data"] = data
        
        await self._publish(task_id, event)
    
    async def publish_concept_failed(
        self,
        task_id: str,
        concept_id: str,
        concept_name: str,
        error: str,
        content_type: str = "tutorial",
    ):
        """
        发布概念内容生成失败事件
        
        Args:
            task_id: 任务 ID
            concept_id: 概念 ID
            concept_name: 概念名称
            content_type: 内容类型 (tutorial/resources/quiz)
            error: 错误信息
        """
        event = {
            "type": TaskEvent.CONCEPT_FAILED,
            "task_id": task_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "content_type": content_type,
            "error": error[:200],  # 限制错误信息长度
            "timestamp": beijing_now().isoformat(),
            "message": f"内容生成失败: {concept_name}",
        }
        
        await self._publish(task_id, event)
    
    async def publish_concept_all_content_complete(
        self,
        task_id: str,
        concept_id: str,
        concept_name: str,
        data: Optional[dict] = None,
    ):
        """
        发布 Concept 全部内容完成事件（Tutorial + Resource + Quiz）
        
        与 publish_concept_complete 的区别：
        - concept_complete: 单项内容完成时发送（如 Tutorial 完成）
        - concept_all_content_complete: 三项内容全部完成时发送（用于前端更新节点状态）
        
        Args:
            task_id: 任务 ID
            concept_id: 概念 ID
            concept_name: 概念名称
            data: 生成的内容数据（包含 tutorial_id, resources_id, quiz_id）
        """
        event = {
            "type": TaskEvent.CONCEPT_ALL_CONTENT_COMPLETE,
            "task_id": task_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "timestamp": beijing_now().isoformat(),
            "message": f"✅ Concept 完整内容已生成: {concept_name}",
        }
        
        if data:
            event["data"] = data
        
        await self._publish(task_id, event)
    
    async def publish_batch_start(
        self,
        task_id: str,
        batch_index: int,
        batch_size: int,
        total_batches: int,
        concept_ids: list[str],
    ):
        """
        发布批次处理开始事件
        
        Args:
            task_id: 任务 ID
            batch_index: 当前批次索引（从 1 开始）
            batch_size: 当前批次大小
            total_batches: 总批次数
            concept_ids: 本批次包含的概念 ID 列表
        """
        event = {
            "type": TaskEvent.BATCH_START,
            "task_id": task_id,
            "batch_index": batch_index,
            "batch_size": batch_size,
            "total_batches": total_batches,
            "concept_ids": concept_ids,
            "timestamp": beijing_now().isoformat(),
            "message": f"开始处理批次 {batch_index}/{total_batches}",
        }
        
        await self._publish(task_id, event)
    
    async def publish_batch_complete(
        self,
        task_id: str,
        batch_index: int,
        total_batches: int,
        completed: int,
        failed: int,
        total: int,
    ):
        """
        发布批次处理完成事件
        
        Args:
            task_id: 任务 ID
            batch_index: 当前批次索引（从 1 开始）
            total_batches: 总批次数
            completed: 已完成数量
            failed: 已失败数量
            total: 总数量
        """
        percentage = round((completed + failed) / total * 100, 1) if total > 0 else 0
        
        event = {
            "type": TaskEvent.BATCH_COMPLETE,
            "task_id": task_id,
            "batch_index": batch_index,
            "total_batches": total_batches,
            "progress": {
                "completed": completed,
                "failed": failed,
                "total": total,
                "percentage": percentage,
            },
            "timestamp": beijing_now().isoformat(),
            "message": f"批次 {batch_index}/{total_batches} 处理完成",
        }
        
        await self._publish(task_id, event)
    
    async def _publish(self, task_id: str, event: dict):
        """
        发布事件到 Redis 频道
        
        如果 Redis 连接失败或超时，会记录错误但不会抛出异常，
        确保工作流不会因为通知失败而中断。
        
        在异常处理上下文中调用时，能够优雅处理事件循环冲突。
        
        Args:
            task_id: 任务 ID
            event: 事件数据
        """
        try:
            await self._ensure_connected()
            channel = self._get_channel(task_id)
            
            message = json.dumps(event, ensure_ascii=False)
            
            # 添加超时保护：5秒超时
            # 注意：在异常处理上下文中，asyncio.wait_for 可能触发事件循环冲突
            # 因此需要捕获 RuntimeError
            await asyncio.wait_for(
                redis_client._client.publish(channel, message),
                timeout=5.0
            )
            
            logger.debug(
                "notification_published",
                task_id=task_id,
                event_type=event.get("type"),
                channel=channel,
            )
            
        except asyncio.TimeoutError:
            logger.error(
                "notification_publish_timeout",
                task_id=task_id,
                event_type=event.get("type"),
                timeout_seconds=5,
            )
        except RuntimeError as e:
            # 事件循环冲突（如 "Future attached to a different loop"）
            logger.error(
                "notification_publish_failed",
                task_id=task_id,
                event_type=event.get("type"),
                error=f"Event loop conflict: {str(e)}",
            )
        except Exception as e:
            logger.error(
                "notification_publish_failed",
                task_id=task_id,
                event_type=event.get("type"),
                error=str(e),
            )
    
    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """
        订阅任务事件流
        
        Args:
            task_id: 任务 ID
            
        Yields:
            事件字典
            
        Example:
            ```python
            async for event in notification_service.subscribe("task-123"):
                print(event)
                if event["type"] == "completed":
                    break
            ```
        """
        await self._ensure_connected()
        channel = self._get_channel(task_id)
        
        # 创建 Pub/Sub 订阅
        pubsub = redis_client._client.pubsub()
        
        try:
            await pubsub.subscribe(channel)
            
            logger.info(
                "notification_subscribed",
                task_id=task_id,
                channel=channel,
            )
            
            # 持续监听消息
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = message["data"]
                        # Redis 返回的可能是 bytes 或 str
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        
                        event = json.loads(data)
                        yield event
                        
                        # 如果是终止事件，结束订阅
                        if event.get("type") in (TaskEvent.COMPLETED, TaskEvent.FAILED):
                            logger.info(
                                "notification_subscription_ended",
                                task_id=task_id,
                                reason=event.get("type"),
                            )
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "notification_message_decode_error",
                            task_id=task_id,
                            error=str(e),
                        )
                        continue
        
        except asyncio.CancelledError:
            logger.info(
                "notification_subscription_cancelled",
                task_id=task_id,
            )
            raise
        
        except Exception as e:
            logger.error(
                "notification_subscription_error",
                task_id=task_id,
                error=str(e),
            )
            raise
        
        finally:
            # 清理订阅
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            
            logger.debug(
                "notification_subscription_cleanup",
                task_id=task_id,
            )
    
    async def subscribe_with_timeout(
        self,
        task_id: str,
        timeout_seconds: int = 3600,  # 默认 1 小时超时
    ) -> AsyncIterator[dict]:
        """
        带超时的订阅
        
        Args:
            task_id: 任务 ID
            timeout_seconds: 超时时间（秒）
            
        Yields:
            事件字典
        """
        try:
            async with asyncio.timeout(timeout_seconds):
                async for event in self.subscribe(task_id):
                    yield event
        except asyncio.TimeoutError:
            logger.warning(
                "notification_subscription_timeout",
                task_id=task_id,
                timeout_seconds=timeout_seconds,
            )
            yield {
                "type": "timeout",
                "task_id": task_id,
                "message": f"订阅超时（{timeout_seconds}秒）",
                "timestamp": beijing_now().isoformat(),
            }


# 全局单例
notification_service = NotificationService()

