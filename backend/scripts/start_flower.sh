#!/bin/bash
# Celery Flower 监控启动脚本
#
# 用途：启动 Flower 监控工具，用于查看 Celery 任务执行情况
#
# 访问地址：http://localhost:5555
#
# 功能：
# - 实时查看任务状态
# - 查看 Worker 状态和统计
# - 查看任务历史和详情
# - 重启 Worker

celery -A app.core.celery_app flower \
    --port=5555 \
    --broker=redis://localhost:6379/0

