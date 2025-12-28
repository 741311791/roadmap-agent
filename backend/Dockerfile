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
RUN uv export --no-dev --no-hashes > requirements.txt

# 使用 uv pip 安装依赖到系统 Python
RUN uv pip install --system -r requirements.txt

# 复制实际的应用代码
COPY ./app /app/app
COPY ./prompts /app/prompts
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./scripts /app/scripts

# 复制启动脚本
COPY ./scripts/railway_entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 使用 entrypoint 脚本，根据 SERVICE_TYPE 环境变量决定启动哪个服务
# SERVICE_TYPE 可选值：api, celery_logs, celery_content
ENTRYPOINT ["/app/entrypoint.sh"]





