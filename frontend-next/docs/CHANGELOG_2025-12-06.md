# 前端重构计划变更日志

> **日期**: 2025-12-06  
> **版本**: v2.1.0  
> **变更类型**: 实时通信方案调整

---

## 📋 变更摘要

基于后端已有的完整 WebSocket 实现，将前端重构计划的实时通信方案从"SSE 优先"调整为"WebSocket 优先（路线图）+ SSE（AI 聊天）"。

### 关键决策

**之前**: SSE 作为路线图生成和 AI 聊天的统一方案  
**现在**: 
- ✅ **路线图生成**: WebSocket（主）+ 轮询（降级）
- ✅ **AI 聊天**: SSE

**原因**:
1. 路线图生成有人工审核环节，需要双向通信
2. 用户可能刷新页面或离开再回来，需要状态恢复
3. WebSocket 支持 `include_history` 参数，完美适配状态持久化场景
4. AI 聊天是流式输出，SSE 更简单适用

---

## 📝 文档更新清单

### 1. backend/docs/FRONTEND_API_GUIDE.md

**位置**: Section 6 - 实时通知协议（第 866-906 行）

**更新内容**:

#### ✅ 补充 WebSocket 完整文档（新增 600+ 行）

1. **连接说明**
   - 端点：`ws://localhost:8000/ws/{task_id}`
   - 查询参数：`include_history=true/false`
   - 优点和适用场景

2. **完整事件类型定义**（11 种事件）
   
   **连接级别**:
   - `ConnectedEvent` - 连接成功
   - `CurrentStatusEvent` - 当前状态（状态恢复）
   - `ClosingEvent` - 连接关闭
   - `ErrorEvent` - 错误

   **阶段级别**:
   - `ProgressEvent` - 进度更新
   - `HumanReviewRequiredEvent` - 人工审核
   - `CompletedEvent` - 任务完成
   - `FailedEvent` - 任务失败

   **Concept 级别**:
   - `ConceptStartEvent` - 开始生成
   - `ConceptCompleteEvent` - 生成完成
   - `ConceptFailedEvent` - 生成失败

   **批次级别**:
   - `BatchStartEvent` - 批次开始
   - `BatchCompleteEvent` - 批次完成

3. **客户端消息格式**
   - `PingMessage` - 心跳
   - `GetStatusMessage` - 请求状态

4. **使用示例**（3 个完整示例）
   - 基础连接和事件监听
   - 页面刷新后状态恢复
   - 错误处理和降级策略

5. **场景推荐**
   - 路线图生成：WebSocket + 轮询
   - AI 聊天：SSE

#### ✅ 更新 SSE 章节说明

- 标注为"适用于 AI 聊天"
- 补充优点和使用场景
- 简化示例

---

### 2. frontend-next/REFACTORING_PLAN.md

**位置**: Phase 1.3 - 实现实时通信客户端（第 854-880 行）

**更新内容**:

#### ✅ 调整目录结构

```typescript
lib/api/
├── websocket/              # 路线图生成（P0）
│   ├── roadmap-ws.ts
│   └── heartbeat.ts
├── polling/                # 降级方案（P0）
│   └── task-polling.ts
└── sse/                    # AI 聊天（P1）
    ├── client.ts
    └── chat-sse.ts
```

#### ✅ 调整任务优先级

- 🔴 P0: WebSocket 客户端、轮询客户端
- 🟡 P1: SSE 客户端

#### ✅ 新增代码示例（4 个完整类）

1. **RoadmapWebSocket 类**（~120 行）
   - 完整的事件处理
   - 心跳机制（30 秒）
   - 自动重连（指数退避）
   - 状态恢复（include_history）

2. **TaskPolling 类**（~40 行）
   - 轮询逻辑（2 秒间隔）
   - 自动停止
   - 错误处理

3. **useRoadmapGenerationWS Hook**（~100 行）
   - WebSocket 优先
   - 自动降级到轮询
   - Store 集成
   - 状态恢复

4. **useChatStream Hook**（~60 行）
   - SSE 流式监听
   - 流式输出处理

---

### 3. frontend-next/REFACTORING_CHECKLIST.md

**位置**: Phase 1.3（第 124-161 行）

**更新内容**:

#### ✅ 更新任务清单

**新增任务**:
- WebSocket 基础客户端（P0）
- 路线图生成 WebSocket 封装（P0）
- 心跳和重连机制（P0）
- 降级到轮询的策略（P0）
- 轮询客户端实现（P0）

**调整任务**:
- SSE 基础客户端（P0 → P1）
- 聊天流式 SSE 封装（P0 → P1）

**测试任务扩展**:
- 新增 WebSocket 测试项（6 项）
- 保留 SSE 测试项（2 项）

**子任务数**: 15 → 27

---

### 4. frontend-next/QUICK_START.md

**更新内容**:

#### ✅ 更新架构图

- 添加 WebSocket 层说明
- 添加实时通信方案说明

#### ✅ 更新创建目录命令

```bash
mkdir -p lib/api/{endpoints,websocket,polling,sse,interceptors}
mkdir -p lib/hooks/{api,websocket,sse,ui}
```

#### ✅ 更新执行流程

- Phase 1: WebSocket 客户端（优先）
- Day 3: WebSocket 而非 SSE

#### ✅ 更新重点关注

- 重点关注 WebSocket 事件类型（Section 6）

---

### 5. frontend-next/README.md

**更新内容**:

#### ✅ 更新 Tech Stack

```diff
- Streaming | Native SSE (Server-Sent Events)
+ Real-time (Roadmap) | WebSocket + Polling (fallback)
+ Real-time (Chat) | SSE (Server-Sent Events)
```

#### ✅ 更新 Project Structure

- 添加 `lib/api/websocket/` 目录
- 添加 `lib/api/polling/` 目录
- 添加 `lib/hooks/websocket/` 目录

#### ✅ 更新 API Integration 示例

- 新增 WebSocket 使用示例
- 更新 SSE 示例（标注为 AI 聊天）

---

## 📊 更新统计

### 文档修改

| 文档 | 新增行数 | 修改行数 | 删除行数 |
|:---|:---:|:---:|:---:|
| FRONTEND_API_GUIDE.md | ~600 | ~40 | ~20 |
| REFACTORING_PLAN.md | ~350 | ~100 | ~50 |
| REFACTORING_CHECKLIST.md | ~40 | ~20 | ~10 |
| QUICK_START.md | ~20 | ~30 | ~10 |
| README.md | ~30 | ~20 | ~10 |
| **总计** | **~1,040** | **~210** | **~100** |

### 代码示例

| 示例 | 行数 | 文件 |
|:---|:---:|:---|
| RoadmapWebSocket 类 | ~120 | REFACTORING_PLAN.md, FRONTEND_API_GUIDE.md |
| TaskPolling 类 | ~40 | REFACTORING_PLAN.md |
| useRoadmapGenerationWS Hook | ~100 | REFACTORING_PLAN.md |
| useChatStream Hook | ~60 | REFACTORING_PLAN.md |
| ChatSSE 类 | ~60 | REFACTORING_PLAN.md |
| **总计** | **~380 行** | - |

---

## 🎯 技术方案对比

### 路线图生成场景

| 特性 | WebSocket (✅ 采用) | SSE | 轮询 |
|:---|:---:|:---:|:---:|
| **实时性** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **双向通信** | ✅ | ❌ | ❌ |
| **状态恢复** | ✅ (`include_history`) | ❌ | ✅ |
| **人工审核支持** | ✅ | ⚠️ 需轮询 | ✅ |
| **页面刷新恢复** | ✅ | ❌ | ✅ |
| **心跳保持** | ✅ | ✅ (自动) | N/A |
| **实现复杂度** | 中 | 低 | 低 |
| **健壮性** | 高（+ 降级） | 中 | 高 |
| **带宽占用** | 低 | 低 | 高 |

**选择**: WebSocket（主）+ 轮询（降级）

### AI 聊天场景

| 特性 | SSE (✅ 采用) | WebSocket |
|:---|:---:|:---:|
| **流式输出** | ⭐⭐⭐ | ⭐⭐ |
| **实现简单** | ✅ | ❌ |
| **自动重连** | ✅ | 需实现 |
| **单向通信** | ✅ | ⚠️ 过度设计 |
| **浏览器兼容** | 好 | 好 |
| **适用场景** | 流式输出 | 双向交互 |

**选择**: SSE

---

## 🔄 实施影响

### 开发优先级调整

**Phase 1（第 1-3 天）**:

之前:
1. API 客户端
2. SSE 客户端
3. Zustand Stores

现在:
1. API 客户端
2. 🔴 **WebSocket 客户端**（新增，优先）
3. 🔴 **轮询客户端**（新增，优先）
4. Zustand Stores
5. 🟡 SSE 客户端（降级为 P1）

### 任务数调整

- Phase 1: 23 → **27** 任务（+4）
- 总任务数: 111 → **115** 任务（+4）

### 时间估算不变

- 总工期仍为 **20 天**（SSE 开发时间转移到 WebSocket）

---

## ✅ 已完成的更新

- [x] FRONTEND_API_GUIDE.md - WebSocket 完整文档
- [x] FRONTEND_API_GUIDE.md - SSE 章节调整
- [x] REFACTORING_PLAN.md - Phase 1.3 重写
- [x] REFACTORING_PLAN.md - 代码示例更新
- [x] REFACTORING_CHECKLIST.md - 任务优先级调整
- [x] QUICK_START.md - 架构和流程更新
- [x] README.md - Tech Stack 和示例更新
- [x] REFACTORING_SUMMARY.md - 方案对比更新
- [x] REFACTORING_UPDATE_SUMMARY.md - 创建更新总结
- [x] CHANGELOG_2025-12-06.md - 创建变更日志（本文档）

---

## 🚀 后续行动

### 立即开始

1. **查看更新后的文档**
   ```bash
   # WebSocket API 文档
   open backend/docs/FRONTEND_API_GUIDE.md
   
   # 重构计划
   open frontend-next/REFACTORING_PLAN.md
   
   # 更新总结
   open frontend-next/REFACTORING_UPDATE_SUMMARY.md
   ```

2. **按新优先级开发**
   - Day 1-2: API 客户端
   - Day 3: WebSocket 客户端 + 轮询
   - Day 4-5: Zustand Stores
   - Week 2: Hooks 和组件
   - Week 3+: SSE（AI 聊天）、测试、优化

3. **参考完整代码**
   - 所有示例都可以直接使用
   - TypeScript 类型完整
   - 包含错误处理和降级逻辑

---

## 📚 相关资源

### 后端实现参考

- **WebSocket 端点**: `backend/app/api/v1/websocket.py`
- **事件服务**: `backend/app/services/notification_service.py`
- **测试脚本**: `backend/scripts/test_websocket.py`

### 前端文档

- **重构计划**: `frontend-next/REFACTORING_PLAN.md`
- **执行清单**: `frontend-next/REFACTORING_CHECKLIST.md`
- **快速开始**: `frontend-next/QUICK_START.md`
- **配置更新**: `frontend-next/CONFIG_UPDATES.md`

### 技术文档

- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Redis Pub/Sub](https://redis.io/docs/manual/pubsub/)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 🎉 总结

此次更新完全基于后端已有的成熟 WebSocket 实现，无需后端开发新功能，仅需完善文档。前端重构计划已全面调整，可以立即开始开发。

**核心收益**:
- ✅ 更好的用户体验（状态恢复、人工审核支持）
- ✅ 更健壮的实时通信（降级策略）
- ✅ 更清晰的技术选型（场景适配）
- ✅ 完整的文档和示例（快速开发）

---

**变更负责人**: Frontend Team  
**审核人**: Backend Team  
**批准日期**: 2025-12-06  
**生效日期**: 2025-12-06
