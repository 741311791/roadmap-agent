# task_id 统一化重构计划（激进版）

## 🎯 目标

**破坏性变更**：直接将系统中的 `trace_id` 替换为 `task_id`，遵循 OneId 建模原则。同时清空所有测试脏数据，重新开始。

## 🔥 重构原则

1. **不考虑向后兼容** - 直接修改，不保留过渡期
2. **清空所有数据** - 删除测试期间的脏数据
3. **一次性完成** - 避免渐进式迁移的复杂性
4. **快速验证** - 重构后立即进行全面测试

## 📊 现状分析

### 当前问题

1. **同一概念，多个名称**：
   - `trace_id`：工作流追踪ID
   - `task_id`：任务业务ID  
   - `thread_id`：LangGraph线程ID
   - **实际值：完全相同的 UUID**

2. **影响范围**：
   - `task_id` 出现 337 次
   - `trace_id` 出现 282 次
   - 显式转换 `task_id=trace_id` 67 次

3. **违反原则**：
   - ❌ OneId 原则：一个概念应该只有一个标识符
   - ❌ 最小惊讶原则：开发者需要记住隐含的等价关系
   - ❌ DRY 原则：重复的概念定义

### 为什么选择 task_id？

| 标准 | task_id | trace_id |
|------|---------|----------|
| **业务语义** | ✅ 清晰（任务管理） | ⚠️ 技术性强（追踪） |
| **使用频率** | ✅ 337 次 | 282 次 |
| **数据库角色** | ✅ 主键 | 索引字段 |
| **API 惯例** | ✅ `/tasks/{id}` | ⚠️ 非标准 |
| **团队理解** | ✅ 直观 | ⚠️ 需要解释 |

**结论**：`task_id` 更符合业务领域和系统定位。

---

## 🚀 重构方案（激进版）

### Phase 1: 数据清理（30分钟）

#### 1.1 清空所有表数据

**创建清理脚本**：`backend/scripts/clear_all_data.py`

```python
"""清空所有表数据（保留表结构）"""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
import structlog

logger = structlog.get_logger()

TABLES_TO_CLEAR = [
    "execution_logs",           # 执行日志
    "quiz_questions",           # 测验题目
    "quiz",                     # 测验
    "resources",                # 资源推荐
    "tutorials",                # 教程内容
    "intent_analysis_results",  # 需求分析结果
    "roadmap_metadata",         # 路线图元数据
    "roadmap_tasks",            # 任务记录
    "user_profiles",            # 用户画像
]

async def clear_all_tables():
    """清空所有表数据"""
    async with AsyncSessionLocal() as session:
        try:
            for table in TABLES_TO_CLEAR:
                logger.info(f"清空表: {table}")
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            
            await session.commit()
            logger.info("✅ 所有表数据清空完成")
            
            # 显示清空结果
            for table in TABLES_TO_CLEAR:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                count = result.scalar()
                logger.info(f"  {table}: {count} 条记录")
                
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ 清空失败: {e}")
            raise

if __name__ == "__main__":
    print("⚠️  警告：此操作将删除所有数据！")
    confirm = input("确认清空所有表数据？(yes/no): ")
    
    if confirm.lower() == "yes":
        asyncio.run(clear_all_tables())
        print("✅ 数据清空完成")
    else:
        print("❌ 操作已取消")
```

**执行清理**：

```bash
cd backend
python scripts/clear_all_data.py
# 输入 yes 确认
```

#### 1.2 重置 Alembic 版本（可选）

如果需要从头开始迁移：

```bash
# 1. 删除现有迁移历史
alembic downgrade base

# 2. 删除 alembic_version 表记录
# psql -d roadmap_db -c "TRUNCATE TABLE alembic_version;"

# 3. 重新运行所有迁移
alembic upgrade head
```

### Phase 2: 数据库模型修改（1小时）

#### 2.1 直接修改 ExecutionLog 模型

**修改文件**：`backend/app/models/database.py`

```python
class ExecutionLog(SQLModel, table=True):
    """
    执行日志表
    
    记录工作流执行过程中的关键事件，用于：
    - 通过 task_id 追踪请求完整生命周期  # ✅ 改为 task_id
    - 聚合错误报告
    - 性能分析和问题定位
    """
    __tablename__ = "execution_logs"
    
    id: str = Field(primary_key=True)
    
    # ✅ 直接使用 task_id（删除 trace_id）
    task_id: str = Field(index=True, description="任务 ID")
    roadmap_id: Optional[str] = Field(default=None, index=True)
    concept_id: Optional[str] = Field(default=None, index=True)
    
    # 日志分类
    level: str = Field(default="info", index=True)
    category: str = Field(index=True)
    step: Optional[str] = Field(default=None, index=True)
    agent_name: Optional[str] = Field(default=None, index=True)
    
    # 日志内容
    message: str = Field(sa_column=Column(Text))
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    duration_ms: Optional[int] = Field(default=None)
    
    created_at: datetime = Field(default_factory=beijing_now)
```

**对比变化**：

```diff
- trace_id: str = Field(index=True, description="追踪 ID，对应 task_id")
+ task_id: str = Field(index=True, description="任务 ID")
```

#### 2.2 创建数据库迁移

**创建迁移**：`backend/alembic/versions/rename_trace_id_to_task_id.py`

```python
"""重命名 trace_id 为 task_id（破坏性变更）

Revision ID: xxxx_rename_trace_to_task
Revises: prev_revision
Create Date: 2025-12-07

说明：
- 直接重命名字段
- 数据已清空，无需迁移
- 重建索引
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxxx_rename_trace_to_task'
down_revision = 'prev_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 删除旧索引
    op.drop_index('ix_execution_logs_trace_id', table_name='execution_logs')
    
    # 2. 重命名字段
    op.alter_column(
        'execution_logs',
        'trace_id',
        new_column_name='task_id',
        existing_type=sa.String(),
        nullable=False
    )
    
    # 3. 创建新索引
    op.create_index(
        'ix_execution_logs_task_id',
        'execution_logs',
        ['task_id']
    )
    
    print("✅ trace_id 已重命名为 task_id")


def downgrade() -> None:
    # 回滚操作（如果需要）
    op.drop_index('ix_execution_logs_task_id', table_name='execution_logs')
    
    op.alter_column(
        'execution_logs',
        'task_id',
        new_column_name='trace_id',
        existing_type=sa.String(),
        nullable=False
    )
    
    op.create_index(
        'ix_execution_logs_trace_id',
        'execution_logs',
        ['trace_id']
    )
```

**执行迁移**：

```bash
cd backend
alembic revision --autogenerate -m "rename_trace_id_to_task_id"
alembic upgrade head
```

### Phase 3: 代码批量替换（2-3小时）

#### 3.1 全局搜索替换策略

**使用 VS Code 或 grep 进行批量替换**：

```bash
# 1. 查找所有 trace_id 使用
cd backend
rg "trace_id" --type py -l | wc -l  # 统计文件数量

# 2. 批量替换（需要人工审查）
# 使用 VS Code 的全局替换功能：
# - 搜索：\btrace_id\b
# - 替换：task_id
# - 作用域：backend/**/*.py
```

#### 3.2 替换优先级和策略

| 模式 | 替换策略 | 示例 |
|------|----------|------|
| **变量名** | 直接替换 | `trace_id = uuid()` → `task_id = uuid()` |
| **参数名** | 直接替换 | `def func(trace_id: str)` → `def func(task_id: str)` |
| **字典键** | 直接替换 | `state["trace_id"]` → `state["task_id"]` |
| **日志字段** | 直接替换 | `logger.info(..., trace_id=x)` → `logger.info(..., task_id=x)` |
| **注释文档** | 人工审查 | `追踪 ID` → `任务 ID` |
| **LangGraph thread_id** | **保持不变** | `thread_id` 是框架要求 |

#### 3.3 关键文件修改清单

**必须手动审查的文件**（约 30 个核心文件）：

1. **模型层**（1个文件）：
   ```
   app/models/database.py - ExecutionLog 定义
   ```

2. **服务层**（3个文件）：
   ```
   app/services/roadmap_service.py
   app/services/execution_logger.py
   app/db/repositories/execution_log_repo.py
   ```

3. **工作流层**（8个文件）：
   ```
   app/core/orchestrator/executor.py
   app/core/orchestrator/state_manager.py
   app/core/orchestrator/builder.py
   app/core/orchestrator/node_runners/intent_runner.py
   app/core/orchestrator/node_runners/curriculum_runner.py
   app/core/orchestrator/node_runners/content_runner.py
   app/core/orchestrator/node_runners/review_runner.py
   app/core/orchestrator/node_runners/validation_runner.py
   ```

4. **API 层**（3个文件）：
   ```
   app/api/v1/endpoints/generation.py
   app/api/v1/roadmap.py
   app/api/v1/websocket.py
   ```

5. **错误处理**（1个文件）：
   ```
   app/core/error_handler.py
   ```

6. **测试文件**（约 15 个文件）：
   ```
   tests/**/*.py
   ```

#### 3.4 State 定义修改

**文件**：`app/core/orchestrator/builder.py` 或相关 State 定义

```python
# 修改前
class RoadmapState(TypedDict):
    trace_id: str  # ❌
    roadmap_id: str | None
    user_request: UserRequest
    intent_analysis: IntentAnalysisOutput | None
    ...

# 修改后
class RoadmapState(TypedDict):
    task_id: str  # ✅
    roadmap_id: str | None
    user_request: UserRequest
    intent_analysis: IntentAnalysisOutput | None
    ...
```

#### 3.5 LangGraph thread_id 处理

**保持 thread_id 不变，但使用 task_id 的值**：

```python
# executor.py - 正确的方式
async def execute(
    self,
    user_request: UserRequest,
    task_id: str,  # ✅ 参数名用 task_id
) -> RoadmapState:
    # ✅ LangGraph 配置仍使用 thread_id（框架要求）
    config = {
        "configurable": {
            "thread_id": task_id  # 但值来自 task_id
        }
    }
    
    initial_state = {
        "task_id": task_id,  # ✅ State 中用 task_id
        "user_request": user_request,
        ...
    }
    
    return await self.graph.ainvoke(initial_state, config=config)
```

**说明**：`thread_id` 是 LangGraph 框架的 API 要求，我们保留这个键名，但将其值设置为 `task_id`。

### Phase 4: 验证和测试（1小时）

---

## 🧪 测试策略

### 单元测试

```python
# tests/unit/test_task_id_migration.py

def test_execution_log_uses_task_id():
    """验证 ExecutionLog 使用 task_id 而不是 trace_id"""
    log = ExecutionLog(
        task_id="test-task-123",
        level="info",
        category="workflow",
        message="测试消息"
    )
    assert log.task_id == "test-task-123"
    # trace_id 应该已被删除
    assert not hasattr(log, 'trace_id')


def test_state_contains_task_id():
    """验证 State 包含 task_id"""
    state = create_initial_state(request, task_id="test-123")
    assert "task_id" in state
    assert state["task_id"] == "test-123"
```

### 集成测试

```python
# tests/integration/test_task_id_e2e.py

async def test_full_workflow_uses_task_id():
    """端到端测试：验证整个工作流使用 task_id"""
    task_id = str(uuid.uuid4())
    
    # 1. 生成路线图
    result = await service.generate_roadmap(request, task_id=task_id)
    assert result["task_id"] == task_id
    
    # 2. 查询任务状态
    status = await service.get_task_status(task_id)
    assert status["task_id"] == task_id
    
    # 3. 验证数据库记录
    task = await task_repo.get_by_task_id(task_id)
    assert task.task_id == task_id
    
    # 4. 验证日志记录
    logs = await log_repo.list_by_task(task_id)  # ✅ 新方法名
    assert all(log.task_id == task_id for log in logs)
```

### 数据完整性测试

```python
async def test_data_migration_integrity():
    """验证数据迁移的完整性"""
    # 迁移前后数据应该一致
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM execution_logs 
                WHERE task_id IS NOT NULL
            """)
        )
        count = result.scalar()
        assert count > 0  # 所有记录都应该有 task_id
```

---

## ⚠️ 风险评估与应对（激进版）

### 风险矩阵

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 遗漏部分代码未重构 | **中** | **高** | ✅ 全代码搜索、自动化测试 |
| 数据丢失 | **低** | **低** | ⚠️ 数据已确认为测试脏数据，可清空 |
| 测试失败 | **中** | **中** | ✅ 修复测试，重新运行 |
| LangGraph 集成问题 | **低** | **中** | ✅ thread_id 映射验证 |

### 简化的回滚计划

**条件**：发现严重问题需要回滚

```bash
# 1. 回滚代码
git reset --hard HEAD~1  # 或使用 git revert

# 2. 回滚数据库（如果已执行迁移）
alembic downgrade -1

# 3. 重新清空数据（数据已经是空的）
# 不需要额外操作
```

**注意**：由于数据已清空，回滚风险大大降低。

---

## 📈 预期收益

### 量化指标

| 指标 | 当前 | 重构后 | 改善 |
|------|------|--------|------|
| 标识符数量 | 2个（task_id + trace_id） | 1个（task_id） | -50% |
| 显式转换次数 | 67次 | 0次 | -100% |
| 认知负担 | 需要记住等价关系 | 直观理解 | 显著降低 |
| 新人入职时间 | 需要额外解释 | 无需解释 | 节省培训时间 |

### 质量指标

- ✅ **可维护性**：减少概念重复，降低维护成本
- ✅ **可读性**：代码意图更清晰，减少困惑
- ✅ **一致性**：遵循 OneId 原则，架构更优雅
- ✅ **扩展性**：未来添加新功能时不会引入更多混淆

---

## 📅 实施时间表（激进版）

| 阶段 | 任务 | 预估时间 | 说明 |
|------|------|----------|------|
| **Phase 1** | 数据清理 | 30分钟 | 清空所有表数据 |
| | - 运行清理脚本 | 10分钟 | |
| | - 验证数据清空 | 10分钟 | |
| | - 备份确认 | 10分钟 | |
| **Phase 2** | 数据库模型修改 | 1小时 | 修改模型和迁移 |
| | - 修改 ExecutionLog | 20分钟 | |
| | - 创建 Alembic 迁移 | 20分钟 | |
| | - 执行迁移 | 20分钟 | |
| **Phase 3** | 代码批量替换 | 2-3小时 | 全局搜索替换 |
| | - 自动替换（VS Code） | 1小时 | |
| | - 人工审查关键文件 | 1-2小时 | |
| | - 处理 LangGraph 特殊情况 | 30分钟 | |
| **Phase 4** | 验证和测试 | 1小时 | 全面测试 |
| | - 单元测试 | 20分钟 | |
| | - 集成测试 | 20分钟 | |
| | - E2E 测试 | 20分钟 | |

**总计：4.5-5.5 小时（半天工作量）**

---

## ✅ 验收标准（激进版）

### 代码检查清单

- [ ] **零残留**：`trace_id` 变量名全部替换为 `task_id`
- [ ] **State 一致**：`state["trace_id"]` 改为 `state["task_id"]`
- [ ] **无显式转换**：删除所有 `task_id=trace_id` 赋值
- [ ] **模型已更新**：`ExecutionLog.trace_id` 字段改为 `task_id`
- [ ] **测试通过**：所有单元测试和集成测试通过

### 自动化检查脚本

```bash
# 检查是否还有 trace_id 残留
cd backend
echo "🔍 检查 trace_id 残留..."

# 1. 查找 Python 代码中的 trace_id
trace_count=$(rg "\btrace_id\b" --type py -g '!alembic/versions/*' | wc -l)
if [ $trace_count -eq 0 ]; then
    echo "✅ Python 代码：无 trace_id 残留"
else
    echo "❌ Python 代码：发现 $trace_count 处 trace_id"
    rg "\btrace_id\b" --type py -g '!alembic/versions/*' -l
fi

# 2. 查找文档中的 trace_id
doc_count=$(rg "trace_id" --type md | wc -l)
if [ $doc_count -eq 0 ]; then
    echo "✅ 文档：无 trace_id 残留"
else
    echo "⚠️  文档：发现 $doc_count 处 trace_id（可能需要更新）"
fi

# 3. 检查 State 定义
state_check=$(rg '"trace_id"' --type py)
if [ -z "$state_check" ]; then
    echo "✅ State 定义：已更新为 task_id"
else
    echo "❌ State 定义：仍在使用 trace_id"
fi
```

### 数据库检查

```sql
-- 1. 验证表已清空
SELECT 
    'execution_logs' as table_name, 
    COUNT(*) as record_count 
FROM execution_logs
UNION ALL
SELECT 'roadmap_tasks', COUNT(*) FROM roadmap_tasks
UNION ALL
SELECT 'roadmap_metadata', COUNT(*) FROM roadmap_metadata;
-- 所有结果应该为 0

-- 2. 验证 task_id 字段存在
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'execution_logs' AND column_name = 'task_id';
-- 应该返回：task_id | character varying

-- 3. 验证 trace_id 字段已删除
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'execution_logs' AND column_name = 'trace_id';
-- 结果应该为空
```

### 功能验证清单

**手动测试**：

- [ ] **生成路线图**：创建新任务，验证返回 `task_id`
- [ ] **查询状态**：`GET /api/v1/roadmaps/{task_id}/status` 正常
- [ ] **WebSocket**：实时通知包含 `task_id` 字段
- [ ] **日志查询**：可以通过 `task_id` 查询执行日志
- [ ] **数据库记录**：新创建的记录使用 `task_id`

**自动化测试**：

```bash
# 运行所有测试
cd backend
pytest tests/ -v

# 重点测试工作流
pytest tests/integration/test_orchestrator_workflow.py -v

# 测试 API 端点
pytest tests/api/test_new_endpoints_e2e.py -v
```

---

## 📚 参考资料

### 相关原则

1. **OneId 原则**（DDD）：
   - 一个聚合根应该只有一个唯一标识符
   - 避免在不同上下文使用不同名称

2. **最小惊讶原则**（Principle of Least Astonishment）：
   - 系统行为应该符合用户直觉
   - 减少需要特殊记忆的规则

3. **DRY 原则**（Don't Repeat Yourself）：
   - 避免重复的概念和定义

### 类似案例

- **Kubernetes**：`name` 作为资源的唯一标识符
- **AWS**：`ARN` 作为资源的全局唯一标识符
- **HTTP**：`request-id` / `trace-id` 统一追踪

---

## 🚀 快速执行指南

### 一键执行脚本

创建完整的重构脚本：`backend/scripts/refactor_trace_to_task.sh`

```bash
#!/bin/bash
set -e

echo "🔥 开始 trace_id → task_id 重构（激进版）"
echo "================================================"

# Step 1: 数据清理
echo ""
echo "📦 Phase 1: 清空数据库数据"
python scripts/clear_all_data.py

# Step 2: 执行数据库迁移
echo ""
echo "🗄️  Phase 2: 执行数据库迁移"
alembic upgrade head

# Step 3: 代码批量替换（需要人工执行）
echo ""
echo "💻 Phase 3: 代码批量替换"
echo "⚠️  请使用 VS Code 执行以下操作："
echo "   1. 打开全局搜索替换 (Cmd+Shift+H)"
echo "   2. 搜索：\\btrace_id\\b"
echo "   3. 替换：task_id"
echo "   4. 作用域：backend/**/*.py"
echo "   5. 人工审查并确认每个替换"
echo ""
read -p "完成批量替换后，按 Enter 继续..."

# Step 4: 运行测试
echo ""
echo "🧪 Phase 4: 运行测试验证"
pytest tests/ -v --maxfail=5

# Step 5: 验证检查
echo ""
echo "✅ Phase 5: 最终验证"
./scripts/check_trace_id_residue.sh

echo ""
echo "================================================"
echo "🎉 重构完成！"
echo ""
echo "下一步："
echo "1. 提交代码：git add . && git commit -m 'refactor: 统一使用 task_id 替代 trace_id'"
echo "2. 推送到远程：git push"
echo "3. 创建 PR 并请求代码审查"
```

### 手动执行步骤（推荐）

如果不使用自动化脚本，按以下步骤执行：

#### Step 1: 清空数据（5分钟）

```bash
cd backend
python scripts/clear_all_data.py
# 输入 yes 确认
```

#### Step 2: 修改模型（10分钟）

编辑 `app/models/database.py`，将 `ExecutionLog` 中的 `trace_id` 改为 `task_id`。

#### Step 3: 创建迁移（10分钟）

```bash
# 自动生成迁移
alembic revision --autogenerate -m "rename_trace_id_to_task_id"

# 检查生成的迁移文件
# 编辑 alembic/versions/xxxx_rename_trace_id_to_task_id.py

# 执行迁移
alembic upgrade head
```

#### Step 4: 批量替换代码（1-2小时）

**使用 VS Code**：
1. 打开全局搜索替换（`Cmd+Shift+H` 或 `Ctrl+Shift+H`）
2. 搜索正则：`\btrace_id\b`
3. 替换为：`task_id`
4. 文件范围：`backend/**/*.py`
5. 排除：`alembic/versions/*`（旧迁移文件）

**手动审查关键文件**（必须检查）：
- `app/models/database.py` - 模型定义
- `app/core/orchestrator/executor.py` - 确认 `thread_id` 映射
- `app/services/roadmap_service.py` - 核心服务
- `tests/**/*.py` - 所有测试文件

#### Step 5: 运行测试（20分钟）

```bash
# 运行所有测试
pytest tests/ -v

# 如果有失败，逐个修复并重新运行
pytest tests/integration/ -v
pytest tests/api/ -v
```

#### Step 6: 提交代码（5分钟）

```bash
git add .
git commit -m "refactor: 统一使用 task_id 替代 trace_id (破坏性变更)

- 将所有 trace_id 重命名为 task_id
- 更新 ExecutionLog 模型定义
- 清空所有测试数据
- 遵循 OneId 建模原则

BREAKING CHANGE: trace_id 已全部替换为 task_id
"
```

## 💡 最佳实践和注意事项

### 重要提醒

1. **LangGraph thread_id**：
   ```python
   # ✅ 正确：thread_id 是框架要求，保留键名
   config = {"configurable": {"thread_id": task_id}}
   
   # ❌ 错误：不要改成 task_id
   config = {"configurable": {"task_id": task_id}}  # 这会导致 LangGraph 错误
   ```

2. **State 字典键**：
   ```python
   # ✅ 全部改为 task_id
   state["task_id"] = uuid.uuid4()
   task_id = state["task_id"]
   
   # ❌ 不要遗漏
   state["trace_id"]  # 应该改为 task_id
   ```

3. **日志字段**：
   ```python
   # ✅ 统一使用 task_id
   logger.info("处理中", task_id=task_id)
   
   # ❌ 不要混用
   logger.info("处理中", trace_id=task_id)  # 字段名错误
   ```

### 代码审查检查点

在提交 PR 前，确保：

- [ ] 搜索 `\btrace_id\b`，确认无残留（排除文档和迁移文件）
- [ ] 所有测试通过
- [ ] `ExecutionLog` 模型已更新
- [ ] `RoadmapState` TypedDict 已更新
- [ ] API 文档已更新
- [ ] LangGraph `thread_id` 映射正确

---

## 📞 联系与支持

- **问题反馈**：GitHub Issues
- **技术咨询**：Backend Team
- **紧急支持**：On-call Engineer

---

**文档版本**：v1.0  
**创建日期**：2025-12-07  
**最后更新**：2025-12-07
