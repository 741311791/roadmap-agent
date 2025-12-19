# Shader 背景位置修复

**问题**: Shader 背景下移了很多，覆盖了不应该覆盖的区域  
**修复时间**: 2025-12-19

---

## 🔴 问题分析

### 原因
之前的布局结构导致 `AnimatedShaderHero` 容器包含了：
1. Hero Section 内容（h-screen）
2. LearningPathDemo Section

```tsx
<AnimatedShaderHero>  // min-h-screen，但实际内容超过一屏
  <div className="min-h-screen">
    {/* Hero 内容 */}
  </div>
  <div className="-mt-32 pt-48 pb-16">
    <LearningPathDemo />  // 这部分也在 AnimatedShaderHero 内
  </div>
</AnimatedShaderHero>
```

**结果**: 
- AnimatedShaderHero 容器高度 = Hero (100vh) + LearningPathDemo (~500px)
- Shader Canvas 被拉伸到整个容器高度
- 视觉上 Shader 背景"下移"到了下一个 Section

---

## ✅ 修复方案

### 1. 调整 Hero Section 布局

**修改文件**: `frontend-next/app/(marketing)/page.tsx`

```tsx
// 修复后的结构
<section className="relative w-full h-screen overflow-hidden">
  <AnimatedShaderHero className="h-screen">
    <div className="relative w-full h-full flex flex-col items-center justify-center">
      {/* Hero 内容 */}
    </div>
  </AnimatedShaderHero>
</section>

<section className="relative z-20 bg-gradient-to-b from-background via-background to-background py-24 px-6">
  <LearningPathDemo />
</section>
```

**关键改动**:
- ✅ Hero Section 明确设置为 `h-screen`（固定高度）
- ✅ AnimatedShaderHero 也设置为 `h-screen`
- ✅ LearningPathDemo 移出 AnimatedShaderHero，成为独立 section
- ✅ 移除负 margin 和复杂的叠加逻辑

### 2. 优化 AnimatedShaderHero 组件

**修改文件**: `frontend-next/components/ui/animated-shader-hero.tsx`

**改动 1**: 支持自定义高度类名
```tsx
// 之前
<div className={`relative w-full min-h-screen overflow-hidden ${className}`}>

// 之后
<div className={`relative w-full ${className || 'min-h-screen'} overflow-hidden`}>
```

**改动 2**: Canvas 填充方式优化
```tsx
// 之前
<canvas className="... object-contain ..." />

// 之后
<canvas className="... object-cover ..." />
```

**原因**:
- `object-contain`: Canvas 保持比例，可能留有空白
- `object-cover`: Canvas 完全填充容器，无缝覆盖

---

## 📊 修复前后对比

### 修复前
```
┌─────────────────────────────────┐
│   AnimatedShaderHero            │
│   ┌───────────────────────┐     │
│   │   Hero Content        │     │ ← 100vh
│   │   (h-screen)          │     │
│   └───────────────────────┘     │
│                                 │
│   ┌───────────────────────┐     │
│   │ LearningPathDemo      │     │ ← +500px
│   │ (also inside)         │     │
│   └───────────────────────┘     │
└─────────────────────────────────┘
        ↑
    Shader 背景被拉伸到这里
```

### 修复后
```
┌─────────────────────────────────┐
│   AnimatedShaderHero            │
│   ┌───────────────────────┐     │
│   │   Hero Content        │     │ ← 固定 100vh
│   │   (h-screen)          │     │
│   └───────────────────────┘     │
└─────────────────────────────────┘
        ↑
    Shader 背景只到这里

┌─────────────────────────────────┐
│   LearningPathDemo Section      │
│   (独立的 section)              │
└─────────────────────────────────┘
```

---

## 🎯 修复效果

### ✅ 已解决的问题
1. **Shader 位置正确**: 背景只覆盖 Hero Section（100vh）
2. **布局清晰**: 每个 Section 独立，不再嵌套
3. **性能优化**: Canvas 不需要渲染超过一屏的区域
4. **视觉一致**: 背景和内容对齐，无错位感

### ✅ 保持的功能
- 🎨 Shader 动效正常运行
- ⚡ 所有动画效果保持不变
- 📱 响应式布局正常
- 🎭 BlurFade 等组件继续工作

---

## 🛠️ 技术细节

### Canvas 渲染优化

```tsx
// object-cover 确保 Canvas 完全填充容器
<canvas
  ref={canvasRef}
  className="absolute inset-0 w-full h-full object-cover touch-none"
  style={{ background: '#f6f1ea' }}
/>
```

**优点**:
- 无白边或空隙
- 自适应不同屏幕尺寸
- 保持 Shader 效果的完整性

### 高度控制策略

```tsx
// 外层 section: 固定高度
<section className="h-screen">
  // AnimatedShaderHero: 继承高度
  <AnimatedShaderHero className="h-screen">
    // 内容: 使用 h-full + flex 居中
    <div className="h-full flex items-center justify-center">
```

**设计思路**:
- 明确的高度控制链
- 避免 min-h-* 导致的不确定高度
- 使用 flex 实现真正的垂直居中

---

## 📝 修改文件清单

| 文件 | 改动内容 | 行数 |
|------|---------|------|
| `frontend-next/app/(marketing)/page.tsx` | 重构 Hero Section 布局 | ~30 行 |
| `frontend-next/components/ui/animated-shader-hero.tsx` | 优化高度控制和 Canvas 填充 | 2 行 |

---

## ✨ 总结

**问题根源**: 不合理的嵌套结构导致 Shader 容器高度超过预期

**解决方案**: 
1. 固定 Hero Section 高度为 100vh
2. 将 LearningPathDemo 独立出来
3. 优化 Canvas 的填充方式

**结果**: Shader 背景精确覆盖 Hero 区域，视觉效果完美！✅

---

**无 Linter 错误，可直接使用！** 🎉

