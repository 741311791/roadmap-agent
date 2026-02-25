#!/usr/bin/env python3
"""
清空 Celery 队列中的所有待处理任务

用法：
    cd backend
    uv run python scripts/clear_celery_queue.py
"""
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.celery_app import celery_app
from app.config.settings import settings
import redis


def kill_celery_workers():
    """
    终止所有 Celery Worker 进程，解决僵尸 worker 抢占任务导致日志不显示的问题。
    """
    print("\n0️⃣ 终止所有 Celery Worker 进程...")
    try:
        result = subprocess.run(
            ["pkill", "-f", "celery.*worker"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("   ✅ 已终止所有 Celery Worker 进程")
        else:
            # pkill 返回 1 表示没有匹配的进程
            print("   ℹ️ 当前没有运行中的 Celery Worker")
    except FileNotFoundError:
        print("   ⚠️ pkill 命令不可用（非 Unix 系统）")
    except Exception as e:
        print(f"   ❌ 终止 Worker 失败: {e}")


def clear_celery_queue():
    """清空 Celery 队列"""
    print("🧹 清空 Celery 队列")
    print("=" * 70)

    # 步骤0: 先终止所有僵尸 worker，避免多进程竞争导致任务被看不见的进程抢走
    kill_celery_workers()

    # 方法1: 使用 Celery API 清空队列
    print("\n1️⃣ 使用 Celery API 清空队列...")
    try:
        # 获取所有队列名称
        active_queues = celery_app.control.inspect().active_queues()
        
        if active_queues:
            print(f"   发现活跃的 Worker: {len(active_queues)}")
            
            # 清空所有队列
            celery_app.control.purge()
            print(f"   ✅ 已清空所有队列")
        else:
            print(f"   ⚠️ 未发现活跃的 Worker")
    except Exception as e:
        print(f"   ❌ Celery API 清空失败: {e}")
    
    # 方法2: 直接清空 Redis 中的队列键
    print("\n2️⃣ 直接清空 Redis 队列键...")
    try:
        # 连接 Redis
        redis_url = settings.get_redis_url
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Celery 默认队列键模式
        queue_patterns = [
            "celery",           # 默认队列
            "celery:*",         # Celery 相关所有键
            "_kombu.binding.*", # Kombu 绑定
        ]
        
        deleted_count = 0
        for pattern in queue_patterns:
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                deleted_count += deleted
                print(f"   删除 {pattern}: {deleted} 个键")
        
        if deleted_count > 0:
            print(f"   ✅ 共删除 {deleted_count} 个 Redis 键")
        else:
            print(f"   ℹ️ Redis 中没有待处理的任务")
        
    except Exception as e:
        print(f"   ❌ Redis 清空失败: {e}")
    
    # 方法3: 终止所有正在运行的任务
    print("\n3️⃣ 终止所有正在运行的任务...")
    try:
        # 获取正在运行的任务
        active_tasks = celery_app.control.inspect().active()
        
        if active_tasks:
            total_tasks = sum(len(tasks) for tasks in active_tasks.values())
            print(f"   发现 {total_tasks} 个正在运行的任务")
            
            # 撤销所有任务
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    task_id = task['id']
                    celery_app.control.revoke(task_id, terminate=True)
                    print(f"   撤销任务: {task_id} (Worker: {worker})")
            
            print(f"   ✅ 已撤销所有正在运行的任务")
        else:
            print(f"   ℹ️ 没有正在运行的任务")
            
    except Exception as e:
        print(f"   ❌ 撤销任务失败: {e}")
    
    print("\n" + "=" * 70)
    print("✅ 清理完成")
    print("\n💡 提示:")
    print("   - 已终止所有 Worker，请重新启动: ./scripts/start_worker_dev.sh 和 ./scripts/start_content_worker_dev.sh")
    print("   - 如果要防止任务重新入队，考虑临时禁用 task_acks_late")


if __name__ == "__main__":
    clear_celery_queue()

