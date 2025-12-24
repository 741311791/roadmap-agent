FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（使用官方安装脚本）并验证安装
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv --version

# 配置环境变量：将 uv 添加到 PATH
ENV PATH="/root/.local/bin:$PATH"

# 配置 uv 使用系统 Python（在 Docker 容器中不需要虚拟环境）
ENV UV_SYSTEM_PYTHON=1

# 复制依赖文件（uv 需要 pyproject.toml 和 uv.lock）
COPY pyproject.toml uv.lock ./

# 使用 uv 同步生产环境依赖
# --frozen: 使用 uv.lock 锁定版本，确保可重现构建
# --no-dev: 不安装开发依赖（pytest, black 等）
# --no-install-project: 只安装依赖，不安装项目本身（app/ 代码还未复制）
RUN uv sync --frozen --no-dev --no-install-project

# 复制应用代码
COPY ./app /app/app
COPY ./prompts /app/prompts

# 复制 Alembic 迁移配置（Railway 部署时需要运行数据库迁移）
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Railway 会自动检测端口，无需显式 EXPOSE
# EXPOSE 8000

# 启动命令：
# 1. 运行数据库迁移 (alembic upgrade head)
# 2. 启动 Uvicorn，使用 Railway 提供的 $PORT 环境变量（默认为 8000）
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

