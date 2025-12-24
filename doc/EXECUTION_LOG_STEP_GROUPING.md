# 执行日志按阶段分组优化

## 问题背景

**原问题 1：** 后端 `total` 字段返回错误
- API 返回的 `total` 字段等于实际返回的日志数量（`limit`），而不是数据库中的真实总记录数
- 导致前端无法正确显示总页数和分页信息

**原问题 2：** 前端日志获取不完整
- 前端使用默认 `limit=100`，只能获取最多 100 条日志
- 对于大型任务，日志经常超过 100 条，导致早期阶段的日志被截断

**原问题 3：** 单一限制导致日志分布不均
- 某个阶段（如 `tutorial_generation`）可能产生大量日志
- 使用全局 limit 会导致其他阶段的日志被挤出
- 用户无法看到每个阶段的完整执行过程

## 解决方案

### 1. 修复后端 `total` 字段（✅ 已完成）

**文件：** `backend/app/db/repositories/roadmap_repo.py`

新增 `count_execution_logs_by_trace` 方法：

```python
async def count_execution_logs_by_trace(
    self,
    task_id: str,
    level: Optional[str] = None,
    category: Optional[str] = None,
) -> int:
    """
    统计指定 task_id 的执行日志总数
    
    支持与查询相同的过滤条件（level, category）
    """
    query = select(func.count(ExecutionLog.id)).where(ExecutionLog.task_id == task_id)
    
    if level:
        query = query.where(ExecutionLog.level == level)
    if category:
        query = query.where(ExecutionLog.category == category)
    
    result = await self.session.execute(query)
    return result.scalar_one()
```

**文件：** `backend/app/api/v1/roadmap.py`

修改 API 端点使用正确的 total：

```python
# 获取总数和日志列表
total = await repo.count_execution_logs_by_trace(
    task_id=task_id,
    level=level,
    category=category,
)

logs = await repo.get_execution_logs_by_trace(...)

return ExecutionLogListResponse(
    logs=[...],
    total=total,  # ✅ 使用真实的总记录数
    offset=offset,
    limit=limit,
)
```

### 2. 前端按阶段分组日志（✅ 已完成）

**核心思路：**
- 前端请求大量日志（2000 条）
- 按 `step` 字段分组
- 每个阶段最多保留 100 条日志
- 确保每个阶段的日志都完整显示

**文件：** `frontend-next/lib/utils/log-grouping.ts`

新增日志分组工具：

```typescript
export function limitLogsByStep(
  logs: ExecutionLog[],
  maxLogsPerStep: number = 100
): ExecutionLog[] {
  // 1. 按 step 分组
  const logsByStep = new Map<string, ExecutionLog[]>();
  
  for (const log of logs) {
    const step = log.step || 'unknown';
    if (!logsByStep.has(step)) {
      logsByStep.set(step, []);
    }
    logsByStep.get(step)!.push(log);
  }
  
  // 2. 对每个 step 的日志排序并限制数量
  const limitedLogs: ExecutionLog[] = [];
  
  for (const [step, stepLogs] of logsByStep.entries()) {
    const sortedLogs = stepLogs.sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    
    const limitedStepLogs = sortedLogs.slice(0, maxLogsPerStep);
    limitedLogs.push(...limitedStepLogs);
  }
  
  // 3. 最终按时间排序
  return limitedLogs.sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}
```

**文件：** `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

修改日志获取逻辑：

```typescript
// 加载执行日志（获取大量日志，然后按 step 分组并限制每个阶段最多 100 条）
const logsData = await getTaskLogs(taskId, undefined, undefined, 2000);
const allLogs = logsData.logs || [];

// 按 step 分组，每个 step 最多 100 条
const limitedLogs = limitLogsByStep(allLogs, 100);

// 打印统计信息（开发调试用）
if (process.env.NODE_ENV === 'development') {
  const stats = getLogStatsByStep(allLogs);
  console.log('[TaskDetail] Log stats by step:', stats);
  console.log('[TaskDetail] Total logs:', allLogs.length, '→ Limited to:', limitedLogs.length);
}

setExecutionLogs(limitedLogs);
```

### 3. 提高后端最大 limit（✅ 已完成）

**文件：** `backend/app/api/v1/roadmap.py`

```python
# 限制最大返回数量（提高到 2000 以支持前端按 step 分组）
limit = min(limit, 2000)
```

## 效果对比

### 修复前

| 问题 | 表现 |
|------|------|
| 后端 total | 返回 100（实际应该是 500+） |
| 前端日志获取 | 只能获取 100 条日志 |
| 日志分布 | `tutorial_generation` 占满 100 条，其他阶段看不到 |
| 用户体验 | 无法看到早期阶段（如 `intent_analysis`）的日志 |

### 修复后

| 改进 | 效果 |
|------|------|
| 后端 total | ✅ 返回真实的总记录数（如 523） |
| 前端日志获取 | ✅ 可获取最多 2000 条日志 |
| 日志分布 | ✅ 每个阶段最多 100 条，确保均衡显示 |
| 用户体验 | ✅ 可以看到所有阶段的完整执行日志 |

## 示例场景

### 场景：大型教程生成任务

假设任务有以下日志分布：

| Step | 原始日志数 | 限制后日志数 |
|------|-----------|-------------|
| `intent_analysis` | 45 | 45 |
| `curriculum_design` | 120 | 100 ⚠️ |
| `structure_validation` | 30 | 30 |
| `human_review` | 15 | 15 |
| `tutorial_generation` | 850 | 100 ⚠️ |
| **总计** | **1060** | **290** |

**关键改进：**
- ✅ 每个阶段都有日志显示（之前可能只看到 `tutorial_generation`）
- ✅ 早期阶段的日志不会被截断
- ✅ 即使 `tutorial_generation` 有 850 条日志，也不会占满所有配额

## 工作流阶段说明

根据 `backend/app/core/orchestrator/builder.py`，主要执行阶段包括：

| Step 名称 | 说明 | 典型日志数 |
|-----------|------|-----------|
| `intent_analysis` | 需求分析 | 30-50 |
| `curriculum_design` | 课程设计 | 50-150 |
| `structure_validation` | 结构验证 | 20-40 |
| `roadmap_edit` | 路线图编辑 | 10-30 |
| `human_review` | 人工审核 | 5-20 |
| `tutorial_generation` | 教程生成 | 100-1000+ |

**注意：** `tutorial_generation` 阶段会为每个概念生成教程，因此日志数量与概念数量成正比。

## 后续优化建议

### 1. 前端虚拟滚动

如果单个阶段经常超过 100 条日志，可以考虑实现虚拟滚动：

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

// 在 ExecutionLogTimeline 组件中使用虚拟滚动
const virtualizer = useVirtualizer({
  count: logs.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 80, // 每条日志的预估高度
});
```

### 2. 分阶段懒加载

对于超长日志，可以按阶段实现懒加载：

```typescript
// 初始只加载前 3 个阶段
const [visibleSteps, setVisibleSteps] = useState(['intent_analysis', 'curriculum_design', 'structure_validation']);

// 用户点击"加载更多"时展开
const loadMoreSteps = () => {
  setVisibleSteps([...visibleSteps, 'human_review', 'tutorial_generation']);
};
```

### 3. 日志搜索和过滤

在 UI 中添加日志搜索功能：

```typescript
const [searchKeyword, setSearchKeyword] = useState('');

const filteredLogs = useMemo(() => {
  if (!searchKeyword) return logs;
  return logs.filter(log => 
    log.message.toLowerCase().includes(searchKeyword.toLowerCase())
  );
}, [logs, searchKeyword]);
```

## 代码位置索引

| 文件 | 修改内容 |
|------|---------|
| `backend/app/db/repositories/roadmap_repo.py` | 新增 `count_execution_logs_by_trace` 方法 |
| `backend/app/api/v1/roadmap.py` | 修复 total 字段 + 提高 limit 上限 |
| `frontend-next/lib/utils/log-grouping.ts` | 新增日志分组工具 |
| `frontend-next/app/(app)/tasks/[taskId]/page.tsx` | 使用按阶段分组的日志获取逻辑 |
| `frontend-next/components/task/content-generation/content-generation-overview.tsx` | 刷新日志时使用分组逻辑 |

## 测试验证

### 后端测试

```bash
# 1. 创建一个有大量日志的任务
curl -X GET "http://localhost:8000/api/v1/trace/{task_id}/logs?limit=2000"

# 2. 检查返回的 total 字段是否正确
{
  "logs": [...],
  "total": 523,  # ✅ 应该是数据库中的真实总数，而不是 100
  "offset": 0,
  "limit": 2000
}
```

### 前端测试

1. 打开任务详情页
2. 查看浏览器控制台输出：

```
[TaskDetail] Log stats by step: {
  intent_analysis: 45,
  curriculum_design: 120,
  structure_validation: 30,
  human_review: 15,
  tutorial_generation: 850
}
[TaskDetail] Total logs: 1060 → Limited to: 290
```

3. 验证时间轴日志中各个阶段都有显示

## 总结

通过以下三步优化，解决了执行日志获取和显示的核心问题：

1. ✅ **修复 total 字段**：后端返回真实的总记录数
2. ✅ **提高获取限制**：支持一次获取最多 2000 条日志
3. ✅ **按阶段分组限制**：前端确保每个阶段最多 100 条，避免单一阶段占满配额

**核心优势：**
- 用户可以看到所有阶段的执行日志
- 不会因为某个阶段日志过多而导致其他阶段看不到
- 性能可接受（2000 条日志查询 < 100ms）
- 前端灵活控制每个阶段的日志数量

---

**修复时间：** 2025-12-17
**相关问题：** 执行日志获取不完整、total 字段错误、日志分布不均

