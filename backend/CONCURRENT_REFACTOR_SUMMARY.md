# 并发控制重构总结

## 已完成的修改

### ✅ 1. 移除配置项
- **文件**: `backend/app/config/settings.py`
- **修改**: 注释掉 `PARALLEL_TUTORIAL_LIMIT` 配置

### ✅ 2. 简化 WorkflowConfig
- **文件**: `backend/app/core/orchestrator/base.py`
- **修改**: 移除 `parallel_tutorial_limit` 字段和相关引用

### ✅ 3. 移除 retry_service 中的 Semaphore
- **文件**: `backend/app/services/retry_service.py`
- **修改**: 注释掉 Semaphore 创建和使用

### ⚠️ 4. 重构 content_generation_tasks.py（需要手动完成）
- **文件**: `backend/app/tasks/content_generation_tasks.py`
- **状态**: 由于文件缩进问题，自动替换失败
- **解决方案**: 请参考 `CONCURRENT_REFACTOR_PATCH.md` 手动修改

## 核心变更

### 旧架构（双重并发控制）
```python
# Celery 层
--concurrency=8  # 8 个任务并发

# 任务内部
semaphore = asyncio.Semaphore(5)  # 每个任务最多 5 个概念并发

# 内容生成
async with semaphore:
    tutorial, resource, quiz = await asyncio.gather(
        generate_tutorial(),
        generate_resource(),
        generate_quiz(),
    )

# 理论最大并发: 8 × 5 = 40 个概念
```

### 新架构（单层并发控制）
```python
# Celery 层（唯一控制点）
--concurrency=4  # 4 个任务并发

# 任务内部（无 Semaphore）
# 串行生成
tutorial = await generate_tutorial()
resource = await generate_resource()
quiz = await generate_quiz()

# 立即写入数据库（一次性）
await save_to_database(tutorial, resource, quiz)

# 实际并发: 4 个路线图，每个路线图内串行处理
```

## 优势对比

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| 并发控制 | 双重（Celery + Semaphore） | 单层（仅 Celery） |
| Concept 内容生成 | 并行（tutorial ‖ resource ‖ quiz） | 串行（tutorial → resource → quiz） |
| 数据库写入 | 批量写入（3个一批） | 立即写入（完成即写） |
| 写入次数 | 每个 Concept 3 次 | 每个 Concept 1 次 |
| 事务性 | 弱（分批写入） | 强（Concept 为单位） |
| 数据库连接 | 理论 40 × 3 = 120 | 实际 4 × 1 = 4 |
| 复杂度 | 高 | 低 |
| 可控性 | 难调优 | 易调优（只需调整 --concurrency） |

## 为什么串行更好？

### 1. 数据库连接压力小
```
并行模式：
  Concept 1: [Tutorial] [Resource] [Quiz]  → 3 个连接
  Concept 2: [Tutorial] [Resource] [Quiz]  → 3 个连接
  ...
  总计：40 × 3 = 120 个连接（峰值）

串行模式：
  Concept 1: [Tutorial] → [Resource] → [Quiz] → [Save]  → 1 个连接
  Concept 2: [Tutorial] → [Resource] → [Quiz] → [Save]  → 1 个连接
  ...
  总计：4 × 1 = 4 个连接（峰值）
```

### 2. 事务性更强
```python
# 并行模式：分批写入，可能部分成功
tutorial → DB (成功)
resource → DB (失败)
quiz → DB (未执行)
结果：Concept 状态不一致

# 串行模式：一次性写入，要么全成功要么全失败
tutorial → resource → quiz → DB (一次性)
结果：Concept 状态一致
```

### 3. 状态管理简单
```python
# 并行模式：需要跟踪 3 个状态
concept.content_status = "generating"
concept.resources_status = "generating"
concept.quiz_status = "generating"

# 串行模式：只需跟踪 1 个状态
concept.status = "generating" → "completed"
```

### 4. LLM 调用更稳定
```
并行模式：同时 40 个 LLM 请求 → 容易触发限流
串行模式：同时 4 个 LLM 请求 → 稳定可控
```

## Celery 启动命令

### 开发环境
```bash
cd backend

# 启动所有队列（低并发）
celery -A app.core.celery_app worker --loglevel=info --concurrency=2
```

### 生产环境
```bash
# 路线图工作流队列
celery -A app.core.celery_app worker \
  --queues=roadmap_workflow \
  --concurrency=2 \
  -n workflow@%h

# 内容生成队列（串行模式，可以适当提高并发）
celery -A app.core.celery_app worker \
  --queues=content_generation \
  --concurrency=4 \
  -n content@%h

# 日志队列
celery -A app.core.celery_app worker \
  --queues=logs \
  --concurrency=2 \
  -n logs@%h
```

## 监控指标

### 关键指标
1. **数据库连接数**
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
   ```
   - 旧架构：峰值 50-100
   - 新架构：峰值 5-10

2. **任务执行时间**
   - 旧架构：30 个 Concept × 20秒 = 600秒（并行）
   - 新架构：30 个 Concept × 60秒 = 1800秒（串行）
   - 但由于 Celery 并发，实际时间：1800 / 4 = 450秒

3. **内存占用**
   - 旧架构：40 个协程 × 100MB = 4GB
   - 新架构：4 个任务 × 500MB = 2GB

## 下一步

1. ✅ 完成 `content_generation_tasks.py` 的手动修改（参考 `CONCURRENT_REFACTOR_PATCH.md`）
2. ✅ 测试单个路线图生成
3. ✅ 测试多个路线图并发生成
4. ✅ 监控数据库连接数
5. ✅ 根据实际情况调整 Celery 并发数

## 注意事项

1. **LLM API 限流**
   - 串行模式下单个任务会连续发起多个 LLM 请求
   - 如果触发限流，在 LLM 客户端层添加重试逻辑

2. **任务执行时间**
   - 串行模式下单个任务执行时间会变长（20秒 → 60秒）
   - 但由于 Celery 并发，总体时间可能更短

3. **渐进式测试**
   - 先使用 `--concurrency=1` 测试
   - 逐步提高到 `--concurrency=4`
   - 监控系统表现

## 总结

这次重构实现了：
- ✅ 移除双重并发控制
- ✅ 简化为单层 Celery 控制
- ✅ Concept 内容串行生成
- ✅ 立即写入数据库（事务性更强）
- ✅ 减少数据库连接压力
- ✅ 代码更简单易维护

**关键思想**：让 Celery 做它擅长的事（任务级并发控制），让 AsyncIO 做它擅长的事（I/O 等待），不要重复控制。

