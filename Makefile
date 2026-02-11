# Makefile for Roadmap Agent Project
# 提供统一的开发工作流命令

.PHONY: help install dev test sync check-sync clean

# 默认目标：显示帮助
help:
	@echo "╔════════════════════════════════════════════════╗"
	@echo "║   Roadmap Agent - Development Commands         ║"
	@echo "╚════════════════════════════════════════════════╝"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  make install      - 安装前后端依赖"
	@echo "  make dev          - 启动开发环境（前端+后端）"
	@echo "  make dev-backend  - 仅启动后端服务"
	@echo "  make dev-frontend - 仅启动前端服务"
	@echo "  make test         - 运行所有测试"
	@echo "  make sync         - 同步前后端 Schema"
	@echo "  make check-sync   - 检查前后端同步状态"
	@echo "  make clean        - 清理构建产物"
	@echo "  make db-migrate   - 运行数据库迁移"
	@echo "  make db-reset     - 重置数据库"
	@echo "  make db-clear     - 清空所有表数据（保留表结构）"
	@echo "  make test-assessment - 测试技术栈测验题异步初始化"
	@echo ""

# 安装依赖
install:
	@echo "📦 Installing dependencies..."
	@echo ""
	@echo "Installing backend dependencies..."
	cd backend && pip install uv && uv sync
	@echo ""
	@echo "Installing frontend dependencies..."
	cd frontend-next && npm install
	@echo ""
	@echo "✅ Dependencies installed successfully!"

# 启动完整开发环境
dev:
	@echo "🚀 Starting development environment..."
	@echo ""
	@echo "Starting backend server..."
	@cd backend && uvicorn app.main:app --reload --port 8000 &
	@sleep 3
	@echo ""
	@echo "Starting frontend server..."
	@cd frontend-next && npm run dev &
	@echo ""
	@echo "✅ Development environment is running!"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	@wait

# 仅启动后端
dev-backend:
	@echo "🚀 Starting backend server..."
	cd backend && uvicorn app.main:app --reload --port 8000

# 仅启动前端
dev-frontend:
	@echo "🚀 Starting frontend server..."
	cd frontend-next && npm run dev

# 运行测试
test:
	@echo "🧪 Running tests..."
	@echo ""
	@echo "Running backend tests..."
	cd backend && pytest
	@echo ""
	@echo "Running frontend tests..."
	cd frontend-next && npm run test:run
	@echo ""
	@echo "✅ All tests passed!"

# 同步前后端 Schema
sync:
	@echo "🔄 Syncing frontend-backend schema..."
	@./scripts/sync-frontend-backend.sh

# 检查同步状态
check-sync:
	@echo "🔍 Checking sync status..."
	@./scripts/sync-frontend-backend.sh --check

# 强制重新生成
sync-force:
	@echo "🔄 Force regenerating types..."
	@./scripts/sync-frontend-backend.sh --force

# 数据库迁移
db-migrate:
	@echo "🗄️  Running database migrations..."
	cd backend && alembic upgrade head
	@echo "✅ Migrations completed!"

# 重置数据库
db-reset:
	@echo "⚠️  Resetting database..."
	@read -p "Are you sure? This will delete all data [y/N]: " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && alembic downgrade base && alembic upgrade head; \
		echo "✅ Database reset completed!"; \
	else \
		echo "❌ Cancelled"; \
	fi

# 清空所有表数据（保留表结构）
db-clear:
	@echo "🗑️  Clearing all database tables..."
	@echo "⚠️  This will delete ALL data from ALL tables (including checkpoints)"
	@cd backend && python3 scripts/clear_all_tables.py

# 清理构建产物
clean:
	@echo "🧹 Cleaning build artifacts..."
	@echo ""
	@echo "Cleaning backend..."
	@find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find backend -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo ""
	@echo "Cleaning frontend..."
	@cd frontend-next && rm -rf .next node_modules/.cache
	@echo ""
	@echo "✅ Clean completed!"

# 查看 OpenAPI 文档
docs:
	@echo "📚 Opening API documentation..."
	@open http://localhost:8000/docs

# 查看日志
logs-backend:
	@echo "📋 Viewing backend logs..."
	@tail -f backend/logs/*.log

# 生成类型
generate-types:
	@echo "🔨 Generating TypeScript types..."
	cd frontend-next && npm run generate:types

# 类型检查
type-check:
	@echo "🔍 Checking types..."
	@echo ""
	@echo "Checking backend types..."
	cd backend && mypy app
	@echo ""
	@echo "Checking frontend types..."
	cd frontend-next && npm run type-check
	@echo ""
	@echo "✅ Type checking passed!"

# 代码格式化
format:
	@echo "💅 Formatting code..."
	@echo ""
	@echo "Formatting backend..."
	cd backend && black app tests
	@echo ""
	@echo "Formatting frontend..."
	cd frontend-next && npx prettier --write .
	@echo ""
	@echo "✅ Formatting completed!"

# Lint 检查
lint:
	@echo "🔍 Running linters..."
	@echo ""
	@echo "Linting backend..."
	cd backend && ruff check app
	@echo ""
	@echo "Linting frontend..."
	cd frontend-next && npm run lint
	@echo ""
	@echo "✅ Linting passed!"

# 查看系统状态
status:
	@echo "📊 System Status"
	@echo "════════════════════════════════════════════════"
	@echo ""
	@echo "Backend Status:"
	@curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "❌ Backend not running"
	@echo ""
	@echo "Frontend Status:"
	@curl -s http://localhost:3000 > /dev/null 2>&1 && echo "✅ Frontend running" || echo "❌ Frontend not running"
	@echo ""
	@echo "Database Status:"
	@cd backend && python -c "from app.db.session import check_db_health; import asyncio; print(asyncio.run(check_db_health()))" 2>/dev/null || echo "❌ Database not accessible"
	@echo ""

# ============================================================
# 测试技术栈测验题异步初始化
# ============================================================
test-assessment:
	@echo "🧪 Testing Assessment Initialization (Async)"
	@echo "════════════════════════════════════════════════"
	@echo ""
	@echo "⚠️  确保以下服务已启动："
	@echo "   1. 后端服务：make run"
	@echo "   2. Celery Worker：make celery"
	@echo ""
	@read -p "按 Enter 键继续测试..." dummy
	@echo ""
	@cd backend && python3 scripts/test_assessment_initialization.py --mode=progress

test-assessment-full:
	@echo "🧪 Testing Assessment Initialization (Full Test - Clear & Generate)"
	@echo "════════════════════════════════════════════════"
	@echo ""
	@echo "⚠️  警告：此测试将清空所有技术栈测验题数据！"
	@echo "⚠️  确保以下服务已启动："
	@echo "   1. 后端服务：make run"
	@echo "   2. Celery Worker：make celery"
	@echo ""
	@read -p "确认继续？[y/N]: " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && python3 scripts/test_assessment_initialization.py --mode=full; \
	else \
		echo "❌ 测试取消"; \
	fi

