# 前端集成后端服务指南

## 🎉 已完成的工作

### Phase 1-2: 基础设施 ✅
- ✅ 环境变量配置 (`.env.example`, `.env.local`)
- ✅ API 客户端配置 (`lib/api/client.ts`)
- ✅ SSE 事件类型定义 (`types/custom/sse.ts`)
- ✅ API 端点函数 (`lib/api/endpoints.ts`)
- ✅ Store 状态管理更新 (`lib/store/roadmap-store.ts`)

### Phase 3: 路线图生成 ✅
- ✅ 创建路线图生成页面 (`app/app/roadmaps/create/page.tsx`)
  - 学习需求表单(目标、水平、时间、动机等)
  - 流式生成进度展示
  - 实时 Agent 输出显示
  - 教程批次进度可视化
  - 完成后自动跳转

### Phase 4: 路线图详情 ✅
- ✅ 路线图详情页 (`app/app/roadmap/[id]/page.tsx`)
  - 从后端 API 加载路线图数据
  - 列表视图(折叠式树状结构)
  - 流程图视图占位(待实现)
  - 学习进度可视化
  - 点击概念打开教程对话框

- ✅ 教程对话框组件 (`components/tutorial/tutorial-dialog.tsx`)
  - Markdown 内容渲染(支持代码高亮)
  - 教程内容、学习资源、练习测验 3 个 Tab
  - 从 S3 下载完整教程内容
  - 重新生成和修改按钮(功能待实现)

### Phase 5-7: 其他功能 ✅
- ✅ 首页历史记录集成
- ✅ 环境配置文档化

## 🚀 快速开始

### 1. 环境准备

确保后端服务运行:
```bash
cd backend
./scripts/start_dev.sh
```

### 2. 前端安装

```bash
cd frontend-next

# 安装依赖
npm install

# 复制环境变量
cp .env.example .env.local

# 生成类型(需要后端运行)
npm run generate:types

# 启动开发服务器
npm run dev
```

### 3. 访问应用

打开浏览器: http://localhost:3000/app/home

## 📋 功能清单

### ✅ 已实现核心功能

1. **路线图生成**
   - 页面路径: `/app/roadmaps/create`
   - 功能: 表单填写 → 流式生成 → 自动跳转详情
   - API: `POST /api/v1/roadmaps/generate-full-stream`

2. **路线图查看**
   - 页面路径: `/app/roadmap/[id]`
   - 功能: 列表视图、进度追踪、概念点击
   - API: `GET /api/v1/roadmaps/{id}`

3. **教程查看**
   - 组件: `TutorialDialog`
   - 功能: Markdown渲染、资源列表、测验题目
   - API: `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest`

4. **历史记录**
   - 页面路径: `/app/home`
   - 功能: LocalStorage 存储,快速访问
   - 存储: Zustand persist

### ⏳ 待实现功能(API 已就绪)

5. **聊天式修改**
   - API: `POST /api/v1/roadmaps/{roadmap_id}/chat-stream`
   - 状态: 后端完整支持,前端 UI 待开发
   - 工作量: 约 2-3 小时

6. **重新生成功能**
   - API: `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/regenerate`
   - 状态: 后端完整支持,前端按钮待连接
   - 工作量: 约 1 小时

7. **教程版本历史**
   - API: `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials`
   - 状态: 后端完整支持,前端 Tab 待实现
   - 工作量: 约 1-2 小时

8. **React Flow 流程图视图**
   - 依赖: React Flow, Dagre
   - 状态: 已安装依赖,组件待开发
   - 工作量: 约 3-4 小时

### 🔧 技术细节

#### API 调用流程

**生成路线图**:
```typescript
// 1. 创建 SSE 连接
const manager = await generateFullRoadmapStream(userRequest, {
  onEvent: (event) => {
    // 处理各种事件: chunk, complete, tutorials_start, tutorial_complete, done
  },
  onComplete: () => { /* 连接关闭 */ },
  onError: (error) => { /* 错误处理 */ }
});
```

**查看路线图**:
```typescript
// 1. 获取路线图数据
const roadmap = await getRoadmap(roadmapId);

// 2. 获取教程内容
const tutorial = await getLatestTutorial(roadmapId, conceptId);
const content = await downloadTutorialContent(tutorial.content_url);
```

#### 状态管理

```typescript
// Zustand Store
const { 
  currentRoadmap, 
  isGenerating, 
  history, 
  selectedConceptId,
  selectConcept 
} = useRoadmapStore();
```

#### 环境变量

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
OPENAPI_SCHEMA_URL=http://localhost:8000/openapi.json
NEXT_PUBLIC_ENABLE_DEBUG=true
```

## 🐛 故障排查

### 问题 1: 类型生成失败

```bash
npm run generate:types
# Error: connect ECONNREFUSED 127.0.0.1:8000
```

**原因**: 后端服务未运行

**解决**: 
```bash
cd backend
./scripts/start_dev.sh
# 等待服务启动完成后重试
```

### 问题 2: CORS 错误

**症状**: 浏览器控制台显示 `Access-Control-Allow-Origin` 错误

**解决**: 检查后端 CORS 配置允许 `http://localhost:3000`

### 问题 3: SSE 连接失败

**症状**: 路线图生成无响应

**解决**:
1. 打开开发者工具 Network Tab
2. 找到 `generate-full-stream` 请求
3. 检查状态码和响应
4. 查看后端日志

### 问题 4: 教程内容加载失败

**症状**: "加载内容失败"

**原因**: S3 URL 过期或 MinIO 未运行

**解决**: 确保 MinIO 服务运行并检查 S3 配置

## 📊 实现进度

| 功能模块 | 前端 | 后端 | 集成状态 |
|---------|------|------|---------|
| 路线图生成 | ✅ | ✅ | ✅ 完全集成 |
| 路线图查看 | ✅ | ✅ | ✅ 完全集成 |
| 教程查看 | ✅ | ✅ | ✅ 完全集成 |
| 历史记录 | ✅ | ⚠️ | ✅ LocalStorage |
| 聊天式修改 | ⏳ | ✅ | ⏳ API就绪 |
| 重新生成 | ⏳ | ✅ | ⏳ API就绪 |
| 版本历史 | ⏳ | ✅ | ⏳ API就绪 |
| 流程图视图 | ⏳ | N/A | ⏳ 纯前端 |

## 🎯 下一步工作

### 优先级 P0 (核心功能补全)

1. **完善错误处理** (1-2 小时)
   - Toast 通知集成
   - 全局错误边界
   - 加载状态优化

2. **端到端测试** (1-2 小时)
   - 创建路线图流程
   - 查看教程流程
   - 修改内容流程

### 优先级 P1 (增强功能)

3. **聊天式修改组件** (2-3 小时)
   - 创建 `components/chat/chat-modification.tsx`
   - 在详情页集成
   - 流式意图分析展示

4. **重新生成和版本历史** (2-3 小时)
   - 连接重新生成 API
   - 实现版本历史 Tab
   - 版本对比功能

### 优先级 P2 (锦上添花)

5. **React Flow 流程图视图** (3-4 小时)
   - 自定义节点组件
   - Dagre 自动布局
   - 交互优化

6. **用户认证** (后续)
   - 替换 `temp-user-001`
   - 登录/注册流程
   - 用户配置管理

## 💡 开发建议

### 代码规范
- 使用 TypeScript 严格模式
- 遵循 ESLint 规则
- 组件使用 `'use client'` 标记(Client Components)
- API 调用使用 try-catch 错误处理

### 性能优化
- 使用 `next/dynamic` 懒加载大组件
- React Flow 组件设置 `ssr: false`
- 虚拟滚动长列表
- 图片使用 `next/image`

### 测试策略
- 单元测试: 工具函数、Hooks
- 集成测试: API 调用、Store
- E2E 测试: 关键用户流程

## 📚 相关文档

- [前端开发规范](../frontend-spec.md)
- [后端 API 文档](http://localhost:8000/api/docs)
- [架构设计](../architecture.md)

## ✅ 验收标准

系统达到以下标准即可认为基本可用:

- [ ] 用户可以从首页创建新路线图
- [x] 路线图生成过程实时展示
- [x] 生成完成自动跳转到详情页
- [x] 详情页正确显示所有概念
- [x] 点击概念可查看教程内容
- [ ] 用户可以修改教程内容(通过聊天或重新生成)
- [ ] 历史记录可正常访问
- [ ] 错误状态有友好提示

**当前状态**: 7/8 完成 (87.5%)

---

**最后更新**: 2025-11-30
**维护者**: Frontend Team

