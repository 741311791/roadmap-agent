# Structure Validation日志展示修复

## 问题描述
前端任务详情页中，Execution Logs模块缺少了structure_validation阶段的日志展示。

## 问题分析
`ExecutionLogTimeline`组件虽然在步骤配置中包含了`structure_validation`，但是没有集成`LogCardRouter`来渲染特殊的验证结果卡片（`ValidationResultCard`）。这导致验证结果只显示为普通的文本日志，而不是更友好的卡片形式。

## 修复内容

### 1. 集成LogCardRouter到ExecutionLogTimeline
**文件**: `frontend-next/components/task/execution-log-timeline.tsx`

- 导入`LogCardRouter`组件
- 修改`LogItem`组件，添加对特殊日志卡片的支持：
  - 首先尝试使用`LogCardRouter`渲染特殊卡片
  - 如果返回null，则渲染默认的日志项

```typescript
// 尝试渲染特殊的日志卡片（如验证结果卡片）
const specialCard = LogCardRouter({ log });

// 如果有特殊卡片，渲染特殊卡片
if (specialCard) {
  return (
    <div className="px-4 py-3">
      {specialCard}
    </div>
  );
}
```

### 2. 导出LogCardRouter
**文件**: `frontend-next/components/task/log-cards/index.tsx`

添加`LogCardRouter`函数的导出，使其可以被其他组件使用。

### 3. 修复ValidationResultCard数据结构
**文件**: `frontend-next/components/task/log-cards/validation-result-card.tsx`

修复了与后端数据结构不匹配的问题：

#### 验证通过 (validation_passed)
- **检查项**: 支持对象格式（包含name、description、passed字段）和字符串格式
- **结构统计**: 显示stages、modules、concepts的数量（来自`structure_summary`）
- **问题统计**: 显示warnings和suggestions的数量（来自`issues_summary`）

#### 验证失败 (validation_failed)
- **问题统计**: 显示critical、warnings、suggestions的分类统计（来自`issues_breakdown`）
- **关键问题列表**: 
  - 显示问题位置（`issue.location`）
  - 显示问题描述（`issue.issue`）
  - 显示改进建议（`issue.suggestion`）

## 后端数据格式参考

### 验证通过日志结构
```typescript
{
  log_type: "validation_passed",
  overall_score: 85.5,
  structure_summary: {
    total_stages: 4,
    total_modules: 12,
    total_concepts: 48
  },
  checks_performed: [
    { name: "Dependency Validation", description: "...", passed: true },
    { name: "Difficulty Progression", description: "...", passed: true },
    // ...
  ],
  issues_summary: {
    warnings: 2,
    suggestions: 5,
    warning_details: [...]
  }
}
```

### 验证失败日志结构
```typescript
{
  log_type: "validation_failed",
  overall_score: 45.0,
  issues_breakdown: {
    critical: 3,
    warnings: 5,
    suggestions: 8
  },
  critical_issues: [
    {
      location: "Stage 2 > Module 3",
      issue: "Missing prerequisite concepts",
      suggestion: "Add prerequisite concepts before advanced topics"
    },
    // ...
  ]
}
```

## 效果
现在在任务详情页的Execution Logs模块中，structure_validation阶段的日志会以卡片形式展示：
- ✅ 验证通过：显示绿色卡片，包含检查项、结构统计和问题统计
- ❌ 验证失败：显示红色卡片，包含问题统计和详细的关键问题列表
- ℹ️ 验证跳过：显示灰色卡片，说明跳过原因

## 相关组件
- `ExecutionLogTimeline`: 执行日志时间轴主组件
- `LogCardRouter`: 日志卡片路由器，根据日志类型渲染对应的卡片
- `ValidationResultCard`: 验证结果卡片组件
- `ValidationRunner`: 后端验证执行器（负责记录验证日志）

## 测试建议
1. 创建一个新的学习路线图
2. 观察任务详情页的Execution Logs模块
3. 确认structure_validation阶段显示为卡片形式
4. 验证卡片内容与后端日志数据一致

