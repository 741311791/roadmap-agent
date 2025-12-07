# 前端项目彻底重构计划

> **版本**: v2.0  
> **创建日期**: 2025-12-06  
> **目标**: 基于后端 API v2.0 重构前端，不考虑向后兼容  
> **保留**: 前后端共享 Pydantic 模型的自动类型生成功能

---

## 📋 目录

1. [重构目标与原则](#重构目标与原则)
2. [现状分析](#现状分析)
3. [重构架构设计](#重构架构设计)
4. [详细实施计划](#详细实施计划)
5. [里程碑与时间估算](#里程碑与时间估算)
6. [风险评估与应对](#风险评估与应对)

---

## 重构目标与原则

### 核心目标

1. **API 完全对齐**：前端 API 调用与后端 API 文档 100% 匹配
2. **类型安全**：TypeScript 严格模式，所有 API 响应完全类型化
3. **状态管理规范**：清晰的全局状态管理和数据流
4. **实时通信优化**：SSE 优先，WebSocket 作为备选方案
5. **用户体验提升**：加载状态、错误处理、乐观更新
6. **可维护性**：模块化架构，清晰的文件组织
7. **测试覆盖**：关键路径 80%+ 测试覆盖率

### 重构原则

- ✅ **破坏性变更**：不考虑向后兼容，彻底重构
- ✅ **保留类型生成**：继续使用 openapi-typescript-codegen
- ✅ **模块化优先**：每个功能模块独立、可测试
- ✅ **渐进增强**：从核心功能开始，逐步扩展
- ✅ **代码质量**：ESLint strict mode，Prettier 格式化
- ✅ **文档同步**：代码和文档同步更新

---

## 现状分析

### 存在的主要问题

#### 1. **缺失关键目录和文件**

```
❌ 缺失 lib/ 目录（但代码中多处引用）
   - lib/api/endpoints.ts
   - lib/api/websocket.ts
   - lib/store/roadmap-store.ts
   - lib/store/ui-store.ts
   - lib/store/chat-store.ts
   - lib/hooks/use-roadmap.ts
   - lib/utils.ts

❌ 缺失测试目录
   - __tests__/
   - e2e/
```

#### 2. **API 层问题**

- 没有统一的 API 客户端封装
- 直接在组件中调用 API，违反关注点分离
- 缺少请求拦截器（认证、错误处理）
- 没有统一的错误处理机制
- 缺少请求重试和超时配置

#### 3. **状态管理问题**

- Store 只有类型定义，没有实现
- 状态更新逻辑分散在各个组件中
- 缺少持久化存储（localStorage）
- 没有 DevTools 集成

#### 4. **实时通信问题**

- WebSocket 客户端功能不完整
- SSE 支持缺失（后端主推 SSE）
- 事件类型与后端不匹配
- 缺少断线重连机制
- 没有消息队列和去重

#### 5. **类型系统问题**

- 自定义类型与生成类型混用
- 缺少运行时类型验证
- 枚举值与后端不同步
- 缺少类型守卫（type guards）

#### 6. **组件架构问题**

- 组件职责不清晰
- 业务逻辑与 UI 耦合
- 缺少复用性设计
- 没有 Loading/Error 边界处理

#### 7. **开发体验问题**

- 缺少完整的开发文档
- 没有 Storybook 组件库
- 缺少调试工具
- 代码提交前检查不完善

### 技术债务清单

| 优先级 | 问题 | 影响 | 预计修复时间 |
|:---:|:---|:---|:---:|
| 🔴 P0 | 缺失 lib/ 核心文件 | 阻塞开发 | 2天 |
| 🔴 P0 | API 层重构 | 阻塞新功能 | 3天 |
| 🔴 P0 | Store 实现 | 状态管理混乱 | 2天 |
| 🟡 P1 | SSE 支持 | 实时性差 | 2天 |
| 🟡 P1 | 错误处理 | 用户体验差 | 1天 |
| 🟡 P1 | 类型同步 | 类型安全问题 | 1天 |
| 🟢 P2 | 测试覆盖 | 代码质量 | 3天 |
| 🟢 P2 | 文档补全 | 开发效率 | 2天 |

---

## 重构架构设计

### 新目录结构

```
frontend-next/
├── app/                          # Next.js App Router
│   ├── (auth)/                  # 认证路由组
│   │   ├── login/
│   │   └── register/
│   ├── (marketing)/             # 营销页面路由组
│   │   ├── page.tsx            # Landing page
│   │   ├── pricing/
│   │   └── methodology/
│   └── (app)/                   # 应用路由组
│       ├── layout.tsx          # App shell layout
│       ├── home/               # 首页
│       ├── new/                # 创建路线图
│       ├── roadmap/[id]/       # 路线图详情
│       │   ├── page.tsx
│       │   └── learn/[conceptId]/
│       ├── roadmaps/           # 路线图列表
│       ├── profile/            # 用户画像
│       └── settings/           # 设置
│
├── components/                  # React 组件
│   ├── ui/                     # Shadcn/ui 基础组件
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── ...
│   ├── layout/                 # 布局组件
│   │   ├── app-shell.tsx
│   │   ├── left-sidebar.tsx
│   │   └── right-sidebar.tsx
│   ├── roadmap/                # 路线图组件
│   │   ├── roadmap-view.tsx
│   │   ├── stage-card.tsx
│   │   ├── module-card.tsx
│   │   ├── concept-card.tsx
│   │   ├── phase-indicator.tsx
│   │   ├── generation-progress.tsx
│   │   └── human-review-dialog.tsx
│   ├── tutorial/               # 教程组件
│   │   ├── tutorial-viewer.tsx
│   │   ├── markdown-renderer.tsx
│   │   └── code-block.tsx
│   ├── chat/                   # AI 聊天组件
│   │   ├── chat-widget.tsx
│   │   ├── message-list.tsx
│   │   └── input-box.tsx
│   ├── profile/                # 用户画像组件
│   │   └── profile-form.tsx
│   └── common/                 # 通用组件
│       ├── loading-spinner.tsx
│       ├── error-boundary.tsx
│       ├── empty-state.tsx
│       └── page-header.tsx
│
├── lib/                        # 🆕 核心业务逻辑（新建）
│   ├── api/                    # API 客户端
│   │   ├── client.ts           # Axios 客户端配置
│   │   ├── endpoints/          # API 端点封装
│   │   │   ├── index.ts
│   │   │   ├── roadmaps.ts     # 路线图相关 API
│   │   │   ├── content.ts      # 内容相关 API
│   │   │   ├── users.ts        # 用户相关 API
│   │   │   └── tasks.ts        # 任务相关 API
│   │   ├── sse/                # SSE 客户端（新增）
│   │   │   ├── client.ts       # SSE 基础客户端
│   │   │   ├── roadmap-sse.ts  # 路线图生成 SSE
│   │   │   └── chat-sse.ts     # 聊天修改 SSE
│   │   ├── websocket/          # WebSocket 客户端（重构）
│   │   │   ├── client.ts
│   │   │   └── task-ws.ts
│   │   └── interceptors/       # 请求拦截器（新增）
│   │       ├── auth.ts
│   │       ├── error.ts
│   │       └── retry.ts
│   │
│   ├── store/                  # 🆕 Zustand 状态管理（实现）
│   │   ├── roadmap-store.ts    # 路线图状态
│   │   ├── chat-store.ts       # 聊天状态
│   │   ├── ui-store.ts         # UI 状态
│   │   ├── learning-store.ts   # 学习进度状态
│   │   ├── auth-store.ts       # 认证状态（新增）
│   │   └── middleware/         # Store 中间件（新增）
│   │       ├── persist.ts      # 持久化
│   │       └── devtools.ts     # DevTools
│   │
│   ├── hooks/                  # 🆕 自定义 React Hooks（新建）
│   │   ├── api/                # API 相关 hooks
│   │   │   ├── use-roadmap.ts
│   │   │   ├── use-roadmap-list.ts
│   │   │   ├── use-roadmap-generation.ts
│   │   │   ├── use-tutorial.ts
│   │   │   ├── use-resources.ts
│   │   │   ├── use-quiz.ts
│   │   │   └── use-task-status.ts
│   │   ├── sse/                # SSE 相关 hooks
│   │   │   ├── use-sse.ts
│   │   │   ├── use-roadmap-generation-stream.ts
│   │   │   └── use-chat-modification-stream.ts
│   │   ├── store/              # Store hooks
│   │   │   └── use-store-sync.ts
│   │   └── ui/                 # UI hooks
│   │       ├── use-debounce.ts
│   │       ├── use-throttle.ts
│   │       └── use-media-query.ts
│   │
│   ├── utils/                  # 工具函数
│   │   ├── cn.ts               # className 合并
│   │   ├── format.ts           # 格式化函数
│   │   ├── validation.ts       # 验证函数
│   │   ├── storage.ts          # LocalStorage 封装
│   │   └── logger.ts           # 日志工具（新增）
│   │
│   ├── schemas/                # 🆕 Zod 运行时验证（新增）
│   │   ├── roadmap.ts
│   │   ├── user.ts
│   │   └── sse-events.ts
│   │
│   └── constants/              # 🆕 常量定义（新增）
│       ├── api.ts              # API 相关常量
│       ├── routes.ts           # 路由常量
│       └── config.ts           # 配置常量
│
├── types/                      # TypeScript 类型
│   ├── generated/              # 自动生成（保留）
│   │   ├── models/
│   │   └── services/
│   ├── custom/                 # 自定义类型（重构）
│   │   ├── index.ts
│   │   ├── api.ts              # 🆕 API 扩展类型
│   │   ├── sse.ts              # 重构：与后端对齐
│   │   ├── store.ts            # 保留
│   │   ├── ui.ts               # 保留
│   │   └── phases.ts           # 保留
│   └── index.ts
│
├── __tests__/                  # 🆕 测试目录（新建）
│   ├── unit/                   # 单元测试
│   │   ├── api/
│   │   ├── store/
│   │   ├── hooks/
│   │   └── utils/
│   ├── integration/            # 集成测试
│   │   ├── roadmap-generation.test.ts
│   │   └── chat-modification.test.ts
│   └── e2e/                    # E2E 测试
│       ├── roadmap-flow.spec.ts
│       └── tutorial-learning.spec.ts
│
├── scripts/                    # 脚本
│   ├── generate-types.ts       # 保留
│   ├── check-types.ts          # 🆕 类型检查脚本
│   └── validate-env.ts         # 🆕 环境变量验证
│
├── docs/                       # 文档
│   ├── ARCHITECTURE.md         # 架构文档（更新）
│   ├── API_INTEGRATION.md      # 🆕 API 集成文档
│   ├── DEVELOPMENT.md          # 🆕 开发指南
│   └── TESTING.md              # 🆕 测试指南
│
└── package.json                # 依赖配置（更新）
```

### 核心模块设计

#### 1. API 客户端架构

```typescript
// lib/api/client.ts - Axios 客户端配置
import axios from 'axios';
import { authInterceptor } from './interceptors/auth';
import { errorInterceptor } from './interceptors/error';
import { retryInterceptor } from './interceptors/retry';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(authInterceptor);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  errorInterceptor
);

// 重试拦截器
retryInterceptor(apiClient);
```

```typescript
// lib/api/endpoints/roadmaps.ts - 路线图 API 端点
import { apiClient } from '../client';
import type { UserRequest, RoadmapFramework, TaskStatusResponse } from '@/types';

export const roadmapsApi = {
  // 生成路线图（同步）
  generate: async (request: UserRequest) => {
    const { data } = await apiClient.post('/roadmaps/generate', request);
    return data;
  },

  // 获取路线图详情
  getById: async (roadmapId: string) => {
    const { data } = await apiClient.get<RoadmapFramework>(`/roadmaps/${roadmapId}`);
    return data;
  },

  // 获取用户的所有路线图
  getUserRoadmaps: async (userId: string, params?: { status?: string; limit?: number; offset?: number }) => {
    const { data } = await apiClient.get(`/roadmaps/user/${userId}`, { params });
    return data;
  },

  // 查询任务状态
  getTaskStatus: async (taskId: string) => {
    const { data } = await apiClient.get<TaskStatusResponse>(`/roadmaps/tasks/${taskId}/status`);
    return data;
  },

  // 提交人工审核
  submitApproval: async (taskId: string, approved: boolean, feedback?: string) => {
    const { data } = await apiClient.post(`/roadmaps/tasks/${taskId}/approve`, {
      approved,
      feedback,
    });
    return data;
  },

  // 重试失败的内容生成
  retryFailed: async (roadmapId: string) => {
    const { data } = await apiClient.post(`/roadmaps/${roadmapId}/retry-failed`);
    return data;
  },
};
```

#### 2. WebSocket 客户端架构（路线图生成 - 主要方案）

```typescript
// lib/api/websocket/roadmap-ws.ts - 路线图生成 WebSocket 客户端
import type {
  ProgressEvent,
  HumanReviewRequiredEvent,
  ConceptStartEvent,
  ConceptCompleteEvent,
  ConceptFailedEvent,
  BatchStartEvent,
  BatchCompleteEvent,
  CompletedEvent,
  FailedEvent,
  CurrentStatusEvent,
} from '@/types/custom/websocket';

export interface RoadmapWSHandlers {
  onConnected?: () => void;
  onCurrentStatus?: (event: CurrentStatusEvent) => void;
  onProgress?: (event: ProgressEvent) => void;
  onHumanReview?: (event: HumanReviewRequiredEvent) => void;
  onConceptStart?: (event: ConceptStartEvent) => void;
  onConceptComplete?: (event: ConceptCompleteEvent) => void;
  onConceptFailed?: (event: ConceptFailedEvent) => void;
  onBatchStart?: (event: BatchStartEvent) => void;
  onBatchComplete?: (event: BatchCompleteEvent) => void;
  onCompleted?: (event: CompletedEvent) => void;
  onFailed?: (event: FailedEvent) => void;
  onError?: (error: Error) => void;
  onClose?: (reason: string) => void;
}

export class RoadmapWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private handlers: RoadmapWSHandlers;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(taskId: string, handlers: RoadmapWSHandlers) {
    this.taskId = taskId;
    this.handlers = handlers;
  }

  connect(includeHistory = true) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const url = `${wsUrl}/ws/${this.taskId}?include_history=${includeHistory}`;
    
    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
      this.startHeartbeat();
    } catch (error) {
      console.error('[WS] Connection failed:', error);
      this.handlers.onError?.(error as Error);
    }
  }

  private setupEventHandlers() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('[WS] Connected to task:', this.taskId);
      this.reconnectAttempts = 0;
      this.handlers.onConnected?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      this.handlers.onError?.(new Error('WebSocket connection error'));
    };

    this.ws.onclose = (event) => {
      console.log('[WS] Connection closed:', event.code, event.reason);
      this.stopHeartbeat();
      
      const reason = event.reason || 'unknown';
      this.handlers.onClose?.(reason);
      
      // 仅在非正常关闭时重连
      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnect();
      }
    };
  }

  private handleMessage(data: any) {
    switch (data.type) {
      case 'connected':
        console.log('[WS] Connection confirmed');
        break;
        
      case 'current_status':
        this.handlers.onCurrentStatus?.(data);
        break;
        
      case 'progress':
        this.handlers.onProgress?.(data);
        break;
        
      case 'human_review_required':
        this.handlers.onHumanReview?.(data);
        break;
        
      case 'concept_start':
        this.handlers.onConceptStart?.(data);
        break;
        
      case 'concept_complete':
        this.handlers.onConceptComplete?.(data);
        break;
        
      case 'concept_failed':
        this.handlers.onConceptFailed?.(data);
        break;
        
      case 'batch_start':
        this.handlers.onBatchStart?.(data);
        break;
        
      case 'batch_complete':
        this.handlers.onBatchComplete?.(data);
        break;
        
      case 'completed':
        this.handlers.onCompleted?.(data);
        this.disconnect();
        break;
        
      case 'failed':
        this.handlers.onFailed?.(data);
        this.disconnect();
        break;
        
      case 'closing':
        console.log('[WS] Server closing connection:', data.reason);
        break;
        
      case 'pong':
        // 心跳响应
        break;
        
      default:
        console.warn('[WS] Unknown message type:', data.type);
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);  // 每 30 秒发送一次心跳
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private reconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(
      `[WS] Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  // 主动请求当前状态
  requestStatus() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'get_status' }));
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
```

```typescript
// lib/api/polling/task-polling.ts - 轮询客户端（WebSocket 降级方案）
import { roadmapsApi } from '../endpoints/roadmaps';
import type { TaskStatusResponse } from '@/types';

export interface PollingHandlers {
  onStatusUpdate: (status: TaskStatusResponse) => void;
  onComplete: (status: TaskStatusResponse) => void;
  onError: (error: Error) => void;
}

export class TaskPolling {
  private taskId: string;
  private handlers: PollingHandlers;
  private intervalId: NodeJS.Timeout | null = null;
  private isRunning = false;

  constructor(taskId: string, handlers: PollingHandlers) {
    this.taskId = taskId;
    this.handlers = handlers;
  }

  start(intervalMs = 2000) {
    if (this.isRunning) {
      console.warn('[Polling] Already running');
      return;
    }

    console.log('[Polling] Started for task:', this.taskId);
    this.isRunning = true;

    this.intervalId = setInterval(async () => {
      try {
        const status = await roadmapsApi.getTaskStatus(this.taskId);
        this.handlers.onStatusUpdate(status);

        // 任务结束时自动停止
        if (status.status === 'completed' || status.status === 'failed') {
          this.handlers.onComplete(status);
          this.stop();
        }
      } catch (error) {
        console.error('[Polling] Error:', error);
        this.handlers.onError(error as Error);
      }
    }, intervalMs);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      this.isRunning = false;
      console.log('[Polling] Stopped');
    }
  }
}
```

#### 4. SSE 客户端架构（AI 聊天场景）

```typescript
// lib/api/sse/chat-sse.ts - AI 聊天流式客户端
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { ChatModificationEvent } from '@/types/custom/sse';

export interface ChatSSEHandlers {
  onAnalyzing?: (event: AnalyzingEvent) => void;
  onIntents?: (event: IntentsEvent) => void;
  onModifying?: (event: ModifyingEvent) => void;
  onResult?: (event: ResultEvent) => void;
  onDone?: (event: ModificationDoneEvent) => void;
  onError?: (event: ModificationErrorEvent) => void;
}

export class ChatSSE {
  private abortController: AbortController | null = null;
  private handlers: ChatSSEHandlers;

  constructor(handlers: ChatSSEHandlers) {
    this.handlers = handlers;
  }

  async connect(endpoint: string, requestBody: any) {
    this.abortController = new AbortController();

    await fetchEventSource(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
      signal: this.abortController.signal,
      
      onopen: async (response) => {
        if (response.ok) {
          console.log('[SSE] Chat connection opened');
        } else {
          throw new Error(`SSE connection failed: ${response.status}`);
        }
      },
      
      onmessage: (event) => {
        try {
          const data: ChatModificationEvent = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('[SSE] Failed to parse message:', error);
        }
      },
      
      onerror: (error) => {
        console.error('[SSE] Error:', error);
        throw error;
      },
    });
  }

  private handleMessage(data: ChatModificationEvent) {
    switch (data.type) {
      case 'analyzing':
        this.handlers.onAnalyzing?.(data);
        break;
      case 'intents':
        this.handlers.onIntents?.(data);
        break;
      case 'modifying':
        this.handlers.onModifying?.(data);
        break;
      case 'result':
        this.handlers.onResult?.(data);
        break;
      case 'done':
        this.handlers.onDone?.(data);
        this.disconnect();
        break;
      case 'error':
        this.handlers.onError?.(data);
        this.disconnect();
        break;
    }
  }

  disconnect() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
      console.log('[SSE] Chat connection closed');
    }
  }
}
```

#### 3. Zustand Store 实现

```typescript
// lib/store/roadmap-store.ts - 路线图状态管理
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { RoadmapStore } from '@/types/custom/store';

export const useRoadmapStore = create<RoadmapStore>()(
  devtools(
    persist(
      (set, get) => ({
        // State
        currentRoadmap: null,
        isLoading: false,
        error: null,
        isGenerating: false,
        generationProgress: 0,
        currentStep: null,
        generationPhase: 'idle',
        generationBuffer: '',
        tutorialProgress: { completed: 0, total: 0 },
        activeTaskId: null,
        activeGenerationPhase: null,
        isLiveGenerating: false,
        history: [],
        selectedConceptId: null,

        // Actions
        setRoadmap: (roadmap) => set({ currentRoadmap: roadmap }),
        
        clearRoadmap: () => set({ 
          currentRoadmap: null, 
          selectedConceptId: null 
        }),
        
        setLoading: (loading) => set({ isLoading: loading }),
        
        setError: (error) => set({ error }),
        
        setGenerating: (generating) => set({ 
          isGenerating: generating,
          ...(generating ? {} : { generationProgress: 0, currentStep: null })
        }),
        
        updateProgress: (step, progress) => set({ 
          currentStep: step, 
          generationProgress: progress 
        }),
        
        setHistory: (history) => set({ history }),
        
        addToHistory: (roadmap) => set((state) => ({
          history: [roadmap, ...state.history]
        })),
        
        selectConcept: (conceptId) => set({ selectedConceptId: conceptId }),
        
        updateConceptStatus: (conceptId, status) => set((state) => {
          if (!state.currentRoadmap) return state;
          
          const updatedRoadmap = { ...state.currentRoadmap };
          
          // Find and update concept
          for (const stage of updatedRoadmap.stages) {
            for (const module of stage.modules) {
              const concept = module.concepts.find(c => c.concept_id === conceptId);
              if (concept) {
                Object.assign(concept, status);
                break;
              }
            }
          }
          
          return { currentRoadmap: updatedRoadmap };
        }),

        // Generation streaming
        setGenerationPhase: (phase) => set({ generationPhase: phase }),
        
        appendGenerationBuffer: (chunk) => set((state) => ({
          generationBuffer: state.generationBuffer + chunk
        })),
        
        clearGenerationBuffer: () => set({ generationBuffer: '' }),
        
        updateTutorialProgress: (completed, total) => set({
          tutorialProgress: { completed, total }
        }),

        // Live generation tracking
        setActiveTask: (taskId) => set({ activeTaskId: taskId }),
        
        setActiveGenerationPhase: (phase) => set({ activeGenerationPhase: phase }),
        
        setLiveGenerating: (isLive) => set({ isLiveGenerating: isLive }),
        
        clearLiveGeneration: () => set({
          activeTaskId: null,
          activeGenerationPhase: null,
          isLiveGenerating: false,
        }),
      }),
      {
        name: 'roadmap-storage',
        partialize: (state) => ({
          // Only persist these fields
          history: state.history,
          selectedConceptId: state.selectedConceptId,
        }),
      }
    ),
    {
      name: 'RoadmapStore',
    }
  )
);
```

#### 4. 自定义 Hooks

```typescript
// lib/hooks/api/use-roadmap.ts - 路线图数据获取 Hook
import { useQuery } from '@tanstack/react-query';
import { roadmapsApi } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';

export function useRoadmap(roadmapId: string | undefined) {
  const setRoadmap = useRoadmapStore((state) => state.setRoadmap);
  const setError = useRoadmapStore((state) => state.setError);

  return useQuery({
    queryKey: ['roadmap', roadmapId],
    queryFn: async () => {
      if (!roadmapId) throw new Error('Roadmap ID is required');
      const roadmap = await roadmapsApi.getById(roadmapId);
      setRoadmap(roadmap);
      return roadmap;
    },
    enabled: !!roadmapId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    onError: (error: Error) => {
      setError(error.message);
    },
  });
}
```

```typescript
// lib/hooks/websocket/use-roadmap-generation-ws.ts - 路线图生成 WebSocket Hook（主要方案）
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RoadmapWebSocket, type RoadmapWSHandlers } from '@/lib/api/websocket/roadmap-ws';
import { TaskPolling } from '@/lib/api/polling/task-polling';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { roadmapsApi } from '@/lib/api/endpoints';
import type { TaskStatusResponse } from '@/types';

export interface UseRoadmapGenerationWSOptions {
  onComplete?: (roadmapId: string) => void;
  onError?: (error: string) => void;
}

export function useRoadmapGenerationWS(
  taskId: string | null,
  options?: UseRoadmapGenerationWSOptions
) {
  const router = useRouter();
  const wsRef = useRef<RoadmapWebSocket | null>(null);
  const pollingRef = useRef<TaskPolling | null>(null);
  const [connectionType, setConnectionType] = useState<'ws' | 'polling'>('ws');
  const [isConnected, setIsConnected] = useState(false);

  const {
    updateProgress,
    setRoadmap,
    setError,
    updateConceptStatus,
  } = useRoadmapStore();

  useEffect(() => {
    if (!taskId) return;

    // 优先使用 WebSocket
    if (connectionType === 'ws') {
      const handlers: RoadmapWSHandlers = {
        onConnected: () => {
          console.log('[WS] Connected successfully');
          setIsConnected(true);
        },

        onCurrentStatus: (event) => {
          console.log('[WS] Current status:', event);
          
          // 恢复 UI 状态
          updateProgress(event.current_step, calculateProgress(event.current_step));
          
          // 如果已完成，直接导航
          if (event.status === 'completed' && event.roadmap_id) {
            options?.onComplete?.(event.roadmap_id);
          }
        },

        onProgress: (event) => {
          console.log('[WS] Progress:', event);
          const progress = calculateProgress(event.step);
          updateProgress(event.step, progress);
          
          // 早期导航：roadmap_id 可用时
          if (event.data?.roadmap_id && event.step === 'curriculum_design') {
            router.push(`/app/roadmap/${event.data.roadmap_id}`);
          }
        },

        onHumanReview: (event) => {
          console.log('[WS] Human review required:', event);
          // 显示审核对话框
          // showReviewDialog(event);
        },

        onConceptStart: (event) => {
          console.log('[WS] Concept start:', event);
          updateConceptStatus(event.concept_id, { tutorial_status: 'generating' });
        },

        onConceptComplete: (event) => {
          console.log('[WS] Concept complete:', event);
          updateConceptStatus(event.concept_id, { tutorial_status: 'completed' });
        },

        onBatchComplete: (event) => {
          console.log('[WS] Batch complete:', event);
          // 更新批次进度
        },

        onCompleted: (event) => {
          console.log('[WS] Task completed:', event);
          options?.onComplete?.(event.roadmap_id);
        },

        onFailed: (event) => {
          console.error('[WS] Task failed:', event);
          setError(event.error);
          options?.onError?.(event.error);
        },

        onError: (error) => {
          console.warn('[WS] Connection error, fallback to polling:', error);
          setConnectionType('polling');
          setIsConnected(false);
        },

        onClose: (reason) => {
          console.log('[WS] Connection closed:', reason);
          setIsConnected(false);
        },
      };

      const ws = new RoadmapWebSocket(taskId, handlers);
      ws.connect(true);  // include_history = true
      wsRef.current = ws;

      return () => {
        ws.disconnect();
      };
    }

    // 降级方案：轮询
    if (connectionType === 'polling') {
      const polling = new TaskPolling(taskId, {
        onStatusUpdate: (status: TaskStatusResponse) => {
          updateProgress(status.current_step, calculateProgress(status.current_step));
        },

        onComplete: (status: TaskStatusResponse) => {
          if (status.status === 'completed' && status.roadmap_id) {
            options?.onComplete?.(status.roadmap_id);
          } else if (status.status === 'failed') {
            setError(status.error_message || '任务失败');
            options?.onError?.(status.error_message || '任务失败');
          }
        },

        onError: (error: Error) => {
          console.error('[Polling] Error:', error);
          setError(error.message);
        },
      });

      polling.start(2000);
      pollingRef.current = polling;

      return () => {
        polling.stop();
      };
    }
  }, [taskId, connectionType]);

  return {
    connectionType,
    isConnected,
    requestStatus: () => wsRef.current?.requestStatus(),
    disconnect: () => {
      wsRef.current?.disconnect();
      pollingRef.current?.stop();
    },
  };
}

// 辅助函数：根据步骤计算进度
function calculateProgress(step: string): number {
  const stepProgress: Record<string, number> = {
    'queued': 5,
    'intent_analysis': 20,
    'curriculum_design': 40,
    'structure_validation': 50,
    'human_review': 60,
    'content_generation': 80,
    'completed': 100,
  };
  return stepProgress[step] || 0;
}
```

```typescript
// lib/hooks/sse/use-chat-stream.ts - AI 聊天流式 Hook（SSE）
import { useEffect, useRef, useState } from 'react';
import { ChatSSE, type ChatSSEHandlers } from '@/lib/api/sse/chat-sse';
import { useChatStore } from '@/lib/store/chat-store';

export interface UseChatStreamOptions {
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function useChatStream(
  endpoint: string | null,
  requestBody: any | null,
  options?: UseChatStreamOptions
) {
  const sseRef = useRef<ChatSSE | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const {
    appendToStream,
    completeStream,
    setError,
  } = useChatStore();

  useEffect(() => {
    if (!endpoint || !requestBody) return;

    const handlers: ChatSSEHandlers = {
      onAnalyzing: (event) => {
        console.log('[SSE] Analyzing:', event);
        setIsStreaming(true);
      },

      onIntents: (event) => {
        console.log('[SSE] Intents detected:', event);
        // 显示意图分析结果
      },

      onModifying: (event) => {
        console.log('[SSE] Modifying:', event);
        appendToStream(`正在修改：${event.target_name}\n`);
      },

      onResult: (event) => {
        console.log('[SSE] Result:', event);
        if (event.success) {
          appendToStream(`✓ ${event.target_name} 修改成功\n`);
        } else {
          appendToStream(`✗ ${event.target_name} 修改失败：${event.error_message}\n`);
        }
      },

      onDone: (event) => {
        console.log('[SSE] Done:', event);
        completeStream();
        setIsStreaming(false);
        options?.onComplete?.();
      },

      onError: (event) => {
        console.error('[SSE] Error:', event);
        setError(event.message);
        setIsStreaming(false);
        options?.onError?.(event.message);
      },
    };

    const sse = new ChatSSE(handlers);
    sse.connect(endpoint, requestBody);
    sseRef.current = sse;
    setIsStreaming(true);

    return () => {
      sse.disconnect();
      setIsStreaming(false);
    };
  }, [endpoint, requestBody]);

  return {
    isStreaming,
    disconnect: () => sseRef.current?.disconnect(),
  };
}
```

---

## 详细实施计划

### Phase 1: 基础设施重建（第 1-3 天）

#### 1.1 创建 lib/ 目录核心结构

**任务清单**:

- [ ] 创建 `lib/api/` 目录结构
- [ ] 创建 `lib/store/` 目录结构
- [ ] 创建 `lib/hooks/` 目录结构
- [ ] 创建 `lib/utils/` 目录结构
- [ ] 创建 `lib/constants/` 目录结构
- [ ] 创建 `lib/schemas/` 目录结构

**产出物**:
- 完整的目录结构
- README 文件说明每个目录用途

---

#### 1.2 实现 API 客户端基础设施

**任务清单**:

1. **创建 Axios 客户端** (`lib/api/client.ts`)
   - [ ] 基础配置（baseURL, timeout, headers）
   - [ ] 环境变量配置
   - [ ] TypeScript 类型定义

2. **实现请求拦截器** (`lib/api/interceptors/`)
   - [ ] `auth.ts` - 添加认证 token
   - [ ] `error.ts` - 统一错误处理
   - [ ] `retry.ts` - 失败重试逻辑
   - [ ] `logger.ts` - 请求日志（开发环境）

3. **封装 API 端点** (`lib/api/endpoints/`)
   - [ ] `roadmaps.ts` - 路线图相关 API
   - [ ] `content.ts` - 内容相关 API（教程、资源、测验）
   - [ ] `users.ts` - 用户相关 API
   - [ ] `tasks.ts` - 任务相关 API
   - [ ] `index.ts` - 统一导出

**示例代码**:

```typescript
// lib/api/endpoints/roadmaps.ts
import { apiClient } from '../client';
import type {
  UserRequest,
  GenerateRoadmapResponse,
  RoadmapDetail,
  RoadmapListResponse,
  TaskStatusResponse,
  ApprovalRequest,
  ApprovalResponse,
} from '@/types';

export const roadmapsApi = {
  // 生成路线图（同步）
  generate: async (request: UserRequest): Promise<GenerateRoadmapResponse> => {
    const { data } = await apiClient.post('/roadmaps/generate', request);
    return data;
  },

  // 获取路线图详情
  getById: async (roadmapId: string): Promise<RoadmapDetail> => {
    const { data } = await apiClient.get(`/roadmaps/${roadmapId}`);
    return data;
  },

  // 获取用户的所有路线图
  getUserRoadmaps: async (
    userId: string,
    params?: { status?: string; limit?: number; offset?: number }
  ): Promise<RoadmapListResponse> => {
    const { data } = await apiClient.get(`/roadmaps/user/${userId}`, { params });
    return data;
  },

  // 查询任务状态
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await apiClient.get(`/roadmaps/tasks/${taskId}/status`);
    return data;
  },

  // 提交人工审核
  submitApproval: async (
    taskId: string,
    approval: ApprovalRequest
  ): Promise<ApprovalResponse> => {
    const { data } = await apiClient.post(`/roadmaps/tasks/${taskId}/approve`, approval);
    return data;
  },

  // 重试失败的内容生成
  retryFailed: async (roadmapId: string) => {
    const { data } = await apiClient.post(`/roadmaps/${roadmapId}/retry-failed`);
    return data;
  },
};
```

**测试清单**:
- [ ] 测试 API 客户端基础配置
- [ ] 测试请求拦截器
- [ ] 测试响应拦截器
- [ ] 测试错误处理
- [ ] 测试重试逻辑

---

#### 1.3 实现实时通信客户端（WebSocket + SSE）

**目录结构**:

```typescript
lib/api/
├── websocket/              # 路线图生成场景（主要方案，优先级 P0）
│   ├── client.ts           # WebSocket 基础客户端
│   ├── roadmap-ws.ts       # 路线图生成 WebSocket
│   ├── reconnect.ts        # 断线重连逻辑
│   └── heartbeat.ts        # 心跳管理
│
├── sse/                    # AI 聊天场景（优先级 P1）
│   ├── client.ts           # SSE 基础客户端
│   └── chat-sse.ts         # 聊天流式客户端
│
└── polling/                # 轮询备用方案（优先级 P0）
    └── task-polling.ts     # 任务状态轮询（WebSocket 降级）
```

**任务清单**:

1. **WebSocket 基础客户端** (`lib/api/websocket/client.ts`) - 🔴 P0
   - [ ] 基础连接管理（connect/disconnect）
   - [ ] 事件监听和分发
   - [ ] 自动重连（指数退避）
   - [ ] 错误处理和降级

2. **路线图生成 WebSocket** (`lib/api/websocket/roadmap-ws.ts`) - 🔴 P0
   - [ ] 完整事件类型处理（progress, human_review, concept_*, batch_*, completed, failed）
   - [ ] 心跳机制（每 30 秒发送 ping）
   - [ ] 主动请求状态（get_status 消息）
   - [ ] 状态恢复（include_history 参数）
   - [ ] 连接管理（连接、断开、重连）

3. **轮询客户端** (`lib/api/polling/task-polling.ts`) - 🔴 P0
   - [ ] 轮询逻辑（2 秒间隔）
   - [ ] 自动停止（任务完成/失败）
   - [ ] 与 WebSocket 降级集成

4. **SSE 基础客户端** (`lib/api/sse/client.ts`) - 🟡 P1
   - [ ] 基础连接管理
   - [ ] 事件监听
   - [ ] 自动重连
   - [ ] 错误处理

5. **聊天流式 SSE** (`lib/api/sse/chat-sse.ts`) - 🟡 P1
   - [ ] 聊天修改流程事件监听
   - [ ] 意图分析处理
   - [ ] 流式输出处理
   - [ ] 修改结果处理

**注意事项**:
- WebSocket 优先用于路线图生成（支持人工审核、状态恢复）
- 轮询作为 WebSocket 的降级方案（连接失败时）
- SSE 用于 AI 聊天场景（流式输出、逐字显示）
- EventSource 不支持 POST，考虑使用 `@microsoft/fetch-event-source`

**测试清单**:
- [ ] 测试 WebSocket 连接和断开
- [ ] 测试事件解析和分发
- [ ] 测试断线重连
- [ ] 测试心跳机制
- [ ] 测试降级到轮询
- [ ] 测试状态恢复（include_history）
- [ ] 测试 SSE 连接（AI 聊天）

---

#### 1.4 实现 Zustand Stores

**任务清单**:

1. **路线图 Store** (`lib/store/roadmap-store.ts`)
   - [ ] 基础状态定义
   - [ ] 路线图数据管理
   - [ ] 生成状态管理
   - [ ] 持久化配置
   - [ ] DevTools 集成

2. **聊天 Store** (`lib/store/chat-store.ts`)
   - [ ] 消息列表管理
   - [ ] 流式输入处理
   - [ ] 上下文管理

3. **UI Store** (`lib/store/ui-store.ts`)
   - [ ] 侧边栏状态
   - [ ] 对话框状态
   - [ ] 视图模式

4. **学习进度 Store** (`lib/store/learning-store.ts`)
   - [ ] 进度追踪
   - [ ] 完成状态
   - [ ] 时间统计

**测试清单**:
- [ ] 测试状态更新
- [ ] 测试持久化
- [ ] 测试派生状态
- [ ] 测试并发更新

---

### Phase 2: API 集成与类型同步（第 4-6 天）

#### 2.1 更新类型生成脚本

**任务清单**:

- [ ] 更新 `scripts/generate-types.ts`
- [ ] 添加类型验证脚本
- [ ] 添加类型差异检测
- [ ] 配置自动类型生成（git hooks）

**脚本示例**:

```typescript
// scripts/check-types.ts
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

async function checkTypes() {
  console.log('🔍 Checking type definitions...');

  // 1. 从后端获取最新 OpenAPI schema
  const schemaUrl = process.env.BACKEND_URL + '/openapi.json';
  const response = await fetch(schemaUrl);
  const remoteSchema = await response.json();

  // 2. 读取本地 schema
  const localSchemaPath = path.join(__dirname, '../.openapi-cache.json');
  const localSchema = JSON.parse(fs.readFileSync(localSchemaPath, 'utf-8'));

  // 3. 比较差异
  if (JSON.stringify(remoteSchema) !== JSON.stringify(localSchema)) {
    console.warn('⚠️  Backend API schema has changed!');
    console.log('Run `npm run generate:types` to update types.');
    process.exit(1);
  }

  console.log('✅ Types are up to date!');
}

checkTypes();
```

---

#### 2.2 同步枚举和常量

**任务清单**:

1. **创建常量文件** (`lib/constants/`)
   - [ ] `api.ts` - API 相关常量
   - [ ] `status.ts` - 状态枚举
   - [ ] `routes.ts` - 路由常量

**示例代码**:

```typescript
// lib/constants/status.ts
// 与后端完全同步的状态枚举

export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  HUMAN_REVIEW_PENDING = 'human_review_pending',
  COMPLETED = 'completed',
  PARTIAL_FAILURE = 'partial_failure',
  FAILED = 'failed',
}

export enum ContentStatus {
  PENDING = 'pending',
  GENERATING = 'generating',  // 前端临时状态
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum WorkflowStep {
  INIT = 'init',
  QUEUED = 'queued',
  STARTING = 'starting',
  INTENT_ANALYSIS = 'intent_analysis',
  CURRICULUM_DESIGN = 'curriculum_design',
  STRUCTURE_VALIDATION = 'structure_validation',
  HUMAN_REVIEW = 'human_review',
  ROADMAP_EDIT = 'roadmap_edit',
  CONTENT_GENERATION = 'content_generation',
  TUTORIAL_GENERATION = 'tutorial_generation',
  RESOURCE_RECOMMENDATION = 'resource_recommendation',
  QUIZ_GENERATION = 'quiz_generation',
  FINALIZING = 'finalizing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// 状态显示配置
export const TASK_STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  [TaskStatus.PENDING]: { label: '排队中', color: 'gray' },
  [TaskStatus.PROCESSING]: { label: '处理中', color: 'blue' },
  [TaskStatus.HUMAN_REVIEW_PENDING]: { label: '等待审核', color: 'yellow' },
  [TaskStatus.COMPLETED]: { label: '已完成', color: 'green' },
  [TaskStatus.PARTIAL_FAILURE]: { label: '部分失败', color: 'orange' },
  [TaskStatus.FAILED]: { label: '失败', color: 'red' },
};
```

---

#### 2.3 实现 Zod Schema 验证（新增）

**任务清单**:

1. **创建 Zod Schema** (`lib/schemas/`)
   - [ ] `roadmap.ts` - 路线图数据验证
   - [ ] `sse-events.ts` - SSE 事件验证
   - [ ] `user.ts` - 用户数据验证

**示例代码**:

```typescript
// lib/schemas/sse-events.ts
import { z } from 'zod';

// 基础 SSE 事件
export const BaseSSEEventSchema = z.object({
  type: z.string(),
  timestamp: z.string().datetime(),
});

// 进度事件
export const ProgressEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('progress'),
  task_id: z.string(),
  current_step: z.string(),
  message: z.string().optional(),
  data: z.record(z.unknown()).optional(),
});

// 完成事件
export const CompleteEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('complete'),
  task_id: z.string(),
  roadmap_id: z.string(),
  status: z.enum(['completed', 'partial_failure']),
});

// 错误事件
export const ErrorEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('error'),
  task_id: z.string(),
  error: z.string(),
  step: z.string().optional(),
});

// 联合类型
export const RoadmapGenerationEventSchema = z.discriminatedUnion('type', [
  ProgressEventSchema,
  CompleteEventSchema,
  ErrorEventSchema,
  // ... 其他事件类型
]);

// 验证函数
export function validateSSEEvent(data: unknown) {
  return RoadmapGenerationEventSchema.parse(data);
}
```

**测试清单**:
- [ ] 测试 Schema 验证
- [ ] 测试错误消息
- [ ] 测试类型推导

---

#### 2.4 更新 SSE 事件类型

**任务清单**:

- [ ] 重构 `types/custom/sse.ts`
- [ ] 与后端 API 文档完全对齐
- [ ] 添加详细的注释说明
- [ ] 导出类型守卫函数

**更新后的类型**:

```typescript
// types/custom/sse.ts
// 完全与后端 API 文档对齐

import type { WorkflowStep, TaskStatus, ContentStatus } from '@/lib/constants/status';

// ============================================================
// 基础 SSE 事件
// ============================================================

export interface BaseSSEEvent {
  type: string;
  timestamp: string;  // ISO 8601
}

// ============================================================
// 路线图生成 SSE 事件（与后端 FRONTEND_API_GUIDE.md 完全对齐）
// ============================================================

export interface ProgressEvent extends BaseSSEEvent {
  type: 'progress';
  task_id: string;
  current_step: WorkflowStep;
  message: string;
  data?: {
    roadmap_id?: string;
    stages_count?: number;
    total_concepts?: number;
    [key: string]: unknown;
  };
}

export interface StepCompleteEvent extends BaseSSEEvent {
  type: 'step_complete';
  task_id: string;
  step: WorkflowStep;
  result?: {
    roadmap?: RoadmapFramework;
    [key: string]: unknown;
  };
}

export interface CompleteEvent extends BaseSSEEvent {
  type: 'complete';
  task_id: string;
  roadmap_id: string;
  status: 'completed' | 'partial_failure';
  tutorials_count?: number;
  failed_count?: number;
}

export interface ErrorEvent extends BaseSSEEvent {
  type: 'error';
  task_id: string;
  error: string;
  step?: WorkflowStep;
}

export type RoadmapGenerationEvent =
  | ProgressEvent
  | StepCompleteEvent
  | CompleteEvent
  | ErrorEvent;

// ============================================================
// 类型守卫函数
// ============================================================

export function isProgressEvent(event: BaseSSEEvent): event is ProgressEvent {
  return event.type === 'progress';
}

export function isStepCompleteEvent(event: BaseSSEEvent): event is StepCompleteEvent {
  return event.type === 'step_complete';
}

export function isCompleteEvent(event: BaseSSEEvent): event is CompleteEvent {
  return event.type === 'complete';
}

export function isErrorEvent(event: BaseSSEEvent): event is ErrorEvent {
  return event.type === 'error';
}
```

---

### Phase 3: React Hooks 实现（第 7-9 天）

#### 3.1 实现 API Hooks

**任务清单**:

1. **路线图相关 Hooks** (`lib/hooks/api/`)
   - [ ] `use-roadmap.ts` - 获取路线图详情
   - [ ] `use-roadmap-list.ts` - 获取路线图列表
   - [ ] `use-task-status.ts` - 查询任务状态（轮询）
   - [ ] `use-roadmap-generation.ts` - 生成路线图（mutation）

2. **内容相关 Hooks** (`lib/hooks/api/`)
   - [ ] `use-tutorial.ts` - 获取教程内容
   - [ ] `use-resources.ts` - 获取学习资源
   - [ ] `use-quiz.ts` - 获取测验题目
   - [ ] `use-content-modification.ts` - 修改内容

**示例代码**:

```typescript
// lib/hooks/api/use-roadmap.ts
import { useQuery } from '@tanstack/react-query';
import { roadmapsApi } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';

export function useRoadmap(roadmapId: string | undefined) {
  const setRoadmap = useRoadmapStore((state) => state.setRoadmap);
  const setError = useRoadmapStore((state) => state.setError);

  return useQuery({
    queryKey: ['roadmap', roadmapId],
    queryFn: async () => {
      if (!roadmapId) throw new Error('Roadmap ID is required');
      const roadmap = await roadmapsApi.getById(roadmapId);
      setRoadmap(roadmap);
      return roadmap;
    },
    enabled: !!roadmapId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    onError: (error: Error) => {
      setError(error.message);
    },
  });
}
```

```typescript
// lib/hooks/api/use-roadmap-generation.ts
import { useMutation } from '@tanstack/react-query';
import { roadmapsApi } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest } from '@/types';

export function useRoadmapGeneration() {
  const setGenerating = useRoadmapStore((state) => state.setGenerating);
  const setError = useRoadmapStore((state) => state.setError);
  const setActiveTask = useRoadmapStore((state) => state.setActiveTask);

  return useMutation({
    mutationFn: (request: UserRequest) => roadmapsApi.generate(request),
    onMutate: () => {
      setGenerating(true);
      setError(null);
    },
    onSuccess: (data) => {
      setActiveTask(data.task_id);
    },
    onError: (error: Error) => {
      setError(error.message);
      setGenerating(false);
    },
  });
}
```

```typescript
// lib/hooks/api/use-task-status.ts
import { useQuery } from '@tanstack/react-query';
import { roadmapsApi } from '@/lib/api/endpoints';

export function useTaskStatus(
  taskId: string | undefined,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  return useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => {
      if (!taskId) throw new Error('Task ID is required');
      return roadmapsApi.getTaskStatus(taskId);
    },
    enabled: options?.enabled ?? !!taskId,
    refetchInterval: options?.refetchInterval ?? 2000, // 默认 2 秒轮询
    refetchIntervalInBackground: false,
  });
}
```

**测试清单**:
- [ ] 测试数据获取
- [ ] 测试错误处理
- [ ] 测试缓存策略
- [ ] 测试轮询逻辑

---

#### 3.2 实现 SSE Hooks

**任务清单**:

1. **基础 SSE Hook** (`lib/hooks/sse/use-sse.ts`)
   - [ ] 通用 SSE 连接管理
   - [ ] 事件监听
   - [ ] 自动清理

2. **路线图生成流式 Hook** (`lib/hooks/sse/use-roadmap-generation-stream.ts`)
   - [ ] 流式生成监听
   - [ ] 进度更新
   - [ ] 状态同步

3. **聊天修改流式 Hook** (`lib/hooks/sse/use-chat-modification-stream.ts`)
   - [ ] 聊天修改监听
   - [ ] 流式输出处理

**示例代码**:

```typescript
// lib/hooks/sse/use-roadmap-generation-stream.ts
import { useEffect, useRef, useState } from 'react';
import { RoadmapGenerationSSE, type RoadmapGenerationHandlers } from '@/lib/api/sse/roadmap-sse';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest } from '@/types';

export interface UseRoadmapGenerationStreamOptions {
  onComplete?: (roadmapId: string) => void;
  onError?: (error: string) => void;
}

export function useRoadmapGenerationStream(
  request: UserRequest | null,
  options?: UseRoadmapGenerationStreamOptions
) {
  const sseRef = useRef<RoadmapGenerationSSE | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const {
    setGenerationPhase,
    updateProgress,
    setRoadmap,
    setError,
    setActiveTask,
    setLiveGenerating,
    updateConceptStatus,
  } = useRoadmapStore();

  useEffect(() => {
    if (!request) return;

    const handlers: RoadmapGenerationHandlers = {
      onProgress: (event) => {
        console.log('[SSE] Progress:', event);
        
        // 更新进度
        const progress = calculateProgress(event.current_step);
        updateProgress(event.current_step, progress);
        
        // 提取 roadmap_id（早期导航）
        if (event.data?.roadmap_id) {
          setActiveTask(event.task_id);
          setLiveGenerating(true);
        }
      },

      onStepComplete: (event) => {
        console.log('[SSE] Step complete:', event);
        
        // 如果是 curriculum_design 完成，提取路线图框架
        if (event.step === 'curriculum_design' && event.result?.roadmap) {
          setRoadmap(event.result.roadmap);
        }
      },

      onComplete: (event) => {
        console.log('[SSE] Complete:', event);
        setGenerationPhase('completed');
        setLiveGenerating(false);
        options?.onComplete?.(event.roadmap_id);
      },

      onError: (event) => {
        console.error('[SSE] Error:', event);
        setError(event.error);
        setLiveGenerating(false);
        options?.onError?.(event.error);
      },
    };

    sseRef.current = new RoadmapGenerationSSE(request, handlers);
    sseRef.current.connect();
    setIsConnected(true);

    return () => {
      sseRef.current?.disconnect();
      setIsConnected(false);
    };
  }, [request]);

  return {
    isConnected,
    disconnect: () => sseRef.current?.disconnect(),
  };
}

// 辅助函数：根据步骤计算进度
function calculateProgress(step: string): number {
  const stepProgress: Record<string, number> = {
    'intent_analysis': 20,
    'curriculum_design': 40,
    'structure_validation': 50,
    'human_review': 60,
    'content_generation': 80,
    'completed': 100,
  };
  return stepProgress[step] || 0;
}
```

**测试清单**:
- [ ] 测试 SSE 连接
- [ ] 测试事件处理
- [ ] 测试自动清理
- [ ] 测试错误恢复

---

#### 3.3 实现 UI Hooks

**任务清单**:

- [ ] `use-debounce.ts` - 防抖
- [ ] `use-throttle.ts` - 节流
- [ ] `use-media-query.ts` - 响应式断点
- [ ] `use-local-storage.ts` - LocalStorage 封装
- [ ] `use-intersection-observer.ts` - 可见性检测

---

### Phase 4: 组件重构（第 10-14 天）

#### 4.1 重构页面组件

**任务清单**:

1. **创建路线图页面** (`app/(app)/new/page.tsx`)
   - [ ] 使用新的 API Hooks
   - [ ] 使用新的 SSE Hooks
   - [ ] 优化表单验证
   - [ ] 添加加载状态
   - [ ] 添加错误处理

2. **路线图详情页面** (`app/(app)/roadmap/[id]/page.tsx`)
   - [ ] 使用 useRoadmap Hook
   - [ ] 实时生成状态监听
   - [ ] 人工审核流程
   - [ ] 内容状态展示

3. **学习页面** (`app/(app)/roadmap/[id]/learn/[conceptId]/page.tsx`)
   - [ ] 使用 useTutorial Hook
   - [ ] Markdown 渲染
   - [ ] 代码高亮
   - [ ] 学习进度追踪

**示例代码**:

```typescript
// app/(app)/new/page.tsx - 重构后
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRoadmapGeneration } from '@/lib/hooks/api/use-roadmap-generation';
import { useRoadmapGenerationStream } from '@/lib/hooks/sse/use-roadmap-generation-stream';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest } from '@/types';

export default function NewRoadmapPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<FormData>({ /* ... */ });
  
  // API Mutation Hook
  const { mutate: generateRoadmap, isPending } = useRoadmapGeneration();
  
  // 生成状态
  const isGenerating = useRoadmapStore((state) => state.isGenerating);
  const activeTaskId = useRoadmapStore((state) => state.activeTaskId);
  
  // SSE 流式监听
  const [request, setRequest] = useState<UserRequest | null>(null);
  useRoadmapGenerationStream(request, {
    onComplete: (roadmapId) => {
      router.push(`/app/roadmap/${roadmapId}`);
    },
  });

  const handleSubmit = () => {
    const userRequest: UserRequest = {
      user_id: userId,
      preferences: {
        learning_goal: formData.learningGoal,
        current_level: formData.currentLevel,
        // ...
      },
    };
    
    // 1. 调用同步 API 启动任务
    generateRoadmap(userRequest, {
      onSuccess: (response) => {
        // 2. 启动 SSE 流式监听
        setRequest(userRequest);
      },
    });
  };

  return (
    <div>
      {/* Form UI */}
      {isGenerating && (
        <GenerationProgress
          taskId={activeTaskId}
          onComplete={(roadmapId) => router.push(`/app/roadmap/${roadmapId}`)}
        />
      )}
    </div>
  );
}
```

---

#### 4.2 重构功能组件

**任务清单**:

1. **路线图组件** (`components/roadmap/`)
   - [ ] `roadmap-view.tsx` - 路线图整体视图
   - [ ] `stage-card.tsx` - Stage 卡片
   - [ ] `module-card.tsx` - Module 卡片
   - [ ] `concept-card.tsx` - Concept 卡片（重构）
   - [ ] `generation-progress.tsx` - 生成进度（新增）
   - [ ] `phase-indicator.tsx` - 阶段指示器（保留）

2. **教程组件** (`components/tutorial/`)
   - [ ] `tutorial-viewer.tsx` - 教程查看器（新增）
   - [ ] `markdown-renderer.tsx` - Markdown 渲染器（新增）
   - [ ] `code-block.tsx` - 代码块组件（新增）

3. **聊天组件** (`components/chat/`)
   - [ ] `chat-widget.tsx` - 聊天窗口
   - [ ] `message-list.tsx` - 消息列表
   - [ ] `streaming-message.tsx` - 流式消息（新增）

**示例代码**:

```typescript
// components/roadmap/generation-progress.tsx - 新增组件
'use client';

import { useEffect } from 'react';
import { useTaskStatus } from '@/lib/hooks/api/use-task-status';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { Progress } from '@/components/ui/progress';
import { GENERATION_PHASES } from '@/types/custom/phases';

interface GenerationProgressProps {
  taskId: string | null;
  onComplete?: (roadmapId: string) => void;
}

export function GenerationProgress({ taskId, onComplete }: GenerationProgressProps) {
  const { data: status, isLoading } = useTaskStatus(taskId, {
    enabled: !!taskId,
    refetchInterval: 2000,
  });
  
  const { generationProgress, currentStep } = useRoadmapStore();

  useEffect(() => {
    if (status?.status === 'completed' && status.roadmap_id) {
      onComplete?.(status.roadmap_id);
    }
  }, [status, onComplete]);

  const currentPhase = GENERATION_PHASES.find(p => p.id === currentStep);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {currentPhase?.label || '处理中...'}
        </span>
        <span className="text-sm text-muted-foreground">
          {Math.round(generationProgress)}%
        </span>
      </div>
      
      <Progress value={generationProgress} className="h-2" />
      
      <p className="text-xs text-muted-foreground">
        {currentPhase?.description}
      </p>
    </div>
  );
}
```

---

#### 4.3 优化布局组件

**任务清单**:

- [ ] 重构 `app-shell.tsx` - 应用外壳
- [ ] 重构 `left-sidebar.tsx` - 左侧边栏
- [ ] 重构 `right-sidebar.tsx` - 右侧边栏（AI 聊天）
- [ ] 添加响应式布局
- [ ] 添加 Loading Skeleton

---

### Phase 5: 测试与质量保证（第 15-17 天）

#### 5.1 单元测试

**任务清单**:

1. **API 测试** (`__tests__/unit/api/`)
   - [ ] 测试 API 客户端配置
   - [ ] 测试拦截器
   - [ ] 测试端点封装
   - [ ] Mock API 响应

2. **Store 测试** (`__tests__/unit/store/`)
   - [ ] 测试状态更新
   - [ ] 测试派生状态
   - [ ] 测试持久化

3. **Hooks 测试** (`__tests__/unit/hooks/`)
   - [ ] 测试 API Hooks
   - [ ] 测试 SSE Hooks
   - [ ] 测试自定义 Hooks

4. **工具函数测试** (`__tests__/unit/utils/`)
   - [ ] 测试格式化函数
   - [ ] 测试验证函数
   - [ ] 测试类型守卫

**示例代码**:

```typescript
// __tests__/unit/api/roadmaps.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { roadmapsApi } from '@/lib/api/endpoints/roadmaps';
import { apiClient } from '@/lib/api/client';

vi.mock('@/lib/api/client');

describe('roadmapsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('generate', () => {
    it('should call POST /roadmaps/generate', async () => {
      const mockResponse = {
        data: {
          task_id: 'task-123',
          roadmap_id: 'roadmap-456',
          status: 'processing',
          message: 'Generation started',
        },
      };
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        user_id: 'user-1',
        preferences: {
          learning_goal: 'Learn React',
          current_level: 'beginner',
        },
      };

      const result = await roadmapsApi.generate(request);

      expect(apiClient.post).toHaveBeenCalledWith('/roadmaps/generate', request);
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle API errors', async () => {
      const mockError = new Error('Network error');
      vi.mocked(apiClient.post).mockRejectedValue(mockError);

      const request = { /* ... */ };

      await expect(roadmapsApi.generate(request)).rejects.toThrow('Network error');
    });
  });

  // More tests...
});
```

**测试覆盖率目标**:
- API 层: 90%+
- Store: 90%+
- Hooks: 80%+
- Utils: 95%+

---

#### 5.2 集成测试

**任务清单**:

1. **路线图生成流程** (`__tests__/integration/roadmap-generation.test.ts`)
   - [ ] 测试完整生成流程
   - [ ] 测试 SSE 事件处理
   - [ ] 测试状态更新

2. **聊天修改流程** (`__tests__/integration/chat-modification.test.ts`)
   - [ ] 测试意图分析
   - [ ] 测试内容修改
   - [ ] 测试流式输出

**示例代码**:

```typescript
// __tests__/integration/roadmap-generation.test.ts
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useRoadmapGeneration } from '@/lib/hooks/api/use-roadmap-generation';
import { useRoadmapGenerationStream } from '@/lib/hooks/sse/use-roadmap-generation-stream';
import { createWrapper } from '../utils/test-wrapper';

describe('Roadmap Generation Flow', () => {
  it('should generate roadmap successfully', async () => {
    const { result: generationResult } = renderHook(
      () => useRoadmapGeneration(),
      { wrapper: createWrapper() }
    );

    const request = {
      user_id: 'test-user',
      preferences: {
        learning_goal: 'Learn React',
        current_level: 'beginner',
      },
    };

    // Step 1: Start generation
    generationResult.current.mutate(request);

    await waitFor(() => {
      expect(generationResult.current.isSuccess).toBe(true);
      expect(generationResult.current.data?.task_id).toBeDefined();
    });

    // Step 2: Monitor SSE stream
    const taskId = generationResult.current.data!.task_id;
    
    // ... SSE 测试逻辑
  });
});
```

---

#### 5.3 E2E 测试（使用 Playwright）

**任务清单**:

1. **路线图生成流程** (`__tests__/e2e/roadmap-flow.spec.ts`)
   - [ ] 填写表单
   - [ ] 提交生成
   - [ ] 等待完成
   - [ ] 查看路线图

2. **教程学习流程** (`__tests__/e2e/tutorial-learning.spec.ts`)
   - [ ] 选择 Concept
   - [ ] 查看教程
   - [ ] 完成学习
   - [ ] 测验答题

**示例代码**:

```typescript
// __tests__/e2e/roadmap-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Roadmap Generation Flow', () => {
  test('should generate a roadmap from start to finish', async ({ page }) => {
    // 1. Navigate to create page
    await page.goto('/app/new');

    // 2. Fill in learning goal
    await page.fill('[name="learningGoal"]', 'I want to learn React');
    
    // 3. Select level
    await page.click('text=Beginner');
    
    // 4. Continue to preferences
    await page.click('text=Continue');
    
    // 5. Set hours per week
    await page.fill('[name="availableHours"]', '10');
    
    // 6. Select content preferences
    await page.click('text=Visual');
    await page.click('text=Text');
    
    // 7. Generate roadmap
    await page.click('text=Generate Roadmap');
    
    // 8. Wait for generation to complete
    await expect(page.locator('text=生成完成')).toBeVisible({ timeout: 60000 });
    
    // 9. Verify navigation to roadmap page
    await expect(page).toHaveURL(/\/app\/roadmap\/[a-zA-Z0-9-]+/);
    
    // 10. Verify roadmap structure
    await expect(page.locator('[data-testid="stage-card"]')).toHaveCount(3);
  });
});
```

---

### Phase 6: 文档与优化（第 18-20 天）

#### 6.1 更新文档

**任务清单**:

1. **架构文档** (`docs/ARCHITECTURE.md`)
   - [ ] 更新目录结构
   - [ ] 更新数据流图
   - [ ] 更新状态机图

2. **API 集成文档** (`docs/API_INTEGRATION.md`) - 🆕
   - [ ] API 调用示例
   - [ ] SSE 使用指南
   - [ ] 错误处理指南
   - [ ] 最佳实践

3. **开发指南** (`docs/DEVELOPMENT.md`) - 🆕
   - [ ] 环境配置
   - [ ] 本地开发流程
   - [ ] 调试技巧
   - [ ] 常见问题

4. **测试指南** (`docs/TESTING.md`) - 🆕
   - [ ] 测试策略
   - [ ] 编写单元测试
   - [ ] 编写集成测试
   - [ ] E2E 测试指南

**文档示例**:

```markdown
<!-- docs/API_INTEGRATION.md -->
# API 集成指南

## 快速开始

### 1. 使用 API Hooks

推荐使用封装好的 Hooks 而不是直接调用 API：

\`\`\`typescript
import { useRoadmap } from '@/lib/hooks/api/use-roadmap';

function RoadmapPage() {
  const { data, isLoading, error } = useRoadmap(roadmapId);
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return <RoadmapView roadmap={data} />;
}
\`\`\`

### 2. 使用 SSE 流式更新

对于实时生成，使用 SSE Hooks：

\`\`\`typescript
import { useRoadmapGenerationStream } from '@/lib/hooks/sse/use-roadmap-generation-stream';

function GenerationPage() {
  const [request, setRequest] = useState<UserRequest | null>(null);
  
  useRoadmapGenerationStream(request, {
    onComplete: (roadmapId) => {
      router.push(\`/roadmap/\${roadmapId}\`);
    },
  });
  
  // ...
}
\`\`\`

### 3. 错误处理

所有 API 错误会自动被拦截器处理，并显示 Toast 提示：

\`\`\`typescript
// lib/api/interceptors/error.ts
export function errorInterceptor(error: AxiosError) {
  if (error.response?.status === 401) {
    toast.error('请先登录');
    router.push('/login');
  } else if (error.response?.status === 500) {
    toast.error('服务器错误，请稍后重试');
  }
  // ...
}
\`\`\`

## 最佳实践

### ✅ DO

- 使用 Hooks 而不是直接调用 API
- 使用 TanStack Query 的缓存机制
- 使用 SSE 而不是频繁轮询
- 添加 loading 和 error 状态
- 实现乐观更新

### ❌ DON'T

- 不要在组件中直接使用 axios
- 不要忽略错误处理
- 不要过度轮询（轮询间隔 < 2 秒）
- 不要在组件卸载后更新状态
```

---

#### 6.2 性能优化

**任务清单**:

1. **代码分割**
   - [ ] 动态导入大组件
   - [ ] 路由级别代码分割
   - [ ] 第三方库按需加载

2. **缓存策略**
   - [ ] TanStack Query 缓存配置
   - [ ] LocalStorage 缓存
   - [ ] Service Worker 缓存（可选）

3. **渲染优化**
   - [ ] React.memo 优化
   - [ ] useMemo/useCallback 优化
   - [ ] 虚拟列表（长列表）

4. **网络优化**
   - [ ] 请求去重
   - [ ] 请求合并
   - [ ] 预加载关键资源

**示例代码**:

```typescript
// 动态导入大组件
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false,
});

// React.memo 优化
export const ConceptCard = React.memo(function ConceptCard({ concept }: Props) {
  // ...
}, (prevProps, nextProps) => {
  // 自定义比较函数
  return prevProps.concept.concept_id === nextProps.concept.concept_id;
});

// 虚拟列表（使用 react-window）
import { FixedSizeList } from 'react-window';

function ConceptList({ concepts }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={concepts.length}
      itemSize={100}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <ConceptCard concept={concepts[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

---

#### 6.3 开发体验优化

**任务清单**:

1. **开发工具**
   - [ ] TanStack Query DevTools
   - [ ] Zustand DevTools
   - [ ] React DevTools 配置

2. **代码质量**
   - [ ] ESLint 配置更新
   - [ ] Prettier 配置
   - [ ] Husky 配置（pre-commit hooks）
   - [ ] lint-staged 配置

3. **环境变量管理**
   - [ ] `.env.example` 示例文件
   - [ ] 环境变量验证脚本
   - [ ] 类型化环境变量

**配置示例**:

```json
// .husky/pre-commit
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npm run type-check
npm run lint
npm run test:unit
```

```typescript
// lib/utils/env.ts - 类型化环境变量
import { z } from 'zod';

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  NEXT_PUBLIC_WS_URL: z.string().url().optional(),
  NEXT_PUBLIC_ENV: z.enum(['development', 'staging', 'production']),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  NEXT_PUBLIC_ENV: process.env.NEXT_PUBLIC_ENV || 'development',
});
```

---

## 里程碑与时间估算

| 阶段 | 任务 | 时间估算 | 依赖 | 产出物 |
|:---:|:---|:---:|:---|:---|
| **Phase 1** | 基础设施重建 | **3 天** | 无 | lib/ 目录完整结构 |
| 1.1 | 创建目录结构 | 0.5 天 | - | 目录 + README |
| 1.2 | API 客户端 | 1 天 | 1.1 | 完整的 API 封装 |
| 1.3 | SSE 客户端 | 1 天 | 1.1 | SSE 基础设施 |
| 1.4 | Zustand Stores | 0.5 天 | 1.1 | 所有 Store 实现 |
| **Phase 2** | API 集成与类型同步 | **3 天** | Phase 1 | 类型完全同步 |
| 2.1 | 更新类型生成 | 0.5 天 | - | 类型生成脚本 |
| 2.2 | 同步枚举常量 | 0.5 天 | 2.1 | 枚举定义 |
| 2.3 | Zod Schema | 1 天 | 2.1 | 运行时验证 |
| 2.4 | 更新 SSE 类型 | 1 天 | 2.1 | SSE 事件类型 |
| **Phase 3** | React Hooks 实现 | **3 天** | Phase 1, 2 | 完整 Hooks 库 |
| 3.1 | API Hooks | 1.5 天 | Phase 1 | 所有 API Hooks |
| 3.2 | SSE Hooks | 1 天 | Phase 1 | SSE Hooks |
| 3.3 | UI Hooks | 0.5 天 | - | 工具 Hooks |
| **Phase 4** | 组件重构 | **5 天** | Phase 1, 2, 3 | 重构完成的组件 |
| 4.1 | 页面组件 | 2 天 | Phase 3 | 主要页面 |
| 4.2 | 功能组件 | 2 天 | Phase 3 | 路线图/教程组件 |
| 4.3 | 布局组件 | 1 天 | Phase 3 | 布局优化 |
| **Phase 5** | 测试与质量保证 | **3 天** | Phase 1-4 | 测试覆盖 80%+ |
| 5.1 | 单元测试 | 1.5 天 | Phase 1-3 | API/Store/Hooks 测试 |
| 5.2 | 集成测试 | 1 天 | Phase 4 | 流程测试 |
| 5.3 | E2E 测试 | 0.5 天 | Phase 4 | E2E 测试 |
| **Phase 6** | 文档与优化 | **3 天** | Phase 1-5 | 完整文档 + 优化 |
| 6.1 | 更新文档 | 1 天 | Phase 1-5 | 4 份完整文档 |
| 6.2 | 性能优化 | 1 天 | Phase 4 | 性能提升 |
| 6.3 | 开发体验优化 | 1 天 | - | 开发工具配置 |
| **总计** | - | **20 天** | - | 完整重构 |

### 关键里程碑

- **M1（第 3 天）**: 基础设施完成 ✅
- **M2（第 6 天）**: API 集成完成 ✅
- **M3（第 9 天）**: Hooks 库完成 ✅
- **M4（第 14 天）**: 组件重构完成 ✅
- **M5（第 17 天）**: 测试覆盖达标 ✅
- **M6（第 20 天）**: 项目完整重构 ✅

---

## 风险评估与应对

### 高风险项

#### 1. **SSE 兼容性问题**

**风险**: EventSource 不支持 POST 请求，需要使用第三方库或 fetch stream

**应对方案**:
- 使用 `@microsoft/fetch-event-source` 库
- 备选方案：降级为 WebSocket
- 备选方案：轮询 + 长轮询

#### 2. **类型生成与后端不同步**

**风险**: 后端 API 变更导致类型不匹配

**应对方案**:
- 添加 CI/CD 类型检查
- 定期自动生成类型
- 运行时 Zod 验证兜底

#### 3. **状态管理复杂度**

**风险**: 多个 Store 之间状态同步困难

**应对方案**:
- 明确状态边界和职责
- 使用 Store 中间件统一处理
- 添加状态变更日志

#### 4. **测试覆盖不足**

**风险**: 时间紧张导致测试覆盖率低

**应对方案**:
- 优先测试核心路径
- 使用集成测试覆盖关键流程
- 后续补充单元测试

### 中风险项

#### 5. **组件重构遗漏**

**风险**: 部分组件未使用新 API，导致不一致

**应对方案**:
- 使用 ESLint 规则检测旧 API 调用
- Code Review 检查清单
- 删除旧的 API 调用代码

#### 6. **性能回退**

**风险**: 重构后性能下降

**应对方案**:
- 性能测试基准对比
- Lighthouse CI 检查
- 优化热路径代码

---

## 成功标准

### 功能完整性

- [ ] 所有页面功能正常
- [ ] API 调用 100% 对齐后端文档
- [ ] SSE 流式更新稳定工作
- [ ] 错误处理覆盖所有场景
- [ ] 加载状态友好展示

### 代码质量

- [ ] TypeScript strict mode 无错误
- [ ] ESLint 无警告
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试覆盖核心流程
- [ ] E2E 测试覆盖用户主流程

### 性能指标

- [ ] 首屏加载 < 2秒
- [ ] API 响应 < 500ms (p95)
- [ ] SSE 延迟 < 100ms
- [ ] 内存泄漏检测通过

### 文档完整性

- [ ] API 集成文档完整
- [ ] 开发指南清晰
- [ ] 测试指南可操作
- [ ] 架构图更新

---

## 后续优化建议

### Phase 7: 高级功能（可选）

1. **离线支持**
   - Service Worker 缓存
   - IndexedDB 本地存储
   - 离线编辑同步

2. **性能监控**
   - Sentry 错误追踪
   - Datadog RUM 监控
   - 自定义性能指标

3. **国际化**
   - i18n 支持
   - 多语言切换
   - 区域化配置

4. **可访问性增强**
   - ARIA 完整支持
   - 键盘导航优化
   - 屏幕阅读器优化

---

## 附录

### A. 依赖包更新清单

需要添加的新依赖：

```json
{
  "dependencies": {
    "@microsoft/fetch-event-source": "^2.0.1",  // SSE 支持
    "zod": "^3.22.0",                          // 运行时验证（已有）
  },
  "devDependencies": {
    "vitest": "^1.0.0",                        // 单元测试
    "vitest": "^1.0.0",                        // 单元测试
    "@testing-library/react": "^14.0.0",       // React 测试
    "@testing-library/react-hooks": "^8.0.1",  // Hooks 测试
    "@playwright/test": "^1.40.0",             // E2E 测试
    "msw": "^2.0.0",                           // Mock Service Worker
  }
}
```

### B. 环境变量示例

```bash
# .env.example
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_ENV=development
```

### C. 联系方式

**重构负责人**: [您的名字]  
**后端对接人**: Backend Team  
**Slack**: #frontend-refactoring  
**文档更新**: 每周五

---

**文档版本**: v1.0.0  
**创建日期**: 2025-12-06  
**最后更新**: 2025-12-06  
**维护者**: Frontend Team
