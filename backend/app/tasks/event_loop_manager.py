"""
Celery Worker 事件循环管理器

解决问题：
- 问题：每次 Celery 任务使用 asyncio.run() 创建新事件循环，导致 AsyncPostgresSaver 的 Lock 对象跨循环使用失败
- 方案：在 Worker 进程启动时创建单一持久的事件循环，整个 Worker 生命周期内复用

架构优势：
- 符合 asyncio 最佳实践（长期运行的应用应该只有一个事件循环）
- 避免 asyncio 原语（Lock、Event等）跨循环使用的问题
- 保持 OrchestratorFactory 单例架构的同时，确保线程安全

使用场景：
- 在 Celery Worker 启动时调用 setup_event_loop()
- 在 Celery Worker 关闭时调用 cleanup_event_loop()
- 在任务执行时使用 run_async_in_worker_loop() 替代 asyncio.run()
"""
import asyncio
import threading
import structlog
from typing import Coroutine, TypeVar, Any

logger = structlog.get_logger()

T = TypeVar('T')

# ====================================================================
# 全局事件循环管理
# ====================================================================

# Worker 进程的全局事件循环（每个进程一个）
_worker_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_loop_ready = threading.Event()


def setup_event_loop() -> None:
    """
    在 Celery Worker 启动时创建持久的事件循环
    
    应该在 Celery Worker 的 worker_process_init signal 中调用。
    创建一个后台线程来运行事件循环，确保它在整个 Worker 生命周期内保持活跃。
    
    注意：
        - 每个 Worker 进程只能调用一次
        - 线程安全：使用 threading.Event 同步循环就绪状态
    """
    global _worker_loop, _loop_thread, _loop_ready
    
    if _worker_loop is not None:
        logger.warning(
            "event_loop_already_setup",
            message="Worker事件循环已存在，跳过初始化",
        )
        return
    
    def run_loop():
        """后台线程：运行事件循环"""
        global _worker_loop
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _worker_loop = loop
        
        logger.info(
            "worker_event_loop_created",
            loop_id=id(loop),
            thread_id=threading.get_ident(),
        )
        
        # 通知主线程循环已就绪
        _loop_ready.set()
        
        # 运行事件循环直到被停止
        try:
            loop.run_forever()
        finally:
            # 清理未完成的任务
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.info(
                    "cancelling_pending_tasks",
                    count=len(pending),
                )
                for task in pending:
                    task.cancel()
                
                # 等待所有任务取消完成
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            logger.info("worker_event_loop_closed")
    
    # 启动后台线程
    _loop_thread = threading.Thread(target=run_loop, daemon=True, name="CeleryEventLoop")
    _loop_thread.start()
    
    # 等待循环就绪（超时5秒）
    if not _loop_ready.wait(timeout=5):
        raise RuntimeError("事件循环初始化超时")
    
    logger.info(
        "worker_event_loop_setup_complete",
        loop_thread_id=_loop_thread.ident,
    )


def cleanup_event_loop() -> None:
    """
    在 Celery Worker 关闭时清理事件循环
    
    应该在 Celery Worker 的 worker_process_shutdown signal 中调用。
    停止事件循环并等待后台线程结束。
    """
    global _worker_loop, _loop_thread, _loop_ready
    
    if _worker_loop is None:
        logger.debug("event_loop_not_initialized")
        return
    
    logger.info("stopping_worker_event_loop")
    
    # 停止事件循环
    _worker_loop.call_soon_threadsafe(_worker_loop.stop)
    
    # 等待线程结束（超时10秒）
    if _loop_thread and _loop_thread.is_alive():
        _loop_thread.join(timeout=10)
        if _loop_thread.is_alive():
            logger.warning("event_loop_thread_did_not_stop")
    
    # 重置全局变量
    _worker_loop = None
    _loop_thread = None
    _loop_ready.clear()
    
    logger.info("worker_event_loop_cleanup_complete")


def run_async_in_worker_loop(coro: Coroutine[Any, Any, T]) -> T:
    """
    在 Worker 的持久事件循环中运行异步协程（替代 asyncio.run）
    
    使用场景：
        - 在 Celery 任务中执行异步代码
        - 替代原来的 asyncio.run(coro)
    
    Args:
        coro: 要执行的异步协程
    
    Returns:
        协程的返回值
    
    Raises:
        RuntimeError: 如果事件循环未初始化
        Exception: 协程执行过程中的任何异常
    
    注意：
        - 线程安全：使用 asyncio.run_coroutine_threadsafe
        - 会阻塞调用线程直到协程完成
    """
    global _worker_loop
    
    if _worker_loop is None:
        raise RuntimeError(
            "Worker事件循环未初始化。"
            "请确保在 Celery Worker 启动时调用了 setup_event_loop()。"
        )
    
    if not _worker_loop.is_running():
        raise RuntimeError("Worker事件循环未运行")
    
    # 使用 run_coroutine_threadsafe 在事件循环线程中执行协程
    # 返回一个 concurrent.futures.Future 对象
    future = asyncio.run_coroutine_threadsafe(coro, _worker_loop)
    
    try:
        # 阻塞等待结果（无超时，让Celery的time_limit处理）
        result = future.result()
        return result
    except Exception as e:
        # 记录异常但不吞掉（让上层处理）
        logger.error(
            "async_task_failed_in_worker_loop",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


def get_worker_loop() -> asyncio.AbstractEventLoop | None:
    """
    获取当前 Worker 的事件循环（仅供调试）
    
    Returns:
        事件循环对象，如果未初始化则返回 None
    """
    return _worker_loop


def is_loop_initialized() -> bool:
    """
    检查 Worker 事件循环是否已初始化
    
    Returns:
        True 如果循环已初始化且正在运行
    """
    return _worker_loop is not None and _worker_loop.is_running()
