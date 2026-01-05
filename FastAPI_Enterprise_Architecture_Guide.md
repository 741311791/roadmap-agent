# FastAPI + Redis + Celery 企业级架构重构与开发指南

> 基于 fastapi-practices/fastapi_best_architecture 项目的生产级架构经验总结  
> 版本：v1.0 | 更新日期：2026-01-05

---

## 📑 目录

- [第一部分：技术栈全景图](#第一部分技术栈全景图)
- [第二部分：项目目录结构规范](#第二部分项目目录结构规范)
- [第三部分：数据库设计与操作规范](#第三部分数据库设计与操作规范)
- [第四部分：API 设计规范](#第四部分api-设计规范)
- [第五部分：Redis 使用规范](#第五部分redis-使用规范)
- [第六部分：Celery 异步任务规范](#第六部分celery-异步任务规范)
- [第七部分：异常处理与日志规范](#第七部分异常处理与日志规范)
- [第八部分：中间件架构设计](#第八部分中间件架构设计)
- [第九部分：安全性设计](#第九部分安全性设计)
- [第十部分：性能优化策略](#第十部分性能优化策略)
- [第十一部分：可观测性](#第十一部分可观测性)
- [第十二部分：测试策略](#第十二部分测试策略)
- [第十三部分：部署与运维](#第十三部分部署与运维)
- [第十四部分：代码质量](#第十四部分代码质量)
- [第十五部分：完整业务示例](#第十五部分完整业务示例)
- [附录](#附录)

---

## 第一部分：技术栈全景图

### 1.1 核心技术栈选型

| 组件类型 | 技术选型 | 版本要求 | 选型理由 |
|---------|---------|---------|---------|
| **Web 框架** | FastAPI | ≥ 0.110 | 高性能、自动文档、类型安全 |
| **Python 版本** | Python | ≥ 3.10 | 类型提示改进、性能提升 |
| **ORM** | SQLAlchemy | ≥ 2.0 | 原生异步、Mapped类型注解 |
| **DB 驱动 (PostgreSQL)** | asyncpg | ≥ 0.29 | 最快的异步PG驱动 |
| **DB 驱动 (MySQL)** | asyncmy | ≥ 0.2.9 | 原生异步MySQL驱动 |
| **数据验证** | Pydantic | ≥ 2.0 | v2基于Rust重写，性能10倍提升 |
| **配置管理** | pydantic-settings | ≥ 2.0 | 类型安全的配置管理 |
| **缓存/队列** | Redis | ≥ 7.0 | 高性能内存数据库 |
| **Redis 客户端** | redis[hiredis] | ≥ 5.0 | 异步客户端+C扩展加速 |
| **任务队列** | Celery | ≥ 5.3 | 成熟的分布式任务队列 |
| **异步任务池** | celery-aio-pool | ≥ 0.1.0 | 支持async/await语法 |
| **密码加密** | bcrypt | ≥ 4.0 | 业界标准加密算法 |
| **JWT** | python-jose | ≥ 3.3 | JWT token生成/解析 |
| **日志** | loguru | ≥ 0.7 | 开箱即用的日志库 |
| **CRUD 封装** | sqlalchemy-crud-plus | ≥ 1.13 | 类Django ORM的便捷性 |
| **HTTP 客户端** | httpx | ≥ 0.25 | 异步HTTP客户端 |
| **序列化加速** | msgspec | ≥ 0.18 | 比Pydantic快10倍 |

### 1.2 技术选型对比

#### 数据库驱动选择

| 驱动 | 类型 | 性能 | 推荐场景 |
|------|-----|------|---------|
| **asyncpg** | 异步 | ⭐⭐⭐⭐⭐ | PostgreSQL 生产环境 ✅ |
| **psycopg3** | 同步/异步 | ⭐⭐⭐⭐ | 兼容旧代码迁移 |
| **asyncmy** | 异步 | ⭐⭐⭐⭐ | MySQL 生产环境 ✅ |
| **pymysql** | 同步 | ⭐⭐ | ❌ 不推荐（同步阻塞） |

#### Celery Broker 选择

| Broker | 持久化 | 性能 | 适用场景 |
|--------|--------|------|---------|
| **Redis** | AOF/RDB | ⭐⭐⭐⭐⭐ | 中小规模、高性能场景 ✅ |
| **RabbitMQ** | 磁盘 | ⭐⭐⭐⭐ | 大规模、高可靠场景 |
| **内存队列** | 无 | ⭐⭐⭐⭐⭐ | ❌ 不推荐（数据易丢失） |

### 1.3 依赖安装

```bash
# 使用 uv (推荐，比 pip 快 10-100 倍)
uv pip install fastapi[standard] sqlalchemy[asyncio] pydantic-settings

# 数据库驱动 (二选一)
uv pip install asyncpg  # PostgreSQL
uv pip install asyncmy  # MySQL

# 核心依赖
uv pip install redis[hiredis] celery celery-aio-pool
uv pip install bcrypt python-jose loguru
uv pip install sqlalchemy-crud-plus msgspec
```

---

## 第二部分：项目目录结构规范

### 2.1 标准目录树

```
project_root/
├── backend/                      # 后端代码根目录
│   ├── app/                      # 业务应用模块
│   │   ├── admin/               # [核心] 管理后台模块
│   │   │   ├── api/            # API 路由层
│   │   │   │   └── v1/         # API 版本控制
│   │   │   │       ├── auth/   # 认证相关接口
│   │   │   │       └── sys/    # 系统管理接口
│   │   │   ├── service/        # 业务逻辑层
│   │   │   │   ├── user_service.py
│   │   │   │   └── auth_service.py
│   │   │   ├── crud/           # 数据访问层 (DAO)
│   │   │   │   ├── crud_user.py
│   │   │   │   └── __init__.py
│   │   │   ├── model/          # 数据库模型 (ORM)
│   │   │   │   ├── user.py
│   │   │   │   └── m2m.py      # 多对多关联表
│   │   │   ├── schema/         # 数据传输对象 (DTO)
│   │   │   │   ├── user.py
│   │   │   │   └── token.py
│   │   │   └── utils/          # 模块内工具
│   │   └── task/                # 异步任务模块
│   │       ├── celery.py        # Celery 应用实例
│   │       ├── tasks/           # 任务定义
│   │       └── database.py      # Result Backend 重写
│   ├── core/                     # 核心配置
│   │   ├── conf.py              # Pydantic Settings 配置
│   │   ├── registrar.py         # 应用注册器 (中间件/路由)
│   │   └── path_conf.py         # 路径配置
│   ├── database/                 # 数据库基础设施
│   │   ├── db.py                # 异步引擎/Session工厂
│   │   └── redis.py             # Redis 连接池
│   ├── middleware/               # 自定义中间件
│   │   ├── jwt_auth_middleware.py
│   │   ├── opera_log_middleware.py
│   │   └── access_middleware.py
│   ├── common/                   # 通用组件
│   │   ├── exception/           # 异常定义
│   │   ├── response/            # 响应封装
│   │   ├── security/            # 安全组件 (JWT/RBAC)
│   │   └── pagination.py        # 分页封装
│   ├── utils/                    # 工具函数
│   │   ├── timezone.py
│   │   └── serializers.py
│   ├── alembic/                  # 数据库迁移
│   │   └── versions/
│   ├── main.py                   # 应用入口
│   └── .env                      # 环境变量
├── tests/                        # 测试代码
├── docker-compose.yml            # Docker编排
├── Dockerfile                    # Docker镜像
├── pyproject.toml                # 项目元数据
└── README.md                     # 项目文档
```

### 2.2 分层架构职责定义

#### API 层 (api/)
**职责**：HTTP 协议适配层
- ✅ 解析请求参数 (Query/Path/Body)
- ✅ 调用 Service 层方法
- ✅ 格式化响应 (ResponseModel)
- ❌ **禁止**：包含业务逻辑
- ❌ **禁止**：直接操作数据库

```python
# backend/app/admin/api/v1/sys/user.py
@router.get("/{pk}")
async def get_user(
    db: CurrentSession,
    pk: Annotated[int, Path(description="用户ID")]
) -> ResponseSchemaModel[GetUserInfoDetail]:
    """✅ 正确：只负责HTTP适配"""
    user = await user_service.get_userinfo(db=db, pk=pk)
    return response_base.success(data=user)
```

#### Service 层 (service/)
**职责**：业务逻辑聚合层
- ✅ 实现业务规则
- ✅ 编排多个 CRUD 调用
- ✅ 处理缓存逻辑
- ✅ 控制事务边界（通过依赖注入）
- ❌ **禁止**：直接写 SQL
- ❌ **禁止**：返回 ORM Model（必须转为 Schema）

```python
# backend/app/admin/service/user_service.py
class UserService:
    @staticmethod
    async def create(*, db: AsyncSession, obj: AddUserParam) -> None:
        """✅ 正确：业务逻辑验证 + CRUD调用"""
        # 业务规则验证
        if await user_dao.get_by_username(db, obj.username):
            raise errors.ConflictError(msg="用户名已存在")
        
        # 编排多个数据操作
        await user_dao.add(db, obj)
        await role_dao.assign_default_role(db, obj.user_id)
```

#### CRUD 层 (crud/)
**职责**：纯数据访问层
- ✅ 封装 SQLAlchemy 查询
- ✅ 提供通用 CRUD 方法
- ✅ 构建复杂查询条件
- ❌ **禁止**：包含业务规则判断
- ❌ **禁止**：直接返回给 API (返回给 Service)

```python
# backend/app/admin/crud/crud_user.py
from sqlalchemy_crud_plus import CRUDPlus

class CRUDUser(CRUDPlus[User]):
    """✅ 正确：纯数据库操作"""
    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        return await self.select_model_by_column(db, username=username)

user_dao = CRUDUser(User)
```

### 2.3 文件命名规范

| 文件类型 | 命名规则 | 示例 |
|---------|---------|------|
| **Model** | 单数名词 | `user.py`, `order.py` |
| **Schema** | 单数名词 | `user.py`, `token.py` |
| **CRUD** | `crud_<model>.py` | `crud_user.py` |
| **Service** | `<domain>_service.py` | `user_service.py`, `auth_service.py` |
| **API Router** | 复数名词 | `users.py`, `orders.py` |
| **中间件** | `<name>_middleware.py` | `jwt_auth_middleware.py` |

---

## 第三部分：数据库设计与操作规范

### 3.1 连接池配置

#### 参数调优指南

```python
# backend/database/db.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    url,
    echo=False,                # 生产环境禁用SQL日志
    pool_size=10,              # 常驻连接数
    max_overflow=20,           # 峰值额外连接数
    pool_timeout=30,           # 获取连接超时(秒)
    pool_recycle=3600,         # ⭐ 1小时回收 (防止MySQL gone away)
    pool_pre_ping=True,        # ⭐ 使用前先ping (确保连接有效)
    pool_use_lifo=False,       # FIFO策略 (均匀使用连接)
)
```

#### 不同场景推荐配置

| 场景 | pool_size | max_overflow | pool_recycle | 说明 |
|------|----------|-------------|--------------|------|
| **低并发 API** | 5 | 10 | 3600 | 小团队内部系统 |
| **中并发 API** | 10 | 20 | 1800 | 中小型SaaS应用 ✅ |
| **高并发 API** | 20 | 40 | 900 | 大型电商平台 |
| **Celery Worker** | 3 | 5 | 1800 | 异步任务场景 |

### 3.2 Session 生命周期管理

#### 读写分离设计

```python
# backend/database/db.py

# ✅ 读操作 Session (无自动commit)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """只读操作使用"""
    async with async_db_session() as session:
        yield session
        # 自动关闭，但不commit

# ✅ 写操作 Session (自动commit/rollback)
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """写操作使用"""
    async with async_db_session.begin() as session:
        yield session
        # 成功自动commit，异常自动rollback

# Annotated 简化注入
CurrentSession = Annotated[AsyncSession, Depends(get_db)]
CurrentSessionTransaction = Annotated[AsyncSession, Depends(get_db_transaction)]
```

#### 使用示例

```python
# ✅ 正确：读操作用 CurrentSession
@router.get("/users")
async def get_users(db: CurrentSession):
    return await user_dao.get_list(db)

# ✅ 正确：写操作用 CurrentSessionTransaction
@router.post("/users")
async def create_user(db: CurrentSessionTransaction, obj: AddUserParam):
    await user_service.create(db=db, obj=obj)
    return response_base.success()
```

### 3.3 ORM 模型设计

#### SQLAlchemy 2.0 Mapped 语法

```python
# backend/app/admin/model/user.py
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base

class User(Base):
    """用户表"""
    __tablename__ = "sys_user"
    
    # ✅ 使用 Mapped 类型注解
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password: Mapped[str | None] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256), unique=True)
    status: Mapped[int] = mapped_column(default=1, comment="0停用 1正常")
    created_time: Mapped[datetime] = mapped_column(default_factory=datetime.now)
    
    # 逻辑外键（不使用 ForeignKey 约束，提高灵活性）
    dept_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
```

#### 关系映射

```python
# 多对多关联表
# backend/app/admin/model/m2m.py
from sqlalchemy import Table, Column, BigInteger

user_role = Table(
    "sys_user_role",
    Base.metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("role_id", BigInteger, primary_key=True),
)
```

### 3.4 CRUD 操作封装

#### 基于 sqlalchemy-crud-plus

```python
# backend/app/admin/crud/crud_user.py
from sqlalchemy_crud_plus import CRUDPlus, JoinConfig

class CRUDUser(CRUDPlus[User]):
    async def get_select(
        self,
        dept: int | None,
        username: str | None,
        status: int | None
    ) -> Select:
        """✅ 动态查询条件构建"""
        filters = {}
        
        if dept:
            filters["dept_id"] = dept
        if username:
            filters["username__like"] = f"%{username}%"  # 模糊查询
        if status is not None:
            filters["status"] = status
        
        # ✅ 关联查询
        return await self.select_order(
            "id", "desc",
            join_conditions=[
                JoinConfig(
                    model=Dept,
                    join_on=Dept.id == self.model.dept_id,
                    fill_result=True
                ),
                JoinConfig(
                    model=user_role,
                    join_on=user_role.c.user_id == self.model.id
                ),
                JoinConfig(
                    model=Role,
                    join_on=Role.id == user_role.c.role_id,
                    fill_result=True
                ),
            ],
            **filters
        )
```

---

## 第四部分：API 设计规范

### 4.1 RESTful API 设计

#### URL 命名规范

```python
# ✅ 正确
/api/v1/users              # 用户列表
/api/v1/users/{id}         # 单个用户
/api/v1/users/{id}/orders  # 用户的订单

# ❌ 错误
/api/v1/getUsers           # 不要在URL中使用动词
/api/v1/user               # 使用复数形式
```

#### HTTP 方法映射

| 方法 | URL | 语义 | 操作 |
|------|-----|------|------|
| `GET` | `/users` | 获取列表 | `user_dao.get_list()` |
| `GET` | `/users/{id}` | 获取单个 | `user_dao.get(id)` |
| `POST` | `/users` | 创建 | `user_dao.create()` |
| `PUT` | `/users/{id}` | 完整更新 | `user_dao.update(id)` |
| `PATCH` | `/users/{id}` | 部分更新 | `user_dao.partial_update(id)` |
| `DELETE` | `/users/{id}` | 删除 | `user_dao.delete(id)` |

### 4.2 统一响应格式

#### ResponseModel 设计

```python
# backend/common/response/response_schema.py
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

SchemaT = TypeVar("SchemaT")

class ResponseModel(BaseModel):
    """通用响应模型"""
    code: int = Field(200, description="状态码")
    msg: str = Field("Success", description="消息")
    data: Any | None = Field(None, description="数据")

class ResponseSchemaModel(ResponseModel, Generic[SchemaT]):
    """泛型响应模型（带类型提示）"""
    data: SchemaT  # ⭐ 指定具体的Schema类型
```

#### 使用示例

```python
@router.get("/users/{pk}")
async def get_user(pk: int) -> ResponseSchemaModel[GetUserInfoDetail]:
    #                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                          Swagger 自动生成完整文档
    user = await user_service.get_userinfo(pk=pk)
    return response_base.success(data=user)
```

### 4.3 参数验证

#### Pydantic Schema 设计模式

```python
# backend/app/admin/schema/user.py

# ✅ Base Schema (共享字段)
class UserBase(SchemaBase):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr | None = None

# ✅ Create Schema (创建时的字段)
class CreateUserParam(UserBase):
    password: str = Field(min_length=6, max_length=32)
    dept_id: int

# ✅ Update Schema (更新时的字段)
class UpdateUserParam(UserBase):
    status: int | None = None  # 可选字段

# ✅ Response Schema (返回给前端)
class GetUserDetail(UserBase):
    model_config = ConfigDict(from_attributes=True)  # 从ORM转换
    
    id: int
    created_time: datetime
    # ⭐ 不包含敏感字段 password
```

#### 参数来源注解

```python
from typing import Annotated
from fastapi import Query, Path, Body

@router.get("/users")
async def get_users(
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
    keyword: Annotated[str | None, Query(max_length=50)] = None,
):
    ...

@router.put("/users/{user_id}")
async def update_user(
    user_id: Annotated[int, Path(description="用户ID")],
    obj: Annotated[UpdateUserParam, Body(description="更新参数")],
):
    ...
```

### 4.4 分页查询标准

```python
# backend/common/pagination.py
from fastapi_pagination import Page, paginate

# ✅ 使用 fastapi-pagination 库
@router.get("/users")
async def get_users(
    db: CurrentSession,
    deps: DependsPagination,  # 自动注入 page/size
) -> ResponseSchemaModel[Page[GetUserDetail]]:
    stmt = await user_dao.get_select(...)
    page_data = await paging_data(db, stmt)
    return response_base.success(data=page_data)

# 返回格式
{
  "code": 200,
  "msg": "Success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  }
}
```

---

## 第五部分：Redis 使用规范

### 5.1 连接管理

```python
# backend/database/redis.py
from redis.asyncio import Redis, ConnectionPool

class RedisCli(Redis):
    """Redis 客户端封装"""
    
    def __init__(self):
        self.redis_client: Redis | None = None
    
    async def open(self):
        """初始化连接池"""
        pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DATABASE,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,          # 最大连接数
            socket_connect_timeout=5,    # 连接超时
            socket_keepalive=True,       # TCP keepalive
        )
        self.redis_client = Redis(connection_pool=pool)
    
    async def delete_prefix(self, prefix: str, exclude: str | None = None):
        """✅ 批量删除指定前缀的key"""
        keys = []
        async for key in self.redis_client.scan_iter(match=f"{prefix}*"):
            if exclude and key == exclude:
                continue
            keys.append(key)
        
        if keys:
            await self.redis_client.delete(*keys)

redis_client = RedisCli()
```

### 5.2 缓存策略

#### Key 命名规范

```python
# ✅ 推荐格式：{project}:{module}:{type}:{id}
"fba:user:123"                    # 用户缓存
"fba:token:456:abc-def"           # Token缓存
"fba:login:captcha:uuid-123"      # 验证码
"fba:celery:task_id_xxx"          # Celery任务

# ❌ 避免
"user123"                         # 无前缀，易冲突
"user:info:id:123"                # 过度嵌套
```

#### TTL 设置策略

| 数据类型 | TTL | 理由 |
|---------|-----|------|
| **Token** | 24小时 | 用户会话时长 |
| **验证码** | 5分钟 | 安全性要求 |
| **用户信息缓存** | 1小时 | 平衡性能与数据新鲜度 |
| **热点数据** | 10分钟 | 高频访问，需实时性 |
| **统计数据** | 1天 | 允许一定延迟 |

#### 缓存模式

```python
# ✅ Cache-Aside 模式（推荐）
async def get_user_with_cache(user_id: int) -> User:
    # 1. 先查缓存
    cache_key = f"{settings.USER_CACHE_PREFIX}:{user_id}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        return User.model_validate_json(cached)
    
    # 2. 缓存未命中，查数据库
    async with async_db_session() as db:
        user = await user_dao.get(db, user_id)
    
    # 3. 写入缓存
    await redis_client.setex(
        cache_key,
        3600,  # 1小时
        user.model_dump_json()
    )
    
    return user

# ✅ 缓存失效
async def update_user_invalidate_cache(user_id: int, obj: UpdateUserParam):
    async with async_db_session.begin() as db:
        await user_dao.update(db, user_id, obj)
    
    # ⭐ 删除缓存
    cache_key = f"{settings.USER_CACHE_PREFIX}:{user_id}"
    await redis_client.delete(cache_key)
```

### 5.3 Redis 作为 Celery Broker

#### 持久化配置

```bash
# redis.conf
appendonly yes                     # ⭐ 启用AOF
appendfsync everysec              # ⭐ 每秒同步 (性能与安全平衡)
save 900 1                        # RDB快照备份
save 300 10
save 60 10000
```

#### 队列监控

```python
# 查看队列长度
queue_length = await redis_client.llen("celery")

# 告警
if queue_length > 10000:
    logger.warning(f"Celery队列积压: {queue_length}")
```

---

## 第六部分：Celery 异步任务规范

### 6.1 Celery 配置

```python
# backend/app/task/celery.py
import celery
import celery_aio_pool

def init_celery() -> celery.Celery:
    # ✅ 启用异步任务池
    celery.app.trace.build_tracer = celery_aio_pool.build_async_tracer
    celery.app.trace.reset_worker_optimizations()
    
    # Broker 配置
    broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.CELERY_BROKER_REDIS_DATABASE}"
    
    # Result Backend 配置
    result_backend = f"db+postgresql+psycopg://{settings.DATABASE_USER}:密码@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_SCHEMA}"
    
    app = celery.Celery(
        "fba_celery",
        broker_url=broker_url,
        broker_connection_retry_on_startup=True,  # ⭐ 启动时重试连接
        result_backend=result_backend,
        result_extended=True,                     # ⭐ 存储扩展信息
        task_cls="backend.app.task.tasks.base:TaskBase",
        task_track_started=True,                  # ⭐ 追踪任务开始
        timezone=settings.DATETIME_TIMEZONE,
    )
    
    # 自动发现任务
    app.autodiscover_tasks(["backend.app.task.tasks"])
    
    return app

celery_app = init_celery()
```

### 6.2 任务定义规范

#### 任务基类

```python
# backend/app/task/tasks/base.py
from celery import Task
from sqlalchemy.exc import SQLAlchemyError

class TaskBase(Task):
    """Celery 任务基类"""
    
    # ✅ 自动重试配置
    autoretry_for = (SQLAlchemyError,)  # 遇到数据库错误自动重试
    max_retries = 5                      # 最多重试5次
    retry_backoff = True                 # 指数退避 (2s, 4s, 8s...)
    
    async def before_start(self, task_id: str, args, kwargs):
        """任务开始前钩子"""
        logger.info(f"Task {task_id} started")
    
    async def on_success(self, retval, task_id: str, args, kwargs):
        """任务成功后钩子"""
        logger.info(f"Task {task_id} succeeded")
    
    def on_failure(self, exc: Exception, task_id: str, args, kwargs, einfo):
        """任务失败后钩子"""
        logger.error(f"Task {task_id} failed: {exc}")
```

#### 任务定义示例

```python
# backend/app/task/tasks/tasks.py
from backend.app.task.celery import celery_app

# ✅ 异步任务
@celery_app.task(name="send_email")
async def send_email_task(user_id: int, subject: str, body: str):
    """发送邮件异步任务"""
    async with async_db_session() as db:
        user = await user_dao.get(db, user_id)
    
    # 调用SMTP服务
    await send_email(user.email, subject, body)
    
    return {"status": "sent", "email": user.email}

# ✅ 同步任务（遗留代码兼容）
@celery_app.task(name="legacy_task")
def legacy_task(data: dict):
    """同步任务"""
    time.sleep(10)
    return {"result": "ok"}
```

### 6.3 任务调用

```python
# FastAPI 路由中调用
@router.post("/send-notification")
async def send_notification(user_id: int, message: str):
    # ✅ delay() - 快速调用
    task = send_email_task.delay(user_id, "通知", message)
    
    return {"task_id": task.id}

# ✅ apply_async() - 高级调用
@router.post("/scheduled-notification")
async def scheduled_notification(user_id: int, message: str):
    from datetime import datetime, timedelta
    
    # 10分钟后执行
    eta = datetime.now() + timedelta(minutes=10)
    
    task = send_email_task.apply_async(
        args=[user_id, "定时通知", message],
        eta=eta,
        priority=5,                    # 优先级
        retry=True,
        retry_policy={
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
        }
    )
    
    return {"task_id": task.id, "eta": eta}
```

### 6.4 任务可靠性

#### 幂等性设计

```python
@celery_app.task(name="process_order", bind=True)
async def process_order_task(self, order_id: int):
    """✅ 幂等性示例"""
    async with async_db_session.begin() as db:
        order = await order_dao.get(db, order_id)
        
        # ⭐ 检查状态，避免重复处理
        if order.status != OrderStatus.PENDING:
            logger.warning(f"Order {order_id} already processed")
            return {"status": "skipped"}
        
        # 处理逻辑
        order.status = OrderStatus.PROCESSING
        await db.flush()
        
        # ... 业务逻辑 ...
        
        order.status = OrderStatus.COMPLETED
        await db.commit()
    
    return {"status": "success"}
```

#### 超时控制

```python
@celery_app.task(
    name="long_running_task",
    time_limit=3600,        # 硬限制：1小时后强制SIGKILL
    soft_time_limit=3300,   # 软限制：55分钟后抛出异常
)
async def long_running_task(data: dict):
    try:
        # ... 耗时操作 ...
        pass
    except SoftTimeLimitExceeded:
        # 优雅清理
        logger.warning("Task approaching time limit, cleaning up...")
        raise
```

---

## 第七部分：异常处理与日志规范

### 7.1 全局异常处理

```python
# backend/common/exception/exception_handler.py

def register_exception(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        """Pydantic 验证失败"""
        errors = exc.errors()
        msg = f"请求参数非法: {errors[0]['msg']}"
        
        return MsgSpecJSONResponse(
            status_code=422,
            content={"code": 422, "msg": msg, "data": errors if settings.ENVIRONMENT == "dev" else None}
        )
    
    @app.exception_handler(BaseExceptionError)
    async def custom_exception_handler(request: Request, exc: BaseExceptionError):
        """自定义业务异常"""
        return MsgSpecJSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "msg": exc.msg, "data": exc.data}
        )
    
    @app.exception_handler(Exception)
    async def unknown_handler(request: Request, exc: Exception):
        """未知异常"""
        if settings.ENVIRONMENT == "dev":
            msg = str(exc)
        else:
            msg = "服务器内部错误"  # ⭐ 生产环境隐藏细节
        
        return MsgSpecJSONResponse(
            status_code=500,
            content={"code": 500, "msg": msg, "data": None}
        )
```

### 7.2 自定义异常类

```python
# backend/common/exception/errors.py

class BaseExceptionError(Exception):
    """异常基类"""
    code: int = 400
    msg: str = "Bad Request"
    data: Any = None

class NotFoundError(BaseExceptionError):
    """资源不存在"""
    code = 404
    msg = "资源不存在"

class ConflictError(BaseExceptionError):
    """资源冲突"""
    code = 409
    msg = "资源已存在"

class TokenError(BaseExceptionError):
    """Token 异常"""
    code = 401
    msg = "Token 无效或已过期"
```

### 7.3 日志规范

```python
# backend/common/log.py
from loguru import logger

# ✅ 配置日志
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",               # 每天00:00轮转
    retention="30 days",            # 保留30天
    compression="zip",              # 压缩旧日志
    enqueue=True,                   # 异步写入
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]}</cyan> | <level>{message}</level>",
)

# ✅ 使用示例
logger.info("User logged in", extra={"request_id": "abc-123", "user_id": 456})
logger.error("Payment failed", extra={"request_id": "def-456", "order_id": 789, "error": str(exc)})
```

---

## 第八部分：中间件架构设计

### 8.1 中间件执行顺序

```python
# backend/core/registrar.py

def register_middleware(app: FastAPI):
    """⭐ 注册顺序：从下往上执行"""
    
    # 第7层：CORS (最先进入，最后返回)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 第6层：ContextVar (生成 TraceID)
    app.add_middleware(
        ContextMiddleware,
        plugins=[RequestIdPlugin(validate=True)]
    )
    
    # 第5层：Access Log
    app.add_middleware(AccessMiddleware)
    
    # 第4层：I18n (国际化)
    app.add_middleware(I18nMiddleware)
    
    # 第3层：JWT Authentication
    app.add_middleware(
        AuthenticationMiddleware,
        backend=JwtAuthMiddleware(),
        on_error=JwtAuthMiddleware.auth_exception_handler,
    )
    
    # 第2层：State (状态管理)
    app.add_middleware(StateMiddleware)
    
    # 第1层：Opera Log (最后进入，最先返回)
    app.add_middleware(OperaLogMiddleware)
```

### 8.2 操作日志中间件

```python
# backend/middleware/opera_log_middleware.py

class OperaLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""
    
    opera_log_queue: Queue = Queue(maxsize=100000)  # 内存队列
    
    async def dispatch(self, request: Request, call_next):
        # 1. 记录请求信息
        start_time = time.perf_counter()
        
        # 2. 执行请求
        response = await call_next(request)
        
        # 3. 计算耗时
        elapsed = round((time.perf_counter() - start_time) * 1000, 3)
        
        # 4. 构造日志对象
        opera_log = CreateOperaLogParam(
            trace_id=get_request_trace_id(),
            username=request.user.username if hasattr(request, "user") else None,
            method=request.method,
            path=request.url.path,
            ip=ctx.ip,
            cost_time=elapsed,
        )
        
        # 5. ⭐ 异步入队 (不阻塞请求)
        await self.opera_log_queue.put(opera_log)
        
        return response
    
    @classmethod
    async def consumer(cls):
        """后台消费者：批量写入数据库"""
        while True:
            logs = await batch_dequeue(
                cls.opera_log_queue,
                max_items=100,      # 每次最多100条
                timeout=60,         # 最多等待60秒
            )
            
            if logs:
                async with async_db_session.begin() as db:
                    await opera_log_service.bulk_create(db=db, objs=logs)
```

---

## 第九部分：安全性设计

### 9.1 JWT 认证

```python
# backend/common/security/jwt.py

async def create_access_token(user_id: int, *, multi_login: bool) -> AccessToken:
    """生成 Access Token"""
    expire = timezone.now() + timedelta(seconds=settings.TOKEN_EXPIRE_SECONDS)
    session_uuid = str(uuid.uuid4())  # ⭐ Session UUID
    
    # 生成 JWT
    access_token = jwt.encode({
        "session_uuid": session_uuid,
        "exp": timezone.to_utc(expire).timestamp(),
        "sub": str(user_id),
    }, settings.TOKEN_SECRET_KEY, settings.TOKEN_ALGORITHM)
    
    # ⭐ 存储到 Redis (支持单点登录控制)
    if not multi_login:
        await redis_client.delete_prefix(f"{settings.TOKEN_REDIS_PREFIX}:{user_id}")
    
    await redis_client.setex(
        f"{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}",
        settings.TOKEN_EXPIRE_SECONDS,
        access_token,
    )
    
    return AccessToken(access_token=access_token, expire_time=expire, session_uuid=session_uuid)

async def jwt_authentication(token: str) -> User:
    """JWT 认证 + 多级缓存"""
    # 1. 解析 Token
    payload = jwt_decode(token)
    user_id = payload.id
    
    # 2. 验证 Token 有效性
    redis_token = await redis_client.get(f"{settings.TOKEN_REDIS_PREFIX}:{user_id}:{payload.session_uuid}")
    if not redis_token or token != redis_token:
        raise errors.TokenError(msg="Token 已失效")
    
    # 3. ⭐ 查询用户缓存
    cache_user = await redis_client.get(f"{settings.JWT_USER_REDIS_PREFIX}:{user_id}")
    if cache_user:
        return User.model_validate_json(cache_user)
    
    # 4. 缓存未命中，查数据库
    async with async_db_session() as db:
        user = await user_dao.get_join(db, user_id=user_id)
        await redis_client.setex(
            f"{settings.JWT_USER_REDIS_PREFIX}:{user_id}",
            settings.TOKEN_EXPIRE_SECONDS,
            user.model_dump_json(),
        )
    
    return user
```

### 9.2 RBAC 权限控制

```python
# backend/common/security/rbac.py

async def rbac_verify(request: Request, required_permission: str) -> bool:
    """RBAC 权限验证"""
    user = request.user
    
    # 1. 超级管理员：通过所有权限检查
    if user.is_superuser:
        return True
    
    # 2. 获取用户所有角色的权限
    user_permissions = set()
    for role in user.roles:
        for menu in role.menus:
            if menu.permission:
                user_permissions.add(menu.permission)
    
    # 3. 检查是否拥有所需权限
    if required_permission not in user_permissions:
        raise errors.AuthorizationError(msg=f"缺少权限: {required_permission}")
    
    return True

# 使用示例
@router.post("/reports")
async def generate_report(
    deps: Annotated[bool, Depends(RequestPermission("sys:report:generate"))],
    deps_rbac: DependsRBAC,
):
    ...
```

### 9.3 密码安全

```python
# backend/app/admin/utils/password_security.py
import bcrypt

def get_hash_password(password: str, salt: bytes) -> str:
    """密码加密"""
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def password_verify(plain_password: str, hashed_password: str) -> bool:
    """密码验证"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

async def validate_new_password(db: AsyncSession, user_id: int, new_password: str):
    """密码策略验证"""
    # 1. 长度检查
    if len(new_password) < settings.USER_PASSWORD_MIN_LENGTH:
        raise errors.RequestError(msg=f"密码长度不能少于 {settings.USER_PASSWORD_MIN_LENGTH} 位")
    
    # 2. 历史密码检查
    histories = await password_history_dao.get_recent(db, user_id, count=settings.USER_PASSWORD_HISTORY_CHECK_COUNT)
    
    for history in histories:
        if password_verify(new_password, history.password):
            raise errors.RequestError(msg=f"不能使用最近 {settings.USER_PASSWORD_HISTORY_CHECK_COUNT} 次使用过的密码")
```

---

## 第十部分：性能优化策略

### 10.1 数据库性能优化

#### N+1 查询问题

```python
# ❌ 错误：N+1 查询
async def get_users_with_roles():
    users = await user_dao.get_all(db)
    for user in users:
        user.roles = await role_dao.get_by_user(db, user.id)  # N次查询

# ✅ 正确：使用 JOIN
async def get_users_with_roles():
    stmt = await user_dao.get_select(
        join_conditions=[
            JoinConfig(model=user_role, join_on=...),
            JoinConfig(model=Role, join_on=..., fill_result=True),
        ]
    )
    return await db.execute(stmt)
```

#### 批量操作

```python
# ❌ 错误：循环插入
for item in items:
    await db.execute(insert(Task).values(**item))
    await db.commit()  # 每次都commit

# ✅ 正确：批量插入
await db.execute(insert(Task), items)
await db.commit()  # 一次commit
```

### 10.2 缓存优化

#### 缓存穿透防护

```python
async def get_user_safe(user_id: int) -> User | None:
    cache_key = f"user:{user_id}"
    
    # 1. 查缓存
    cached = await redis_client.get(cache_key)
    if cached == "NULL":  # ⭐ 空对象标记
        return None
    if cached:
        return User.model_validate_json(cached)
    
    # 2. 查数据库
    async with async_db_session() as db:
        user = await user_dao.get(db, user_id)
    
    # 3. 缓存结果（包括空结果）
    if user:
        await redis_client.setex(cache_key, 3600, user.model_dump_json())
    else:
        await redis_client.setex(cache_key, 60, "NULL")  # ⭐ 缓存空结果（短TTL）
    
    return user
```

### 10.3 异步并发

```python
# ✅ 使用 asyncio.gather 并发执行
async def get_user_dashboard(user_id: int):
    user, orders, messages = await asyncio.gather(
        user_service.get_user(user_id),
        order_service.get_user_orders(user_id),
        message_service.get_user_messages(user_id),
    )
    
    return {
        "user": user,
        "orders": orders,
        "messages": messages,
    }
```

---

## 第十一部分：可观测性

### 11.1 TraceID 传播

```python
# backend/utils/trace_id.py
from starlette_context import context

def get_request_trace_id() -> str:
    """获取当前请求的 TraceID"""
    return context.get("X-Request-ID", "-")

# 使用
logger.info("Processing order", extra={"trace_id": get_request_trace_id()})
```

### 11.2 Prometheus 指标

```python
# backend/common/prometheus/instruments.py
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["app_name", "method", "path"]
)

# 响应时间分布
RESPONSE_TIME_HISTOGRAM = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["app_name", "method", "path"]
)

# 并发请求数
IN_PROGRESS_GAUGE = Gauge(
    "http_requests_in_progress",
    "HTTP requests in progress",
    ["app_name", "method", "path"]
)

# 埋点
REQUEST_COUNTER.labels(app_name="fba", method="POST", path="/api/v1/users").inc()
RESPONSE_TIME_HISTOGRAM.labels(app_name="fba", method="POST", path="/api/v1/users").observe(0.123)
```

---

## 第十二部分：测试策略

### 12.1 单元测试

```python
# tests/test_user_service.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(async_client: AsyncClient, db_session):
    """测试用户创建"""
    response = await async_client.post(
        "/api/v1/users",
        json={
            "username": "testuser",
            "password": "Pass123!",
            "email": "test@example.com",
        }
    )
    
    assert response.status_code == 200
    assert response.json()["code"] == 200
    
    # 验证数据库
    async with db_session() as db:
        user = await user_dao.get_by_username(db, "testuser")
        assert user is not None
        assert user.email == "test@example.com"
```

---

## 第十三部分：部署与运维

### 13.1 Docker 容器化

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install uv && uv pip install --system -r pyproject.toml

# 复制代码
COPY backend/ ./backend/

# 启动
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: "3.8"

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
  
  celery:
    build: .
    command: celery -A backend.app.task.celery worker -l info
    depends_on:
      - redis
      - postgres
```

---

## 第十四部分：代码质量

### 14.1 Ruff 配置

```toml
# .ruff.toml
line-length = 120
target-version = "py310"

[lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[format]
quote-style = "single"
indent-style = "space"
```

---

## 第十五部分：完整业务示例

### 15.1 用户注册登录流程

```python
# 1. Schema 定义
class RegisterParam(SchemaBase):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=32)
    email: EmailStr

# 2. API 层
@router.post("/auth/register")
async def register(
    db: CurrentSessionTransaction,
    obj: RegisterParam
) -> ResponseSchemaModel[GetUserDetail]:
    user = await auth_service.register(db=db, obj=obj)
    return response_base.success(data=user)

# 3. Service 层
class AuthService:
    @staticmethod
    async def register(*, db: AsyncSession, obj: RegisterParam) -> User:
        # 业务规则验证
        if await user_dao.get_by_username(db, obj.username):
            raise errors.ConflictError(msg="用户名已存在")
        
        if await user_dao.check_email(db, obj.email):
            raise errors.ConflictError(msg="邮箱已被注册")
        
        # 密码加密
        salt = bcrypt.gensalt()
        obj.password = get_hash_password(obj.password, salt)
        
        # 创建用户
        await user_dao.add(db, obj)
        
        # ⭐ 发送异步任务
        send_welcome_email.delay(user.id)
        
        return user

# 4. CRUD 层
class CRUDUser(CRUDPlus[User]):
    async def add(self, db: AsyncSession, obj: RegisterParam) -> None:
        new_user = User(**obj.model_dump())
        db.add(new_user)
        await db.flush()
```

---

## 附录

### A. 性能调优 Checklist

- [ ] 数据库索引优化
- [ ] 连接池参数调优
- [ ] Redis 缓存策略
- [ ] 异步并发优化
- [ ] N+1 查询消除
- [ ] 批量操作替代循环
- [ ] MsgSpec 序列化加速
- [ ] Celery Worker 数量调整

### B. 常见问题

**Q: 如何选择 Redis 还是 RabbitMQ 作为 Broker？**  
A: 中小规模项目推荐 Redis（性能高、配置简单）；金融/医疗等高可靠场景推荐 RabbitMQ。

**Q: Session 是否需要手动 commit？**  
A: 不需要。使用 `CurrentSessionTransaction` 会自动管理事务。

**Q: 如何避免操作日志丢失？**  
A: 可以将内存队列改为 Redis 队列，或实现优雅关闭机制。

---

**文档版本**: v1.0  
**最后更新**: 2026-01-05  
**维护者**: 架构团队
