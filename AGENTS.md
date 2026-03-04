# AGENTS.md

Roadmap Agent — 基于多 Agent 协作的个性化学习路线图生成系统。

## 项目结构

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI + LangGraph + Celery 后端（Python 3.12, uv） |
| `frontend-next/` | Next.js 14 + TypeScript 前端（npm） |
| `prompts/` | Jinja2 Prompt 模板 |
| `Makefile` | 统一开发命令入口 |

## 快速参考

- **后端开发命令**: 参见 `Makefile` 中的 `dev-backend`, `test`, `lint`, `format` 等 targets
- **前端开发命令**: 参见 `frontend-next/AGENTS.md`
- **数据库迁移**: `cd backend && uv run alembic upgrade head`

## Cursor Cloud specific instructions

### 基础设施

用户已通过 Secrets 注入远程 PostgreSQL、Redis 及 LLM API Keys 等环境变量，**不需要**在本地启动 Docker 容器来运行 PostgreSQL 或 Redis。这些 Secrets 会覆盖 `backend/.env` 中的默认值。

### 启动服务

```bash
# 后端（端口 8000）
cd /workspace/backend && uv run uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# 前端（端口 3000）
cd /workspace/frontend-next && npm run dev
```

### 数据库表初始化

Alembic 迁移假设表已存在（首次迁移为 ALTER 而非 CREATE）。若为全新数据库，需先通过 SQLModel 创建表：

```bash
cd /workspace/backend && uv run python -c "
import asyncio
from app.db.session import engine
from sqlmodel import SQLModel
from app.models.database import *

async def create_all():
    async with engine.begin() as conn:
        from app.models.database import Base
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SQLModel.metadata.create_all)

asyncio.run(create_all())
"
```

然后运行 `cd /workspace/backend && uv run alembic stamp head` 标记为最新。

### Lint / Test

```bash
# 后端 lint（有约 200 个预存 ruff 告警，均为代码库已有问题）
cd /workspace/backend && uv run ruff check app

# 前端 lint（需要 .eslintrc.json，若不存在需创建 {"extends":"next/core-web-vitals"}）
cd /workspace/frontend-next && npm run lint

# 后端测试（跳过 e2e 和 agent 测试，这些需要 LLM API 调用）
cd /workspace/backend && uv run pytest tests/unit/ -q

# 前端测试
cd /workspace/frontend-next && npm run test:run
```

### 注意事项

- 前端 ESLint 配置文件 `.eslintrc.json` 可能不存在于仓库中；`next lint` 会交互式提示创建。非交互环境下需提前手动创建。
- 后端 `tests/integration/test_services.py` 有预存的 `ModuleNotFoundError`（`app.services.concept_service`），运行完整测试套件时需 `--ignore` 该文件。
- Celery Worker 需要单独启动（参见 `Makefile` 中 `celery-workflow` 和 `celery-content`），路线图生成工作流依赖 Celery 异步任务处理。
