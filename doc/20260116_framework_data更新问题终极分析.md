# framework_data更新问题终极分析

**日期**: 2026-01-16  
**优先级**: 🔴 Critical  
**状态**: ✅ 已确认根因

---

## 🎯 问题确认

**现象**: `roadmap_metadata` 表中的 `framework_data` 字段没有包含内容引用 (content_refs)

**影响**: 用户无法通过API查询到tutorial_id, resources_id, quiz_id等内容

---

## 📊 数据证据

### 测试路线图: `python-fullstack-engineer-9b2k4m8p`

| 数据源 | 状态 | 证据 |
|-------|------|------|
| **ConceptMetadata** | ✅ 完全正常 | Tutorial: 100% (39/39)<br>Resources: 97.4% (38/39)<br>Quiz: 100% (39/39) |
| **framework_data** | ❌ 完全缺失 | tutorial_id: 0% (0/39)<br>resources_id: 0% (0/39)<br>quiz_id: 0% (0/39) |
| **更新时间** | ❌ 异常 | created_at: 2026-01-15 09:58:06<br>updated_at: 2026-01-15 09:58:06<br>**相差仅0.02秒** |

### 关键时间线

```
09:24:43 - 任务创建
09:58:06 - roadmap_metadata 创建 (curriculum_design节点)
10:00:58 - 第一个Concept完成 (ConceptMetadata)
10:03:52 - 任务标记为completed
```

**矛盾点**: 
- ✅ ConceptMetadata在10:00-10:03之间正常保存
- ❌ roadmap_metadata在09:58创建后**从未更新**

---

## 🔗 根因追踪 (第一性原理)

### 关键日志证据

```log
2026-01-15 09:58:38 | ERROR | app.core.orchestrator.subgraphs.content_generation_legacy
  resource_recommendation_failed

2026-01-15 10:03:52 | WARNING | app.core.orchestrator.handlers.registry
  handler_not_found | node_name=final_aggregation
  
2026-01-15 10:03:52 | WARNING | app.services.workflows.execution.workflow_execution_service
  workflow_incomplete | current_step=content_generation
```

### 因果链推导

```
任务在旧代码时创建 (2026-01-15 09:24)
    ↓
使用旧版本的 content_generation_legacy.py
    ↓
旧版本子图架构:
    fan_out → [generate_tutorial, generate_resource, generate_quiz] → END
    ❌ 没有 final_aggregation 节点
    ↓
各Concept的元数据正常保存到 ConceptMetadata
    ↓
但缺少汇总节点,不会调用 update_framework_batch
    ↓
framework_data 从未被更新
    ↓
更新时间停留在创建时刻
```

### 代码架构变迁

**旧版本** (`content_generation_legacy.py` - 已废弃):
```python
# ❌ 没有 final_aggregation
builder.add_edge(NodeName.GENERATE_TUTORIAL.value, END)
builder.add_edge(NodeName.GENERATE_RESOURCE.value, END)
builder.add_edge(NodeName.GENERATE_QUIZ.value, END)
```

**新版本** (`content_generation.py` - 当前使用):
```python
# ✅ 有 final_aggregation, 会更新framework_data
builder.add_edge("single_concept_subgraph", "final_aggregation")
builder.add_edge("final_aggregation", END)

async def final_aggregation(state, config):
    # 批量更新 Framework
    await handler.update_framework_batch(
        session=session,
        roadmap_id=roadmap_id,
        concept_results=concept_results,
    )
```

**导入配置** (`subgraphs/__init__.py`):
```python
from .content_generation import build_content_generation_subgraph  # ✅ 正确
```

---

## 🛠️ 解决方案

### 方案1: 修复历史数据 (推荐)

为旧任务补充framework_data的content_refs。

**实施步骤**:

1. 查询所有 `updated_at ≈ created_at` 的 roadmap_metadata
2. 对每个roadmap:
   - 从 ConceptMetadata 读取 tutorial_id, resources_id, quiz_id
   - 更新 framework_data 中对应的字段
   - 更新 updated_at 时间戳

**SQL实现**:
```sql
-- 1. 查找需要修复的roadmap
SELECT roadmap_id, title, created_at, updated_at
FROM roadmap_metadata
WHERE updated_at - created_at < INTERVAL '1 second'
AND roadmap_id IN (
    SELECT DISTINCT roadmap_id FROM concept_metadata
    WHERE tutorial_status = 'completed'
);

-- 2. 修复逻辑需要用Python脚本实现 (遍历framework_data JSON)
```

**Python修复脚本**:
```python
async def fix_framework_data(roadmap_id: str):
    async with async_session_maker.begin() as session:
        # 1. 获取roadmap和所有ConceptMetadata
        roadmap = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        concepts = await concept_crud.get_by_roadmap(session, roadmap_id)
        
        # 2. 构建concept_id -> metadata的映射
        metadata_map = {c.concept_id: c for c in concepts}
        
        # 3. 更新framework_data
        framework_data = roadmap.framework_data
        for stage in framework_data['stages']:
            for module in stage['modules']:
                for concept in module['concepts']:
                    concept_id = concept['concept_id']
                    if concept_id in metadata_map:
                        meta = metadata_map[concept_id]
                        
                        # 更新ID字段
                        concept['tutorial_id'] = meta.tutorial_id
                        concept['resources_id'] = meta.resources_id
                        concept['quiz_id'] = meta.quiz_id
                        
                        # 更新status字段
                        concept['tutorial_status'] = meta.tutorial_status
                        concept['resources_status'] = meta.resources_status
                        concept['quiz_status'] = meta.quiz_status
        
        # 4. 保存回数据库
        roadmap.framework_data = framework_data
        await session.flush()
```

---

### 方案2: 忽略历史数据

**原因**: 历史任务已完成，用户可以通过重新生成获得正确数据

**不推荐理由**:
- ❌ 用户体验差 (已有数据丢失)
- ❌ 浪费资源 (重新生成需要调用LLM)

---

## ✅ 验证当前代码

### 检查清单

- [x] 新版本导入正确: `from .content_generation import ...` ✅
- [x] 新版本有 final_aggregation 节点 ✅
- [x] final_aggregation 调用 update_framework_batch ✅
- [x] update_framework_batch 逻辑完整 ✅
- [ ] **需要验证**: 新任务是否正常更新framework_data

### 验证方法

创建一个新的测试任务，检查其framework_data：

```bash
# 1. 通过API创建新任务
curl -X POST http://localhost:8000/api/v1/tasks/generate \
  -H "Content-Type: application/json" \
  -d '{...}'

# 2. 等待任务完成

# 3. 检查framework_data
python scripts/check_framework_data.py <new_roadmap_id>

# 4. 预期结果
# ✅ tutorial_id: 100%
# ✅ resources_id: 100%
# ✅ quiz_id: 100%
```

---

## 📋 修复脚本实现

我将创建自动修复脚本:
- `scripts/fix_framework_data.py` - 修复单个roadmap
- `scripts/batch_fix_framework_data.py` - 批量修复所有旧roadmap

---

## 经验总结

### 第一性原理

1. **数据一致性**: ORM元数据表 (ConceptMetadata) 和业务数据 (framework_data) 必须同步
2. **时间戳审计**: `updated_at - created_at ≈ 0` 是数据未更新的明确信号
3. **版本迁移**: 架构升级时必须考虑历史数据兼容性
4. **日志追踪**: 关键业务操作 (如framework更新) 必须有明确的日志标记

### 架构改进建议

1. **数据库触发器**: 自动同步ConceptMetadata变化到framework_data
2. **健康检查API**: 定期检查数据一致性 (metadata vs framework_data)
3. **迁移脚本**: 架构升级时提供自动修复工具
4. **监控告警**: 检测 `updated_at` 长时间未变化的记录

