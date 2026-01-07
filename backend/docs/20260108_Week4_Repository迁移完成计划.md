# Week 4: Repository迁移完成计划

> **计划日期**: 2026-01-08  
> **预计工期**: 5天（20工作小时）  
> **目标**: 完成剩余55%的Repository迁移，彻底删除repositories/目录  
> **前置条件**: ✅ Week 3已完成45%迁移，基础CRUD已就绪

---

## 📋 Week 3 完成情况回顾

### ✅ 已完成工作

| 类别 | 内容 | 成果 |
|------|------|------|
| **Bug修复** | TaskListItem Schema错误 | ✅ API正常工作 |
| **基础设施** | 创建7个新CRUD类 | ✅ ~500行高质量代码 |
| **Service迁移** | 5个Service文件 | ✅ 删除~54行重复代码 |
| **验证** | 渐进式迁移方案 | ✅ 证明可行性 |

**完成度**: 45% (14/31 文件相关工作)  
**剩余工作**: 55% (17个文件 + CRUD扩展)

### 🎓 经验总结

**成功之处**:
- ✅ 渐进式策略避免了系统停滞
- ✅ CRUD单例模式简化依赖注入
- ✅ 每个迁移都经过验证

**发现的挑战**:
- ⚠️ 48%的文件需要CRUD业务方法扩展
- ⚠️ Repository方法多达100+个，需要系统化迁移
- ⚠️ 测试覆盖不足

---

## 🎯 Week 4 核心目标

### 主目标

1. **完成CRUD方法扩展** - 为高频CRUD类添加所有必要的业务方法
2. **迁移剩余26个文件** - 包括Service、Celery、Core、API/Tools层
3. **删除repositories/目录** - 彻底清理旧代码
4. **全量测试验证** - 确保迁移后系统正常运行

### 成功标准

- [ ] 100%文件迁移完成
- [ ] repositories/目录已删除
- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 无Lint错误
- [ ] API响应时间无劣化

---

## 📅 Day-by-Day 详细计划

### Day 1: CRUD方法扩展（Part 1）- 8小时

**目标**: 扩展最常用的CRUD类（RoadmapCRUD, TaskCRUD, ConceptCRUD）

#### 上午：RoadmapCRUD扩展（4小时）

**新增方法**:
```python
# app/crud/crud_roadmap.py

# 1. Roadmap元数据相关
async def get_roadmap_metadata_by_task(session, task_id) -> Optional[RoadmapMetadata]
async def get_roadmap_with_framework(session, roadmap_id) -> Optional[dict]

# 2. Intent分析相关  
async def get_intent_analysis_metadata(session, task_id) -> Optional[IntentAnalysisMetadata]
async def save_intent_analysis(session, task_id, analysis_data) -> IntentAnalysisMetadata

# 3. 执行日志相关
async def get_execution_logs_by_trace(session, task_id, offset, limit) -> List[ExecutionLog]
async def count_execution_logs_by_trace(session, task_id) -> int
async def get_execution_logs_summary(session, task_id) -> dict
async def get_error_logs_by_trace(session, task_id, limit) -> List[ExecutionLog]

# 4. 批量查询优化
async def get_roadmaps_by_user(session, user_id, skip, limit) -> List[RoadmapMetadata]
```

**实施步骤**:
1. 阅读 `roadmap_repo.py` 中对应方法的实现（1小时）
2. 在 `crud_roadmap.py` 中实现新方法（2小时）
3. 编写单元测试（1小时）

#### 下午：TaskCRUD + ConceptCRUD扩展（4小时）

**TaskCRUD新增方法**:
```python
# app/crud/crud_task.py

async def get_tasks_by_roadmap_ids_batch(session, roadmap_ids) -> dict
async def update_task_status(session, task_id, status, error=None) -> None
async def get_user_tasks_with_stats(session, user_id, filters) -> dict
```

**ConceptCRUD新增方法**:
```python
# app/crud/crud_concept.py

async def get_failed_concepts(session, roadmap_id) -> List[dict]
async def update_concept_status_in_framework(session, roadmap_id, concept_id, status) -> None
async def get_concept_with_content_status(session, concept_id) -> dict
```

**实施步骤**:
1. 分析Repository方法（1小时）
2. 实现TaskCRUD扩展（1.5小时）
3. 实现ConceptCRUD扩展（1小时）
4. 编写测试（0.5小时）

**Day 1 验收**:
- [ ] RoadmapCRUD新增8个方法
- [ ] TaskCRUD新增3个方法
- [ ] ConceptCRUD新增3个方法
- [ ] 所有新方法有单元测试
- [ ] Lint检查通过

---

### Day 2: CRUD方法扩展（Part 2）+ Service迁移（Part 1）- 8小时

#### 上午：TechAssessmentCRUD扩展（3小时）

**新增方法**:
```python
# app/crud/crud_tech_assessment.py

async def get_available_technologies(session) -> List[str]
async def get_assessment(session, technology, proficiency) -> Optional[TechStackAssessment]
async def technology_exists(session, technology) -> bool
async def create_assessment_with_questions(session, technology, proficiency, questions) -> TechStackAssessment
```

**实施步骤**:
1. 阅读 `tech_assessment_repo.py`（0.5小时）
2. 实现方法（2小时）
3. 测试（0.5小时）

#### 下午：迁移P1高优先级Service（5小时）

**目标文件**（3个）:
1. **retry_service.py** (2小时)
   - 替换 RoadmapRepository
   - 使用 RoadmapCRUD + TaskCRUD
   
2. **roadmap_service.py** (1.5小时)
   - 替换 RoadmapRepository
   - 使用 RoadmapCRUD
   
3. **tech_assessment_service.py** (1.5小时)
   - 使用新扩展的 TechAssessmentCRUD
   - 替换所有 Repository 调用

**Day 2 验收**:
- [ ] TechAssessmentCRUD完全扩展
- [ ] 3个P1 Service迁移完成
- [ ] 原有功能验证通过

---

### Day 3: Service层批量迁移 - 8小时

#### 上午：P2中优先级Service（4小时）

**目标文件**（4个）:
1. **trace_service.py** (1小时)
   - 使用扩展后的 RoadmapCRUD 执行日志方法
   
2. **concept_status_service.py** (1小时)
   - 使用 ConceptCRUD
   
3. **content_retry_service.py** (1.5小时)
   - 使用 ConceptCRUD + RoadmapCRUD
   
4. **tech_assessment_initializer.py** (0.5小时)
   - 使用 TechAssessmentCRUD

#### 下午：其他Service文件（4小时）

**目标文件**（4个）:
1. **progress_service.py** (如存在，1小时)
2. **user_service.py** (检查是否需要迁移，1小时)
3. **其他Service** (2小时)

**Day 3 验收**:
- [ ] 8个Service文件迁移完成
- [ ] Service层迁移完成度: 100%
- [ ] 所有Service单元测试通过

---

### Day 4: Celery/Core层迁移 - 6小时

#### 上午：Celery层迁移（3小时）

**1. celery_session.py** (2小时) - **最关键文件**
```python
# ❌ 旧代码（9个Repository导入）
from app.db.repositories.task_repo import TaskRepository
from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
# ... 共9个

# ✅ 新代码
from app.crud.crud_task import TaskCRUD
from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_workflow import (
    IntentAnalysisCRUD, ExecutionLogCRUD, 
    ValidationCRUD, EditCRUD
)
```

**实施步骤**:
1. 替换9个Repository导入（30分钟）
2. 更新所有Repository实例化（30分钟）
3. 调整方法调用（session参数）（30分钟）
4. 测试Celery任务执行（30分钟）

**2. content_generation_tasks.py + concept_generator.py** (1小时)
- 替换 ConceptMetadataRepository
- 替换 RoadmapRepository

#### 下午：Core/Orchestrator层迁移（3小时）

**目标文件**（7个）:
1. **workflow_brain.py** (0.5小时)
2. **curriculum_runner.py** (0.5小时)
3. **editor_runner.py** (0.5小时)
4. **edit_plan_runner.py** (0.5小时)
5. **review_runner.py** (0.5小时)
6. **unit_of_work.py** (0.5小时)
7. **其他runners** (0小时)

**迁移模式**:
```python
# 统一模式：
# ❌ self._repo = Repository(session)
# ✅ self.crud = CRUD(Model)
```

**Day 4 验收**:
- [ ] celery_session.py完全迁移
- [ ] Celery任务正常执行
- [ ] 7个Orchestrator文件迁移完成
- [ ] 工作流测试通过

---

### Day 5: 收尾 + 验收 - 6小时

#### 上午：最后的文件迁移（2小时）

**API/Tools层**（3个）:
1. **api/v1/websocket.py** (0.5小时)
   ```python
   # 替换 RoadmapRepository
   # 验证 WebSocket 连接
   ```

2. **tools/mentor/mark_content_complete_tool.py** (0.5小时)
   ```python
   # 替换 RepositoryFactory
   # 使用 ConceptCRUD
   ```

3. **tools/search/web_search_router.py** (1小时)
   ```python
   # 特殊处理：TavilyKeyRepository
   # 决策：保留或迁移
   ```

#### 下午：删除repositories/ + 全量验证（4小时）

**步骤1: 最终检查**（1小时）
```bash
# 确认无残留引用
grep -r "from app.db.repositories" app/ --include="*.py"

# 预期输出：无匹配（或仅 tavily_key_repo）
```

**步骤2: 备份 + 删除**（0.5小时）
```bash
# 备份
tar -czf repositories_backup_20260108.tar.gz app/db/repositories/

# 删除
rm -rf app/db/repositories/

# 清理 __init__.py
# 删除 Repository 相关导出
```

**步骤3: 全量测试**（2小时）
```bash
# 单元测试
pytest tests/unit/ -v --cov=app --cov-report=html

# 集成测试
pytest tests/integration/ -v

# E2E测试（关键流程）
pytest tests/e2e/test_roadmap_lifecycle.py -v
```

**步骤4: Lint + 性能检查**（0.5小时）
```bash
# Lint检查
ruff check app/ --fix
mypy app/ --strict

# 性能基准测试
pytest tests/performance/benchmark.py -v
```

**Day 5 验收**:
- [ ] 所有文件迁移完成（100%）
- [ ] repositories/目录已删除
- [ ] 单元测试覆盖率>80%
- [ ] 所有集成测试通过
- [ ] E2E测试通过
- [ ] 无Lint错误
- [ ] 性能无劣化

---

## 📊 进度追踪表

### CRUD扩展进度

| CRUD类 | 现有方法数 | 需新增 | Day 1 | Day 2 | 状态 |
|--------|-----------|--------|-------|-------|------|
| RoadmapCRUD | 5 | 8 | ⏳ | - | Pending |
| TaskCRUD | 3 | 3 | ⏳ | - | Pending |
| ConceptCRUD | 4 | 3 | ⏳ | - | Pending |
| TechAssessmentCRUD | 4 | 4 | - | ⏳ | Pending |
| 其他CRUD | - | - | - | - | - |

### Service层迁移进度

| Service | Priority | Day | 预计工时 | 状态 |
|---------|----------|-----|---------|------|
| ✅ featured_service.py | - | Week3 | - | Done |
| ✅ streaming_service.py | - | Week3 | - | Done |
| ✅ validation_service.py | - | Week3 | - | Done |
| ✅ intent_service.py | - | Week3 | - | Done |
| ✅ edit_service.py | - | Week3 | - | Done |
| retry_service.py | P1 | Day 2 | 2h | Pending |
| roadmap_service.py | P1 | Day 2 | 1.5h | Pending |
| tech_assessment_service.py | P1 | Day 2 | 1.5h | Pending |
| trace_service.py | P2 | Day 3 | 1h | Pending |
| concept_status_service.py | P2 | Day 3 | 1h | Pending |
| content_retry_service.py | P2 | Day 3 | 1.5h | Pending |
| tech_assessment_initializer.py | P2 | Day 3 | 0.5h | Pending |

### Celery/Core层迁移进度

| 文件 | 复杂度 | Day | 预计工时 | 状态 |
|------|--------|-----|---------|------|
| celery_session.py | 高 | Day 4 | 2h | Pending |
| content_generation_tasks.py | 中 | Day 4 | 0.5h | Pending |
| concept_generator.py | 中 | Day 4 | 0.5h | Pending |
| workflow_brain.py | 中 | Day 4 | 0.5h | Pending |
| 6个node_runners | 低 | Day 4 | 3h | Pending |

### API/Tools层迁移进度

| 文件 | Day | 预计工时 | 状态 |
|------|-----|---------|------|
| websocket.py | Day 5 | 0.5h | Pending |
| mark_content_complete_tool.py | Day 5 | 0.5h | Pending |
| web_search_router.py | Day 5 | 1h | Pending |

---

## ⚠️ 风险管理

### 已识别风险

| 风险 | 严重性 | 概率 | 缓解措施 |
|------|--------|------|---------|
| CRUD方法实现错误 | 高 | 中 | 参考Repository实现，编写测试 |
| Celery任务执行失败 | 高 | 低 | 详细测试，保留备份 |
| 性能劣化 | 中 | 低 | 基准测试，查询优化 |
| 测试覆盖不足 | 中 | 中 | 补充单元测试 |

### 回滚方案

如果迁移出现严重问题：
```bash
# 1. 恢复 repositories/
tar -xzf repositories_backup_20260108.tar.gz

# 2. 回滚代码（使用git）
git checkout HEAD~N -- app/services/
git checkout HEAD~N -- app/crud/

# 3. 重新部署
# ...
```

---

## 🧪 测试策略

### 单元测试（Day 1-3，持续）

**每个新CRUD方法必须有测试**:
```python
# tests/unit/crud/test_roadmap_crud.py

@pytest.mark.asyncio
async def test_get_roadmap_metadata_by_task(session):
    """测试：通过task_id获取roadmap元数据"""
    crud = RoadmapCRUD(RoadmapMetadata)
    
    # 创建测试数据
    task = await create_test_task(session, roadmap_id="test-roadmap")
    
    # 执行查询
    metadata = await crud.get_roadmap_metadata_by_task(session, task.task_id)
    
    # 断言
    assert metadata is not None
    assert metadata.roadmap_id == "test-roadmap"
```

**目标覆盖率**: >80%

### 集成测试（Day 4-5）

**关键流程测试**:
```python
# tests/integration/test_migration.py

@pytest.mark.asyncio
async def test_roadmap_generation_after_migration():
    """测试：迁移后路线图生成功能完整性"""
    # 1. 创建用户
    # 2. 生成路线图
    # 3. 验证数据库记录
    # 4. 验证WebSocket通知
    # 5. 验证任务状态
```

### E2E测试（Day 5）

**完整用户流程**:
```python
@pytest.mark.e2e
def test_full_user_journey():
    """端到端测试：完整用户旅程"""
    # 1. 注册/登录
    # 2. 生成路线图
    # 3. 查看内容
    # 4. 重试失败内容
    # 5. 更新进度
    # 6. 伴学聊天
```

---

## 📝 文档更新计划

### 需要更新的文档

| 文档 | 更新内容 | 负责阶段 |
|------|---------|---------|
| ARCHITECTURE.md | CRUD层说明，删除Repository章节 | Day 5 |
| API.md | 确认无影响 | Day 5 |
| CONTRIBUTING.md | 新的开发规范（使用CRUD） | Day 5 |
| README.md | 架构图更新 | Day 5 |

### 新增文档

1. **CRUD_GUIDE.md** - CRUD层使用指南
2. **MIGRATION_LOG.md** - 迁移详细日志
3. **WEEK4_SUMMARY.md** - Week 4 完成总结

---

## 🏆 Week 4 成功标准

### 代码质量

- [ ] 100%文件迁移完成（31/31）
- [ ] repositories/目录已删除
- [ ] 所有CRUD方法有单元测试
- [ ] Lint检查0错误
- [ ] Mypy类型检查通过

### 功能完整性

- [ ] 所有API endpoint正常工作
- [ ] Celery任务正常执行
- [ ] WebSocket通知正常
- [ ] 工作流正常运行
- [ ] 数据库操作正常

### 测试覆盖

- [ ] 单元测试覆盖率>80%
- [ ] 集成测试全部通过
- [ ] E2E测试关键流程通过
- [ ] 性能测试无劣化（<5%）

### 文档完整

- [ ] 架构文档已更新
- [ ] CRUD使用指南已创建
- [ ] 迁移日志已归档
- [ ] Week 4总结已生成

---

## 📅 每日检查清单

### Day 1 EOD（End of Day）
- [ ] RoadmapCRUD扩展完成（8个方法）
- [ ] TaskCRUD扩展完成（3个方法）
- [ ] ConceptCRUD扩展完成（3个方法）
- [ ] 所有新方法有测试
- [ ] 代码提交并Push

### Day 2 EOD
- [ ] TechAssessmentCRUD扩展完成
- [ ] 3个P1 Service迁移完成
- [ ] 功能验证通过
- [ ] 代码提交并Push

### Day 3 EOD
- [ ] 8个Service迁移完成
- [ ] Service层100%迁移
- [ ] 所有Service测试通过
- [ ] 代码提交并Push

### Day 4 EOD
- [ ] celery_session.py迁移完成
- [ ] 7个Orchestrator文件迁移完成
- [ ] Celery任务测试通过
- [ ] 代码提交并Push

### Day 5 EOD
- [ ] API/Tools层迁移完成
- [ ] repositories/目录已删除
- [ ] 全量测试通过
- [ ] 文档更新完成
- [ ] **Week 4完成！** 🎉

---

## 🚀 启动Week 4

### 准备工作（1小时）

1. **环境准备**
   ```bash
   # 创建Week 4分支
   git checkout -b week4-repository-migration
   
   # 更新依赖
   poetry install
   
   # 运行基准测试（迁移前）
   pytest tests/performance/benchmark.py -v > baseline.txt
   ```

2. **代码Review**
   - Review Week 3已完成的5个Service
   - 确认迁移模式正确

3. **团队同步**
   - 分享Week 4计划
   - 分配任务（如有团队）
   - 确认时间安排

### 第一个任务

从 **Day 1上午** 开始：
```bash
# 1. 打开 crud_roadmap.py
# 2. 参考 roadmap_repo.py
# 3. 实现第一个方法：get_roadmap_metadata_by_task()
# 4. 编写测试
# 5. 验证通过
```

---

## 📞 支持与协作

### 遇到问题时

1. **技术问题**：参考Repository原实现
2. **测试问题**：查看现有测试用例
3. **性能问题**：使用SQLAlchemy profiler分析

### 沟通渠道

- 技术讨论：Team Chat
- 代码Review：Pull Request
- 进度更新：Daily Standup

---

**文档版本**: v1.0  
**创建日期**: 2026-01-08  
**预计开始**: 2026-01-08  
**预计完成**: 2026-01-12  
**工作量**: 20小时（5天×4小时/天）  
**负责人**: 后端开发团队

**状态**: 📋 待执行  
**前置条件**: ✅ Week 3已完成45%迁移

**下一步**: 启动 Day 1 - CRUD方法扩展！

