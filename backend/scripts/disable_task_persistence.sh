#!/bin/bash
# 临时禁用 Celery 任务持久化
# 用于防止 Worker 重启时任务自动重新入队

echo "🔧 临时禁用 Celery 任务持久化"
echo "======================================================================"
echo ""
echo "修改配置文件: backend/app/core/celery_app.py"
echo ""
echo "将以下配置临时修改为:"
echo "  task_acks_late=False,              # ❌ 临时禁用"
echo "  task_reject_on_worker_lost=False,  # ❌ 临时禁用"
echo ""
echo "⚠️ 注意事项:"
echo "  1. 修改后需要重启 Celery Worker"
echo "  2. 此配置会导致任务丢失（不推荐生产环境）"
echo "  3. 测试完成后记得恢复原配置"
echo ""
echo "======================================================================"

