#!/bin/bash
# Celery Worker 启动脚本（开发环境）
#
# 使用场景：
# - 本地开发和调试
# - 修复了 SIGSEGV 崩溃问题后的重启
#
# 配置说明：
# - concurrency=2: 降低并发，避免资源竞争和 API 限流
# - pool=threads: 本地开发优先保证 Celery inspect / control 可用，
#   避免 solo 模式下长任务阻塞监控与后台清理
# - max-tasks-per-child=500: 每 500 个任务重启进程，防止内存泄漏
# - loglevel=info: 输出详细日志，便于调试
#
# 启动方式：
# cd backend
# chmod +x scripts/start_worker_dev.sh
# ./scripts/start_worker_dev.sh

set -e

echo "=========================================="
echo "启动 Celery Worker（开发环境）"
echo "=========================================="
echo ""
echo "配置："
echo "  - 并发数: 2"
echo "  - 队列: celery（默认队列）"
echo "  - 池类型: threads（便于监控与 inspect）"
echo "  - 日志级别: INFO"
echo "  - 进程刷新: 每 500 个任务"
echo ""
echo "按 Ctrl+C 停止 Worker"
echo "=========================================="
echo ""

# 切换到 backend 目录（如果不在的话）
cd "$(dirname "$0")/.."

# 启动 Celery Worker
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=prefork \
    --hostname=workflow@%h \
    --max-tasks-per-child=500 \
    --queues=celery
