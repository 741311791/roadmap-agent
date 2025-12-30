# WorkflowBrain Commit 修复

## 问题描述

用户报告：
1. 任务详情页的 Intent Analysis 不显示
2. 路线图拓扑图不显示
3. 报错：`Intent analysis metadata not found`
4. 控制台没有 `roadmap_metadata` 的请求

## 根本原因

`workflow_brain.py` 中的 `save_intent_analysis` 和 `save_roadmap_framework` 方法存在严重 bug：

### 问题代码
```python
# save_intent_analysis 方法（修复前）
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_intent_analysis_metadata(task_id, intent_analysis)
    # 此方法内部已经 commit，metadata 已经持久化  ❌ 错误注释！

# save_roadmap_framework 方法（修复前）
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_roadmap_metadata(roadmap_id, user_id, framework)
    # 此方法内部已经 commit，framework 已经持久化  ❌ 错误注释！
```

### 问题原因

根据 `20251231_数据库优化实施总结.md`，Repository 方法内部只调用 `flush()` 而不是 `commit()`，目的是让调用者控制事务边界。

然而，`workflow_brain.py` 中的注释错误地认为"此方法内部已经 commit"，所以没有手动调用 `commit()`。

**结果**：当 `async with AsyncSessionLocal() as session:` 块结束时，由于没有 commit，事务被自动回滚，数据没有被持久化！

## 修复方案

### 1. 修复 `save_intent_analysis` 方法

```python
# 修复后
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_intent_analysis_metadata(task_id, intent_analysis)
    await session.commit()  # ✅ 必须手动 commit 才能持久化
```

### 2. 修复 `save_roadmap_framework` 方法

```python
# 修复后
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_roadmap_metadata(roadmap_id, user_id, framework)
    await session.commit()  # ✅ 必须手动 commit 才能持久化
```

### 3. 清理重复的 commit 调用

发现并清理了以下位置的重复 `await session.commit()` 调用：
- `_before_node` 方法（第 231-232 行）
- `_on_error` 方法（第 359-360 行）
- `notify_human_review_required` 方法（第 1037-1038 行）

## 修改的文件

- `backend/app/core/orchestrator/workflow_brain.py`

## 影响范围

此修复影响以下功能：
1. **Intent Analysis 保存**：用户需求分析结果现在能正确保存到数据库
2. **Roadmap Framework 保存**：路线图框架现在能正确保存到数据库
3. **前端数据显示**：
   - Intent Analysis Card 可以正常显示
   - 路线图拓扑图可以正常显示
   - 不再出现 "Intent analysis metadata not found" 错误

## 测试建议

1. 创建新的学习任务
2. 等待 `intent_analysis` 阶段完成
3. 验证前端能正常显示 Intent Analysis Card
4. 等待 `curriculum_design` 阶段完成
5. 验证前端能正常显示路线图拓扑图
6. 刷新页面，验证数据仍然存在

## 教训

1. **代码注释要准确**：错误的注释导致了这个 bug 长期存在
2. **理解事务边界**：使用 `async with AsyncSessionLocal()` 时，必须显式 commit
3. **Repository 设计模式**：Repository 方法使用 `flush()` 是正确的设计，但调用者必须负责 commit

