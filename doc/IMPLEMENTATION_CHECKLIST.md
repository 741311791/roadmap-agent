# 路线图任务架构重构 - 实施检查列表

> **基于**: `doc/路线图任务架构重构方案_简化版.md`  
> **日期**: 2025-12-12

---

## ✅ Phase 1: 数据库迁移

### 1.1 创建迁移文件

- [ ] 创建 `backend/alembic/versions/XXXX_refactor_roadmap_task_structure.py`
- [ ] 实现 `upgrade()` 函数
  - [ ] 添加 `task_type` 字段
  - [ ] 添加 `concept_id` 字段
  - [ ] 添加 `content_type` 字段
  - [ ] 更新现有记录设置 `task_type='creation'`
  - [ ] 创建索引 `idx_roadmap_tasks_roadmap_id_status`
  - [ ] 创建索引 `idx_roadmap_tasks_roadmap_id_created_at`
  - [ ] 删除 `roadmap_metadata.task_id` 字段
- [ ] 实现 `downgrade()` 函数
- [ ] 测试迁移：`alembic upgrade head`
- [ ] 测试回滚：`alembic downgrade -1`

---

## ✅ Phase 2: 数据模型更新

### 2.1 更新 `backend/app/models/database.py`

**RoadmapTask 模型**：
- [ ] Line ~48: 添加 `task_type: Optional[str]` 字段
- [ ] Line ~49: 添加 `concept_id: Optional[str]` 字段
- [ ] Line ~50: 添加 `content_type: Optional[str]` 字段

**RoadmapMetadata 模型**：
- [ ] Line ~103: 删除 `task_id: str = Field(index=True)` 字段

---

## ✅ Phase 3: Repository 层更新

### 3.1 更新 `backend/app/db/repositories/roadmap_repo.py`

**create_task 方法**：
- [ ] Line ~46: 添加 `task_type` 参数（默认值 `"creation"`）
- [ ] Line ~47: 添加 `concept_id` 参数（默认值 `None`）
- [ ] Line ~48: 添加 `content_type` 参数（默认值 `None`）
- [ ] Line ~63: 在 `RoadmapTask()` 初始化时设置新字段
- [ ] Line ~74: 在日志中记录 `task_type`

**新增 get_active_tasks_by_roadmap_id 方法**：
- [ ] Line ~112 后: 添加新方法（返回 `list[RoadmapTask]`）
- [ ] 查询条件：`roadmap_id` + `status IN ('pending', 'processing', 'human_review_pending')`
- [ ] 排序：`created_at DESC`

**save_roadmap_metadata 方法**：
- [ ] Line ~164: 删除 `task_id: str` 参数
- [ ] Line ~178: 删除 `task_id=task_id` 字段赋值
- [ ] Line ~185: 删除日志中的 `task_id`

---

## ✅ Phase 4: API 端点修复

### 4.1 `backend/app/api/v1/roadmap.py`

**get_roadmap_active_task 函数** (Line ~237):
- [ ] Line ~246: 删除 `task = await repo.get_task(metadata.task_id)` 
- [ ] Line ~246: 改为 `task = await repo.get_active_task_by_roadmap_id(roadmap_id)`
- [ ] Line ~251-256: 更新响应，添加 `task_type`, `concept_id`, `content_type` 字段

**check_roadmap_status_quick 函数** (Line ~327):
- [ ] Line ~366: 删除 `task = await repo.get_task(metadata.task_id)`
- [ ] Line ~367: 删除 `has_active_task = task and task.status in [...]`
- [ ] Line ~366: 改为 `active_tasks = await repo.get_active_tasks_by_roadmap_id(roadmap_id)`
- [ ] Line ~367: 改为 `has_active_task = len(active_tasks) > 0`
- [ ] Line ~370-377: 更新响应，返回 `active_tasks` 列表

**save_roadmap_metadata 调用** (Line ~1630):
- [ ] Line ~1630: 删除 `task_id=roadmap_metadata.task_id` 参数

### 4.2 `backend/app/api/v1/endpoints/retrieval.py`

**get_active_task 函数** (Line ~80):
- [ ] Line ~119: 删除 `task = await repo.get_task(metadata.task_id)`
- [ ] Line ~119: 改为 `task = await repo.get_active_task_by_roadmap_id(roadmap_id)`

### 4.3 `backend/app/api/v1/endpoints/generation.py`

**save_roadmap 调用** (Line ~392):
- [ ] Line ~395: 删除 `task_id=roadmap_metadata.task_id` 参数

**retry_tutorial 函数** (Line ~419):
- [ ] Line ~448 后: 添加 `async with repo_factory.create_session()` 块
- [ ] 调用 `task_repo.create_task()` 时传入新参数：
  - [ ] `task_type="retry_tutorial"`
  - [ ] `concept_id=concept_id`
  - [ ] `content_type="tutorial"`
- [ ] 调用 `task_repo.update_task_status()` 设置 `status="processing"`
- [ ] 在 `try` 块结束时调用 `update_task_status(status="completed")`
- [ ] 在 `except` 块中调用 `update_task_status(status="failed")`

**retry_resources 函数** (Line ~563):
- [ ] 同上，`task_type="retry_resources"`, `content_type="resources"`

**retry_quiz 函数** (Line ~723):
- [ ] 同上，`task_type="retry_quiz"`, `content_type="quiz"`

### 4.4 `backend/app/api/v1/endpoints/modification.py`

**检查所有 save_roadmap_metadata 调用**:
- [ ] 搜索 `save_roadmap_metadata` 并移除所有 `task_id` 参数

### 4.5 `backend/app/api/v1/endpoints/retry.py`

**retry_failed_content 函数**:
- [ ] Line ~1286: 检查 `repo.create_task()` 调用
- [ ] 添加 `task_type="retry_batch"` 参数

---

## ✅ Phase 5: Orchestrator 层更新

### 5.1 `backend/app/core/orchestrator/node_runners/curriculum_runner.py`

**_save_roadmap_framework 方法** (Line ~213):
- [ ] Line ~227: 检查 `repo.save_roadmap_metadata()` 调用
- [ ] Line ~230: 删除 `task_id=task_id` 参数

---

## ✅ Phase 6: 脚本更新（可选）

### 6.1 `backend/scripts/generate_tutorials_for_roadmap.py`

- [ ] Line ~41: 删除 `print(f"Task ID: {metadata.task_id}")`
- [ ] Line ~60: 改为通过 `roadmap_id` 查询活跃任务
- [ ] Line ~109: 删除 `save_roadmap_metadata` 调用中的 `task_id` 参数
- [ ] Line ~122: 改为通过 `roadmap_id` 查询任务并更新状态

---

## ✅ Phase 7: 测试

### 7.1 单元测试

- [ ] Repository 层测试
  - [ ] `test_create_task_with_new_fields()`
  - [ ] `test_get_active_tasks_by_roadmap_id()`
  - [ ] `test_save_roadmap_metadata_without_task_id()`

### 7.2 集成测试

- [ ] 创建路线图流程
  - [ ] 任务记录包含 `task_type='creation'`
  - [ ] roadmap_metadata 无 task_id 字段
  - [ ] 可以通过 roadmap_id 查询活跃任务

- [ ] 重试教程流程
  - [ ] 任务记录包含 `task_type='retry_tutorial'`
  - [ ] 任务记录包含正确的 `concept_id` 和 `content_type`
  - [ ] WebSocket 正常推送事件
  - [ ] 任务完成后状态正确更新

- [ ] 僵尸状态检测
  - [ ] 有活跃重试任务时不误报
  - [ ] 无活跃任务时正确检测僵尸概念

### 7.3 端到端测试

- [ ] 前端创建路线图 → 后端任务记录正确
- [ ] 前端重试失败概念 → 新任务创建并关联
- [ ] 切换 tab 后返回 → 状态检查准确
- [ ] 任务异常终止 → 僵尸状态正确识别

---

## 🔍 验证检查点

### 数据库检查

```sql
-- 检查 roadmap_tasks 表结构
\d roadmap_tasks

-- 验证新字段存在
SELECT task_id, task_type, concept_id, content_type 
FROM roadmap_tasks 
LIMIT 5;

-- 检查现有记录的 task_type
SELECT task_type, COUNT(*) 
FROM roadmap_tasks 
GROUP BY task_type;

-- 检查 roadmap_metadata 表
\d roadmap_metadata

-- 验证 task_id 字段已删除
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'roadmap_metadata';
```

### API 检查

```bash
# 测试获取活跃任务
curl http://localhost:8000/api/v1/roadmaps/{roadmap_id}/active-task

# 测试僵尸状态检测
curl http://localhost:8000/api/v1/roadmaps/{roadmap_id}/status-check

# 测试重试端点
curl -X POST http://localhost:8000/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/retry \
  -H "Content-Type: application/json" \
  -d '{"preferences": {...}}'
```

---

## 📊 完成度追踪

- [ ] Phase 1: 数据库迁移 (0/5)
- [ ] Phase 2: 数据模型更新 (0/4)
- [ ] Phase 3: Repository 层更新 (0/7)
- [ ] Phase 4: API 端点修复 (0/15)
- [ ] Phase 5: Orchestrator 层更新 (0/2)
- [ ] Phase 6: 脚本更新 (0/4)
- [ ] Phase 7: 测试 (0/12)

**总进度**: 0/49 任务完成

---

## 🚀 实施顺序建议

1. **Phase 1** → **Phase 2** → **Phase 3** (数据层)
2. **Phase 4** (API 层)
3. **Phase 5** (Orchestrator 层)
4. **Phase 6** (脚本，可选)
5. **Phase 7** (测试验证)

---

## ⚠️ 注意事项

1. **备份数据库**：在运行迁移前务必备份
2. **测试环境先行**：在测试环境完全验证后再应用到生产
3. **回滚准备**：确保 downgrade 函数可用
4. **代码审查**：所有修改建议进行 code review
5. **分支管理**：建议在独立分支进行，合并前充分测试

---

**状态**: 📋 **就绪，可开始实施**

