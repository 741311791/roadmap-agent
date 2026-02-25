# resume_after_human_review 流程与性能分析

## 核心结论

**是的，无论是批准还是提交反馈重新修改，`resume_after_human_review` 走的都是同一套逻辑，且都会读取 PostgreSQL checkpoint。** 二者在流程上完全一致，只是批准会很快结束，而提交反馈会多跑多个 LLM 节点。

---

## 1. 完整调用链（两种场景相同）

```
用户点击「批准」或「提交反馈」
    ↓
API: POST /tasks/{task_id}/approve
    ↓ 立即返回 200（异步）
Celery Task: resume_after_review.apply_async(approved, feedback)
    ↓
Celery Worker 拉取任务
    ↓
WorkflowExecutionService.resume_workflow_after_review()
    ├── 更新 Task 状态为 processing
    ├── 发送 WS "Resuming workflow after review..."
    ├── OrchestratorFactory.initialize()     ← 潜在耗时点 ①
    ├── executor.resume_after_human_review()
    │   ├── graph.aget_state(config)         ← 读取 checkpoint ①
    │   ├── graph.astream_events(Command(resume=...))
    │   │   │   ← LangGraph 内部再次读取 checkpoint ②
    │   │   ├── [批准] human_review → 触发内容生成 Celery → 结束（快）
    │   │   └── [拒绝] human_review → edit_plan_analysis(LLM) → roadmap_edit(LLM) → ...
    │   └── graph.aget_state(config)         ← 读取 checkpoint ③
    └── 更新 Task 最终状态
```

---

## 2. Checkpoint 读取时机

| 步骤 | 位置 | 说明 |
|------|------|------|
| 1 | `resume_after_human_review` 入口 | `state_before_resume = await self.graph.aget_state(config)`，用于日志和初始 `final_state` |
| 2 | LangGraph `Command(resume=...)` 内部 | 恢复 graph 时从 checkpoint 加载中断时的完整 state |
| 3 | 流结束后 | `state_snapshot_after = await self.graph.aget_state(config)`，检查是否再次 interrupt |

每次 `aget_state` 都会查询 PostgreSQL 的 checkpoint 表，且会反序列化完整 state（含 `roadmap_framework`、`intent_analysis` 等），数据量可能较大。

---

## 3. 主要耗时来源

### 3.1 批准 vs 拒绝的差异

| 阶段 | 批准 | 提交反馈 |
|------|------|----------|
| 初始化 + Checkpoint 读取 | 相同 | 相同 |
| human_review 节点 | 触发 Celery，快速返回 | 返回后路由到 edit_plan_analysis |
| 后续节点 | 无 | edit_plan_analysis（LLM ~10–30s）→ roadmap_edit（LLM ~10–30s）→ ... |
| 总耗时 | 主要受前段影响 | 前段 + 多轮 LLM |

### 3.2 共同耗时的具体来源

1. **OrchestratorFactory.initialize()**
   - 创建 `AsyncConnectionPool`（连 PostgreSQL）
   - `await cls._connection_pool.open()`：建立连接
   - `await cls._checkpointer.setup()`：确保 checkpoint 表存在
   - 首次或长时间 idle 时可能 5–15 秒
   - 已有单例会快速返回，但 Celery fork 后子进程会重新初始化

2. **Checkpoint 读取**
   - 每次 `aget_state` 均为一次 PostgreSQL 查询
   - State 含 roadmap、intent 等，体积较大，序列化/反序列化也有成本
   - 若用云 RDS，网络延迟会叠加

3. **Celery 任务调度**
   - 任务入队、Worker 拉取、反序列化
   - 通常几百毫秒级，但在队列拥堵时会变长

### 3.3 拒绝场景的额外耗时

- **edit_plan_analysis**：EditPlanAnalyzerAgent，一次 LLM 调用
- **roadmap_edit**：EditorAgent，一次 LLM 调用
- 每次 LLM 调用通常在 10–30 秒左右，总计可再增加 20–60 秒

---

## 4. 相关代码位置

| 文件 | 相关逻辑 |
|------|----------|
| `executor.py` L449-450 | `state_before_resume = await self.graph.aget_state(config)` |
| `executor.py` L461 | `astream_events(Command(resume=resume_value))` |
| `executor.py` L583 | `state_snapshot_after = await self.graph.aget_state(config)` |
| `orchestrator_factory.py` L80-179 | `initialize()`：连接池、checkpointer 等 |
| `workflow_execution_service.py` L385-401 | `factory.initialize()` + `resume_after_human_review()` |

---

## 5. 优化方向建议

1. **预初始化 Worker**
   - 在 Celery Worker 启动时调用 `OrchestratorFactory.initialize()`，避免首次 resume 时冷启动。

2. **减少 checkpoint 读取**
   - 入口处的 `aget_state` 若仅用于日志，可考虑省略或改为可选。
   - 研究 LangGraph 是否支持在 resume 时直接传入 state，避免重复加载。

3. **Checkpoint 存储优化**
   - 评估是否可将大字段拆出或压缩，减小每次读写的数据量。

4. **前端体验**
   - 提交后立即展示「正在恢复工作流」等状态。
   - 对 edit_plan_analysis、roadmap_edit 等步骤做进度反馈。
