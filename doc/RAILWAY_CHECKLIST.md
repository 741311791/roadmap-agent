# Railway 部署检查清单

在部署到 Railway 前，请逐一确认以下事项。

---

## 📦 代码准备

### Backend Dockerfile
- [ ] `backend/Dockerfile` 已包含 Alembic 迁移文件复制：
  ```dockerfile
  COPY ./alembic /app/alembic
  COPY ./alembic.ini /app/alembic.ini
  ```
- [ ] `backend/Dockerfile` 启动命令包含数据库迁移：
  ```dockerfile
  CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
  ```
- [ ] Dockerfile 使用动态端口 `${PORT:-8000}` 而非硬编码 `8000`

### 依赖配置
- [ ] `backend/pyproject.toml` 包含所有必要依赖：
  - `alembic>=1.13.0`
  - `asyncpg>=0.30.0`
  - `redis[hiredis]>=5.2.0`
  - `langgraph>=1.0.2`
  - `fastapi>=0.115.0`

### Git 仓库
- [ ] 代码已推送到 GitHub
- [ ] `.gitignore` 已排除 `.env` 文件
- [ ] 没有将敏感信息（API Keys）提交到仓库

---

## 🚂 Railway 项目配置

### 服务创建
- [ ] 已创建 Railway 项目并连接 GitHub 仓库
- [ ] Backend 服务的 **Root Directory** 设置为 `/backend`
- [ ] 服务名称已设置为 `roadmap-backend`（可选，便于识别）

### 数据库服务
- [ ] 已添加 PostgreSQL 数据库
- [ ] 已添加 Redis 数据库
- [ ] 数据库服务名称已确认（默认为 `Postgres` 和 `Redis`）

---

## 🔐 环境变量配置

### 数据库连接（必填）
- [ ] `POSTGRES_HOST=${{Postgres.PGHOST}}`
- [ ] `POSTGRES_PORT=${{Postgres.PGPORT}}`
- [ ] `POSTGRES_USER=${{Postgres.PGUSER}}`
- [ ] `POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}`
- [ ] `POSTGRES_DB=${{Postgres.PGDATABASE}}`
- [ ] `REDIS_HOST=${{Redis.REDISHOST}}`
- [ ] `REDIS_PORT=${{Redis.REDISPORT}}`
- [ ] `REDIS_PASSWORD=${{Redis.REDISPASSWORD}}`

**注意**：引用语法为 `${{ServiceName.VARIABLE}}`，如果数据库服务名不同，请替换。

### 应用基础配置（必填）
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `CORS_ORIGINS=["https://your-frontend.up.railway.app"]` （JSON 数组格式）

### LLM API Keys（必填）
至少需要配置以下两个（其他会自动复用）：
- [ ] `ANALYZER_API_KEY=sk-...` （OpenAI）
- [ ] `ARCHITECT_API_KEY=sk-ant-...` （Anthropic）

完整配置（推荐）：
- [ ] `ANALYZER_API_KEY` (OpenAI - Intent Analyzer)
- [ ] `ARCHITECT_API_KEY` (Anthropic - Curriculum Architect)
- [ ] `VALIDATOR_API_KEY` (OpenAI - Structure Validator)
- [ ] `EDITOR_API_KEY` (Anthropic - Roadmap Editor)
- [ ] `GENERATOR_API_KEY` (Anthropic - Tutorial Generator)
- [ ] `RECOMMENDER_API_KEY` (OpenAI - Resource Recommender)
- [ ] `QUIZ_API_KEY` (OpenAI - Quiz Generator)

### Web Search API（必填）
- [ ] `TAVILY_API_KEY=tvly-...` 或 `TAVILY_API_KEY_LIST=["tvly-1", "tvly-2"]`
- [ ] `USE_DUCKDUCKGO_FALLBACK=true` （推荐，作为备选）

### S3 存储（必填）
选择以下任一方案：

**AWS S3：**
- [ ] `S3_ENDPOINT_URL=https://s3.amazonaws.com`
- [ ] `S3_ACCESS_KEY_ID=AKIA...`
- [ ] `S3_SECRET_ACCESS_KEY=...`
- [ ] `S3_BUCKET_NAME=roadmap-content`
- [ ] `S3_REGION=us-east-1`

**Cloudflare R2：**
- [ ] `S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com`
- [ ] `S3_ACCESS_KEY_ID=...`
- [ ] `S3_SECRET_ACCESS_KEY=...`
- [ ] `S3_BUCKET_NAME=roadmap-content`
- [ ] `S3_REGION=auto`

### JWT 认证（必填）
- [ ] `JWT_SECRET_KEY=<随机生成的字符串>` （使用 `bash scripts/generate_jwt_secret.sh` 生成）
- [ ] `JWT_ALGORITHM=HS256` （可选，默认值）
- [ ] `JWT_LIFETIME_SECONDS=86400` （可选，默认 24 小时）

### 邮件服务（可选）
如果需要邀请邮件功能：
- [ ] `RESEND_API_KEY=re-...`
- [ ] `RESEND_FROM_EMAIL=noreply@yourdomain.com`
- [ ] `FRONTEND_URL=https://your-frontend.up.railway.app`

---

## 🚀 部署验证

### 部署状态
- [ ] Railway 已自动触发部署
- [ ] 部署状态显示为 "Active" 或 "Success"
- [ ] 没有显示 "Crashed" 或 "Failed"

### 部署日志
在 **Deployments** -> 最新部署 -> **Deploy Logs** 中应看到：
- [ ] `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.`
- [ ] `INFO  [alembic.runtime.migration] Running upgrade`
- [ ] `INFO:     Uvicorn running on http://0.0.0.0:xxxx`
- [ ] `INFO:     Application startup complete.`

### 网络配置
- [ ] 已生成公网域名（Settings -> Networking -> Generate Domain）
- [ ] 域名格式为 `*.up.railway.app`
- [ ] 可以通过浏览器访问该域名

### API 测试
- [ ] 健康检查通过：
  ```bash
  curl https://your-backend.up.railway.app/health
  # 预期返回: {"status":"ok"}
  ```
- [ ] API 文档可访问：
  ```
  https://your-backend.up.railway.app/docs
  ```
- [ ] WebSocket 连接测试（可选）

---

## 🔄 后续配置

### CORS 更新
- [ ] 前端部署完成后，更新 `CORS_ORIGINS` 包含前端实际域名
- [ ] 重新部署后端服务使 CORS 生效

### 前端配置
- [ ] 前端环境变量中的 API 地址已更新为 Railway 后端域名
- [ ] 前端的 WebSocket 地址已更新（如果使用）

### 自定义域名（可选）
- [ ] 在 Railway Settings -> Networking 中添加自定义域名
- [ ] 在域名 DNS 服务商配置 CNAME 记录
- [ ] SSL 证书自动签发成功

### 监控与告警（推荐）
- [ ] 集成 Sentry 用于错误追踪
- [ ] 配置 Railway 的使用量告警
- [ ] 设置数据库备份策略

---

## ⚠️ 常见问题预检

### 数据库连接
- [ ] 变量引用语法使用 `${{}}` 而非 `${}`
- [ ] 数据库服务名称与引用中的名称一致

### 端口配置
- [ ] 没有硬编码端口 8000
- [ ] 使用了 `${PORT:-8000}` 动态端口

### CORS 配置
- [ ] `CORS_ORIGINS` 是 JSON 数组格式的**字符串**
- [ ] 域名使用 HTTPS（`https://` 而非 `http://`）
- [ ] 没有末尾斜杠（`https://domain.com` 而非 `https://domain.com/`）

### Alembic 迁移
- [ ] `alembic/` 目录和 `alembic.ini` 已复制到 Docker 镜像
- [ ] 启动命令在 Uvicorn 前执行了 `alembic upgrade head`

### S3 存储
- [ ] Bucket 已提前创建（Railway 不会自动创建）
- [ ] Access Key 有 Bucket 的读写权限
- [ ] 使用公网可访问的端点（不是 `localhost` 或内网 IP）

---

## 📊 性能优化（生产环境）

### Railway 服务配置
- [ ] 考虑升级到 Hobby Plan（$5/月）以避免休眠
- [ ] 根据实际负载调整服务的 CPU/内存配额
- [ ] 启用 Auto Deploy（Git push 自动部署）

### 数据库优化
- [ ] PostgreSQL 启用连接池（通过 `psycopg-pool`）
- [ ] 定期备份数据库（Railway Snapshots 或手动 `pg_dump`）
- [ ] 监控数据库查询性能（慢查询日志）

### 缓存策略
- [ ] Redis 用于会话存储和 LangGraph Checkpoint
- [ ] 考虑添加 CDN 加速静态资源（如 S3 前面加 CloudFront）

---

## ✅ 最终确认

在将域名公开发布前：
- [ ] 所有 API Keys 已替换为生产环境密钥
- [ ] `JWT_SECRET_KEY` 是安全生成的随机字符串
- [ ] `.env` 文件没有被提交到 Git
- [ ] 数据库已完成初始迁移
- [ ] 关键功能（路线图生成、教程生成）已端到端测试
- [ ] 错误监控和日志系统已配置
- [ ] 团队成员已了解部署架构和故障恢复流程

---

## 📚 参考文档

- 详细部署指南：[RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md)
- 快速开始：[RAILWAY_QUICK_START.md](./RAILWAY_QUICK_START.md)
- 环境变量模板：[RAILWAY_ENV_TEMPLATE.txt](./RAILWAY_ENV_TEMPLATE.txt)
- Railway 官方文档：https://docs.railway.app/

---

**祝部署顺利！** 🎉

如遇问题，请查看 `RAILWAY_DEPLOYMENT_GUIDE.md` 中的"常见问题排查"部分。

