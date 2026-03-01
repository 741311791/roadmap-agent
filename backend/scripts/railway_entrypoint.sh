#!/bin/bash
# Railway 多服务启动脚本
#
# 根据 SERVICE_TYPE 环境变量决定启动哪个服务：
# - api:                   FastAPI 应用（默认），含数据库初始化
# - celery_worker:         主工作流 Worker（处理 celery 默认队列）
# - celery_content_worker: 内容生成 Worker（处理 content_generation 队列）
# - celery_beat:           Celery Beat 定时调度器
# - flower:                Celery Flower 监控界面

set -e

SERVICE_TYPE=${SERVICE_TYPE:-api}

echo "Starting service: $SERVICE_TYPE"

case $SERVICE_TYPE in
  api)
    echo "Starting FastAPI API server..."
    # 数据库初始化（只在 API 服务启动时执行一次）
    python scripts/create_tables.py
    alembic stamp head
    python scripts/create_admin_user.py \
      --email "${ADMIN_EMAIL:-admin@example.com}" \
      --password "${ADMIN_PASSWORD:-admin123}" \
      --username "${ADMIN_USERNAME:-admin}" || true

    # 启动 FastAPI 应用
    # UVICORN_WORKERS 默认 8（生产环境），研发可通过环境变量降为 2-4
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${UVICORN_WORKERS:-8}"
    ;;

  celery_worker)
    echo "Starting Celery Worker (queue: celery)..."
    # 等待 Redis / PostgreSQL 就绪
    sleep 5

    # 主工作流 Worker，处理以下任务：
    # - 路线图生成工作流（LangGraph 编排）
    # - 工作流断点恢复（人工审核后续流程）
    # - 执行日志批量写入
    # - 定时维护任务（Checkpoint 清理等）
    # - Tavily Key 缓存刷新
    #
    # 参数说明：
    # - queues=celery:           只消费 celery 默认队列（与内容生成队列隔离）
    # - concurrency:             默认 4，生产环境建议通过 CELERY_CONCURRENCY 设为 6-8
    # - max-tasks-per-child=500: 每 500 个任务重启子进程，防止内存泄漏
    exec celery -A app.core.celery_app worker \
      --loglevel="${CELERY_LOG_LEVEL:-info}" \
      --concurrency="${CELERY_CONCURRENCY:-4}" \
      --pool=prefork \
      --hostname=workflow@%h \
      --queues=celery \
      --max-tasks-per-child=500
    ;;

  celery_content_worker)
    echo "Starting Celery Content Generation Worker (queue: content_generation)..."
    # 等待 Redis / PostgreSQL 就绪
    sleep 5

    # 内容生成专用 Worker，处理以下任务：
    # - generate_all_content（批量生成教程、资源、测验）
    # - content.regenerate_single（单 Concept 重新生成）
    #
    # 参数说明：
    # - queues=content_generation: 只消费内容生成专用队列
    # - concurrency:               默认 4，内容生成 I/O 密集，适当提高并发
    # - max-tasks-per-child=100:   内容任务内存占用高，更频繁重启以避免 OOM
    exec celery -A app.core.celery_app worker \
      --loglevel="${CELERY_LOG_LEVEL:-info}" \
      --concurrency="${CELERY_CONTENT_CONCURRENCY:-4}" \
      --pool=prefork \
      --hostname=content@%h \
      --queues=content_generation \
      --max-tasks-per-child=100
    ;;

  celery_beat)
    echo "Starting Celery Beat scheduler..."
    # 等待 Redis 就绪
    sleep 5

    # 启动 Celery Beat 定时调度器
    # 负责触发以下周期性任务：
    # - 每天凌晨 3 点：清理旧 Checkpoint（maintenance.cleanup_old_checkpoints）
    # - 每小时整点：监控 Checkpoint 表大小（maintenance.monitor_checkpoint_size）
    # - 每 5 分钟：刷新 Tavily API Key 缓存（tavily_cache.refresh_keys）
    # - 每小时第 15 分钟：清理失效 Tavily Key（tavily_cache.cleanup_expired）
    #
    # 注意：生产环境只能运行一个 Beat 实例，不可水平扩展
    exec celery -A app.core.celery_app beat \
      --loglevel="${CELERY_LOG_LEVEL:-info}"
    ;;

  flower)
    echo "Starting Celery Flower monitoring dashboard..."
    # 等待 Redis 就绪
    sleep 5

    # 启动 Flower 监控界面（同时监控两个队列）
    exec celery -A app.core.celery_app flower \
      --port="${FLOWER_PORT:-5555}"
    ;;

  *)
    echo "Unknown SERVICE_TYPE: $SERVICE_TYPE"
    echo "Valid options: api, celery_worker, celery_content_worker, celery_beat, flower"
    exit 1
    ;;
esac

