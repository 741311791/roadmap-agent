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

# 复制 pyproject.toml 和创建最小的项目结构（用于安装依赖）
COPY pyproject.toml ./
RUN mkdir -p /app/app && touch /app/app/__init__.py

# 使用 uv pip 安装项目依赖到系统 Python
# --system: 直接安装到系统 Python，不创建虚拟环境
# -e .: 以 editable 模式安装当前项目，会安装 pyproject.toml 中的所有依赖
RUN uv pip install --system -e .

# 复制实际的应用代码（覆盖之前的占位符）
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

