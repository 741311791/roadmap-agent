# Railway 快速部署指南 (5 分钟)

这是一个浓缩版的快速操作指南，适合有一定经验的开发者。详细文档请参考 `RAILWAY_DEPLOYMENT_GUIDE.md`。

---

## 第一步：创建项目 (1 分钟)

1. 访问 [railway.app](https://railway.app) -> **New Project** -> **Deploy from GitHub repo**
2. 选择 `roadmap-agent` 仓库
3. Railway 会自动检测到 Dockerfile

---

## 第二步：配置服务 (1 分钟)

### Backend 服务
1. 点击服务卡片 -> **Settings**
2. **Root Directory**: `/backend`
3. **Service Name**: `roadmap-backend` (可选)

### 添加数据库
1. **New** -> **Database** -> **PostgreSQL**
2. **New** -> **Database** -> **Redis**

---

## 第三步：配置环境变量 (3 分钟)

点击 Backend 服务 -> **Variables** -> **RAW Editor**，粘贴以下内容（替换占位符）：

```bash
# 数据库连接（自动引用）
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
REDIS_HOST=${{Redis.REDISHOST}}
REDIS_PORT=${{Redis.REDISPORT}}
REDIS_PASSWORD=${{Redis.REDISPASSWORD}}

# 应用配置
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=["https://your-frontend-url.up.railway.app"]

# LLM API Keys (必填)
ANALYZER_API_KEY=sk-your-openai-key
ARCHITECT_API_KEY=sk-ant-your-anthropic-key
VALIDATOR_API_KEY=sk-your-openai-key
EDITOR_API_KEY=sk-ant-your-anthropic-key
GENERATOR_API_KEY=sk-ant-your-anthropic-key
RECOMMENDER_API_KEY=sk-your-openai-key
QUIZ_API_KEY=sk-your-openai-key

# Web Search (必填)
TAVILY_API_KEY=tvly-your-key

# S3 存储 (必填 - 使用 AWS S3 或 Cloudflare R2)
# AWS S3:
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=roadmap-content
S3_REGION=us-east-1

# 或 Cloudflare R2:
# S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
# S3_ACCESS_KEY_ID=...
# S3_SECRET_ACCESS_KEY=...
# S3_BUCKET_NAME=roadmap-content
# S3_REGION=auto

# JWT (必填 - 使用 openssl rand -base64 48 生成)
JWT_SECRET_KEY=<生成的随机字符串>

# 邮件服务 (可选)
RESEND_API_KEY=re-your-key
RESEND_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=https://your-frontend-url.up.railway.app
```

**注意**：
- 数据库变量的引用语法使用 `${{ServiceName.VARIABLE}}`
- 如果你的数据库服务名不是 `Postgres`/`Redis`，请替换为实际名称
- `CORS_ORIGINS` 必须是 JSON 数组格式的字符串

---

## 第四步：部署与测试

1. **部署**：变量配置完成后 Railway 会自动部署
2. **查看日志**：点击 **Deployments** -> 最新部署 -> 查看日志
3. **生成域名**：**Settings** -> **Networking** -> **Generate Domain**
4. **测试 API**：
   ```bash
   curl https://your-backend.up.railway.app/health
   # 预期返回: {"status":"ok"}
   ```

---

## 成功标志

部署日志中应该看到：

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Running upgrade -> ...
INFO:     Uvicorn running on http://0.0.0.0:xxxx
INFO:     Application startup complete.
```

---

## 常见问题

### 1. 数据库连接失败
检查变量引用语法是否正确：`${{Postgres.PGHOST}}` 而非 `${Postgres.PGHOST}`

### 2. Alembic 迁移失败
确认 Dockerfile 已更新（包含 `COPY ./alembic` 和 `alembic upgrade head`）

### 3. CORS 错误
确认 `CORS_ORIGINS` 格式为：`["https://url1.com", "https://url2.com"]`

### 4. Port binding 错误
Dockerfile 应使用 `${PORT:-8000}` 而非硬编码 `8000`

---

## 检查清单

- [ ] Backend Root Directory 设置为 `/backend`
- [ ] PostgreSQL 和 Redis 已添加
- [ ] 所有环境变量已配置（至少 LLM Keys + S3 + JWT）
- [ ] 部署成功且服务运行
- [ ] 生成了公网域名
- [ ] API 健康检查通过

---

## 下一步

1. **部署前端**：参考前端部署文档（Vercel/Netlify）
2. **更新 CORS**：将前端域名添加到 `CORS_ORIGINS`
3. **配置自定义域名**（可选）
4. **设置监控告警**（推荐）

---

**需要详细说明？** 查看 `RAILWAY_DEPLOYMENT_GUIDE.md`

**需要环境变量模板？** 查看 `RAILWAY_ENV_TEMPLATE.txt`

