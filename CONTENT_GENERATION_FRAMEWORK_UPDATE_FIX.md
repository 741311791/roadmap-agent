# 内容生成后 Framework 更新 Bug 修复

## 问题描述

**Bug**: 在路线图生成过程中，内容生成（教程、资源、测验）完成后，只更新了独立的元数据表（`TutorialMetadata`、`ResourceRecommendationMetadata`、`QuizMetadata`），但**没有更新** `roadmap_metadata.framework_data` 中的 Concept 对象。

### 影响

- 虽然全局状态（`RoadmapState`）在工作流执行期间是正确的
- 但 `roadmap_metadata.framework_data` 中的 Concept 对象缺少内容引用字段：
  - `content_ref`（教程 URL）
  - `content_summary`（教程摘要）
  - `resources_id`（资源推荐 ID）
  - `resources_count`（资源数量）
  - `quiz_id`（测验 ID）
  - `quiz_questions_count`（测验题目数量）
- 导致前端查询路线图详情时无法获取这些关键信息

## 问题证据

### 证据1：全局状态有更新 ✅

在 `ContentRunner.run()` 中，返回值包含所有生成结果：

```python
# backend/app/core/orchestrator/node_runners/content_runner.py:127-138
return {
    "tutorial_refs": tutorial_refs,
    "resource_refs": resource_refs,
    "quiz_refs": quiz_refs,
    "failed_concepts": failed_concepts,
    "current_step": "content_generation",
    "execution_history": [
        f"内容生成完成: {len(tutorial_refs)} 个教程, "
        f"{len(resource_refs)} 个资源, "
        f"{len(quiz_refs)} 个测验"
    ],
}
```

这些通过 LangGraph 的 reducer 机制正确合并到全局状态。

### 证据2：roadmap_metadata 没有更新 ❌

在修复前，`WorkflowBrain.save_content_results()` 只保存了独立表：

```python
# 修复前的代码
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    
    # 只保存独立的元数据表
    if tutorial_refs:
        await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
    if resource_refs:
        await repo.save_resources_batch(resource_refs, roadmap_id)
    if quiz_refs:
        await repo.save_quizzes_batch(quiz_refs, roadmap_id)
    
    # 更新 task 状态
    await repo.update_task_status(...)
    
    await session.commit()
    # ❌ 没有更新 roadmap_metadata.framework_data
```

### 证据3：其他地方有正确实现

在重试失败内容和脚本中，都有正确的实现：

```python
# backend/app/api/v1/roadmap.py:1632-1639
# 保存更新后的框架
from app.models.domain import RoadmapFramework
updated_framework = RoadmapFramework.model_validate(framework_data)
await repo.save_roadmap_metadata(
    roadmap_id=roadmap_id,
    user_id=roadmap_metadata.user_id,
    framework=updated_framework,
)
```

## 修复方案

### 修改文件

- `backend/app/core/orchestrator/workflow_brain.py`

### 修改内容

#### 1. 在 `save_content_results()` 中添加 framework 更新逻辑

```python
async def save_content_results(
    self,
    task_id: str,
    roadmap_id: str,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
):
    """
    保存内容生成结果（批量事务操作）
    
    在同一事务中执行:
    1. 批量保存 TutorialMetadata
    2. 批量保存 ResourceRecommendationMetadata
    3. 批量保存 QuizMetadata
    4. ✅ 更新 roadmap_metadata 的 framework_data（新增）
    5. 更新 task 最终状态
    """
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 批量保存元数据
        if tutorial_refs:
            await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
        if resource_refs:
            await repo.save_resources_batch(resource_refs, roadmap_id)
        if quiz_refs:
            await repo.save_quizzes_batch(quiz_refs, roadmap_id)
        
        # ✅ 新增：更新 roadmap_metadata 的 framework_data
        roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
        if roadmap_metadata and roadmap_metadata.framework_data:
            # 使用辅助方法更新 framework 中的 Concept 状态
            updated_framework = self._update_framework_with_content_refs(
                framework_data=roadmap_metadata.framework_data,
                tutorial_refs=tutorial_refs,
                resource_refs=resource_refs,
                quiz_refs=quiz_refs,
                failed_concepts=failed_concepts,
            )
            
            # 保存更新后的 framework
            from app.models.domain import RoadmapFramework
            framework_obj = RoadmapFramework.model_validate(updated_framework)
            await repo.save_roadmap_metadata(
                roadmap_id=roadmap_id,
                user_id=roadmap_metadata.user_id,
                framework=framework_obj,
            )
        
        # 更新 task 状态
        await repo.update_task_status(...)
        await session.commit()
```

#### 2. 新增辅助方法 `_update_framework_with_content_refs()`

```python
def _update_framework_with_content_refs(
    self,
    framework_data: dict,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
) -> dict:
    """
    更新 framework 中所有 Concept 的内容引用字段
    
    遍历 framework_data 中的所有 Concept，根据生成结果更新：
    - content_status, content_ref, content_summary（教程）
    - resources_status, resources_id, resources_count（资源）
    - quiz_status, quiz_id, quiz_questions_count（测验）
    """
    # 遍历三层结构：Stage -> Module -> Concept
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                if not concept_id:
                    continue
                
                # 更新教程相关字段
                if concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept_id]
                    concept["content_status"] = "completed"
                    concept["content_ref"] = tutorial_output.content_url
                    concept["content_summary"] = tutorial_output.summary
                elif concept_id in failed_concepts:
                    if "content_status" not in concept or concept["content_status"] == "pending":
                        concept["content_status"] = "failed"
                
                # 更新资源相关字段
                if concept_id in resource_refs:
                    resource_output = resource_refs[concept_id]
                    concept["resources_status"] = "completed"
                    concept["resources_id"] = resource_output.id
                    concept["resources_count"] = len(resource_output.resources)
                elif concept_id in failed_concepts:
                    if "resources_status" not in concept or concept["resources_status"] == "pending":
                        concept["resources_status"] = "failed"
                
                # 更新测验相关字段
                if concept_id in quiz_refs:
                    quiz_output = quiz_refs[concept_id]
                    concept["quiz_status"] = "completed"
                    concept["quiz_id"] = quiz_output.quiz_id
                    concept["quiz_questions_count"] = quiz_output.total_questions
                elif concept_id in failed_concepts:
                    if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                        concept["quiz_status"] = "failed"
    
    return framework_data
```

## 修复验证

### 修复后的执行流程

1. **内容生成** (`ContentRunner.run()`)
   - 并行生成教程、资源、测验
   - 返回 `tutorial_refs`, `resource_refs`, `quiz_refs`
   - ✅ 更新全局状态（`RoadmapState`）

2. **保存结果** (`WorkflowBrain.save_content_results()`)
   - 保存独立元数据表（`TutorialMetadata`, `ResourceRecommendationMetadata`, `QuizMetadata`）
   - ✅ **读取 roadmap_metadata**
   - ✅ **更新 framework_data 中的 Concept 字段**
   - ✅ **保存更新后的 framework_data**
   - 更新 task 状态

### 数据一致性保证

修复后，以下数据保持一致：

| 数据源 | 状态 | 说明 |
|--------|------|------|
| **RoadmapState**（内存） | ✅ 正确 | 工作流执行期间的全局状态 |
| **TutorialMetadata**（数据库） | ✅ 正确 | 教程详细信息 |
| **ResourceRecommendationMetadata**（数据库） | ✅ 正确 | 资源推荐详细信息 |
| **QuizMetadata**（数据库） | ✅ 正确 | 测验详细信息 |
| **roadmap_metadata.framework_data**（数据库） | ✅ **修复后正确** | Concept 包含完整的内容引用 |

### 事务原子性

所有操作在同一事务中执行，确保数据一致性：

```python
async with AsyncSessionLocal() as session:
    # 1. 保存独立元数据
    await repo.save_tutorials_batch(...)
    await repo.save_resources_batch(...)
    await repo.save_quizzes_batch(...)
    
    # 2. 更新 framework_data
    await repo.save_roadmap_metadata(...)
    
    # 3. 更新 task 状态
    await repo.update_task_status(...)
    
    # 4. 提交事务（全部成功或全部回滚）
    await session.commit()
```

## 测试建议

### 1. 单元测试

```python
async def test_save_content_results_updates_framework():
    """测试 save_content_results 是否正确更新 framework_data"""
    # 准备测试数据
    tutorial_refs = {
        "concept-1": TutorialGenerationOutput(
            tutorial_id="tut-1",
            concept_id="concept-1",
            content_url="http://...",
            summary="测试教程",
            ...
        )
    }
    
    # 执行保存
    await brain.save_content_results(
        task_id="test-task",
        roadmap_id="test-roadmap",
        tutorial_refs=tutorial_refs,
        resource_refs={},
        quiz_refs={},
        failed_concepts=[],
    )
    
    # 验证 framework_data 已更新
    metadata = await repo.get_roadmap_metadata("test-roadmap")
    assert metadata.framework_data["stages"][0]["modules"][0]["concepts"][0]["content_ref"] == "http://..."
```

### 2. 集成测试

生成一个完整的路线图，验证：
- [ ] 所有 Concept 的 `content_status` 为 "completed"
- [ ] 所有 Concept 包含 `content_ref` 字段
- [ ] 所有 Concept 包含 `resources_id` 字段
- [ ] 所有 Concept 包含 `quiz_id` 字段
- [ ] 前端可以正确展示所有内容

### 3. 回归测试

检查现有功能是否受影响：
- [ ] 路线图生成流程正常
- [ ] 内容重试功能正常
- [ ] 路线图详情查询正常
- [ ] 进度追踪正常

## 相关文件

### 修改的文件
- `backend/app/core/orchestrator/workflow_brain.py`

### 参考实现
- `backend/app/api/v1/roadmap.py:1632-1639`（重试失败内容）
- `backend/scripts/generate_tutorials_for_roadmap.py:103-113`（脚本实现）
- `backend/app/api/v1/endpoints/generation.py:333-396`（单个内容修改）

## 总结

- **问题根源**：内容生成完成后缺少更新 `roadmap_metadata.framework_data` 的逻辑
- **修复方式**：在 `WorkflowBrain.save_content_results()` 中添加框架更新步骤
- **影响范围**：所有新生成的路线图（修复后生成的路线图将包含完整的内容引用）
- **数据迁移**：历史数据可以通过重新生成内容或运行修复脚本来更新

---

**修复时间**: 2025-12-13  
**修复人**: AI Assistant  
**状态**: ✅ 已完成

