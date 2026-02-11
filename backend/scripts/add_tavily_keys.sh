#!/bin/bash
# 批量添加 Tavily API Keys 脚本（Shell 版本）
#
# 使用方法:
#   1. 设置环境变量（推荐）:
#      export API_BASE_URL="http://localhost:8000"
#      export ADMIN_EMAIL="admin@example.com"
#      export ADMIN_PASSWORD="your_password"
#      ./scripts/add_tavily_keys.sh
#
#   2. 或直接修改下面的变量

# ========== 配置区域 ==========
# 如果环境变量未设置，使用下面的默认值
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
PLAN_LIMIT="${PLAN_LIMIT:-1000}"

# ========== 参数验证 ==========
if [ -z "$ADMIN_EMAIL" ]; then
    echo "错误: 缺少管理员邮箱"
    echo "请设置环境变量 ADMIN_EMAIL 或修改脚本中的 ADMIN_EMAIL 变量"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "错误: 缺少管理员密码"
    echo "请设置环境变量 ADMIN_PASSWORD 或修改脚本中的 ADMIN_PASSWORD 变量"
    exit 1
fi

# ========== 执行 Python 脚本 ==========
echo "=========================================="
echo "批量添加 Tavily API Keys"
echo "=========================================="
echo "API URL: $API_BASE_URL"
echo "管理员: $ADMIN_EMAIL"
echo "配额限制: $PLAN_LIMIT"
echo "=========================================="
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.." || exit 1

# 执行 Python 脚本
python scripts/batch_add_tavily_keys.py \
    --base-url "$API_BASE_URL" \
    --email "$ADMIN_EMAIL" \
    --password "$ADMIN_PASSWORD" \
    --plan-limit "$PLAN_LIMIT"

exit $?

