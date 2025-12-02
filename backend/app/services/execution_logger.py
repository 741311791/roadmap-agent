"""
执行日志服务 (ExecutionLogger)

提供结构化日志记录功能，用于：
- 通过 trace_id 追踪请求完整生命周期
- 聚合错误报告
- 性能分析和问题定位

使用示例：
    ```python
    from app.services.execution_logger import execution_logger

    # 记录工作流开始
    await execution_logger.log_workflow_start(
        trace_id="abc-123",
        step="intent_analysis",
        message="开始需求分析",
    )

    # 记录 Agent 执行
    await execution_logger.log_agent_execution(
        trace_id="abc-123",
        agent_name="IntentAnalyzer",
        message="需求分析完成",
        duration_ms=1500,
        details={"key_technologies": ["Python", "FastAPI"]},
    )

    # 记录错误
    await execution_logger.log_error(
        trace_id="abc-123",
        category="agent",
        message="教程生成失败",
        details={"error": str(e), "concept_id": "concept-1"},
    )
    ```
"""
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
import time
import structlog

from app.db.session import AsyncSessionLocal
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
    
    提供异步日志记录，支持：
    - 多级别日志 (debug, info, warning, error)
    - 多分类日志 (workflow, agent, tool, database)
    - 性能计时
    - 批量写入优化
    """
    
    def __init__(self):
        self._batch: list[ExecutionLog] = []
        self._batch_size = 10  # 批量写入阈值
    
    async def log(
        self,
        trace_id: str,
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
        写入执行日志
        
        Args:
            trace_id: 追踪 ID（对应 task_id）
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
            创建的日志记录
        """
        log_entry = ExecutionLog(
            trace_id=trace_id,
            level=level,
            category=category,
            message=message,
            step=step,
            agent_name=agent_name,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            details=details,
            duration_ms=duration_ms,
            created_at=beijing_now(),
        )
        
        # 写入数据库
        try:
            async with AsyncSessionLocal() as session:
                session.add(log_entry)
                await session.commit()
                await session.refresh(log_entry)
        except Exception as e:
            # 日志写入失败不应影响主流程
            logger.warning(
                "execution_log_write_failed",
                trace_id=trace_id,
                error=str(e),
            )
        
        return log_entry
    
    # ============================================================
    # 便捷方法：按日志级别
    # ============================================================
    
    async def debug(
        self,
        trace_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录调试日志"""
        return await self.log(trace_id, LogLevel.DEBUG, category, message, **kwargs)
    
    async def info(
        self,
        trace_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录信息日志"""
        return await self.log(trace_id, LogLevel.INFO, category, message, **kwargs)
    
    async def warning(
        self,
        trace_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录警告日志"""
        return await self.log(trace_id, LogLevel.WARNING, category, message, **kwargs)
    
    async def error(
        self,
        trace_id: str,
        category: str,
        message: str,
        **kwargs,
    ) -> ExecutionLog:
        """记录错误日志"""
        return await self.log(trace_id, LogLevel.ERROR, category, message, **kwargs)
    
    # ============================================================
    # 便捷方法：按使用场景
    # ============================================================
    
    async def log_workflow_start(
        self,
        trace_id: str,
        step: str,
        message: str,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录工作流步骤开始"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.WORKFLOW,
            message=message,
            step=step,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_workflow_complete(
        self,
        trace_id: str,
        step: str,
        message: str,
        duration_ms: Optional[int] = None,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录工作流步骤完成"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.WORKFLOW,
            message=message,
            step=step,
            duration_ms=duration_ms,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_agent_start(
        self,
        trace_id: str,
        agent_name: str,
        message: str,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录 Agent 开始执行"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            concept_id=concept_id,
            details=details,
        )
    
    async def log_agent_complete(
        self,
        trace_id: str,
        agent_name: str,
        message: str,
        duration_ms: Optional[int] = None,
        concept_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录 Agent 执行完成"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            duration_ms=duration_ms,
            concept_id=concept_id,
            details=details,
        )
    
    async def log_agent_error(
        self,
        trace_id: str,
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
            trace_id=trace_id,
            category=LogCategory.AGENT,
            message=message,
            agent_name=agent_name,
            concept_id=concept_id,
            details=error_details,
        )
    
    async def log_tool_call(
        self,
        trace_id: str,
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
            trace_id=trace_id,
            category=LogCategory.TOOL,
            message=message,
            agent_name=agent_name,
            duration_ms=duration_ms,
            details=tool_details,
        )
    
    async def log_retry_start(
        self,
        trace_id: str,
        message: str,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录重试开始"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.RETRY,
            message=message,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    async def log_retry_complete(
        self,
        trace_id: str,
        message: str,
        duration_ms: Optional[int] = None,
        roadmap_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ExecutionLog:
        """记录重试完成"""
        return await self.info(
            trace_id=trace_id,
            category=LogCategory.RETRY,
            message=message,
            duration_ms=duration_ms,
            roadmap_id=roadmap_id,
            details=details,
        )
    
    # ============================================================
    # 上下文管理器：自动计时
    # ============================================================
    
    @asynccontextmanager
    async def timed_operation(
        self,
        trace_id: str,
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
                trace_id="abc-123",
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
            trace_id=trace_id,
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
                trace_id=trace_id,
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
                trace_id=trace_id,
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

