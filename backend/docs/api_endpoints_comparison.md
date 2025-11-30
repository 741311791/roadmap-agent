# API 端点对比说明

## 路线图生成 API 端点

系统提供了两种不同的路线图生成API端点，各有不同的用途和特点：

### 1. `/api/v1/roadmaps/generate` - 后台任务模式 ✅

**特点：**
- 异步后台任务执行
- **会保存到数据库** ✓
- 立即返回任务 ID
- 通过 WebSocket 或轮询接口查询进度
- 使用完整的 LangGraph 工作流（包含结构验证、人工审核等）
- 支持 Human-in-the-Loop

**使用场景：**
- 生产环境
- 需要保存路线图和教程到数据库
- 需要人工审核
- 需要通过 WebSocket 实时查看进度

**数据库写入：**
- ✅ 创建 `roadmap_tasks` 记录
- ✅ 保存 `roadmap_metadata`
- ✅ 保存 `tutorial_metadata`（如果生成教程）

**示例：**
```bash
curl -X POST http://localhost:8000/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{...}'
  
# 返回
{
  "task_id": "xxx-xxx-xxx",
  "status": "processing",
  "message": "路线图生成任务已启动..."
}
```

---

### 2. `/api/v1/roadmaps/generate-stream` - 流式模式（已修复）✅

**特点：**
- Server-Sent Events (SSE) 流式传输
- **现在会保存到数据库** ✓（修复后）
- 实时返回生成过程的每个 token
- 不使用 LangGraph 工作流（直接调用 Agent）
- 跳过结构验证和人工审核
- 可选是否生成教程（`include_tutorials` 参数）

**使用场景：**
- 演示和测试
- 需要实时展示生成过程
- 不需要人工审核的场景
- 快速预览生成结果

**数据库写入：**（修复后）
- ✅ 创建 `roadmap_tasks` 记录
- ✅ 保存 `roadmap_metadata`
- ✅ 保存 `tutorial_metadata`（如果 `include_tutorials=true`）

**示例：**
```bash
# 仅生成需求分析和路线图框架
python scripts/test_streaming.py

# 生成完整路线图（包含教程）
python scripts/test_streaming.py --full

# 使用便捷端点
python scripts/test_streaming.py --full-endpoint
```

---

### 3. `/api/v1/roadmaps/generate-full-stream` - 完整流式模式 ✅

**特点：**
- 等同于 `/generate-stream?include_tutorials=true`
- **会保存到数据库** ✓
- 自动包含教程生成阶段
- 完整的流式体验

**使用场景：**
- 与 `/generate-stream --full` 相同
- 更简洁的API调用方式

---

## 修复说明

### 问题

之前 `/generate-stream` 和 `/generate-full-stream` 端点**不会保存数据到数据库**，只是将生成结果通过流式传输返回给客户端。

### 修复内容

在 `_generate_sse_stream` 函数中添加了数据库保存逻辑：

1. **生成任务 ID** (`trace_id`)
2. **收集教程引用** - 在流式传输过程中收集所有生成的教程元数据
3. **完成后保存到数据库**：
   - 创建任务记录
   - 保存路线图元数据
   - 保存教程元数据
   - 更新任务状态为完成

### 新增参数

- `save_to_db: bool = True` - 控制是否保存到数据库（默认启用）

### 返回值变化

`done` 事件现在包含：
```json
{
  "type": "done",
  "task_id": "xxx-xxx-xxx",
  "roadmap_id": "yyy-yyy-yyy",
  "summary": {...}
}
```

---

## 对比表

| 特性 | `/generate` | `/generate-stream` | `/generate-full-stream` |
|------|------------|-------------------|------------------------|
| 执行模式 | 后台任务 | 流式SSE | 流式SSE |
| 保存数据库 | ✅ | ✅（修复后） | ✅（修复后） |
| 实时反馈 | WebSocket | SSE Stream | SSE Stream |
| 工作流 | 完整LangGraph | 直接Agent | 直接Agent |
| 结构验证 | ✅ | ❌ | ❌ |
| 人工审核 | ✅ 支持 | ❌ | ❌ |
| 教程生成 | ✅ | 可选 | ✅ 默认 |
| 返回速度 | 立即 | 流式 | 流式 |
| 适用场景 | 生产环境 | 演示/测试 | 演示/测试 |

---

## 测试脚本使用

### 测试流式端点（不含教程）
```bash
cd backend
source .venv/bin/activate
python scripts/test_streaming.py
```

### 测试流式端点（含教程）
```bash
python scripts/test_streaming.py --full
```

### 测试完整流式端点
```bash
python scripts/test_streaming.py --full-endpoint
```

### 验证数据库写入
```bash
python scripts/check_tutorial_metadata.py
```

---

## 建议

1. **生产环境** - 使用 `/generate` 端点配合 WebSocket
2. **演示展示** - 使用 `/generate-stream` 或 `/generate-full-stream`
3. **测试调试** - 两种端点都可以，流式端点更直观

现在两种端点**都会保存数据到数据库**，选择哪个取决于你的使用场景和UI需求。

