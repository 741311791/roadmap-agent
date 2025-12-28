"""
执行日志服务 (ExecutionLogger) - Celery 异步队列版本

提供结构化日志记录功能，用于：
- 通过 task_id 追踪请求完整生命周期
- 聚合错误报告
- 性能分析和问题定位

重构版本特点：
- 使用 Celery 异步任务处理日志写入
- 完全解耦主流程和数据库操作
- 本地缓冲区减少 Celery 任务数量
- API 兼容性：所有方法签名保持不变

使用示例：
    ```python
    from app.services.execution_logger import execution_logger

    # 记录工作流开始
    await execution_logger.log_workflow_start(
        task_id="abc-123",
        step="intent_analysis",
        message="开始需求分析",
    )

    # 记录 Agent 执行
    await execution_logger.log_agent_complete(
        task_id="abc-123",
        agent_name="IntentAnalyzer",
        message="需求分析完成",
        duration_ms=1500,
        details={"key_technologies": ["Python", "FastAPI"]},
    )

    # 记录错误
    await execution_logger.error(
        task_id="abc-123",
        category="agent",
        message="教程生成失败",
        details={"error": str(e), "concept_id": "concept-1"},
    )
    ```
"""
from typing import Optional
import time
import asyncio
from contextlib import asynccontextmanager
import structlog

from app.models.database import ExecutionLog, beijing_now

logger = structlog.get_logger()


class LogLevel:
    """日志级别常量"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogCategory:
    """日志分类常量"""
    WORKFLOW = "workflow"
    AGENT = "agent"
    TOOL = "tool"
    DATABASE = "database"
    API = "api"
    RETRY = "retry"


class ExecutionLogger:
    """
    执行日志服务（Celery 异步队列版本）
    
    所有日志写入都通过 Celery 异步任务处理，完全解耦主流程和数据库操作。
    支持所有工作流节点和重试场景。
    
    架构：
    - 本地缓冲区：减少 Celery 任务数量
    - 批量发送：达到阈值或超时时发送
    - 异步处理：不阻塞主流程
    - 降级保护：发送失败时重新入队
    """
    
    def __init__(self):
        # 本地缓冲区：减少 Celery 任务数量
        self._log_buffer: list[dict] = []
        self._buffer_size = 50  # 本地缓冲区大小
        self._flush_interval = 2.0  # 2 秒刷新一次
        self._last_flush_time = time.time()
        self._flush_lock = asyncio.Lock()  # 防止并发刷新
    
    async def log(
        self,
        task_id: str,
        level: str,
        category: str,
        message: str,
        step: Optional[str] = None,
        agent_name: Optional[str] = None,
        roadmap_id: Optional[str] = None,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> ExecutionLog:
        """
        写入执行日志（异步，非阻塞）
        
        将日志数据放入本地缓冲区，达到批量大小或超时时，
        发送到 Celery 任务队列。
        
        支持所有场景：
        - 工作流节点日志（IntentAnalysis, CurriculumDesign, Validation 等）
        - Agent 执行日志（开始、完成、错误）
        - 工具调用日志
        - 重试场景日志
        - 错误处理日志
        
        Args:
            task_id: 任务 ID
            level: 日志级别 (debug, info, warning, error)
            category: 日志分类 (workflow, agent, tool, database)
            message: 日志消息
            step: 当前步骤（可选）
            agent_name: Agent 名称（可选）
            roadmap_id: 路线图 ID（可选）
            concept_id: 概念 ID（可选）
            details: 详细数据（可选）
            duration_ms: 执行耗时毫秒（可选）
            
        Returns:
            创建的日志记录（注意：实际写入是异步的，返回的对象可能还没有 ID）
        """
        # 构建日志数据字典
        log_data = {
            "task_id": task_id,
            "level": level,
            "category": category,
            "message": message,
            "step": step,
            "agent_name": agent_name,
            "roadmap_id": roadmap_id,
            "concept_id": concept_id,
            "details": details,
            "duration_ms": duration_ms,
            "created_at": beijing_now(),
        }
        
        # 添加到本地缓冲区
        async with self._flush_lock:
            self._log_buffer.append(log_data)
            
            # 检查是否需要刷新
            current_time = time.time()
            should_flush = (
                len(self._log_buffer) >= self._buffer_size or
                (current_time - self._last_flush_time) >= self._flush_interval
            )
            
            if should_flush:
                await self._flush_to_celery()
        
        # 返回模拟的 ExecutionLog 对象（保持 API 兼容性）
        # 注意：实际写入是异步的，这个对象可能还没有数据库 ID
        return ExecutionLog(**log_data)
    
    async def _flush_to_celery(self):
        """将缓冲区中的日志发送到 Celery"""
        if not self._log_buffer:
            return
        
        batch = self._log_buffer.copy()
        self._log_buffer.clear()
        self._last_flush_time = time.time()
        
        # 发送到 Celery（非阻塞）
        try:
            # 延迟导入避免循环依赖
            from app.tasks.log_tasks import batch_write_logs
            
            # 使用 apply_async 异步发送，不等待结果
            batch_write_logs.apply_async(
                args=[batch],
                queue="logs",
            )
        except Exception as e:
            logger.warning(
                "execution_logger_celery_send_failed",
                error=str(e),
                batch_size=len(batch),
                error_type=type(e).__name__,
            )
            # 发送失败时的降级方案：重新放入缓冲区
            # 这样不会丢失日志，但可能导致内存增长
            self._log_buffer.extend(batch)
    
    async def flush(self):
        """
        立即刷新所有待发送的日志
        
        用于应用关闭时确保所有日志都被发送。
        """
        async with self._flush_lock:
            if self._log_buffer:
                await self._flush_to_celery()
    
    # ============================================================
    # 便捷方法：按日志级别（保持不变，内部调用 log()）
    # ============================================================
    
    async def debug(
        self,
        task_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录调试日志"""
        return await self.log(task_id, LogLevel.DEBUG, category, message, **kwargs)
    
    async def info(
        self,
        task_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录信息日志"""
        return await self.log(task_id, LogLevel.INFO, category, message, **kwargs)
    
    async def warning(
        self,
        task_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录警告日志"""
        return await self.log(task_id, LogLevel.WARNING, category, message, **kwargs)
    
    async def error(
        self,
        task_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录错误日志"""
        return await self.log(task_id, LogLevel.ERROR, category, message, **kwargs)
    
    # ============================================================
    # 便捷方法：按使用场景（保持不变，内部调用 log()）
    # ============================================================
    
    async def log_workflow_start(
        self,
        task_id: str,
        step: str,
        message: str,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录工作流步骤开始"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            message=message,
            step=step,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_workflow_complete(
        self,
        task_id: str,
        step: str,
        message: str,
        duration_ms: Optional[int] = None,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录工作流步骤完成"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            message=message,
            step=step,
            duration_ms=duration_ms,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_agent_start(
        self,
        task_id: str,
        agent_name: str,
        message: str,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录 Agent 开始执行"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            concept_id=concept_id,
            details=details,
        )
    
    async def log_agent_complete(
        self,
        task_id: str,
        agent_name: str,
        message: str,
        duration_ms: Optional[int] = None,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录 Agent 执行完成"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            duration_ms=duration_ms,
            concept_id=concept_id,
            details=details,
        )
    
    async def log_agent_error(
        self,
        task_id: str,
        agent_name: str,
        message: str,
        error: str,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录 Agent 执行错误"""
        error_details = {"error": error}
        if details:
            error_details.update(details)
        
        return await self.error(
            task_id=task_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            concept_id=concept_id,
            details=error_details,
        )
    
    async def log_tool_call(
        self,
        task_id: str,
        agent_name: str,
        tool_name: str,
        message: str,
        duration_ms: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录工具调用"""
        tool_details = {"tool_name": tool_name}
        if details:
            tool_details.update(details)
        
        return await self.debug(
            task_id=task_id,
            category=LogCategory.TOOL,
            message=message,
            agent_name=agent_name,
            duration_ms=duration_ms,
            details=tool_details,
        )
    
    async def log_retry_start(
        self,
        task_id: str,
        message: str,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录重试开始"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.RETRY,
            message=message,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_retry_complete(
        self,
        task_id: str,
        message: str,
        duration_ms: Optional[int] = None,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录重试完成"""
        return await self.info(
            task_id=task_id,
            category=LogCategory.RETRY,
            message=message,
            duration_ms=duration_ms,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    # ============================================================
    # 上下文管理器：自动计时（保持不变）
    # ============================================================
    
    @asynccontextmanager
    async def timed_operation(
        self,
        task_id: str,
        category: str,
        operation_name: str,
        agent_name: Optional[str] = None,
        concept_id: Optional[str] = None,
        roadmap_id: Optional[str] = None,
    ):
        """
        计时上下文管理器
        
        自动记录操作开始和结束，并计算耗时。
        
        使用示例：
            ```python
            async with execution_logger.timed_operation(
                task_id="abc-123",
                category="agent",
                operation_name="TutorialGenerator",
                concept_id="concept-1",
            ) as timer:
                # 执行操作
                result = await generate_tutorial()
                timer.set_details({"title": result.title})
            ```
        """
        start_time = time.time()
        timer = _TimerContext()
        
        # 记录开始
        await self.info(
            task_id=task_id,
            category=category,
            message=f"{operation_name} 开始",
            agent_name=agent_name,
            concept_id=concept_id,
            roadmap_id=roadmap_id,
        )
        
        try:
            yield timer
            
            # 记录成功完成
            duration_ms = int((time.time() - start_time) * 1000)
            await self.info(
                task_id=task_id,
                category=category,
                message=f"{operation_name} 完成",
                agent_name=agent_name,
                concept_id=concept_id,
                roadmap_id=roadmap_id,
                duration_ms=duration_ms,
                details=timer.details,
            )
            
        except Exception as e:
            # 记录失败
            duration_ms = int((time.time() - start_time) * 1000)
            await self.error(
                task_id=task_id,
                category=category,
                message=f"{operation_name} 失败: {str(e)[:100]}",
                agent_name=agent_name,
                concept_id=concept_id,
                roadmap_id=roadmap_id,
                duration_ms=duration_ms,
                details={"error": str(e), **(timer.details or {})},
            )
            raise


class _TimerContext:
    """计时上下文辅助类"""
    
    def __init__(self):
        self.details: Optional[dict] = None
    
    def set_details(self, details: dict):
        """设置详细数据"""
        self.details = details


# 全局单例
execution_logger = ExecutionLogger()
