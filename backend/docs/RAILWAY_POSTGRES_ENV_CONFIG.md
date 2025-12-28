# Railway PostgreSQL 环境变量配置指南

## 📋 概述

当使用 Railway 自己的 PostgreSQL 数据库服务时，需要正确配置环境变量以连接数据库。Railway PostgreSQL 服务会自动提供一组环境变量，但应用代码需要特定的变量名格式。

---

## 🔍 Railway PostgreSQL 提供的变量

Railway PostgreSQL 服务会自动生成以下环境变量：

| Railway 变量名 | 说明 | 示例值 |
|---------------|------|--------|
| `PGHOST` | PostgreSQL 主机地址 | `containers-us-west-xxx.railway.app` |
| `PGPORT` | PostgreSQL 端口 | `5432` |
| `PGUSER` | 数据库用户名 | `postgres` |
| `PGPASSWORD` | 数据库密码 | `xxx` |
| `PGDATABASE` | 数据库名称 | `railway` |
| `DATABASE_URL` | 完整连接字符串 | `postgresql://user:pass@host:5432/dbname` |

**注意**：Railway 的服务名称默认为 `Postgres`，如果你的服务使用了自定义名称（如 `roadmap-db`），请替换下面示例中的 `Postgres`。

---

## ✅ 正确的配置方式

### 方式一：分别映射变量（推荐）

应用代码期望使用分别的 `POSTGRES_*` 变量，因此需要将 Railway 的变量映射到应用期望的格式：

```env
# 在 Railway Dashboard → Variables 中配置

# PostgreSQL 连接（引用 Railway PostgreSQL 服务）
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
```

**Railway 变量引用语法**：
- 使用 `${{ServiceName.VARIABLE}}` 格式
- `Postgres` 是 Railway PostgreSQL 服务的默认名称
- 如果你的服务名称不同，请替换为实际名称

### 方式二：使用 DATABASE_URL（不推荐）

虽然 Railway 提供了 `DATABASE_URL`，但应用代码目前**不支持**直接使用它。应用会从分别的 `POSTGRES_*` 变量构建自己的 `DATABASE_URL`。

如果未来需要支持 `DATABASE_URL`，需要修改 `backend/app/config/settings.py` 中的 `Settings` 类。

---

## 🎯 完整配置示例

### API 服务环境变量

```env
# 服务类型
SERVICE_TYPE=api

# 端口配置
PORT=8000
UVICORN_WORKERS=4

# PostgreSQL（引用 Railway PostgreSQL 服务）
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}

# Redis（引用 Railway Redis 或 Upstash Redis）
REDIS_URL=${{Redis.REDIS_URL}}
# 或者分别配置：
# REDIS_HOST=${{Redis.REDISHOST}}
# REDIS_PORT=${{Redis.REDISPORT}}
# REDIS_PASSWORD=${{Redis.REDISPASSWORD}}

# 应用配置
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=http://localhost:3000,https://your-frontend.up.railway.app

# LLM API Keys（必需）
ANALYZER_API_KEY=sk-your-openai-key
ARCHITECT_API_KEY=sk-ant-your-anthropic-key
VALIDATOR_API_KEY=sk-your-openai-key
EDITOR_API_KEY=sk-ant-your-anthropic-key
GENERATOR_API_KEY=sk-ant-your-anthropic-key
RECOMMENDER_API_KEY=sk-your-openai-key
QUIZ_API_KEY=sk-your-openai-key

# Web Search
TAVILY_API_KEY=tvly-your-key

# S3 存储
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=roadmap-content
S3_REGION=us-east-1

# JWT 认证
JWT_SECRET_KEY=<生成一个至少32字符的随机字符串>
JWT_ALGORITHM=HS256
JWT_LIFETIME_SECONDS=86400
```

### Celery Worker 服务环境变量

```env
# 服务类型
SERVICE_TYPE=celery_logs  # 或 celery_content

# Worker 配置
CELERY_LOGS_CONCURRENCY=2
CELERY_CONTENT_CONCURRENCY=2
CELERY_LOG_LEVEL=info

# PostgreSQL（引用 Railway PostgreSQL 服务）
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}

# Redis（引用 Railway Redis 或 Upstash Redis）
REDIS_URL=${{Redis.REDIS_URL}}

# 应用配置
ENVIRONMENT=production
DEBUG=false

# 共享的 API Keys（从 API 服务引用）
ANALYZER_API_KEY=${{roadmap-api.ANALYZER_API_KEY}}
ARCHITECT_API_KEY=${{roadmap-api.ARCHITECT_API_KEY}}
# ... 其他 API Keys
```

---

## ⚠️ 常见问题

### Q1: 如果 PostgreSQL 服务名称不是 `Postgres` 怎么办？

**A**: 替换变量引用中的服务名称。例如，如果你的服务名称是 `roadmap-db`：

```env
POSTGRES_HOST=${{roadmap-db.PGHOST}}
POSTGRES_PORT=${{roadmap-db.PGPORT}}
POSTGRES_USER=${{roadmap-db.PGUSER}}
POSTGRES_PASSWORD=${{roadmap-db.PGPASSWORD}}
POSTGRES_DB=${{roadmap-db.PGDATABASE}}
```

### Q2: 可以直接使用 `DATABASE_URL` 吗？

**A**: 目前**不支持**。应用代码需要分别的 `POSTGRES_*` 变量来构建连接 URL。如果未来需要支持，需要修改 `backend/app/config/settings.py`。

### Q3: 如何查看 Railway PostgreSQL 服务的实际变量名？

**A**: 
1. 在 Railway Dashboard 中点击 PostgreSQL 服务
2. 进入 **Variables** 标签页
3. 查看所有可用的环境变量
4. 注意服务名称（显示在服务卡片上）

### Q4: 多个服务如何共享数据库配置？

**A**: 在每个服务的 **Variables** 中都添加相同的引用：

```env
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
```

Railway 会自动解析这些引用，所有服务都会连接到同一个数据库。

---

## 📚 相关文档

- **Railway 部署指南**: [QUICK_START_RAILWAY.md](../QUICK_START_RAILWAY.md)
- **环境变量模板**: [doc/RAILWAY_ENV_TEMPLATE.txt](../../doc/RAILWAY_ENV_TEMPLATE.txt)
- **配置类定义**: [app/config/settings.py](../app/config/settings.py)

---

## 🔧 验证配置

部署后，可以通过以下方式验证数据库连接：

1. **查看服务日志**：
   ```
   Railway Dashboard → 服务 → Deployments → 查看最新部署的日志
   ```

2. **检查健康检查端点**：
   ```bash
   curl https://your-api.railway.app/health
   ```

3. **查看数据库连接池状态**：
   应用启动时会输出数据库连接信息，检查日志中是否有连接错误。

