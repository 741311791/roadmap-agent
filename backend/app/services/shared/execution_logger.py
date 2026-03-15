"""
执行日志服务（ExecutionLogger）

当前设计目标：
- `workflow` 分类日志作为任务阶段的权威落库数据；
- 阶段完成时支持“先同步写库，再发 WebSocket”；
- `agent/tool` 日志暂不落库，避免拖慢主流程并减少噪音。

说明：
- 为兼容现有调用方，`log()/info()/error()` 等 API 保持不变；
- 仅 `workflow` 分类日志会进入阶段缓冲区；
- 调用方可在阶段结束时显式触发 `flush_stage_logs()` 保证数据库先于前端事件可见。
"""
from collections import defaultdict
from typing import Optional
import time
import asyncio
from contextlib import asynccontextmanager
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.celery_session import get_celery_session
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
    执行日志服务

    设计原则：
    1. `workflow` 日志按 task_id + step 分阶段缓存；
    2. 阶段完成时由调用方显式同步落库；
    3. 非 `workflow` 日志暂不写数据库，仅保留返回对象兼容旧调用。
    """
    
    def __init__(self):
        # 按任务与阶段分桶，确保“某阶段完成时”能够精确提取并同步写库。
        self._stage_log_buffer: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self._flush_lock = asyncio.Lock()
    
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
        记录执行日志。

        当前仅 `workflow` 分类日志进入阶段缓冲区，等待后续显式落库；
        其他分类日志仅返回兼容对象，不会写入数据库。
        
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

        if category == LogCategory.WORKFLOW and step:
            async with self._flush_lock:
                self._stage_log_buffer[(task_id, step)].append(log_data)

        return ExecutionLog(**log_data)

    async def drain_stage_logs(
        self,
        task_id: str,
        step: str,
    ) -> list[dict]:
        """
        提取并清空指定阶段的缓冲日志。

        Args:
            task_id: 任务 ID
            step: 阶段名

        Returns:
            该阶段缓存的日志列表
        """
        async with self._flush_lock:
            return self._stage_log_buffer.pop((task_id, step), [])

    async def persist_logs(
        self,
        logs: list[dict],
        session: AsyncSession | None = None,
    ) -> int:
        """
        同步写入日志到数据库。

        Args:
            logs: 待写入日志列表
            session: 可选外部事务会话；若未提供则内部自建事务

        Returns:
            成功写入的日志数量
        """
        if not logs:
            return 0

        if session is not None:
            await self._persist_logs_to_session(session, logs)
            return len(logs)

        async with get_celery_session() as managed_session:
            await self._persist_logs_to_session(managed_session, logs)
            return len(logs)

    async def flush_stage_logs(
        self,
        task_id: str,
        step: str,
        session: AsyncSession | None = None,
    ) -> int:
        """
        将指定阶段的缓冲日志同步写入数据库。

        Args:
            task_id: 任务 ID
            step: 阶段名
            session: 可选外部事务会话

        Returns:
            成功写入的日志数量
        """
        logs = await self.drain_stage_logs(task_id, step)
        return await self.persist_logs(logs, session=session)

    async def flush(self):
        """
        同步刷新所有阶段缓冲日志。

        主要用于：
        - 工作流结束时兜底；
        - 应用关闭前确保已缓存的 workflow 日志全部入库。
        """
        async with self._flush_lock:
            all_logs: list[dict] = []
            for logs in self._stage_log_buffer.values():
                all_logs.extend(logs)
            self._stage_log_buffer.clear()

        if not all_logs:
            return

        await self.persist_logs(all_logs)

    async def _persist_logs_to_session(
        self,
        session: AsyncSession,
        logs: list[dict],
    ) -> None:
        """
        使用指定会话将日志写入数据库。

        Args:
            session: 数据库会话
            logs: 待写入日志列表
        """
        log_entries = [ExecutionLog(**log_data) for log_data in logs]
        session.add_all(log_entries)
        await session.flush()
    
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
