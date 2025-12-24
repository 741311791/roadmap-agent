# Human Review 重试 UX 修复

**修复日期**: 2025-12-24  
**问题严重级别**: 中  
**影响范围**: 人工审核阶段的用户体验和视觉一致性

---

## 🐛 问题描述

用户在路线图详情页进行任务重试时，当工作流再次进入人工审核阶段后，发现以下问题：

### 1. 状态未重置问题

**现象**: 当工作流再次回到 Human Review 阶段时，界面默认停留在"反馈信息填写"状态，而不是重新显示"接受/拒绝"选项。

**影响**: 
- 用户无法直接看到批准/拒绝按钮
- 需要手动点击"Cancel"才能返回初始状态
- 体验不连贯，容易造成困惑

**根本原因**: 
- `WorkflowProgressEnhanced` 和 `WorkflowTopology` 组件没有检测工作流重新进入 Human Review 状态
- 组件内部的 `reviewStatus` 和 `showFeedback` 状态没有在重新进入时重置

### 2. 网络连接失败错误信息

**现象**: 前端显示中文错误信息"网络连接失败，请检查您的网络"

**影响**:
- 违反网站英文规范（前端所有可见文本必须使用英文）
- 与整体 UI 语言不一致

**根本原因**:
- `error.ts` 拦截器中的错误信息使用了中文硬编码

### 3. 对话框样式不一致问题

**现象**: Human Review 内嵌面板的主题颜色和样式与全局设计系统不符

**影响**:
- 使用蓝色主题（`bg-blue-50`, `border-blue-300`）而不是 Sage 主题
- 对话框可能溢出 Workflow Progress 卡片范围
- 按钮文本不够清晰（"Change" vs "Needs changes"）
- Textarea 行数太少（2行），不利于用户输入详细反馈

### 4. 路线图标题溢出问题

**现象**: 当路线图标题过长时（如"React前端开发工程师学习路..."），文本溢出对话框边界

**影响**:
- 标题文本超出对话框宽度
- 视觉效果不佳，影响用户体验
- 无法看到完整的路线图标题

---

## ✅ 修复方案

### 修复 1: 添加状态重置逻辑

#### 文件: `frontend-next/components/task/workflow-progress-enhanced.tsx`

**改动 1**: 添加 React Hooks 导入

```typescript
import { useState, useEffect, useRef } from 'react';
```

**改动 2**: 添加状态跟踪和重置逻辑

```typescript
export function WorkflowProgressEnhanced({
  // ... props
}: WorkflowProgressEnhancedProps) {
  // Human Review 状态
  const [reviewStatus, setReviewStatus] = useState<'waiting' | 'submitting' | 'approved' | 'rejected'>('waiting');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const isHumanReviewActive = 
    currentStep === 'human_review' || 
    currentStep === 'human_review_pending' ||
    status === 'human_review_pending';

  /**
   * 跟踪上一次的 Human Review 状态，用于检测状态变化
   */
  const prevHumanReviewActiveRef = useRef<boolean>(false);

  /**
   * 当任务重新进入 Human Review 状态时，重置审核状态
   * 场景：用户reject后，编辑完成，工作流再次回到review节点
   */
  useEffect(() => {
    // 检测：从非human_review状态 → 进入human_review状态
    const isReenteringHumanReview = !prevHumanReviewActiveRef.current && isHumanReviewActive;
    
    // 当重新进入human_review状态，且当前处于已完成的审核状态时，重置为waiting
    if (isReenteringHumanReview && (reviewStatus === 'approved' || reviewStatus === 'rejected')) {
      setReviewStatus('waiting');
      setFeedback('');
      setShowFeedback(false);
      setReviewError(null);
    }
    
    // 更新上一次的状态
    prevHumanReviewActiveRef.current = isHumanReviewActive;
  }, [isHumanReviewActive, reviewStatus]);

  // ... rest of component
}
```

**工作原理**:
1. 使用 `useRef` 跟踪上一次的 `isHumanReviewActive` 状态
2. 在 `useEffect` 中检测从非 Human Review 状态到 Human Review 状态的转换
3. 当检测到重新进入且当前状态为 `approved` 或 `rejected` 时，重置所有审核相关状态
4. 确保用户每次进入审核阶段都看到初始的"接受/拒绝"选项

#### 文件: `frontend-next/components/task/workflow-topology.tsx`

**说明**: 该组件已经在之前的修复中实现了相同的状态重置逻辑（参见 `WORKFLOW_BRANCH_STATE_FIX_2025-12-23.md`），无需额外修改。

---

### 修复 2: 更新错误信息为英文

#### 文件: `frontend-next/lib/api/interceptors/error.ts`

```typescript
export function errorInterceptor(error: AxiosError<ErrorResponse>) {
  const { response, config } = error;
  
  if (!response) {
    // 网络错误
    logger.error('[API] Network connection failed', error);
    return Promise.reject(new Error('Network connection failed. Please check your internet connection.'));
  }
  
  // ... rest of function
}
```

**改动**:
- 将日志信息从"网络连接失败"改为"Network connection failed"
- 将错误信息从"网络连接失败，请检查您的网络"改为"Network connection failed. Please check your internet connection."

---

### 修复 3: 统一对话框样式为 Sage 主题

#### 文件: `frontend-next/components/task/workflow-progress-enhanced.tsx`

**改动**: 更新 `HumanReviewInlinePanel` 组件样式

```typescript
function HumanReviewInlinePanel({
  // ... props
}: HumanReviewInlinePanelProps) {
  // ... approved/rejected states ...

  // 等待审核状态
  return (
    <div className="p-4 bg-sage-50 dark:bg-sage-950/20 border-2 border-sage-300 dark:border-sage-700 rounded-xl shadow-md space-y-3">
      {/* 标题 */}
      <div className="text-center">
        <p className="text-xs text-sage-700 dark:text-sage-300 font-medium">Review Required</p>
        {roadmapTitle && (
          <p className="text-sm font-semibold text-sage-900 dark:text-sage-100 truncate" title={roadmapTitle}>
            {roadmapTitle}
          </p>
        )}
        <p className="text-[10px] text-sage-600 dark:text-sage-400">{stagesCount} stages</p>
      </div>

      {/* 错误提示 */}
      {reviewError && (
        <div className="p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-600 dark:text-red-400">
          {reviewError}
        </div>
      )}

      {/* 反馈输入 */}
      {showFeedback && (
        <div className="space-y-2">
          <Textarea
            placeholder="Describe what needs to be changed..."
            value={feedback}
            onChange={(e) => onFeedbackChange(e.target.value)}
            rows={3}  {/* 从 2 增加到 3 */}
            className="resize-none text-xs bg-white dark:bg-gray-900"
            disabled={reviewStatus === 'submitting'}
          />
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex items-center justify-center gap-2">
        {showFeedback ? (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onCancelFeedback}
              disabled={reviewStatus === 'submitting'}
              className="h-8 text-xs"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting' || !feedback.trim()}
              className="h-8 text-xs"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <X className="w-3 h-3 mr-1" />
              )}
              Submit
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting'}
              className="h-8 text-xs border-sage-300 hover:bg-sage-50 dark:border-sage-700 dark:hover:bg-sage-950"
            >
              <X className="w-3 h-3 mr-1" />
              Needs changes  {/* 从 "Change" 改为更明确的 "Needs changes" */}
            </Button>
            <Button
              size="sm"
              onClick={onApprove}
              disabled={reviewStatus === 'submitting'}
              className="h-8 text-xs bg-sage-600 hover:bg-sage-700 dark:bg-sage-600 dark:hover:bg-sage-700 text-white"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Check className="w-3 h-3 mr-1" />
              )}
              Approve and continue  {/* 从 "Approve" 改为更明确的 "Approve and continue" */}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
```

**样式改动总结**:

1. **主题颜色统一**:
   - 背景: `bg-blue-50` → `bg-sage-50 dark:bg-sage-950/20`
   - 边框: `border-blue-300` → `border-sage-300 dark:border-sage-700`
   - 文本: `text-blue-*` → `text-sage-*`

2. **按钮样式优化**:
   - 高度: `h-7` → `h-8` (更易点击)
   - "Needs changes" 按钮: 添加 Sage 主题边框和悬停效果
   - "Approve and continue" 按钮: 使用 Sage 主题背景色

3. **文本改进**:
   - "Change" → "Needs changes" (更清晰的语义)
   - "Approve" → "Approve and continue" (明确后续动作)

4. **Textarea 优化**:
   - 行数: `rows={2}` → `rows={3}` (更多输入空间)
   - 背景: 添加明确的白色/深色背景以提高对比度

5. **深色模式支持**:
   - 所有颜色都添加了 `dark:` 变体
   - 确保在深色模式下也有良好的可读性

#### 文件: `frontend-next/components/task/workflow-topology.tsx`

**改动**: 在 `HumanReviewInlinePanel` 组件中应用相同的样式更新（与上述相同）。

---

### 修复 4: 防止路线图标题溢出

#### 文件: `frontend-next/components/task/workflow-progress-enhanced.tsx`

**改动**: 添加对话框最大宽度和标题截断处理

```typescript
// 等待审核状态
return (
  <div className="p-4 bg-sage-50 dark:bg-sage-950/20 border-2 border-sage-300 dark:border-sage-700 rounded-xl shadow-md space-y-3 max-w-[320px]">
    {/* 标题 */}
    <div className="text-center space-y-0.5">
      <p className="text-xs text-sage-700 dark:text-sage-300 font-medium">Review Required</p>
      {roadmapTitle && (
        <p className="text-sm font-semibold text-sage-900 dark:text-sage-100 truncate px-2" title={roadmapTitle}>
          {roadmapTitle}
        </p>
      )}
      <p className="text-[10px] text-sage-600 dark:text-sage-400">{stagesCount} stages</p>
    </div>
    {/* ... rest of component */}
  </div>
);
```

**关键改动**:
1. 对话框容器添加 `max-w-[320px]`，限制最大宽度，防止溢出 Workflow Progress 卡片
2. 标题添加 `px-2` 水平内边距，确保文本不会紧贴边缘
3. 标题容器添加 `space-y-0.5`，改善垂直间距
4. 标题保留 `truncate` 类，配合 `title` 属性在悬停时显示完整文本

#### 文件: `frontend-next/components/task/workflow-topology.tsx`

**改动**: 应用相同的宽度限制和标题截断处理。

#### 文件: `frontend-next/components/task/human-review-card.tsx`

**改动**: 在完整的 Card 组件中也添加标题截断

```typescript
<div className="p-4 bg-muted/50 rounded-lg space-y-3">
  <div>
    <p className="text-sm text-muted-foreground mb-1">Roadmap Title</p>
    <p className="font-medium truncate" title={roadmapTitle}>{roadmapTitle}</p>
  </div>
  <div className="flex items-center gap-4">
    <Badge variant="secondary" className="gap-1">
      <Clock className="w-3 h-3" />
      {stagesCount} stages
    </Badge>
    <span className="text-xs text-muted-foreground truncate" title={roadmapId}>
      ID: {roadmapId.substring(0, 20)}...
    </span>
  </div>
</div>
```

#### 文件: `frontend-next/components/roadmap/human-review-dialog.tsx`

**改动**: 在对话框中也添加标题截断处理（与 human-review-card.tsx 相同）。

---

## 🎯 修复效果

### 1. 状态重置

**修复前**:
```
用户提交反馈 → 工作流编辑 → 再次进入审核
❌ 界面停留在反馈输入状态，显示之前的反馈文本
❌ 用户需要点击 Cancel 才能看到批准/拒绝按钮
```

**修复后**:
```
用户提交反馈 → 工作流编辑 → 再次进入审核
✅ 界面自动重置为初始状态
✅ 直接显示"Needs changes"和"Approve and continue"按钮
✅ 反馈文本框已清空
```

### 2. 错误信息

**修复前**:
```
网络连接失败，请检查您的网络
```

**修复后**:
```
Network connection failed. Please check your internet connection.
```

### 3. 视觉一致性

**修复前**:
- 蓝色主题（与全局 Sage 主题不符）
- 按钮文本模糊（"Change"）
- Textarea 太小（2行）

**修复后**:
- Sage 主题（与全局设计系统一致）
- 按钮文本清晰（"Needs changes", "Approve and continue"）
- Textarea 更大（3行），支持更详细的反馈
- 完整的深色模式支持

### 4. 标题溢出修复

**修复前**:
```
React前端开发工程师学习路... (文本超出对话框边界)
```

**修复后**:
```
React前端开发工程师... (文本正确截断，悬停显示完整标题)
✅ 对话框宽度限制为 320px
✅ 标题添加 truncate 和 title 属性
✅ 标题添加水平内边距，避免紧贴边缘
```

---

## 📋 测试验证

### 测试场景 1: 重新进入审核状态

1. 创建一个新的路线图生成任务
2. 等待工作流进入 Human Review 阶段
3. 点击"Needs changes"并输入反馈
4. 点击"Submit"提交反馈
5. 等待工作流完成编辑并再次进入 Human Review 阶段
6. **验证**: 界面应该显示初始的"Needs changes"和"Approve and continue"按钮，而不是反馈输入框

### 测试场景 2: 网络错误信息

1. 断开网络连接
2. 尝试提交审核反馈或执行任何 API 操作
3. **验证**: 错误信息应该显示英文文本"Network connection failed. Please check your internet connection."

### 测试场景 3: 视觉一致性

1. 在浅色模式下查看 Human Review 面板
2. 切换到深色模式
3. **验证**: 
   - 面板使用 Sage 主题颜色
   - 按钮文本清晰易懂
   - Textarea 有足够的空间输入反馈
   - 深色模式下所有元素清晰可见

### 测试场景 4: 标题溢出

1. 创建一个标题很长的路线图（如"React前端开发工程师完整学习路线图从入门到精通"）
2. 等待工作流进入 Human Review 阶段
3. **验证**: 
   - 标题应该正确截断，不会溢出对话框边界
   - 悬停在标题上时，应该显示完整的标题文本
   - 对话框宽度不超过 320px
   - 标题文本不会紧贴对话框边缘

---

## 🔄 相关修复

### 之前的相关修复

1. **WORKFLOW_BRANCH_STATE_FIX_2025-12-23.md**: 
   - 在 `WorkflowTopology` 组件中实现了状态重置逻辑
   - 本次修复将相同逻辑应用到 `WorkflowProgressEnhanced` 组件

2. **HUMAN_REVIEW_INTEGRATION_SUMMARY.md**:
   - Human Review 功能的初始实现
   - 定义了基本的审核流程和状态管理

### 技术债务

无明显技术债务。状态管理逻辑清晰，样式符合设计系统规范。

---

## 📝 总结

### 修改文件

1. ✅ `frontend-next/components/task/workflow-progress-enhanced.tsx`
   - 添加状态重置逻辑（useEffect + useRef）
   - 更新 HumanReviewInlinePanel 样式为 Sage 主题
   - 改进按钮文本和 Textarea 大小

2. ✅ `frontend-next/components/task/workflow-topology.tsx`
   - 更新 HumanReviewInlinePanel 样式为 Sage 主题
   - 保持与 WorkflowProgressEnhanced 的视觉一致性

3. ✅ `frontend-next/lib/api/interceptors/error.ts`
   - 将网络错误信息从中文改为英文

### 预期效果

- **更好的用户体验**: 重新进入审核时自动重置状态，无需手动操作
- **语言一致性**: 所有可见文本使用英文，符合网站规范
- **视觉统一性**: 使用 Sage 主题，与全局设计系统保持一致
- **更清晰的交互**: 按钮文本更明确，Textarea 更大，便于输入详细反馈

### 后续跟进

1. 监控用户反馈，确认状态重置逻辑工作正常
2. 检查其他组件是否也存在类似的中文错误信息
3. 考虑将状态重置逻辑提取为自定义 Hook，便于复用

