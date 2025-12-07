# 前端技术架构文档

## 技术架构概览

### 核心技术栈

| 组件 | 技术选型 | 说明 |
|:---|:---|:---|
| **框架** | Next.js 14 (App Router) | React Server Components + SSR |
| **语言** | TypeScript | 严格类型检查 |
| **UI 组件库** | Shadcn/ui | 基于 Radix UI 的可访问组件 |
| **样式** | Tailwind CSS | 原子化 CSS 框架 |
| **状态管理** | Zustand | 轻量级全局状态管理 |
| **数据获取** | TanStack Query v5 | 服务端状态管理和缓存 |
| **WebSocket** | 原生 WebSocket API | 实时进度推送 |
| **状态轮询** | Axios + TanStack Query | 任务状态查询 |
| **类型生成** | openapi-typescript-codegen | 从 OpenAPI Schema 生成类型 |

### 架构分层

```
┌─────────────────────────────────────────┐
│      Presentation Layer (Pages)          │
│  - App Router Pages                     │
│  - Server Components                    │
│  - Client Components                    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Component Layer                    │
│  - UI Components (Shadcn/ui)           │
│  - Feature Components                   │
│  - Layout Components                    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      State Management Layer              │
│  - Zustand Stores (Client State)        │
│  - TanStack Query (Server State)       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      API Layer                          │
│  - API Client (Axios)                  │
│  - WebSocket Client                    │
│  - Status Polling                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Type System                        │
│  - Generated Types (OpenAPI)            │
│  - Custom Types                         │
└─────────────────────────────────────────┘
```

---

## 路线图生成状态机

### 状态机时序图

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户
    participant Page as New Roadmap Page
    participant Store as Roadmap Store<br/>(Zustand)
    participant WS as WebSocket Client
    participant API as Backend API
    participant BG as Background Task
    
    %% 阶段 1: 用户提交
    User->>Page: 填写学习目标
    User->>Page: 提交表单
    Page->>Store: setGenerating(true)
    Page->>API: POST /roadmaps/generate
    
    %% 阶段 2: 任务创建
    API-->>Page: {task_id, status: 'processing'}
    Page->>Store: setTaskId(task_id)
    Page->>WS: 建立 WebSocket 连接<br/>ws://api/ws/{task_id}
    WS-->>Page: 连接成功
    
    %% 阶段 3: 后台任务执行
    API->>BG: 创建后台任务
    BG->>BG: 执行 Orchestrator
    
    %% 阶段 4: 需求分析阶段
    BG->>WS: {type: 'progress', step: 'intent_analysis'}
    WS->>Store: setGenerationPhase('analyzing')
    WS->>Page: 更新 UI
    
    BG->>WS: {type: 'progress', step: 'intent_analysis_complete'}
    WS->>Store: setGenerationPhase('curriculum_design')
    
    %% 阶段 5: 框架设计阶段
    BG->>WS: {type: 'progress', step: 'curriculum_design'}
    WS->>Page: 更新 UI
    
    BG->>WS: {type: 'roadmap_created', roadmap_id: 'xxx'}
    WS->>Store: setRoadmapId(roadmap_id)
    
    %% 阶段 6: 人工审核阶段
    BG->>WS: {type: 'human_review_pending'}
    WS->>Store: setGenerationPhase('human_review')
    WS->>Page: 显示审核对话框
    Page->>User: 展示路线图预览
    
    alt 用户批准
        User->>Page: 点击"批准"
        Page->>API: POST /roadmaps/{task_id}/approve?approved=true
        API-->>Page: 200 OK
        Page->>Store: setGenerationPhase('content_generation')
    else 用户拒绝
        User->>Page: 点击"拒绝"
        Page->>API: POST /roadmaps/{task_id}/approve?approved=false
        API-->>Page: 200 OK
        Page->>Store: setGenerationPhase('idle')
        Page->>WS: 断开连接
    end
    
    %% 阶段 7: 内容生成阶段
    BG->>WS: {type: 'progress', step: 'tutorial_generation'}
    WS->>Store: setGenerationPhase('content_generation')
        
        loop 每个 Concept
        BG->>WS: {type: 'concept_start', concept_id: 'xxx'}
        WS->>Store: updateConceptStatus('xxx', 'generating')
            
        BG->>WS: {type: 'concept_complete', concept_id: 'xxx'}
        WS->>Store: updateConceptStatus('xxx', 'completed')
        WS->>Page: 更新进度条
        end
    
    %% 阶段 8: 完成
    BG->>WS: {type: 'task_complete', roadmap_id: 'xxx'}
    WS->>Store: setGenerationPhase('completed')
    WS->>Store: setGenerating(false)
    
    Page->>API: GET /roadmaps/{roadmap_id}
    API-->>Page: RoadmapFramework
    Page->>Store: setRoadmap(framework)
    Page->>Page: 导航到 /app/roadmap/{id}
    Page->>User: 显示完成状态
```

### 状态机状态流转

```mermaid
stateDiagram-v2
    [*] --> IDLE: 初始状态
    
    IDLE --> ANALYZING: 用户提交表单
    
    ANALYZING --> CURRICULUM_DESIGN: 需求分析完成
    
    CURRICULUM_DESIGN --> HUMAN_REVIEW: 框架设计完成
    
    HUMAN_REVIEW --> CONTENT_GENERATION: 用户批准
    HUMAN_REVIEW --> IDLE: 用户拒绝
    
    CONTENT_GENERATION --> TUTORIAL_GENERATION: 开始生成教程
    CONTENT_GENERATION --> RESOURCE_GENERATION: 开始生成资源
    CONTENT_GENERATION --> QUIZ_GENERATION: 开始生成测验
    
    TUTORIAL_GENERATION --> CONTENT_COMPLETED: 教程生成完成
    RESOURCE_GENERATION --> CONTENT_COMPLETED: 资源生成完成
    QUIZ_GENERATION --> CONTENT_COMPLETED: 测验生成完成
    
    CONTENT_COMPLETED --> COMPLETED: 所有内容生成完成
    
    COMPLETED --> [*]: 导航到详情页
    
    note right of HUMAN_REVIEW
        显示审核对话框
        等待用户操作
    end note
    
    note right of CONTENT_GENERATION
        并行生成三种内容
        实时更新进度
    end note
```

### 用户流程

```mermaid
graph TB
    START[用户访问 /app/new] --> STEP1[步骤1: 输入学习目标]
    STEP1 --> STEP2[步骤2: 填写偏好设置]
    STEP2 --> SUBMIT[提交表单]
    
    SUBMIT --> API[POST /roadmaps/generate]
    API --> TASK_ID[获得 task_id]
    TASK_ID --> WS[建立 WebSocket 连接]
    
    WS --> ANALYZING[显示: 需求分析中...]
    ANALYZING --> DESIGNING[显示: 框架设计中...]
    DESIGNING --> PREVIEW[显示: 路线图预览]
    
    PREVIEW --> REVIEW{用户审核}
    REVIEW -->|批准| APPROVE[POST /approve]
    REVIEW -->|拒绝| STEP1
    
    APPROVE --> GENERATING[显示: 内容生成中...]
    GENERATING --> PROGRESS[WebSocket 实时进度]
    PROGRESS --> POLL[轮询 GET /status]
    POLL --> COMPLETE[生成完成]
    
    COMPLETE --> FETCH[GET /roadmaps/{id}]
    FETCH --> NAVIGATE[导航到 /app/roadmap/{id}]
    
    style ANALYZING fill:#e3f2fd
    style DESIGNING fill:#e3f2fd
    style GENERATING fill:#e8f5e9
    style COMPLETE fill:#c8e6c9
```

---

## UI/UX 开发规范

### 设计系统：Editorial Cream & Sage

#### 色彩系统

```css
/* 主色调 */
--background: 40 20% 99%;        /* Warm cream 背景 */
--foreground: 24 10% 10%;        /* Charcoal 文本 */
--primary: 24 10% 10%;           /* Charcoal 主色 */
--sage: 140 15% 55%;             /* Sage green 强调色 */

/* 辅助色 */
--muted: 40 10% 94%;             /* 柔和背景 */
--accent: 140 15% 55%;           /* Sage 强调 */
--border: 24 5% 90%;              /* 柔和边框 */
```

#### 字体系统

```typescript
// tailwind.config.ts
fontFamily: {
  serif: ['Playfair Display', 'Georgia', 'serif'],  // 标题字体
  sans: ['Inter', 'system-ui', 'sans-serif'],       // 正文字体
  'sans-sc': ['Noto Sans SC', 'sans-serif'],       // 中文字体
}
```

#### 间距系统

使用 Tailwind 默认间距系统（4px 基准）：
- `space-1` = 4px
- `space-2` = 8px
- `space-4` = 16px
- `space-6` = 24px
- `space-8` = 32px

#### 圆角系统

```typescript
borderRadius: {
  none: '0',
  sm: '0.125rem',    // 2px
  DEFAULT: '0.5rem', // 8px (--radius)
  md: '0.5rem',      // 8px
  lg: '0.75rem',     // 12px
  xl: '1rem',        // 16px
}
```

### 组件开发规范

#### 组件结构

```typescript
'use client';  // 客户端组件标记

import { useState } from 'react';
import { cn } from '@/lib/utils';  // 类名合并工具
import type { ComponentProps } from '@/types';

interface MyComponentProps {
  /** 组件标题 */
  title: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义类名 */
  className?: string;
}

export function MyComponent({
  title,
  disabled = false,
  className,
}: MyComponentProps) {
  return (
    <div className={cn('base-styles', className)}>
      <h2>{title}</h2>
    </div>
  );
}
```

#### 组件命名规范

- **组件文件**：使用 `kebab-case`（如 `phase-indicator.tsx`）
- **组件名称**：使用 `PascalCase`（如 `PhaseIndicator`）
- **Props 接口**：组件名 + `Props`（如 `PhaseIndicatorProps`）

#### 样式规范

1. **优先使用 Tailwind 工具类**
2. **使用 `cn()` 合并类名**（支持条件类名）
3. **响应式设计**：移动端优先（`md:`, `lg:` 断点）
4. **暗色模式**：使用 `dark:` 前缀

```typescript
<div
  className={cn(
    'base-classes',
    {
      'active-classes': isActive,
      'disabled-classes': disabled,
    },
    className  // 允许外部覆盖
  )}
/>
```

### 布局规范

#### App Layout（三栏布局）

```
┌─────────────────────────────────────────────────┐
│              App Layout                          │
├──────────┬──────────────────────┬────────────────┤
│ Left     │    Main Content      │   Right        │
│ Sidebar  │    (flex-1)          │   Sidebar      │
│ (260px)  │                      │   (350px)      │
│          │                      │                │
│ - Logo   │  ┌────────────────┐  │  - AI Chat    │
│ - Search │  │  Page Content  │  │  - Context    │
│ - Nav    │  │                │  │  - Input     │
│ - Recent │  │                │  │               │
│ - User   │  └────────────────┘  │               │
└──────────┴──────────────────────┴────────────────┘
```

#### 响应式断点

```typescript
// tailwind.config.ts
screens: {
  sm: '640px',   // 移动端
  md: '768px',   // 平板
  lg: '1024px',  // 桌面
  xl: '1280px',  // 大屏
}
```

**响应式策略**：
- 移动端：单栏布局，侧边栏折叠
- 平板：两栏布局（主内容 + 侧边栏）
- 桌面：三栏布局（完整布局）

### 交互规范

#### 加载状态

```typescript
// 使用 Skeleton 组件
<Skeleton className="h-4 w-full" />

// 使用 Loading Spinner
<Loader2 className="w-4 h-4 animate-spin" />

// 使用 Progress Bar
<Progress value={progress} />
```

#### 错误处理

```typescript
// 使用 Error Boundary
<ErrorBoundary fallback={<ErrorFallback />}>
  <Component />
</ErrorBoundary>

// 使用 Toast 提示
import { toast } from 'sonner';
toast.error('操作失败', { description: '错误详情' });
```

#### 表单验证

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  learningGoal: z.string().min(1, '请输入学习目标'),
});

const form = useForm({
  resolver: zodResolver(schema),
});
```

### 可访问性（A11y）规范

1. **语义化 HTML**：使用正确的 HTML 标签
2. **ARIA 属性**：为交互元素添加 `aria-label`、`aria-describedby`
3. **键盘导航**：支持 Tab 键导航，Esc 关闭对话框
4. **焦点管理**：对话框打开时聚焦第一个可交互元素
5. **颜色对比度**：文本与背景对比度 ≥ 4.5:1

```typescript
<button
  aria-label="关闭对话框"
  onClick={handleClose}
  className="focus:outline-none focus:ring-2 focus:ring-primary"
>
  <X />
</button>
```

---

## API 集成规范

### 类型生成

#### 生成命令

```bash
# 一次性生成
npm run generate:types

# 监听后端变化（开发模式）
npm run generate:types:watch
```

#### 类型使用

```typescript
// 导入生成的类型
import type {
  RoadmapFramework,
  Concept,
  Tutorial,
  LearningPreferences,
} from '@/types/generated/models';

// 导入生成的 API 服务
import { RoadmapsService } from '@/types/generated/services';

// 使用
const roadmap = await RoadmapsService.getRoadmap({
  roadmapId: 'xxx',
});
```

### API 客户端

#### REST API（主要方式）

```typescript
// lib/api/endpoints.ts
import { apiClient } from './client';

// 1. 提交生成任务
export async function generateRoadmapAsync(request: UserRequest) {
  const response = await apiClient.post('/roadmaps/generate', request);
  return response.data; // { task_id, status, message }
}

// 2. 查询任务状态
export async function getRoadmapStatus(taskId: string) {
  const response = await apiClient.get(`/roadmaps/${taskId}/status`);
  return response.data; // { task_id, status, roadmap_id, ... }
}

// 3. 获取完整路线图
export async function getRoadmap(roadmapId: string) {
  const response = await apiClient.get(`/roadmaps/${roadmapId}`);
  return response.data; // RoadmapFramework
}

// 4. 人工审核
export async function approveRoadmap(taskId: string, approved: boolean) {
  const response = await apiClient.post(
    `/roadmaps/${taskId}/approve`,
    null,
    { params: { approved } }
  );
  return response.data;
}
```

#### WebSocket API（实时进度）

```typescript
// lib/api/websocket.ts
import { TaskWebSocket } from '@/lib/api/websocket';

const ws = new TaskWebSocket(taskId, {
  onProgress: (event) => {
    // 更新进度: { type: 'progress', step: 'xxx', progress: 0.5 }
  },
  onRoadmapCreated: (event) => {
    // 路线图创建: { type: 'roadmap_created', roadmap_id: 'xxx' }
  },
  onHumanReviewPending: (event) => {
    // 等待人工审核: { type: 'human_review_pending' }
  },
  onConceptStart: (event) => {
    // Concept 开始生成: { type: 'concept_start', concept_id: 'xxx' }
  },
  onConceptComplete: (event) => {
    // Concept 生成完成: { type: 'concept_complete', concept_id: 'xxx' }
  },
  onTaskComplete: (event) => {
    // 任务完成: { type: 'task_complete', roadmap_id: 'xxx' }
  },
});
```

#### 典型使用流程

```typescript
// 1. 提交任务
const { task_id } = await generateRoadmapAsync(request);

// 2. 建立 WebSocket 连接
const ws = new TaskWebSocket(task_id, {
  onProgress: (event) => {
    setProgress(event.step);
  },
  onTaskComplete: async (event) => {
    // 3. 获取完整路线图
    const roadmap = await getRoadmap(event.roadmap_id);
    setRoadmap(roadmap);
    router.push(`/app/roadmap/${event.roadmap_id}`);
  },
});

// 4. 可选：轮询状态（作为 WebSocket 的备用方案）
const interval = setInterval(async () => {
  const status = await getRoadmapStatus(task_id);
  if (status.status === 'completed') {
    clearInterval(interval);
    const roadmap = await getRoadmap(status.roadmap_id!);
    setRoadmap(roadmap);
  }
}, 2000);
```

### 数据获取模式

#### 1. 使用 TanStack Query（REST API）

```typescript
// lib/hooks/use-roadmap.ts
import { useQuery } from '@tanstack/react-query';
import { getRoadmap, getRoadmapStatus } from '@/lib/api/endpoints';

// 获取完整路线图
export function useRoadmap(roadmapId: string | undefined) {
  return useQuery({
    queryKey: ['roadmap', roadmapId],
    queryFn: () => getRoadmap(roadmapId!),
    enabled: !!roadmapId,
    staleTime: 5 * 60 * 1000, // 5 分钟
  });
}

// 轮询任务状态
export function useTaskStatus(taskId: string | undefined) {
  return useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => getRoadmapStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: 2000, // 每 2 秒轮询一次
  });
}
```

#### 2. 使用 WebSocket（实时进度）

```typescript
// lib/hooks/use-roadmap-generation.ts
import { useEffect } from 'react';
import { TaskWebSocket } from '@/lib/api/websocket';
import { useRoadmapStore } from '@/lib/store/roadmap-store';

export function useRoadmapGeneration(taskId: string) {
  const { setProgress, setRoadmapId } = useRoadmapStore();
  
  useEffect(() => {
    const ws = new TaskWebSocket(taskId, {
      onProgress: (event) => {
        setProgress(event.step, event.progress);
      },
      onRoadmapCreated: (event) => {
        setRoadmapId(event.roadmap_id);
      },
      onTaskComplete: (event) => {
        // 导航到路线图详情页
        window.location.href = `/app/roadmap/${event.roadmap_id}`;
      },
    });
    
    return () => ws.disconnect();
  }, [taskId]);
}
```

#### 3. 使用 Zustand Store（全局状态）

```typescript
// lib/store/roadmap-store.ts
import { create } from 'zustand';
import type { RoadmapFramework } from '@/types';

interface RoadmapStore {
  // 路线图数据
  currentRoadmap: RoadmapFramework | null;
  setRoadmap: (roadmap: RoadmapFramework) => void;
  
  // 生成状态
  isGenerating: boolean;
  taskId: string | null;
  roadmapId: string | null;
  currentPhase: string;
  progress: number;
  
  // 更新方法
  setGenerating: (generating: boolean) => void;
  setTaskId: (taskId: string) => void;
  setRoadmapId: (roadmapId: string) => void;
  setProgress: (phase: string, progress: number) => void;
}

export const useRoadmapStore = create<RoadmapStore>((set) => ({
  currentRoadmap: null,
  isGenerating: false,
  taskId: null,
  roadmapId: null,
  currentPhase: 'idle',
  progress: 0,
  
  setRoadmap: (roadmap) => set({ currentRoadmap: roadmap }),
  setGenerating: (generating) => set({ isGenerating: generating }),
  setTaskId: (taskId) => set({ taskId }),
  setRoadmapId: (roadmapId) => set({ roadmapId }),
  setProgress: (phase, progress) => set({ currentPhase: phase, progress }),
}));
```

---

## 目录结构

```
frontend-next/
├── AGENT.md                    # 本文档
├── app/                        # Next.js App Router
│   ├── layout.tsx             # 根布局
│   ├── page.tsx               # Landing 页
│   └── app/                   # 应用路由组
│       ├── layout.tsx         # App Layout
│       ├── new/               # 创建路线图
│       │   └── page.tsx
│       └── roadmap/[id]/      # 路线图详情
│           └── page.tsx
├── components/                # React 组件
│   ├── ui/                   # Shadcn/ui 组件
│   ├── layout/               # 布局组件
│   ├── roadmap/              # 路线图组件
│   ├── tutorial/             # 教程组件
│   └── chat/                 # 聊天组件
├── lib/                      # 工具库
│   ├── api/                  # API 客户端
│   │   ├── client.ts        # Axios 客户端配置
│   │   ├── endpoints.ts     # REST API 端点
│   │   └── websocket.ts     # WebSocket 客户端
│   ├── store/                # Zustand Stores
│   │   ├── roadmap-store.ts
│   │   ├── chat-store.ts
│   │   └── ui-store.ts
│   └── hooks/                # 自定义 Hooks
│       ├── use-roadmap.ts
│       └── use-sse.ts
├── types/                    # TypeScript 类型
│   ├── generated/           # 自动生成（OpenAPI）
│   └── custom/              # 自定义类型
└── scripts/                  # 脚本
    └── generate-types.ts    # 类型生成脚本
```

---

## 开发规范

### 代码规范

#### TypeScript 配置

```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
  }
}
```

#### ESLint 配置

- 使用 Next.js 默认 ESLint 配置
- 添加 `@typescript-eslint/recommended` 规则
- 使用 Prettier 格式化代码

#### 文件命名

- **组件文件**：`kebab-case.tsx`（如 `phase-indicator.tsx`）
- **工具文件**：`kebab-case.ts`（如 `use-roadmap.ts`）
- **类型文件**：`kebab-case.ts`（如 `phases.ts`）

### 性能优化

#### 代码分割

```typescript
// 动态导入组件
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false,  // 禁用 SSR（如需要）
});
```

#### 图片优化

```typescript
import Image from 'next/image';

<Image
  src="/image.jpg"
  alt="描述"
  width={800}
  height={600}
  priority  // 首屏图片
  placeholder="blur"  // 模糊占位符
/>
```

#### 状态优化

- 使用 `useMemo` 缓存计算结果
- 使用 `useCallback` 缓存函数引用
- 避免在渲染中创建新对象/数组

### 测试规范

#### 单元测试

```typescript
// __tests__/components/PhaseIndicator.test.tsx
import { render, screen } from '@testing-library/react';
import { PhaseIndicator } from '@/components/roadmap/phase-indicator';

describe('PhaseIndicator', () => {
  it('should render current phase', () => {
    render(<PhaseIndicator currentPhase="analyzing" />);
    expect(screen.getByText('需求分析')).toBeInTheDocument();
  });
});
```

#### E2E 测试

```typescript
// e2e/roadmap-generation.spec.ts
import { test, expect } from '@playwright/test';

test('should generate roadmap', async ({ page }) => {
  await page.goto('/app/new');
  await page.fill('[name="learningGoal"]', '学习 React');
  await page.click('button[type="submit"]');
  await expect(page.locator('text=生成完成')).toBeVisible();
});
```

---

## 常见问题

### Q: 如何添加新的 API 端点？

1. 后端添加端点后，运行 `npm run generate:types`
2. 在 `lib/api/endpoints.ts` 中添加封装函数
3. 在 `lib/hooks/` 中创建对应的 Hook（如需要）

### Q: 如何处理实时进度更新？

使用 WebSocket 客户端 + 轮询状态作为备用：

```typescript
// 主要方式：WebSocket
const ws = new TaskWebSocket(taskId, {
  onProgress: (event) => {
    updateProgress(event.step, event.progress);
  },
  onTaskComplete: (event) => {
    // 任务完成
  },
});

// 备用方式：轮询（WebSocket 连接失败时）
const pollStatus = async () => {
  const status = await getRoadmapStatus(taskId);
  if (status.status === 'completed') {
    handleComplete(status.roadmap_id);
  }
};
```

### Q: 如何实现暗色模式？

使用 `next-themes`：

```typescript
import { ThemeProvider } from 'next-themes';

<ThemeProvider attribute="class" defaultTheme="light">
  {children}
</ThemeProvider>
```

### Q: 如何优化首屏加载时间？

1. 使用 Next.js Image 组件优化图片
2. 代码分割，按需加载组件
3. 使用 `loading="lazy"` 延迟加载非关键内容
4. 启用 Next.js 自动优化（压缩、缓存）

---

**文档版本**：v1.0.0  
**最后更新**：2025-01-XX  
**维护者**：Frontend Team

