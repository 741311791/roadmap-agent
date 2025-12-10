# trace_id → task_id 重构总结

## 🎯 重构目标

统一使用 `task_id` 作为唯一标识符，遵循 OneId 建模原则。

## 📊 分析结果

### 现状问题

- **同一个值，三个名称**：`trace_id`、`task_id`、`thread_id`
- **使用统计**：
  - `task_id` 出现 337 次
  - `trace_id` 出现 282 次
  - 显式转换 67 次
- **违反原则**：OneId、DRY、最小惊讶原则

### 为什么选择 task_id

| 标准 | 优势 |
|------|------|
| 业务语义 | ✅ 清晰直观 |
| 使用频率 | ✅ 更高（337 vs 282） |
| 数据库角色 | ✅ 主键字段 |
| API 惯例 | ✅ RESTful 标准 |

## 🔧 重构方案

### 激进版（推荐）

**特点**：
- ❌ 不考虑向后兼容
- 🗑️ 清空所有测试脏数据
- ⚡ 一次性完成（半天工作量）

**核心步骤**：
1. 清空数据库（30分钟）
2. 修改模型和迁移（1小时）
3. 批量替换代码（2-3小时）
4. 验证测试（1小时）

**总时间**：4.5-5.5 小时

### 关键文件

**必须修改**（约30个）：
- `app/models/database.py` - ExecutionLog 模型
- `app/services/roadmap_service.py` - 核心服务
- `app/core/orchestrator/**/*.py` - 工作流节点（8个文件）
- `app/api/v1/**/*.py` - API 端点（3个文件）
- `tests/**/*.py` - 测试文件（15个）

**特殊处理**：
- `thread_id`：LangGraph 框架要求，保留键名但使用 `task_id` 的值

## ✅ 验收标准

### 代码检查

```bash
# 搜索残留（应为0）
rg "\btrace_id\b" --type py -g '!alembic/versions/*' | wc -l
```

### 数据库验证

```sql
-- task_id 字段存在
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'execution_logs' AND column_name = 'task_id';

-- trace_id 字段已删除
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'execution_logs' AND column_name = 'trace_id';
```

### 功能测试

- [ ] 生成路线图正常
- [ ] 任务状态查询正常
- [ ] WebSocket 通知正常
- [ ] 日志追踪正常

## 📈 预期收益

| 指标 | 改善 |
|------|------|
| 标识符数量 | -50% (2→1) |
| 显式转换 | -100% (67→0) |
| 认知负担 | 显著降低 |
| 维护成本 | 降低 |

## 📚 相关文档

- [TASK_ID_UNIFICATION_PLAN.md](./TASK_ID_UNIFICATION_PLAN.md) - 完整重构计划
- [DATABASE_TIMEOUT_FIX.md](./DATABASE_TIMEOUT_FIX.md) - 数据库优化

## 🚀 快速开始

```bash
# 1. 清空数据
cd backend
python scripts/clear_all_data.py

# 2. 执行迁移
alembic upgrade head

# 3. 批量替换（使用 VS Code）
# 搜索：\btrace_id\b
# 替换：task_id

# 4. 运行测试
pytest tests/ -v

# 5. 提交代码
git commit -m "refactor: 统一使用 task_id 替代 trace_id"
```

---

**创建时间**：2025-12-07  
**预估工时**：4.5-5.5 小时  
**破坏性变更**：是
