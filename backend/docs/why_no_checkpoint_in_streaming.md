# 为什么流式端点不使用 Checkpoint？

## 架构对比

### 1. `/generate` 端点（使用 Checkpoint）

```
用户请求
  ↓
后台任务（BackgroundTask）
  ↓
RoadmapOrchestrator
  ↓
LangGraph 工作流
  ↓ ↓ ↓ ↓ ↓
[状态机] → [Checkpoint] → [持久化]
  ├─ Intent Analysis
  ├─ Curriculum Design
  ├─ Structure Validation  ← 循环重试
  ├─ Roadmap Edit          ← 循环修正
  ├─ Human Review          ← 暂停等待
  └─ Tutorial Generation
```

**使用 Checkpoint 的原因：**

1. **Human-in-the-Loop（人工审核）**
   - 工作流在 `human_review` 节点会使用 `interrupt()` 暂停
   - 状态需要持久化到数据库（AsyncPostgresSaver）
   - 等待用户审核批准后，使用 `Command(resume=...)` 恢复
   - 这个过程可能跨越几小时甚至几天

2. **循环重试机制**
   - Structure Validation ↔ Roadmap Edit 可能循环多次
   - 每次迭代的状态都需要保存
   - 方便调试和追溯

3. **故障恢复**
   - 如果服务器重启，可以从 checkpoint 恢复
   - 长时间运行的任务需要可靠性保证

4. **状态追踪**
   - 可以随时查询工作流的当前状态
   - 支持复杂的分支逻辑

---

### 2. `/generate-stream` 端点（不使用 Checkpoint）

```
用户请求
  ↓
流式响应（SSE Stream）
  ↓
直接调用 Agent（无状态机）
  ├─ Intent Analyzer.analyze_stream()     → 流式输出
  ├─ Curriculum Architect.design_stream() → 流式输出
  └─ Tutorial Generator.generate_stream() → 流式输出（可选）
       ↓
一次性完成，完成后保存到数据库
```

**不使用 Checkpoint 的原因：**

1. **无需暂停和恢复**
   - 没有 Human-in-the-Loop
   - 一次性执行完成
   - 不需要跨请求的状态持久化

2. **追求简单和快速**
   - 直接调用 Agent，无状态机开销
   - 不需要写入/读取 checkpoint 表
   - 减少数据库 I/O

3. **实时流式反馈**
   - 主要目的是实时展示生成过程
   - 状态在内存中传递
   - 不需要持久化中间状态

4. **不需要循环重试**
   - 跳过 Structure Validation
   - 跳过 Roadmap Edit
   - 一次生成，直接返回

5. **完成后才保存**
   - 只在流式传输完成后保存最终结果
   - 保存到常规数据库表（roadmap_tasks, roadmap_metadata, tutorial_metadata）
   - 不需要 checkpoint 机制

---

## 代码对比

### `/generate` 端点 - 使用 LangGraph + Checkpoint

```python
@router.post("/generate")
async def generate_roadmap(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    orchestrator: RoadmapOrchestrator = Depends(get_orchestrator),  # ← 使用 orchestrator
):
    trace_id = str(uuid.uuid4())
    
    # 创建任务记录
    repo = RoadmapRepository(db)
    await repo.create_task(task_id=trace_id, ...)
    
    # 在后台执行 LangGraph 工作流
    background_tasks.add_task(
        _execute_roadmap_generation_task,
        request,
        trace_id,
        orchestrator,  # ← 使用 orchestrator（内部使用 checkpoint）
    )
    
    return {"task_id": trace_id, "status": "processing"}
```

### `/generate-stream` 端点 - 直接调用 Agent

```python
@router.post("/generate-stream")
async def generate_roadmap_stream(
    request: UserRequest,
    include_tutorials: bool = False,
):
    # 直接返回流式生成器，不使用 orchestrator
    return StreamingResponse(
        _generate_sse_stream(request, include_tutorials=include_tutorials),
        media_type="text/event-stream",
    )

async def _generate_sse_stream(request, include_tutorials):
    # 1. 直接调用 Intent Analyzer
    intent_analyzer = IntentAnalyzerAgent()
    async for event in intent_analyzer.analyze_stream(request):
        yield f"data: {json.dumps(event)}\n\n"  # ← 流式输出
    
    # 2. 直接调用 Curriculum Architect
    architect = CurriculumArchitectAgent()
    async for event in architect.design_stream(...):
        yield f"data: {json.dumps(event)}\n\n"  # ← 流式输出
    
    # 3. 可选：调用 Tutorial Generator
    if include_tutorials:
        generator = TutorialGeneratorAgent()
        async for event in generator.generate_stream(...):
            yield f"data: {json.dumps(event)}\n\n"  # ← 流式输出
    
    # 4. 完成后保存到数据库（不使用 checkpoint）
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.create_task(...)           # ← 直接保存
        await repo.save_roadmap_metadata(...) # ← 直接保存
        await repo.save_tutorials_batch(...)  # ← 直接保存
```

---

## Checkpoint 表结构

LangGraph 使用的 checkpoint 表：

```sql
-- checkpoints - 存储工作流的快照
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB,
    metadata JSONB,
    ...
);

-- checkpoint_writes - 存储写入操作
CREATE TABLE checkpoint_writes (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id TEXT,
    task_id TEXT,
    idx INTEGER,
    channel TEXT,
    type TEXT,
    value JSONB,
    ...
);

-- checkpoint_blobs - 存储大型二进制数据
CREATE TABLE checkpoint_blobs (
    thread_id TEXT,
    checkpoint_ns TEXT,
    channel TEXT,
    version TEXT,
    type TEXT,
    blob BYTEA,
    ...
);
```

这些表只在使用 LangGraph 工作流时需要，用于：
- 保存工作流状态
- 支持暂停和恢复
- 处理 interrupt() 和 Command(resume=...)

---

## 何时使用哪种端点？

### 使用 `/generate` + Checkpoint

✅ **适合场景：**
- 生产环境
- 需要人工审核
- 需要结构验证和多次迭代
- 需要故障恢复
- 复杂的工作流控制

❌ **不适合：**
- 快速演示
- 不需要审核的场景
- 简单的一次性生成

### 使用 `/generate-stream` - 无 Checkpoint

✅ **适合场景：**
- 演示和测试
- 实时展示生成过程
- 快速预览
- 不需要人工审核
- UI 需要流式反馈

❌ **不适合：**
- 需要人工审核
- 需要复杂的状态管理
- 需要故障恢复

---

## 总结

**流式端点不使用 checkpoint 是设计选择，不是 bug：**

1. **架构简化** - 直接调用 Agent，无状态机
2. **性能优化** - 减少数据库 I/O，更快响应
3. **用途明确** - 用于演示和快速生成，不需要复杂的状态管理
4. **仍然保存数据** - 完成后保存到常规表，不需要 checkpoint 机制

两种端点各有优势，根据使用场景选择：
- **生产环境** → `/generate` + Checkpoint
- **演示/测试** → `/generate-stream` - 无 Checkpoint

现在的实现是**完全符合设计意图**的！✅














