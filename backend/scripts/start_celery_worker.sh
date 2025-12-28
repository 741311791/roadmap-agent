#!/bin/bash
# Celery Worker 启动脚本
#
# 用途：启动 Celery Worker 处理异步日志队列
#
# 配置说明：
# - loglevel: info - 日志级别
# - queues: logs - 只处理 logs 队列
# - concurrency: 4 - 并发数（可根据负载调整）
# - pool: prefork - 使用进程池（默认，支持同步任务调用异步代码）
# - hostname: logs@%h - Worker 主机名
# - max-tasks-per-child: 500 - 每个子进程最多处理 500 个任务后重启（加快资源清理）
#
# 注意：
# - 使用 prefork pool（默认），每个 worker 进程独立运行
# - 每个 Worker 进程维护一个事件循环，不在任务结束时关闭
# - 通过定期重启子进程来清理事件循环和连接资源
# - max-tasks-per-child 从 1000 降低到 500，更积极地清理资源

celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=logs \
    --concurrency=4 \
    --pool=prefork \
    --hostname=logs@%h \
    --max-tasks-per-child=500

