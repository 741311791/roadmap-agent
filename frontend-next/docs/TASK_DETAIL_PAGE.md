# 任务详情页面设计文档

> **创建日期**: 2025-12-13  
> **功能**: 任务执行详情页面，提供实时进度跟踪和详细日志查看

---

## 📋 功能概述

任务详情页面为用户提供了对路线图生成任务的全面可视化跟踪能力，包括：

1. **横向工作流步进器** - 直观展示任务所有执行阶段
2. **实时WebSocket订阅** - 自动更新任务状态和日志
3. **分阶段日志展示** - 按工作流阶段分组的详细执行日志
4. **性能指标** - 每个阶段的执行时长统计

---

## 🎨 设计特色

### 1. **横向步进器 (Horizontal Workflow Stepper)**

采用现代的线性进度指示器设计：

- **视觉效果**：圆点 + 连接线，清晰展示工作流进度
- **动态动画**：当前阶段带有脉冲动画和阴影效果
- **状态区分**：
  - ✅ 已完成：绿色圆点 + 对勾图标
  - 🔄 进行中：蓝色圆点 + 加载动画 + 阴影
  - ⏳ 待处理：灰色圆点 + 空心图标
  - ❌ 失败：红色圆点 + 错误图标

### 2. **执行日志时间轴 (Execution Log Timeline)**

按阶段分组的日志展示：

- **阶段过滤**：通过标签快速跳转到特定阶段
- **可折叠卡片**：每个阶段独立卡片，支持展开/折叠
- **日志级别色彩**：
  - 🔴 Error - 红色背景
  - 🟡 Warning - 黄色背景
  - 🟢 Success - 绿色背景
  - 🔵 Info - 灰色背景
- **时间戳 + 分类标签**：清晰标注日志来源和时间
- **性能指标**：显示每条日志的执行耗时

### 3. **实时更新机制**

- **WebSocket连接**：自动订阅任务状态更新
- **历史状态恢复**：页面刷新后可恢复之前的进度
- **事件处理**：
  - `onProgress` - 任务进度更新
  - `onConceptStart` - 概念内容生成开始
  - `onConceptComplete` - 概念内容生成完成
  - `onCompleted` - 任务完成
  - `onFailed` - 任务失败

---

## 📂 文件结构

```
frontend-next/
├── app/(app)/tasks/
│   └── [taskId]/
│       └── page.tsx                    # 任务详情页面主文件
├── components/task/
│   ├── horizontal-workflow-stepper.tsx # 横向步进器组件
│   ├── execution-log-timeline.tsx      # 执行日志时间轴组件
│   └── task-list.tsx                   # 任务列表（已更新链接）
└── lib/api/
    └── endpoints.ts                    # API端点（新增日志相关接口）
```

---

## 🔌 API接口

### 1. **获取任务详情**

```typescript
GET /api/v1/roadmaps/{taskId}/status

Response:
{
  task_id: string;
  title: string;
  status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  roadmap_id?: string | null;
}
```

### 2. **获取任务执行日志**

```typescript
GET /api/v1/trace/{taskId}/logs?level=info&category=workflow&limit=100&offset=0

Response:
{
  logs: ExecutionLogItem[];
  total: number;
  offset: number;
  limit: number;
}
```

### 3. **获取任务执行摘要**

```typescript
GET /api/v1/trace/{taskId}/summary

Response:
{
  task_id: string;
  level_stats: Record<string, number>;
  category_stats: Record<string, number>;
  total_duration_ms: number | null;
  first_log_at: string | null;
  last_log_at: string | null;
  total_logs: number;
}
```

### 4. **WebSocket实时订阅**

```typescript
ws://localhost:8000/ws/{taskId}?include_history=true

Events:
- progress: 任务进度更新
- status: 任务状态更新
- concept_start: 概念内容生成开始
- concept_complete: 概念内容生成完成
- completed: 任务完成
- failed: 任务失败
```

---

## 🛠️ 工作流阶段定义

| 阶段ID | 标签 | 包含步骤 | 描述 |
|:---|:---|:---|:---|
| `intent_analysis` | Intent Analysis | init, queued, starting, intent_analysis | 分析学习目标和需求 |
| `curriculum_design` | Curriculum Design | curriculum_design, framework_generation | 设计课程结构框架 |
| `structure_validation` | Structure Validation | structure_validation | 验证路线图逻辑性 |
| `human_review` | Human Review | human_review, roadmap_edit | 等待用户确认和编辑 |
| `content_generation` | Content Generation | content_generation, tutorial_generation, resource_recommendation, quiz_generation | 生成学习材料 |
| `finalizing` | Finalizing | finalizing | 收尾处理 |

---

## 🎯 使用场景

### 1. **开发调试**
- 开发者可以实时查看任务执行的每一步
- 快速定位问题所在阶段
- 查看详细的错误日志和堆栈信息

### 2. **用户透明度**
- 用户可以清楚看到路线图生成进度
- 了解每个阶段的执行情况
- 对于长时间任务有明确的预期

### 3. **性能分析**
- 查看每个阶段的执行耗时
- 识别性能瓶颈
- 优化工作流效率

---

## 🚀 快速开始

### 1. **从任务列表进入**

在任务列表页面（`/tasks`），点击任何任务的标题即可进入详情页：

```typescript
// 任务列表中的链接
<Link href={`/tasks/${task.task_id}`}>
  {task.title}
</Link>
```

### 2. **直接访问**

也可以通过URL直接访问：

```
http://localhost:3000/tasks/{taskId}
```

### 3. **页面加载流程**

1. 加载任务基本信息（`getTaskDetail`）
2. 加载执行日志（`getTaskLogs`）
3. 如果任务正在处理中，建立WebSocket连接
4. 实时接收并显示新的日志

---

## 💡 设计理念

### 1. **信息层次清晰**

- **第一层**：任务基本信息（标题、ID、状态）
- **第二层**：工作流整体进度（横向步进器）
- **第三层**：详细执行日志（时间轴）

### 2. **视觉引导**

- 使用色彩区分不同状态和级别
- 动画效果突出当前活动的阶段
- 清晰的视觉层级引导用户关注重点

### 3. **性能优化**

- 日志按阶段分组，默认可折叠，减少初始渲染负担
- WebSocket仅在任务处理中时连接
- 支持分页加载大量日志

### 4. **用户体验**

- 页面刷新后自动恢复状态（`include_history=true`）
- 支持快速跳转到特定阶段
- 详细信息可展开查看，避免信息过载

---

## 🔧 技术实现细节

### 1. **阶段映射逻辑**

```typescript
// 将后端的步骤映射到前端的阶段
const PHASE_MAPPING: Record<string, { label: string; steps: string[] }> = {
  intent_analysis: {
    label: 'Intent Analysis',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  // ... 其他阶段
};
```

### 2. **WebSocket事件处理**

```typescript
const ws = new TaskWebSocket(taskId, {
  onProgress: (event) => {
    // 添加实时日志到日志列表
    setExecutionLogs((prev) => [...prev, newLog]);
    // 更新当前步骤
    setTaskInfo((prev) => ({ ...prev, current_step: event.step }));
  },
  // ... 其他事件处理器
});

ws.connect(true); // include_history = true
```

### 3. **日志分组和过滤**

```typescript
// 按阶段分组日志
const groupedLogs = useMemo(() => {
  const groups: Record<string, ExecutionLog[]> = {};
  logs.forEach((log) => {
    const phase = mapStepToPhase(log.step);
    if (!groups[phase]) groups[phase] = [];
    groups[phase].push(log);
  });
  return groups;
}, [logs]);
```

---

## 📊 数据流图

```
┌─────────────────┐
│   User Action   │
│  Click Task     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load Task Data │
│  - getTaskDetail│
│  - getTaskLogs  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Render UI       │
│ - Stepper       │
│ - Log Timeline  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WebSocket       │  ←──┐
│ (if processing) │     │
└────────┬────────┘     │
         │              │
         ▼              │
┌─────────────────┐     │
│ Real-time       │     │
│ Updates         │─────┘
└─────────────────┘
```

---

## 🎨 UI截图说明

### 横向步进器
- 顶部显示任务基本信息和状态Badge
- 中间是横向的工作流步进器，展示所有阶段
- 当前阶段高亮显示，带有动画效果

### 日志时间轴
- 顶部是阶段过滤标签
- 每个阶段一个可折叠卡片
- 卡片头部显示阶段名称、日志数量、总耗时、错误/警告数
- 卡片内容是该阶段的所有日志，按时间排序
- 每条日志显示时间戳、分类、消息、耗时

---

## 🔮 未来优化方向

1. **日志搜索功能** - 支持关键词搜索日志
2. **日志导出** - 导出日志为JSON或文本文件
3. **性能图表** - 可视化每个阶段的耗时分布
4. **错误分析** - 智能分析错误原因和建议
5. **日志级别筛选** - 支持按日志级别快速筛选
6. **实时通知** - 任务完成或失败时的桌面通知

---

## 📚 相关文档

- [WebSocket API文档](../../backend/docs/FRONTEND_API_GUIDE.md)
- [任务状态枚举](../../doc/STATUS_ALIGNMENT_SUMMARY.md)
- [前端架构文档](./ARCHITECTURE.md)

---

## ✅ 测试清单

- [ ] 页面正常加载任务信息
- [ ] 横向步进器正确显示当前阶段
- [ ] 执行日志按阶段正确分组
- [ ] WebSocket实时更新工作正常
- [ ] 页面刷新后状态恢复正常
- [ ] 任务失败时显示错误信息
- [ ] 任务完成时显示成功提示
- [ ] 阶段过滤功能正常工作
- [ ] 日志可折叠/展开
- [ ] 返回任务列表链接正常工作
- [ ] 响应式设计在移动端正常显示

