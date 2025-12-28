#!/bin/bash
# Railway 多服务启动脚本
#
# 根据 SERVICE_TYPE 环境变量决定启动哪个服务
# 支持的服务类型：
# - api: FastAPI 应用（默认）
# - celery_logs: Celery Worker 处理日志队列
# - celery_content: Celery Worker 处理内容生成队列

set -e

SERVICE_TYPE=${SERVICE_TYPE:-api}

echo "🚀 Starting service: $SERVICE_TYPE"

case $SERVICE_TYPE in
  api)
    echo "📡 Starting FastAPI API server..."
    # 运行数据库初始化（只在 API 服务中运行）
    echo "🔧 Creating base tables..."
    python scripts/create_tables.py
    
    echo "🔍 Checking migration state..."
    # 检查并修复迁移状态（如果之前使用了 alembic stamp）
    python scripts/check_and_fix_migration.py || true
    
    echo "🔄 Running database migrations..."
    alembic upgrade head
    
    echo "👤 Creating admin user..."
    python scripts/create_admin_user.py \
      --email ${ADMIN_EMAIL:-admin@example.com} \
      --password ${ADMIN_PASSWORD:-admin123} \
      --username ${ADMIN_USERNAME:-admin} || true
    
    echo "✅ Database initialization complete!"
    
    # 启动 FastAPI 应用
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port ${PORT:-8000} \
      --workers ${UVICORN_WORKERS:-4}
    ;;
    
  celery_logs)
    echo "🔄 Starting Celery Worker for Logs Queue..."
    # 等待 Redis 和 PostgreSQL 就绪（可选，Railway 通常会自动等待）
    sleep 5
    
    # 启动 Celery Worker 处理日志队列
    # 使用 prefork pool（标准 Celery 支持），每个 worker 进程独立运行
    # 任务内部可以创建事件循环来执行异步数据库操作
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --queues=logs \
      --concurrency=${CELERY_LOGS_CONCURRENCY:-2} \
      --pool=prefork \
      --hostname=logs@%h \
      --max-tasks-per-child=1000
    ;;
    
  celery_content)
    echo "🎨 Starting Celery Worker for Content Generation Queue..."
    # 等待 Redis 和 PostgreSQL 就绪
    sleep 5
    
    # 启动 Celery Worker 处理内容生成队列
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --queues=content_generation \
      --concurrency=${CELERY_CONTENT_CONCURRENCY:-2} \
      --pool=prefork \
      --hostname=content@%h \
      --max-tasks-per-child=50
    ;;
    
  flower)
    echo "🌸 Starting Celery Flower monitoring dashboard..."
    # 等待 Redis 就绪
    sleep 5
    
    # 启动 Flower 监控界面
    exec celery -A app.core.celery_app flower \
      --port=${FLOWER_PORT:-5555} \
      --broker=${REDIS_URL:-redis://redis:6379/0}
    ;;
    
  *)
    echo "❌ Unknown SERVICE_TYPE: $SERVICE_TYPE"
    echo "Valid options: api, celery_logs, celery_content, flower"
    exit 1
    ;;
esac

