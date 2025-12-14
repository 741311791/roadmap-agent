# Framework Data 同步问题解决方案

## 问题描述

内容生成完成后，独立元数据表（`TutorialMetadata`、`ResourceRecommendationMetadata`、`QuizMetadata`）有数据，但 `roadmap_metadata.framework_data` 中的 Concept 对象没有对应的引用字段（`content_ref`、`resources_id`、`quiz_id`），导致前端无法获取这些信息。

## 根本原因

### 1. 代码逻辑已实现但历史数据未更新

查看 `backend/app/core/orchestrator/workflow_brain.py`，发现 `save_content_results()` 方法已经实现了更新 `framework_data` 的逻辑：

```python
# workflow_brain.py: 463-642 行
async def save_content_results(...):
    # 保存独立元数据表
    await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
    await repo.save_resources_batch(resource_refs, roadmap_id)
    await repo.save_quizzes_batch(quiz_refs, roadmap_id)
    
    # ✅ 更新 roadmap_metadata 的 framework_data
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if roadmap_metadata and roadmap_metadata.framework_data:
        updated_framework = self._update_framework_with_content_refs(
            framework_data=roadmap_metadata.framework_data,
            tutorial_refs=tutorial_refs,
            resource_refs=resource_refs,
            quiz_refs=quiz_refs,
            failed_concepts=failed_concepts,
        )
        # 保存更新后的 framework
        await repo.save_roadmap_metadata(...)
```

代码逻辑正确，但历史数据（在此修复之前生成的路线图）没有被更新。

### 2. 字段名称正确

检查了 Domain Models：
- `TutorialGenerationOutput.content_url` ✅
- `ResourceRecommendationOutput.id` ✅
- `QuizGenerationOutput.quiz_id` ✅

字段名称与代码中使用的一致。

## 解决方案

### 1. 修复脚本：`fix_framework_data_sync.py`

创建了修复脚本来同步已有数据：

```python
# backend/scripts/fix_framework_data_sync.py

async def fix_single_roadmap(roadmap_id: str):
    """修复单个路线图的 framework_data"""
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 1. 读取 framework_data
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        framework_data = metadata.framework_data
        
        # 2. 读取独立元数据表
        tutorials = {概念ID: 教程数据}
        resources = {概念ID: 资源数据}
        quizzes = {概念ID: 测验数据}
        
        # 3. 更新 framework_data
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    # 更新教程
                    if concept_id in tutorials:
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorials[concept_id]["content_url"]
                        concept["content_summary"] = tutorials[concept_id]["summary"]
                    
                    # 更新资源
                    if concept_id in resources:
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resources[concept_id]["id"]
                        concept["resources_count"] = resources[concept_id]["resources_count"]
                    
                    # 更新测验
                    if concept_id in quizzes:
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quizzes[concept_id]["quiz_id"]
                        concept["quiz_questions_count"] = quizzes[concept_id]["total_questions"]
        
        # 4. 使用 UPDATE 语句直接更新数据库
        from sqlalchemy import update
        from app.models.database import RoadmapMetadata
        
        stmt = (
            update(RoadmapMetadata)
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
            .values(framework_data=framework_data)
        )
        await session.execute(stmt)
        await session.commit()
```

### 2. 关键修复点

#### 问题1：`ResourceRecommendationMetadata` 表字段名错误

修复前：
```python
SELECT concept_id, resources_id, resources_count
FROM resource_recommendation_metadata
```

修复后：
```python
SELECT concept_id, id, resources_count
FROM resource_recommendation_metadata
```

**原因**：`ResourceRecommendationMetadata` 表的主键是 `id`，不是 `resources_id`。

#### 问题2：缩进错误导致保存逻辑不执行

修复前（缩进错误）：
```python
if updated_count == 0:
    print("⚠️  没有需要更新的 Concept")
    return False

    # 4. 保存回数据库（这里缩进错了，在 if 内部）
    framework_obj = RoadmapFramework.model_validate(framework_data)
    await repo.save_roadmap_metadata(...)
```

修复后：
```python
if updated_count == 0:
    print("⚠️  没有需要更新的 Concept")
    return False

# 4. 保存回数据库（缩进正确）
stmt = (
    update(RoadmapMetadata)
    .where(RoadmapMetadata.roadmap_id == roadmap_id)
    .values(framework_data=framework_data)
)
await session.execute(stmt)
await session.commit()
```

#### 问题3：事务管理问题

修复前：使用 `repo.save_roadmap_metadata()` 方法，该方法内部会调用 `commit()`，导致重复提交或session管理混乱。

修复后：直接使用 `UPDATE` 语句更新数据库，避免事务管理问题。

## 修复结果

运行修复脚本后：

```bash
cd backend && uv run python scripts/fix_framework_data_sync.py
```

结果：
- **修复成功**: 7 个路线图
- **跳过**: 3 个路线图（没有内容数据）

验证数据：
```sql
SELECT 
    (framework_data->'stages'->0->'modules'->0->'concepts'->0->>'content_ref') as content_ref,
    (framework_data->'stages'->0->'modules'->0->'concepts'->0->>'resources_id') as resources_id,
    (framework_data->'stages'->0->'modules'->0->'concepts'->0->>'quiz_id') as quiz_id
FROM roadmap_metadata 
WHERE roadmap_id = 'n8n-workflow-automation-d5c4b3a2';
```

结果：
- `content_ref`: `http://47.111.115.130:9000/roadmap/...`
- `resources_id`: `56acedd0-3791-46e9-a76f-3650ccdb983f`
- `quiz_id`: `aa0fed4e-e0ae-4a43-be9b-78dd03d13aac`

✅ 数据成功更新！

## 诊断脚本

创建了 `diagnose_framework_data.py` 用于检查数据一致性：

```bash
cd backend && uv run python scripts/diagnose_framework_data.py
```

输出示例：
```
🗺️  路线图: 从零搭建N8N自动化工作流完整学习路线
📈 统计信息:
   总 Concept 数: 18
   包含 content_ref 的: 6 (33.3%)
   包含 resources_id 的: 6 (33.3%)
   包含 quiz_id 的: 6 (33.3%)
```

**注意**：比例不是100%的原因是独立元数据表中只有部分 Concept 的数据（内容生成时部分失败）。

## 未来预防措施

### 1. 确保 `WorkflowBrain.save_content_results()` 被正确调用

在 `ContentRunner.run()` 中已经正确调用：

```python
# backend/app/core/orchestrator/node_runners/content_runner.py:170
await self.brain.save_content_results(
    task_id=state["task_id"],
    roadmap_id=state.get("roadmap_id"),
    tutorial_refs=tutorial_refs,
    resource_refs=resource_refs,
    quiz_refs=quiz_refs,
    failed_concepts=failed_concepts,
)
```

### 2. 添加数据一致性检查

定期运行诊断脚本检查数据一致性：
```bash
cd backend && uv run python scripts/diagnose_framework_data.py
```

### 3. 监控日志

在内容生成完成后，检查日志确认 framework 更新：
```
workflow_brain_framework_updated_with_content_refs
```

如果没有此日志，说明更新失败。

## 相关文件

- **修复脚本**: `backend/scripts/fix_framework_data_sync.py`
- **诊断脚本**: `backend/scripts/diagnose_framework_data.py`
- **核心逻辑**: `backend/app/core/orchestrator/workflow_brain.py`
- **ContentRunner**: `backend/app/core/orchestrator/node_runners/content_runner.py`

## 总结

1. ✅ 代码逻辑已正确实现
2. ✅ 历史数据已通过修复脚本同步
3. ✅ 未来生成的路线图会自动更新 framework_data
4. ✅ 提供诊断工具用于检查数据一致性

---

**修复日期**: 2025-12-13  
**修复人**: AI Assistant  
**状态**: ✅ 已完成并验证
