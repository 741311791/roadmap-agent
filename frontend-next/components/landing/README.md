# Landing Page Components

## 概述

这些组件构成了 Fast Learning 的全新落地页，采用 Motion 动画库和 Magic UI 设计风格。

## 组件列表

### 1. Navigation
**文件**: `navigation.tsx`

响应式导航栏，支持桌面和移动端。

```tsx
import { Navigation } from '@/components/landing';

<Navigation />
```

### 2. HeroSection
**文件**: `hero-section.tsx`

Hero 区域，包含主标题、工作流动画和订阅表单。

```tsx
import { HeroSection } from '@/components/landing';

<HeroSection />
```

### 3. WorkflowAnimation
**文件**: `workflow-animation.tsx`

4 步工作流循环动画组件（内部使用，通常不单独导出）。

### 4. FeaturesSection
**文件**: `features-section.tsx`

Features 区域，展示 4 个核心功能和对应卡片。

```tsx
import { FeaturesSection } from '@/components/landing';

<FeaturesSection />
```

### 5. Feature Cards
**文件**: `feature-cards.tsx`

4 个精美展示卡片：
- IntentAnalysisCard
- RoadmapCard
- QuizCard
- ResourceCard

```tsx
import { IntentAnalysisCard, RoadmapCard } from '@/components/landing';

<IntentAnalysisCard />
```

### 6. AgentsGrid
**文件**: `agents-grid.tsx`

8 个 AI Agent 网格展示。

```tsx
import { AgentsGrid } from '@/components/landing';

<AgentsGrid />
```

### 7. TestimonialsSection
**文件**: `testimonials.tsx`

用户评价自动滚动区域。

```tsx
import { TestimonialsSection } from '@/components/landing';

<TestimonialsSection />
```

### 8. CTASection
**文件**: `cta-section.tsx`

行动号召区域，包含订阅表单。

```tsx
import { CTASection } from '@/components/landing';

<CTASection />
```

### 9. Footer
**文件**: `footer.tsx`

页脚组件。

```tsx
import { Footer } from '@/components/landing';

<Footer />
```

## 完整示例

```tsx
import {
  Navigation,
  HeroSection,
  FeaturesSection,
  AgentsGrid,
  TestimonialsSection,
  CTASection,
  Footer,
} from '@/components/landing';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-stone-50">
      <Navigation />
      <HeroSection />
      <FeaturesSection />
      <AgentsGrid />
      <TestimonialsSection />
      <CTASection />
      <Footer />
    </div>
  );
}
```

## 设计系统

### 颜色
- **Primary**: sage-600 (#7d8f7d)
- **Background**: stone-50 (#fafaf9)
- **Text**: stone-900 (#1c1917)
- **Accent**: sage-400 (#a8b8a8)

### 字体
- **Headings**: font-serif
- **Body**: font-sans

### 间距
- **Section padding**: py-24 px-6
- **Container**: max-w-7xl mx-auto

## 动画配置

所有动画使用 Motion (framer-motion 的新版本)：

```tsx
import { motion } from 'motion/react';
```

默认 transition：
- duration: 0.5-0.8s
- ease: "easeInOut"

## 响应式断点

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 依赖

必需的包：
- `motion` - 动画库
- `@tabler/icons-react` - 图标库
- `lucide-react` - 图标库
- shadcn/ui 组件

## 注意事项

1. 所有组件使用 `'use client'` 指令
2. Logo 路径：`/logo/svg_word.svg` 和 `/logo/svg_noword.svg`
3. 表单提交逻辑需要集成实际 API
4. 所有文本必须是英文

