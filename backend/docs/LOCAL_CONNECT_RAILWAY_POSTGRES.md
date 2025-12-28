# 本地连接 Railway PostgreSQL 数据库指南

## 📋 概述

本指南说明如何从本地开发环境连接到 Railway 上的 PostgreSQL 数据库，用于调试、数据查看或数据迁移。

---

## 🔍 第一步：获取连接信息

### 方法 1：从 Railway Dashboard 获取（推荐）

1. **登录 Railway Dashboard**
   - 访问 https://railway.app/dashboard
   - 登录你的账户

2. **找到 PostgreSQL 服务**
   - 在项目画布中找到 PostgreSQL 服务卡片
   - 点击进入服务详情页

3. **查看 Variables（环境变量）**
   - 点击 **Variables** 标签页
   - 找到以下变量并复制值：
     - `PGHOST` - 主机地址（例如：`containers-us-west-xxx.railway.app`）
     - `PGPORT` - 端口（通常是 `5432`）
     - `PGUSER` - 用户名（通常是 `postgres`）
     - `PGPASSWORD` - 密码（长字符串）
     - `PGDATABASE` - 数据库名（通常是 `railway`）

4. **或者查看 Connection Info**
   - 在 PostgreSQL 服务页面，点击 **Connect** 或 **Connection Info**
   - Railway 会显示完整的连接字符串，格式：
     ```
     postgresql://postgres:password@host:5432/railway
     ```

### 方法 2：从 Railway CLI 获取

```bash
# 安装 Railway CLI（如果未安装）
npm i -g @railway/cli

# 登录
railway login

# 进入项目目录
cd /path/to/your/project

# 链接到 Railway 项目
railway link

# 查看 PostgreSQL 连接信息
railway variables
```

---

## 🔧 第二步：使用 psql 命令行连接

### 安装 PostgreSQL 客户端

**macOS**:
```bash
brew install postgresql
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install postgresql-client
```

**Windows**:
- 下载并安装 PostgreSQL: https://www.postgresql.org/download/windows/
- 或使用 WSL

### 连接命令

**方式 1：使用环境变量**
```bash
# 设置环境变量
export PGHOST=containers-us-west-xxx.railway.app
export PGPORT=5432
export PGUSER=postgres
export PGPASSWORD=your_password_here
export PGDATABASE=railway

# 连接
psql
```

**方式 2：使用连接字符串**
```bash
psql "postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway"
```

**方式 3：使用参数**
```bash
psql -h containers-us-west-xxx.railway.app \
     -p 5432 \
     -U postgres \
     -d railway
```

连接后会提示输入密码，输入 `PGPASSWORD` 的值。

### 常用 psql 命令

```sql
-- 列出所有数据库
\l

-- 连接到特定数据库
\c railway

-- 列出所有表
\dt

-- 查看表结构
\d table_name

-- 执行 SQL 查询
SELECT * FROM users LIMIT 10;

-- 退出
\q
```

---

## 🖥️ 第三步：使用 GUI 工具连接

### pgAdmin

1. **下载并安装 pgAdmin**
   - 访问 https://www.pgadmin.org/download/
   - 安装适合你操作系统的版本

2. **添加服务器**
   - 打开 pgAdmin
   - 右键点击 **Servers** → **Create** → **Server**
   - **General** 标签：
     - Name: `Railway PostgreSQL`（任意名称）
   - **Connection** 标签：
     - Host name/address: `containers-us-west-xxx.railway.app`
     - Port: `5432`
     - Maintenance database: `railway`
     - Username: `postgres`
     - Password: `your_password_here`
   - **SSL** 标签（重要）：
     - SSL mode: `Require` 或 `Prefer`
   - 点击 **Save**

### DBeaver

1. **下载并安装 DBeaver**
   - 访问 https://dbeaver.io/download/
   - 安装 Community Edition（免费）

2. **创建新连接**
   - 打开 DBeaver
   - 点击 **New Database Connection**（或 `Cmd+N` / `Ctrl+N`）
   - 选择 **PostgreSQL**
   - 点击 **Next**

3. **配置连接**
   - **Main** 标签：
     - Host: `containers-us-west-xxx.railway.app`
     - Port: `5432`
     - Database: `railway`
     - Username: `postgres`
     - Password: `your_password_here`
   - **SSL** 标签：
     - 勾选 **Use SSL**
     - SSL Mode: `require`
   - 点击 **Test Connection** 测试连接
   - 点击 **Finish**

### TablePlus（macOS）

1. **下载并安装 TablePlus**
   - 访问 https://tableplus.com/
   - 安装应用

2. **创建新连接**
   - 打开 TablePlus
   - 点击 **Create a new connection**
   - 选择 **PostgreSQL**

3. **配置连接**
   - Name: `Railway PostgreSQL`
   - Host: `containers-us-west-xxx.railway.app`
   - Port: `5432`
   - User: `postgres`
   - Password: `your_password_here`
   - Database: `railway`
   - SSL: 选择 **Require**
   - 点击 **Test** 测试连接
   - 点击 **Connect**

---

## 🐍 第四步：使用 Python 连接

### 使用 asyncpg（异步）

```python
import asyncio
import asyncpg

async def connect_railway():
    # 从 Railway 获取的连接信息
    conn = await asyncpg.connect(
        host='containers-us-west-xxx.railway.app',
        port=5432,
        user='postgres',
        password='your_password_here',
        database='railway',
        ssl='require'  # Railway PostgreSQL 需要 SSL
    )
    
    # 执行查询
    rows = await conn.fetch('SELECT * FROM users LIMIT 10')
    for row in rows:
        print(row)
    
    await conn.close()

# 运行
asyncio.run(connect_railway())
```

### 使用 psycopg2（同步）

```python
import psycopg2
from psycopg2.extras import RealDictCursor

# 连接字符串
conn_string = (
    "host=containers-us-west-xxx.railway.app "
    "port=5432 "
    "dbname=railway "
    "user=postgres "
    "password=your_password_here "
    "sslmode=require"
)

# 连接
conn = psycopg2.connect(conn_string)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# 执行查询
cursor.execute("SELECT * FROM users LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(row)

# 关闭连接
cursor.close()
conn.close()
```

### 使用 SQLAlchemy

```python
from sqlalchemy import create_engine, text

# 构建连接字符串
database_url = (
    "postgresql+psycopg2://postgres:your_password_here"
    "@containers-us-west-xxx.railway.app:5432/railway"
    "?sslmode=require"
)

# 创建引擎
engine = create_engine(database_url)

# 执行查询
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM users LIMIT 10"))
    for row in result:
        print(row)
```

---

## 🔐 第五步：配置本地环境变量

为了方便本地开发，可以在 `.env` 文件中配置 Railway 数据库连接：

```bash
# backend/.env

# Railway PostgreSQL 连接（用于本地调试）
POSTGRES_HOST=containers-us-west-xxx.railway.app
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=railway
```

**⚠️ 安全提示**：
- `.env` 文件已添加到 `.gitignore`，**不要**提交到 Git
- 密码是敏感信息，不要分享给他人
- 如果密码泄露，立即在 Railway Dashboard 中重置

---

## ⚠️ 注意事项

### SSL 连接

Railway PostgreSQL **要求使用 SSL 连接**。确保：

1. **psql**:
   ```bash
   psql "postgresql://user:pass@host:5432/db?sslmode=require"
   ```

2. **GUI 工具**: 在连接设置中启用 SSL

3. **Python**: 添加 `ssl='require'` 或 `sslmode=require`

### 连接限制

- Railway PostgreSQL 有**最大连接数限制**（通常是 200）
- 不要在生产数据库上运行长时间查询
- 使用完连接后及时关闭

### 网络访问

- Railway PostgreSQL 默认允许来自任何 IP 的连接
- 如果遇到连接问题，检查：
  1. 防火墙设置
  2. Railway 服务状态
  3. 网络连接

### 数据安全

- ⚠️ **不要在生产数据库上直接修改数据**
- 建议先备份数据
- 使用事务进行测试操作
- 操作前先 `BEGIN`，确认无误后 `COMMIT`

---

## 🛠️ 常见问题

### Q1: 连接超时怎么办？

**A**: 
1. 检查网络连接
2. 确认主机地址和端口正确
3. 检查 Railway 服务是否运行
4. 尝试使用 `sslmode=prefer` 而不是 `require`

### Q2: 密码认证失败？

**A**:
1. 确认密码是从 Railway Dashboard 复制的完整字符串
2. 检查是否有特殊字符需要转义
3. 尝试在 Railway Dashboard 中重置密码

### Q3: SSL 连接错误？

**A**:
1. 确保使用 `sslmode=require` 或 `ssl='require'`
2. 某些工具可能需要下载 SSL 证书
3. 尝试使用 `sslmode=prefer`（如果 Railway 支持）

### Q4: 如何查看连接状态？

**A**: 在 psql 中执行：
```sql
SELECT * FROM pg_stat_activity;
```

### Q5: 如何限制连接数？

**A**: Railway PostgreSQL 会自动管理连接数。如果需要，可以在应用中使用连接池：
```python
# 使用 SQLAlchemy 连接池
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20
)
```

---

## 📚 相关文档

- **Railway PostgreSQL 配置**: [RAILWAY_POSTGRES_ENV_CONFIG.md](./RAILWAY_POSTGRES_ENV_CONFIG.md)
- **Railway 部署指南**: [QUICK_START_RAILWAY.md](../QUICK_START_RAILWAY.md)
- **PostgreSQL 官方文档**: https://www.postgresql.org/docs/

---

## 🔧 快速连接脚本

创建一个便捷的连接脚本：

```bash
#!/bin/bash
# backend/scripts/connect_railway_db.sh

# 从环境变量读取连接信息
PGHOST=${RAILWAY_PGHOST:-"containers-us-west-xxx.railway.app"}
PGPORT=${RAILWAY_PGPORT:-5432}
PGUSER=${RAILWAY_PGUSER:-postgres}
PGPASSWORD=${RAILWAY_PGPASSWORD:-""}
PGDATABASE=${RAILWAY_PGDATABASE:-railway}

# 连接
export PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
psql
```

使用方法：
```bash
# 设置环境变量
export RAILWAY_PGHOST=containers-us-west-xxx.railway.app
export RAILWAY_PGPASSWORD=your_password_here

# 运行脚本
chmod +x backend/scripts/connect_railway_db.sh
./backend/scripts/connect_railway_db.sh
```

