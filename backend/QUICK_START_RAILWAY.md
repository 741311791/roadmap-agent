# Railway 快速部署指南 🚀

5 分钟内在 Railway 上部署完整的路线图生成系统。

---

## 📋 前置条件

- [ ] Railway 账号（免费或付费计划）
- [ ] GitHub 仓库已推送最新代码
- [ ] 已获取 OpenAI API Key

---

## 🚀 部署步骤

### 第 1 步：创建 Railway 项目

1. 登录 [Railway](https://railway.app/)
2. 点击 **"New Project"**
3. 选择 **"Deploy from GitHub repo"**
4. 授权并选择你的仓库

---

### 第 2 步：添加基础设施

#### 2.1 添加 PostgreSQL
```
Dashboard → Add Service → Database → PostgreSQL
```
✅ Railway 会自动生成 `DATABASE_URL` 环境变量

#### 2.2 添加 Redis
```
Dashboard → Add Service → Database → Redis
```
或使用 Upstash Redis（推荐，更便宜）：
```
Dashboard → Add Service → Add Integration → Upstash Redis
```
✅ 自动生成 `REDIS_URL` 环境变量

---

### 第 3 步：创建 API 服务

1. **添加服务**
   ```
   Dashboard → Add Service → GitHub Repo → 选择你的仓库
   ```

2. **配置服务**
   - **Service Name**: `roadmap-api`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile.railway`

3. **设置环境变量**
   
   点击服务 → **Variables** → 添加以下变量：
   
   ```env
   # 服务类型（必需）
   SERVICE_TYPE=api
   
   # 端口配置
   PORT=8000
   UVICORN_WORKERS=4
   
   # 数据库（自动生成，无需手动添加）
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   
   # Redis（自动生成，无需手动添加）
   REDIS_URL=${{Redis.REDIS_URL}}
   
   # JWT 配置（必需）
   JWT_SECRET_KEY=<运行 ./scripts/generate_jwt_secret.sh 生成>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=43200
   
   # OpenAI 配置（必需）
   OPENAI_API_KEY=sk-your-api-key-here
   OPENAI_MODEL=gpt-4o-mini
   
   # 管理员账号（必需）
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=your-secure-password-here
   ADMIN_USERNAME=admin
   
   # 应用配置
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **部署**
   - 点击 **"Deploy"**
   - 等待构建完成（约 3-5 分钟）

5. **获取 API URL**
   ```
   Settings → Domains → 复制 Public URL
   例如：https://roadmap-api-production.up.railway.app
   ```

---

### 第 4 步：创建 Celery Worker (Logs)

1. **添加服务**
   ```
   Dashboard → Add Service → GitHub Repo → 选择相同的仓库
   ```

2. **配置服务**
   - **Service Name**: `roadmap-celery-logs`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile.railway`

3. **设置环境变量**
   
   ```env
   # 服务类型（必需）
   SERVICE_TYPE=celery_logs
   
   # Worker 配置
   CELERY_LOGS_CONCURRENCY=2
   CELERY_LOG_LEVEL=info
   
   # 共享变量（引用其他服务）
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   JWT_SECRET_KEY=${{roadmap-api.JWT_SECRET_KEY}}
   OPENAI_API_KEY=${{roadmap-api.OPENAI_API_KEY}}
   OPENAI_MODEL=${{roadmap-api.OPENAI_MODEL}}
   
   # 应用配置
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **部署**
   - 点击 **"Deploy"**
   - ⚠️ **重要**：在 **Settings → Networking** 中，**不要**暴露 HTTP 端口（这是后台服务）

---

### 第 5 步：创建 Celery Worker (Content)

1. **添加服务**
   ```
   Dashboard → Add Service → GitHub Repo → 选择相同的仓库
   ```

2. **配置服务**
   - **Service Name**: `roadmap-celery-content`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile.railway`

3. **设置环境变量**
   
   ```env
   # 服务类型（必需）
   SERVICE_TYPE=celery_content
   
   # Worker 配置
   CELERY_CONTENT_CONCURRENCY=2
   CELERY_LOG_LEVEL=info
   
   # 共享变量
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   JWT_SECRET_KEY=${{roadmap-api.JWT_SECRET_KEY}}
   OPENAI_API_KEY=${{roadmap-api.OPENAI_API_KEY}}
   OPENAI_MODEL=${{roadmap-api.OPENAI_MODEL}}
   
   # 应用配置
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **部署**
   - 点击 **"Deploy"**
   - ⚠️ **重要**：同样不要暴露 HTTP 端口

---

## ✅ 验证部署

### 检查 API 服务
```bash
curl https://your-api-url.railway.app/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "2.1.0"
}
```

### 检查 Celery Workers

1. 查看 **roadmap-celery-logs** 日志：
   ```
   Dashboard → roadmap-celery-logs → Logs
   ```
   应该看到：
   ```
   🔄 Starting Celery Worker for Logs Queue...
   [INFO] celery@logs ready.
   ```

2. 查看 **roadmap-celery-content** 日志：
   ```
   Dashboard → roadmap-celery-content → Logs
   ```
   应该看到：
   ```
   🎨 Starting Celery Worker for Content Generation Queue...
   [INFO] celery@content ready.
   ```

### 测试完整流程

```bash
# 1. 登录获取 Token
curl -X POST https://your-api-url.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-secure-password-here"
  }'

# 2. 创建路线图（使用上一步返回的 access_token）
curl -X POST https://your-api-url.railway.app/api/v1/roadmaps \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{
    "goal": "Learn React from scratch",
    "context": {
      "current_level": "beginner",
      "time_available": "3 months"
    }
  }'
```

如果返回路线图 ID，说明部署成功！🎉

---

## 📊 服务架构总览

部署完成后，你的 Railway 项目应该有以下服务：

```
Railway Project
├── Postgres (数据库)
├── Redis (消息队列)
├── roadmap-api (API 服务) ← 暴露公共 URL
├── roadmap-celery-logs (日志 Worker) ← 后台运行
└── roadmap-celery-content (内容 Worker) ← 后台运行
```

---

## 🔧 常见问题

### Q: 为什么需要 3 个服务？

A: 因为引入了 Celery 异步任务队列：
- **API 服务**：处理 HTTP 请求
- **Logs Worker**：异步写入执行日志（避免阻塞主流程）
- **Content Worker**：异步生成路线图内容（CPU 密集型任务）

详细说明请参考：[DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)

### Q: 可以只部署一个服务吗？

A: **不推荐**。如果只部署 API 服务，会导致：
- ❌ 内容生成失败（找不到 Worker）
- ❌ 日志写入失败
- ❌ 路线图生成流程中断

### Q: 如何查看 Worker 的日志？

A: 在 Railway Dashboard 中：
```
Dashboard → 选择 Worker 服务 → Logs 标签页
```

### Q: 如何更新代码？

A: 推送代码到 GitHub 后，Railway 会自动重新部署：
```bash
git add .
git commit -m "Update code"
git push origin main
```
Railway 会检测到更新并自动部署所有服务。

### Q: 如何回滚到之前的版本？

A: 在 Railway Dashboard 中：
```
Dashboard → 选择服务 → Deployments → 选择之前的部署 → Redeploy
```

---

## 💰 成本估算

使用 Railway Starter 计划（$5/月/服务）：

| 服务 | 实例规格 | 月度成本 |
|-----|---------|---------|
| PostgreSQL | 共享 | $5 |
| Redis (Upstash) | 按使用量 | ~$2-5 |
| roadmap-api | Starter | $5 |
| roadmap-celery-logs | Starter | $5 |
| roadmap-celery-content | Starter | $5 |
| **总计** | | **$22-25/月** |

**优化建议**：
- 使用更小的实例运行 Logs Worker（低 CPU 消耗）
- 非高峰时段可以暂停 Content Worker

---

## 🌸 可选：添加 Flower 监控

如果想监控 Celery 任务状态，可以添加第四个服务：

1. **添加服务**
   ```
   Dashboard → Add Service → GitHub Repo
   ```

2. **配置**
   - **Service Name**: `roadmap-celery-flower`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile.railway`

3. **环境变量**
   ```env
   SERVICE_TYPE=flower
   FLOWER_PORT=5555
   REDIS_URL=${{Redis.REDIS_URL}}
   ```

4. **暴露端口**
   - Settings → Networking → 暴露端口 5555

5. **访问监控界面**
   ```
   https://roadmap-celery-flower-production.up.railway.app
   ```

---

## 📚 相关文档

- **详细部署指南**：[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- **方案对比**：[DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)
- **Celery 配置**：[docs/CELERY_SETUP.md](docs/CELERY_SETUP.md)
- **主 README**：[README.md](README.md)

---

## 🎉 下一步

✅ 部署完成！现在你可以：

1. 🌐 访问你的 API
2. 📝 创建路线图
3. 📊 查看执行日志
4. 🔍 监控 Worker 状态

如有问题，请查看 [故障排查文档](RAILWAY_DEPLOYMENT.md#故障排查)。





