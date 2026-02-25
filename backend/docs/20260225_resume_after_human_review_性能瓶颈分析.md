# resume_after_human_review 性能瓶颈分析

基于实际日志（第一次提交反馈拒绝、第二次批准）的完整时间线分析。

---

## 1. 两次 Resume 总览

| 项目 | 第一次（拒绝+反馈）| 第二次（批准）|
|------|------------------|---------------|
| **总耗时** | **329,247ms（约 5分29秒）** | **798ms** |
| DB 连接（NullPool）| 156ms | 148ms |
| aget_state #1 | 45ms | 46ms |
| astream 启动到首节点 | 137ms | 18ms |
| LLM 调用 | edit_plan ~7.34s + roadmap_edit ~4.5min | 无 |
| **Checkpoint 写入（隐蔽）** | **edit_plan 后 18.14s** | N/A |
| Handler DB 写入 | ~3.3s | 181ms |
| aget_state #2 | 51ms | 15ms |

---

## 2. 瓶颈一：LangGraph Checkpoint 写入（最严重）

**现象**：

```
edit_plan_analysis_completed  ← LLM 返回，节点函数执行完毕
        ↕ 18,141ms 空洞（无任何日志）
workflow_resume_node_completed  ← on_chain_end 才到达
```

**原因**：LangGraph 在节点函数返回后、发出 `on_chain_end` 前，会将完整 state 序列化并写入 PostgreSQL checkpoint 表。State 含 `roadmap_framework`（完整路线图）+ `intent_analysis` + `edit_plan` 等，数据量可达数十至数百 KB。

**影响**：本地 PG 约 18s；云 RDS 可能 30s+。

---

## 3. 瓶颈二：Handler DB 写入阻塞 astream 事件循环

**现象**：

```
on_chain_end (edit_plan_analysis)
    ↓
EditPlanHandler 开始 DB 写入（review_feedback、edit_plan）
    ↓ 3.3s 阻塞
coordinator_node_complete
    ↓
on_chain_start (roadmap_edit)  ← 被 handler 阻塞了 3.35s 才消费到
```

**原因**：`on_chain_end` 中 `await handler_registry.handle()` 在 astream 的 `async for event` 循环内串行执行，Handler 的 DB 写入阻塞整个事件循环，后续节点事件堆积在 generator 缓冲区。

---

## 4. 瓶颈三：NullPool 每次建立新 TCP 连接

**现象**：`resume_db_status_update_done` 约 **148~156ms**。

**原因**：`get_celery_session()` 使用 NullPool，每次调用都建立新 TCP 连接，无连接复用。

**影响**：本地 PG 约 150ms；云 RDS 可达 1~3s（此前曾出现 3.245s 黑洞）。

---

## 5. 瓶颈四：WebSocket 通知超时

**现象**：

```
notification_publish_timeout  (timeout_seconds=1)
```

在 `edit_plan_analysis` 节点内部发送 WebSocket 通知时触发 1s 超时，说明 Redis Pub/Sub 在某些时刻响应慢。

---

## 6. 优化方向（按优先级）

### ① 最紧迫：减小 Checkpoint state 体积

- 避免将完整 `roadmap_framework` 放入 LangGraph state
- 可考虑只存 `roadmap_id`，需要时从 DB 读取
- 或改用 Redis 作为 checkpoint 后端，减少大对象写入 PG

### ② 中等：Handler DB 写入异步化

- 将 `on_chain_end` 中的 handler 调用改为 `asyncio.create_task()` fire-and-forget
- 不阻塞 astream 事件循环，后续节点事件可及时消费

### ③ 低优先级：NullPool 改为连接池

- Celery Worker 启动时预建连接
- 或使用 QueuePool 等，复用连接

---

## 7. 相关代码位置

| 文件 | 相关逻辑 |
|------|----------|
| `executor.py` | `on_chain_end` 中 `await self.handler_registry.handle(...)` |
| `workflow_execution_service.py` | `get_celery_session()` 首次 DB 写入 |
| `db/celery_session.py` | NullPool 配置 |
| LangGraph 内部 | 节点返回后的 checkpoint 写入时机 |
