# WorkflowBrain 重构任务清单

> **关联文档**: [WORKFLOW_BRAIN_ARCHITECTURE_ANALYSIS.md](../architecture/WORKFLOW_BRAIN_ARCHITECTURE_ANALYSIS.md)  
> **创建日期**: 2024-12-13  
> **预计工期**: 8-13 天

---

## 📋 任务总览

| Phase | 任务数 | 预计时间 | 优先级 | 状态 |
|-------|--------|---------|-------|------|
| Phase 1: 基础设施 | 9 个任务 | 2-3 天 | 🔴 Critical | ⏳ Pending |
| Phase 2: Runner 迁移 | 23 个任务 | 3-5 天 | 🟠 High | ⏳ Pending |
| Phase 3: 事务增强 | 5 个任务 | 2-3 天 | 🟡 Medium | ⏳ Pending |
| Phase 4: 优化监控 | 6 个任务 | 1-2 天 | 🟢 Low | ⏳ Pending |
| **总计** | **43 个任务** | **8-13 天** | - | ⏳ Pending |

---

## 🎯 Phase 1: 基础设施搭建

**目标**: 创建 WorkflowBrain 核心组件，为后续 Runner 迁移打好基础

**关键里程碑**: WorkflowBrain 类可用，通过单元测试

### 任务列表

#### 1.1 创建 WorkflowBrain 核心类
- **ID**: `phase1-1-create-brain-class`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 创建 WorkflowBrain 主类，定义构造函数和依赖注入
- **依赖**: 无
- **验收标准**:
  - [ ] 文件创建完成
  - [ ] 类定义包含 `__init__` 方法
  - [ ] 正确注入 StateManager, NotificationService, ExecutionLogger
  - [ ] 添加中文文档注释

**代码骨架**:
```python
"""
工作流大脑 - 统一协调者

职责:
1. 状态管理 (State Management)
2. Checkpoint 协调 (Checkpoint Coordination)
3. 数据库操作 (DB Operations)
4. 日志管理 (Logging)
5. 通知发布 (Notification)
"""
import structlog
from contextlib import asynccontextmanager

logger = structlog.get_logger()

class WorkflowBrain:
    """工作流大脑"""
    
    def __init__(
        self,
        state_manager: StateManager,
        notification_service: NotificationService,
        execution_logger: ExecutionLogger,
    ):
        self.state_manager = state_manager
        self.notification_service = notification_service
        self.execution_logger = execution_logger
        self._current_context: NodeContext | None = None
```

---

#### 1.2 实现 NodeContext 数据类
- **ID**: `phase1-2-node-context`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 创建节点执行上下文数据类
- **依赖**: 1.1
- **验收标准**:
  - [ ] `@dataclass` 装饰器
  - [ ] 包含 node_name, task_id, roadmap_id, start_time, state_snapshot
  - [ ] 类型注解完整

**代码示例**:
```python
from dataclasses import dataclass

@dataclass
class NodeContext:
    """节点执行上下文"""
    node_name: str
    task_id: str
    roadmap_id: str | None
    start_time: float
    state_snapshot: dict
```

---

#### 1.3 实现 node_execution 上下文管理器
- **ID**: `phase1-3-context-manager`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 实现 async 上下文管理器，协调 before/after/error 处理
- **依赖**: 1.1, 1.2
- **验收标准**:
  - [ ] `@asynccontextmanager` 装饰器
  - [ ] 正确调用 `_before_node`
  - [ ] try/except/finally 结构完整
  - [ ] 异常时调用 `_on_error`

**代码框架**:
```python
@asynccontextmanager
async def node_execution(
    self,
    node_name: str,
    state: RoadmapState,
):
    """节点执行上下文管理器"""
    ctx = await self._before_node(node_name, state)
    try:
        yield ctx
        await self._after_node(ctx, state)
    except Exception as e:
        await self._on_error(ctx, state, e)
        raise
```

---

#### 1.4 实现 _before_node 方法
- **ID**: `phase1-4-before-node`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 节点执行前的统一处理（状态更新、日志、通知）
- **依赖**: 1.3
- **验收标准**:
  - [ ] 更新 live_step 缓存
  - [ ] 更新数据库 task 状态
  - [ ] 记录开始日志
  - [ ] 发布进度通知
  - [ ] 所有操作有错误处理

**实现要点**:
- 使用 `AsyncSessionLocal()` 创建数据库会话
- 使用 `RoadmapRepository` 进行数据库操作
- 调用 `execution_logger.log_workflow_start()`
- 调用 `notification_service.publish_progress()`

---

#### 1.5 实现 _after_node 方法
- **ID**: `phase1-5-after-node`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 节点执行后的统一处理（日志、通知、清理）
- **依赖**: 1.3
- **验收标准**:
  - [ ] 计算执行时长
  - [ ] 记录完成日志
  - [ ] 发布完成通知
  - [ ] 清理 `_current_context`

---

#### 1.6 实现 _on_error 方法
- **ID**: `phase1-6-on-error`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 节点执行失败的统一处理
- **依赖**: 1.3
- **验收标准**:
  - [ ] 更新数据库状态为 "failed"
  - [ ] 记录错误日志（包含堆栈信息）
  - [ ] 发布错误通知
  - [ ] 清理 `_current_context`

---

#### 1.7 实现特定节点的数据保存方法
- **ID**: `phase1-7-save-methods`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 实现 `save_intent_analysis`, `save_roadmap_framework`, `save_content_results`
- **依赖**: 1.1
- **验收标准**:
  - [ ] `save_intent_analysis()` - 保存需求分析结果
  - [ ] `save_roadmap_framework()` - 保存路线图框架
  - [ ] `save_content_results()` - 批量保存内容生成结果
  - [ ] 所有方法使用统一事务
  - [ ] 添加详细日志

**关键点**: 在同一个事务中执行所有数据库操作

---

#### 1.8 添加 WorkflowBrain 单元测试
- **ID**: `phase1-8-unit-tests`
- **文件**: `backend/tests/unit/test_workflow_brain.py`
- **描述**: 完整的单元测试覆盖
- **依赖**: 1.1-1.7
- **验收标准**:
  - [ ] 测试覆盖率 > 80%
  - [ ] 测试 `node_execution` 成功场景
  - [ ] 测试 `node_execution` 异常场景
  - [ ] 测试数据保存方法
  - [ ] 使用 mock 隔离外部依赖
  - [ ] 所有测试通过

**测试用例**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_node_execution_success():
    """测试节点执行成功场景"""
    brain = WorkflowBrain(...)
    
    async with brain.node_execution("test_node", mock_state):
        # 验证 before_node 被调用
        pass
    
    # 验证 after_node 被调用
    # 验证日志和通知

@pytest.mark.asyncio
async def test_node_execution_error():
    """测试节点执行异常场景"""
    brain = WorkflowBrain(...)
    
    with pytest.raises(ValueError):
        async with brain.node_execution("test_node", mock_state):
            raise ValueError("Test error")
    
    # 验证 on_error 被调用
    # 验证错误日志和通知
```

---

#### 1.9 集成 WorkflowBrain 到 orchestrator_factory
- **ID**: `phase1-9-integration`
- **文件**: `backend/app/core/orchestrator_factory.py`
- **描述**: 在工厂方法中创建和注入 WorkflowBrain
- **依赖**: 1.1-1.8
- **验收标准**:
  - [ ] 在 `create_orchestrator()` 中实例化 WorkflowBrain
  - [ ] 正确注入依赖
  - [ ] 传递给所有 Runner
  - [ ] 不影响现有功能

---

## 🔄 Phase 2: Runner 迁移

**目标**: 逐一重构每个 Runner，使用 WorkflowBrain 统一管理状态

**迁移顺序**: ValidationRunner → EditorRunner → ReviewRunner → IntentAnalysisRunner → CurriculumDesignRunner → ContentRunner

**通用迁移步骤模板**:
1. 创建新版 Runner（使用 brain）
2. 添加迁移测试
3. 并行运行新旧版本对比结果
4. 切换到新版本
5. 删除旧代码

---

### 2.1 迁移 ValidationRunner（最简单）

#### 2.1.1 创建新版 ValidationRunner
- **ID**: `phase2-1-1-validation-new`
- **文件**: `backend/app/core/orchestrator/node_runners/validation_runner.py`
- **依赖**: Phase 1 全部完成
- **验收标准**:
  - [ ] 删除 `_update_task_status()` 方法
  - [ ] 使用 `brain.node_execution()` 包装执行逻辑
  - [ ] 只保留 Agent 调用逻辑
  - [ ] 代码行数减少 > 60%

**重构对比**:
```python
# 重构前
async def run(self, state: RoadmapState) -> dict:
    await self._update_task_status(...)  # ← 删除
    await execution_logger.log_workflow_start(...)  # ← 删除
    await notification_service.publish_progress(...)  # ← 删除
    
    result = await agent.execute(...)
    
    await execution_logger.log_workflow_complete(...)  # ← 删除
    await notification_service.publish_progress(...)  # ← 删除
    return ...

# 重构后
async def run(self, state: RoadmapState) -> dict:
    async with self.brain.node_execution("structure_validation", state):
        result = await agent.execute(...)
        return {"validation_result": result, ...}
```

---

#### 2.1.2 添加 ValidationRunner 迁移测试
- **ID**: `phase2-1-2-validation-test`
- **文件**: `backend/tests/integration/test_validation_runner_migration.py`
- **依赖**: 2.1.1
- **验收标准**:
  - [ ] 对比新旧版本输出一致性
  - [ ] 验证数据库状态正确
  - [ ] 验证日志完整性
  - [ ] 验证通知发送

---

#### 2.1.3-2.1.5 并行对比、切换、清理
- **ID**: `phase2-1-3-validation-compare`, `phase2-1-4-validation-switch`, `phase2-1-5-validation-cleanup`
- **依赖**: 2.1.2
- **验收标准**:
  - [ ] 新版本通过所有测试
  - [ ] 性能无回退
  - [ ] 旧代码完全移除

---

### 2.2 迁移 EditorRunner

#### 2.2.1 创建新版 EditorRunner
- **ID**: `phase2-2-1-editor-new`
- **文件**: `backend/app/core/orchestrator/node_runners/editor_runner.py`
- **依赖**: 2.1 全部完成
- **验收标准**:
  - [ ] 删除 `_update_task_status()` 和 `_update_roadmap_framework()`
  - [ ] 使用 `brain.node_execution()`
  - [ ] 使用 `brain.save_roadmap_framework()` 保存框架
  - [ ] 代码简化

---

### 2.3 迁移 ReviewRunner

#### 2.3.1 创建新版 ReviewRunner
- **ID**: `phase2-3-1-review-new`
- **文件**: `backend/app/core/orchestrator/node_runners/review_runner.py`
- **依赖**: 2.2 全部完成
- **特别注意**: 保留 `interrupt()` 逻辑，只移除数据库操作

---

### 2.4 迁移 IntentAnalysisRunner

#### 2.4.1 创建新版 IntentAnalysisRunner
- **ID**: `phase2-4-1-intent-new`
- **文件**: `backend/app/core/orchestrator/node_runners/intent_runner.py`
- **依赖**: 2.3 全部完成

#### 2.4.2 实现 brain.ensure_unique_roadmap_id()
- **ID**: `phase2-4-2-intent-roadmap-id`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 将 roadmap_id 唯一性验证逻辑移到 brain
- **验收标准**:
  - [ ] 方法实现完整
  - [ ] 事务处理正确
  - [ ] 添加单元测试

---

### 2.5 迁移 CurriculumDesignRunner

#### 2.5.1 创建新版 CurriculumDesignRunner
- **ID**: `phase2-5-1-curriculum-new`
- **文件**: `backend/app/core/orchestrator/node_runners/curriculum_runner.py`
- **依赖**: 2.4 全部完成
- **验收标准**:
  - [ ] 删除 `_update_task_status()` 和 `_save_roadmap_framework()`
  - [ ] 使用 `brain.save_roadmap_framework()`

---

### 2.6 迁移 ContentRunner（最复杂）

#### 2.6.1 创建新版 ContentRunner
- **ID**: `phase2-6-1-content-new`
- **文件**: `backend/app/core/orchestrator/node_runners/content_runner.py`
- **依赖**: 2.5 全部完成

#### 2.6.2 实现 brain.save_content_results()
- **ID**: `phase2-6-2-content-batch`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 批量保存教程、资源、测验元数据
- **验收标准**:
  - [ ] 批量保存逻辑正确
  - [ ] 使用统一事务
  - [ ] 处理部分失败场景

---

#### 2.7 端到端验证
- **ID**: `phase2-7-e2e-validation`
- **文件**: `backend/tests/e2e/test_all_runners_migration.py`
- **依赖**: Phase 2 所有迁移完成
- **验收标准**:
  - [ ] 完整工作流端到端测试通过
  - [ ] 所有 Runner 正常工作
  - [ ] 数据库状态一致性验证
  - [ ] 性能对比报告

---

## 🔐 Phase 3: 事务增强

**目标**: 添加完整的事务支持，确保原子性和一致性

### 任务列表

#### 3.1 实现 Unit of Work 模式
- **ID**: `phase3-1-uow-pattern`
- **文件**: `backend/app/core/orchestrator/unit_of_work.py`
- **描述**: 实现 UoW 模式，统一管理事务边界
- **依赖**: Phase 2 完成
- **验收标准**:
  - [ ] `UnitOfWork` 上下文管理器实现
  - [ ] 支持嵌套事务
  - [ ] 自动 commit/rollback
  - [ ] 集成到 WorkflowBrain

**代码框架**:
```python
class UnitOfWork:
    """工作单元模式"""
    
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        await self.session.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
```

---

#### 3.2 添加 PostgreSQL savepoint 支持
- **ID**: `phase3-2-savepoint`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 在关键操作前设置 savepoint
- **验收标准**:
  - [ ] 在每个 Runner 执行前设置 savepoint
  - [ ] 异常时回滚到 savepoint
  - [ ] 不影响主事务

**使用示例**:
```python
async with session.begin_nested():  # savepoint
    await repo.update_task_status(...)
```

---

#### 3.3 实现智能回滚策略
- **ID**: `phase3-3-rollback`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 根据异常类型决定回滚范围
- **验收标准**:
  - [ ] 网络错误 → 回滚当前节点
  - [ ] 数据验证错误 → 回滚当前节点
  - [ ] 系统错误 → 回滚整个工作流
  - [ ] 添加回滚日志

---

#### 3.4 添加事务超时处理
- **ID**: `phase3-4-timeout`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 防止长时间事务阻塞
- **验收标准**:
  - [ ] 设置合理的事务超时（如 30s）
  - [ ] 超时后自动回滚
  - [ ] 记录超时日志
  - [ ] 发送超时告警

---

#### 3.5 添加事务场景测试
- **ID**: `phase3-5-transaction-test`
- **文件**: `backend/tests/integration/test_transaction_scenarios.py`
- **描述**: 完整测试事务边界和回滚机制
- **依赖**: 3.1-3.4
- **验收标准**:
  - [ ] 测试正常提交场景
  - [ ] 测试异常回滚场景
  - [ ] 测试 savepoint 回滚
  - [ ] 测试超时场景
  - [ ] 事务回滚成功率 100%

---

## 📊 Phase 4: 优化与监控

**目标**: 性能优化、监控指标、文档完善

### 任务列表

#### 4.1 批量数据库操作优化
- **ID**: `phase4-1-batch-optimize`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 优化批量插入/更新操作
- **依赖**: Phase 3 完成
- **验收标准**:
  - [ ] 使用 `bulk_insert_mappings` 批量插入
  - [ ] 减少数据库往返次数
  - [ ] 性能提升 > 30%

---

#### 4.2 添加性能监控指标
- **ID**: `phase4-2-metrics`
- **文件**: `backend/app/core/orchestrator/workflow_brain.py`
- **描述**: 添加 Prometheus 指标
- **验收标准**:
  - [ ] 节点执行时长指标
  - [ ] 数据库操作时长指标
  - [ ] 事务提交/回滚计数
  - [ ] 错误率指标
  - [ ] Grafana 仪表板

---

#### 4.3 完善错误恢复机制
- **ID**: `phase4-3-recovery`
- **文件**: `backend/app/services/task_recovery_service.py`
- **描述**: 增强 TaskRecoveryService，利用 WorkflowBrain 的事务边界
- **验收标准**:
  - [ ] 自动检测不一致状态
  - [ ] 智能恢复建议
  - [ ] 错误恢复成功率 > 95%

---

#### 4.4 实现状态一致性检查工具
- **ID**: `phase4-4-consistency-check`
- **文件**: `backend/scripts/check_state_consistency.py`
- **描述**: 脚本检查 LangGraph checkpoint 与数据库一致性
- **验收标准**:
  - [ ] 检查所有活跃任务
  - [ ] 输出不一致报告
  - [ ] 提供修复建议
  - [ ] 支持定时运行

---

#### 4.5 更新架构文档和开发指南
- **ID**: `phase4-5-documentation`
- **文件**: `doc/architecture/WORKFLOW_BRAIN_GUIDE.md`
- **描述**: 完整的开发者文档
- **验收标准**:
  - [ ] 架构设计说明
  - [ ] API 使用指南
  - [ ] 最佳实践
  - [ ] 故障排查手册
  - [ ] 迁移完整记录

---

#### 4.6 性能基准测试与对比报告
- **ID**: `phase4-6-benchmarks`
- **文件**: `doc/implementation/WORKFLOW_BRAIN_PERFORMANCE_REPORT.md`
- **描述**: 重构前后性能对比
- **验收标准**:
  - [ ] 执行时长对比
  - [ ] 数据库查询次数对比
  - [ ] 内存使用对比
  - [ ] 可靠性指标对比
  - [ ] 代码复杂度对比

---

## 🎯 成功指标（KPI）

### 代码质量

- ✅ 代码重复率下降 > 60%
- ✅ 单个 Runner 代码行数 < 100 行
- ✅ 测试覆盖率 > 80%

### 可靠性

- ✅ 事务回滚成功率 = 100%
- ✅ 状态一致性检查通过率 = 100%
- ✅ 错误恢复成功率 > 95%

### 可维护性

- ✅ 新增 Runner 开发时间 < 2 小时
- ✅ Bug 修复平均时间下降 > 50%

---

## 📅 里程碑与时间表

```
Week 1:
├─ Day 1-3: Phase 1 完成 (WorkflowBrain 核心)
│  ├─ Day 1: 1.1-1.3 (核心类和上下文管理器)
│  ├─ Day 2: 1.4-1.7 (before/after/error + 保存方法)
│  └─ Day 3: 1.8-1.9 (测试 + 集成)
│
└─ Day 4-7: Phase 2 开始 (Runner 迁移)
   ├─ Day 4: ValidationRunner + EditorRunner
   ├─ Day 5: ReviewRunner + IntentAnalysisRunner
   ├─ Day 6: CurriculumDesignRunner
   └─ Day 7: ContentRunner (复杂)

Week 2:
├─ Day 8-10: Phase 3 完成 (事务增强)
│  ├─ Day 8: UoW 模式 + savepoint
│  ├─ Day 9: 回滚策略 + 超时处理
│  └─ Day 10: 事务测试
│
└─ Day 11-13: Phase 4 完成 (优化监控)
   ├─ Day 11: 批量优化 + 性能指标
   ├─ Day 12: 错误恢复 + 一致性检查
   └─ Day 13: 文档 + 性能报告
```

---

## 🚨 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|-----|------|---------|--------|
| LangGraph checkpoint 不兼容 | 高 | 低 | 深入研究 LangGraph 源码 | 架构师 |
| 性能回归 | 中 | 低 | 每个阶段性能基准测试 | 开发者 |
| 数据迁移问题 | 高 | 中 | 提前备份，灰度发布 | DBA |
| 工期延长 | 中 | 中 | 渐进式实施，可随时暂停 | PM |

---

## 📝 注意事项

1. **每个 Phase 完成后必须通过测试才能进入下一阶段**
2. **保持向后兼容，确保可以随时回滚**
3. **定期更新 TODO 列表状态**
4. **每日同步进度，及时识别风险**
5. **遇到阻塞问题立即升级**

---

## 🔗 相关文档

- [架构分析文档](../architecture/WORKFLOW_BRAIN_ARCHITECTURE_ANALYSIS.md)
- [Orchestrator 架构文档](../architecture/orchestrator_architecture.md)
- [错误处理文档](../implementation/error_handling.md)

---

*任务清单创建于 2024-12-13，持续更新中...*

