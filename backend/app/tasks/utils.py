"""
Celery 任务通用工具函数（重构版 - 持久事件循环）

提供事件循环管理、错误处理等公共功能。

架构改进：
- 旧架构：每次任务使用 asyncio.run() 创建新的事件循环
- 新架构：使用 Worker 进程的持久事件循环
- 解决问题：避免 asyncio 原语（Lock、Event等）跨循环使用
"""
import structlog

logger = structlog.get_logger()


def run_async(coro):
    """
    在同步上下文中运行异步协程（重构版 - 持久事件循环 + 测试兼容）
    
    使用 Worker 进程的持久事件循环，而不是每次创建新循环。
    
    关键改进：
    - 旧实现：使用 asyncio.run() 每次创建新循环
    - 新实现：使用 run_async_in_worker_loop() 在持久循环中运行
    - 优势：
      1. 避免 asyncio 原语跨循环使用的问题
      2. 性能更好（不需要每次创建/销毁循环）
      3. 符合 asyncio 最佳实践
    
    测试兼容性：
    - 如果在非 Worker 环境（如测试、脚本）中调用，自动降级为 asyncio.run()
    - 在生产环境（Celery Worker）中强制使用持久循环
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    
    Raises:
        Exception: 协程执行过程中的任何异常
    
    注意：
        - 推荐在 Celery Worker 中调用（事件循环已初始化）
        - 在测试/脚本环境会自动降级，但会记录警告日志
    """
    from app.tasks.event_loop_manager import run_async_in_worker_loop, is_loop_initialized
    
    # 检查是否在 Celery Worker 环境中
    if is_loop_initialized():
        # 生产环境：使用持久事件循环
        return run_async_in_worker_loop(coro)
    else:
        # 测试/脚本环境：降级为 asyncio.run()
        import asyncio
        logger.warning(
            "run_async_fallback_to_asyncio_run",
            message="Worker事件循环未初始化，降级为 asyncio.run()（仅用于测试/脚本）",
            hint="在生产环境应该使用 Celery Worker",
        )
        return asyncio.run(coro)

