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

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

