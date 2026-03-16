#!/bin/bash
# 多服务启动脚本
#
# 使用 SERVICE_ROLE 环境变量决定当前服务角色：
# - api_redis
# - workflow_worker
# - content_worker
# - celery_beat
# - flower
#
# 生产安全原则：
# 1. 数据库建表、迁移、管理员初始化均改为显式开关
# 2. Worker / Beat 启动参数优先读取环境变量
# 3. 统一使用 uv run，避免依赖外部虚拟环境激活

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"


log() {
  echo "[entrypoint] $*"
}


is_true() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}


require_env() {
  local env_name="$1"
  if [ -z "${!env_name:-}" ]; then
    log "缺少必填环境变量：${env_name}"
    exit 1
  fi
}


normalize_service_role() {
  local raw_service_role="${SERVICE_ROLE:-api_redis}"

  case "$raw_service_role" in
    api_redis)
      echo "api"
      ;;
    workflow_worker)
      echo "celery_worker"
      ;;
    content_worker)
      echo "celery_content_worker"
      ;;
    celery_beat)
      echo "celery_beat"
      ;;
    flower)
      echo "flower"
      ;;
    *)
      log "未知服务角色：${raw_service_role}"
      log "有效值：api_redis, workflow_worker, content_worker, celery_beat, flower"
      exit 1
      ;;
  esac
}


run_api_bootstrap() {
  # 说明：
  # - 全新数据库首次初始化：RUN_DB_CREATE_TABLES=true
  # - Alembic 正式迁移：RUN_DB_MIGRATIONS=true
  # - 初始化管理员：RUN_CREATE_ADMIN_USER=true，并显式提供 ADMIN_PASSWORD
  if is_true "${RUN_DB_CREATE_TABLES:-false}"; then
    log "执行数据库建表脚本"
    uv run python scripts/create_tables.py
  else
    log "跳过数据库建表脚本"
  fi

  if is_true "${RUN_DB_MIGRATIONS:-false}"; then
    log "执行 Alembic 迁移"
    uv run alembic upgrade head
  else
    log "跳过 Alembic 迁移"
  fi

  if is_true "${RUN_CREATE_ADMIN_USER:-false}"; then
    require_env ADMIN_PASSWORD

    log "执行管理员初始化脚本"
    uv run python scripts/create_admin_user.py \
      --email "${ADMIN_EMAIL:-${FEATURED_USER_EMAIL:-admin@example.com}}" \
      --password "${ADMIN_PASSWORD}" \
      --user-id "${FEATURED_USER_ID:-04005faa-fb45-47dd-a83c-969a25a77046}" \
      --username "${ADMIN_USERNAME:-admin}"
  else
    log "跳过管理员初始化脚本"
  fi
}


start_celery_worker() {
  local default_queue="$1"
  local default_hostname="$2"
  local default_concurrency="$3"
  local default_max_tasks_per_child="$4"

  local celery_log_level="${CELERY_LOG_LEVEL:-info}"
  local celery_pool="${CELERY_POOL:-prefork}"
  local celery_queue="${CELERY_QUEUE:-$default_queue}"
  local celery_hostname="${CELERY_HOSTNAME:-$default_hostname}"
  local celery_concurrency="${CELERY_CONCURRENCY:-$default_concurrency}"
  local celery_max_tasks_per_child="${CELERY_MAX_TASKS_PER_CHILD:-$default_max_tasks_per_child}"

  log "等待依赖服务就绪"
  sleep "${DEPENDENCY_WAIT_SECONDS:-5}"

  log "启动 Celery Worker"
  log "queue=${celery_queue} pool=${celery_pool} concurrency=${celery_concurrency} hostname=${celery_hostname}"

  exec uv run celery -A app.core.celery_app worker \
    --loglevel="${celery_log_level}" \
    --concurrency="${celery_concurrency}" \
    --pool="${celery_pool}" \
    --hostname="${celery_hostname}" \
    --queues="${celery_queue}" \
    --max-tasks-per-child="${celery_max_tasks_per_child}"
}


SERVICE_TYPE_NORMALIZED="$(normalize_service_role)"
log "启动服务：${SERVICE_TYPE_NORMALIZED}"

case "$SERVICE_TYPE_NORMALIZED" in
  api)
    log "启动 FastAPI API 服务"
    run_api_bootstrap

    exec uv run uvicorn app.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-${APP_PORT:-8000}}" \
      --workers "${UVICORN_WORKERS:-1}"
    ;;

  celery_worker)
    start_celery_worker "celery" "workflow@%h" "1" "500"
    ;;

  celery_content_worker)
    start_celery_worker "content_generation" "content@%h" "1" "100"
    ;;

  celery_beat)
    log "等待依赖服务就绪"
    sleep "${DEPENDENCY_WAIT_SECONDS:-5}"

    log "启动 Celery Beat 调度器"
    if [ -n "${CELERY_BEAT_SCHEDULE_FILE:-}" ]; then
      exec uv run celery -A app.core.celery_app beat \
        --loglevel="${CELERY_LOG_LEVEL:-info}" \
        --schedule="${CELERY_BEAT_SCHEDULE_FILE}"
    fi

    exec uv run celery -A app.core.celery_app beat \
      --loglevel="${CELERY_LOG_LEVEL:-info}"
    ;;

  flower)
    log "等待依赖服务就绪"
    sleep "${DEPENDENCY_WAIT_SECONDS:-5}"

    log "启动 Flower 监控面板"
    exec uv run celery -A app.core.celery_app flower \
      --port="${FLOWER_PORT:-5555}"
    ;;
esac

