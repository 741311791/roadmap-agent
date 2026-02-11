"""
Celery 任务通用工具函数

提供事件循环管理、错误处理等公共功能。
"""
import asyncio
import structlog

logger = structlog.get_logger()


def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    使用 asyncio.run() 确保每次执行都在干净的事件循环中进行，
    避免事件循环冲突和资源泄漏。
    
    asyncio.run() 会自动：
    1. 创建新的事件循环
    2. 设置为当前事件循环
    3. 运行协程
    4. 清理所有未完成的任务
    5. 关闭事件循环
    
    这是 Python 3.7+ 推荐的标准做法，避免手动管理事件循环。
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    """
    return asyncio.run(coro)

