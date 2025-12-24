# Railway 部署指南

本文档详细说明如何将后端服务部署到 Railway。

## 前置准备

- ✅ Railway 账户（支持 GitHub 登录）
- ✅ 代码已推送到 GitHub 仓库
- ✅ 准备好所有必需的 API Keys（OpenAI、Anthropic、Tavily、Resend）

---

## 部署步骤

### 第一步：创建 Railway 项目

1. 登录 [Railway Dashboard](https://railway.app/dashboard)
2. 点击 **"New Project"**
3. 选择 **"Deploy from GitHub repo"**
4. 选择你的 `roadmap-agent` 仓库
5. Railway 会自动检测到 Dockerfile 并创建服务

### 第二步：配置服务（Backend）

#### 2.1 设置 Root Directory

默认情况下，Railway 会在仓库根目录查找 Dockerfile，但我们的后端在 `backend/` 子目录下。

1. 点击刚创建的服务卡片
2. 进入 **Settings** 标签页
3. 找到 **Source** -> **Root Directory** 设置
4. 输入：`/backend`
5. 点击 **Save**

#### 2.2 设置服务名称（可选）

在 **Settings** -> **Service Name** 中将服务重命名为 `roadmap-backend`（便于识别）。

### 第三步：添加数据库服务

#### 3.1 添加 PostgreSQL

1. 在项目画布（Canvas）空白处右键点击（或点击右上角 **"+ New"**）
2. 选择 **Database** -> **Add PostgreSQL**
3. Railway 会自动创建一个 PostgreSQL 实例，并生成以下变量：
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`

#### 3.2 添加 Redis

1. 同样在空白处右键点击（或点击 **"+ New"**）
2. 选择 **Database** -> **Add Redis**
3. Railway 会自动创建一个 Redis 实例，并生成以下变量：
   - `REDISHOST`
   - `REDISPORT`
   - `REDISPASSWORD`

### 第四步：配置环境变量

点击 **Backend 服务** -> **Variables** 标签页，添加以下环境变量。

#### 4.1 数据库连接变量（引用 Railway 数据库）

Railway 支持跨服务引用变量，语法为 `${ServiceName.VARIABLE}`。

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` | PostgreSQL 主机地址 |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` | PostgreSQL 端口 |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` | PostgreSQL 用户名 |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` | PostgreSQL 密码 |
| `POSTGRES_DB` | `${{Postgres.PGDATABASE}}` | PostgreSQL 数据库名 |
| `REDIS_HOST` | `${{Redis.REDISHOST}}` | Redis 主机地址 |
| `REDIS_PORT` | `${{Redis.REDISPORT}}` | Redis 端口 |
| `REDIS_PASSWORD` | `${{Redis.REDISPASSWORD}}` | Redis 密码 |

**注意**：
- 如果你的数据库服务使用了自定义名称（如 `roadmap-db`），请替换 `Postgres` 为实际服务名。
- Railway 的变量引用语法使用 `${{}}` 而非 `${}`。

#### 4.2 应用基础配置

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `ENVIRONMENT` | `production` | 运行环境 |
| `DEBUG` | `false` | 关闭调试模式 |
| `CORS_ORIGINS` | `["https://your-frontend.up.railway.app"]` | 跨域白名单（JSON 格式字符串） |

**重要**：`CORS_ORIGINS` 必须是 **JSON 数组字符串格式**，例如：
```
["https://roadmap-frontend.up.railway.app", "https://www.yourdomain.com"]
```

#### 4.3 LLM API Keys

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `ANALYZER_API_KEY` | `sk-...` | OpenAI API Key（Intent Analyzer） |
| `ARCHITECT_API_KEY` | `sk-ant-...` | Anthropic API Key（Curriculum Architect） |
| `VALIDATOR_API_KEY` | `sk-...` | OpenAI API Key（Structure Validator） |
| `EDITOR_API_KEY` | `sk-ant-...` | Anthropic API Key（Roadmap Editor） |
| `GENERATOR_API_KEY` | `sk-ant-...` | Anthropic API Key（Tutorial Generator） |
| `RECOMMENDER_API_KEY` | `sk-...` | OpenAI API Key（Resource Recommender） |
| `QUIZ_API_KEY` | `sk-...` | OpenAI API Key（Quiz Generator） |

**简化配置**：如果你使用相同的 Key，可以只配置以下两个：
- `ANALYZER_API_KEY`（OpenAI）
- `ARCHITECT_API_KEY`（Anthropic）

其他 Agent 会自动复用这些 Key（参见 `backend/app/config/settings.py`）。

#### 4.4 Web Search 配置

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `TAVILY_API_KEY` | `tvly-...` | Tavily API Key（单个 Key） |
| `TAVILY_API_KEY_LIST` | `["tvly-1", "tvly-2"]` | Tavily Key 列表（可选，逗号分隔或 JSON 数组） |
| `USE_DUCKDUCKGO_FALLBACK` | `true` | Tavily 失败时使用 DuckDuckGo 备选 |

#### 4.5 S3/MinIO 存储配置

Railway 上建议使用 **AWS S3** 或 **Cloudflare R2** 替代本地 MinIO。

**使用 AWS S3：**
| Variable Name | Value | 说明 |
|--------------|-------|------|
| `S3_ENDPOINT_URL` | `https://s3.amazonaws.com` | AWS S3 端点 |
| `S3_ACCESS_KEY_ID` | `AKIA...` | AWS Access Key |
| `S3_SECRET_ACCESS_KEY` | `...` | AWS Secret Key |
| `S3_BUCKET_NAME` | `roadmap-content` | Bucket 名称（需提前创建） |
| `S3_REGION` | `us-east-1` | AWS 区域 |

**使用 Cloudflare R2：**
| Variable Name | Value | 说明 |
|--------------|-------|------|
| `S3_ENDPOINT_URL` | `https://<accountid>.r2.cloudflarestorage.com` | R2 端点 |
| `S3_ACCESS_KEY_ID` | `...` | R2 Access Key |
| `S3_SECRET_ACCESS_KEY` | `...` | R2 Secret Key |
| `S3_BUCKET_NAME` | `roadmap-content` | Bucket 名称 |
| `S3_REGION` | `auto` | R2 不需要 region |

#### 4.6 JWT 认证配置

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `JWT_SECRET_KEY` | `<随机生成的长字符串>` | JWT 签名密钥（至少 32 字符） |
| `JWT_ALGORITHM` | `HS256` | 加密算法（默认值，可省略） |
| `JWT_LIFETIME_SECONDS` | `86400` | Token 有效期（24小时，可省略） |

**生成 JWT_SECRET_KEY**：
```bash
# 使用 OpenSSL 生成随机字符串
openssl rand -base64 48
```

#### 4.7 邮件服务配置（可选）

用于邀请邮件功能，使用 Resend。

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `RESEND_API_KEY` | `re_...` | Resend API Key |
| `RESEND_FROM_EMAIL` | `noreply@yourdomain.com` | 发件人邮箱 |
| `FRONTEND_URL` | `https://your-frontend.up.railway.app` | 前端 URL（用于邮件链接） |

#### 4.8 工作流控制（可选）

| Variable Name | Value | 说明 |
|--------------|-------|------|
| `SKIP_STRUCTURE_VALIDATION` | `false` | 是否跳过结构验证 |
| `SKIP_HUMAN_REVIEW` | `false` | 是否跳过人工审核 |
| `SKIP_TUTORIAL_GENERATION` | `false` | 是否跳过教程生成 |
| `MAX_FRAMEWORK_RETRY` | `3` | 验证最大重试次数 |
| `PARALLEL_TUTORIAL_LIMIT` | `10` | 并发教程生成数量 |

### 第五步：部署与验证

#### 5.1 触发部署

完成环境变量配置后，Railway 会自动触发部署。如果没有：
1. 进入 **Deployments** 标签页
2. 点击 **"Deploy Now"**

#### 5.2 查看部署日志

1. 点击最新的 Deployment
2. 查看 **Build Logs** 和 **Deploy Logs**
3. 成功标志：
   ```
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Running upgrade ... -> ...
   INFO:     Uvicorn running on http://0.0.0.0:xxxx
   INFO:     Application startup complete.
   ```

#### 5.3 生成公网域名

1. 进入 **Settings** -> **Networking**
2. 点击 **"Generate Domain"**
3. 你会获得一个类似 `roadmap-backend-production.up.railway.app` 的 URL

#### 5.4 测试 API

```bash
# 健康检查
curl https://your-backend-url.up.railway.app/health

# 预期返回
{"status":"ok"}
```

---

## 常见问题排查

### 1. 数据库连接失败

**症状**：日志中出现 `could not connect to server`

**解决方法**：
- 检查 `POSTGRES_HOST` 等变量是否正确引用了 `${{Postgres.PGHOST}}`
- 确保 Backend 服务和 Postgres 服务在同一个 Project 内
- 在 Postgres 服务的 **Variables** 中检查变量是否存在

### 2. Port binding 错误

**症状**：`OSError: [Errno 98] Address already in use`

**解决方法**：
- 确认 Dockerfile 中的 CMD 使用了 `${PORT:-8000}` 动态端口
- Railway 会自动设置 `PORT` 环境变量

### 3. Alembic 迁移失败

**症状**：日志中出现 `alembic: command not found` 或 `could not locate a Flask/SQLAlchemy application`

**解决方法**：
- 确认 `alembic/` 目录和 `alembic.ini` 已通过 Dockerfile 复制到镜像中
- 检查 `pyproject.toml` 中是否包含 `alembic>=1.13.0` 依赖

### 4. CORS 错误

**症状**：前端请求后端时浏览器控制台报 `CORS policy blocked`

**解决方法**：
- 检查 `CORS_ORIGINS` 是否包含前端的实际域名
- 确保格式为 JSON 数组字符串：`["https://frontend.up.railway.app"]`
- 重新部署后端服务

### 5. S3/MinIO 连接超时

**症状**：教程生成失败，日志中出现 `ConnectionError` 或 `ReadTimeout`

**解决方法**：
- Railway 上不建议使用自托管的 MinIO（网络隔离问题）
- 改用 AWS S3、Cloudflare R2 或 Backblaze B2
- 确保 `S3_ENDPOINT_URL` 使用公网可访问的 HTTPS 地址

---

## 成本估算（Railway Free Plan）

Railway 提供以下免费额度：
- **$5/月** 的免费使用额度
- **512 MB** RAM 限制（单服务）
- **1 GB** Disk 限制

**预估成本**（轻度使用）：
- Backend (Web Service): ~$2-3/月
- PostgreSQL: ~$2/月
- Redis: ~$1/月

**总计**：~$5/月（恰好在免费额度内）

**升级建议**：
- 正式上线建议升级到 **Hobby Plan** ($5/月起)
- 或按需付费（$0.000231/GB-second）

---

## 后续优化

### 1. 添加自定义域名

1. 购买域名（如 Cloudflare、Namecheap）
2. 在 Railway **Settings** -> **Networking** 中添加 Custom Domain
3. 按提示配置 DNS CNAME 记录

### 2. 配置环境隔离

建议为不同环境创建独立的 Railway 项目：
- `roadmap-staging`（测试环境）
- `roadmap-production`（生产环境）

### 3. 监控与日志

- **内置监控**：Railway Dashboard 提供 CPU、内存、网络监控
- **日志聚合**：考虑集成 Sentry（错误追踪）或 Logtail（日志管理）

### 4. 数据库备份

Railway PostgreSQL 提供自动快照功能：
- **Free Plan**：不保证备份
- **Hobby Plan**：每日自动备份，保留 7 天

生产环境建议：
- 使用 Railway 的 **Database Snapshots**
- 或定期导出数据到 S3（`pg_dump`）

---

## 参考资源

- [Railway 官方文档](https://docs.railway.app/)
- [Railway PostgreSQL 配置](https://docs.railway.app/databases/postgresql)
- [Railway Redis 配置](https://docs.railway.app/databases/redis)
- [Railway 环境变量引用语法](https://docs.railway.app/develop/variables#referencing-another-services-variable)

---

## 部署检查清单

完成以下检查清单以确保部署成功：

- [ ] 已将代码推送到 GitHub
- [ ] Railway 项目已创建并连接到仓库
- [ ] Backend 服务的 Root Directory 设置为 `/backend`
- [ ] PostgreSQL 数据库已添加
- [ ] Redis 数据库已添加
- [ ] 所有必需的环境变量已配置
- [ ] 数据库连接变量正确引用了 `${{Postgres.*}}`
- [ ] CORS_ORIGINS 包含前端域名
- [ ] JWT_SECRET_KEY 已生成并配置
- [ ] 部署成功且服务运行正常
- [ ] 公网域名已生成
- [ ] API 健康检查通过
- [ ] 前端已更新 API 地址指向 Railway 域名

---

## 需要帮助？

如果遇到问题：
1. 检查 Railway 的 **Deploy Logs**
2. 参考本文档的 **常见问题排查** 部分
3. 访问 [Railway Discord 社区](https://discord.gg/railway)
4. 提交 GitHub Issue

---

**Last Updated**: 2025-12-24
**Author**: Roadmap Agent Team

