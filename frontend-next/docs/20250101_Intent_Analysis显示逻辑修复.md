# Intent Analysis 显示逻辑修复

## 问题描述

**问题现象：**
任务详情页中 `intent_analysis` 已经完成，前端也成功获取到数据，但 "Learning Path Overview" 标题下方没有显示 Intent Analysis 卡片，导致页面看起来是空的。

**根本原因：**
前端的 `shouldShowIntentCard` 函数逻辑错误，明确排除了 `intent_analysis` 步骤本身。当后端完成 intent_analysis 并设置 `current_step="intent_analysis"` 时，前端虽然有数据，但因为当前步骤不在允许显示的列表中而不显示卡片。

## 问题分析

### 数据流程

```
后端 intent_analysis 完成
  ↓
设置 current_step="intent_analysis"
  ↓
前端获取到 intentAnalysis 数据 ✅
  ↓
shouldShowIntentCard(currentStep, intentAnalysis) 检查
  ↓
currentStep = "intent_analysis"
  ↓
"intent_analysis" 不在 stepsAfterIntent 列表中 ❌
  ↓
返回 false - 不显示卡片
  ↓
用户看到空白的 Learning Path Overview
```

### 原始代码逻辑

```typescript
function shouldShowIntentCard(currentStep, intentAnalysis) {
  if (!intentAnalysis || !currentStep) return false;
  
  // ❌ 注释说"不包括 intent_analysis 阶段本身"
  const stepsAfterIntent = [
    'curriculum_design',  // 从这里开始
    'structure_validation',
    // ... 其他步骤
  ];
  
  // "intent_analysis" 不在列表中，返回 false
  return stepsAfterIntent.includes(currentStep);
}
```

### 错误假设

原始代码的注释表明了一个错误假设：

> "不包括 intent_analysis 阶段本身，因为此时数据可能还未完成"

但实际情况是：
- 后端在完成 intent_analysis 后才设置 `current_step="intent_analysis"`
- 此时数据已经保存到数据库
- 前端已经成功获取到 `intentAnalysis` 数据
- **数据完整且可以显示**

## 解决方案

### 修复逻辑

修改 `shouldShowIntentCard` 函数，在列表中包含 `'intent_analysis'` 步骤：

```typescript
function shouldShowIntentCard(currentStep, intentAnalysis) {
  // 必须有数据才显示
  if (!intentAnalysis || !currentStep) return false;
  
  // ✅ intent_analysis 完成后（包括 intent_analysis 步骤本身）的任何阶段都显示
  // 只要数据存在，就说明 intent_analysis 已经完成，可以显示
  const stepsWithIntent = [
    'intent_analysis',  // ✅ 新增：包含 intent_analysis 步骤本身
    'curriculum_design',
    'framework_generation',
    // ... 其他步骤
  ];
  
  return stepsWithIntent.includes(currentStep);
}
```

### 修复后的数据流程

```
后端 intent_analysis 完成
  ↓
设置 current_step="intent_analysis"
  ↓
前端获取到 intentAnalysis 数据 ✅
  ↓
shouldShowIntentCard(currentStep, intentAnalysis) 检查
  ↓
currentStep = "intent_analysis"
  ↓
"intent_analysis" 在 stepsWithIntent 列表中 ✅
  ↓
返回 true - 显示卡片 ✅
  ↓
用户看到完整的 Intent Analysis 内容
```

## 修改文件

- `frontend-next/components/task/core-display-area.tsx`
  - Line 100-124: 修复 `shouldShowIntentCard` 函数逻辑

## 影响范围

### 受影响的功能
- ✅ 任务详情页 - Intent Analysis 卡片显示
- ✅ Learning Path Overview 区域

### 显示内容
Intent Analysis 卡片包含：
- Learning Goal（学习目标）
- Key Technologies（关键技术栈）
- Difficulty Level（难度等级）
- Estimated Duration（预计时长）
- Estimated Hours/Week（每周学习时长）

## 其他相关逻辑

### 加载状态判断（无需修改）

```typescript
const isLoading = !['completed', 'failed'].includes(status) &&
  currentStep && 
  !['completed', 'failed'].includes(currentStep) &&
  !intentAnalysis &&    // 数据不存在时才显示骨架
  !showIntentCard &&    // 修复后，有数据时会返回 true
  !showRoadmap;
```

修复后的逻辑：
- 当 `intent_analysis` 完成且有数据时，`showIntentCard = true`
- 因此 `isLoading = false`，不会显示骨架加载
- 而是正常渲染 Intent Analysis 卡片

## 测试验证

**验证步骤：**
1. 创建新任务，等待 intent_analysis 完成
2. 刷新任务详情页
3. 检查 "Learning Path Overview" 下是否显示 Intent Analysis 卡片
4. 验证卡片内容是否完整（学习目标、技术栈、难度等）

**预期结果：**
- ✅ Intent Analysis 卡片正常显示
- ✅ 包含完整的分析信息
- ✅ 可以正常折叠/展开
- ✅ 不再出现空白的 Learning Path Overview

## 历史背景

这个 bug 可能是早期开发时的保守设计导致的：
- 担心在 `intent_analysis` 步骤时数据还未完成
- 因此选择排除这个步骤，只在"之后"的步骤显示
- 但实际上后端的状态设置是准确的，数据存在即可显示

## 改进建议

**更简洁的逻辑：**

可以进一步简化判断逻辑，只要数据存在就显示，无需检查步骤列表：

```typescript
function shouldShowIntentCard(currentStep, intentAnalysis) {
  // 只要有数据且不是初始状态，就显示
  return !!intentAnalysis && !!currentStep && currentStep !== 'init' && currentStep !== 'queued';
}
```

但考虑到代码稳定性和可维护性，暂时保持当前的白名单方式，确保明确控制显示时机。

