# framework_data更新缺失问题分析

**日期**: 2026-01-16  
**优先级**: 🔴 Critical  
**影响**: 用户无法看到最新的路线图数据

---

## 问题描述

在路线图生成工作流的最后一个节点（`content_generation`）结束后，`roadmap_metadata` 表中的 `framework_data` 字段**没有被正确更新**。

---

## 根因分析

### 架构现状

工作流分为两层：
1. **主图 (Main Graph)**: `content_generation_node`
2. **子图 (Subgraph)**: `final_aggregation` 节点

### 数据流断裂点

```
content_generation_node (主图)
    ↓
调用 subgraph.ainvoke()
    ↓
final_aggregation (子图内部)
    ↓
✅ 在子图内部的Session中更新了framework_data
    ↓
⚠️ 但主图的 ContentHandler **从未被触发**
    ↓
❌ framework_data更新被孤立在子图内部
```

### 代码证据

**1. 子图内部更新 (正常执行)**

```python
# backend/app/core/orchestrator/subgraphs/content_generation.py:224-240

async def final_aggregation(state, config):
    # ...
    async with get_celery_session() as session:
        # ✅ 批量更新 Framework
        await handler.update_framework_batch(
            session=session,
            roadmap_id=roadmap_id,
            concept_results=concept_results,
        )
        
        # ✅ 更新 Task 最终状态
        final_status = "completed" if all_saved else "partial_failure"
        await handler.update_task_final_status(
            session=session,
            task_id=task_id,
            status=final_status,
        )
```

**2. 主图节点返回值 (缺少framework)**

```python
# backend/app/core/orchestrator/nodes/content_generation.py:117-124

async def content_generation_node(state, config):
    # ...
    result = await subgraph.ainvoke(sub_state, config)
    
    # ⚠️ 返回的output不包含framework相关字段
    return {
        "roadmap_id": roadmap_id,
        "concept_results": concept_results,
        "current_step": "content_generation",
        "execution_history": [
            f"内容生成完成：成功 {successful_count}，失败 {failed_count}"
        ],
    }
```

**3. ContentHandler期望的输入 (未被满足)**

```python
# backend/app/core/orchestrator/handlers/content_handler.py:40-46

async def _handle_output(self, output, task_id, session):
    """
    处理内容生成输出
    
    期望 output 包含：
    - roadmap_id
    - tutorial_refs
    - resource_refs
    - quiz_refs
    - failed_concepts
    """
    # ❌ 但实际的output只有: roadmap_id, concept_results, current_step
```

---

## 问题1: 架构不一致

### 旧架构 (已废弃)
- `content_generation_node` 返回 `tutorial_refs`, `resource_refs`, `quiz_refs`
- `ContentHandler` 接收这些refs并更新framework_data

### 新架构 (当前)
- 子图内部的 `final_aggregation` **直接**更新framework_data
- 主图的 `ContentHandler` **不再被使用**
- 但注册表中仍然注册了 `ContentHandler`

### 断裂原因
迁移到新架构时，**忘记移除ContentHandler的注册**，导致：
1. `final_aggregation` 在子图内部更新了framework_data
2. 主图的 `ContentHandler` 期望接收老格式的output
3. 实际返回的output不匹配，ContentHandler无法正常工作

---

## 问题2: Handler调用逻辑

### Executor中的调用

```python
# backend/app/core/orchestrator/executor.py:219-225

async with get_celery_session() as session:
    await self.handler_registry.handle(
        node_name=node_name,
        output=node_output,
        task_id=task_id,
        session=session,
    )
```

### 实际情况
- `node_name` = `"content_generation"`
- `node_output` = `{"roadmap_id": ..., "concept_results": [...], ...}`
- `ContentHandler` 被调用，但因为output格式不匹配，**可能静默失败**

---

## 解决方案

### 方案1: 移除ContentHandler (推荐)

**原因**: 新架构中framework_data已经在子图内部更新完成

**步骤**:
1. 从 `HandlerRegistry` 中移除 `ContentHandler` 的注册
2. 确认 `final_aggregation` 中的更新逻辑完整
3. 验证数据库事务正确commit

**优点**:
- ✅ 符合当前架构设计
- ✅ 避免重复更新
- ✅ 减少复杂度

**缺点**:
- ⚠️ 需要确保子图内部的更新逻辑100%可靠

---

### 方案2: 修复ContentHandler (备选)

**原因**: 保持Handler统一管理数据库更新的原则

**步骤**:
1. 修改 `content_generation_node` 返回值，包含更新所需的所有数据
2. 修改 `ContentHandler._handle_output` 适配新格式
3. 从 `final_aggregation` 中移除framework_data更新逻辑

**优点**:
- ✅ 保持Handler统一管理数据库操作
- ✅ 更清晰的职责分离

**缺点**:
- ⚠️ 需要修改多个文件
- ⚠️ 子图需要返回大量数据给主图

---

### 方案3: 双重保障 (过度工程)

在子图内部更新 + ContentHandler再次确认更新

**不推荐**: 违反单一职责原则，增加维护成本

---

## 推荐实施步骤

### Step 1: 验证子图更新逻辑

```python
# backend/app/core/orchestrator/subgraphs/content_generation.py

async def final_aggregation(state, config):
    # 确认这里的更新逻辑完整
    async with get_celery_session() as session:
        await handler.update_framework_batch(
            session=session,
            roadmap_id=roadmap_id,
            concept_results=concept_results,
        )
        # ✅ get_celery_session() 使用 .begin()，自动 commit
```

### Step 2: 检查update_framework_batch实现

```python
# backend/app/core/orchestrator/handlers/content_handler.py

async def update_framework_batch(self, session, roadmap_id, concept_results):
    # 确认这里正确更新了framework_data
    pass
```

### Step 3: 移除或修复ContentHandler注册

```python
# backend/app/core/orchestrator/factory.py 或 executor.py

# 选项A: 移除注册
# registry.register("content_generation", ContentHandler(...))  # 注释掉

# 选项B: 修复Handler逻辑（如果选择方案2）
```

---

## 验证清单

- [ ] 检查 `final_aggregation` 中的 `update_framework_batch` 方法是否正确实现
- [ ] 验证 `get_celery_session()` 的事务是否正确commit
- [ ] 确认数据库中 `framework_data` 字段是否包含 `content_refs`
- [ ] 检查日志中是否有 `content_handler_saved` 日志
- [ ] 对比 `roadmap_framework` (State) 和 `framework_data` (DB) 的内容

---

## 临时排查SQL

```sql
-- 检查framework_data是否包含content_refs
SELECT 
    roadmap_id,
    jsonb_pretty(framework_data::jsonb) as framework
FROM roadmap_metadata
WHERE roadmap_id = 'YOUR_ROADMAP_ID'
LIMIT 1;

-- 检查是否有tutorial_id, resource_id, quiz_id字段
SELECT 
    roadmap_id,
    framework_data -> 'stages' -> 0 -> 'modules' -> 0 -> 'concepts' -> 0 -> 'tutorial_id' as has_tutorial_id
FROM roadmap_metadata
WHERE roadmap_id = 'YOUR_ROADMAP_ID';
```

---

## 附录: Handler注册位置

查找Handler注册的位置：

```bash
cd backend
grep -r "ContentHandler" app/core/orchestrator/
grep -r "registry.register.*content" app/
```

