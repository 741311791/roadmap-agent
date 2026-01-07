# Week 3: Repository 清理迁移计划

> **执行日期**: 2026-01-07  
> **目标**: 彻底清理 `app/db/repositories/` 目录，将所有引用迁移到CRUD层  
> **影响范围**: 31个文件，69处引用

---

## 📊 当前状况

### 引用统计

| Repository | 引用次数 | 主要使用位置 | 对应CRUD状态 |
|-----------|---------|------------|------------|
| **roadmap_repo** | ~15 | services, api, tasks | ✅ RoadmapCRUD 已存在 |
| **task_repo** | ~8 | celery_session, tasks | ✅ TaskCRUD 已存在 |
| **concept_meta_repo** | ~5 | services | ✅ ConceptCRUD 已存在 |
| **tutorial_repo** | ~3 | celery_session | ✅ TutorialCRUD 已存在 |
| **resource_repo** | ~3 | celery_session | ✅ ResourceCRUD 已存在 |
| **quiz_repo** | ~3 | celery_session | ✅ QuizCRUD 已存在 |
| **tech_assessment_repo** | 3 | tech_assessment_service | ❌ 需创建 TechAssessmentCRUD |
| **user_profile_repo** | 2 | tech_assessment_service | ❌ 需创建 UserProfileCRUD |
| **intent_analysis_repo** | 2 | celery_session | ❌ 需创建 IntentAnalysisCRUD |
| **execution_log_repo** | 2 | celery_session | ❌ 需创建 ExecutionLogCRUD |
| **validation_repo** | 2 | validation_service, celery_session | ❌ 需创建 ValidationCRUD |
| **edit_repo** | 2 | edit_service, celery_session | ❌ 需创建 EditCRUD |
| **tavily_key_repo** | 2 | web_search_router | ⚠️ 特殊处理（需保留或迁移） |
| **其他** | ~19 | 各处 | ❌ 需评估 |

### 需要创建的CRUD类（7个）

1. ✅ **TechAssessmentCRUD** - 技术评估相关
2. ✅ **UserProfileCRUD** - 用户画像（已有user.py，需扩展）
3. ✅ **IntentAnalysisCRUD** - 意图分析
4. ✅ **ExecutionLogCRUD** - 执行日志
5. ✅ **ValidationCRUD** - 验证记录
6. ✅ **EditCRUD** - 编辑记录
7. ⚠️ **TavilyKeyCRUD** - Tavily API Key管理（特殊处理）

---

## 🎯 迁移策略

### 阶段1: 创建缺失的CRUD类（2小时）

**优先级**: P0

#### 1.1 创建 crud_tech_assessment.py

```python
# app/crud/crud_tech_assessment.py
from app.crud.base import BaseCRUD
from app.models.database import TechAssessment, TechAssessmentQuestion

class TechAssessmentCRUD(BaseCRUD[TechAssessment, dict, dict]):
    """技术评估CRUD"""
    pass

class TechAssessmentQuestionCRUD(BaseCRUD[TechAssessmentQuestion, dict, dict]):
    """技术评估问题CRUD"""
    pass
```

#### 1.2 扩展 crud_user.py

```python
# app/crud/crud_user.py 中添加
from app.models.database import UserProfile

class UserProfileCRUD(BaseCRUD[UserProfile, dict, dict]):
    """用户画像CRUD"""
    
    async def get_by_user_id(self, session, user_id: str):
        """根据用户ID获取画像"""
        # ...
```

#### 1.3 创建 crud_workflow.py（统一工作流相关）

```python
# app/crud/crud_workflow.py
from app.crud.base import BaseCRUD
from app.models.database import (
    IntentAnalysis,
    ExecutionLog,
    ValidationRecord,
    EditRecord,
)

class IntentAnalysisCRUD(BaseCRUD[IntentAnalysis, dict, dict]):
    """意图分析CRUD"""
    pass

class ExecutionLogCRUD(BaseCRUD[ExecutionLog, dict, dict]):
    """执行日志CRUD"""
    pass

class ValidationCRUD(BaseCRUD[ValidationRecord, dict, dict]):
    """验证记录CRUD"""
    pass

class EditCRUD(BaseCRUD[EditRecord, dict, dict]):
    """编辑记录CRUD"""
    pass
```

#### 1.4 Tavily Key 特殊处理

**方案A（推荐）**: 保留在 repositories/，因为涉及复杂的轮询和锁机制
**方案B**: 迁移到 crud_tavily_key.py，但保留特殊逻辑

暂定：**保留在原位**，但重命名为 `app/core/tavily_key_manager.py`

---

### 阶段2: 迁移Service层引用（3小时）

**优先级**: P1

#### 2.1 迁移 retry_service.py

```python
# ❌ 旧代码
from app.db.repositories.roadmap_repo import RoadmapRepository

class RetryService:
    def __init__(self):
        self.roadmap_repo = RoadmapRepository()

# ✅ 新代码
from app.crud.crud_roadmap import RoadmapCRUD
from app.models.database import RoadmapMetadata

class RetryService:
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
```

#### 2.2 迁移 tech_assessment_service.py

```python
# ❌ 旧代码
from app.db.repositories.tech_assessment_repo import TechAssessmentRepository
from app.db.repositories.user_profile_repo import UserProfileRepository

# ✅ 新代码
from app.crud.crud_tech_assessment import TechAssessmentCRUD
from app.crud.crud_user import UserProfileCRUD
```

#### 2.3 其他Service层文件（10个）

| 文件 | Repository | 替换为 CRUD |
|-----|-----------|------------|
| featured_service.py | RoadmapRepository | RoadmapCRUD |
| streaming_service.py | RoadmapRepository | RoadmapCRUD |
| edit_service.py | EditRepository, RoadmapRepository | EditCRUD, RoadmapCRUD |
| validation_service.py | ValidationRepository | ValidationCRUD |
| intent_service.py | RoadmapRepository | RoadmapCRUD |
| trace_service.py | RoadmapRepository | RoadmapCRUD |
| content_retry_service.py | ConceptMetadataRepository, RoadmapRepository | ConceptCRUD, RoadmapCRUD |
| concept_status_service.py | ConceptMetadataRepository | ConceptCRUD |

---

### 阶段3: 迁移Celery相关引用（2小时）

**优先级**: P1

#### 3.1 迁移 celery_session.py

这个文件包含**9个Repository导入**，是引用最密集的文件。

```python
# ❌ 旧代码（celery_session.py line 256-296）
from app.db.repositories.task_repo import TaskRepository
from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
from app.db.repositories.tutorial_repo import TutorialRepository
# ... 共9个

# ✅ 新代码
from app.crud.crud_task import TaskCRUD
from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_tutorial import TutorialCRUD
from app.crud.crud_resource import ResourceCRUD
from app.crud.crud_quiz import QuizCRUD
from app.crud.crud_workflow import (
    IntentAnalysisCRUD,
    ExecutionLogCRUD,
    ValidationCRUD,
    EditCRUD,
)
```

**关键变化**：
- Repository实例化：`TaskRepository(session)` → `TaskCRUD(RoadmapTask)`
- 方法调用保持兼容性

#### 3.2 迁移 content_generation_tasks.py

```python
# ❌ 旧代码
from app.db.repositories.concept_meta_repo import ConceptMetadataRepository

# ✅ 新代码
from app.crud.crud_concept import ConceptCRUD
```

#### 3.3 迁移 concept_generator.py

```python
# ❌ 旧代码
from app.db.repositories.roadmap_repo import RoadmapRepository

# ✅ 新代码
from app.crud.crud_roadmap import RoadmapCRUD
```

---

### 阶段4: 迁移其他模块（2小时）

#### 4.1 迁移 core/orchestrator/

| 文件 | Repository | 替换 |
|-----|-----------|------|
| workflow_brain.py | RoadmapRepository | RoadmapCRUD |
| node_runners/curriculum_runner.py | RoadmapRepository | RoadmapCRUD |
| node_runners/editor_runner.py | EditRepository | EditCRUD |
| node_runners/edit_plan_runner.py | EditRepository | EditCRUD |
| node_runners/review_runner.py | ValidationRepository | ValidationCRUD |
| unit_of_work.py | RoadmapRepository | RoadmapCRUD |

#### 4.2 迁移 api/v1/websocket.py

```python
# ❌ 旧代码
from app.db.repositories.roadmap_repo import RoadmapRepository

# ✅ 新代码
from app.crud.crud_roadmap import RoadmapCRUD
```

#### 4.3 迁移 tools/

| 文件 | Repository | 替换 |
|-----|-----------|------|
| web_search_router.py | TavilyKeyRepository | TavilyKeyCRUD（或保留） |
| mark_content_complete_tool.py | ConceptMetadataRepository | ConceptCRUD |

---

### 阶段5: 删除 repositories/ 目录（1小时）

**前提条件**：所有引用已迁移

#### 5.1 验证无残留引用

```bash
# 检查是否还有引用
grep -r "from app.db.repositories" app/ --include="*.py"

# 预期输出：无匹配（或仅 tavily_key_repo）
```

#### 5.2 删除目录

```bash
# 备份（可选）
mv app/db/repositories app/db/repositories.backup

# 确认测试通过后永久删除
rm -rf app/db/repositories.backup
```

#### 5.3 清理 db/__init__.py

```python
# 删除 Repository 导出
# from app.db.repositories import *  # ❌ 删除
```

---

## 📋 执行检查清单

### 阶段1: 创建CRUD ✅

- [ ] crud_tech_assessment.py (TechAssessmentCRUD, TechAssessmentQuestionCRUD)
- [ ] crud_user.py 扩展 (UserProfileCRUD)
- [ ] crud_workflow.py (IntentAnalysisCRUD, ExecutionLogCRUD, ValidationCRUD, EditCRUD)
- [ ] 决定 TavilyKeyCRUD 处理方案

### 阶段2: Service层迁移 ✅

- [ ] retry_service.py
- [ ] tech_assessment_service.py
- [ ] featured_service.py
- [ ] streaming_service.py
- [ ] edit_service.py
- [ ] validation_service.py
- [ ] intent_service.py
- [ ] trace_service.py
- [ ] content_retry_service.py
- [ ] concept_status_service.py

### 阶段3: Celery层迁移 ✅

- [ ] celery_session.py (9个Repository)
- [ ] content_generation_tasks.py
- [ ] concept_generator.py

### 阶段4: 其他模块迁移 ✅

- [ ] workflow_brain.py
- [ ] 6个 node_runners
- [ ] websocket.py
- [ ] 2个 tools

### 阶段5: 清理验收 ✅

- [ ] 无残留 `from app.db.repositories` 引用
- [ ] 删除 repositories/ 目录
- [ ] 清理 db/__init__.py
- [ ] 运行 Lint 检查
- [ ] 运行单元测试

---

## ⚠️ 风险与注意事项

### 风险1: 方法签名不兼容

**Repository** 和 **CRUD** 的方法签名可能不同：

```python
# Repository (旧)
await repo.get_by_roadmap_id(roadmap_id)

# CRUD (新)
await crud.get_by_roadmap_id(session, roadmap_id)
```

**缓解**: 逐文件迁移并运行Lint检查

### 风险2: celery_session.py 复杂度高

这个文件包含9个Repository，且是Celery任务的核心依赖。

**缓解**: 
- 先在测试环境验证
- 保留备份
- 逐个Repository迁移

### 风险3: Tavily Key 锁机制

`TavilyKeyRepository` 包含复杂的分布式锁和配额管理逻辑。

**建议**: 
- **方案1（推荐）**: 重命名为 `app/core/tavily_key_manager.py`，保留特殊逻辑
- **方案2**: 迁移到 CRUD，但保留锁逻辑

---

## 📈 预期成果

### 代码质量提升

| 指标 | 迁移前 | 迁移后 | 改善 |
|-----|-------|--------|------|
| repositories/ 文件数 | 20个 | **0个** | -100% |
| 重复代码层 | 2层（Repo+CRUD） | **1层（CRUD）** | -50% |
| 导入路径统一性 | 混乱 | **统一** | +100% |
| 架构违规文件数 | 31个 | **0个** | -100% |

### 时间估算

| 阶段 | 工作量 | 风险 |
|-----|--------|------|
| 阶段1: 创建CRUD | 2小时 | 低 |
| 阶段2: Service层 | 3小时 | 中 |
| 阶段3: Celery层 | 2小时 | 高 |
| 阶段4: 其他模块 | 2小时 | 中 |
| 阶段5: 清理验收 | 1小时 | 低 |
| **总计** | **10小时** | - |

---

**文档版本**: v1.0  
**创建日期**: 2026-01-07  
**预计完成**: 2026-01-08  
**负责人**: AI开发助手

