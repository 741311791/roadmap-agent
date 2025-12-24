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

# 复制依赖配置文件和 README（构建需要）
COPY pyproject.toml uv.lock README.md ./

# 创建临时的 app 目录（满足项目结构要求）
RUN mkdir -p /app/app && touch /app/app/__init__.py

# 使用 uv 导出生产环境依赖到 requirements.txt
# --no-dev: 不包含开发依赖
# --no-hashes: 不包含哈希值（简化输出）
RUN uv export --no-dev --no-hashes > requirements.txt

# 使用 uv pip 安装依赖到系统 Python
# --system: 直接安装到系统 Python，不创建虚拟环境
# -r requirements.txt: 从文件读取依赖列表
RUN uv pip install --system -r requirements.txt

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

