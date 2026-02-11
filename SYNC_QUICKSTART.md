# Frontend-Backend Schema Sync - Quick Start Guide

> 前后端 Schema 自动同步 - 5 分钟上手指南

---

## 🚀 快速开始

### 1. 首次设置

```bash
# 1. 安装依赖
make install

# 2. 启动后端服务
cd backend
uvicorn app.main:app --reload

# 3. 在新终端，生成前端类型
cd frontend-next
npm run generate:types
```

---

## 📋 常用命令

### 方式一：使用 Make (推荐)

```bash
make sync           # 完整同步前后端 Schema
make check-sync     # 检查是否需要同步
make sync-force     # 强制重新生成类型
make status         # 查看系统状态
```

### 方式二：使用 npm scripts

```bash
cd frontend-next

npm run generate:types     # 生成类型
npm run check:schema-sync  # 检查同步状态
npm run sync:backend       # 完整同步
npm run type-check         # 验证类型
```

### 方式三：直接运行脚本

```bash
./scripts/sync-frontend-backend.sh          # 完整同步
./scripts/sync-frontend-backend.sh --check  # 仅检查
./scripts/sync-frontend-backend.sh --force  # 强制重新生成
```

---

## 🔄 典型工作流

### 场景 1: 我修改了后端 Schema

```bash
# 1. 修改 Pydantic Model
vim backend/app/schemas/roadmap.py

# 2. 同步前端类型
make sync

# 3. 提交代码（Pre-commit hook 自动验证）
git add .
git commit -m "feat: 新增路线图精选功能"
```

### 场景 2: 我拉取了最新代码

```bash
# 1. 拉取代码
git pull origin develop

# 2. 检查同步状态
make check-sync

# 3. 如果提示不同步，运行同步
make sync
```

### 场景 3: 后端不可用时

```bash
# 生成脚本会自动降级到占位符类型
npm run generate:types

# 输出: ✅ Placeholder types generated successfully!
```

---

## ✅ 验证同步状态

```bash
# 方法 1: Make 命令
make check-sync

# 方法 2: npm 命令
cd frontend-next
npm run check:schema-sync

# 输出示例（同步状态）:
# ✅ Frontend types are in sync with backend!
#
# 📊 Generation stats:
#    - Last generated: 2026-01-11 10:30:00
#    - Models: 45
#    - Services: 8
#    - Endpoints: 67
```

---

## 🛠️ 故障排查

### 问题: 后端服务未运行

```
❌ 后端服务未运行: http://localhost:8000
```

**解决**:
```bash
cd backend
uvicorn app.main:app --reload
```

### 问题: 类型不同步

```
❌ Frontend types are OUT OF SYNC with backend!
```

**解决**:
```bash
make sync
# 或
npm run sync:backend
```

### 问题: Pre-commit 失败

```
❌ Frontend types are out of sync!
```

**解决**:
```bash
# 1. 同步类型
make sync

# 2. 添加生成的文件
git add frontend-next/types/generated/

# 3. 重新提交
git commit
```

---

## 📊 查看变更报告

同步后会生成详细的变更报告：

```bash
cat frontend-next/.sync-report.md
```

报告内容示例：

```markdown
# Frontend-Backend Sync Report

## 🆕 新增 API 端点
- POST /api/v1/roadmaps/featured
- GET /api/v1/admin/monitoring/celery/stats

## 🆕 新增 Schema 定义
- FeaturedRoadmapRequest
- FeaturedRoadmapResponse
```

---

## 🎯 最佳实践

1. **频繁同步**: 修改 Schema 后立即同步，避免积累
2. **提交前检查**: 依赖 Pre-commit Hook 自动验证
3. **查看报告**: 关注变更报告，了解具体变更内容
4. **类型验证**: 同步后运行 `npm run type-check` 确保无错误

---

## 📚 更多文档

- [完整方案文档](./doc/20260111_前后端Schema自动同步方案.md)
- [后端 API 文档](http://localhost:8000/docs)
- [架构设计文档](./doc/architecture.md)

---

## 🆘 需要帮助？

- 查看详细文档: `doc/20260111_前后端Schema自动同步方案.md`
- 查看系统状态: `make status`
- 联系团队: Backend & Frontend Team

