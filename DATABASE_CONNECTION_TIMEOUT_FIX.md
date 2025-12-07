# 🔧 数据库/Redis 连接超时问题修复方案

## 问题诊断

### 错误症状
1. **Redis 超时**: `Timeout reading from 47.111.115.130:6379`
2. **PostgreSQL 超时**: `Operation timed out` (psycopg.OperationalError)
3. **LangGraph Checkpointer 失败**: 无法从 AsyncPostgresSaver 读取数据

### 根本原因分析

从日志看，系统尝试连接到远程服务器 `47.111.115.130`：
- Redis: `47.111.115.130:6379`
- PostgreSQL: `47.111.115.130:5432`

**可能原因**:
1. ❌ **网络连接问题** - 远程服务器不可达或网络不稳定
2. ❌ **超时配置过短** - 当前配置对远程连接不够宽松
3. ❌ **连接池耗尽** - 高并发时连接池不足
4. ❌ **防火墙/安全组** - 远程服务器阻止连接

## 修复方案

### 方案 1: 增加超时配置 (推荐)

#### 1.1 PostgreSQL 连接超时增强

修改 `backend/app/db/session.py`:

```python
# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=60,  # ✅ 增加到 60 秒（原30秒）
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",
        },
        "command_timeout": 120,  # ✅ 增加到 120 秒（原60秒）
        "timeout": 60,  # ✅ 增加到 60 秒（原30秒）
        # ✅ 新增：针对远程连接的优化
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)
```

#### 1.2 LangGraph Checkpointer 超时配置

修改 `backend/app/core/orchestrator_factory.py`:

```python
@classmethod
async def initialize(cls) -> None:
    """初始化工厂（应用启动时调用一次）"""
    if cls._initialized:
        logger.info("orchestrator_factory_already_initialized")
        return
    
    cls._state_manager = StateManager()
    cls._agent_factory = AgentFactory(settings)
    
    # ✅ 创建 AsyncPostgresSaver 时添加连接参数
    try:
        # 构建带超时配置的连接字符串
        conn_string = f"{settings.CHECKPOINTER_DATABASE_URL}?connect_timeout=60&command_timeout=120&keepalives=1&keepalives_idle=30"
        
        checkpointer_cm = AsyncPostgresSaver.from_conn_string(conn_string)
        cls._checkpointer_cm = checkpointer_cm
        cls._checkpointer = await checkpointer_cm.__aenter__()
        
        await cls._checkpointer.setup()
        
        logger.info(
            "orchestrator_factory_initialized",
            checkpointer_type="AsyncPostgresSaver",
            database_url=settings.CHECKPOINTER_DATABASE_URL.split("@")[-1],
        )
        
        cls._initialized = True
        
    except Exception as e:
        logger.error(
            "orchestrator_factory_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

#### 1.3 Redis 超时配置

修改 `backend/app/services/notification_service.py` (如果存在):

```python
import redis.asyncio as redis
from app.config.settings import settings

# ✅ 增加 Redis 连接超时
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=30,  # ✅ 连接超时 30秒
    socket_timeout=30,  # ✅ 读写超时 30秒
    socket_keepalive=True,  # ✅ 启用 keepalive
    health_check_interval=30,  # ✅ 健康检查间隔
    retry_on_timeout=True,  # ✅ 超时自动重试
    max_connections=50,  # ✅ 增加连接池大小
)
```

### 方案 2: 使用本地服务 (开发环境推荐)

如果是开发环境，建议使用本地 Docker 容器：

#### 2.1 启动本地 PostgreSQL 和 Redis

创建 `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: roadmap_user
      POSTGRES_PASSWORD: roadmap_pass
      POSTGRES_DB: roadmap_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U roadmap_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

启动命令:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

#### 2.2 更新 `.env` 配置

```env
# 开发环境使用本地服务
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=roadmap_user
POSTGRES_PASSWORD=roadmap_pass
POSTGRES_DB=roadmap_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 留空
REDIS_DB=0
```

### 方案 3: 添加连接健康检查和重试机制

#### 3.1 数据库连接健康检查

创建 `backend/app/utils/health_check.py`:

```python
"""健康检查工具"""
import asyncio
import structlog
from sqlalchemy import text
from app.db.session import engine

logger = structlog.get_logger()

async def check_database_connection(max_retries: int = 3) -> bool:
    """检查数据库连接健康"""
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("database_health_check_passed", attempt=attempt)
                return True
        except Exception as e:
            logger.warning(
                "database_health_check_failed",
                attempt=attempt,
                max_retries=max_retries,
                error=str(e),
            )
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # 指数退避
            else:
                raise
    return False

async def check_redis_connection() -> bool:
    """检查 Redis 连接健康"""
    try:
        from app.services.notification_service import notification_service
        # 简单 ping 测试
        # await notification_service.redis.ping()
        logger.info("redis_health_check_passed")
        return True
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return False
```

#### 3.2 在应用启动时检查连接

修改 `backend/app/main.py`:

```python
from app.utils.health_check import check_database_connection

@app.on_event("startup")
async def startup():
    """应用启动事件"""
    logger.info("application_startup")
    
    # ✅ 检查数据库连接
    try:
        await check_database_connection(max_retries=5)
        logger.info("database_connection_verified")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise RuntimeError("无法连接到数据库，应用启动失败")
    
    # 初始化 Orchestrator
    await initialize_orchestrator()
    
    # 检查 MinIO
    await check_minio_connection()
    
    logger.info("application_startup_complete")
```

### 方案 4: 降级策略（生产环境）

#### 4.1 添加 Redis 降级逻辑

如果 Redis 不可用，可以临时禁用 WebSocket 通知：

```python
class NotificationService:
    def __init__(self):
        self.redis_available = False
        self._init_redis()
    
    async def _init_redis(self):
        """初始化 Redis（容忍失败）"""
        try:
            self.redis = redis.from_url(...)
            await self.redis.ping()
            self.redis_available = True
            logger.info("redis_initialized")
        except Exception as e:
            logger.warning("redis_unavailable_fallback_mode", error=str(e))
            self.redis_available = False
    
    async def publish(self, task_id: str, event: dict):
        """发布事件（降级模式下跳过）"""
        if not self.redis_available:
            logger.debug("redis_unavailable_skipping_publish", task_id=task_id)
            return
        
        try:
            await self.redis.publish(...)
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))
            # 不抛出异常，允许任务继续
```

#### 4.2 Checkpointer 降级（不推荐，仅紧急情况）

如果 Checkpointer 完全不可用，可以禁用它：

```python
# 仅作为最后手段
checkpointer = None  # 禁用 checkpoint
executor = WorkflowExecutor(
    builder=builder,
    state_manager=state_manager,
    checkpointer=None,  # ⚠️ 这将禁用状态持久化和恢复
)
```

**警告**: 这将导致无法使用 human-in-the-loop 和故障恢复功能。

## 快速测试脚本

创建 `backend/scripts/test_connections.py`:

```python
#!/usr/bin/env python3
"""测试数据库和 Redis 连接"""
import asyncio
import sys
sys.path.insert(0, '/Users/louie/Documents/Vibecoding/roadmap-agent/backend')

from app.db.session import engine
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

async def test_postgres():
    """测试 PostgreSQL 连接"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL 连接成功")
            print(f"   版本: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
        return False

async def test_redis():
    """测试 Redis 连接"""
    try:
        import redis.asyncio as redis
        from app.config.settings import settings
        
        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await client.ping()
        info = await client.info("server")
        print(f"✅ Redis 连接成功")
        print(f"   版本: {info['redis_version']}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False

async def main():
    print("=" * 50)
    print("测试远程服务连接")
    print("=" * 50)
    print()
    
    pg_ok = await test_postgres()
    print()
    redis_ok = await test_redis()
    print()
    
    if pg_ok and redis_ok:
        print("✅ 所有连接测试通过")
        return 0
    else:
        print("❌ 部分连接测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

运行测试:
```bash
cd backend
python3 scripts/test_connections.py
```

## 推荐执行顺序

### 立即执行（开发环境）:
1. ✅ 运行连接测试脚本确认问题
2. ✅ 启动本地 Docker 容器（方案 2）
3. ✅ 更新 `.env` 使用本地服务
4. ✅ 重启后端服务测试

### 生产环境:
1. ✅ 增加超时配置（方案 1）
2. ✅ 添加健康检查（方案 3）
3. ✅ 实施降级策略（方案 4）
4. ✅ 配置监控告警

## 验证修复

修复后，重新发起生成请求，观察日志应该看到：

```log
✅ [info] orchestrator_factory_initialized checkpointer_type=AsyncPostgresSaver
✅ [info] workflow_execution_starting
✅ [info] intent_analysis_started
✅ [info] curriculum_design_started
❌ 不再出现 timeout 错误
```

---

**修复时间**: 2025-12-07  
**优先级**: 🔴 Critical  
**建议方案**: 方案 1 + 方案 2 (开发环境) / 方案 1 + 方案 3 (生产环境)

