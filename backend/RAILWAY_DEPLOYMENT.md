# Railway 多服务部署指南

## 📋 概述

本项目引入 Celery 后，需要运行多个服务：
- **API 服务**：FastAPI 应用
- **Celery Worker (Logs)**：处理执行日志队列
- **Celery Worker (Content)**：处理内容生成队列

Railway 支持在同一个项目中部署多个服务，共享环境变量和基础设施。

---

## 🚀 部署步骤

### 1. 准备基础设施

在 Railway 项目中添加以下服务：

#### 1.1 PostgreSQL 数据库
```
- 从 Railway Dashboard 添加 PostgreSQL 插件
- Railway 会自动生成 DATABASE_URL 环境变量
```

#### 1.2 Redis（使用 Upstash Redis）
```
- 从 Railway Dashboard 添加 Upstash Redis 插件
- 或者手动添加环境变量：
  - REDIS_URL: your-upstash-redis-url (格式：rediss://...)
```

### 2. 创建三个服务

#### 2.1 服务 1：API Service

**配置：**
- **Name**: `roadmap-api`
- **Dockerfile Path**: `backend/Dockerfile.railway`
- **Root Directory**: `backend`
- **Environment Variables**:
  ```env
  SERVICE_TYPE=api
  PORT=8000
  UVICORN_WORKERS=4
  
  # 数据库配置（Railway 自动生成）
  DATABASE_URL=${{Postgres.DATABASE_URL}}
  
  # Redis 配置
  REDIS_URL=${{Redis.REDIS_URL}}
  
  # JWT 配置
  JWT_SECRET_KEY=your-secret-key-here
  JWT_ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=43200
  
  # 管理员账号配置
  ADMIN_EMAIL=admin@example.com
  ADMIN_PASSWORD=your-secure-password
  ADMIN_USERNAME=admin
  
  # OpenAI 配置
  OPENAI_API_KEY=your-openai-api-key
  OPENAI_MODEL=gpt-4o-mini
  
  # 应用配置
  ENVIRONMENT=production
  DEBUG=false
  ```

- **Build Command**: *(留空，使用 Dockerfile)*
- **Start Command**: *(留空，由 entrypoint.sh 处理)*

---

#### 2.2 服务 2：Celery Worker (Logs)

**配置：**
- **Name**: `roadmap-celery-logs`
- **Dockerfile Path**: `backend/Dockerfile.railway`
- **Root Directory**: `backend`
- **Environment Variables**:
  ```env
  SERVICE_TYPE=celery_logs
  CELERY_LOGS_CONCURRENCY=2
  CELERY_LOG_LEVEL=info
  
  # 共享的基础设施变量（引用与 API 相同）
  DATABASE_URL=${{Postgres.DATABASE_URL}}
  REDIS_URL=${{Redis.REDIS_URL}}
  JWT_SECRET_KEY=${{roadmap-api.JWT_SECRET_KEY}}
  OPENAI_API_KEY=${{roadmap-api.OPENAI_API_KEY}}
  OPENAI_MODEL=${{roadmap-api.OPENAI_MODEL}}
  ENVIRONMENT=production
  DEBUG=false
  ```

- **Important**: 不要暴露 HTTP 端口（这是一个后台 Worker）

---

#### 2.3 服务 3：Celery Worker (Content)

**配置：**
- **Name**: `roadmap-celery-content`
- **Dockerfile Path**: `backend/Dockerfile.railway`
- **Root Directory**: `backend`
- **Environment Variables**:
  ```env
  SERVICE_TYPE=celery_content
  CELERY_CONTENT_CONCURRENCY=2
  CELERY_LOG_LEVEL=info
  
  # 共享的基础设施变量
  DATABASE_URL=${{Postgres.DATABASE_URL}}
  REDIS_URL=${{Redis.REDIS_URL}}
  JWT_SECRET_KEY=${{roadmap-api.JWT_SECRET_KEY}}
  OPENAI_API_KEY=${{roadmap-api.OPENAI_API_KEY}}
  OPENAI_MODEL=${{roadmap-api.OPENAI_MODEL}}
  ENVIRONMENT=production
  DEBUG=false
  ```

- **Important**: 不要暴露 HTTP 端口（这是一个后台 Worker）

---

### 3. 服务依赖关系

确保服务按以下顺序启动：
1. PostgreSQL
2. Redis
3. API Service (会运行数据库迁移)
4. Celery Workers (依赖数据库和 Redis)

Railway 会自动处理依赖关系，但你可以在 Dashboard 中调整启动顺序。

---

## 🔧 环境变量管理

### 共享变量（推荐方式）

Railway 支持通过 `${{service.VARIABLE_NAME}}` 语法引用其他服务的环境变量：

```env
# 在 Worker 服务中引用 API 服务的变量
JWT_SECRET_KEY=${{roadmap-api.JWT_SECRET_KEY}}
OPENAI_API_KEY=${{roadmap-api.OPENAI_API_KEY}}
```

**优势**：
- 单一数据源（在 API 服务中定义一次）
- 自动同步
- 减少配置错误

---

## 📊 监控和日志

### 查看服务状态
```
Railway Dashboard → Services → 查看每个服务的状态
```

### 查看日志
```
Railway Dashboard → Logs → 筛选服务
```

**日志前缀：**
- API 服务：`📡 Starting FastAPI API server...`
- Celery Logs Worker：`🔄 Starting Celery Worker for Logs Queue...`
- Celery Content Worker：`🎨 Starting Celery Worker for Content Generation Queue...`

### 监控 Celery 任务（可选）

如果需要监控 Celery 任务状态，可以添加第四个服务：

#### 服务 4：Celery Flower (可选)

**配置：**
- **Name**: `roadmap-celery-flower`
- **Dockerfile Path**: `backend/Dockerfile.railway`
- **Root Directory**: `backend`
- **Environment Variables**:
  ```env
  SERVICE_TYPE=flower
  REDIS_URL=${{Redis.REDIS_URL}}
  FLOWER_PORT=5555
  ```

需要在 `railway_entrypoint.sh` 中添加 `flower` 分支：

```bash
flower)
  echo "🌸 Starting Celery Flower monitoring..."
  exec celery -A app.core.celery_app flower \
    --port=${FLOWER_PORT:-5555} \
    --broker=${REDIS_URL}
  ;;
```

---

## 🧪 测试部署

### 1. 检查 API 服务
```bash
curl https://your-railway-url.railway.app/health
```

### 2. 检查 Celery Workers
```bash
# 查看 Railway 日志，确认 Workers 已启动
# 应该看到类似的日志：
# - celery@logs ready
# - celery@content ready
```

### 3. 测试完整流程
```bash
# 创建一条路线图，观察：
# 1. API 服务接收请求
# 2. Celery Content Worker 处理内容生成
# 3. Celery Logs Worker 处理日志写入
```

---

## 💡 性能优化建议

### Worker 并发数配置

根据你的 Railway 实例规格调整并发数：

| 实例规格 | API Workers | Celery Logs | Celery Content |
|---------|-------------|-------------|----------------|
| Starter | 2 | 1 | 1 |
| Developer | 4 | 2 | 2 |
| Team | 8 | 4 | 4 |

### 成本优化

如果预算有限，可以：
1. **合并 Logs Worker 到 API 服务**（仅用于开发）
2. **使用更小的实例**（减少并发数）
3. **按需扩展**（高峰时段增加 Worker）

---

## 🐛 故障排查

### 问题 1：Worker 无法连接 Redis

**症状：**
```
ConnectionError: Error connecting to Redis
```

**解决方案：**
- 检查 `REDIS_URL` 是否正确配置
- 确保使用 `rediss://` 协议（TLS）
- 检查 Upstash Redis 配置中的 SSL 设置

### 问题 2：数据库迁移失败

**症状：**
```
relation "roadmaps" does not exist
```

**解决方案：**
- 确保 API 服务先于 Worker 服务启动
- 手动运行迁移：
  ```bash
  railway run --service roadmap-api python scripts/create_tables.py
  ```

### 问题 3：Worker 内存占用过高

**症状：**
- Railway 显示内存使用率 > 90%

**解决方案：**
- 降低并发数（`CELERY_CONTENT_CONCURRENCY=1`）
- 减少 `max-tasks-per-child`（更频繁地重启子进程）
- 升级实例规格

---

## 📦 与原 Dockerfile 的区别

| 特性 | 原 Dockerfile | Railway Dockerfile |
|-----|--------------|-------------------|
| 用途 | 单一 API 服务 | 多服务支持 |
| 启动方式 | 直接启动 uvicorn | entrypoint.sh 根据 SERVICE_TYPE 启动 |
| 数据库迁移 | 总是运行 | 仅在 API 服务中运行 |
| 灵活性 | 固定 | 通过环境变量控制 |

---

## 🎯 下一步

1. ✅ 在 Railway Dashboard 创建三个服务
2. ✅ 配置环境变量
3. ✅ 部署所有服务
4. ✅ 测试完整流程
5. ⏳ 监控性能和日志
6. ⏳ 根据负载调整并发数

---

## 📚 相关文档

- [Railway 多服务部署](https://docs.railway.app/deploy/monorepo)
- [Celery 配置说明](./docs/CELERY_SETUP.md)
- [原 Dockerfile](./Dockerfile)
- [Docker Compose 配置](./docker-compose.yml)

---

## ❓ 常见问题

**Q: 可以只部署一个服务吗？**  
A: 可以，但不推荐。如果不启动 Celery Workers，内容生成和日志写入会失败。

**Q: Railway 上的 Redis 费用如何？**  
A: 推荐使用 Upstash Redis（按请求计费），比 Railway 自带的 Redis 更便宜。

**Q: 如何回滚到单一服务模式？**  
A: 使用原 `Dockerfile`，并移除所有 Celery 相关配置（不推荐，会导致连接池耗尽）。





