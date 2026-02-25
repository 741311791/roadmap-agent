# AGENTS.md

此文档为前端代码库的编码规范和工作流程指南。

## Build/Lint/Test 命令

```bash
# 开发与构建
npm run dev                 # 启动开发服务器（端口 3000）
npm run build               # 生产构建
npm run start               # 生产环境运行

# 代码质量
npm run lint                # ESLint 检查
npm run type-check          # TypeScript 类型检查

# 类型生成（OpenAPI）
npm run generate:all        # 生成所有类型和常量

# 测试
npm test                    # Vitest 监听模式
npm run test:run            # 运行所有测试
npm run test:coverage       # 测试覆盖率报告

# 单个测试
npm test -- roadmap-helpers.test.ts        # 运行特定测试文件
npm test -t "isConceptIdValid"            # 运行特定测试用例
```

## 代码风格规范

### 文件命名
- 组件文件：`kebab-case.tsx`（如 `phase-indicator.tsx`）
- 工具文件：`kebab-case.ts`（如 `use-roadmap.ts`）
- 组件名：`PascalCase`（如 `PhaseIndicator`）
- Props 接口：组件名 + `Props`（如 `PhaseIndicatorProps`）

### 导入顺序
```typescript
// 1. React/Next.js
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
// 2. 第三方库
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
// 3. 内部类型
import type { RoadmapFramework } from '@/types/generated/models';
// 4. 内部组件
import { Button } from '@/components/ui/button';
// 5. 内部工具/Hooks/Stores
import { cn } from '@/lib/utils';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
```

### 组件开发规范
```typescript
'use client';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface MyComponentProps {
  title: string;
  disabled?: boolean;
  className?: string;
}

export function MyComponent({ title, disabled = false, className }: MyComponentProps) {
  return <div className={cn('base-classes', className)}><h2>{title}</h2></div>;
}
```

### 样式规范
- 优先使用 Tailwind CSS 工具类
- 使用 `cn()` 合并类名（支持条件类名）
- 响应式：移动端优先（`md:`, `lg:` 断点）
- 暗色模式：使用 `dark:` 前缀
```typescript
<div className={cn('base-classes', { active: isActive }, className)} />
```

### Store 开发规范（Zustand）
```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface MyStore {
  value: string;
  setValue: (value: string) => void;
}

export const useMyStore = create<MyStore>()(
  devtools(persist((set) => ({ value: '', setValue: (value) => set({ value }) }), { name: 'my-storage' }), { name: 'MyStore' })
);
```

## 命名约定

- **组件**：PascalCase（如 `PhaseIndicator`）
- **函数**：camelCase（如 `calculateProgress`）
- **常量**：UPPER_SNAKE_CASE（如 `API_TIMEOUT`）
- **类型/接口**：PascalCase（如 `RoadmapFramework`）

## 重要规则（来自 Cursor Rules）

### 1. MVP & Greenfield 开发
- 不考虑向后兼容，使用最新稳定特性
- 删除旧代码，直接修改函数，不创建 v2 版本

### 2. 严格枚举和常量一致性
- 不猜测枚举/常量值，必须从代码库中获取确切定义
- 优先使用枚举引用而非原始字符串

### 3. Git 分支管理
- `main`：生产分支（仅接受从 develop 合并）
- `develop`：开发分支（日常开发）
- 提交格式：`<type>: <description>`（feat/fix/docs/refactor/chore）

### 4. 文档和注释
- 代码注释使用**简体中文**，UI 可见文本使用**英文**
- 文档命名：`YYYYMMDD_中文文档名.md`
- 每个函数必须包含 JSDoc 注释

## 技术栈

- **框架**：Next.js 14 (App Router)
- **语言**：TypeScript (严格模式)
- **UI 组件库**：Shadcn/ui (Radix UI)
- **样式**：Tailwind CSS
- **状态管理**：Zustand
- **数据获取**：TanStack Query v5
- **测试**：Vitest + Testing Library
- **表单**：React Hook Form + Zod

## API 集成

```bash
npm run generate:types  # 从 OpenAPI Schema 生成类型
```

```typescript
import { apiClient } from '@/lib/api/client';
const roadmap = await apiClient.get(`/roadmaps/${id}`);
```

## 注意事项

1. **类型安全**：始终使用 TypeScript，避免 `any`
2. **性能优化**：使用 `useMemo`/`useCallback` 优化计算
3. **可访问性**：使用语义化 HTML，添加 ARIA 属性
4. **代码分割**：使用 `dynamic()` 动态导入大型组件
5. **环境变量**：使用 `.env.local`，不提交 `.env`
