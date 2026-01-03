#!/usr/bin/env python3
"""
诊断任务阻塞问题的脚本

从第一性原理分析：
1. 任务是否真的被提交到队列？
2. Worker 是否真的在处理任务？
3. 是否有任务卡在某个状态？
"""
import redis
import json
from app.core.celery_app import celery_app
from app.config.settings import settings


def main():
    print("\n" + "=" * 100)
    print("任务阻塞诊断报告")
    print("=" * 100)
    
    # 1. 检查 Redis 队列中的任务数量
    print("\n📦 Step 1: 检查 Redis 队列")
    print("-" * 100)
    
    r = redis.from_url(settings.REDIS_URL)
    
    queues = ['roadmap_workflow', 'content_generation', 'logs']
    for queue_name in queues:
        queue_key = f"celery:{queue_name}"  # Celery 默认队列前缀
        queue_length = r.llen(queue_key)
        print(f"   {queue_name:25} : {queue_length} 个任务在队列中")
        
        # 如果有任务，显示前 3 个
        if queue_length > 0:
            tasks = r.lrange(queue_key, 0, 2)
            for i, task_data in enumerate(tasks, 1):
                try:
                    task = json.loads(task_data)
                    headers = task.get('headers', {})
                    print(f"      └─ Task {i}: {headers.get('task', 'unknown')}")
                    print(f"         ID: {headers.get('id', 'unknown')}")
                except:
                    print(f"      └─ Task {i}: (无法解析)")
    
    # 2. 检查 Worker 状态
    print("\n\n⚙️  Step 2: 检查 Worker 状态")
    print("-" * 100)
    
    inspect = celery_app.control.inspect()
    
    # 2.1 活跃任务
    active_tasks = inspect.active()
    if active_tasks:
        for worker_name, tasks in active_tasks.items():
            if 'workflow@' in worker_name:
                print(f"\n   Worker: {worker_name}")
                if tasks:
                    print(f"   ├─ 正在执行 {len(tasks)} 个任务:")
                    for task in tasks:
                        print(f"   │  ├─ Task ID: {task.get('id')}")
                        print(f"   │  ├─ Name: {task.get('name')}")
                        print(f"   │  └─ Started: {task.get('time_start')}")
                else:
                    print(f"   └─ 空闲")
    
    # 2.2 预留任务
    reserved_tasks = inspect.reserved()
    if reserved_tasks:
        for worker_name, tasks in reserved_tasks.items():
            if 'workflow@' in worker_name:
                print(f"\n   Worker: {worker_name}")
                if tasks:
                    print(f"   ├─ 预留了 {len(tasks)} 个任务（即将执行）:")
                    for task in tasks:
                        print(f"   │  ├─ Task ID: {task.get('id')}")
                        print(f"   │  └─ Name: {task.get('name')}")
                else:
                    print(f"   └─ 无预留任务")
    
    # 2.3 Worker 配置
    stats = inspect.stats()
    if stats:
        for worker_name, stat in stats.items():
            if 'workflow@' in worker_name:
                pool = stat.get('pool', {})
                print(f"\n   Worker: {worker_name}")
                print(f"   ├─ Max Concurrency: {pool.get('max-concurrency', 'N/A')}")
                print(f"   ├─ Prefetch Multiplier: {stat.get('prefetch_count', 'N/A')}")
                print(f"   └─ Total Tasks: {stat.get('total', {})}")
    
    # 3. 检查数据库中的任务状态
    print("\n\n💾 Step 3: 检查数据库中的任务状态")
    print("-" * 100)
    print("   (需要异步查询，请运行独立脚本)")
    
    # 4. 诊断结论
    print("\n\n🔍 Step 4: 诊断结论")
    print("-" * 100)
    
    # 检查是否有任务堆积
    workflow_queue_length = r.llen("celery:roadmap_workflow")
    
    if workflow_queue_length > 0:
        print("   ⚠️  发现问题：Redis 队列中有任务堆积")
        print(f"      - 队列中有 {workflow_queue_length} 个任务")
        print("      - 可能原因：")
        print("        1. Worker 并发数不足")
        print("        2. Worker 进程崩溃或未启动")
        print("        3. 任务执行时间过长")
    else:
        print("   ✅ Redis 队列为空")
    
    # 检查 Worker 是否有活跃任务
    has_active = False
    if active_tasks:
        for worker_name, tasks in active_tasks.items():
            if 'workflow@' in worker_name and tasks:
                has_active = True
                print(f"   ✅ Worker 正在处理 {len(tasks)} 个任务")
    
    if not has_active and workflow_queue_length == 0:
        print("   ℹ️  当前没有任务在执行，也没有任务在队列中")
        print("      - 这可能意味着所有任务都已完成")
        print("      - 或者任务状态卡在数据库层面（status=pending 但未提交到 Celery）")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

