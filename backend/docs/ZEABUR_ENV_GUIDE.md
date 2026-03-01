# Zeabur 环境变量配置指南

后端在 Zeabur 上分为三个服务部署时的环境变量配置说明。

## 服务架构

| 服务 | 职责 | 启动命令/队列 |
|------|------|----------------|
| **FastAPI 主应用** | HTTP API、WebSocket、健康检查 | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Celery 默认队列** | 路线图生成、工作流恢复、封面图、日志、维护任务 | `celery -A app.core.celery_app worker --queues=celery` |
| **Celery 内容生成队列** | 教程/资源/测验生成、单 Concept 重新生成 | `celery -A app.core.celery_app worker --queues=content_generation` |

---

## 一、三个服务共用（必须相同）

以下变量在三个服务中**必须保持一致**：

### 数据库（Zeabur 绑定了 PostgreSQL 后通常自动注入）

```
DATABASE_URL=postgresql+asyncpg://用户:密码@主机:5432/数据库名
# 或分拆为：
POSTGRES_HOST=xxx.zeabur.com
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=xxx
POSTGRES_DB=roadmap_db
```

### Redis（Zeabur 绑定了 Redis 后通常自动注入）

```
REDIS_URL=redis://default:密码@主机:6379/0
# 或 Upstash 风格（TLS）：
REDIS_URL=rediss://default:密码@xxx.upstash.io:6379
```

### S3/R2 对象存储

```
S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=xxx
S3_SECRET_ACCESS_KEY=xxx
S3_BUCKET_NAME=roadmap-content
S3_REGION=auto
```

### LLM API 密钥（所有 Agent 共用）

```
# A1 意图分析师
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=gpt-4o-mini
ANALYZER_API_KEY=sk-xxx

# A2 课程架构师
ARCHITECT_PROVIDER=anthropic
ARCHITECT_MODEL=claude-3-5-sonnet-20241022
ARCHITECT_API_KEY=sk-ant-xxx

# A3 结构验证器
VALIDATOR_PROVIDER=openai
VALIDATOR_MODEL=gpt-4o-mini
VALIDATOR_API_KEY=sk-xxx

# 路线图编辑师
EDITOR_PROVIDER=anthropic
EDITOR_MODEL=claude-3-5-sonnet-20241022
EDITOR_API_KEY=sk-ant-xxx

# A4 教程生成器（内容生成队列主要使用）
GENERATOR_PROVIDER=anthropic
GENERATOR_MODEL=claude-3-5-sonnet-20241022
GENERATOR_API_KEY=sk-ant-xxx

# A5 资源推荐师
RECOMMENDER_PROVIDER=openai
RECOMMENDER_MODEL=gpt-4o-mini
RECOMMENDER_API_KEY=sk-xxx

# A6 测验生成器
QUIZ_PROVIDER=openai
QUIZ_MODEL=gpt-4o-mini
QUIZ_API_KEY=sk-xxx
```

### 外部服务

```
TAVILY_API_KEY=tvly-xxx
TAVILY_RATE_LIMIT_PER_MINUTE=100
```

### 安全与业务

```
JWT_SECRET_KEY=生产环境强密钥
ENVIRONMENT=production
```

---

## 二、仅 FastAPI 主应用需要

| 变量 | 说明 | 示例 |
|------|------|------|
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔） | `https://your-app.vercel.app,https://yourdomain.com` |
| `FRONTEND_URL` | 前端 URL（邮件链接等） | `https://your-app.vercel.app` |
| `RESEND_API_KEY` | Resend 发信密钥（可选） | `re_xxx` |
| `RESEND_FROM_EMAIL` | 发件人邮箱 | `noreply@yourdomain.com` |
| `PORT` | 端口（Zeabur 通常自动注入） | 8000 |

---

## 三、服务差异化配置（可选）

### Celery Worker 可选调优

| 变量 | 默认 | 说明 |
|------|------|------|
| `CELERY_CONCURRENCY` | 4 | 并发数，内容生成队列可设 6-8 |
| `CELERY_LOG_LEVEL` | info | 日志级别 |

### 数据库连接池（多 Worker 时注意总连接数）

生产环境默认：`DB_POOL_SIZE=7`，`DB_MAX_OVERFLOW=3`。若 Zeabur 数据库连接数有限，可适当减小。

---

## 四、Zeabur 部署步骤摘要

1. **创建项目**：从 GitHub 导入 `roadmap-agent` 仓库。
2. **添加数据服务**：PostgreSQL、Redis（Zeabur 会自动注入 `DATABASE_URL`、`REDIS_URL`）。
3. **拆分服务**：
   - 服务 1：识别为 Web 服务，使用 `uvicorn` 启动（Zeabur 通常自动识别）。
   - 服务 2：新建 Service，选择同一仓库，设置启动命令为 Celery 默认队列。
   - 服务 3：新建 Service，选择同一仓库，设置启动命令为 Celery 内容生成队列。
4. **环境变量**：在 Zeabur 项目/服务级别配置上述变量，三个服务共享数据库和 Redis 连接串。

---

## 五、推荐 Zeabur 启动命令

### FastAPI 主应用

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
```

### Celery 默认队列

```
celery -A app.core.celery_app worker --loglevel=info --concurrency=4 --queues=celery --max-tasks-per-child=500
```

### Celery 内容生成队列

```
celery -A app.core.celery_app worker --loglevel=info --concurrency=6 --queues=content_generation --max-tasks-per-child=100
```

---

## 六、环境变量总览（按优先级）

| 优先级 | 变量 | 服务 | 说明 |
|--------|------|------|------|
| 必填 | `DATABASE_URL` 或 `POSTGRES_*` | 全部 | 数据库连接 |
| 必填 | `REDIS_URL` | 全部 | Redis 连接 |
| 必填 | `JWT_SECRET_KEY` | 全部 | JWT 签名密钥 |
| 必填 | `ANALYZER_API_KEY`、`ARCHITECT_API_KEY` 等 | 全部 | 各 Agent 的 LLM API Key |
| 必填 | `S3_*` | 全部 | 对象存储 |
| 必填 | `CORS_ORIGINS`、`FRONTEND_URL` | 仅 FastAPI | 跨域与前端地址 |
| 推荐 | `TAVILY_API_KEY` | 全部 | 搜索增强 |
| 可选 | `RESEND_API_KEY` | 仅 FastAPI | 邀请邮件 |
| 可选 | `CELERY_CONCURRENCY` | Celery | 并发数 |
| 可选 | `ENVIRONMENT=production` | 全部 | 生产环境标识 |
