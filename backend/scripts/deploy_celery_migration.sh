#!/bin/bash
# Celery 内容生成迁移部署脚本
# 用途: 在本地开发环境中启动所有服务，验证 Celery 迁移

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  Celery 内容生成迁移部署脚本"
echo "=========================================="
echo ""

# 1. 检查 Docker 是否运行
echo "[1/5] 检查 Docker 环境..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi
echo "✅ Docker 运行正常"
echo ""

# 2. 停止现有服务
echo "[2/5] 停止现有服务..."
cd "$(dirname "$0")/.."
docker-compose down
echo "✅ 已停止现有服务"
echo ""

# 3. 构建镜像
echo "[3/5] 构建 Docker 镜像..."
docker-compose build
echo "✅ 镜像构建完成"
echo ""

# 4. 启动所有服务
echo "[4/5] 启动所有服务..."
docker-compose up -d
echo "✅ 服务已启动"
echo ""

# 5. 等待服务就绪并验证
echo "[5/5] 验证服务状态..."
sleep 5

# 检查 API 服务
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ FastAPI 服务运行正常 (http://localhost:8000)"
else
    echo "⚠️  FastAPI 服务尚未就绪，请稍后检查"
fi

# 检查 Celery Worker（日志）
echo ""
echo "检查 Celery Worker 日志（内容生成）..."
docker-compose logs --tail=10 celery_content_worker

# 检查 Celery Worker（日志队列）
echo ""
echo "检查 Celery Worker 日志（日志队列）..."
docker-compose logs --tail=10 celery_worker

echo ""
echo "=========================================="
echo "  ✅ 部署完成"
echo "=========================================="
echo ""
echo "服务访问地址:"
echo "  - FastAPI API: http://localhost:8000"
echo "  - FastAPI Docs: http://localhost:8000/docs"
echo "  - Flower 监控: http://localhost:5555"
echo ""
echo "查看服务日志:"
echo "  docker-compose logs -f celery_content_worker"
echo ""
echo "停止所有服务:"
echo "  docker-compose down"
echo ""

