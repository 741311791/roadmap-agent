# 已归档的 Repository 脚本

> **归档日期**: 2026-01-08  
> **归档原因**: Repository → CRUD 架构迁移完成

---

## 📦 本目录包含的脚本

本目录包含 **14个** 使用旧 Repository 模式的历史脚本，这些脚本因架构升级已无法直接使用。

### 归档脚本列表

1. **test_intent_analysis.py** - 意图分析测试
2. **test_framework_data_and_concept_status.py** - 框架数据与概念状态测试
3. **reset_assessment_pool.py** - 重置评估池
4. **test_refactored_system.py** - 重构系统测试
5. **test_framework_data_update.py** - 框架数据更新测试
6. **fix_single_roadmap.py** - 修复单个路线图
7. **fix_framework_data_sync.py** - 修复框架数据同步
8. **diagnose_framework_data.py** - 诊断框架数据
9. **generate_tutorials_for_roadmap.py** - 为路线图生成教程
10. **approve_pending_tasks.py** - 批准待处理任务
11. **test_repository_migration.py** - Repository 迁移测试
12. **test_modification_system.py** - 修改系统测试
13. **test_e2e_acceptance.py** - 端到端验收测试
14. **test_streaming_db_write.py** - 流式数据库写入测试

---

## ⚠️ 这些脚本的问题

所有脚本都使用了已删除的 Repository 类：

```python
# ❌ 已删除的导入
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.db.repositories.task_repo import TaskRepository
# ... 等等
```

---

## 🔧 如需重新启用某个脚本

需要将 Repository 调用替换为 CRUD：

### 迁移示例

```python
# ❌ 旧代码（Repository 模式）
from app.db.repositories.roadmap_repo import RoadmapRepository

async with get_db() as session:
    repo = RoadmapRepository(session)
    roadmap = await repo.get_roadmap_metadata(roadmap_id)

# ✅ 新代码（CRUD 模式）
from app.crud.crud_roadmap import get_roadmap_crud

async with get_db() as session:
    crud = get_roadmap_crud()
    roadmap = await crud.get_by_roadmap_id(session, roadmap_id)
```

### Repository → CRUD 映射

| 旧 Repository | 新 CRUD | 位置 |
|--------------|---------|------|
| RoadmapRepository | RoadmapCRUD | `app.crud.crud_roadmap` |
| TaskRepository | TaskCRUD | `app.crud.crud_task` |
| ConceptRepository | ConceptCRUD | `app.crud.crud_concept` |
| TutorialRepository | TutorialCRUD | `app.crud.crud_tutorial` |
| ResourceRepository | ResourceCRUD | `app.crud.crud_resource` |
| QuizRepository | QuizCRUD | `app.crud.crud_quiz` |
| TechAssessmentRepository | TechAssessmentCRUD | `app.crud.crud_tech_assessment` |

---

## 📋 建议

1. **确认不再需要** → 可长期保留在此目录（不影响系统运行）
2. **需要重新启用** → 按上述迁移指南更新代码
3. **完全确认废弃** → 可考虑删除（建议保留至少3个月）

---

## 📚 相关文档

- [Repository 清理工作完成报告](../../docs/20260108_Repository清理工作完成报告.md)
- [CRUD 架构说明](../../docs/ARCHITECTURE.md)

---

**归档人**: AI Assistant  
**最后更新**: 2026-01-08

