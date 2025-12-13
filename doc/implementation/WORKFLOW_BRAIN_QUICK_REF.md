# WorkflowBrain 快速参考卡片

> **用途**: 开发时的快速查阅手册  
> **保持打开**: 建议在编码时在第二屏幕显示

---

## 🎯 核心概念 (1分钟理解)

```
┌─────────────────────────────────────────────────────┐
│  WorkflowBrain = 统一协调者                          │
├─────────────────────────────────────────────────────┤
│  职责:                                               │
│  1. 状态管理 (live_step)                             │
│  2. 数据库操作 (统一事务)                            │
│  3. 日志记录 (execution_logger)                      │
│  4. 通知发布 (notification_service)                  │
│  5. 错误处理 (统一策略)                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Runner = 纯执行者                                   │
├─────────────────────────────────────────────────────┤
│  职责:                                               │
│  1. 调用 Agent                                       │
│  2. 返回纯结果                                       │
│  3. 不再直接操作数据库 ❌                            │
│  4. 不再记录日志 ❌                                  │
│  5. 不再发送通知 ❌                                  │
└─────────────────────────────────────────────────────┘
```

---

## 📋 重构前后对比 (代码模板)

### ❌ 重构前 (不要这样写)

```python
class OldRunner:
    async def run(self, state: RoadmapState) -> dict:
        task_id = state["task_id"]
        
        # ❌ 直接操作数据库
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="some_step",
            )
            await session.commit()
        
        # ❌ 直接记录日志
        await execution_logger.log_workflow_start(...)
        
        # ❌ 直接发送通知
        await notification_service.publish_progress(...)
        
        # 执行 Agent
        result = await agent.execute(...)
        
        # ❌ 又是数据库操作
        async with AsyncSessionLocal() as session:
            # ...
            await session.commit()
        
        # ❌ 又是日志
        await execution_logger.log_workflow_complete(...)
        
        # ❌ 又是通知
        await notification_service.publish_progress(...)
        
        return result
```

### ✅ 重构后 (这样写)

```python
class NewRunner:
    def __init__(self, brain: WorkflowBrain, agent_factory: AgentFactory):
        self.brain = brain
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        # ✅ 使用 brain 统一管理
        async with self.brain.node_execution("some_step", state):
            # 1. 只调用 Agent
            agent = self.agent_factory.create_xxx_agent()
            result = await agent.execute(...)
            
            # 2. 如果需要保存数据，调用 brain 的方法
            await self.brain.save_xxx(...)
            
            # 3. 返回纯状态更新
            return {
                "xxx": result,
                "current_step": "some_step",
                "execution_history": ["完成 xxx"],
            }
```

---

## 🔧 WorkflowBrain API 速查

### 核心方法

```python
# 1. 节点执行上下文管理器
async with brain.node_execution(node_name: str, state: RoadmapState):
    # 自动处理:
    # - before_node: 更新状态、记录日志、发送通知
    # - after_node: 记录完成、发送通知
    # - on_error: 错误处理、状态更新、错误通知
    ...
```

### 数据保存方法

```python
# 2. 保存需求分析结果
await brain.save_intent_analysis(
    task_id: str,
    intent_analysis: IntentAnalysisOutput,
    unique_roadmap_id: str,
)

# 3. 保存路线图框架
await brain.save_roadmap_framework(
    task_id: str,
    roadmap_id: str,
    user_id: str,
    framework: RoadmapFramework,
)

# 4. 批量保存内容生成结果
await brain.save_content_results(
    task_id: str,
    roadmap_id: str,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
)

# 5. 确保 roadmap_id 唯一性
unique_id = await brain.ensure_unique_roadmap_id(roadmap_id: str)
```

---

## 📝 Runner 重构步骤清单

### Step 1: 修改构造函数

```python
# 添加 brain 参数
def __init__(
    self,
    brain: WorkflowBrain,  # ← 新增
    agent_factory: AgentFactory,
):
    self.brain = brain  # ← 新增
    self.agent_factory = agent_factory
```

### Step 2: 删除不需要的方法

```python
# ❌ 删除这些方法
async def _update_task_status(self, ...): ...
async def _save_xxx(self, ...): ...
# ... 所有数据库操作方法
```

### Step 3: 重写 run() 方法

```python
async def run(self, state: RoadmapState) -> dict:
    # 用 brain.node_execution 包装
    async with self.brain.node_execution("node_name", state):
        # 只保留 Agent 调用逻辑
        agent = self.agent_factory.create_xxx_agent()
        result = await agent.execute(...)
        
        # 如果需要保存数据
        await self.brain.save_xxx(...)
        
        # 返回状态更新
        return {"xxx": result, ...}
```

### Step 4: 更新 orchestrator_factory

```python
# 在 orchestrator_factory.py 中
brain = WorkflowBrain(
    state_manager=state_manager,
    notification_service=notification_service,
    execution_logger=execution_logger,
)

# 传递给所有 Runner
xxx_runner = XxxRunner(
    brain=brain,  # ← 传递 brain
    agent_factory=agent_factory,
)
```

---

## 🧪 测试模板

### 单元测试模板

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_xxx_runner_success():
    """测试 XXX Runner 成功场景"""
    # 准备
    mock_brain = MagicMock()
    mock_brain.node_execution = AsyncMock()
    mock_brain.save_xxx = AsyncMock()
    
    mock_agent_factory = MagicMock()
    mock_agent = AsyncMock()
    mock_agent_factory.create_xxx_agent.return_value = mock_agent
    
    runner = XxxRunner(
        brain=mock_brain,
        agent_factory=mock_agent_factory,
    )
    
    # 执行
    result = await runner.run(mock_state)
    
    # 验证
    assert result["xxx"] == expected_result
    mock_brain.node_execution.assert_called_once()
    mock_brain.save_xxx.assert_called_once()
```

### 集成测试模板

```python
@pytest.mark.asyncio
async def test_xxx_runner_integration():
    """测试 XXX Runner 集成（实际数据库）"""
    # 使用真实的 brain 和数据库
    brain = WorkflowBrain(...)
    runner = XxxRunner(brain=brain, ...)
    
    # 执行
    result = await runner.run(test_state)
    
    # 验证数据库状态
    async with AsyncSessionLocal() as session:
        task = await repo.get_task(task_id)
        assert task.status == "processing"
        assert task.current_step == "xxx"
```

---

## ⚠️ 常见错误与解决

### 错误 1: 忘记传递 brain

```python
# ❌ 错误
runner = XxxRunner(agent_factory=agent_factory)

# ✅ 正确
runner = XxxRunner(
    brain=brain,
    agent_factory=agent_factory,
)
```

### 错误 2: 仍在 Runner 中操作数据库

```python
# ❌ 错误
async def run(self, state):
    async with AsyncSessionLocal() as session:  # ← 不要这样做！
        ...

# ✅ 正确
async def run(self, state):
    async with self.brain.node_execution("xxx", state):
        await self.brain.save_xxx(...)  # ← 使用 brain 的方法
```

### 错误 3: 没有返回完整的状态更新

```python
# ❌ 错误
return {"result": result}  # ← 不完整

# ✅ 正确
return {
    "xxx": result,
    "current_step": "xxx",
    "execution_history": ["完成 xxx"],
}
```

### 错误 4: 在测试中没有 mock brain

```python
# ❌ 错误
runner = XxxRunner(brain=None, ...)  # ← 会报错

# ✅ 正确
mock_brain = MagicMock()
runner = XxxRunner(brain=mock_brain, ...)
```

---

## 📦 文件结构速查

```
backend/app/core/orchestrator/
├── workflow_brain.py          # ← 新增: WorkflowBrain 核心
├── base.py                    # 保持不变
├── builder.py                 # 保持不变
├── executor.py                # 保持不变
├── state_manager.py           # 保持不变
└── node_runners/
    ├── intent_runner.py       # ← 重构: 使用 brain
    ├── curriculum_runner.py   # ← 重构: 使用 brain
    ├── validation_runner.py   # ← 重构: 使用 brain
    ├── editor_runner.py       # ← 重构: 使用 brain
    ├── review_runner.py       # ← 重构: 使用 brain
    └── content_runner.py      # ← 重构: 使用 brain

backend/app/core/
└── orchestrator_factory.py    # ← 修改: 创建 brain 并传递

backend/tests/
├── unit/
│   └── test_workflow_brain.py # ← 新增: brain 单元测试
└── integration/
    └── test_xxx_runner_migration.py  # ← 新增: 迁移测试
```

---

## 🎯 代码行数目标

| Runner | 重构前 | 目标 | 减少 |
|--------|--------|------|------|
| IntentAnalysisRunner | 248 行 | ~80 行 | -68% |
| CurriculumDesignRunner | 240 行 | ~70 行 | -71% |
| ValidationRunner | 177 行 | ~50 行 | -72% |
| EditorRunner | 210 行 | ~60 行 | -71% |
| ReviewRunner | 162 行 | ~50 行 | -69% |
| ContentRunner | 565 行 | ~200 行 | -65% |

**如果重构后代码行数没有明显减少，说明可能没有正确使用 brain！**

---

## 💡 最佳实践

### ✅ DO (要做)

1. **使用 brain.node_execution() 包装所有执行逻辑**
2. **调用 brain 的保存方法而非直接操作数据库**
3. **保持 Runner 的 run() 方法简洁 (< 30 行)**
4. **为每个 Runner 添加单元测试和集成测试**
5. **遵循中文注释规范**

### ❌ DON'T (不要做)

1. **不要在 Runner 中创建数据库会话 (AsyncSessionLocal)**
2. **不要在 Runner 中直接调用 execution_logger**
3. **不要在 Runner 中直接调用 notification_service**
4. **不要保留旧的 _update_xxx 方法**
5. **不要忘记删除不再需要的 import 语句**

---

## 🔍 调试技巧

### 查看 brain 执行流程

```python
# 在 workflow_brain.py 中添加调试日志
logger.info(
    "brain_before_node",
    node_name=node_name,
    task_id=task_id,
    roadmap_id=roadmap_id,
)
```

### 验证数据库事务

```python
# 检查事务是否正确提交
async with AsyncSessionLocal() as session:
    task = await session.get(RoadmapTask, task_id)
    print(f"Task status: {task.status}")
    print(f"Current step: {task.current_step}")
```

### 对比新旧版本输出

```python
# 运行两个版本并对比结果
old_result = await old_runner.run(state)
new_result = await new_runner.run(state)

assert old_result == new_result, "输出不一致！"
```

---

## 📞 遇到问题？

### 检查清单

- [ ] 是否正确传递了 brain 参数？
- [ ] 是否删除了所有 `async with AsyncSessionLocal()` 代码？
- [ ] 是否使用了 `brain.node_execution()` 包装？
- [ ] 是否调用了正确的 brain 保存方法？
- [ ] 是否返回了完整的状态更新？
- [ ] 测试是否通过？

### 常用命令

```bash
# 运行单元测试
pytest backend/tests/unit/test_workflow_brain.py -v

# 运行集成测试
pytest backend/tests/integration/ -v

# 检查代码覆盖率
pytest --cov=backend/app/core/orchestrator --cov-report=html

# 运行 linter
ruff check backend/app/core/orchestrator/

# 格式化代码
black backend/app/core/orchestrator/
```

---

## 🎓 参考文档

- [完整架构分析](../architecture/WORKFLOW_BRAIN_ARCHITECTURE_ANALYSIS.md)
- [详细任务清单](WORKFLOW_BRAIN_TASK_BREAKDOWN.md)
- [任务看板](WORKFLOW_BRAIN_KANBAN.md)
- [Orchestrator 架构](../architecture/orchestrator_architecture.md)

---

**💪 准备好了吗？开始第一个任务吧！**

```bash
# 创建分支
git checkout -b feature/workflow-brain-phase1

# 标记第一个任务为进行中
# 在 Cursor 中更新 TODO: phase1-1-create-brain-class → in_progress

# 开始编码！
```

---

*最后更新: 2024-12-13*

