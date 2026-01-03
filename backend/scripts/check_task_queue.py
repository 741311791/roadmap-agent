#!/usr/bin/env python3
"""
检查 Celery 任务队列状态和最近的路线图任务
"""
import sys
import redis
from celery import Celery
from app.core.celery_app import celery_app


def main():
    """检查任务队列状态"""
    print("\n" + "=" * 100)
    print("Celery 任务队列状态检查")
    print("=" * 100)
    
    # 检查 Worker 状态
    print("\n📊 Active Workers:")
    print("-" * 100)
    
    inspect = celery_app.control.inspect()
    
    # 获取活跃的 Workers
    active_workers = inspect.active()
    if active_workers:
        for worker_name, tasks in active_workers.items():
            print(f"\n🔧 Worker: {worker_name}")
            if tasks:
                for task in tasks:
                    print(f"   ├─ Task ID: {task.get('id')}")
                    print(f"   ├─ Name: {task.get('name')}")
                    print(f"   ├─ Args: {task.get('args')}")
                    print(f"   └─ Started: {task.get('time_start')}")
            else:
                print("   └─ (空闲)")
    else:
        print("❌ 没有活跃的 Workers")
    
    # 检查预留任务（队列中等待的任务）
    print("\n\n⏳ Reserved Tasks (队列中等待的任务):")
    print("-" * 100)
    
    reserved = inspect.reserved()
    if reserved:
        for worker_name, tasks in reserved.items():
            print(f"\n🔧 Worker: {worker_name}")
            if tasks:
                for task in tasks:
                    print(f"   ├─ Task ID: {task.get('id')}")
                    print(f"   ├─ Name: {task.get('name')}")
                    print(f"   └─ Args: {task.get('args')}")
            else:
                print("   └─ (无等待任务)")
    else:
        print("✅ 没有等待的任务")
    
    # 检查 Worker 并发配置
    print("\n\n⚙️  Worker 配置:")
    print("-" * 100)
    
    stats = inspect.stats()
    if stats:
        for worker_name, stat in stats.items():
            pool = stat.get('pool', {})
            print(f"\n🔧 Worker: {worker_name}")
            print(f"   ├─ Max Concurrency: {pool.get('max-concurrency', 'N/A')}")
            print(f"   ├─ Processes: {pool.get('processes', 'N/A')}")
            print(f"   └─ Pool Type: {stat.get('pool', {}).get('implementation', 'N/A')}")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)

