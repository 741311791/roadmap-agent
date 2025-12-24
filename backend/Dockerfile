FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install --no-cache-dir poetry

# 配置 Poetry（不使用虚拟环境）
RUN poetry config virtualenvs.create false

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖（生产环境）
RUN poetry install --no-dev --no-interaction --no-ansi

# 复制应用代码
COPY ./app /app/app
COPY ./prompts /app/prompts
COPY ./specs /app/specs

# 复制 Alembic 迁移配置（Railway 部署时需要运行数据库迁移）
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Railway 会自动检测端口，无需显式 EXPOSE
# EXPOSE 8000

# 启动命令：
# 1. 运行数据库迁移 (alembic upgrade head)
# 2. 启动 Uvicorn，使用 Railway 提供的 $PORT 环境变量（默认为 8000）
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

