#!/bin/bash
# Celery AI 伴学助手持久化 Worker 启动脚本（开发环境）
#
# 使用场景：
# - 处理消息归档、STM 更新、会话元数据刷新
# - 独立于长期记忆提炼 Worker，避免轻任务被重任务阻塞
#
# 配置说明：
# - concurrency=2：轻任务允许适度并发，提升本地调试效率
# - pool=threads：与现有开发脚本保持一致，便于 inspect / control
# - queue=mentor_persist：AI 伴学助手持久化专用队列
# - max-tasks-per-child=300：定期重启子进程，降低长时间调试的资源漂移
# - loglevel=info：输出详细日志，便于排查问题
#
# 启动方式：
# cd backend
# chmod +x scripts/start_mentor_persist_worker_dev.sh
# ./scripts/start_mentor_persist_worker_dev.sh

set -e

echo "=========================================="
echo "启动 Celery Mentor Persist Worker（开发环境）"
echo "=========================================="
echo ""
echo "配置："
echo "  - 并发数: 2"
echo "  - 队列: mentor_persist"
echo "  - 池类型: threads（便于监控与 inspect）"
echo "  - 日志级别: INFO"
echo "  - 进程刷新: 每 300 个任务"
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
    --pool=solo \
    --hostname=mentor-persist@%h \
    --max-tasks-per-child=300 \
    --queues=mentor_persist
