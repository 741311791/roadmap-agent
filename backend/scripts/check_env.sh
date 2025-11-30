#!/bin/bash
# 环境检查脚本

echo "🔍 检查本地开发环境..."
echo ""

# 检查 Python 版本
echo "1. 检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
    echo "   ✅ Python $PYTHON_VERSION (需要 3.12+)"
else
    echo "   ❌ Python $PYTHON_VERSION (需要 3.12+)"
    exit 1
fi

# 检查包管理工具（优先 uv，其次 Poetry）
echo ""
echo "2. 检查包管理工具..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | awk '{print $2}')
    echo "   ✅ uv $UV_VERSION (推荐)"
    PACKAGE_MANAGER="uv"
elif command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version | awk '{print $3}')
    echo "   ✅ Poetry $POETRY_VERSION"
    PACKAGE_MANAGER="poetry"
else
    echo "   ❌ 未找到包管理工具（uv 或 Poetry）"
    echo "   安装 uv (推荐): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   或安装 Poetry: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# 检查 .env 文件
echo ""
echo "3. 检查环境变量文件..."
if [ -f .env ]; then
    echo "   ✅ .env 文件存在"
    
    # 检查关键环境变量
    if grep -q "ANALYZER_API_KEY=your_" .env 2>/dev/null || grep -q "ANALYZER_API_KEY=sk-xxx" .env 2>/dev/null; then
        echo "   ⚠️  请更新 .env 文件中的 API 密钥（ANALYZER_API_KEY 仍为占位符）"
    fi
    
    if grep -q "TAVILY_API_KEY=your_" .env 2>/dev/null || grep -q "TAVILY_API_KEY=your_tavily" .env 2>/dev/null; then
        echo "   ⚠️  请更新 .env 文件中的 Tavily API 密钥"
    fi
else
    echo "   ⚠️  .env 文件不存在，将从 .env.example 复制"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "   ✅ 已创建 .env 文件"
    else
        echo "   ❌ .env.example 文件不存在"
        exit 1
    fi
fi

# 检查依赖是否安装
echo ""
echo "4. 检查项目依赖..."
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    if [ -d ".venv" ]; then
        echo "   ✅ uv 虚拟环境已创建"
        # 检查关键依赖
        if uv pip show fastapi &> /dev/null; then
            echo "   ✅ 项目依赖已安装"
        else
            echo "   ⚠️  项目依赖未安装，运行: uv sync --all-extras"
        fi
    else
        echo "   ⚠️  uv 虚拟环境未创建，运行: uv sync --all-extras"
    fi
else
    if [ -d ".venv" ] || poetry env info &> /dev/null; then
        echo "   ✅ Poetry 虚拟环境已创建"
        # 检查关键依赖
        if poetry show fastapi &> /dev/null; then
            echo "   ✅ 项目依赖已安装"
        else
            echo "   ⚠️  项目依赖未安装，运行: poetry install"
        fi
    else
        echo "   ⚠️  Poetry 虚拟环境未创建，运行: poetry install"
    fi
fi

# 检查数据库服务
echo ""
echo "7. 检查数据库服务..."
if docker-compose ps postgres | grep -q "Up"; then
    echo "   ✅ PostgreSQL 正在运行"
else
    echo "   ⚠️  PostgreSQL 未运行，运行: docker-compose up -d postgres"
fi

if docker-compose ps redis | grep -q "Up"; then
    echo "   ✅ Redis 正在运行"
else
    echo "   ⚠️  Redis 未运行，运行: docker-compose up -d redis"
fi

echo ""
echo "✅ 环境检查完成！"
echo ""
echo "下一步："
echo "  1. 编辑 .env 文件，填入 API 密钥"
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    echo "  2. 运行: uv sync --all-extras (如果依赖未安装)"
else
    echo "  2. 运行: poetry install (如果依赖未安装)"
fi
echo "  3. 运行: ./scripts/start_dev.sh 启动开发服务器"

