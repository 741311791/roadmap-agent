# 路线图任务架构重构 - 进度报告

> **开始时间**: 2025-12-12  
> **状态**: 🚧 进行中

---

## ✅ 已完成

### Phase 1: 数据库迁移 ✅
- [x] 创建迁移文件 `backend/alembic/versions/refactor_roadmap_task_structure.py`
- [x] 实现 `upgrade()` 函数
- [x] 实现 `downgrade()` 函数

### Phase 2: 数据模型更新 ✅
- [x] `backend/app/models/database.py`
  - [x] RoadmapTask: 添加 `task_type`, `concept_id`, `content_type` 字段
  - [x] RoadmapMetadata: 删除 `task_id` 字段

### Phase 3: Repository 层更新 ✅
- [x] `backend/app/db/repositories/roadmap_repo.py`
  - [x] `create_task()`: 添加 3 个新参数
  - [x] 新增 `get_active_tasks_by_roadmap_id()` 方法
  - [x] `save_roadmap_metadata()`: 移除 task_id 参数

---

## 🚧 进行中

### Phase 4: API 端点修复 (需要继续)

#### 4.1 `backend/app/api/v1/roadmap.py`
需要修复 3 处：

1. **get_roadmap_active_task** (Line ~237)
```python
# ❌ 旧代码 (Line ~246):
task = await repo.get_task(metadata.task_id) if metadata.task_id else None

# ✅ 新代码:
task = await repo.get_active_task_by_roadmap_id(roadmap_id)
```

2. **check_roadmap_status_quick** (Line ~327)
```python
# ❌ 旧代码 (Line ~366-367):
task = await repo.get_task(metadata.task_id) if metadata.task_id else None
has_active_task = task and task.status in ['pending', 'processing', 'human_review_pending']

# ✅ 新代码:
active_tasks = await repo.get_active_tasks_by_roadmap_id(roadmap_id)
has_active_task = len(active_tasks) > 0

# 同时更新响应格式
```

3. **save_roadmap_metadata 调用** (Line ~1630)
```python
# ❌ 旧代码:
await repo.save_roadmap_metadata(
    roadmap_id=roadmap_id,
    user_id=roadmap_metadata.user_id,
    task_id=roadmap_metadata.task_id,  # ← 删除这行
    framework=updated_framework,
)

# ✅ 新代码:
await repo.save_roadmap_metadata(
    roadmap_id=roadmap_id,
    user_id=roadmap_metadata.user_id,
    framework=updated_framework,
)
```

#### 4.2 `backend/app/api/v1/endpoints/retrieval.py`
需要修复 1 处：

**get_active_task** (Line ~119)
```python
# ❌ 旧代码:
task = await repo.get_task(metadata.task_id) if metadata.task_id else None

# ✅ 新代码:
task = await repo.get_active_task_by_roadmap_id(roadmap_id)
```

#### 4.3 `backend/app/api/v1/endpoints/generation.py`
需要修复 4 处：

1. **save_roadmap 调用** (Line ~395): 删除 task_id 参数
2. **retry_tutorial** (Line ~419): 添加任务持久化
3. **retry_resources** (Line ~563): 添加任务持久化
4. **retry_quiz** (Line ~723): 添加任务持久化

#### 4.4 `backend/app/api/v1/endpoints/modification.py`
需要检查所有 `save_roadmap_metadata` 调用

#### 4.5 `backend/app/api/v1/endpoints/retry.py`
需要修复 1 处：
- Line ~1286: 添加 `task_type="retry_batch"` 参数

---

## 📋 待完成

### Phase 5: Orchestrator 层更新
- [ ] `backend/app/core/orchestrator/node_runners/curriculum_runner.py`
  - [ ] Line ~227: 移除 save_roadmap_metadata 调用中的 task_id 参数

### Phase 6: 脚本更新（可选）
- [ ] `backend/scripts/generate_tutorials_for_roadmap.py`
  - [ ] 多处修改

### Phase 7: 测试
- [ ] 运行迁移测试
- [ ] 单元测试
- [ ] 集成测试
- [ ] 端到端测试

---

## 🚀 下一步行动

**建议继续方式**：

由于 Phase 4 涉及大量文件修改，建议：

1. **手动审查** `doc/路线图任务架构重构方案_简化版.md` 中的详细代码示例
2. **逐文件修复** Phase 4.1 到 4.5 的所有端点
3. **使用搜索替换** 批量修复 `save_roadmap_metadata` 调用
4. **运行 linter** 检查语法错误
5. **运行迁移** `cd backend && alembic upgrade head`
6. **测试验证** 按照 Phase 7 的测试清单验证

---

## 📊 完成度

- ✅ Phase 1: 数据库迁移 (100%)
- ✅ Phase 2: 数据模型更新 (100%)
- ✅ Phase 3: Repository 层更新 (100%)
- 🚧 Phase 4: API 端点修复 (0%)
- ⏳ Phase 5: Orchestrator 层更新 (0%)
- ⏳ Phase 6: 脚本更新 (0%)
- ⏳ Phase 7: 测试 (0%)

**总进度**: 约 45% 完成

---

## ⚠️ 重要提示

1. **数据库迁移尚未运行**：迁移文件已创建但未执行
2. **API 端点需要全面修复**：Phase 4 是最关键的步骤
3. **建议测试环境先行**：在生产环境前充分测试

---

**继续实施请参考**: `doc/路线图任务架构重构方案_简化版.md`  
**实施清单**: `doc/IMPLEMENTATION_CHECKLIST.md`

