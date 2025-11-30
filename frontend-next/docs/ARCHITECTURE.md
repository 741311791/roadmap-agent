# 前端架构设计文档

## 一、技术架构概览

### 1.1 技术栈

| 领域 | 技术选型 | 说明 |
|:---|:---|:---|
| **框架** | Next.js 14 (App Router) | SSR + 流式渲染，迁移自当前 Vite + React |
| **语言** | TypeScript | 与后端 Pydantic 模型端到端类型对齐 |
| **UI 组件** | Shadcn/ui + Tailwind CSS | 保持当前 Editorial Cream & Sage 设计风格 |
| **状态管理** | Zustand | 轻量级跨组件状态同步 |
| **流程图** | React Flow | 路线图可视化 |
| **数据获取** | TanStack Query v5 | REST API 请求，内置缓存 |
| **流式通信** | Native EventSource (SSE) | 处理后端流式响应 |

### 1.2 与后端共享类型系统

```
后端 Pydantic Models  →  FastAPI OpenAPI Schema  →  openapi-typescript-codegen  →  前端 TypeScript Types
      (domain.py)           (/openapi.json)                (自动生成)               (types/generated/)
```

**核心共享模型**（来自 `backend/app/models/domain.py`）：

- `LearningPreferences` - 学习偏好
- `UserRequest` - 用户请求
- `Concept`, `Module`, `Stage`, `RoadmapFramework` - 路线图结构
- `Tutorial`, `TutorialSection` - 教程内容
- `Resource`, `ResourceRecommendationOutput` - 资源推荐
- `QuizQuestion`, `QuizGenerationOutput` - 测验
- `ModificationAnalysisOutput`, `TutorialModificationOutput` 等 - 修改相关

---

## 二、页面路由规划

### 2.1 路由结构

```
/                           # 营销首页 (Landing)
├── /methodology           # 方法论介绍
├── /pricing              # 定价页面
│
/app                       # 应用主入口 (需要 session)
├── /app/dashboard        # 用户仪表盘（我的路线图列表）
├── /app/new              # 创建新路线图（输入学习目标）
├── /app/roadmap/[id]     # 路线图详情
│   ├── /app/roadmap/[id]/overview    # 路线图概览（默认）
│   ├── /app/roadmap/[id]/flow        # 流程图模式
│   └── /app/roadmap/[id]/learn/[conceptId]  # 学习视图
└── /app/settings         # 用户设置
```

### 2.2 路由-布局映射

| 路由 | 布局 | 说明 |
|:---|:---|:---|
| `/`, `/methodology`, `/pricing` | `MarketingLayout` | Navbar + Footer，营销页面 |
| `/app/*` | `AppLayout` | 三栏布局（左侧导航 + 主内容 + AI 助手） |
| `/app/roadmap/[id]/learn/[conceptId]` | `LearningLayout` | 三栏布局（TOC + 内容 + AI 助手） |

---

## 三、页面布局架构

### 3.1 AppLayout（应用主布局）

```
┌─────────────────────────────────────────────────────────────────┐
│                         App Layout                               │
├──────────┬────────────────────────────────────┬─────────────────┤
│ LeftSide │          Main Content              │   RightSidebar  │
│  (260px) │          (flex-1)                  │    (350px)      │
│          │                                    │                 │
│ ┌──────┐ │  ┌──────────────────────────────┐  │  ┌───────────┐  │
│ │ Logo │ │  │                              │  │  │ AI Agent  │  │
│ ├──────┤ │  │       Page Content           │  │  │           │  │
│ │Search│ │  │     (Outlet / Children)      │  │  │ Chat UI   │  │
│ ├──────┤ │  │                              │  │  │           │  │
│ │ Nav  │ │  │                              │  │  │           │  │
│ │Items │ │  │                              │  │  │           │  │
│ ├──────┤ │  │                              │  │  │           │  │
│ │Recent│ │  │                              │  │  │ ┌───────┐ │  │
│ │Roads │ │  │                              │  │  │ │ Input │ │  │
│ ├──────┤ │  └──────────────────────────────┘  │  │ └───────┘ │  │
│ │User  │ │                                    │  └───────────┘  │
│ └──────┘ │                                    │                 │
├──────────┴────────────────────────────────────┴─────────────────┤
│                     Resizable Panels                             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 LearningLayout（学习视图布局）

```
┌─────────────────────────────────────────────────────────────────┐
│                       Learning Layout                            │
├─────────┬──────────────────────────────────────┬────────────────┤
│   TOC   │         Reader Content               │  AI Assistant  │
│ (240px) │          (flex-1)                    │   (400px)      │
│         │                                      │                │
│ ┌─────┐ │  ┌────────────────────────────────┐  │  ┌──────────┐  │
│ │Back │ │  │    Paper Container             │  │  │ Context  │  │
│ ├─────┤ │  │  ┌──────────────────────────┐  │  │  │ Aware    │  │
│ │     │ │  │  │  Title + Meta            │  │  │  │ Chat     │  │
│ │ Sec │ │  │  ├──────────────────────────┤  │  │  │          │  │
│ │ tion│ │  │  │  Markdown Content        │  │  │  │ "这部分  │  │
│ │ Nav │ │  │  │  (ReactMarkdown)         │  │  │  │  不理解"  │  │
│ │     │ │  │  │                          │  │  │  │          │  │
│ │     │ │  │  ├──────────────────────────┤  │  │  │          │  │
│ │     │ │  │  │  Quiz Section            │  │  │  │ ┌──────┐ │  │
│ │     │ │  │  ├──────────────────────────┤  │  │  │ │Input │ │  │
│ └─────┘ │  │  │  Resources               │  │  │  │ └──────┘ │  │
│         │  │  └──────────────────────────┘  │  │  └──────────┘  │
│         │  └────────────────────────────────┘  │                │
└─────────┴──────────────────────────────────────┴────────────────┘
```

---

## 四、用户动线设计

### 4.1 新用户流程

```
Landing Page (/)
    │
    ▼ "开始学习"
Dashboard (/app/dashboard)
    │ (无路线图 → 显示 Empty State)
    ▼ "创建第一个路线图"
New Roadmap (/app/new)
    │
    │ 输入学习目标、偏好
    ▼ 提交
[SSE 流式生成]
    │
    │ 显示进度 + 预览
    ▼ 完成
Roadmap Detail (/app/roadmap/[id])
    │
    ▼ 点击 Concept
Learning View (/app/roadmap/[id]/learn/[conceptId])
```

### 4.2 返回用户流程

```
Landing Page (/)
    │
    ▼ "进入应用"
Dashboard (/app/dashboard)
    │ (显示历史路线图列表)
    ▼ 选择路线图
Roadmap Detail (/app/roadmap/[id])
    │
    ├─▶ 继续学习 (上次位置)
    ├─▶ 查看流程图 (/flow)
    └─▶ AI 对话修改内容
```

### 4.3 学习闭环

```
Learning View
    │
    ├─▶ 阅读教程内容
    │
    ├─▶ 完成测验 (Quiz)
    │     │
    │     └─▶ 查看答案解析
    │
    ├─▶ 查看推荐资源
    │
    ├─▶ AI 助手对话
    │     │
    │     └─▶ "帮我简化这部分" → 触发 Tutorial Modify
    │
    └─▶ 标记完成 → 返回 Roadmap
```

---

## 五、项目目录结构

```
frontend-next/
├── app/                          # Next.js 14 App Router
│   ├── layout.tsx               # 根布局（Providers）
│   ├── page.tsx                 # Landing (/)
│   ├── methodology/
│   │   └── page.tsx            # 方法论
│   ├── pricing/
│   │   └── page.tsx            # 定价
│   └── (app)/                   # 应用路由组
│       ├── layout.tsx          # AppLayout（三栏）
│       ├── dashboard/
│       │   └── page.tsx        # 用户仪表盘
│       ├── new/
│       │   └── page.tsx        # 创建路线图
│       ├── roadmap/
│       │   └── [id]/
│       │       ├── layout.tsx  # RoadmapLayout
│       │       ├── page.tsx    # 概览（默认）
│       │       ├── flow/
│       │       │   └── page.tsx  # 流程图
│       │       └── learn/
│       │           └── [conceptId]/
│       │               └── page.tsx  # 学习视图
│       └── settings/
│           └── page.tsx        # 设置
│
├── components/
│   ├── ui/                     # Shadcn/ui 组件
│   ├── layout/                 # 布局组件
│   │   ├── app-shell.tsx
│   │   ├── left-sidebar.tsx
│   │   └── right-sidebar.tsx
│   ├── roadmap/                # 路线图组件
│   │   ├── RoadmapTree.tsx
│   │   ├── FlowCanvas.tsx
│   │   ├── ConceptCard.tsx
│   │   └── ...
│   ├── learning/               # 学习视图组件
│   │   ├── TutorialReader.tsx
│   │   ├── QuizSection.tsx
│   │   ├── ResourceList.tsx
│   │   └── ReflectionSection.tsx
│   ├── chat/                   # AI 聊天组件
│   │   ├── ChatContainer.tsx
│   │   ├── MessageList.tsx
│   │   ├── ChatInput.tsx
│   │   └── StreamRenderer.tsx
│   └── common/                 # 通用组件
│       ├── empty-state.tsx
│       ├── loading-spinner.tsx
│       └── ...
│
├── lib/
│   ├── api/                    # API 客户端
│   │   ├── client.ts          # Axios 配置
│   │   ├── sse.ts             # SSE 管理器
│   │   └── endpoints.ts       # 端点定义
│   ├── store/                  # Zustand Stores
│   │   ├── roadmap-store.ts
│   │   ├── chat-store.ts
│   │   ├── ui-store.ts
│   │   └── learning-store.ts
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── use-sse.ts
│   │   ├── use-roadmap.ts
│   │   └── index.ts
│   └── utils.ts
│
├── types/
│   ├── generated/              # 自动生成（来自后端 OpenAPI）
│   │   ├── index.ts
│   │   ├── core/               # API 核心类型
│   │   ├── models/             # 数据模型
│   │   └── services/           # API 服务
│   └── custom/                 # 前端专用类型
│       ├── ui.ts
│       ├── sse.ts
│       └── store.ts
│
├── docs/
│   └── ARCHITECTURE.md         # 本文档
│
├── scripts/
│   └── generate-types.ts       # 类型生成脚本
│
└── 配置文件...
```

---

## 六、API 集成规划

### 6.1 后端 API 端点映射

| 功能 | HTTP 方法 | 端点 | 前端使用场景 |
|:---|:---|:---|:---|
| 生成路线图 | POST | `/roadmaps/generate-full-stream` | `/app/new` 页面提交 |
| 查询状态 | GET | `/roadmaps/{task_id}/status` | 轮询生成进度 |
| 获取路线图 | GET | `/roadmaps/{roadmap_id}` | `/app/roadmap/[id]` 加载 |
| 审核路线图 | POST | `/roadmaps/{task_id}/approve` | 用户确认框架 |
| 获取最新教程 | GET | `/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest` | 学习视图加载 |
| 修改教程 | POST | `/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify` | AI 助手修改 |
| 修改资源 | POST | `/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/modify` | AI 助手修改 |
| 修改测验 | POST | `/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/modify` | AI 助手修改 |
| 聊天修改流 | POST | `/roadmaps/{roadmap_id}/chat-stream` | AI 助手自然语言修改 |

### 6.2 SSE 事件流处理

```typescript
// 路线图生成事件
type GenerationEvent =
  | { type: 'step_start'; step: string; progress: number }
  | { type: 'roadmap_preview'; framework: RoadmapFramework }
  | { type: 'tutorial_progress'; concept_id: string; status: string }
  | { type: 'complete'; roadmap_id: string }
  | { type: 'error'; message: string };

// 聊天修改事件
type ChatModificationEvent =
  | { type: 'analyzing'; message: string }
  | { type: 'intents'; intents: SingleModificationIntent[] }
  | { type: 'modifying'; target_id: string; target_name: string }
  | { type: 'result'; result: SingleModificationResult }
  | { type: 'done'; summary: string }
  | { type: 'error'; message: string };
```

---

## 七、状态管理设计

### 7.1 Store 划分

| Store | 职责 | 主要状态 |
|:---|:---|:---|
| `useRoadmapStore` | 当前路线图数据 | `currentRoadmap`, `isGenerating`, `progress` |
| `useChatStore` | AI 对话状态 | `messages`, `isStreaming`, `streamBuffer` |
| `useUIStore` | UI 状态 | `sidebarCollapsed`, `viewMode`, `selectedConceptId` |
| `useLearningStore` | 学习进度 | `completedConcepts`, `currentPosition` |

### 7.2 Store 实现示例

```typescript
// lib/store/roadmap-store.ts
import { create } from 'zustand';
import type { RoadmapFramework, Concept } from '@/types';

interface RoadmapState {
  currentRoadmap: RoadmapFramework | null;
  selectedConceptId: string | null;
  isGenerating: boolean;
  generationProgress: number;
  
  // Actions
  setRoadmap: (roadmap: RoadmapFramework) => void;
  selectConcept: (conceptId: string) => void;
  setGenerating: (isGenerating: boolean, progress?: number) => void;
  reset: () => void;
}

export const useRoadmapStore = create<RoadmapState>((set) => ({
  currentRoadmap: null,
  selectedConceptId: null,
  isGenerating: false,
  generationProgress: 0,
  
  setRoadmap: (roadmap) => set({ currentRoadmap: roadmap }),
  selectConcept: (conceptId) => set({ selectedConceptId: conceptId }),
  setGenerating: (isGenerating, progress = 0) => 
    set({ isGenerating, generationProgress: progress }),
  reset: () => set({ 
    currentRoadmap: null, 
    selectedConceptId: null,
    isGenerating: false,
    generationProgress: 0 
  }),
}));
```

---

## 八、类型生成工作流

### 8.1 生成命令

```bash
# 一次性生成
npm run generate:types

# 监听后端变化自动生成
npm run generate:types:watch
```

### 8.2 生成脚本

```typescript
// scripts/generate-types.ts
import { execSync } from 'child_process';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const OUTPUT_DIR = './types/generated';

execSync(`npx openapi-typescript-codegen \
  --input ${BACKEND_URL}/openapi.json \
  --output ${OUTPUT_DIR} \
  --client axios \
  --useOptions \
  --useUnionTypes`, { stdio: 'inherit' });
```

### 8.3 类型使用示例

```typescript
// 导入生成的类型
import type { 
  RoadmapFramework, 
  Concept, 
  Tutorial,
  LearningPreferences 
} from '@/types';

// 导入生成的 API 服务
import { RoadmapService } from '@/types/generated/services';

// 使用
const roadmap = await RoadmapService.getRoadmap({ roadmapId: 'xxx' });
```

---

## 九、设计系统迁移

### 9.1 保留的设计令牌

当前 Editorial Cream & Sage 主题的核心 CSS 变量已迁移至 `app/globals.css`：

```css
:root {
  /* 背景色 */
  --background: 45 30% 96%;        /* Warm cream */
  --foreground: 45 10% 20%;        /* Deep brown-black */
  
  /* 主色调 - Sage Green */
  --primary: 140 25% 45%;          /* Muted sage */
  --primary-foreground: 45 30% 96%;
  
  /* 强调色 */
  --accent: 30 40% 50%;            /* Warm terracotta */
  --accent-foreground: 45 30% 96%;
  
  /* 卡片 */
  --card: 45 25% 92%;              /* Slightly darker cream */
  --card-foreground: 45 10% 20%;
  
  /* 边框 */
  --border: 45 20% 85%;            /* Soft cream border */
}
```

### 9.2 字体配置

```typescript
// tailwind.config.ts
fontFamily: {
  serif: ['Playfair Display', 'Georgia', 'serif'],
  sans: ['Inter', 'system-ui', 'sans-serif'],
}
```

---

## 十、开发指南

### 10.1 启动开发环境

```bash
# 安装依赖
npm install

# 生成类型（需要后端运行）
npm run generate:types

# 启动开发服务器
npm run dev
```

### 10.2 添加新页面

1. 在 `app/` 目录下创建对应的 `page.tsx`
2. 如需特殊布局，创建 `layout.tsx`
3. 使用生成的类型定义数据结构
4. 使用 Zustand store 管理状态

### 10.3 添加新 API 端点

1. 后端添加新端点后，重新生成类型
2. 在 `lib/api/endpoints.ts` 添加端点常量
3. 使用生成的 Service 或创建自定义 Hook

### 10.4 代码规范

- 组件使用 PascalCase 命名
- 文件使用 kebab-case 命名
- 类型优先使用生成的类型，避免手动定义
- 使用 `cn()` 工具函数合并 Tailwind 类名

