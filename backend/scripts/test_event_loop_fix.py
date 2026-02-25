"""
验证Event Loop修复

测试点：
1. run_async_in_worker_loop 函数是否正确工作
2. 验证在同一event loop中多次调用的安全性
3. 验证异常处理是否正确
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import asyncio
import threading
from app.tasks.event_loop_manager import (
    setup_event_loop,
    cleanup_event_loop,
    run_async_in_worker_loop,
    is_loop_initialized,
)


async def simple_async_task() -> str:
    """简单的异步任务"""
    await asyncio.sleep(0.1)
    return "success"


async def task_with_lock() -> str:
    """使用Lock的异步任务（模拟AsyncPostgresSaver）"""
    lock = asyncio.Lock()
    async with lock:
        await asyncio.sleep(0.1)
        return "locked_task_success"


async def task_that_raises() -> str:
    """抛出异常的任务"""
    await asyncio.sleep(0.1)
    raise ValueError("Test exception")


def test_event_loop_setup():
    """测试1: Event Loop初始化"""
    print("\n=== 测试1: Event Loop初始化 ===")
    
    # 初始化event loop
    setup_event_loop()
    
    # 验证初始化状态
    if is_loop_initialized():
        print("✅ Event Loop初始化成功")
        return True
    else:
        print("❌ Event Loop初始化失败")
        return False


def test_simple_task_execution():
    """测试2: 简单任务执行"""
    print("\n=== 测试2: 简单任务执行 ===")
    
    try:
        result = run_async_in_worker_loop(simple_async_task())
        print(f"✅ 任务执行结果: {result}")
        assert result == "success", "任务返回值不正确"
        print("✅ 通过: 简单任务正确执行")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_lock_usage():
    """测试3: Lock对象使用（核心测试）"""
    print("\n=== 测试3: Lock对象使用测试 ===")
    
    try:
        # 第一次调用
        result1 = run_async_in_worker_loop(task_with_lock())
        print(f"✅ 第一次调用成功: {result1}")
        
        # 第二次调用（复用同一个event loop）
        result2 = run_async_in_worker_loop(task_with_lock())
        print(f"✅ 第二次调用成功: {result2}")
        
        # 第三次调用（确保没有Lock残留问题）
        result3 = run_async_in_worker_loop(task_with_lock())
        print(f"✅ 第三次调用成功: {result3}")
        
        print("✅ 通过: Lock对象在持久event loop中正常工作")
        return True
    except RuntimeError as e:
        if "different event loop" in str(e):
            print(f"❌ 失败: Lock跨循环使用错误 - {e}")
        else:
            print(f"❌ 失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_exception_handling():
    """测试4: 异常处理"""
    print("\n=== 测试4: 异常处理测试 ===")
    
    try:
        result = run_async_in_worker_loop(task_that_raises())
        print(f"❌ 失败: 应该抛出异常但返回了 {result}")
        return False
    except ValueError as e:
        if "Test exception" in str(e):
            print(f"✅ 正确捕获异常: {e}")
            print("✅ 通过: 异常正确传播到调用方")
            return True
        else:
            print(f"❌ 失败: 异常类型不对 - {e}")
            return False
    except Exception as e:
        print(f"❌ 失败: 意外的异常类型 - {e}")
        return False


def test_concurrent_calls():
    """测试5: 并发调用测试"""
    print("\n=== 测试5: 并发调用测试 ===")
    
    try:
        import concurrent.futures
        
        # 模拟多个Celery任务同时执行（在不同线程中调用）
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(run_async_in_worker_loop, simple_async_task())
                for _ in range(5)
            ]
            
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        print(f"✅ 并发执行完成，结果: {results}")
        assert all(r == "success" for r in results), "部分任务失败"
        print("✅ 通过: 并发调用安全")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Event Loop 修复验证")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test1_passed = test_event_loop_setup()
        all_passed = all_passed and test1_passed
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        all_passed = False
    
    try:
        test2_passed = test_simple_task_execution()
        all_passed = all_passed and test2_passed
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        all_passed = False
    
    try:
        test3_passed = test_lock_usage()
        all_passed = all_passed and test3_passed
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        all_passed = False
    
    try:
        test4_passed = test_exception_handling()
        all_passed = all_passed and test4_passed
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        all_passed = False
    
    try:
        test5_passed = test_concurrent_calls()
        all_passed = all_passed and test5_passed
    except Exception as e:
        print(f"❌ 测试5失败: {e}")
        all_passed = False
    
    # 清理
    try:
        cleanup_event_loop()
        print("\n✅ Event Loop清理完成")
    except Exception as e:
        print(f"⚠️ Event Loop清理失败: {e}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！Event Loop问题已修复")
    else:
        print("❌ 部分测试失败，请检查修复")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
