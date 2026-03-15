#!/bin/bash
# Celery Content Generation Worker 启动脚本（开发环境）
#
# 使用场景：
# - 内容生成任务专用 Worker
# - 独立于主工作流 Worker
#
# 配置说明：
# - concurrency=3: 内容生成以 I/O 等待为主，本地开发保守并发足够
# - pool=threads: 本地开发优先保证 Celery inspect / control 可用，
#   避免 solo 模式下长任务阻塞监控与后台清理
# - queue=content_generation: 专用队列
# - max-tasks-per-child=100: 更频繁重启，避免内存泄漏
# - loglevel=info: 详细日志
#
# 启动方式：
# cd backend
# chmod +x scripts/start_content_worker_dev.sh
# ./scripts/start_content_worker_dev.sh

set -e

echo "=========================================="
echo "启动 Celery Content Generation Worker（开发环境）"
echo "=========================================="
echo ""
echo "配置："
echo "  - 并发数: 3（本地开发保守配置）"
echo "  - 队列: content_generation"
echo "  - 池类型: threads（便于监控与 inspect）"
echo "  - 日志级别: INFO"
echo "  - 进程刷新: 每 100 个任务"
echo ""
echo "按 Ctrl+C 停止 Worker"
echo "=========================================="
echo ""

# 切换到 backend 目录（如果不在的话）
cd "$(dirname "$0")/.."

# 启动 Celery Worker
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=3 \
    --pool=prefork \
    --hostname=content@%h \
    --max-tasks-per-child=100 \
    --queues=content_generation
