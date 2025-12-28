# 个性化学习路线图生成系统 - 后端

基于 Multi-Agent 架构的个性化学习路线图生成系统后端服务。

## 🚀 技术栈

- **Python**: 3.12+
- **Web 框架**: FastAPI
- **Agent 编排**: LangGraph
- **LLM 接口**: LiteLLM
- **ORM**: SQLModel / SQLAlchemy
- **数据库**: PostgreSQL 15+
- **状态持久化**: AsyncPostgresSaver (LangGraph 官方)
- **对象存储**: MinIO / S3 兼容存储 (通过 aioboto3)
- **消息队列**: Redis
- **异步任务**: Celery（日志队列处理）
- **任务监控**: Flower

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              状态机工作流                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  START → A1(需求分析师) → A2(课程架构师) → A3(结构审查员)                     │
│                                              ↓                              │
│                                         [验证通过?]                          │
│                                         ↓       ↓                           │
│                                       是       否 → A2E(路线图编辑师) ─┐     │
│                                         ↓                              │     │
│                                    HUMAN_REVIEW ←──────────────────────┘     │
│                                         ↓                                    │
│                                    [审核通过?]                               │
│                                    ↓       ↓                                │
│                                  是       否 → 返回 A2E                      │
│                                    ↓                                        │
│                             A4(教程生成器) → END                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent 角色

| 角色 | 代号 | 职责 |
|------|------|------|
| 需求分析师 | A1 | 解析用户学习需求，提取关键技术栈和学习目标 |
| 课程架构师 | A2 | 设计三层学习路线图框架（Stage → Module → Concept） |
| 路线图编辑师 | A2E | 根据验证反馈修改路线图结构 |
| 结构审查员 | A3 | 验证路线图的合理性、完整性和学习路径 |
| 教程生成器 | A4 | 为每个知识点生成详细教程内容 |

### 工具

| 工具 | 用途 |
|------|------|
| Web Search | 搜索最新技术资料和学习资源（Tavily API） |
| S3 Storage | 存储和下载教程内容（MinIO / S3 兼容存储） |

**S3 Storage 功能：**
- ✅ 异步上传/下载
- ✅ 自动重试机制
- ✅ 支持预签名 URL
- ✅ 启动时自动创建 bucket
- 📖 详细文档：[S3 下载功能使用指南](docs/s3_download_usage.md)

## 📋 项目结构

```
backend/
├── app/                    # 主应用代码
│   ├── config/            # 配置管理
│   ├── api/               # API 路由层
│   ├── core/              # 核心引擎
│   │   ├── orchestrator.py    # LangGraph 状态机编排器
│   │   ├── checkpointers/     # 状态持久化
│   │   └── tool_registry.py   # 工具注册中心
│   ├── agents/            # Agent 实现（5个）
│   │   ├── intent_analyzer.py      # A1
│   │   ├── curriculum_architect.py # A2
│   │   ├── roadmap_editor.py       # A2E
│   │   ├── structure_validator.py  # A3
│   │   └── tutorial_generator.py   # A4
│   ├── tools/             # 工具实现
│   │   ├── search/        # Web 搜索工具
│   │   └── storage/       # S3 存储工具
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑层
│   ├── db/                # 数据库操作
│   └── utils/             # 工具函数
├── prompts/               # Prompt 模板（Jinja2）
├── tests/                 # 测试套件
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── e2e/               # 端到端测试
├── alembic/               # 数据库迁移
└── scripts/               # 运维脚本
```

## 🛠️ 快速开始

### 前置要求

- **Python**: 3.12 或更高版本
- **包管理工具**: 推荐使用 **uv**（更快）或 **Poetry**（传统选择）
- **Docker & Docker Compose**: 用于本地开发环境（PostgreSQL、Redis）
- **Redis**: 用于 Celery 消息队列（可通过 Docker 启动）

### 步骤 1: 检查 Python 版本

```bash
# 检查 Python 版本（需要 3.12+）
python3 --version

# 如果版本低于 3.12，请升级 Python
# macOS: brew install python@3.12
# Ubuntu: sudo apt install python3.12
```

### 步骤 2: 安装包管理工具

**方式 1: 使用 uv（推荐，速度更快）**

```bash
# 安装 uv（macOS/Linux）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 验证安装
uv --version
```

**方式 2: 使用 Poetry（传统方式）**

```bash
# 使用官方安装脚本（推荐）
curl -sSL https://install.python-poetry.org | python3 -

# 验证安装
poetry --version
```

### 步骤 3: 克隆项目并进入目录

```bash
cd roadmap-agent/backend
```

### 步骤 4: 安装项目依赖

**使用 uv（推荐）**

```bash
# ⚠️ 重要: 必须安装开发依赖才能运行测试！
uv sync --extra dev

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux

# 验证依赖安装成功
uv pip list | grep pytest
```

**使用 Poetry**

```bash
poetry install
```

### 步骤 5: 配置环境变量

```bash
# 如果 .env 文件不存在，从模板复制
cp .env.example .env

# 编辑 .env 文件
vim .env
```

**必须配置的环境变量**：

```bash
# ==================== LLM API Keys（必需）====================
# A1: Intent Analyzer (需求分析师)
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=gpt-4o-mini
ANALYZER_BASE_URL=  # 可选，用于自定义端点
ANALYZER_API_KEY=sk-your-openai-api-key-here

# A2: Curriculum Architect (课程架构师)
ARCHITECT_PROVIDER=anthropic
ARCHITECT_MODEL=claude-3-5-sonnet-20241022
ARCHITECT_BASE_URL=  # 可选
ARCHITECT_API_KEY=sk-ant-your-anthropic-api-key-here

# A3: Structure Validator (结构审查员)
VALIDATOR_PROVIDER=openai
VALIDATOR_MODEL=gpt-4o-mini
VALIDATOR_BASE_URL=  # 可选
VALIDATOR_API_KEY=sk-your-openai-api-key-here

# A2E: Roadmap Editor (路线图编辑师)
EDITOR_PROVIDER=anthropic
EDITOR_MODEL=claude-3-5-sonnet-20241022
EDITOR_BASE_URL=  # 可选
EDITOR_API_KEY=sk-ant-your-anthropic-api-key-here

# A4: Tutorial Generator (教程生成器)
GENERATOR_PROVIDER=anthropic
GENERATOR_MODEL=claude-3-5-sonnet-20241022
GENERATOR_BASE_URL=  # 可选
GENERATOR_API_KEY=sk-ant-your-anthropic-api-key-here

# ==================== External Services（必需）====================
# Tavily API（用于 Web 搜索）
TAVILY_API_KEY=your-tavily-api-key-here

# ==================== Database（开发环境默认值）====================
# PostgreSQL（同时用于业务数据和 Checkpointer 状态持久化）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=roadmap_user
POSTGRES_PASSWORD=roadmap_pass
POSTGRES_DB=roadmap_db

# ==================== MinIO / S3 存储（教程内容存储）====================
S3_ENDPOINT_URL=http://localhost:9000  # MinIO 端点
S3_ACCESS_KEY_ID=minioadmin            # MinIO 访问密钥
S3_SECRET_ACCESS_KEY=minioadmin123     # MinIO 密钥
S3_BUCKET_NAME=roadmap-content         # Bucket 名称（启动时自动创建）
S3_REGION=                             # MinIO 不需要 region，留空即可

# ==================== 工作流控制（可选）====================
SKIP_STRUCTURE_VALIDATION=false  # 跳过结构验证
SKIP_HUMAN_REVIEW=false          # 跳过人工审核
SKIP_TUTORIAL_GENERATION=false   # 跳过教程生成

# ==================== 业务配置（可选）====================
MAX_FRAMEWORK_RETRY=3            # 路线图验证最大重试次数
HUMAN_REVIEW_TIMEOUT_HOURS=24    # 人工审核超时时间
PARALLEL_TUTORIAL_LIMIT=10       # 并发生成教程数量
```

**获取 API 密钥**：
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Tavily**: https://tavily.com/

### 步骤 6: 启动数据库和 Redis 服务

```bash
# 使用 Docker Compose 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 检查服务状态
docker-compose ps

# 检查 PostgreSQL 是否就绪
docker-compose exec postgres pg_isready -U roadmap_user

# 检查 Redis 是否就绪
docker-compose exec redis redis-cli ping
```

### 步骤 7: 初始化数据库

```bash
# 运行数据库初始化脚本
uv run python scripts/init_db.py

# 或使用 Alembic 迁移（推荐生产环境）
uv run alembic upgrade head
```

### 步骤 8: 启动开发服务器

**方式 1: 使用快速启动脚本（推荐）**

```bash
./scripts/start_dev.sh
```

**方式 2: 手动启动**

```bash
# 使用 uv 运行
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动成功标志**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 步骤 9: 启动 Celery Worker（必需，用于日志处理）

**在新终端中启动 Celery Worker**：

```bash
cd backend
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=logs \
    --concurrency=4 \
    --hostname=logs@%h \
    --max-tasks-per-child=1000
```

或使用启动脚本：

```bash
./scripts/start_celery_worker.sh
```

**启动成功标志**：
```
-------------- logs@yourhostname v5.6.0 (recovery)
--- ***** ----- 
-- ******* ---- macOS-15.2-arm64-arm-64bit
...
[INFO/MainProcess] logs@yourhostname ready.
```

### 步骤 10: 启动 Flower 监控（可选，推荐）

**在新终端中启动 Flower**：

```bash
cd backend
uv run celery -A app.core.celery_app flower --port=5555
```

或使用启动脚本：

```bash
./scripts/start_flower.sh
```

然后访问 **http://localhost:5555** 查看 Celery 任务监控界面。

### 步骤 11: 验证安装

- **API 文档 (Swagger UI)**: http://localhost:8000/api/docs
- **API 文档 (ReDoc)**: http://localhost:8000/api/redoc
- **健康检查**: http://localhost:8000/health
- **Celery 监控 (Flower)**: http://localhost:5555

## 🔄 Celery 异步日志队列

### 概述

本项目使用 Celery 作为异步任务队列，处理所有执行日志的数据库写入操作。这样可以：

- ✅ **完全解耦**：日志写入不占用主应用数据库连接池
- ✅ **高性能**：批量处理日志，减少数据库操作
- ✅ **可扩展**：可以启动多个 Celery Worker 处理日志
- ✅ **可靠性**：支持任务重试和故障恢复

### 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 应用进程                           │
│                                                               │
│  所有工作流节点 → ExecutionLogger → 本地缓冲区 → Celery 任务  │
│                                                      ↓        │
└──────────────────────────────────────────────────────┼────────┘
                                                       ↓
                                              ┌────────────────┐
                                              │  Redis Broker  │
                                              └────────┬───────┘
                                                       ↓
┌─────────────────────────────────────────────────────┴────────┐
│                  Celery Worker 进程                           │
│                                                               │
│  批量收集日志 → 批量写入数据库 → 独立数据库连接池             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 启动服务

**完整启动流程**：

```bash
# 1. 启动 Redis（如果使用 Docker）
docker-compose up -d redis

# 2. 启动 FastAPI 应用
uv run uvicorn app.main:app --workers 4 --reload --host 0.0.0.0 --port 8000

# 3. 启动 Celery Worker（新终端）
# logs worker
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=logs \
    --concurrency=4 \
    --pool=prefork \
    --hostname=logs@%h \
    --max-tasks-per-child=500

# content worker
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=content_generation \
    --concurrency=2 \
    --pool=prefork \
    --hostname=content@%h \
    --max-tasks-per-child=50
# 4. 启动 Flower 监控（可选，新终端）
celery -A app.core.celery_app flower --port=5555
```

**使用 Docker Compose 一键启动**：

```bash
docker-compose up -d
```

这将启动所有服务：
- FastAPI 应用（端口 8000）
- PostgreSQL（端口 5432）
- Redis（端口 6379）
- Celery Worker（后台运行）
- Flower 监控（端口 5555）

### 监控和调试

**查看 Celery Worker 状态**：

```bash
celery -A app.core.celery_app inspect active
```

**查看队列状态**（需要 redis-cli）：

```bash
redis-cli
> LLEN logs  # 查看队列长度
```

**使用 Flower 监控界面**：

访问 http://localhost:5555 查看：
- 任务执行状态和历史
- Worker 状态和统计
- 任务详情和错误信息

### 配置说明

主要配置项在 `app/core/celery_app.py` 中：

```python
# 本地缓冲区配置（ExecutionLogger）
buffer_size = 50        # 达到 50 条日志时发送
flush_interval = 2.0    # 超过 2 秒时发送

# Worker 配置
concurrency = 4         # 并发工作进程数
max_tasks_per_child = 1000  # 每个进程最多处理 1000 个任务后重启
```

### 详细文档

更多信息请参考：
- **设置指南**：[docs/CELERY_SETUP.md](docs/CELERY_SETUP.md)
- **重构摘要**：[docs/CELERY_REFACTOR_SUMMARY.md](docs/CELERY_REFACTOR_SUMMARY.md)

## 🧪 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行单元测试（无外部依赖）
uv run pytest tests/unit/

# 运行集成测试（需要 Mock LLM）
uv run pytest tests/integration/

# 运行端到端测试
uv run pytest tests/e2e/

# 测试 Celery 日志功能（需要 Redis 和 Celery Worker）
uv run pytest tests/unit/test_execution_logger_celery.py -v
uv run pytest tests/integration/test_celery_log_integration.py -v -m integration

# 带详细输出
uv run pytest -v

# 生成覆盖率报告
uv run pytest --cov=app --cov-report=html
```

### 测试结构

```
tests/
├── conftest.py              # 共享 fixtures
├── unit/
│   ├── test_models.py       # 领域模型单元测试 (25 个)
│   └── test_execution_logger_celery.py  # ExecutionLogger Celery 版本测试
├── integration/
│   ├── test_intent_analyzer.py       # A1 集成测试
│   ├── test_curriculum_architect.py  # A2 集成测试
│   ├── test_roadmap_editor.py        # A2E 集成测试
│   ├── test_structure_validator.py   # A3 集成测试
│   ├── test_tutorial_generator.py    # A4 集成测试
│   ├── test_checkpointer.py          # AsyncPostgresSaver 测试
│   └── test_celery_log_integration.py  # Celery 日志集成测试
└── e2e/
    └── test_workflow.py     # 完整工作流测试
```

## 🚀 生产环境部署

### Railway 多服务部署（推荐）

引入 Celery 后，系统需要运行多个服务：
- **API 服务**：FastAPI 应用
- **Celery Worker (Logs)**：处理执行日志队列
- **Celery Worker (Content)**：处理内容生成队列

Railway 支持在同一个项目中部署多个服务，共享环境变量和基础设施。

#### 快速部署指南

1. **准备基础设施**
   - PostgreSQL 数据库（Railway 插件）
   - Redis（Upstash Redis 插件）

2. **创建三个服务**

**服务 1：API Service**
```yaml
Name: roadmap-api
Dockerfile: backend/Dockerfile.railway
Root Directory: backend
Environment Variables:
  SERVICE_TYPE: api
  PORT: 8000
  UVICORN_WORKERS: 4
  DATABASE_URL: ${{Postgres.DATABASE_URL}}
  REDIS_URL: ${{Redis.REDIS_URL}}
  JWT_SECRET_KEY: your-secret-key
  OPENAI_API_KEY: your-api-key
```

**服务 2：Celery Worker (Logs)**
```yaml
Name: roadmap-celery-logs
Dockerfile: backend/Dockerfile.railway
Root Directory: backend
Environment Variables:
  SERVICE_TYPE: celery_logs
  CELERY_LOGS_CONCURRENCY: 2
  DATABASE_URL: ${{Postgres.DATABASE_URL}}
  REDIS_URL: ${{Redis.REDIS_URL}}
```

**服务 3：Celery Worker (Content)**
```yaml
Name: roadmap-celery-content
Dockerfile: backend/Dockerfile.railway
Root Directory: backend
Environment Variables:
  SERVICE_TYPE: celery_content
  CELERY_CONTENT_CONCURRENCY: 2
  DATABASE_URL: ${{Postgres.DATABASE_URL}}
  REDIS_URL: ${{Redis.REDIS_URL}}
  OPENAI_API_KEY: ${{roadmap-api.OPENAI_API_KEY}}
```

3. **验证部署**
```bash
# 检查 API 服务
curl https://your-railway-url.railway.app/health

# 查看 Railway Dashboard 日志，确认 Workers 已启动
```

#### 详细部署文档

完整的 Railway 部署指南（包括故障排查）请参考：
- **Railway 部署指南**：[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- **Docker Compose 配置**：[docker-compose.yml](docker-compose.yml)

### Docker 部署（本地/自托管）

使用 Docker Compose 一键启动所有服务：

```bash
cd backend
docker-compose up -d
```

这将启动：
- FastAPI 应用（端口 8000）
- PostgreSQL（端口 5432）
- Redis（端口 6379）
- Celery Worker (Logs)
- Celery Worker (Content)
- Flower 监控（端口 5555）

### 环境变量配置

生产环境必需的环境变量：

```env
# 数据库配置
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis 配置
REDIS_URL=redis://localhost:6379/0
# 或使用 Upstash Redis（TLS）
REDIS_URL=rediss://default:your-password@host:6379

# JWT 配置
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# OpenAI 配置
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# 应用配置
ENVIRONMENT=production
DEBUG=false
```

生成安全的 JWT 密钥：
```bash
./scripts/generate_jwt_secret.sh
```

## 🏗️ 开发工作流

### 代码格式化

```bash
# 使用 Black 格式化代码
uv run black app/ tests/

# 使用 Ruff 进行 linting
uv run ruff check app/ tests/

# 自动修复可修复的问题
uv run ruff check --fix app/ tests/
```

### 类型检查

```bash
uv run mypy app/
```

### 数据库迁移

```bash
# 创建新的迁移
uv run alembic revision --autogenerate -m "描述信息"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1
```

## 🐳 Docker 部署

### 构建镜像

```bash
docker build -t roadmap-backend:latest .
```

### 运行容器

```bash
docker run -d \
  --name roadmap-backend \
  -p 8000:8000 \
  --env-file .env \
  roadmap-backend:latest
```

## 🔧 配置说明

主要配置项位于 `.env` 文件中，包括：

- **应用配置**: 环境、调试模式、CORS 设置
- **数据库配置**: PostgreSQL 连接信息（业务数据 + Checkpointer）
- **LLM 配置**: 5 个 Agent 使用的模型和 API 密钥
- **外部服务**: Tavily API（Web 搜索）、MinIO/S3 存储配置
- **工作流控制**: 跳过可选节点的开关
- **观测性**: OpenTelemetry 配置

## 📖 常见问题排查

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 检查端口是否被占用
lsof -i :5432

# 重启数据库服务
docker-compose restart postgres
```

### Redis 连接失败

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试 Redis 连接
redis-cli ping

# 重启 Redis 服务
docker-compose restart redis
```

### Celery Worker 无法启动

```bash
# 检查 Redis 是否可访问
redis-cli ping

# 检查 Celery 配置
uv run python -c "from app.core.celery_app import celery_app; print(celery_app.conf.broker_url)"

# 查看详细错误日志
uv run celery -A app.core.celery_app worker --loglevel=debug

# 清空 Redis 队列（如果任务堆积）
redis-cli
> DEL logs
```

### 日志未写入数据库

**问题排查步骤**：

1. **检查 Celery Worker 是否运行**：
   ```bash
   celery -A app.core.celery_app inspect active
   ```

2. **检查队列中的任务**：
   ```bash
   redis-cli
   > LLEN logs
   ```

3. **查看 Flower 监控**：
   访问 http://localhost:5555 查看任务状态

4. **手动刷新日志缓冲区**（在代码中）：
   ```python
   from app.services.execution_logger import execution_logger
   await execution_logger.flush()
   ```

### 端口 8000 已被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 使用其他端口启动
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 依赖安装失败

```bash
# 删除虚拟环境重新安装
rm -rf .venv
uv sync --extra dev
```

---

**重要更新**：
- ✅ **v2.1.0** (2025-12-27): 引入 Celery 异步日志队列，解决数据库连接池耗尽问题
- 📖 **v2.0.0** (2025-11-27): 初始版本

**文档版本**: v2.1.0  
**最后更新**: 2025-12-27
