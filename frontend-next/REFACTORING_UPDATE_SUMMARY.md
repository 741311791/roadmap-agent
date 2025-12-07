# 前端重构计划更新总结

> **更新日期**: 2025-12-06  
> **更新原因**: 调整实时通信方案，WebSocket 优先（路线图生成），SSE 为辅（AI 聊天）

---

## 📝 更新内容概览

基于后端已有的完整 WebSocket 实现，对前端重构计划和前后端联调文档进行了全面调整。

### 更新的文件

| 文件 | 更新内容 | 状态 |
|:---|:---|:---:|
| **backend/docs/FRONTEND_API_GUIDE.md** | 补充完整的 WebSocket API 文档 | ✅ |
| **frontend-next/REFACTORING_PLAN.md** | 调整 Phase 1.3 为 WebSocket 优先 | ✅ |
| **frontend-next/REFACTORING_CHECKLIST.md** | 更新任务优先级和清单 | ✅ |
| **frontend-next/QUICK_START.md** | 补充 WebSocket 架构说明 | ✅ |
| **frontend-next/README.md** | 更新实时通信方案说明 | ✅ |

---

## 🔄 核心变更

### 1. 实时通信方案调整

**之前**：
- SSE 作为主要方案（路线图生成 + AI 聊天）
- WebSocket 标记为"可选"

**现在**：
- ✅ **路线图生成**：WebSocket（主）+ 轮询（降级）
  - 支持人工审核环节
  - 支持状态持久化和恢复
  - 支持页面刷新后继续
  - 完整的 Concept 级别进度事件
  
- ✅ **AI 聊天**：SSE
  - 流式输出、逐字显示
  - 实现简单
  - 适合单向通信

### 2. WebSocket API 文档补充

在 `backend/docs/FRONTEND_API_GUIDE.md` 中补充了：

#### ✅ 完整的事件类型定义（11 种事件）

**连接级别**：
- `connected` - 连接成功确认
- `current_status` - 当前任务状态（用于状态恢复）
- `closing` - 连接即将关闭
- `error` - 错误事件

**阶段级别**：
- `progress` - 任务进度更新
- `human_review_required` - 人工审核请求
- `completed` - 任务完成
- `failed` - 任务失败

**Concept 级别**：
- `concept_start` - 概念内容生成开始
- `concept_complete` - 概念内容生成完成
- `concept_failed` - 概念内容生成失败

**批次级别**：
- `batch_start` - 批次处理开始
- `batch_complete` - 批次处理完成

#### ✅ 客户端消息格式

- `ping` - 心跳消息
- `get_status` - 主动请求状态

#### ✅ 完整使用示例

- 基础连接示例
- 页面刷新后状态恢复
- 错误处理和降级策略
- 心跳机制

### 3. 前端重构计划调整

#### 目录结构调整

```typescript
lib/api/
├── websocket/              # 🆕 路线图生成（优先级 P0）
│   ├── roadmap-ws.ts
│   └── heartbeat.ts
├── polling/                # 🆕 轮询降级方案（优先级 P0）
│   └── task-polling.ts
└── sse/                    # AI 聊天（优先级 P1）
    ├── client.ts
    └── chat-sse.ts
```

#### Phase 1.3 任务调整

**新增任务**（优先级 P0）：
- WebSocket 基础客户端
- 路线图生成 WebSocket 封装
- 心跳和重连机制
- 降级到轮询的策略

**调整任务**（优先级降为 P1）：
- SSE 基础客户端（用于 AI 聊天）
- 聊天流式 SSE 封装

#### 代码示例更新

新增以下完整代码示例：

1. **WebSocket 客户端** (`RoadmapWebSocket` 类)
   - 完整的事件处理
   - 心跳机制
   - 自动重连
   - 状态恢复

2. **轮询客户端** (`TaskPolling` 类)
   - 轮询逻辑
   - 自动停止
   - 错误处理

3. **混合策略 Hook** (`useRoadmapGenerationWS`)
   - WebSocket 优先
   - 自动降级到轮询
   - Store 集成
   - 早期导航支持

4. **AI 聊天 SSE Hook** (`useChatStream`)
   - SSE 流式监听
   - 流式输出处理

---

## 📊 更新统计

### 文档更新

| 文档 | 新增内容 | 更新内容 |
|:---|:---:|:---:|
| FRONTEND_API_GUIDE.md | 600+ 行 | WebSocket 完整文档 |
| REFACTORING_PLAN.md | - | Phase 1.3 重写 |
| REFACTORING_CHECKLIST.md | 12 个任务 | 任务优先级调整 |
| QUICK_START.md | - | 架构图和流程更新 |
| README.md | - | Tech Stack 更新 |

### 代码示例

| 示例 | 行数 | 说明 |
|:---|:---:|:---|
| RoadmapWebSocket 类 | ~120 行 | WebSocket 客户端 |
| TaskPolling 类 | ~40 行 | 轮询客户端 |
| useRoadmapGenerationWS Hook | ~100 行 | 混合策略 Hook |
| useChatStream Hook | ~60 行 | AI 聊天 SSE Hook |

---

## 🎯 技术选型对比

### 路线图生成场景

| 特性 | WebSocket | SSE | 轮询 |
|:---|:---:|:---:|:---:|
| 实时性 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| 双向通信 | ✅ | ❌ | ❌ |
| 状态恢复 | ✅ | ❌ | ✅ |
| 人工审核支持 | ✅ | ⚠️ | ✅ |
| 实现复杂度 | 中 | 低 | 低 |
| 健壮性 | 高（+ 降级） | 中 | 高 |

**最终选择**：WebSocket（主） + 轮询（降级）

### AI 聊天场景

| 特性 | SSE | WebSocket |
|:---|:---:|:---:|
| 流式输出 | ⭐⭐⭐ | ⭐⭐ |
| 实现简单 | ✅ | ❌ |
| 自动重连 | ✅ | 需要实现 |
| 适合场景 | 单向流式 | 双向交互 |

**最终选择**：SSE

---

## 🚀 后续实施建议

### Phase 1 优先级调整

#### 必须实现（P0）

1. WebSocket 客户端（3 天）
   - `lib/api/websocket/roadmap-ws.ts`
   - `lib/api/polling/task-polling.ts`
   - `lib/hooks/websocket/use-roadmap-generation-ws.ts`

2. Zustand Stores（1 天）
   - `lib/store/roadmap-store.ts`
   - `lib/store/ui-store.ts`

#### 可后续实现（P1）

3. SSE 客户端（2 天）
   - `lib/api/sse/chat-sse.ts`
   - `lib/hooks/sse/use-chat-stream.ts`

### 开发顺序建议

```
Week 1:
  Day 1-2: API 客户端 + 拦截器
  Day 3-4: WebSocket 客户端 + 轮询
  Day 5:   Zustand Stores

Week 2:
  Day 6-7: API Hooks + WebSocket Hooks
  Day 8:   页面组件重构（new/page.tsx）
  Day 9:   页面组件重构（roadmap/[id]/page.tsx）
  Day 10:  集成测试

Week 3:
  Day 11-12: SSE 客户端（AI 聊天）
  Day 13-14: 聊天组件重构
  Day 15:    E2E 测试

Week 4:
  Day 16-17: 性能优化
  Day 18-19: 文档更新
  Day 20:    最终验收
```

---

## ✅ 验收标准

### 功能完整性

- [x] WebSocket API 文档完整
- [ ] WebSocket 客户端实现
- [ ] 轮询降级方案实现
- [ ] 状态恢复功能可用
- [ ] 人工审核流程支持
- [ ] SSE 客户端实现（AI 聊天）

### 文档完整性

- [x] FRONTEND_API_GUIDE.md 补充完整
- [x] REFACTORING_PLAN.md 调整完成
- [x] REFACTORING_CHECKLIST.md 更新
- [x] QUICK_START.md 更新
- [x] README.md 更新

### 架构清晰性

- [x] 实时通信方案明确
- [x] 降级策略清晰
- [x] 场景推荐准确
- [x] 代码示例完整

---

## 🔍 关键技术点总结

### 1. WebSocket 状态恢复

```typescript
// 连接时获取历史状态
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}?include_history=true`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'current_status') {
    // 根据当前状态恢复 UI
    restoreUIState(data);
  }
};
```

### 2. 自动降级策略

```typescript
// WebSocket 错误时自动降级到轮询
ws.onerror = () => {
  console.warn('WebSocket 错误，降级到轮询');
  startPolling(taskId);
};
```

### 3. 心跳保持连接

```typescript
// 每 30 秒发送心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

### 4. 早期导航优化

```typescript
// roadmap_id 可用时立即导航
if (event.data?.roadmap_id && event.step === 'curriculum_design') {
  router.push(`/app/roadmap/${event.data.roadmap_id}`);
}
```

---

## 📚 参考文档

### 后端 API 文档

- **WebSocket API**: `backend/docs/FRONTEND_API_GUIDE.md` - Section 6（实时通知协议）
- **WebSocket 实现**: `backend/app/api/v1/websocket.py`
- **事件服务**: `backend/app/services/notification_service.py`

### 前端重构文档

- **重构计划**: `frontend-next/REFACTORING_PLAN.md`
- **执行清单**: `frontend-next/REFACTORING_CHECKLIST.md`
- **快速开始**: `frontend-next/QUICK_START.md`
- **配置更新**: `frontend-next/CONFIG_UPDATES.md`

---

## 🎉 下一步

1. ✅ **查看更新后的文档**
   ```bash
   # 查看 WebSocket API 文档
   open backend/docs/FRONTEND_API_GUIDE.md
   
   # 查看更新后的重构计划
   open frontend-next/REFACTORING_PLAN.md
   ```

2. ✅ **按照新的优先级开始开发**
   - 优先实现 WebSocket 客户端（P0）
   - 其次实现轮询降级（P0）
   - 最后实现 SSE 客户端（P1，用于 AI 聊天）

3. ✅ **参考完整代码示例**
   - 所有文档中都包含完整的 TypeScript 代码示例
   - 可以直接复制粘贴开始开发

---

**文档维护者**: Frontend Team  
**最后更新**: 2025-12-06  
**版本**: v2.1.0
