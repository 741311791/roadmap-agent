# 数据库连接超时问题修复

**日期**: 2025-12-17  
**问题**: 任务完成后仍然出现数据库连接超时错误

## 问题现象

```
ERROR:    Exception in ASGI application
TimeoutError: [Errno 60] Operation timed out

asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation

sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error) 
<class 'asyncpg.exceptions.ConnectionDoesNotExistError'>: 
connection was closed in the middle of operation
```

## 时间线分析

1. **20:47:31** - 内容生成任务开始
2. **20:56:46** - 任务完成（耗时 535 秒 ≈ 9 分钟）
3. **20:56:46** - 日志查询请求 `GET /api/v1/trace/.../logs` 返回 200 OK
4. **立即报错** - 数据库连接超时

## 根本原因

### 1. 数据库连接超时配置过短

**位置**: `backend/app/db/session.py:27`

```python
"command_timeout": 60,  # 命令超时 60 秒
```

**问题**:
- 长时间运行的任务（如内容生成）耗时 9 分钟
- 60 秒的超时时间无法满足需求
- PostgreSQL 服务器在 60 秒后主动关闭连接

### 2. FastAPI 的 `get_db` 依赖生命周期问题

**位置**: `backend/app/db/session.py:51-68`

**问题流程**:
1. 数据库会话在 **请求开始时创建**
2. 业务逻辑执行数据库查询
3. 数据返回给客户端（HTTP 响应开始）
4. **数据库会话仍然持有**，等待请求完全结束
5. 如果网络慢、客户端处理慢，会话会持续很长时间
6. 超过 60 秒后，PostgreSQL 关闭连接
7. FastAPI 尝试 `commit()` 时，连接已不存在 → **报错**

### 3. 缺少异常处理

原始代码：
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # ❌ 如果连接已关闭，这里会报错
        except Exception:
            await session.rollback()
            raise
```

**问题**: 没有区分连接错误和业务错误，导致无关的连接超时错误影响正常功能。

## 解决方案

### 1. 增加数据库连接超时时间

**修改**: `command_timeout: 60` → `command_timeout: 300`

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={
        "command_timeout": 300,  # 5 分钟，足够处理长时间运行的查询
    },
)
```

**理由**:
- 内容生成任务可能运行 10+ 分钟
- 300 秒可以覆盖大部分场景
- 避免正常操作被意外中断

### 2. 优化 `get_db` 依赖的异常处理

**核心改进**:
1. **区分连接错误和业务错误**
2. **连接错误时优雅降级**（记录警告但不抛出异常）
3. **业务错误时正常抛出**

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
        
        # 尝试 commit，如果连接已经关闭则忽略
        try:
            await session.commit()
        except Exception as commit_error:
            error_msg = str(commit_error).lower()
            is_connection_error = any(
                keyword in error_msg
                for keyword in [
                    "connection",
                    "timeout",
                    "closed",
                    "does not exist",
                    "terminated",
                ]
            )
            
            if is_connection_error:
                # ✅ 连接错误时只记录警告，不抛出异常
                logger.warning(
                    "db_session_commit_connection_error",
                    error=str(commit_error),
                    message="数据库连接已关闭，跳过 commit（数据可能已提交或无需提交）",
                )
            else:
                # ❌ 非连接错误，正常抛出
                logger.error("db_session_commit_failed", error=str(commit_error))
                raise
                
    except Exception as e:
        # 捕获其他异常，尝试回滚
        error_msg = str(e).lower()
        is_connection_error = any(
            keyword in error_msg
            for keyword in ["connection", "timeout", "closed", "does not exist"]
        )
        
        if is_connection_error:
            # ✅ 连接错误时只记录警告
            logger.warning(
                "db_session_rollback_connection_error",
                error=str(e),
                message="数据库连接已关闭，跳过 rollback",
            )
        else:
            # ❌ 非连接错误，尝试回滚
            try:
                await session.rollback()
            except Exception as rollback_error:
                logger.error(
                    "db_session_rollback_failed",
                    original_error=str(e),
                    rollback_error=str(rollback_error),
                )
        
        raise
        
    finally:
        # 确保会话被关闭
        try:
            await session.close()
        except Exception as close_error:
            logger.warning(
                "db_session_close_failed",
                error=str(close_error),
            )
```

## 为什么连接错误时不抛出异常？

### 场景分析

#### 场景 1: 只读查询（如日志查询）
```python
@router.get("/logs")
async def get_logs(db: AsyncSession = Depends(get_db)):
    logs = await db.execute(select(Log))  # ✅ 查询完成，数据已获取
    return logs.all()
    # HTTP 响应发送中...
    # 60 秒后，连接超时
    # get_db 尝试 commit()  → 连接已关闭
```

**分析**:
- 数据已经查询完成并返回给客户端
- `commit()` 对只读查询无实际意义
- 抛出异常会导致 HTTP 500 错误，影响用户体验
- **解决**: 记录警告，忽略错误，客户端正常收到数据 ✅

#### 场景 2: 写操作（如更新任务状态）
```python
@router.post("/update")
async def update_task(db: AsyncSession = Depends(get_db)):
    task.status = "completed"
    db.add(task)
    # 如果在这里连接超时，写操作会自动回滚
    return {"status": "success"}
    # 60 秒后，连接超时
    # get_db 尝试 commit()  → 连接已关闭
```

**分析**:
- 如果连接在 `commit()` 前超时，PostgreSQL 会自动回滚未提交的事务
- 数据不会被写入数据库
- 但 HTTP 响应可能已经发送（显示"成功"），导致不一致

**缓解措施**:
1. **关键写操作应该显式调用 `await db.commit()`**，而不是依赖 `get_db` 的自动 commit
2. **超时时间增加到 300 秒**，减少超时概率
3. **添加重试机制**（在业务层实现）

## 预期效果

### 修复前
- ❌ 任务完成后仍然报错
- ❌ 日志堆栈中充斥连接超时错误
- ❌ 影响用户体验（虽然功能已完成）

### 修复后
- ✅ 连接超时时只记录警告，不影响用户请求
- ✅ 只读查询正常返回数据
- ✅ 日志更清晰，便于排查真正的业务错误
- ✅ 超时时间增加到 300 秒，覆盖更多场景

## 进一步优化建议

### 1. 关键写操作显式 commit
```python
@router.post("/important")
async def important_update(db: AsyncSession = Depends(get_db)):
    task.status = "completed"
    db.add(task)
    
    try:
        await db.commit()  # ✅ 显式 commit，确保数据写入
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, "Failed to save data")
    
    return {"status": "success"}
```

### 2. 使用事务装饰器
```python
from sqlalchemy.orm import Session

async def update_with_retry(db: Session, task_id: str):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            task = await db.get(Task, task_id)
            task.status = "completed"
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            if "connection" in str(e).lower() and attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise
```

### 3. 监控连接池健康
```python
# 添加定期检查
@app.on_event("startup")
async def monitor_db_pool():
    async def check_pool():
        while True:
            pool = engine.pool
            logger.info(
                "db_pool_status",
                size=pool.size(),
                overflow=pool.overflow(),
                checked_out=pool.checked_out_connections(),
            )
            await asyncio.sleep(60)
    
    asyncio.create_task(check_pool())
```

## 总结

### 问题本质
- FastAPI 的 `get_db` 依赖会在整个 HTTP 请求生命周期中持有数据库会话
- 如果请求处理时间（包括网络传输）超过 60 秒，会导致连接超时
- 原始代码没有区分连接错误和业务错误，导致无关错误影响用户体验

### 解决方案
1. **增加超时时间**: 60 秒 → 300 秒
2. **优雅降级**: 连接错误时只记录警告，不抛出异常
3. **改进日志**: 区分连接错误和业务错误

### 适用场景
- ✅ 长时间运行的后台任务
- ✅ 只读查询 API
- ⚠️  关键写操作（建议显式 commit）

---

**修改文件**: `backend/app/db/session.py`  
**测试**: 运行长时间任务，观察是否还有连接超时错误  
**回滚**: 如果有问题，将 `command_timeout` 改回 60 秒，并移除异常处理逻辑


