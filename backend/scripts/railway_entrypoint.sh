#!/bin/bash
# Railway 多服务启动脚本
#
# 根据 SERVICE_TYPE 环境变量决定启动哪个服务
# 支持的服务类型：
# - api: FastAPI 应用（默认）
# - celery_worker: Celery Worker 处理所有异步任务（统一队列）
# - flower: Celery Flower 监控界面
# - tavily_quota_updater: Tavily 配额更新定时任务

set -e

SERVICE_TYPE=${SERVICE_TYPE:-api}

echo "🚀 Starting service: $SERVICE_TYPE"

case $SERVICE_TYPE in
  api)
    echo "📡 Starting FastAPI API server..."
    # 运行数据库初始化（只在 API 服务中运行）
    python scripts/create_tables.py
    alembic stamp head
    python scripts/create_admin_user.py \
      --email ${ADMIN_EMAIL:-admin@example.com} \
      --password ${ADMIN_PASSWORD:-admin123} \
      --username ${ADMIN_USERNAME:-admin} || true
    
    # 启动 FastAPI 应用
    # 默认值为生产环境配置（阿里云数据库 280 连接）
    # 研发环境通过环境变量覆盖为 UVICORN_WORKERS=4
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port ${PORT:-8000} \
      --workers ${UVICORN_WORKERS:-8}
    ;;
    
  celery_worker)
    echo "⚡ Starting Celery Worker for all async tasks..."
    # 等待 Redis 和 PostgreSQL 就绪
    sleep 5
    
    # 启动 Celery Worker 处理所有异步任务（统一队列架构）
    # 处理任务类型：
    # - 执行日志批量写入
    # - 路线图生成工作流
    # - 内容生成（教程、资源、测验）
    # - 工作流恢复（人工审核后、断点恢复）
    # - 定时维护任务
    # 
    # 优化参数说明：
    # - prefetch_multiplier=1: 每次只预取 1 个任务，确保负载均衡
    # - max-tasks-per-child=500: 每 500 个任务重启进程，防止内存泄漏
    # - concurrency=4: 默认并发数（开发环境），生产环境建议 6-8
    # - time-limit=3600: 1 小时硬超时（适应长任务如路线图生成）
    # - soft-time-limit=3480: 58 分钟软超时（提前预警）
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --concurrency=${CELERY_CONCURRENCY:-4} \
      --pool=prefork \
      --hostname=worker@%h \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=500 \
      --time-limit=3600 \
      --soft-time-limit=3480
    ;;
    
  flower)
    echo "🌸 Starting Celery Flower monitoring dashboard..."
    # 等待 Redis 就绪
    sleep 5
    
    # 启动 Flower 监控界面
    # 监控 default 队列的所有任务
    exec celery -A app.core.celery_app flower \
      --port=${FLOWER_PORT:-5555} \
      --broker=${REDIS_URL:-redis://redis:6379/0}
    ;;
    
  tavily_quota_updater)
    echo "⏰ Starting Tavily Quota Updater..."
    # 等待 PostgreSQL 就绪
    sleep 5
    
    # 启动定时任务脚本
    exec python scripts/update_tavily_quota.py
    ;;
    
  *)
    echo "❌ Unknown SERVICE_TYPE: $SERVICE_TYPE"
    echo "Valid options: api, celery_worker, flower, tavily_quota_updater"
    exit 1
    ;;
esac

