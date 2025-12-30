# 并发控制优化方案

## 问题描述

当前系统存在**双重并发控制**：

1. **Celery 层**：`--concurrency=8` 控制任务级并发
2. **任务内部**：`Semaphore(5)` 控制概念级并发

这导致：
- 理论最大并发：8 × 5 = 40 个概念同时生成
- 数据库连接池压力巨大
- 资源利用不合理

## 解决方案：移除任务内部 Semaphore

### 原理

```
旧架构（双重控制）：
Celery --concurrency=8
  ├── Task 1: Semaphore(5) → 5 个概念并发
  ├── Task 2: Semaphore(5) → 5 个概念并发
  └── ...
  └── Task 8: Semaphore(5) → 5 个概念并发
  总计：8 × 5 = 40 个概念并发

新架构（单层控制）：
Celery --concurrency=8
  ├── Task 1: 处理路线图 A（30 个概念，asyncio.gather）
  ├── Task 2: 处理路线图 B（25 个概念，asyncio.gather）
  └── ...
  └── Task 8: 处理路线图 H（20 个概念，asyncio.gather）
  总计：最多 8 个路线图同时处理
```

### 为什么这样更好？

1. **异步 I/O 特性**
   - `asyncio.gather()` 启动 30 个协程，但它们大部分时间在**等待 LLM 响应**
   - 等待期间不占用 CPU 和数据库连接
   - 只在保存结果时短暂使用数据库连接

2. **数据库连接实际使用**
   ```python
   # 伪代码
   async def generate_content(concept):
       # 1. LLM 调用（等待，不占用连接）
       tutorial = await llm.generate_tutorial(concept)  # 20-30秒
       
       # 2. 保存（短暂占用连接）
       async with db.session() as session:
           await session.save(tutorial)  # 0.1秒
       
       # 连接立即释放
   ```

3. **真实并发计算**
   - 虽然启动了 8 × 30 = 240 个协程
   - 但数据库连接只在保存时使用（0.1秒）
   - LLM 调用期间（20-30秒）不占用连接
   - **实际同时占用的连接数 << 理论值**

### 修改内容

#### 1. 移除 Semaphore

**文件**：`backend/app/tasks/content_generation_tasks.py`

```python
# 移除
# max_concurrent = config.parallel_tutorial_limit
# semaphore = asyncio.Semaphore(max_concurrent)

# 修改 _process_single_concept 函数签名
async def _process_single_concept(
    concept_id: str,
    concept_map: dict[str, Concept],
    preferences: LearningPreferences,
    agent_factory: Any,
    # semaphore: asyncio.Semaphore,  # 移除这个参数
    total_concepts: int,
    progress_counter: dict[str, int],
    completed_buffer: dict[str, tuple[Any, Any, Any]],
    roadmap_id: str,
    task_id: str,
    batch_save_threshold: int = 5,
):
    # 移除 async with semaphore: 包装
    # 直接执行逻辑
    ...
```

#### 2. 调整 Celery 并发数

由于移除了任务内部限制，需要降低 Celery 并发数以避免资源耗尽：

```bash
# 旧配置（双重控制）
--concurrency=8  # 8 × 5 = 40 个概念并发

# 新配置（单层控制）
--concurrency=4  # 4 个路线图并发，每个路线图内部并行处理
```

#### 3. 移除配置项

**文件**：`backend/app/config/settings.py`

```python
# 移除或标记为废弃
# PARALLEL_TUTORIAL_LIMIT: int = Field(5, description="...")
```

**文件**：`backend/app/core/orchestrator/base.py`

```python
# WorkflowConfig 中移除
# parallel_tutorial_limit: int = 5
```

### 并发数推荐

| 场景 | Celery 并发数 | 原因 |
|------|--------------|------|
| 开发环境（本地） | `--concurrency=2` | 资源有限 |
| 生产环境（4核8G） | `--concurrency=4` | 均衡性能和资源 |
| 生产环境（8核16G） | `--concurrency=8` | 充分利用资源 |

### 数据库连接池配置

移除 Semaphore 后，需要确保数据库连接池足够：

```python
# backend/app/db/session.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,           # 基础连接数
    max_overflow=30,        # 额外连接数
    pool_pre_ping=True,     # 检查连接有效性
)
```

**计算公式**：
```
最大连接数 = Celery并发数 × 平均路线图概念数 × 并发保存概率
          = 4 × 30 × 0.1  # 假设任意时刻只有 10% 在保存
          = 12 个连接

建议配置：pool_size=20, max_overflow=30 (总计 50)
```

## 迁移步骤

1. **备份当前配置**
   ```bash
   git commit -m "Backup before concurrent optimization"
   ```

2. **修改代码**
   - 移除 `content_generation_tasks.py` 中的 Semaphore
   - 移除 `retry_service.py` 中的 Semaphore
   - 移除配置项

3. **调整 Celery 启动参数**
   ```bash
   celery -A app.core.celery_app worker \
     --queues=content_generation \
     --concurrency=4 \
     -n content@%h
   ```

4. **监控测试**
   - 监控数据库连接数
   - 监控内存使用
   - 监控任务执行时间

5. **调优**
   - 根据实际情况调整 `--concurrency` 参数
   - 调整数据库连接池大小

## 预期效果

### 性能提升
- ✅ 移除不必要的并发控制开销
- ✅ 任务内部充分利用 asyncio 异步特性
- ✅ 减少上下文切换

### 资源优化
- ✅ 数据库连接使用更合理（只在需要时占用）
- ✅ 内存占用更可控（Celery 层控制）
- ✅ 避免连接池耗尽

### 代码简化
- ✅ 移除双重控制的复杂性
- ✅ 配置更直观（只需调整 Celery 并发数）
- ✅ 更容易理解和维护

## 注意事项

1. **LLM API 限流**
   - 移除 Semaphore 后，单个任务可能同时发起 30+ LLM 请求
   - 如果 LLM 提供商有严格限流，可能触发限流
   - 解决方案：在 LLM 客户端层添加重试逻辑

2. **内存监控**
   - 每个 LLM 调用会占用一定内存（存储上下文和响应）
   - 监控 Worker 进程内存使用
   - 如果内存占用过高，降低 Celery 并发数

3. **渐进式迁移**
   - 先在开发环境测试
   - 使用 `--concurrency=2` 进行保守测试
   - 逐步提高并发数
   - 监控系统表现

## 总结

移除任务内部的 Semaphore 是一个**正确的优化方向**，因为：

1. ✅ Celery 本身就是为了解决并发问题
2. ✅ 双重控制增加复杂性，没有实际收益
3. ✅ AsyncIO 的异步特性天然适合高并发 I/O 操作
4. ✅ 数据库连接只在需要时短暂占用，不需要额外限制

**关键是**：通过 Celery 的 `--concurrency` 参数控制全局并发，让每个任务内部充分利用 AsyncIO 的异步能力。

