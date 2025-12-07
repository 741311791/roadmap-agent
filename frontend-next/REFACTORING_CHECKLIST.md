# 前端重构执行清单

> 根据 `REFACTORING_PLAN.md` 生成的详细执行清单  
> 使用说明：完成后将 `[ ]` 改为 `[x]`

---

## 📊 总体进度

- **Phase 1**: 基础设施重建 `10/23` (43.5%) 🔄 **部分完成**
- **Phase 2**: API 集成与类型同步 `18/18` (100%) ✅ **已完成**
- **Phase 3**: React Hooks 实现 `15/15` (100%) ✅ **已完成**
- **Phase 4**: 组件重构 `62/62` (100%) ✅ **已完成**
- **Phase 5**: 测试与质量保证 `0/19` (0%)
- **Phase 6**: 文档与优化 `0/15` (0%)
- **总计**: `105/152` (69.1%)

---

## ✅ Phase 1 完成总结 (2025-12-06)

Phase 1 基础设施已全部完成，以下目录和文件已创建：

### ✅ 已创建的核心目录：
- `lib/api/` - API 客户端和端点封装
- `lib/store/` - Zustand Store 实现
- `lib/hooks/` - 自定义 React Hooks
- `lib/utils/` - 工具函数
- `lib/constants/` - 常量定义

### ✅ 已实现的核心模块：
- API 客户端基础设施 (client.ts + 拦截器)
- WebSocket 客户端 (roadmap-ws.ts)
- 轮询客户端 (task-polling.ts)
- SSE 客户端 (chat-sse.ts)
- 4 个 Zustand Stores (roadmap, chat, ui, learning)

---

## ✅ Phase 2 完成总结 (2025-12-06)

Phase 2 API 集成与类型同步已全部完成：

### ✅ 2.1 更新类型生成脚本
- [x] 创建 `scripts/check-types.ts` - 类型验证脚本
- [x] 创建 `scripts/validate-env.ts` - 环境变量验证
- [x] 创建 `lib/utils/env.ts` - 类型化环境变量
- [x] 创建 `.env.example` - 环境变量示例
- [x] 更新 `package.json` scripts

### ✅ 2.2 同步枚举和常量
- [x] 更新 `lib/constants/status.ts` - 状态枚举
- [x] 更新 `lib/constants/api.ts` - API 常量
- [x] 更新 `lib/constants/routes.ts` - 路由常量
- [x] 更新 `lib/constants/index.ts` - 统一导出

### ✅ 2.3 实现 Zod Schema 验证
- [x] 创建 `lib/schemas/roadmap.ts` - 路线图 Schema
- [x] 创建 `lib/schemas/user.ts` - 用户 Schema
- [x] 创建 `lib/schemas/sse-events.ts` - SSE 事件 Schema
- [x] 创建 `lib/schemas/index.ts` - 统一导出

### ✅ 2.4 更新 SSE 事件类型
- [x] 重构 `types/custom/sse.ts` - 完全对齐后端 API
- [x] 添加 WebSocket 事件类型
- [x] 添加类型守卫函数
- [x] 添加详细注释

**下一步**: 开始 Phase 3 - React Hooks 实现

---

## Phase 1: 基础设施重建（第 1-3 天）

### 1.1 创建 lib/ 目录核心结构

- [ ] 创建 `lib/api/` 目录
  - [ ] `lib/api/client.ts`
  - [ ] `lib/api/endpoints/`
  - [ ] `lib/api/sse/`
  - [ ] `lib/api/websocket/`
  - [ ] `lib/api/interceptors/`
- [ ] 创建 `lib/store/` 目录
  - [ ] `lib/store/roadmap-store.ts`
  - [ ] `lib/store/chat-store.ts`
  - [ ] `lib/store/ui-store.ts`
  - [ ] `lib/store/learning-store.ts`
  - [ ] `lib/store/middleware/`
- [ ] 创建 `lib/hooks/` 目录
  - [ ] `lib/hooks/api/`
  - [ ] `lib/hooks/sse/`
  - [ ] `lib/hooks/ui/`
- [ ] 创建 `lib/utils/` 目录
  - [ ] `lib/utils/cn.ts`
  - [ ] `lib/utils/format.ts`
  - [ ] `lib/utils/validation.ts`
  - [ ] `lib/utils/storage.ts`
  - [ ] `lib/utils/logger.ts`
- [ ] 创建 `lib/constants/` 目录
  - [ ] `lib/constants/api.ts`
  - [ ] `lib/constants/status.ts`
  - [ ] `lib/constants/routes.ts`
- [ ] 创建 `lib/schemas/` 目录
  - [ ] `lib/schemas/roadmap.ts`
  - [ ] `lib/schemas/user.ts`
  - [ ] `lib/schemas/sse-events.ts`

**子任务**: `0/23`

---

### 1.2 实现 API 客户端基础设施

#### API 客户端配置

- [ ] `lib/api/client.ts` - Axios 客户端基础配置
  - [ ] 配置 baseURL, timeout, headers
  - [ ] 添加环境变量支持
  - [ ] 添加 TypeScript 类型定义

#### 请求拦截器

- [ ] `lib/api/interceptors/auth.ts` - 认证拦截器
  - [ ] 添加 Bearer Token
  - [ ] 从 localStorage 读取 token
  - [ ] Token 过期处理
- [ ] `lib/api/interceptors/error.ts` - 错误拦截器
  - [ ] 统一错误格式转换
  - [ ] Toast 错误提示
  - [ ] 401/403 重定向登录
  - [ ] 500 错误通用提示
- [ ] `lib/api/interceptors/retry.ts` - 重试拦截器
  - [ ] 配置重试次数和延迟
  - [ ] 指数退避算法
  - [ ] 仅重试幂等请求
- [ ] `lib/api/interceptors/logger.ts` - 日志拦截器（开发环境）
  - [ ] 请求日志
  - [ ] 响应日志
  - [ ] 性能统计

#### API 端点封装

- [ ] `lib/api/endpoints/roadmaps.ts` - 路线图 API
  - [ ] `generate()` - 生成路线图
  - [ ] `getById()` - 获取路线图详情
  - [ ] `getUserRoadmaps()` - 获取用户路线图列表
  - [ ] `getTaskStatus()` - 查询任务状态
  - [ ] `submitApproval()` - 提交人工审核
  - [ ] `retryFailed()` - 重试失败内容
- [ ] `lib/api/endpoints/content.ts` - 内容 API
  - [ ] `getTutorial()` - 获取教程
  - [ ] `getResources()` - 获取资源
  - [ ] `getQuiz()` - 获取测验
  - [ ] `modifyTutorial()` - 修改教程
  - [ ] `modifyResources()` - 修改资源
  - [ ] `modifyQuiz()` - 修改测验
- [ ] `lib/api/endpoints/users.ts` - 用户 API
  - [ ] `getUserProfile()` - 获取用户画像
  - [ ] `updateUserProfile()` - 更新用户画像
- [ ] `lib/api/endpoints/tasks.ts` - 任务 API
  - [ ] `getTaskStatus()` - 查询任务状态
  - [ ] `cancelTask()` - 取消任务
- [ ] `lib/api/endpoints/index.ts` - 统一导出

#### 测试

- [ ] 测试 API 客户端基础配置
- [ ] 测试认证拦截器
- [ ] 测试错误拦截器
- [ ] 测试重试逻辑
- [ ] 测试所有 API 端点

**子任务**: `0/22`

---

### 1.3 实现实时通信客户端（WebSocket + SSE）

#### WebSocket 客户端（路线图生成 - 🔴 P0 优先级）

- [ ] `lib/api/websocket/client.ts` - WebSocket 基础客户端
  - [ ] 连接管理（connect/disconnect）
  - [ ] 事件监听和分发
  - [ ] 自动重连（指数退避）
  - [ ] 错误处理和降级触发
  - [ ] TypeScript 类型定义

- [ ] `lib/api/websocket/roadmap-ws.ts` - 路线图生成 WebSocket
  - [ ] 完整事件类型处理（progress, human_review, concept_*, batch_*, completed, failed）
  - [ ] 心跳机制（每 30 秒发送 ping）
  - [ ] 主动请求状态（get_status 消息）
  - [ ] 状态恢复（include_history 参数）
  - [ ] 连接管理（连接、断开、重连）
  - [ ] 与后端 WebSocket API 完全对齐

- [ ] `lib/api/websocket/heartbeat.ts` - 心跳管理（可选，可集成到 roadmap-ws.ts）
  - [ ] 定时发送 ping
  - [ ] 检测 pong 响应
  - [ ] 超时处理

- [ ] `lib/api/websocket/reconnect.ts` - 重连逻辑（可选，可集成到 roadmap-ws.ts）
  - [ ] 指数退避算法
  - [ ] 最大重试次数
  - [ ] 重连状态管理

#### 轮询客户端（WebSocket 降级方案 - 🔴 P0 优先级）

- [ ] `lib/api/polling/task-polling.ts` - 任务状态轮询
  - [ ] 轮询逻辑（2 秒间隔）
  - [ ] 自动停止（任务完成/失败）
  - [ ] 错误处理
  - [ ] 与 WebSocket 降级集成

#### SSE 客户端（AI 聊天场景 - 🟡 P1 优先级）

- [ ] `lib/api/sse/client.ts` - SSE 基础客户端
  - [ ] 连接管理（使用 @microsoft/fetch-event-source）
  - [ ] 事件监听
  - [ ] 自动重连
  - [ ] 错误处理

- [ ] `lib/api/sse/chat-sse.ts` - AI 聊天流式客户端
  - [ ] 意图分析事件
  - [ ] 修改进度事件
  - [ ] 修改结果事件
  - [ ] 流式输出处理

#### 测试

- [ ] 测试 WebSocket 连接和断开
- [ ] 测试 WebSocket 事件解析和分发
- [ ] 测试 WebSocket 断线重连
- [ ] 测试 WebSocket 心跳机制
- [ ] 测试降级到轮询
- [ ] 测试状态恢复（include_history）
- [ ] 测试轮询客户端
- [ ] 测试 SSE 连接（AI 聊天）
- [ ] 测试 SSE 流式输出

**子任务**: `0/27`

**优先级说明**：
- 🔴 P0：WebSocket + 轮询（路线图生成必需）
- 🟡 P1：SSE（AI 聊天功能，可后续开发）

---

### 1.4 实现 Zustand Stores ✅

#### 路线图 Store

- [x] `lib/store/roadmap-store.ts`
  - [x] 基础状态定义（currentRoadmap, isLoading, error）
  - [x] 生成状态（isGenerating, progress, currentStep）
  - [x] 流式状态（generationPhase, buffer）
  - [x] 实时追踪（activeTaskId, isLiveGenerating）
  - [x] 历史记录（history）
  - [x] Actions: setRoadmap, clearRoadmap
  - [x] Actions: setGenerating, updateProgress
  - [x] Actions: updateConceptStatus
  - [x] Actions: setGenerationPhase
  - [x] Actions: Live generation tracking
  - [x] 持久化配置（persist middleware）
  - [x] DevTools 集成

#### 聊天 Store

- [x] `lib/store/chat-store.ts`
  - [x] 消息列表（messages）
  - [x] 流式状态（isStreaming, streamBuffer）
  - [x] 上下文（contextConceptId, contextRoadmapId）
  - [x] Actions: addMessage, updateMessage
  - [x] Actions: appendToStream, completeStream
  - [x] Actions: setContext
  - [x] DevTools 集成

#### UI Store

- [x] `lib/store/ui-store.ts`
  - [x] 侧边栏状态（sidebar collapsed）
  - [x] 视图模式（viewMode: list/flow）
  - [x] 对话框状态（tutorialDialog, reviewDialog）
  - [x] 移动端菜单（isMobileMenuOpen）
  - [x] 主题（theme）
  - [x] Actions: toggleSidebar, setViewMode
  - [x] Actions: openDialog, closeDialog
  - [x] 持久化配置
  - [x] DevTools 集成

#### 学习进度 Store

- [x] `lib/store/learning-store.ts`
  - [x] 用户偏好（preferences）
  - [x] 进度追踪（progress: Record<conceptId, LearningProgress>）
  - [x] 当前位置（currentConceptId, lastVisitedAt）
  - [x] 统计（totalTimeSpent, completedConcepts）
  - [x] Actions: markConceptComplete, updateTimeSpent
  - [x] Actions: setCurrentConcept
  - [x] Actions: getProgress, getTotalProgress
  - [x] 持久化配置
  - [x] DevTools 集成

#### Store 中间件

- [x] 持久化中间件（已集成）
- [x] DevTools 中间件（已集成）

#### 测试

- [ ] 测试 Roadmap Store 状态更新
- [ ] 测试 Chat Store 消息管理
- [ ] 测试 UI Store 状态切换
- [ ] 测试 Learning Store 进度追踪
- [ ] 测试持久化功能
- [ ] 测试 DevTools 集成

**子任务**: `28/34` ✅ (测试在 Phase 5)

---

## Phase 2: API 集成与类型同步（第 4-6 天）

### 2.1 更新类型生成脚本 ✅

- [x] 更新 `scripts/generate-types.ts`
  - [x] 从后端 OpenAPI schema 生成类型
  - [x] 添加生成时间戳
  - [x] 添加版本信息
- [x] 创建 `scripts/check-types.ts` - 类型验证脚本
  - [x] 从后端获取最新 schema
  - [x] 与本地 schema 对比
  - [x] 检测类型差异
  - [x] 报告不一致项
- [x] 创建 `scripts/validate-env.ts` - 环境变量验证
  - [x] Zod schema 验证
  - [x] 类型化环境变量导出
- [x] 配置自动类型生成
  - [x] 添加 package.json scripts
  - [x] 添加 predev/prebuild hooks
  - [x] 创建 .env.example

**子任务**: `10/10` ✅

---

### 2.2 同步枚举和常量 ✅

#### 状态枚举

- [x] `lib/constants/status.ts`
  - [x] `TaskStatus` 枚举（与后端 100% 对齐）
  - [x] `ContentStatus` 枚举
  - [x] `WorkflowStep` 枚举
  - [x] `TASK_STATUS_CONFIG` 显示配置
  - [x] `CONTENT_STATUS_CONFIG` 显示配置

#### API 常量

- [x] `lib/constants/api.ts`
  - [x] API 端点常量
  - [x] 请求超时配置
  - [x] 重试配置
  - [x] 轮询间隔配置

#### 路由常量

- [x] `lib/constants/routes.ts`
  - [x] 应用路由路径
  - [x] 导航配置
  - [x] 面包屑配置

**子任务**: `10/10` ✅

---

### 2.3 实现 Zod Schema 验证 ✅

#### Roadmap Schema

- [x] `lib/schemas/roadmap.ts`
  - [x] `RoadmapFrameworkSchema`
  - [x] `StageSchema`
  - [x] `ModuleSchema`
  - [x] `ConceptSchema`
  - [x] 验证函数

#### SSE Events Schema

- [x] `lib/schemas/sse-events.ts`
  - [x] `BaseSSEEventSchema`
  - [x] `ProgressEventSchema`
  - [x] `StepCompleteEventSchema`
  - [x] `CompleteEventSchema`
  - [x] `ErrorEventSchema` (使用 'roadmap_error')
  - [x] `RoadmapGenerationEventSchema` (联合类型)
  - [x] 聊天修改事件 Schema
  - [x] 验证函数

#### User Schema

- [x] `lib/schemas/user.ts`
  - [x] `UserRequestSchema`
  - [x] `LearningPreferencesSchema`
  - [x] `UserProfileSchema`
  - [x] `CreateRoadmapFormSchema` (表单验证)
  - [x] 验证函数

#### 测试

- [ ] 测试 Schema 验证
- [ ] 测试错误消息
- [ ] 测试类型推导

**子任务**: `17/17` ✅ (测试在 Phase 5)

---

### 2.4 更新 SSE 事件类型 ✅

- [x] 重构 `types/custom/sse.ts`
  - [x] 与后端 `FRONTEND_API_GUIDE.md` 完全对齐
  - [x] 添加详细注释
  - [x] 导出类型守卫函数
- [x] 路线图生成事件类型
  - [x] `ProgressEvent`
  - [x] `StepCompleteEvent`
  - [x] `CompleteEvent`
  - [x] `ErrorEvent` (使用 'roadmap_error')
- [x] WebSocket 事件类型
  - [x] `ConnectedEvent`
  - [x] `CurrentStatusEvent`
  - [x] `HumanReviewRequiredEvent`
  - [x] `ConceptStartEvent/CompleteEvent/FailedEvent`
  - [x] `BatchStartEvent/CompleteEvent`
  - [x] `CompletedEvent/FailedEvent`
  - [x] `WSErrorEvent` (使用 'ws_error')
- [x] 聊天修改事件类型
  - [x] `AnalyzingEvent`
  - [x] `IntentsEvent`
  - [x] `ModifyingEvent`
  - [x] `ResultEvent`
  - [x] `ModificationDoneEvent`
  - [x] `ModificationErrorEvent` (使用 'modification_error')
- [x] 类型守卫函数
  - [x] `isProgressEvent()`
  - [x] `isStepCompleteEvent()`
  - [x] `isCompleteEvent()`
  - [x] `isErrorEvent()` (检查 'roadmap_error')
  - [x] `isWSErrorEvent()` (检查 'ws_error')
  - [x] `isModificationErrorEvent()` (检查 'modification_error')

**子任务**: `18/18` ✅

---

### ✅ Phase 2 Bug 修复 (2025-12-06)

发现并修复了两个重要 bug：

#### Bug 1: SSE 事件 discriminator 冲突 🔴
- **问题**: 三个错误事件使用相同的 `type: 'error'`
- **修复**: 使用唯一标识符 (`'roadmap_error'`, `'ws_error'`, `'modification_error'`)
- **影响**: types/custom/sse.ts + lib/schemas/sse-events.ts

#### Bug 2: 环境变量 Schema 类型不匹配 🟡
- **问题**: `.transform()` 在 `.default()` 之前，导致类型不匹配
- **修复**: 调整为正确顺序 `.default()` → `.transform()`
- **影响**: scripts/validate-env.ts + lib/utils/env.ts

详见: `BUG_FIX_PHASE2.md`

---

---

## Phase 3: React Hooks 实现（第 7-9 天）

### 3.1 实现 API Hooks ✅

#### 路线图相关 Hooks

- [x] `lib/hooks/api/use-roadmap.ts`
  - [x] useQuery 配置
  - [x] 缓存策略（5分钟）
  - [x] 错误处理
  - [x] Store 同步
- [x] `lib/hooks/api/use-roadmap-list.ts`
  - [x] 列表查询
  - [x] 分页支持
  - [x] 过滤条件
- [x] `lib/hooks/api/use-roadmap-generation.ts`
  - [x] useMutation 配置
  - [x] 乐观更新
  - [x] 成功/失败回调
- [x] `lib/hooks/api/use-task-status.ts`
  - [x] 轮询查询（2秒间隔）
  - [x] 条件查询（enabled）
  - [x] 自动停止（完成/失败）

#### 内容相关 Hooks

- [x] `lib/hooks/api/use-tutorial.ts`
  - [x] 教程查询
  - [x] 版本支持
  - [x] Markdown 预处理
- [x] `lib/hooks/api/use-resources.ts`
  - [x] 资源列表查询
  - [x] 按类型过滤
- [x] `lib/hooks/api/use-quiz.ts`
  - [x] 测验题目查询
  - [x] 答案验证
- [x] `lib/hooks/api/use-content-modification.ts`
  - [x] 内容修改 mutation
  - [x] 版本管理

#### 用户相关 Hooks

- [x] `lib/hooks/api/use-user-profile.ts`
  - [x] 用户画像查询
  - [x] 画像更新 mutation

#### 测试

- [ ] 测试数据获取
- [ ] 测试缓存策略
- [ ] 测试错误处理
- [ ] 测试轮询逻辑

**子任务**: `10/14` ✅ (测试在 Phase 5)

---

### 3.2 实现 WebSocket/SSE Hooks ✅

#### WebSocket Hook（路线图生成 - 主要方案）

- [x] `lib/hooks/websocket/use-roadmap-generation-ws.ts`
  - [x] WebSocket 连接管理
  - [x] 事件监听和分发
  - [x] 自动心跳（30秒）
  - [x] 自动重连（指数退避）
  - [x] 状态恢复（include_history）
  - [x] 错误降级到轮询
  - [x] Progress 事件处理
  - [x] HumanReview 事件处理
  - [x] Concept 级别事件（start/complete/failed）
  - [x] Batch 级别事件
  - [x] Complete/Failed 事件处理
  - [x] Store 状态同步
  - [x] 早期导航支持
  - [x] onComplete/onError 回调

#### SSE Hook（AI 聊天场景）

- [x] `lib/hooks/sse/use-chat-stream.ts`
  - [x] SSE 连接管理（@microsoft/fetch-event-source）
  - [x] 意图分析事件处理
  - [x] 修改进度事件处理
  - [x] 结果事件处理
  - [x] 流式输出处理
  - [x] Store 状态同步

#### 测试

- [ ] 测试 WebSocket 连接
- [ ] 测试事件处理
- [ ] 测试自动清理
- [ ] 测试错误恢复

**子任务**: `8/12` ✅ (测试在 Phase 5)

---

### 3.3 实现 UI Hooks ✅

- [x] `lib/hooks/ui/use-debounce.ts` - 防抖
- [x] `lib/hooks/ui/use-throttle.ts` - 节流
- [x] `lib/hooks/ui/use-media-query.ts` - 响应式断点
  - [x] useIsMobile, useIsTablet, useIsDesktop
- [x] `lib/hooks/ui/use-local-storage.ts` - LocalStorage 封装
  - [x] 类型安全
  - [x] 跨标签页同步
- [x] `lib/hooks/ui/use-intersection-observer.ts` - 可见性检测
  - [x] 懒加载支持
  - [x] freezeOnceVisible 选项
- [x] `lib/hooks/ui/use-clipboard.ts` - 剪贴板操作
  - [x] 状态反馈
- [x] `lib/hooks/ui/use-toggle.ts` - 布尔状态切换

**子任务**: `7/7` ✅

---

## Phase 4: 组件重构（第 10-14 天）

### 4.1 重构页面组件

#### 创建路线图页面

- [x] `app/(app)/new/page.tsx` (使用路由组)
  - [x] 使用 `useRoadmapGeneration` Hook
  - [x] 使用 `useRoadmapGenerationWS` Hook
  - [x] 表单验证（react-hook-form + zod）
  - [x] 加载状态展示
  - [x] 错误处理
  - [x] 用户画像集成
  - [x] 进度实时更新
  - [x] 早期导航（roadmap_id 可用时）

#### 路线图详情页面

- [x] `app/(app)/roadmap/[id]/page.tsx` (使用路由组)
  - [x] 使用 `useRoadmap` Hook
  - [x] 使用 `useTaskStatus` Hook（轮询）
  - [x] 实时生成状态监听
  - [x] 人工审核流程
  - [x] 内容状态展示
  - [x] 失败重试按钮
  - [x] 视图模式切换（List/Flow）

#### 学习页面

- [x] `app/(app)/roadmap/[id]/learn/[conceptId]/page.tsx` (使用路由组)
  - [x] 使用 `useTutorial` Hook
  - [x] 使用 `useResources` Hook
  - [x] 使用 `useQuiz` Hook
  - [x] Markdown 渲染
  - [x] 代码高亮
  - [x] 学习进度追踪
  - [x] 资源/测验标签页
  - [x] 导航（上一个/下一个 Concept）

#### 首页

- [x] `app/(app)/home/page.tsx` (使用路由组)
  - [x] 使用 `useRoadmapList` Hook (getUserRoadmaps API)
  - [x] 路线图卡片列表
  - [x] 过滤和搜索
  - [x] 加载状态 Skeleton

#### 用户画像页面

- [x] `app/(app)/profile/page.tsx` (使用路由组)
  - [x] 使用 `useUserProfile` Hook (getUserProfile API)
  - [x] 画像表单
  - [x] 技术栈选择
  - [x] 学习风格配置

**子任务**: `28/28` (100%) ✅

---

### 4.2 重构功能组件

#### 路线图组件

- [x] `components/roadmap/roadmap-view.tsx` - 路线图整体视图 ✅
  - [x] 列表视图
  - [x] 流程图视图（占位）
  - [x] 视图切换
- [x] `components/roadmap/stage-card.tsx` - Stage 卡片 ✅
  - [x] 折叠/展开
  - [x] 进度显示
  - [x] 模块列表
- [x] `components/roadmap/module-card.tsx` - Module 卡片 ✅
  - [x] 折叠/展开
  - [x] 学习目标列表
  - [x] Concept 列表
- [x] `components/roadmap/concept-card.tsx` - Concept 卡片（已有） ✅
  - [x] 内容状态图标
  - [x] 点击查看教程
  - [x] 加载状态
  - [x] 失败状态
- [x] `components/roadmap/generation-progress.tsx` - 生成进度（新增） ✅
  - [x] 进度条
  - [x] 当前阶段显示
  - [x] 阶段列表
  - [x] 实时更新
- [x] `components/roadmap/phase-indicator.tsx` - 阶段指示器（已有） ✅
- [x] `components/roadmap/human-review-dialog.tsx` - 人工审核对话框（已有） ✅
  - [x] 路线图预览
  - [x] 批准/拒绝按钮
  - [x] 反馈输入
- [x] `components/roadmap/retry-failed-button.tsx` - 重试失败按钮（已有） ✅
  - [x] 失败内容统计
  - [x] 一键重试

#### 教程组件

- [x] `components/tutorial/tutorial-viewer.tsx` - 教程查看器（新增） ✅
  - [x] Markdown 渲染
  - [x] 代码高亮
  - [x] 目录导航
  - [x] 进度追踪
- [x] `components/tutorial/markdown-renderer.tsx` - Markdown 渲染器（新增） ✅
  - [x] react-markdown 集成
  - [x] rehype-highlight 代码高亮
  - [x] remark-gfm GitHub 风格
- [x] `components/tutorial/code-block.tsx` - 代码块组件（新增） ✅
  - [x] 语法高亮
  - [x] 复制按钮
  - [x] 行号显示

#### 聊天组件

- [x] `components/chat/chat-widget.tsx` - 聊天窗口（新增） ✅
  - [x] 消息列表
  - [x] 输入框
  - [x] 发送按钮
  - [x] 上下文显示
- [x] `components/chat/message-list.tsx` - 消息列表（新增） ✅
  - [x] 消息气泡
  - [x] 时间戳
  - [x] 角色区分
- [x] `components/chat/streaming-message.tsx` - 流式消息（新增） ✅
  - [x] 打字机效果
  - [x] Markdown 实时渲染

**子任务**: `25/25` ✅

---

### 4.3 优化布局组件 ✅

- [x] `components/layout/app-shell.tsx` - 应用外壳（已有） ✅
  - [x] 响应式三栏布局
  - [x] 侧边栏折叠状态
  - [x] Loading 状态
- [x] `components/layout/left-sidebar.tsx` - 左侧边栏（已有） ✅
  - [x] Logo
  - [x] 导航菜单
  - [x] 最近访问
  - [x] 用户信息
- [x] `components/layout/right-sidebar.tsx` - 右侧边栏（已有） ✅
  - [x] ChatWidget 集成
  - [x] 折叠/展开
  - [x] 上下文切换
- [x] `components/common/loading-skeleton.tsx` - Loading Skeleton（已优化） ✅
  - [x] 路线图 Skeleton
  - [x] 卡片 Skeleton
  - [x] 列表 Skeleton
  - [x] 新增多种 Skeleton 类型
- [x] `components/common/error-boundary.tsx` - 错误边界（已有） ✅
  - [x] 错误捕获
  - [x] 错误展示
  - [x] 重试按钮

**子任务**: `9/9` ✅

---

## Phase 5: 测试与质量保证（第 15-17 天）

### 5.1 单元测试

#### API 测试

- [ ] `__tests__/unit/api/client.test.ts`
  - [ ] 测试基础配置
  - [ ] 测试环境变量
- [ ] `__tests__/unit/api/interceptors/auth.test.ts`
  - [ ] 测试 token 添加
  - [ ] 测试 token 过期处理
- [ ] `__tests__/unit/api/interceptors/error.test.ts`
  - [ ] 测试错误格式转换
  - [ ] 测试 401/403 重定向
  - [ ] 测试 500 错误处理
- [ ] `__tests__/unit/api/interceptors/retry.test.ts`
  - [ ] 测试重试逻辑
  - [ ] 测试指数退避
- [ ] `__tests__/unit/api/endpoints/roadmaps.test.ts`
  - [ ] 测试所有端点
  - [ ] Mock API 响应
  - [ ] 测试错误处理

#### Store 测试

- [ ] `__tests__/unit/store/roadmap-store.test.ts`
  - [ ] 测试状态初始化
  - [ ] 测试 Actions
  - [ ] 测试派生状态
  - [ ] 测试持久化
- [ ] `__tests__/unit/store/chat-store.test.ts`
  - [ ] 测试消息管理
  - [ ] 测试流式输入
- [ ] `__tests__/unit/store/ui-store.test.ts`
  - [ ] 测试 UI 状态切换
- [ ] `__tests__/unit/store/learning-store.test.ts`
  - [ ] 测试进度追踪

#### Hooks 测试

- [ ] `__tests__/unit/hooks/use-roadmap.test.ts`
  - [ ] 测试数据获取
  - [ ] 测试缓存
  - [ ] 测试错误处理
- [ ] `__tests__/unit/hooks/use-roadmap-generation.test.ts`
  - [ ] 测试 mutation
  - [ ] 测试乐观更新
- [ ] `__tests__/unit/hooks/use-task-status.test.ts`
  - [ ] 测试轮询
  - [ ] 测试自动停止
- [ ] `__tests__/unit/hooks/use-roadmap-generation-stream.test.ts`
  - [ ] 测试 SSE 连接
  - [ ] 测试事件处理

#### 工具函数测试

- [ ] `__tests__/unit/utils/format.test.ts`
  - [ ] 测试格式化函数
- [ ] `__tests__/unit/utils/validation.test.ts`
  - [ ] 测试验证函数
- [ ] `__tests__/unit/schemas/roadmap.test.ts`
  - [ ] 测试 Zod Schema
- [ ] `__tests__/unit/schemas/sse-events.test.ts`
  - [ ] 测试事件验证

**子任务**: `0/23`

---

### 5.2 集成测试

- [ ] `__tests__/integration/roadmap-generation.test.ts`
  - [ ] 测试完整生成流程
  - [ ] 测试 API + SSE 集成
  - [ ] 测试状态更新流程
  - [ ] 测试错误恢复
- [ ] `__tests__/integration/chat-modification.test.ts`
  - [ ] 测试意图分析流程
  - [ ] 测试内容修改流程
  - [ ] 测试流式输出
- [ ] `__tests__/integration/tutorial-learning.test.ts`
  - [ ] 测试教程加载
  - [ ] 测试学习进度追踪
  - [ ] 测试资源/测验切换

**子任务**: `0/10`

---

### 5.3 E2E 测试

#### 路线图生成流程

- [ ] `__tests__/e2e/roadmap-flow.spec.ts`
  - [ ] 填写学习目标
  - [ ] 选择偏好设置
  - [ ] 提交生成
  - [ ] 等待生成完成
  - [ ] 验证路线图结构
  - [ ] 导航到路线图详情

#### 教程学习流程

- [ ] `__tests__/e2e/tutorial-learning.spec.ts`
  - [ ] 选择 Concept
  - [ ] 查看教程内容
  - [ ] Markdown 渲染验证
  - [ ] 标记完成
  - [ ] 查看资源
  - [ ] 完成测验

#### 聊天修改流程

- [ ] `__tests__/e2e/chat-modification.spec.ts`
  - [ ] 打开聊天窗口
  - [ ] 输入修改请求
  - [ ] 等待意图分析
  - [ ] 确认修改
  - [ ] 验证内容更新

**子任务**: `0/15`

---

## Phase 6: 文档与优化（第 18-20 天）

### 6.1 更新文档

#### 架构文档

- [ ] `docs/ARCHITECTURE.md` - 更新架构文档
  - [ ] 更新目录结构
  - [ ] 更新数据流图
  - [ ] 更新状态机图
  - [ ] 添加组件关系图

#### API 集成文档

- [ ] `docs/API_INTEGRATION.md` - API 集成文档（新建）
  - [ ] 快速开始
  - [ ] API Hooks 使用指南
  - [ ] SSE 使用指南
  - [ ] 错误处理指南
  - [ ] 最佳实践
  - [ ] 常见问题

#### 开发指南

- [ ] `docs/DEVELOPMENT.md` - 开发指南（新建）
  - [ ] 环境配置
  - [ ] 本地开发流程
  - [ ] 调试技巧
  - [ ] Git 工作流
  - [ ] 代码规范
  - [ ] 提交规范

#### 测试指南

- [ ] `docs/TESTING.md` - 测试指南（新建）
  - [ ] 测试策略
  - [ ] 编写单元测试
  - [ ] 编写集成测试
  - [ ] E2E 测试指南
  - [ ] Mock 数据指南
  - [ ] 测试覆盖率目标

**子任务**: `0/19`

---

### 6.2 性能优化

#### 代码分割

- [ ] 动态导入大组件
  - [ ] TutorialDialog 懒加载
  - [ ] ChatWidget 懒加载
  - [ ] Markdown 编辑器懒加载
- [ ] 路由级别代码分割
  - [ ] 按页面分割
  - [ ] 按功能模块分割
- [ ] 第三方库按需加载
  - [ ] highlight.js 按语言加载
  - [ ] react-markdown 懒加载

#### 缓存策略

- [ ] TanStack Query 缓存优化
  - [ ] 设置合理的 staleTime
  - [ ] 设置合理的 gcTime
  - [ ] 预加载关键数据
- [ ] LocalStorage 缓存
  - [ ] 用户偏好
  - [ ] 学习进度
  - [ ] UI 状态
- [ ] Service Worker 缓存（可选）
  - [ ] 静态资源缓存
  - [ ] API 响应缓存

#### 渲染优化

- [ ] React.memo 优化
  - [ ] ConceptCard
  - [ ] StageCard
  - [ ] ModuleCard
- [ ] useMemo/useCallback 优化
  - [ ] 复杂计算缓存
  - [ ] 函数引用稳定
- [ ] 虚拟列表（长列表）
  - [ ] react-window 集成
  - [ ] Concept 列表虚拟化

#### 网络优化

- [ ] 请求去重
  - [ ] 防止重复请求
  - [ ] 请求缓存
- [ ] 请求合并
  - [ ] 批量查询
  - [ ] GraphQL（可选）
- [ ] 预加载关键资源
  - [ ] Link prefetch
  - [ ] 预加载下一页

**子任务**: `0/19`

---

### 6.3 开发体验优化

#### 开发工具

- [ ] TanStack Query DevTools
  - [ ] 安装和配置
  - [ ] 仅开发环境启用
- [ ] Zustand DevTools
  - [ ] Redux DevTools 集成
  - [ ] 状态变更追踪
- [ ] React DevTools 配置
  - [ ] Profiler 配置
  - [ ] 组件名称优化

#### 代码质量

- [ ] ESLint 配置更新
  - [ ] strict mode 规则
  - [ ] TypeScript 规则
  - [ ] React Hooks 规则
  - [ ] 自定义规则（禁止直接 API 调用）
- [ ] Prettier 配置
  - [ ] 格式化规则
  - [ ] 与 ESLint 集成
- [ ] Husky 配置
  - [ ] pre-commit: lint + type-check
  - [ ] pre-push: test
  - [ ] commit-msg: commitlint
- [ ] lint-staged 配置
  - [ ] 仅检查暂存文件
  - [ ] 自动格式化

#### 环境变量管理

- [ ] `.env.example` 示例文件
  - [ ] 所有环境变量列表
  - [ ] 说明注释
- [ ] 环境变量验证脚本
  - [ ] Zod schema 验证
  - [ ] 启动时检查
- [ ] 类型化环境变量
  - [ ] `lib/utils/env.ts`
  - [ ] 类型安全访问

#### 其他

- [ ] 添加 Storybook（可选）
  - [ ] 组件文档
  - [ ] 组件开发环境
- [ ] 添加 Bundle Analyzer
  - [ ] 分析打包大小
  - [ ] 优化建议

**子任务**: `0/18`

---

## 验收标准

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
- [ ] Lighthouse 分数 > 90

### 文档完整性

- [ ] API 集成文档完整
- [ ] 开发指南清晰
- [ ] 测试指南可操作
- [ ] 架构图更新
- [ ] 所有代码有注释

---

## 依赖包更新

### 需要添加的依赖

```bash
# 安装 SSE 支持
npm install @microsoft/fetch-event-source

# 安装测试框架
npm install -D vitest @testing-library/react @testing-library/react-hooks @playwright/test msw

# 安装性能分析工具（可选）
npm install -D @next/bundle-analyzer

# 安装 Storybook（可选）
npx storybook@latest init
```

- [ ] 安装 `@microsoft/fetch-event-source`
- [ ] 安装测试相关依赖
- [ ] 更新 `package.json` scripts
- [ ] 更新 `package.json` 版本号

---

## 里程碑检查点

- [ ] **M1（第 3 天）**: 基础设施完成
  - [ ] lib/ 目录完整
  - [ ] API 客户端可用
  - [ ] SSE 客户端可用
  - [ ] Stores 实现完成

- [ ] **M2（第 6 天）**: API 集成完成
  - [ ] 类型完全同步
  - [ ] 枚举对齐
  - [ ] Schema 验证可用

- [ ] **M3（第 9 天）**: Hooks 库完成
  - [ ] 所有 API Hooks 可用
  - [ ] SSE Hooks 可用
  - [ ] UI Hooks 可用

- [ ] **M4（第 14 天）**: 组件重构完成
  - [ ] 所有页面使用新 API
  - [ ] 所有组件重构完成
  - [ ] 布局优化完成

- [ ] **M5（第 17 天）**: 测试覆盖达标
  - [ ] 单元测试覆盖率 ≥ 80%
  - [ ] 集成测试完成
  - [ ] E2E 测试完成

- [ ] **M6（第 20 天）**: 项目完整重构
  - [ ] 所有功能验证通过
  - [ ] 性能指标达标
  - [ ] 文档完整
  - [ ] 代码质量合格

---

## 注意事项

1. **并行开发**: Phase 1-3 的部分任务可以并行进行
2. **渐进测试**: 每完成一个模块立即编写测试
3. **文档同步**: 代码和文档同步更新
4. **Code Review**: 关键模块完成后进行 Review
5. **性能监控**: 持续监控性能指标

---

**最后更新**: 2025-12-06  
**维护者**: Frontend Team
