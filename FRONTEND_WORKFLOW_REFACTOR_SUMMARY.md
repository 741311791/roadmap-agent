# Frontend Workflow Refactor - Implementation Summary

**日期**: 2025-12-23  
**目标**: 重构前端任务详情页以支持新增的 EditPlanAnalyzer 阶段，包括拓扑图分支结构、执行日志配置和编辑蒙版简化

---

## 完成的工作

### 1. ✅ 创建新的工作流拓扑组件

**文件**: `frontend-next/components/task/workflow-topology.tsx` (新建)

**功能**:
- 实现了主路 + 双分支的拓扑图结构
- **主路节点**: Analysis → Design → Validate → Review → Content
- **验证分支**: Validate → Plan1 → Edit1 → 回到 Validate
- **审核分支**: Review → Plan2 → Edit2 → 回到 Review
- 使用 `edit_source` 字段区分当前激活的分支
- 分支节点渲染在触发节点下方，带有循环箭头指示
- 支持实时状态更新和动画效果
- 内嵌 Human Review 交互面板

**核心数据结构**:

```typescript
// 主路节点
const MAIN_STAGES = [
  { id: 'analysis', ... },
  { id: 'design', ... },
  { id: 'validate', ... },
  { id: 'review', ... },
  { id: 'content', ... },
];

// 验证分支
const VALIDATION_BRANCH = {
  triggerNode: 'validate',
  returnNode: 'validate',
  editSource: 'validation_failed',
  nodes: [
    { id: 'plan1', steps: ['validation_edit_plan_analysis'] },
    { id: 'edit1', steps: ['roadmap_edit'] },
  ],
};

// 审核分支
const REVIEW_BRANCH = {
  triggerNode: 'review',
  returnNode: 'review',
  editSource: 'human_review',
  nodes: [
    { id: 'plan2', steps: ['edit_plan_analysis'] },
    { id: 'edit2', steps: ['roadmap_edit'] },
  ],
};
```

**工具函数**: `getStepLocation()`
- 根据 `currentStep` 和 `editSource` 判断当前位置
- 返回节点所在的主路/分支信息
- 正确处理 `roadmap_edit` 共享步骤（通过 `edit_source` 区分）

---

### 2. ✅ 更新执行日志配置

**文件**: `frontend-next/components/task/execution-log-timeline.tsx`

**修改**: 在 `STEP_CONFIG` 中添加新节点配置

```typescript
// 验证分支节点（验证失败触发）
validation_edit_plan_analysis: { 
  label: 'Validation Edit Plan', 
  color: 'text-amber-700', 
  bgColor: 'bg-amber-50' 
},

// 审核分支节点（用户拒绝触发）
edit_plan_analysis: { 
  label: 'Review Edit Plan', 
  color: 'text-blue-700', 
  bgColor: 'bg-blue-50' 
},

// 共享编辑节点
roadmap_edit: { 
  label: 'Roadmap Edit', 
  color: 'text-purple-700', 
  bgColor: 'bg-purple-50' 
},
```

---

### 3. ✅ 简化 EditingOverlay 组件

**文件**: `frontend-next/components/task/roadmap-tree/RoadmapTree.tsx`

**修改前**: ~300 行复杂组件，包含验证结果、评分卡片、问题统计等

**修改后**: 简化为 ~10 行加载状态蒙版

```typescript
function EditingOverlay() {
  return (
    <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-40 flex items-center justify-center rounded-lg">
      <div className="text-center space-y-3">
        <Loader2 className="w-10 h-10 text-sage-600 animate-spin mx-auto" />
        <p className="text-sm text-gray-600">Updating roadmap structure...</p>
      </div>
    </div>
  );
}
```

**移除的依赖**: `CheckCircle`, `AlertTriangle`, `XCircle`, `TrendingUp`, `Progress`, `getLatestValidation`, `ValidationResult`, `DimensionScore`

---

### 4. ✅ 添加 WebSocket 类型定义

**文件**: `frontend-next/lib/api/websocket.ts`

**修改**: 在 `WSProgressEvent` 接口中添加 `edit_source` 字段

```typescript
export interface WSProgressEvent extends WSEvent {
  type: 'progress';
  step: string;
  status: string;
  message?: string;
  timestamp: string;
  data?: {
    // ... 其他字段 ...
    edit_source?: 'validation_failed' | 'human_review';  // 新增
  };
}
```

---

### 5. ✅ 任务详情页集成

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

**修改**:

1. **添加状态追踪**:
```typescript
// 编辑来源（用于区分分支）
const [editSource, setEditSource] = useState<'validation_failed' | 'human_review' | null>(null);
```

2. **WebSocket 事件处理**:
```typescript
onProgress: async (event) => {
  // ... 其他逻辑 ...
  
  // 更新 edit_source（用于区分分支）
  if (event.data?.edit_source) {
    setEditSource(event.data.edit_source);
  }
}
```

3. **组件替换**:
```typescript
// 替换前
import { WorkflowProgressEnhanced } from '@/components/task/workflow-progress-enhanced';
<WorkflowProgressEnhanced ... />

// 替换后
import { WorkflowTopology } from '@/components/task/workflow-topology';
<WorkflowTopology
  currentStep={taskInfo.current_step}
  status={taskInfo.status}
  editSource={editSource}  // 新增
  ...
/>
```

---

## 关键实现细节

### 1. 分支状态判断

通过 `getStepLocation()` 函数实现：
- **主路节点**: 直接从 `MAIN_STAGES` 查找 `currentStep`
- **分支节点**: 
  - 如果 `currentStep === 'roadmap_edit'`，必须检查 `editSource` 
  - 如果 `editSource === 'validation_failed'` → 验证分支
  - 如果 `editSource === 'human_review'` → 审核分支

### 2. 分支可视化

- **主路**: 横向排列，实线连接
- **分支**: 在触发节点下方垂直渲染，虚线边框
- **回环指示**: 分支底部显示 "↩ Validate" 或 "↩ Review" 标签
- **激活状态**: 当前激活的分支高亮显示，非激活分支透明度降低

### 3. 实时状态同步

后端在 `WorkflowBrain.node_execution()` 中发送进度事件：
```python
# backend/app/core/orchestrator/workflow_brain.py
await self.notification_service.publish_progress(
    task_id=state["task_id"],
    step="validation_edit_plan_analysis",  # 或 edit_plan_analysis
    extra_data={
        "edit_source": state.get("edit_source"),  # validation_failed 或 human_review
    }
)
```

前端接收后更新 `editSource` 状态，触发拓扑图重新渲染。

---

## 测试验证要点

### 1. 验证分支测试
- [ ] 创建一个会验证失败的路线图
- [ ] 观察是否进入 Validate → Plan1 → Edit1 → Validate 循环
- [ ] 检查分支节点是否正确高亮
- [ ] 验证日志中是否显示 "Validation Edit Plan" 和 "Roadmap Edit"

### 2. 审核分支测试
- [ ] 创建路线图并等待 Human Review
- [ ] 拒绝路线图并提供反馈
- [ ] 观察是否进入 Review → Plan2 → Edit2 → Review 循环
- [ ] 检查分支节点是否正确高亮
- [ ] 验证日志中是否显示 "Review Edit Plan" 和 "Roadmap Edit"

### 3. 状态持久性测试
- [ ] 页面刷新后 `currentStep` 和 `editSource` 是否正确恢复
- [ ] 分支状态是否正确显示

### 4. UI/UX 测试
- [ ] 编辑蒙版是否简洁清晰
- [ ] 分支节点是否易于理解
- [ ] Human Review 面板是否正常工作
- [ ] 移动端响应式布局是否正常

---

## 文件变更清单

### 新建文件 (1个)
- `frontend-next/components/task/workflow-topology.tsx` (860+ 行)

### 修改文件 (4个)
- `frontend-next/components/task/execution-log-timeline.tsx` (+20 行注释和配置)
- `frontend-next/components/task/roadmap-tree/RoadmapTree.tsx` (-250 行简化)
- `frontend-next/lib/api/websocket.ts` (+1 行类型定义)
- `frontend-next/app/(app)/tasks/[taskId]/page.tsx` (+10 行状态管理和组件替换)

### 保留文件
- `frontend-next/components/task/workflow-progress-enhanced.tsx` (保留作为备份)
- `frontend-next/components/task/horizontal-workflow-stepper.tsx` (保留作为备份)

---

## 后续优化建议

### 1. 状态持久化
考虑将 `editSource` 保存到任务状态中，避免页面刷新后丢失：
```typescript
// 后端 Task 模型添加字段
edit_source: Optional[str] = Field(None, description="validation_failed 或 human_review")
```

### 2. 分支历史记录
在执行日志中明确标记分支循环次数：
```
[Validation Branch #1] → Plan1 → Edit1 → Validate
[Validation Branch #2] → Plan1 → Edit1 → Validate
```

### 3. 动画优化
为分支激活/切换添加平滑过渡动画。

### 4. 错误恢复
如果 `edit_source` 缺失，添加降级逻辑：
- 根据最近的执行日志推断当前分支
- 或显示警告提示用户刷新页面

---

## 兼容性说明

- **向后兼容**: 旧的 `WorkflowProgressEnhanced` 组件保留，可通过 import 切换回旧版
- **后端要求**: 需要后端发送 `edit_source` 字段（已在 `ValidationEditPlanRunner` 和 `EditPlanRunner` 中实现）
- **浏览器支持**: 使用标准 React/TypeScript，无特殊浏览器要求

---

## 总结

✅ **所有计划任务已完成**

本次重构成功实现了：
1. 真实反映后端工作流的拓扑图可视化
2. 清晰区分验证分支和审核分支
3. 简化编辑蒙版，提升用户体验
4. 完整的状态追踪和实时同步

前端现在可以准确展示路线图生成过程中的所有状态，包括自动修复循环（验证分支）和用户反馈循环（审核分支）。

