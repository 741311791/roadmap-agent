# 数据架构说明：为什么前端能看到教程但 framework_data 未更新？

## 问题背景

在任务恢复过程中，发现了一个有趣的现象：
- 数据库中 `tutorial_metadata`, `resource_recommendation_metadata`, `quiz_metadata` 表都有数据（27条）
- 但 `roadmap_metadata.framework_data` 中的状态字段（`content_status`, `resources_status`, `quiz_status`）全部为 `pending`
- **前端却能正常显示教程、资源、测验内容**

这是为什么？

## 数据架构设计

### 双层数据存储

系统采用了**双层数据存储**架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    Roadmap Metadata                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  framework_data (JSON)                               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Stages → Modules → Concepts                   │  │   │
│  │  │    - concept_id                                │  │   │
│  │  │    - content_status: "pending"/"completed"     │  │   │
│  │  │    - resources_status: "pending"/"completed"   │  │   │
│  │  │    - quiz_status: "pending"/"completed"        │  │   │
│  │  │    - tutorial_id (引用)                        │  │   │
│  │  │    - resources_id (引用)                       │  │   │
│  │  │    - quiz_id (引用)                            │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 引用关系
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              独立的内容表（详细数据）                          │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐│
│  │ tutorial_      │  │ resource_        │  │ quiz_        ││
│  │   metadata     │  │   recommendation │  │   metadata   ││
│  │                │  │   _metadata      │  │              ││
│  │ - tutorial_id  │  │ - id             │  │ - quiz_id    ││
│  │ - concept_id   │  │ - concept_id     │  │ - concept_id ││
│  │ - content_url  │  │ - resources[]    │  │ - questions[]││
│  │ - summary      │  │ - count          │  │ - total      ││
│  └────────────────┘  └──────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 两层的作用

#### 第一层：framework_data（元数据层）

**位置**: `roadmap_metadata.framework_data` (JSON 字段)

**作用**:
1. **路线图结构**：定义学习路径（Stages → Modules → Concepts）
2. **状态管理**：记录每个概念的内容生成状态
3. **快速查询**：前端路线图概览页可以快速获取所有概念的状态
4. **引用索引**：存储 ID 引用，指向实际内容

**包含字段**:
```json
{
  "concept_id": "python-basics-001",
  "title": "Python 基础",
  "content_status": "completed",      // 状态标记
  "resources_status": "completed",    // 状态标记
  "quiz_status": "completed",         // 状态标记
  "tutorial_id": "tut-uuid-001",      // 引用 ID
  "resources_id": "res-uuid-001",     // 引用 ID
  "quiz_id": "quiz-uuid-001",         // 引用 ID
  "content_ref": "s3://bucket/..."    // 内容链接
}
```

#### 第二层：独立内容表（详细数据层）

**位置**: 
- `tutorial_metadata` 表
- `resource_recommendation_metadata` 表
- `quiz_metadata` 表

**作用**:
1. **存储完整内容**：教程的 Markdown、资源列表、测验题目
2. **版本管理**：支持多版本内容（教程有版本历史）
3. **结构化查询**：可以按各种条件查询内容
4. **解耦存储**：大数据量不影响 framework 查询性能

**包含数据**:
- 教程：完整的 Markdown 内容（存储在 S3）
- 资源：资源列表（JSON 数组）
- 测验：题目列表（JSON 数组）

### 前端如何获取数据？

#### 1. 路线图概览页

**API**: `GET /api/v1/roadmaps/{roadmap_id}`

**返回**: `framework_data` (包含状态信息)

**用途**: 
- 显示路线图结构
- 显示每个概念的生成状态
- 显示进度百分比

#### 2. 教程详情页

**API**: `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest`

**返回**: 从 `tutorial_metadata` 表查询

**用途**: 
- 获取教程内容
- 下载 Markdown
- 显示教程详情

这就是为什么即使 `framework_data` 中状态未更新，前端仍然能看到教程！

#### 3. 资源列表页

**API**: `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources`

**返回**: 从 `resource_recommendation_metadata` 表查询

#### 4. 测验页

**API**: `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz`

**返回**: 从 `quiz_metadata` 表查询

## 为什么需要两层？

### 优点

1. **性能优化**
   - 路线图概览只需查询一次 `framework_data`（JSON 字段）
   - 不需要 JOIN 多个表
   - 减少数据库查询次数

2. **数据解耦**
   - 内容变更不影响路线图结构
   - 可以独立管理内容版本
   - 大文件内容（Markdown）存储在 S3，不影响数据库性能

3. **灵活性**
   - 支持内容重新生成（版本管理）
   - 支持内容修改而不影响路线图
   - 可以添加新的内容类型

### 缺点

1. **数据同步风险**
   - 需要同时更新两层数据
   - 如果工作流中断，可能导致数据不一致
   - 需要额外的同步脚本修复

2. **复杂性增加**
   - 开发者需要理解双层架构
   - 数据更新需要同时操作两个地方

## 数据同步机制

### 正常流程

在 `WorkflowBrain.save_content_results()` 中：

```python
# 1. 保存到独立内容表
await tutorial_repo.save_tutorials_batch(tutorial_refs, roadmap_id)
await resource_repo.save_resources_batch(resource_refs, roadmap_id)
await quiz_repo.save_quizzes_batch(quiz_refs, roadmap_id)

# 2. 更新 framework_data 中的状态
for concept_id, tutorial_ref in tutorial_refs.items():
    # 找到对应的 concept
    concept["content_status"] = "completed"
    concept["tutorial_id"] = tutorial_ref["tutorial_id"]
    concept["content_ref"] = tutorial_ref["content_url"]

# 3. 保存更新后的 framework
await roadmap_repo.update_framework_data(roadmap_id, updated_framework)

# 4. 更新任务状态
await task_repo.update_task_status(task_id, status="completed")
```

### 异常情况

如果工作流在步骤 1 完成后中断（如连接池耗尽），会导致：
- ✅ 内容表有数据（教程已生成）
- ❌ framework_data 未更新（状态仍为 pending）
- ❌ 任务状态未更新（仍为 processing）

**解决方案**: 使用 `sync_task_results_to_framework.py` 脚本手动同步

## 修复脚本

已创建两个脚本处理任务恢复：

### 1. `recover_task_simple.py`

**功能**: 从 checkpoint 恢复任务执行

**使用场景**: 
- 任务在执行中被中断
- checkpoint 存在
- 希望继续执行工作流

### 2. `sync_task_results_to_framework.py`

**功能**: 同步已生成的内容到 framework_data

**使用场景**: 
- 内容已生成（内容表有数据）
- framework_data 未更新
- 任务状态未更新

**执行流程**:
1. 查询 tutorial_metadata, resource_recommendation_metadata, quiz_metadata
2. 构建 concept_id → content 的映射
3. 遍历 framework_data 中的所有 concept
4. 更新状态字段和引用 ID
5. 保存更新后的 framework_data
6. 更新任务状态

## 最佳实践

### 开发时

1. **同时更新两层**
   ```python
   # 保存内容
   await save_content_to_table(content)
   
   # 更新 framework
   await update_framework_status(concept_id, "completed")
   ```

2. **使用事务**
   ```python
   async with session.begin():
       await save_content_to_table(content)
       await update_framework_status(concept_id, "completed")
   ```

3. **添加日志**
   ```python
   logger.info("content_saved", concept_id=concept_id)
   logger.info("framework_updated", concept_id=concept_id)
   ```

### 部署时

1. **启用任务恢复**
   ```bash
   ENABLE_TASK_RECOVERY=true
   TASK_RECOVERY_MAX_AGE_HOURS=24
   ```

2. **监控数据一致性**
   - 定期检查 framework_data 与内容表的一致性
   - 设置告警

3. **准备恢复脚本**
   - 保留 `sync_task_results_to_framework.py`
   - 定期测试恢复流程

## 总结

双层数据架构的设计是为了平衡性能和灵活性：
- **framework_data** 提供快速的结构和状态查询
- **独立内容表** 提供详细的内容存储和版本管理

虽然增加了数据同步的复杂性，但通过：
- 完善的事务管理
- 自动任务恢复机制
- 手动同步脚本

可以有效处理各种异常情况，确保数据一致性。

**关键要点**: 前端能看到教程，是因为它直接查询 `tutorial_metadata` 表，而不依赖 `framework_data` 中的状态字段。但 `framework_data` 的状态字段对于路线图概览和进度显示仍然很重要。

