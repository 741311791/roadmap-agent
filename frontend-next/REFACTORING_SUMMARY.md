# 前端重构计划总结

> 一页纸看懂整个重构计划

---

## 📊 重构概览

| 项目 | 内容 |
|:---|:---|
| **重构范围** | 前端项目完全重构，不考虑向后兼容 |
| **核心目标** | API 完全对齐后端 + 补全缺失模块 + 提升代码质量 |
| **预计时间** | 20 个工作日（4 周） |
| **总任务数** | 111 个可执行任务 |
| **团队规模** | 建议 3-5 人 |

---

## 🎯 三大核心目标

### 1️⃣ API 完全对齐

- ✅ 前端 API 调用与后端 `FRONTEND_API_GUIDE.md` 100% 匹配
- ✅ 类型定义自动生成，与 Pydantic 模型同步
- ✅ SSE 流式接口完整支持
- ✅ WebSocket 作为备选方案

### 2️⃣ 补全缺失模块

目前**缺失**的关键目录和文件：

```
❌ lib/                      # 核心业务逻辑目录（完全缺失）
   ├── api/                  # API 客户端封装
   ├── store/                # Zustand 状态管理实现
   ├── hooks/                # 自定义 React Hooks
   ├── utils/                # 工具函数
   ├── constants/            # 常量和枚举
   └── schemas/              # Zod 运行时验证

❌ __tests__/                # 测试目录（完全缺失）
   ├── unit/                 # 单元测试
   ├── integration/          # 集成测试
   └── e2e/                  # E2E 测试
```

### 3️⃣ 提升代码质量

- ✅ TypeScript strict mode（严格类型检查）
- ✅ 单元测试覆盖率 ≥ 80%
- ✅ 集成测试覆盖核心流程
- ✅ E2E 测试覆盖用户主流程
- ✅ 性能优化（首屏 < 2 秒）

---

## 🏗️ 新架构设计

### 分层架构

```
┌────────────────────────────────────────┐
│         Pages (页面组件)                │
│    app/*/page.tsx                      │
│    - 使用 Hooks                        │
│    - 不直接调用 API                     │
└────────────┬───────────────────────────┘
             │
┌────────────┴───────────────────────────┐
│         Hooks (自定义钩子)              │
│    lib/hooks/*                         │
│    - API Hooks (useRoadmap)           │
│    - WebSocket Hooks (路线图生成)      │
│    - SSE Hooks (AI 聊天)              │
│    - UI Hooks (useDebounce)           │
└────────────┬───────────────────────────┘
             │
┌────────────┴───────────────────────────┐
│    API Client + Store (API和状态)      │
│    lib/api/* + lib/store/*            │
│    - WebSocket (路线图) + 轮询(降级)   │
│    - SSE (AI 聊天)                    │
│    - 全局状态管理                       │
│    - 请求拦截器                         │
└────────────┬───────────────────────────┘
             │
┌────────────┴───────────────────────────┐
│         Backend API (后端)             │
│    WebSocket + REST API + SSE         │
└────────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 | 关键文件 |
|:---|:---|:---|
| **API 客户端** | 统一 API 调用、拦截器、错误处理 | `lib/api/client.ts`<br/>`lib/api/endpoints/*` |
| **WebSocket 客户端** | 路线图生成实时事件、状态恢复 | `lib/api/websocket/roadmap-ws.ts`<br/>`lib/api/polling/task-polling.ts` |
| **SSE 客户端** | AI 聊天流式输出 | `lib/api/sse/client.ts`<br/>`lib/api/sse/chat-sse.ts` |
| **Zustand Store** | 全局状态管理、持久化 | `lib/store/roadmap-store.ts`<br/>`lib/store/chat-store.ts` |
| **React Hooks** | 数据获取、状态管理、副作用 | `lib/hooks/websocket/*`<br/>`lib/hooks/sse/*` |
| **类型系统** | 类型生成、运行时验证 | `types/generated/*`<br/>`lib/schemas/*` |

---

## 📅 6 个阶段计划

| 阶段 | 时间 | 任务数 | 优先级 | 关键产出 |
|:---:|:---:|:---:|:---:|:---|
| **Phase 1** | 3 天 | 27 | 🔴 P0 | API 客户端 + WebSocket + 轮询 + Store |
| **Phase 2** | 3 天 | 18 | 🔴 P0 | 类型同步 + Schema 验证 |
| **Phase 3** | 3 天 | 15 | 🟡 P1 | 完整的 Hooks 库（WebSocket + SSE） |
| **Phase 4** | 5 天 | 21 | 🟡 P1 | 组件重构完成 |
| **Phase 5** | 3 天 | 19 | 🟢 P2 | 测试覆盖 80%+ |
| **Phase 6** | 3 天 | 15 | 🟢 P2 | 文档 + 性能优化 |
| **总计** | **20 天** | **115** | - | **完整重构** |

### 关键里程碑

```
Day 3  ✓ M1: 基础设施完成
Day 6  ✓ M2: API 集成完成
Day 9  ✓ M3: Hooks 库完成
Day 14 ✓ M4: 组件重构完成
Day 17 ✓ M5: 测试覆盖达标
Day 20 ✓ M6: 项目完整重构
```

---

## 🚀 快速开始（3 步）

### Step 1: 阅读文档（15 分钟）

| 文档 | 用途 | 必读 |
|:---|:---|:---:|
| `QUICK_START.md` | 5 分钟快速上手 | ✅ |
| `REFACTORING_PLAN.md` | 详细理论和设计 | ⭐ |
| `REFACTORING_CHECKLIST.md` | 执行任务清单 | ✅ |
| `CONFIG_UPDATES.md` | 配置更新指南 | ✅ |

### Step 2: 配置环境（10 分钟）

```bash
# 1. 安装依赖
npm install @microsoft/fetch-event-source
npm install -D vitest @testing-library/react @playwright/test

# 2. 创建目录
mkdir -p lib/{api,store,hooks,utils,constants,schemas}
mkdir -p __tests__/{unit,integration,e2e}

# 3. 配置文件
cp .env.example .env.local
# 参考 CONFIG_UPDATES.md 更新配置
```

### Step 3: 开始执行（按 Checklist）

```bash
# 打开 Checklist
open REFACTORING_CHECKLIST.md

# 从 Phase 1.1 开始执行
# 完成一项，将 [ ] 改为 [x]
```

---

## 📦 需要添加的依赖

### 核心依赖

```json
{
  "dependencies": {
    "@microsoft/fetch-event-source": "^2.0.1"
  },
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/react-hooks": "^8.0.1",
    "@playwright/test": "^1.40.0",
    "msw": "^2.0.0",
    "husky": "^8.0.0",
    "lint-staged": "^15.0.0"
  }
}
```

---

## ✅ 验收标准（简化版）

### 功能验收

- [ ] 所有功能正常工作
- [ ] API 调用与后端文档 100% 匹配
- [ ] WebSocket 实时更新稳定（路线图生成）
- [ ] 轮询降级方案可用
- [ ] SSE 流式更新稳定（AI 聊天）
- [ ] 错误处理完善

### 代码质量

- [ ] TypeScript strict mode 无错误
- [ ] ESLint 无警告
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] E2E 测试覆盖主流程

### 性能指标

- [ ] 首屏加载 < 2 秒
- [ ] API 响应 < 500ms (p95)
- [ ] WebSocket 延迟 < 100ms
- [ ] SSE 延迟 < 100ms
- [ ] Lighthouse 分数 > 90

### 文档完整

- [ ] API 集成文档
- [ ] 开发指南
- [ ] 测试指南
- [ ] 架构图

---

## 🎯 每日工作重点（示例）

### Week 1: 基础设施 + API 集成

| 天 | 阶段 | 重点任务 | 产出 |
|:---:|:---|:---|:---|
| 1 | Phase 1.2 | API 客户端 + 拦截器 | 可调用后端 API |
| 2 | Phase 1.2 | API 端点封装 | 所有端点可用 |
| 3 | Phase 1.3 | WebSocket 客户端 + 轮询 | 路线图生成实时监听 |
| 4 | Phase 2.1-2 | 类型生成 + 枚举同步 | 类型完全对齐 |
| 5 | Phase 2.3-4 | Schema 验证 + WebSocket 类型 | 运行时验证 |

### Week 2: Hooks + 组件重构（前半）

| 天 | 阶段 | 重点任务 | 产出 |
|:---:|:---|:---|:---|
| 6 | Phase 3.1 | API Hooks (路线图) | useRoadmap 可用 |
| 7 | Phase 3.1 | API Hooks (内容) | useTutorial 可用 |
| 8 | Phase 3.2 | WebSocket Hooks + SSE Hooks | 混合策略 Hook |
| 9 | Phase 3.3 | UI Hooks | 工具 Hooks |
| 10 | Phase 4.1 | 页面组件重构（new） | 创建页面完成 |

### Week 3: 组件重构（后半） + 测试

| 天 | 阶段 | 重点任务 | 产出 |
|:---:|:---|:---|:---|
| 11 | Phase 4.1 | 页面组件（roadmap） | 详情页完成 |
| 12 | Phase 4.2 | 功能组件（roadmap） | 路线图组件 |
| 13 | Phase 4.2 | 功能组件（tutorial） | 教程组件 |
| 14 | Phase 4.3 | 布局组件优化 | 布局完成 |
| 15 | Phase 5.1 | 单元测试（API） | API 测试 |

### Week 4: 测试 + 文档 + 优化

| 天 | 阶段 | 重点任务 | 产出 |
|:---:|:---|:---|:---|
| 16 | Phase 5.1 | 单元测试（Store/Hooks） | 核心测试完成 |
| 17 | Phase 5.2-3 | 集成 + E2E 测试 | 测试覆盖达标 |
| 18 | Phase 6.1 | 文档更新 | 4 份完整文档 |
| 19 | Phase 6.2 | 性能优化 | 性能达标 |
| 20 | Phase 6.3 | 开发体验优化 | 重构完成 🎉 |

---

## 🔍 关键技术点

### 1. API 客户端设计

```typescript
// 统一的 API 客户端
apiClient.interceptors.request.use(authInterceptor);
apiClient.interceptors.response.use(null, errorInterceptor);

// 端点封装
export const roadmapsApi = {
  generate: (request) => apiClient.post('/roadmaps/generate', request),
  getById: (id) => apiClient.get(`/roadmaps/${id}`),
  // ...
};
```

### 2. WebSocket 实时更新（路线图生成）

```typescript
// WebSocket 客户端
const ws = new RoadmapWebSocket(taskId, {
  onProgress: (event) => updateProgress(event),
  onHumanReview: (event) => showReviewDialog(event),
  onConceptStart: (event) => updateConceptStatus(event.concept_id, 'generating'),
  onCompleted: (event) => navigate(`/roadmap/${event.roadmap_id}`),
  onError: (error) => fallbackToPolling(),  // 自动降级
});

ws.connect(true);  // include_history = true

// Hook 封装（WebSocket + 轮询混合策略）
const { connectionType, isConnected } = useRoadmapGenerationWS(taskId, {
  onComplete: (roadmapId) => router.push(`/roadmap/${roadmapId}`),
});
```

### 3. SSE 流式更新（AI 聊天）

```typescript
// SSE 客户端（AI 聊天）
const sse = new ChatSSE({
  onAnalyzing: (event) => showAnalyzing(event),
  onModifying: (event) => appendToStream(event.target_name),
  onDone: (event) => showResults(event),
});

await sse.connect('/api/v1/chat/modify', { message: '...' });

// Hook 封装
const { isStreaming } = useChatStream(endpoint, requestBody, {
  onComplete: () => console.log('Done'),
});
```

### 4. Zustand Store

```typescript
// 状态管理
export const useRoadmapStore = create<RoadmapStore>()(
  devtools(
    persist(
      (set) => ({
        currentRoadmap: null,
        setRoadmap: (roadmap) => set({ currentRoadmap: roadmap }),
        // ...
      }),
      { name: 'roadmap-storage' }
    )
  )
);
```

### 5. TanStack Query Hooks

```typescript
// 数据获取
export function useRoadmap(roadmapId: string) {
  return useQuery({
    queryKey: ['roadmap', roadmapId],
    queryFn: () => roadmapsApi.getById(roadmapId),
    staleTime: 5 * 60 * 1000,
  });
}
```

### 6. 实时通信方案总结

| 场景 | 方案 | 原因 |
|:---|:---|:---|
| **路线图生成** | WebSocket + 轮询（降级） | 支持人工审核、状态持久化、页面刷新恢复 |
| **AI 聊天** | SSE | 流式输出简单、逐字显示 |

---

## 🤝 团队协作建议

### 任务分配

| 角色 | 职责 | 主要阶段 |
|:---|:---|:---|
| **Tech Lead** | 架构设计、Code Review、里程碑验收 | 全程 |
| **Backend Dev** | API 对接、类型同步、集成测试 | Phase 1-2 |
| **Frontend A** | API 客户端、Store 实现 | Phase 1-2 |
| **Frontend B** | Hooks 实现、组件重构 | Phase 3-4 |
| **QA/Test** | 测试框架、E2E 测试 | Phase 5 |

### Git 工作流

```
main (保护分支)
  ↑
  └─ develop (开发分支)
       ↑
       ├─ feature/phase1-api-client
       ├─ feature/phase2-type-sync
       ├─ feature/phase3-hooks
       └─ feature/phase4-components
```

---

## 📈 进度跟踪

### 进度计算

```
总进度 = 已完成任务数 / 111
Phase 进度 = 该阶段已完成 / 该阶段总任务
```

### 进度看板（示例）

```
Phase 1: [████░░░░░░] 40% (9/23)
Phase 2: [██░░░░░░░░] 20% (4/18)
Phase 3: [░░░░░░░░░░]  0% (0/15)
Phase 4: [░░░░░░░░░░]  0% (0/21)
Phase 5: [░░░░░░░░░░]  0% (0/19)
Phase 6: [░░░░░░░░░░]  0% (0/15)
─────────────────────────────────
总进度:  [█░░░░░░░░░] 12% (13/111)
```

---

## 🆘 遇到问题？

### 资源导航

1. **理论问题** → 查看 `REFACTORING_PLAN.md`
2. **执行问题** → 查看 `REFACTORING_CHECKLIST.md`
3. **配置问题** → 查看 `CONFIG_UPDATES.md`
4. **上手问题** → 查看 `QUICK_START.md`
5. **API 问题** → 查看 `backend/docs/FRONTEND_API_GUIDE.md`

### 联系方式

- **Slack**: #frontend-refactoring
- **Email**: frontend-team@example.com
- **Code Review**: 提交 PR 到 `develop` 分支

---

## 🎉 重构成功标准

### 核心指标

```
✅ 功能完整性:  100% (所有功能正常)
✅ API 对齐:    100% (与后端文档匹配)
✅ 类型安全:    100% (TypeScript strict mode)
✅ 测试覆盖:     80% (单元测试)
✅ 性能达标:    优秀 (Lighthouse > 90)
✅ 文档完整:    100% (4 份核心文档)
```

### 长期目标

- 📚 完善的开发文档和最佳实践
- 🧪 持续的测试覆盖和质量保证
- ⚡ 持续的性能优化和监控
- 🔄 快速的新功能迭代能力

---

**祝你重构顺利！🚀**

---

**文档版本**: v1.0.0  
**创建日期**: 2025-12-06  
**最后更新**: 2025-12-06  
**维护者**: Frontend Team
