# 任务恢复完整总结

## 问题描述

任务 ID: `49961d40-0cac-4255-abba-adad0b901056`
路线图 ID: `agent-performance-tuning-x5y9z2w8`

**症状**:
1. 任务状态卡在 `processing`，当前步骤为 `content_generation`
2. 数据库中教程、资源、测验已生成（27条记录）
3. `roadmap_metadata.framework_data` 中状态字段未更新（全部为 `pending`）
4. 后端没有任务在运行

**根本原因**:
- 内容生成过程中因连接池耗尽导致任务中断
- 数据已写入独立内容表，但 `framework_data` 和任务状态未同步更新

## 解决方案

### 1. 从 Checkpoint 恢复任务

使用脚本：`backend/scripts/recover_task_simple.py`

```bash
cd backend
uv run python scripts/recover_task_simple.py 49961d40-0cac-4255-abba-adad0b901056
```

**结果**: 
- ✅ Checkpoint 找到
- ✅ 任务恢复执行
- ⚠️  但数据未完全同步（framework_data 仍未更新）

### 2. 手动同步数据到 framework_data

使用脚本：`backend/scripts/sync_task_results_to_framework.py`

```bash
cd backend
uv run python scripts/sync_task_results_to_framework.py 49961d40-0cac-4255-abba-adad0b901056
```

**流程**:
1. 从数据库查询已生成的教程/资源/测验
2. 遍历 `framework_data` 中的所有概念
3. 更新状态字段和引用 ID
4. 保存更新后的 `framework_data`
5. 更新任务状态

**结果**:
- ✅ 27/30 个概念同步成功
- ✅ 3 个概念标记为失败（这是正常的，因为只生成了 27 条记录）
- ✅ 任务状态更新为 `partial_failure`

### 3. 修复模型定义缺失字段

**问题**: `Concept` 模型中缺少 `tutorial_id` 字段

**修复**: 在 `backend/app/models/domain.py` 中添加字段：

```python
class Concept(BaseModel):
    # ... 其他字段 ...
    
    # 教程内容引用
    content_status: Literal["pending", "generating", "completed", "failed"] = "pending"
    tutorial_id: Optional[str] = Field(None, description="教程 ID（UUID 格式）")  # ← 新增
    content_ref: Optional[str] = None
    # ... 其他字段 ...
```

**原因**: 
- Pydantic 的 `model_validate()` 会过滤掉未定义的字段
- 导致 `tutorial_id` 在保存时丢失

## 最终状态

### 任务状态
- **状态**: `partial_failure` ✅
- **步骤**: `content_generation`
- **完成度**: 27/30 (90%)
- **失败概念**: 3 个

### Framework Data 状态
```
总概念数: 30
教程已完成: 27/30 (90%)
资源已完成: 27/30 (90%)
测验已完成: 27/30 (90%)
包含完整引用: 27/27 (100%)
```

### 数据库表状态
```
tutorial_metadata: 27 条记录 ✅
resource_recommendation_metadata: 27 条记录 ✅
quiz_metadata: 27 条记录 ✅
```

## 技术发现

### 双层数据架构

系统采用双层数据存储：

**第一层**: `framework_data` (JSON 字段)
- 作用：存储路线图结构和状态
- 包含：状态字段 + 引用 ID
- 用于：快速查询路线图概览

**第二层**: 独立内容表
- 表：`tutorial_metadata`, `resource_recommendation_metadata`, `quiz_metadata`
- 作用：存储详细内容
- 用于：前端直接查询内容

**关键**: 前端获取教程/资源/测验时，**直接从数据库表查询**，而不是从 `framework_data` 读取。这就是为什么即使 `framework_data` 未更新，前端仍能看到内容。

### API 端点

**路线图概览**:
```
GET /api/v1/roadmaps/{roadmap_id}
→ 返回 framework_data (包含状态)
```

**教程详情**:
```
GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest
→ 直接查询 tutorial_metadata 表
```

**资源列表**:
```
GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources
→ 直接查询 resource_recommendation_metadata 表
```

**测验题目**:
```
GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
→ 直接查询 quiz_metadata 表
```

## 创建的工具

### 1. `recover_task_simple.py`
- **功能**: 从 checkpoint 恢复任务执行
- **适用**: 任务中断且 checkpoint 存在

### 2. `sync_task_results_to_framework.py`
- **功能**: 同步已生成内容到 framework_data
- **适用**: 内容已生成但状态未更新

### 3. `check_task_recovery_status.py`
- **功能**: 检查任务状态和数据一致性
- **适用**: 诊断数据同步问题

### 4. `verify_framework_sync.py`
- **功能**: 验证 framework_data 同步情况
- **适用**: 检查引用字段完整性

## 预防措施

### 1. 配置自动恢复

确保环境变量已设置：
```bash
ENABLE_TASK_RECOVERY=true
TASK_RECOVERY_MAX_AGE_HOURS=24
TASK_RECOVERY_MAX_CONCURRENT=3
```

### 2. 连接池优化

已优化连接池配置（避免再次出现连接池耗尽）：
- SQLAlchemy: `pool_size=50, max_overflow=50` (总计 100)
- Checkpointer: `min_size=2, max_size=10` (总计 10)

### 3. 数据一致性检查

定期运行检查脚本：
```bash
python scripts/check_task_recovery_status.py {task_id}
```

## 教训总结

1. **双层架构需要同步**: 
   - 更新内容表后必须同步更新 framework_data
   - 使用事务确保原子性

2. **模型定义要完整**:
   - Pydantic 会过滤未定义的字段
   - 添加新字段时要更新模型定义

3. **任务恢复机制很重要**:
   - Checkpoint 可以恢复工作流执行
   - 但数据保存逻辑需要单独处理

4. **数据架构的透明性**:
   - 前端直接查询内容表，不依赖 framework_data
   - framework_data 主要用于状态管理和概览

## 后续建议

1. **重试失败的概念**:
   - 使用重试 API 重新生成失败的 3 个概念
   - 或接受 90% 的完成度

2. **监控告警**:
   - 监控连接池使用率
   - 设置任务超时告警
   - 检测数据不一致

3. **文档维护**:
   - 更新数据架构文档
   - 记录常见故障排查步骤
   - 保持恢复脚本可用性

## 相关文档

- [数据架构说明](./DATA_ARCHITECTURE_EXPLANATION.md)
- [连接池配置优化](./DATABASE_CONNECTION_POOL_EXHAUSTION_FIX.md)
- [智能重试机制](../doc/INTELLIGENT_RETRY_MECHANISM.md)

