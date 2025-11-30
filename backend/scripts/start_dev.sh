#!/bin/bash
# 本地开发环境启动脚本

set -e  # 遇到错误立即退出

echo "🚀 启动个性化学习路线图生成系统后端..."
echo ""

# 检查包管理工具（优先 uv，其次 Poetry）
if command -v uv &> /dev/null; then
    PACKAGE_MANAGER="uv"
    echo "✅ 使用 uv 作为包管理工具"
elif command -v poetry &> /dev/null; then
    PACKAGE_MANAGER="poetry"
    echo "✅ 使用 Poetry 作为包管理工具"
else
    echo "❌ 未找到包管理工具（uv 或 Poetry），请先安装："
    echo "   安装 uv (推荐): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   或安装 Poetry: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请编辑并填入 API 密钥"
    echo ""
fi


# 启动开发服务器
echo ""
echo "🌟 启动开发服务器..."
echo "   访问 http://localhost:8000/api/docs 查看 API 文档"
echo "   按 Ctrl+C 停止服务器"
echo ""

if [ "$PACKAGE_MANAGER" = "uv" ]; then
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi

