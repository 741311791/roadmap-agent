# Muset - AI Learning Roadmap Frontend

A modern, personalized learning roadmap application built with Next.js 14, featuring AI-powered curriculum generation and an elegant Editorial Cream & Sage design system.

---

## 🔄 重构计划（2025-12-06）

> **注意**：本项目正在进行彻底重构，完全不考虑向后兼容性。

**重构文档**：
- 📋 **[快速开始](./QUICK_START.md)** - 5 分钟快速了解重构计划
- 📖 **[重构计划](./REFACTORING_PLAN.md)** - 详细的架构设计和实施方案（20,000+ 字）
- ✅ **[执行清单](./REFACTORING_CHECKLIST.md)** - 111 个可执行任务清单
- ⚙️ **[配置更新](./CONFIG_UPDATES.md)** - 配置文件更新指南
- 📊 **[重构总结](./REFACTORING_SUMMARY.md)** - 一页纸看懂整个计划

**核心目标**：
1. ✅ API 完全对齐后端 `FRONTEND_API_GUIDE.md`
2. ✅ 补全缺失的 `lib/` 目录（API、Store、Hooks）
3. ✅ 提升代码质量（TypeScript strict + 80% 测试覆盖）

**时间线**：预计 20 个工作日（4 周）

---

## Tech Stack

| Category | Technology |
|:---------|:-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| UI Components | Shadcn/ui + Tailwind CSS |
| State Management | Zustand |
| Data Fetching | TanStack Query v5 |
| Real-time (Roadmap) | WebSocket + Polling (fallback) |
| Real-time (Chat) | SSE (Server-Sent Events) |
| Styling | Tailwind CSS + CSS Variables |

## Project Structure

```
frontend-next/
├── app/                    # Next.js App Router
│   ├── (app)/              # App route group (with AppLayout)
│   │   ├── dashboard/      # User dashboard
│   │   ├── new/            # Create new roadmap
│   │   ├── roadmap/[id]/   # Roadmap detail + learning view
│   │   └── settings/       # User settings
│   ├── methodology/        # Marketing - Methodology page
│   ├── pricing/            # Marketing - Pricing page
│   └── page.tsx            # Landing page
├── components/
│   ├── ui/                 # Shadcn/ui components
│   ├── layout/             # Layout components (AppShell, Sidebars)
│   ├── common/             # Common components (EmptyState, Spinner)
│   ├── roadmap/            # Roadmap-specific components
│   ├── learning/           # Learning view components
│   └── chat/               # AI chat components
├── lib/
│   ├── api/                # API client, WebSocket, SSE, endpoints
│   │   ├── websocket/      # WebSocket client (roadmap generation)
│   │   ├── polling/        # Polling fallback
│   │   ├── sse/            # SSE client (AI chat)
│   │   ├── endpoints/      # REST API endpoints
│   │   └── interceptors/   # Request/response interceptors
│   ├── store/              # Zustand stores
│   ├── hooks/              # Custom React hooks
│   │   ├── api/            # API hooks
│   │   ├── websocket/      # WebSocket hooks
│   │   └── sse/            # SSE hooks
│   └── utils/              # Utility functions
├── types/
│   ├── generated/          # Auto-generated from backend OpenAPI
│   └── custom/             # Frontend-specific types
└── styles/
    └── globals.css         # Global styles & CSS variables
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm
- Backend API running at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Generate TypeScript types from backend (requires backend to be running)
npm run generate:types

# Start development server
npm run dev
```

### Development Commands

```bash
npm run dev           # Start development server
npm run build         # Build for production
npm run start         # Start production server
npm run lint          # Run ESLint
npm run type-check    # Run TypeScript type checking
npm run generate:types # Generate types from backend OpenAPI schema
```

## Design System

This project uses the **Editorial Cream & Sage** design system:

- **Typography**: Playfair Display (headings) + Inter (body)
- **Colors**: Warm cream background (#FFFCF9) with sage green accents
- **Style**: Sophisticated, editorial, minimalist

### Key Design Tokens

```css
--background: 40 20% 99%;     /* Warm cream */
--foreground: 24 10% 10%;     /* Charcoal */
--sage: 140 15% 55%;          /* Sage green accent */
--primary: 24 10% 10%;        /* Primary = Foreground */
```

### Usage

```tsx
// Use semantic color classes
<div className="bg-background text-foreground">
  <h1 className="font-serif">Editorial Title</h1>
  <button className="bg-sage-600 text-white">Sage Button</button>
</div>
```

## Type System

Types are auto-generated from the backend OpenAPI schema using `openapi-typescript-codegen`.

### Generating Types

```bash
# Make sure backend is running at localhost:8000
npm run generate:types
```

### Using Types

```typescript
// Import generated types
import type { RoadmapFramework, Concept, LearningPreferences } from '@/types';

// Import custom frontend types
import type { ViewMode, ChatMessage } from '@/types/custom';
```

## State Management

Zustand stores are used for global state:

| Store | Purpose |
|:------|:--------|
| `useRoadmapStore` | Current roadmap data, generation state |
| `useChatStore` | AI chat messages, streaming state |
| `useUIStore` | Sidebar states, view modes, dialogs |
| `useLearningStore` | Learning progress, preferences |

### Example Usage

```typescript
import { useRoadmapStore, useUIStore } from '@/lib/store';

function MyComponent() {
  const currentRoadmap = useRoadmapStore((state) => state.currentRoadmap);
  const toggleSidebar = useUIStore((state) => state.toggleLeftSidebar);
  
  return (
    <button onClick={toggleSidebar}>Toggle Sidebar</button>
  );
}
```

## API Integration

### REST API

```typescript
import { roadmapsApi } from '@/lib/api/endpoints';

// Fetch roadmap
const roadmap = await roadmapsApi.getById('roadmap-id');

// Fetch tutorial
const tutorial = await roadmapsApi.getTutorial('roadmap-id', 'concept-id');
```

### WebSocket Real-time (路线图生成)

```typescript
import { RoadmapWebSocket } from '@/lib/api/websocket/roadmap-ws';

// Connect to task updates with state recovery
const ws = new RoadmapWebSocket(taskId, {
  onProgress: (event) => updateProgress(event),
  onHumanReview: (event) => showReviewDialog(event),
  onConceptStart: (event) => updateConceptStatus(event.concept_id, 'generating'),
  onCompleted: (event) => navigateToRoadmap(event.roadmap_id),
  onError: (error) => fallbackToPolling(),
});

ws.connect(true);  // include_history = true for state recovery

// Later: disconnect
ws.disconnect();
```

### SSE Streaming (AI 聊天)

```typescript
import { ChatSSE } from '@/lib/api/sse/chat-sse';

// Connect to chat modification stream
const sse = new ChatSSE({
  onAnalyzing: (event) => console.log('Analyzing:', event),
  onModifying: (event) => updateProgress(event),
  onDone: (event) => showResults(event),
  onError: (error) => console.error('Error:', error),
});

await sse.connect('/api/v1/chat/modify', { message: '...' });

// Later: disconnect
sse.disconnect();
```

## Routes

| Route | Description |
|:------|:------------|
| `/` | Landing page |
| `/methodology` | Methodology explanation |
| `/pricing` | Pricing plans |
| `/app/dashboard` | User dashboard (roadmap list) |
| `/app/new` | Create new roadmap |
| `/app/roadmap/[id]` | Roadmap detail view |
| `/app/roadmap/[id]/learn/[conceptId]` | Learning view |
| `/app/settings` | User settings |

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
OPENAPI_SCHEMA_URL=http://localhost:8000/openapi.json
NEXT_PUBLIC_ENABLE_DEBUG=true
```

## License

MIT

