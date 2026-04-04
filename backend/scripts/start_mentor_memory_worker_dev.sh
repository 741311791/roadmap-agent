#!/bin/bash
# Celery AI 伴学助手长期记忆 Worker 启动脚本（开发环境）
#
# 使用场景：
# - 处理长期记忆提炼与 reflection 类重任务
# - 与 mentor_persist 分离，避免外部 LLM 延迟拖慢持久化链路
#
# 配置说明：
# - concurrency=1：长期记忆提炼依赖外部 LLM，本地开发单并发更稳妥
# - pool=threads：与现有开发脚本保持一致，便于 inspect / control
# - queue=mentor_memory：AI 伴学助手长期记忆专用队列
# - max-tasks-per-child=100：更频繁重启，减少长任务累计的资源问题
# - loglevel=info：输出详细日志，便于调试
#
# 启动方式：
# cd backend
# chmod +x scripts/start_mentor_memory_worker_dev.sh
# ./scripts/start_mentor_memory_worker_dev.sh

set -e

echo "=========================================="
echo "启动 Celery Mentor Memory Worker（开发环境）"
echo "=========================================="
echo ""
echo "配置："
echo "  - 并发数: 1"
echo "  - 队列: mentor_memory"
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
    --concurrency=1 \
    --pool=solo \
    --hostname=mentor-memory@%h \
    --max-tasks-per-child=100 \
    --queues=mentor_memory
