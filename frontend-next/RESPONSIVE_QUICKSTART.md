# 响应式设计快速开始指南

> 5分钟快速上手响应式开发

---

## 🚀 立即开始

### 1. 使用响应式 Hooks

```tsx
'use client';

import { useIsMobile, useIsDesktop, useBreakpoint } from '@/lib/hooks';

export function MyComponent() {
  // 方式1：简单判断
  const isMobile = useIsMobile();  // < 768px
  const isDesktop = useIsDesktop(); // >= 1024px

  // 方式2：详细信息
  const { width, height, currentBreakpoint } = useBreakpoint();

  return (
    <div>
      {isMobile ? <MobileView /> : <DesktopView />}
    </div>
  );
}
```

---

### 2. 使用预定义工具类名

```tsx
import { 
  containerClasses, 
  gridClasses, 
  typographyClasses 
} from '@/lib/utils/responsive';

export function MyPage() {
  return (
    // 响应式容器（自动居中和padding）
    <div className={containerClasses.content}>
      
      {/* 响应式标题 */}
      <h1 className={typographyClasses.h1}>
        My Page Title
      </h1>

      {/* 响应式卡片网格（1列 → 2列 → 3列 → 4列）*/}
      <div className={gridClasses.cards}>
        {items.map(item => <Card key={item.id} {...item} />)}
      </div>
    </div>
  );
}
```

---

### 3. 使用响应式组件

#### 对话框
```tsx
import { 
  ResponsiveDialog, 
  ResponsiveDialogContent,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from '@/components/common';

<ResponsiveDialog open={open} onOpenChange={setOpen}>
  <ResponsiveDialogContent maxWidth="lg">
    <ResponsiveDialogHeader>
      <ResponsiveDialogTitle>Dialog Title</ResponsiveDialogTitle>
    </ResponsiveDialogHeader>
    <div>Content here</div>
  </ResponsiveDialogContent>
</ResponsiveDialog>

// 移动端：全屏 Sheet（从底部弹出）
// 桌面端：居中 Dialog
```

#### 表格
```tsx
import { ResponsiveTable } from '@/components/common';

<ResponsiveTable
  data={tasks}
  columns={[
    { header: 'Title', accessorKey: 'title' },
    { header: 'Status', cell: (item) => <Badge>{item.status}</Badge> },
  ]}
  renderMobileCard={(item) => (
    <Card>
      <h3>{item.title}</h3>
      <Badge>{item.status}</Badge>
    </Card>
  )}
  getRowKey={(item) => item.id}
/>

// 移动端：卡片列表
// 桌面端：标准表格
```

#### 侧边栏
```tsx
import { ResponsiveSidebar } from '@/components/common';

<ResponsiveSidebar side="left" width="w-64">
  <nav>Navigation Links</nav>
</ResponsiveSidebar>

// 移动端：Sheet（抽屉）
// 桌面端：固定侧边栏
```

---

## 💡 常用模式

### 1. 移动端优先的 Tailwind 类名

```tsx
// ✅ 正确：从小屏开始，逐步增强
<div className="p-4 md:p-6 lg:p-8 xl:p-10">
  <h1 className="text-2xl md:text-3xl lg:text-4xl">Title</h1>
</div>

// ❌ 错误：从大屏开始
<div className="p-10 md:p-6 sm:p-4">
  <h1 className="text-4xl md:text-3xl sm:text-2xl">Title</h1>
</div>
```

### 2. 响应式网格

```tsx
// 卡片网格（自动适应列数）
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {items.map(item => <Card key={item.id} />)}
</div>

// 侧边栏布局
<div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
  <main>Main Content</main>
  <aside>Sidebar</aside>
</div>
```

### 3. 响应式按钮

```tsx
// 移动端全宽，桌面端自适应
<Button className="w-full md:w-auto">
  Click Me
</Button>

// 移动端大按钮（触摸友好）
<Button className="h-11 md:h-10 px-6 md:px-4">
  Tap Here
</Button>
```

### 4. 条件渲染（性能优化）

```tsx
// ✅ 正确：不渲染不需要的组件
const isMobile = useIsMobile();
return isMobile ? <MobileView /> : <DesktopView />;

// ❌ 错误：渲染后隐藏（浪费资源）
return (
  <>
    <div className="block md:hidden"><MobileView /></div>
    <div className="hidden md:block"><DesktopView /></div>
  </>
);
```

---

## 📐 断点参考

| 断点 | 最小宽度 | 设备 | Tailwind 前缀 |
|-----|---------|------|--------------|
| xs | 0px | 手机竖屏 | (无前缀) |
| sm | 640px | 手机横屏 | `sm:` |
| md | 768px | 平板竖屏 | `md:` |
| lg | 1024px | 平板横屏/小桌面 | `lg:` |
| xl | 1280px | 桌面 | `xl:` |
| 2xl | 1536px | 大桌面 | `2xl:` |

---

## 🧪 快速测试

### Chrome DevTools
```
1. 打开 Chrome
2. 按 Cmd+Shift+M（Mac）或 Ctrl+Shift+M（Windows）
3. 选择设备：iPhone SE, iPad, Desktop
4. 测试不同尺寸下的显示效果
```

### 常用设备尺寸
- **iPhone SE**: 375px × 667px
- **iPhone 14 Pro**: 393px × 852px
- **iPad Mini**: 768px × 1024px
- **iPad Pro**: 1024px × 1366px
- **Desktop**: 1280px × 720px
- **Wide Desktop**: 1920px × 1080px

---

## 📖 完整文档

- **实施方案**：`docs/20260123_响应式设计系统实施方案.md`
- **实施路线图**：`docs/20260123_响应式重构实施路线图.md`
- **Hooks API**：`lib/hooks/ui/use-breakpoint.ts`
- **工具函数**：`lib/utils/responsive.ts`
- **组件示例**：`components/common/responsive-*.tsx`

---

## ❓ 常见问题

### Q: SSR 下 useMediaQuery 报错？
**A**: 已处理，Hook 内部有 `typeof window === 'undefined'` 检查。

### Q: 如何选择使用哪个 Hook？
**A**: 
- 简单判断 → `useIsMobile()` / `useIsDesktop()`
- 需要宽度信息 → `useBreakpoint()`
- 需要设备类型 → `useDeviceType()`

### Q: 移动端和桌面端切换时闪烁？
**A**: 使用 SSR 默认值（桌面端），避免初始渲染不一致。

### Q: 表格在移动端性能差？
**A**: 使用条件渲染 `isMobile ? <CardList /> : <Table />`。

---

## 🎯 检查清单

重构组件时，请确保：
- [ ] 使用移动端优先的 Tailwind 类名
- [ ] 使用响应式 Hooks 而非媒体查询
- [ ] 避免固定宽度（使用 min-width/max-width）
- [ ] 触摸目标 >= 44px（移动端）
- [ ] 在多个断点下测试
- [ ] 避免横向滚动
- [ ] 图片使用 `sizes` 属性

---

**准备好了吗？开始重构你的第一个组件吧！** 🚀
