#!/bin/bash
# Railway 多服务启动脚本
#
# 根据 SERVICE_TYPE 环境变量决定启动哪个服务
# 支持的服务类型：
# - api: FastAPI 应用（默认）
# - celery_logs: Celery Worker 处理日志队列
# - celery_content: Celery Worker 处理内容生成队列
# - celery_workflow: Celery Worker 处理路线图工作流队列
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
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port ${PORT:-8000} \
      --workers ${UVICORN_WORKERS:-4}
    ;;
    
  celery_logs)
    echo "📝 Starting Celery Worker for Logs Queue..."
    # 等待 Redis 和 PostgreSQL 就绪
    sleep 5
    
    # 启动 Celery Worker 处理日志队列
    # 特点：轻量级、快速、高并发
    # 优化参数：
    # - prefetch_multiplier=1: 避免预取，确保负载均衡
    # - max-tasks-per-child=1000: 高任务量后重启，防止内存泄漏
    # - concurrency=4: 日志任务轻量，可以高并发
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --queues=logs \
      --concurrency=${CELERY_LOGS_CONCURRENCY:-4} \
      --pool=prefork \
      --hostname=logs@%h \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=1000 \
      --time-limit=300 \
      --soft-time-limit=270
    ;;
    
  celery_content)
    echo "🎨 Starting Celery Worker for Content Generation Queue..."
    # 等待 Redis 和 PostgreSQL 就绪
    sleep 5
    
    # 启动 Celery Worker 处理内容生成队列
    # 特点：CPU 密集型、LLM 调用、并发生成多个 Concept
    # 优化参数：
    # - prefetch_multiplier=1: 避免预取，防止任务堆积
    # - max-tasks-per-child=50: 及时释放 LLM 客户端连接
    # - concurrency=6: 中等并发（每个任务内部已有 AsyncIO 并发）
    # - time-limit=1800: 30 分钟硬超时（内容生成可能较慢）
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --queues=content_generation \
      --concurrency=${CELERY_CONTENT_CONCURRENCY:-6} \
      --pool=prefork \
      --hostname=content@%h \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=50 \
      --time-limit=1800 \
      --soft-time-limit=1680
    ;;
    
  celery_workflow)
    echo "🔄 Starting Celery Worker for Roadmap Workflow Queue..."
    # 等待 Redis 和 PostgreSQL 就绪
    sleep 5
    
    # 启动 Celery Worker 处理路线图工作流队列
    # 处理任务：
    # - roadmap_generation.*: 完整路线图生成流程
    # - workflow_resume.*: 人工审核后恢复、断点恢复
    # 特点：长时间运行、状态机、LangGraph 协调
    # 优化参数：
    # - prefetch_multiplier=1: 避免预取，确保 checkpoint 隔离
    # - max-tasks-per-child=100: 定期重启，清理 LangGraph 状态
    # - concurrency=4: 中等并发（避免过多路线图同时生成）
    # - time-limit=3600: 1 小时硬超时（完整路线图生成）
    exec celery -A app.core.celery_app worker \
      --loglevel=${CELERY_LOG_LEVEL:-info} \
      --queues=roadmap_workflow \
      --concurrency=${CELERY_WORKFLOW_CONCURRENCY:-4} \
      --pool=prefork \
      --hostname=workflow@%h \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=100 \
      --time-limit=3600 \
      --soft-time-limit=3480
    ;;
    
  flower)
    echo "🌸 Starting Celery Flower monitoring dashboard..."
    # 等待 Redis 就绪
    sleep 5
    
    # 启动 Flower 监控界面
    # 监控所有队列：logs, content_generation, roadmap_workflow
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
    echo "Valid options: api, celery_logs, celery_content, celery_workflow, flower, tavily_quota_updater"
    exit 1
    ;;
esac

