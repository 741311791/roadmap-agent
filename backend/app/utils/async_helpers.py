"""
异步辅助工具

提供异步迭代器合并等工具函数，用于并发流式处理。
"""
import asyncio
from typing import AsyncIterator, Any, TypeVar
import structlog

logger = structlog.get_logger()

T = TypeVar('T')

# 用于标记迭代器结束的 sentinel 对象
_ITERATOR_DONE = object()


async def merge_async_iterators(
    *iterators: AsyncIterator[T],
) -> AsyncIterator[T]:
    """
    合并多个异步迭代器，按完成顺序 yield 结果
    
    用于并发执行多个流式生成任务并合并输出。
    事件会按照实际产生的顺序交替输出。
    
    Args:
        *iterators: 要合并的异步迭代器列表
        
    Yields:
        来自各个迭代器的事件（按完成顺序）
        
    Example:
        ```python
        async def gen1():
            yield "a1"
            await asyncio.sleep(0.1)
            yield "a2"
        
        async def gen2():
            yield "b1"
            await asyncio.sleep(0.05)
            yield "b2"
        
        async for item in merge_async_iterators(gen1(), gen2()):
            print(item)  # 输出顺序可能是: a1, b1, b2, a2
        ```
    """
    if not iterators:
        return
    
    # 使用 asyncio.Queue 作为事件缓冲
    queue: asyncio.Queue[tuple[int, Any]] = asyncio.Queue()
    
    # 追踪已完成的迭代器数量
    done_count = 0
    total_count = len(iterators)
    
    async def consume_iterator(index: int, iterator: AsyncIterator[T]):
        """消费单个迭代器，将事件放入队列"""
        try:
            async for item in iterator:
                await queue.put((index, item))
        except Exception as e:
            logger.error(
                "merge_async_iterators_consumer_error",
                iterator_index=index,
                error=str(e),
            )
            # 将错误也放入队列，让调用者可以处理
            await queue.put((index, e))
        finally:
            # 标记此迭代器已完成
            await queue.put((index, _ITERATOR_DONE))
    
    # 创建消费者任务
    tasks = [
        asyncio.create_task(consume_iterator(i, iterator))
        for i, iterator in enumerate(iterators)
    ]
    
    try:
        # 从队列中读取事件直到所有迭代器完成
        while done_count < total_count:
            index, item = await queue.get()
            
            if item is _ITERATOR_DONE:
                done_count += 1
                logger.debug(
                    "merge_async_iterators_iterator_done",
                    iterator_index=index,
                    done_count=done_count,
                    total_count=total_count,
                )
            elif isinstance(item, Exception):
                # 可选：重新抛出异常或记录
                logger.warning(
                    "merge_async_iterators_item_error",
                    iterator_index=index,
                    error=str(item),
                )
                # 不重新抛出，继续处理其他迭代器
            else:
                yield item
    
    finally:
        # 确保所有任务都被清理
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


async def collect_async_iterator(
    iterator: AsyncIterator[T],
) -> list[T]:
    """
    收集异步迭代器的所有结果到列表
    
    Args:
        iterator: 异步迭代器
        
    Returns:
        包含所有结果的列表
    """
    results = []
    async for item in iterator:
        results.append(item)
    return results


async def first_completed(
    *iterators: AsyncIterator[T],
    timeout: float | None = None,
) -> T | None:
    """
    返回第一个产生结果的迭代器的第一个值
    
    Args:
        *iterators: 异步迭代器列表
        timeout: 超时时间（秒）
        
    Returns:
        第一个产生的值，或超时返回 None
    """
    if not iterators:
        return None
    
    queue: asyncio.Queue[T] = asyncio.Queue()
    
    async def consume(iterator: AsyncIterator[T]):
        try:
            async for item in iterator:
                await queue.put(item)
                return  # 只取第一个
        except Exception:
            pass
    
    tasks = [asyncio.create_task(consume(it)) for it in iterators]
    
    try:
        result = await asyncio.wait_for(queue.get(), timeout=timeout)
        return result
    except asyncio.TimeoutError:
        return None
    finally:
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class AsyncIteratorBuffer:
    """
    异步迭代器缓冲区
    
    用于在生产者和消费者之间提供缓冲，支持多生产者单消费者模式。
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Args:
            maxsize: 缓冲区最大大小，0 表示无限
        """
        self._queue: asyncio.Queue[T | None] = asyncio.Queue(maxsize=maxsize)
        self._closed = False
    
    async def put(self, item: T):
        """放入一个项目"""
        if self._closed:
            raise RuntimeError("Buffer is closed")
        await self._queue.put(item)
    
    async def close(self):
        """关闭缓冲区"""
        self._closed = True
        await self._queue.put(None)  # sentinel
    
    def __aiter__(self):
        return self
    
    async def __anext__(self) -> T:
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item

