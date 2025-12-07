# 🌍 中英文翻译修复 - `/new` 页面

**日期**: 2025-12-06  
**页面**: `/app/(app)/new/page.tsx`  
**状态**: ✅ 完成

---

## 📋 修改内容

### 1. 引导卡片文本 ✅

**位置**: Profile Guidance Card (第 241-265 行)

#### Before (❌ 中文)
```tsx
<p className="text-sm font-medium text-foreground">
  完善你的学习画像
</p>
<p className="text-xs text-muted-foreground">
  填写个人画像可以帮助我们生成更加个性化的学习路线图
</p>
<Button variant="outline" size="sm">
  填写画像
</Button>
```

#### After (✅ 英文)
```tsx
<p className="text-sm font-medium text-foreground">
  Complete your learning profile
</p>
<p className="text-xs text-muted-foreground">
  A complete profile helps us generate more personalized learning roadmaps
</p>
<Button variant="outline" size="sm">
  Complete Profile
</Button>
```

---

### 2. 内容偏好选项 ✅

**位置**: Content Options (第 39-44 行)

#### Before (❌ 混合中英文)
```tsx
{ id: 'visual', label: 'Visual', labelZh: '视觉类', icon: '🎬', desc: '视频教程、图解、演示' },
{ id: 'text', label: 'Text', labelZh: '文本类', icon: '📚', desc: '文档、文章、书籍' },
{ id: 'audio', label: 'Audio', labelZh: '音频类', icon: '🎧', desc: '播客、有声内容' },
{ id: 'hands_on', label: 'Hands-on', labelZh: '实操类', icon: '🛠️', desc: '互动练习、项目实战' },
```

#### After (✅ 纯英文)
```tsx
{ id: 'visual', label: 'Visual', icon: '🎬', desc: 'Videos, diagrams, demonstrations' },
{ id: 'text', label: 'Text', icon: '📚', desc: 'Documentation, articles, books' },
{ id: 'audio', label: 'Audio', icon: '🎧', desc: 'Podcasts, audio content' },
{ id: 'hands_on', label: 'Hands-on', icon: '🛠️', desc: 'Interactive exercises, projects' },
```

**变更**:
- 移除了 `labelZh` 字段
- 将描述从中文翻译为英文
- 现在页面上显示 "Visual", "Text", "Audio", "Hands-on"

---

### 3. 生成进度状态 ✅

**位置**: Step Progress (第 52-65 行)

#### Before (❌ 中文)
```tsx
const stepProgress = {
  'queued': { progress: 10, status: '任务已排队...' },
  'intent_analysis': { progress: 20, status: '分析学习目标...' },
  'curriculum_design': { progress: 40, status: '设计课程结构...' },
  'structure_validation': { progress: 50, status: '验证路线图结构...' },
  'human_review': { progress: 55, status: '等待人工审核...' },
  'content_generation': { progress: 70, status: '生成学习内容...' },
  'tutorial_generation': { progress: 75, status: '生成教程内容...' },
  'resource_recommendation': { progress: 85, status: '推荐学习资源...' },
  'quiz_generation': { progress: 90, status: '生成测验题目...' },
  'finalizing': { progress: 95, status: '完成处理...' },
  'completed': { progress: 100, status: '生成完成！' },
};
```

#### After (✅ 英文)
```tsx
const stepProgress = {
  'queued': { progress: 10, status: 'Task queued...' },
  'intent_analysis': { progress: 20, status: 'Analyzing learning goals...' },
  'curriculum_design': { progress: 40, status: 'Designing curriculum structure...' },
  'structure_validation': { progress: 50, status: 'Validating roadmap structure...' },
  'human_review': { progress: 55, status: 'Awaiting human review...' },
  'content_generation': { progress: 70, status: 'Generating learning content...' },
  'tutorial_generation': { progress: 75, status: 'Generating tutorial content...' },
  'resource_recommendation': { progress: 85, status: 'Recommending resources...' },
  'quiz_generation': { progress: 90, status: 'Generating quiz questions...' },
  'finalizing': { progress: 95, status: 'Finalizing...' },
  'completed': { progress: 100, status: 'Generation complete!' },
};
```

---

### 4. 生成页面文案 ✅

**位置**: Generating Step (第 472-532 行)

#### 错误状态 (Error State)

**Before (❌)**:
```tsx
<h2>生成失败</h2>
<Button>返回修改</Button>
```

**After (✅)**:
```tsx
<h2>Generation Failed</h2>
<Button>Go Back</Button>
```

#### 完成状态 (Success State)

**Before (❌)**:
```tsx
<h2>路线图生成完成！</h2>
<p>正在跳转到您的学习路线图...</p>
```

**After (✅)**:
```tsx
<h2>Roadmap Generated!</h2>
<p>Redirecting to your learning roadmap...</p>
```

#### 生成中状态 (Loading State)

**Before (❌)**:
```tsx
<h2>正在生成您的学习路线图</h2>
<p>AI 智能体正在协同工作,为您打造个性化的学习课程...</p>
<p>连接方式: {connectionType === 'ws' ? 'WebSocket' : '轮询'}</p>
```

**After (✅)**:
```tsx
<h2>Generating Your Learning Roadmap</h2>
<p>AI agents are collaborating to craft your personalized curriculum...</p>
<p>Connection: {connectionType === 'ws' ? 'WebSocket' : 'Polling'}</p>
```

---

### 5. 代码注释 ✅

**Before (❌)**:
```tsx
// 步骤到进度的映射
// WebSocket Hook (只在有 taskId 时启动)
// 计算当前显示的进度和状态
```

**After (✅)**:
```tsx
// Step to progress mapping
// WebSocket Hook (only starts when taskId is available)
// Calculate current progress and status
```

---

### 6. 默认值 ✅

**Before (❌)**:
```tsx
motivation: formData.motivation || '个人兴趣',
career_background: formData.careerBackground || '未指定',
```

**After (✅)**:
```tsx
motivation: formData.motivation || 'Personal interest',
career_background: formData.careerBackground || 'Not specified',
```

---

## 📊 统计

| 类别 | 修改数量 |
|------|---------|
| UI 文本 | 11 处 |
| 代码注释 | 4 处 |
| 默认值 | 2 处 |
| 数据结构 | 2 处 (移除 labelZh, 翻译 desc) |
| **总计** | **19 处** |

---

## 🎯 用户界面变化

### 引导卡片
- "完善你的学习画像" → "Complete your learning profile"
- "填写个人画像可以帮助我们生成更加个性化的学习路线图" → "A complete profile helps us generate more personalized learning roadmaps"
- "填写画像" 按钮 → "Complete Profile" 按钮

### 内容偏好选择
- "视觉类" → "Visual"
- "文本类" → "Text"
- "音频类" → "Audio"
- "实操类" → "Hands-on"

### 生成进度
所有进度状态消息都改为英文，例如：
- "任务已排队..." → "Task queued..."
- "分析学习目标..." → "Analyzing learning goals..."
- "生成完成！" → "Generation complete!"

### 生成页面
- "正在生成您的学习路线图" → "Generating Your Learning Roadmap"
- "路线图生成完成！" → "Roadmap Generated!"
- "生成失败" → "Generation Failed"

---

## ✅ 验证

### TypeScript 类型检查
```bash
npm run type-check
```
**结果**: ✅ 通过，无错误

### 测试步骤

1. 访问 http://localhost:3000/new
2. 检查引导卡片文本
3. 检查内容偏好选项标签
4. 开始生成路线图，观察进度文本
5. 所有文本应该都是英文

---

## 📝 注意事项

### 已保持原样的部分
- ✅ UI 布局和样式未改变
- ✅ 功能逻辑未改变
- ✅ 表单字段和选项未改变
- ✅ API 请求格式未改变

### 数据结构变更
- `contentOptions` 数组中移除了 `labelZh` 字段
- 使用 `label` 字段直接显示英文标签
- 描述 `desc` 字段翻译为英文

---

## 🚀 部署

修改已完成，无需额外配置。刷新页面即可看到英文文本。

---

**修改完成** ✅  
**类型检查通过** ✅  
**所有文本已国际化** ✅







