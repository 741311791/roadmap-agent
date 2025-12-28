# 部署方案对比

## 📊 方案总览

| 方案 | 适用场景 | 服务数量 | Celery 支持 | 推荐度 |
|-----|---------|---------|------------|-------|
| 单一 Dockerfile（旧） | 简单场景，无 Celery | 1 个 | ❌ 否 | ⭐⭐ (不推荐) |
| Railway 多服务（新） | 生产环境，完整功能 | 3 个 | ✅ 是 | ⭐⭐⭐⭐⭐ (推荐) |
| Docker Compose | 本地开发/自托管 | 5-6 个 | ✅ 是 | ⭐⭐⭐⭐ |

---

## 🔄 为什么需要多服务部署？

### 问题背景

引入 Celery 前，系统的架构是：

```
┌─────────────────┐
│  FastAPI 应用   │ ← 处理所有请求
│                 │ ← 生成路线图内容（阻塞）
│                 │ ← 写入执行日志（耗尽连接池）
└─────────────────┘
```

**存在的问题**：
1. ❌ **数据库连接池耗尽**：每个请求都要写大量日志
2. ❌ **主流程阻塞**：内容生成任务阻塞其他请求
3. ❌ **单点故障**：一个任务失败影响整个服务

### 解决方案：Celery 异步队列

引入 Celery 后，架构变为：

```
┌─────────────────┐     ┌──────────────────────┐
│  FastAPI 应用   │────►│ Celery Worker (Logs) │
│                 │     └──────────────────────┘
│                 │     ┌──────────────────────┐
│                 │────►│ Celery Worker (Content)│
└─────────────────┘     └──────────────────────┘
        ↓                        ↓
    ┌─────────┐          ┌─────────────┐
    │  Redis  │          │ PostgreSQL  │
    └─────────┘          └─────────────┘
```

**优势**：
1. ✅ **完全解耦**：主应用不再直接写日志
2. ✅ **独立连接池**：每个 Worker 有独立的数据库连接
3. ✅ **可扩展性**：可以按需增加 Worker 数量
4. ✅ **可靠性**：任务失败不影响主应用

---

## 📦 方案一：单一 Dockerfile（旧，不推荐）

### 配置

```dockerfile
# Dockerfile
CMD sh -c "python scripts/create_tables.py && \
          alembic stamp head && \
          python scripts/create_admin_user.py || true && \
          uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
```

### 特点

| 特性 | 说明 |
|-----|------|
| 服务数量 | 1 个（仅 API） |
| Celery Worker | ❌ 未启动 |
| 内容生成 | ❌ 会失败（无 Worker 处理） |
| 日志写入 | ❌ 会失败（无 Worker 处理） |
| 数据库连接 | ⚠️ 可能耗尽（如果回退到同步写日志） |
| 适用场景 | 仅用于测试/演示 |

### 问题

❌ **无法使用 Celery**：Worker 进程未启动，所有异步任务会失败  
❌ **性能问题**：如果回退到同步写日志，会耗尽连接池  
❌ **功能残缺**：内容生成和日志记录无法正常工作

---

## ⭐ 方案二：Railway 多服务（新，推荐）

### 配置

使用 `Dockerfile.railway` + `railway_entrypoint.sh`：

```bash
# API 服务
SERVICE_TYPE=api

# Celery Worker (Logs)
SERVICE_TYPE=celery_logs

# Celery Worker (Content)
SERVICE_TYPE=celery_content
```

### 特点

| 特性 | 说明 |
|-----|------|
| 服务数量 | 3 个（API + 2 个 Worker） |
| Celery Worker | ✅ 完整支持 |
| 内容生成 | ✅ 异步处理，不阻塞 |
| 日志写入 | ✅ 异步批量写入 |
| 数据库连接 | ✅ 独立连接池，不会耗尽 |
| 可扩展性 | ✅ 可按需增加 Worker |
| 适用场景 | 生产环境 |

### 优势

✅ **完整功能**：所有异步任务正常工作  
✅ **独立扩展**：可以单独扩展 Worker 数量  
✅ **资源优化**：API 和 Worker 使用独立资源  
✅ **易于监控**：每个服务独立日志和指标

### 成本

| 实例规格 | API | Logs Worker | Content Worker | 总计 |
|---------|-----|-------------|----------------|------|
| Starter ($5/月) | $5 | $5 | $5 | **$15/月** |
| Developer ($10/月) | $10 | $10 | $10 | **$30/月** |

**优化建议**：
- 可以使用更小的实例运行 Logs Worker（低 CPU 消耗）
- Content Worker 可以按需启动（不是持续运行）

---

## 🐳 方案三：Docker Compose

### 配置

```yaml
# docker-compose.yml
services:
  api:           # FastAPI 应用
  postgres:      # 数据库
  redis:         # 消息队列
  celery_worker: # Celery Worker (Logs)
  celery_content_worker: # Celery Worker (Content)
  flower:        # 监控界面（可选）
```

### 特点

| 特性 | 说明 |
|-----|------|
| 服务数量 | 5-6 个（包括基础设施） |
| Celery Worker | ✅ 完整支持 |
| 适用场景 | 本地开发、自托管服务器 |
| 一键启动 | ✅ `docker-compose up -d` |
| 监控界面 | ✅ Flower (http://localhost:5555) |

### 优势

✅ **开发友好**：一键启动所有服务  
✅ **完整环境**：包括数据库和 Redis  
✅ **易于调试**：所有日志在本地查看

---

## 🎯 选择建议

### 我应该选择哪个方案？

| 场景 | 推荐方案 | 原因 |
|-----|---------|------|
| 本地开发 | Docker Compose | 一键启动，包含所有服务 |
| 生产环境 | Railway 多服务 | 完整功能，易于扩展 |
| 快速演示 | ⚠️ 单一 Dockerfile（谨慎） | 功能残缺，仅用于展示 UI |
| 自托管服务器 | Docker Compose | 完全控制，成本低 |

---

## 🚀 迁移步骤

### 从单一 Dockerfile 迁移到 Railway 多服务

1. **创建 PostgreSQL 和 Redis 服务**
   ```
   Railway Dashboard → Add Service → PostgreSQL
   Railway Dashboard → Add Service → Upstash Redis
   ```

2. **创建 API 服务**
   ```yaml
   Dockerfile: backend/Dockerfile.railway
   Environment:
     SERVICE_TYPE: api
     DATABASE_URL: ${{Postgres.DATABASE_URL}}
     REDIS_URL: ${{Redis.REDIS_URL}}
   ```

3. **创建 Celery Worker 服务（Logs）**
   ```yaml
   Dockerfile: backend/Dockerfile.railway
   Environment:
     SERVICE_TYPE: celery_logs
     DATABASE_URL: ${{Postgres.DATABASE_URL}}
     REDIS_URL: ${{Redis.REDIS_URL}}
   ```

4. **创建 Celery Worker 服务（Content）**
   ```yaml
   Dockerfile: backend/Dockerfile.railway
   Environment:
     SERVICE_TYPE: celery_content
     DATABASE_URL: ${{Postgres.DATABASE_URL}}
     REDIS_URL: ${{Redis.REDIS_URL}}
     OPENAI_API_KEY: ${{roadmap-api.OPENAI_API_KEY}}
   ```

5. **验证部署**
   ```bash
   curl https://your-api-url.railway.app/health
   ```

---

## 📚 相关文档

- **Railway 详细部署指南**：[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- **Celery 设置指南**：[docs/CELERY_SETUP.md](docs/CELERY_SETUP.md)
- **Docker Compose 配置**：[docker-compose.yml](docker-compose.yml)
- **原 Dockerfile**：[Dockerfile](Dockerfile)（仅供参考）

---

## ❓ 常见问题

### Q1: 可以只部署一个服务吗？

**A**: 不推荐。如果只部署 API 服务而不启动 Celery Workers，会导致：
- ❌ 内容生成任务失败（找不到 Worker）
- ❌ 执行日志写入失败
- ❌ 路线图生成流程中断

### Q2: Railway 上的成本如何？

**A**: 使用 Starter 计划（$5/月/服务）：
- API 服务：$5/月
- Celery Worker (Logs)：$5/月
- Celery Worker (Content)：$5/月
- **总计：$15/月**

加上基础设施：
- PostgreSQL：$5/月
- Redis (Upstash)：按使用量计费（通常 < $5/月）

**月度总成本：约 $20-25**

### Q3: 如何降低成本？

**优化方案**：
1. **合并 Logs Worker 到 API 服务**（不推荐，可能影响性能）
2. **使用更小的实例规格**（降低并发数）
3. **按需启动 Content Worker**（非高峰时段关闭）

### Q4: 原来的 Dockerfile 还能用吗？

**A**: 可以用，但功能残缺：
- ✅ API 接口正常
- ❌ 内容生成失败（无 Worker）
- ❌ 日志写入失败（无 Worker）

**不推荐用于生产环境。**

### Q5: 本地开发需要启动所有服务吗？

**A**: 推荐使用 Docker Compose 一键启动：
```bash
docker-compose up -d
```

或者手动启动：
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL (或使用 Docker)
docker run -p 5432:5432 -e POSTGRES_PASSWORD=roadmap_pass postgres:15

# Terminal 3: FastAPI
uvicorn app.main:app --reload

# Terminal 4: Celery Worker (Logs)
celery -A app.core.celery_app worker --queues=logs --pool=prefork

# Terminal 5: Celery Worker (Content)
celery -A app.core.celery_app worker --queues=content_generation --pool=prefork
```





