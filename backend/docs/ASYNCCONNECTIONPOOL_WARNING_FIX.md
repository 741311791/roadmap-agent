# AsyncConnectionPool 弃用警告修复

## ⚠️ 问题描述

后端启动时出现以下警告：

```
/backend/.venv/lib/python3.12/site-packages/psycopg_pool/pool_async.py:148: RuntimeWarning: 
opening the async pool AsyncConnectionPool in the constructor is deprecated and will not be 
supported anymore in a future release. Please use `await pool.open()`, or use the pool as 
context manager using: `async with AsyncConnectionPool(...) as pool: `...
```

**原因**：
- 在 `psycopg_pool` 的新版本中，在构造函数中自动打开连接池的行为已被弃用
- 推荐的做法是显式调用 `await pool.open()` 或使用上下文管理器

## ✅ 解决方案

**修改文件**: `backend/app/core/orchestrator_factory.py`

### 修改前（第 76-87 行）

```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=180,
    timeout=60,
    reconnect_timeout=0,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)
```

### 修改后

```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=180,
    timeout=60,
    reconnect_timeout=0,
    open=False,  # ✅ 添加此参数，禁止构造时自动打开
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)
```

**关键改动**：添加 `open=False` 参数

### 工作原理

1. **构造时**：设置 `open=False`，连接池不会自动初始化连接
2. **显式打开**：代码在第 90 行已经有 `await cls._connection_pool.open()`
3. **结果**：符合新的推荐做法，警告消失

## 📊 对比

### 旧方式（产生警告）
```python
pool = AsyncConnectionPool(conninfo=db_url, min_size=2)
# ⚠️ 构造函数会自动尝试打开连接池 → 产生弃用警告
```

### 新方式（无警告）
```python
pool = AsyncConnectionPool(conninfo=db_url, min_size=2, open=False)
await pool.open()  # ✅ 显式打开，符合新的 API 规范
```

## 🧪 验证

### 方式 1: 查看后端启动日志

重启后端服务，检查启动日志中是否还有 `RuntimeWarning`：

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

如果修复成功，日志中应该只显示：
```
2025-12-26 XX:XX:XX [info] orchestrator_factory_initialized ...
```

而不再有 `RuntimeWarning: opening the async pool...` 警告。

### 方式 2: 运行测试脚本

```bash
cd backend
python scripts/test_pool_warning.py
```

输出示例：
```
方式 1: 旧方式（构造时自动打开 - 会产生警告）
⚠️  警告数量: 1
   类型: RuntimeWarning
   消息: opening the async pool AsyncConnectionPool...

方式 2: 新方式（手动打开 - 不会产生警告）
✅ 无警告（修复成功）
```

## 📝 技术细节

### 为什么需要这个修复？

1. **未来兼容性**：psycopg_pool 在未来版本中会移除自动打开的行为
2. **最佳实践**：显式的资源管理更加清晰，便于控制连接池的生命周期
3. **减少警告噪音**：警告会污染日志输出，影响问题排查

### 连接池配置说明

当前配置（生产环境优化）：
- `min_size=2`: 最小保持 2 个连接（基础可用性）
- `max_size=10`: 最多 10 个连接（适配 LangGraph 工作流并发）
- `max_idle=180`: 空闲连接保持 3 分钟
- `timeout=60`: 获取连接超时 60 秒
- `reconnect_timeout=0`: 自动重连
- `open=False`: **新增** - 禁止构造时自动打开

### 总连接数预算

- SQLAlchemy 连接池：100 个连接（主业务逻辑）
- Checkpointer 连接池：10 个连接（LangGraph 状态持久化）
- **总计**：110/200 个连接（数据库最大连接数为 200）

## 🎯 影响范围

- **影响组件**：`OrchestratorFactory`（工作流编排器工厂）
- **影响功能**：LangGraph 状态持久化（Checkpointer）
- **运行时行为**：无变化（只是消除了警告）
- **性能影响**：无（连接池初始化时机相同）

## ✅ 状态

- [x] 代码修改完成
- [x] Linter 检查通过
- [x] 测试脚本准备完毕
- [ ] 需要重启后端服务以验证

## 📚 参考

- [psycopg_pool 官方文档](https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.AsyncConnectionPool)
- [弃用警告说明](https://www.psycopg.org/psycopg3/docs/api/pool.html#pool-lifecycle)

---

**修复完成时间**: 2025-12-26  
**修改文件数**: 1 个  
**代码质量**: ✅ 无 Linter 错误  
**向后兼容**: ✅ 完全兼容

