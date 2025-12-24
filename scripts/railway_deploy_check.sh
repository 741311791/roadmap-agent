#!/bin/bash

# ==================== Railway 部署检查脚本 ====================
# 用途: 在部署到 Railway 前检查必要文件是否存在
# 使用方法: cd roadmap-agent && bash scripts/railway_deploy_check.sh

set -e

echo "🚀 Railway 部署前置检查..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查项计数
PASSED=0
FAILED=0

# 检查函数
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2 - 文件不存在: $1"
        ((FAILED++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2 - 目录不存在: $1"
        ((FAILED++))
    fi
}

check_dockerfile_content() {
    if grep -q "alembic upgrade head" "$1"; then
        echo -e "${GREEN}✓${NC} Dockerfile 包含数据库迁移命令"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Dockerfile 缺少数据库迁移命令"
        echo "   建议在 CMD 中添加: alembic upgrade head"
        ((FAILED++))
    fi
    
    if grep -q "\${PORT" "$1"; then
        echo -e "${GREEN}✓${NC} Dockerfile 使用动态端口配置"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Dockerfile 可能使用硬编码端口"
        echo "   建议修改为: --port \${PORT:-8000}"
        ((FAILED++))
    fi
}

echo "📦 检查后端项目结构..."
check_file "backend/Dockerfile" "Dockerfile 存在"
check_file "backend/pyproject.toml" "pyproject.toml 存在"
check_file "backend/alembic.ini" "alembic.ini 存在"
check_dir "backend/alembic" "alembic/ 目录存在"
check_dir "backend/app" "app/ 目录存在"
check_dir "backend/prompts" "prompts/ 目录存在"

echo ""
echo "🔍 检查 Dockerfile 配置..."
check_dockerfile_content "backend/Dockerfile"

echo ""
echo "📝 检查必要的 Python 依赖..."
if grep -q "alembic" "backend/pyproject.toml"; then
    echo -e "${GREEN}✓${NC} pyproject.toml 包含 alembic 依赖"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} pyproject.toml 缺少 alembic 依赖"
    ((FAILED++))
fi

if grep -q "asyncpg" "backend/pyproject.toml"; then
    echo -e "${GREEN}✓${NC} pyproject.toml 包含 asyncpg 依赖"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} pyproject.toml 缺少 asyncpg 依赖"
    ((FAILED++))
fi

if grep -q "redis" "backend/pyproject.toml"; then
    echo -e "${GREEN}✓${NC} pyproject.toml 包含 redis 依赖"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} pyproject.toml 缺少 redis 依赖"
    ((FAILED++))
fi

echo ""
echo "📄 检查部署文档..."
check_file "RAILWAY_DEPLOYMENT_GUIDE.md" "Railway 部署指南存在"
check_file "RAILWAY_ENV_TEMPLATE.txt" "环境变量模板存在"

echo ""
echo "================================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查项通过! ($PASSED/$((PASSED+FAILED)))${NC}"
    echo ""
    echo "下一步操作："
    echo "1. 提交并推送代码到 GitHub:"
    echo "   git add ."
    echo "   git commit -m 'chore: prepare for Railway deployment'"
    echo "   git push"
    echo ""
    echo "2. 登录 Railway Dashboard 并按照 RAILWAY_DEPLOYMENT_GUIDE.md 操作"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 检查失败! ($PASSED/$((PASSED+FAILED)) 通过)${NC}"
    echo ""
    echo "请修复以上问题后再部署到 Railway。"
    echo ""
    exit 1
fi

