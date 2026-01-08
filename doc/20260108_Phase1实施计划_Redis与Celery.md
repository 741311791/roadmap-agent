# Phase 1 实施计划: Redis + Celery 集成

> **优先级**: 🔴 最高  
> **预计工期**: 5 个工作日  
> **依赖**: 无  
> **目标**: 补全企业架构核心基础设施

---

## 📋 任务概览

### Day 1-2: Redis 缓存层集成

**任务清单**:
- [x] 创建 Redis 客户端封装
- [x] 实现 Cache-Aside 模式
- [x] 集成到现有服务

**预期成果**:
- User 查询缓存命中率 > 80%
- LangGraph 状态查询延迟降低 50%

### Day 3-5: Celery 异步任务队列

**任务清单**:
- [x] Celery 基础配置
- [x] 路线图生成任务异步化
- [x] 任务状态查询端点

**预期成果**:
- 路线图生成 API 响应时间 < 200ms
- 支持并发 100+ 任务生成

---

## 🔧 实施细节

## 一、Redis 客户端封装

### 1.1 创建 Redis 客户端类

**文件**: `backend/app/db/redis.py` (新建)

```python
"""
Redis 客户端封装

提供统一的 Redis 访问接口,支持连接池、自动重连、批量删除等功能。
"""
from typing import Any
from redis.asyncio import Redis, ConnectionPool
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisCli:
    """
    Redis 客户端封装
    
    功能:
    - 连接池管理 (max_connections=50)
    - TCP keepalive 防止连接中断
    - 统一的 Key 命名规范
    - 批量删除 (delete_prefix)
    """
    
    def __init__(self):
        """初始化 Redis 客户端 (延迟连接)"""
        self.redis_client: Redis | None = None
        self._connection_pool: ConnectionPool | None = None
    
    async def open(self):
        """
        打开 Redis 连接池
        
        应在应用启动时调用 (main.py lifespan)
        """
        if self.redis_client is not None:
            logger.warning("redis_client_already_opened")
            return
        
        # 创建连接池
        self._connection_pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            encoding="utf-8",
            decode_responses=True,  # 自动解码为字符串
            max_connections=50,  # 最大连接数
            socket_connect_timeout=5,  # 连接超时 5 秒
            socket_keepalive=True,  # 启用 TCP keepalive
            socket_keepalive_options={
                1: 30,  # TCP_KEEPIDLE: 30 秒空闲后开始探测
                2: 10,  # TCP_KEEPINTVL: 探测间隔 10 秒
                3: 5,   # TCP_KEEPCNT: 最多 5 次探测
            },
        )
        
        # 创建 Redis 客户端
        self.redis_client = Redis(connection_pool=self._connection_pool)
        
        # 测试连接
        try:
            await self.redis_client.ping()
            logger.info(
                "redis_connected",
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
            )
        except Exception as e:
            logger.error(
                "redis_connection_failed",
                error=str(e),
                host=settings.REDIS_HOST,
            )
            raise
    
    async def close(self):
        """
        关闭 Redis 连接池
        
        应在应用关闭时调用 (main.py lifespan)
        """
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
            logger.info("redis_connection_closed")
    
    # ============================================================
    # 基础操作 (代理到 Redis 客户端)
    # ============================================================
    
    async def get(self, key: str) -> str | None:
        """获取缓存值"""
        return await self.redis_client.get(key)
    
    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ex: 过期时间 (秒),None 表示永不过期
        """
        return await self.redis_client.set(key, value, ex=ex)
    
    async def setex(self, key: str, time: int, value: Any) -> bool:
        """设置缓存值并指定过期时间 (秒)"""
        return await self.redis_client.setex(key, time, value)
    
    async def delete(self, *keys: str) -> int:
        """
        删除缓存键
        
        Returns:
            删除的键数量
        """
        return await self.redis_client.delete(*keys)
    
    async def exists(self, *keys: str) -> int:
        """
        检查键是否存在
        
        Returns:
            存在的键数量
        """
        return await self.redis_client.exists(*keys)
    
    async def expire(self, key: str, time: int) -> bool:
        """设置键的过期时间 (秒)"""
        return await self.redis_client.expire(key, time)
    
    async def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间 (秒)
        
        Returns:
            -2: 键不存在
            -1: 键没有设置过期时间
            其他: 剩余秒数
        """
        return await self.redis_client.ttl(key)
    
    # ============================================================
    # 高级操作
    # ============================================================
    
    async def delete_prefix(self, prefix: str, exclude: str | None = None) -> int:
        """
        批量删除指定前缀的键
        
        Args:
            prefix: 键前缀 (如 "user:")
            exclude: 排除的键 (完整键名)
            
        Returns:
            删除的键数量
        """
        keys = []
        async for key in self.redis_client.scan_iter(match=f"{prefix}*"):
            if exclude and key == exclude:
                continue
            keys.append(key)
        
        if keys:
            return await self.redis_client.delete(*keys)
        return 0
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        自增计数器
        
        Args:
            key: 计数器键
            amount: 增量 (默认 1)
            
        Returns:
            自增后的值
        """
        return await self.redis_client.incrby(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """
        自减计数器
        
        Args:
            key: 计数器键
            amount: 减量 (默认 1)
            
        Returns:
            自减后的值
        """
        return await self.redis_client.decrby(key, amount)


# 全局单例实例
redis_client = RedisCli()
```

### 1.2 集成到应用生命周期

**文件**: `backend/app/main.py` (修改)

```python
# 修改前
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup")
    await init_orchestrator()
    await ensure_bucket_exists()
    # ...
    yield
    logger.info("application_shutdown")
    await cleanup_orchestrator()

# 修改后
from app.db.redis import redis_client  # 新增

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup")
    
    # ⭐ 初始化 Redis 连接
    await redis_client.open()
    
    await init_orchestrator()
    await ensure_bucket_exists()
    # ...
    
    yield
    
    logger.info("application_shutdown")
    
    # ⭐ 关闭 Redis 连接
    await redis_client.close()
    
    await cleanup_orchestrator()
```

---

## 二、Cache-Aside 实现

### 2.1 User 缓存

**文件**: `backend/app/services/user_cache_service.py` (新建)

```python
"""
用户缓存服务

实现 Cache-Aside 模式,减少数据库查询压力。
"""
import structlog
from app.db.redis import redis_client
from app.models.database import User
from app.crud.crud_user import get_user_crud

logger = structlog.get_logger()

# 缓存配置
USER_CACHE_PREFIX = "user:"
USER_CACHE_TTL = 3600  # 1 小时


class UserCacheService:
    """用户缓存服务 (Cache-Aside 模式)"""
    
    @staticmethod
    async def get_user_with_cache(session, user_id: str) -> User | None:
        """
        获取用户信息 (优先从缓存)
        
        Cache-Aside 流程:
        1. 查 Redis 缓存
        2. 缓存命中 → 返回
        3. 缓存未命中 → 查数据库 → 写入缓存
        
        Args:
            session: 数据库会话
            user_id: 用户 ID
            
        Returns:
            User 实例或 None
        """
        cache_key = f"{USER_CACHE_PREFIX}{user_id}"
        
        # 1. 查缓存
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug("user_cache_hit", user_id=user_id)
            # 缓存穿透防护: 缓存空结果为 "NULL"
            if cached == "NULL":
                return None
            return User.model_validate_json(cached)
        
        # 2. 缓存未命中,查数据库
        logger.debug("user_cache_miss", user_id=user_id)
        user_crud = get_user_crud()
        user = await user_crud.get_by_user_id(session, user_id)
        
        # 3. 写入缓存
        if user:
            await redis_client.setex(
                cache_key,
                USER_CACHE_TTL,
                user.model_dump_json(),
            )
            logger.debug("user_cached", user_id=user_id)
        else:
            # 缓存穿透防护: 缓存空结果 (短 TTL)
            await redis_client.setex(cache_key, 60, "NULL")
        
        return user
    
    @staticmethod
    async def invalidate_user_cache(user_id: str) -> None:
        """
        失效用户缓存
        
        使用场景:
        - 用户信息更新时
        - 用户权限变更时
        - 用户删除时
        
        Args:
            user_id: 用户 ID
        """
        cache_key = f"{USER_CACHE_PREFIX}{user_id}"
        await redis_client.delete(cache_key)
        logger.info("user_cache_invalidated", user_id=user_id)
```

### 2.2 LangGraph 状态缓存

**文件**: `backend/app/core/orchestrator/state_manager.py` (修改)

```python
# 在 StateManager 类中添加缓存方法

from app.db.redis import redis_client

LANGGRAPH_STATE_PREFIX = "langgraph:state:"
LANGGRAPH_STATE_TTL = 600  # 10 分钟

class StateManager:
    """状态管理器 (增加 Redis 缓存)"""
    
    async def get_state_with_cache(self, trace_id: str) -> dict | None:
        """
        获取 LangGraph 状态 (优先从缓存)
        
        Args:
            trace_id: 追踪 ID
            
        Returns:
            状态字典或 None
        """
        cache_key = f"{LANGGRAPH_STATE_PREFIX}{trace_id}"
        
        # 1. 查缓存
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug("langgraph_state_cache_hit", trace_id=trace_id)
            return json.loads(cached)
        
        # 2. 查 Checkpointer
        state = await self.get_state(trace_id)
        
        # 3. 写缓存
        if state:
            await redis_client.setex(
                cache_key,
                LANGGRAPH_STATE_TTL,
                json.dumps(state),
            )
        
        return state
    
    async def invalidate_state_cache(self, trace_id: str) -> None:
        """
        失效状态缓存
        
        使用场景:
        - 工作流节点完成时
        - 状态更新时
        """
        cache_key = f"{LANGGRAPH_STATE_PREFIX}{trace_id}"
        await redis_client.delete(cache_key)
```

---

## 三、Celery 集成

### 3.1 Celery 配置

**文件**: `backend/app/tasks/__init__.py` (新建目录)

**文件**: `backend/app/tasks/celery_app.py` (新建)

```python
"""
Celery 应用初始化

使用 Redis 作为 Broker 和 Result Backend。
"""
from celery import Celery
from app.config.settings import settings

# 创建 Celery 应用
celery_app = Celery(
    "roadmap_agent",
    broker=settings.get_redis_url,  # Redis 作为消息队列
    backend=settings.get_redis_url,  # Redis 存储任务结果
    include=[
        "app.tasks.roadmap_generation",  # 路线图生成任务
    ],
)

# Celery 配置
celery_app.conf.update(
    # 任务配置
    task_track_started=True,  # 追踪任务开始状态
    task_time_limit=7200,  # 任务硬超时 2 小时
    task_soft_time_limit=6900,  # 任务软超时 1小时55分钟
    task_acks_late=True,  # 任务执行完后才确认
    task_reject_on_worker_lost=True,  # Worker 丢失时拒绝任务
    
    # 结果配置
    result_expires=86400,  # 结果保存 24 小时
    result_extended=True,  # 保存完整任务信息
    
    # 序列化配置
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # 时区配置
    timezone="Asia/Shanghai",
    enable_utc=False,
    
    # 并发配置
    worker_prefetch_multiplier=1,  # 每次只预取 1 个任务 (避免资源浪费)
)

# 导出
__all__ = ["celery_app"]
```

### 3.2 路线图生成任务

**文件**: `backend/app/tasks/roadmap_generation.py` (新建)

```python
"""
路线图生成 Celery 任务

将 LangGraph 工作流封装为异步任务,实现非阻塞响应。
"""
import structlog
from app.tasks.celery_app import celery_app
from app.models.domain import UserRequest
from app.core.orchestrator_factory import OrchestratorFactory

logger = structlog.get_logger()


@celery_app.task(
    name="generate_roadmap",
    bind=True,  # 绑定任务实例 (可访问 self)
    max_retries=3,  # 最多重试 3 次
    default_retry_delay=300,  # 重试延迟 5 分钟
)
async def generate_roadmap_task(self, user_request_dict: dict, task_id: str):
    """
    异步生成路线图
    
    Args:
        self: Celery 任务实例
        user_request_dict: 用户请求字典 (JSON 序列化)
        task_id: 追踪 ID
        
    Returns:
        最终状态字典
        
    Raises:
        Retry: 遇到临时错误时重试
    """
    try:
        # 1. 解析用户请求
        user_request = UserRequest.model_validate(user_request_dict)
        
        # 2. 创建工作流执行器
        executor = OrchestratorFactory.create_workflow_executor()
        
        # 3. 执行工作流
        logger.info(
            "roadmap_generation_started",
            task_id=task_id,
            celery_task_id=self.request.id,
        )
        
        final_state = await executor.execute(user_request, task_id)
        
        logger.info(
            "roadmap_generation_completed",
            task_id=task_id,
            celery_task_id=self.request.id,
            status=final_state.get("current_step"),
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "final_state": final_state,
        }
        
    except Exception as e:
        logger.error(
            "roadmap_generation_failed",
            task_id=task_id,
            celery_task_id=self.request.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        
        # 判断是否应该重试
        if _should_retry(e):
            # 重试任务
            raise self.retry(exc=e)
        
        # 不可重试的错误,直接失败
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
        }


def _should_retry(error: Exception) -> bool:
    """
    判断错误是否应该重试
    
    可重试错误:
    - 网络超时
    - 数据库连接错误
    - LLM API 限流
    
    不可重试错误:
    - 参数验证错误
    - 业务逻辑错误
    """
    error_msg = str(error).lower()
    
    # 可重试的错误关键字
    retryable_keywords = [
        "timeout",
        "connection",
        "rate limit",
        "temporary",
        "retry",
    ]
    
    return any(keyword in error_msg for keyword in retryable_keywords)
```

### 3.3 API 层调用

**文件**: `backend/app/api/v1/endpoints/generation.py` (修改)

```python
# 修改前
@router.post("/generate")
async def generate_roadmap(
    request: UserRequest,
    service: RoadmapService = Depends(get_roadmap_service),
):
    """同步生成路线图 (阻塞 Worker)"""
    result = await service.generate_roadmap(request)
    return result

# 修改后
from app.tasks.roadmap_generation import generate_roadmap_task

@router.post("/generate")
async def generate_roadmap(
    request: UserRequest,
    session: CurrentSessionTransaction,
):
    """
    异步生成路线图 (立即返回)
    
    工作流:
    1. 创建任务记录
    2. 提交 Celery 任务
    3. 立即返回 task_id
    4. 客户端轮询 /tasks/{task_id} 查询状态
    """
    # 1. 创建任务记录
    task_id = str(uuid.uuid4())
    task_crud = get_task_crud()
    await task_crud.create(session, obj_in={
        "task_id": task_id,
        "user_id": request.user_id,
        "status": "pending",
        "current_step": "queued",
    })
    
    # 2. 提交 Celery 任务
    celery_task = generate_roadmap_task.delay(
        request.model_dump(),
        task_id,
    )
    
    logger.info(
        "roadmap_generation_queued",
        task_id=task_id,
        celery_task_id=celery_task.id,
    )
    
    # 3. 立即返回
    return {
        "task_id": task_id,
        "celery_task_id": celery_task.id,
        "status": "queued",
        "message": "路线图生成任务已提交,请轮询 /tasks/{task_id} 查询状态",
    }
```

### 3.4 任务状态查询

**文件**: `backend/app/api/v1/endpoints/generation.py` (新增端点)

```python
from celery.result import AsyncResult

@router.get("/tasks/{task_id}/celery-status")
async def get_celery_task_status(task_id: str):
    """
    查询 Celery 任务状态
    
    状态枚举:
    - PENDING: 任务尚未开始
    - STARTED: 任务已开始执行
    - SUCCESS: 任务成功完成
    - FAILURE: 任务失败
    - RETRY: 任务重试中
    """
    # 1. 查询数据库任务记录获取 celery_task_id
    task_crud = get_task_crud()
    task = await task_crud.get_by_task_id(session, task_id)
    
    if not task or not task.celery_task_id:
        raise HTTPException(404, "任务不存在")
    
    # 2. 查询 Celery 任务状态
    celery_result = AsyncResult(task.celery_task_id)
    
    return {
        "task_id": task_id,
        "celery_task_id": task.celery_task_id,
        "celery_status": celery_result.status,
        "celery_result": celery_result.result if celery_result.ready() else None,
        "db_status": task.status,
        "db_current_step": task.current_step,
    }
```

---

## 四、启动 Celery Worker

### 4.1 创建启动脚本

**文件**: `backend/start_celery.sh` (新建)

```bash
#!/bin/bash

# Celery Worker 启动脚本

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动 Celery Worker
celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=solo \
    --max-tasks-per-child=10 \
    --task-events \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    -n roadmap_worker@%h

# 参数说明:
# --concurrency=4: 并发执行 4 个任务
# --pool=solo: 单进程模式 (支持 asyncio)
# --max-tasks-per-child=10: 每个 Worker 最多处理 10 个任务后重启 (防止内存泄漏)
# --task-events: 启用任务事件 (供 Flower 监控)
# -n roadmap_worker@%h: Worker 名称 (包含主机名)
```

### 4.2 Docker Compose 集成

**文件**: `docker-compose.yml` (修改)

```yaml
# 新增 Celery Worker 服务
services:
  backend:
    # ... (保持不变)
  
  # ⭐ 新增: Celery Worker
  celery_worker:
    build: .
    command: bash start_celery.sh
    environment:
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
  
  # ⭐ 新增: Celery Flower (监控面板)
  celery_flower:
    build: .
    command: celery -A app.tasks.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

---

## 五、验收标准

### 功能验收

- [ ] Redis 连接池正常启动,连接数 50
- [ ] User 缓存命中率 > 80% (通过 Prometheus 监控)
- [ ] LangGraph 状态缓存命中率 > 60%
- [ ] Celery Worker 正常启动,并发数 4
- [ ] 路线图生成任务提交成功,返回 task_id
- [ ] 任务状态查询端点正常工作
- [ ] Celery Flower 监控面板可访问 (http://localhost:5555)

### 性能验收

- [ ] `/roadmaps/generate` API 响应时间 < 200ms (从同步 60s → 异步 200ms)
- [ ] 支持并发 100+ 任务生成 (通过 Celery 队列)
- [ ] Redis 缓存延迟 P99 < 5ms
- [ ] 数据库查询次数减少 70% (通过缓存)

### 日志验收

- [ ] Redis 连接成功日志: `redis_connected`
- [ ] 缓存命中日志: `user_cache_hit`, `langgraph_state_cache_hit`
- [ ] Celery 任务提交日志: `roadmap_generation_queued`
- [ ] Celery 任务完成日志: `roadmap_generation_completed`

---

## 六、回滚计划

### 如果出现问题

1. **Redis 连接失败**:
   - 回滚: 注释 `await redis_client.open()` 行
   - 影响: 缓存功能失效,性能下降

2. **Celery 任务失败**:
   - 回滚: API 层恢复调用 `service.generate_roadmap()`
   - 影响: 恢复同步模式,响应变慢

3. **依赖冲突**:
   - 回滚: `git checkout HEAD~1 pyproject.toml`
   - 重新安装: `poetry install`

---

## 七、监控指标

### Prometheus 指标 (需要在 Phase 2 补充)

```python
# Redis 缓存指标
redis_cache_hit = Counter("redis_cache_hit_total", "缓存命中次数", ["cache_type"])
redis_cache_miss = Counter("redis_cache_miss_total", "缓存未命中次数", ["cache_type"])

# Celery 任务指标
celery_task_submitted = Counter("celery_task_submitted_total", "任务提交次数", ["task_name"])
celery_task_completed = Counter("celery_task_completed_total", "任务完成次数", ["task_name", "status"])
celery_task_duration = Histogram("celery_task_duration_seconds", "任务执行时长", ["task_name"])
```

---

**实施负责人**: Backend Team  
**预计完成日期**: 2026-01-13  
**文档版本**: v1.0

