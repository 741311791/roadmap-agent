# 流式传输 API 使用指南

## 概述

流式传输 API 使用 Server-Sent Events (SSE) 技术，实时推送需求分析和框架设计的生成过程，显著提升用户体验。

## 端点信息

### POST `/api/v1/roadmaps/generate-stream`

流式生成学习路线图（仅需求分析和框架设计阶段）

**特点：**
- 实时推送 AI 生成内容
- 零感知等待时间
- 透明的生成过程
- 自动错误处理

## 请求格式

### Headers
```
Content-Type: application/json
```

### Body
```json
{
  "user_id": "string",
  "session_id": "string",
  "preferences": {
    "learning_goal": "学习目标描述",
    "available_hours_per_week": 10,
    "motivation": "学习动机",
    "current_level": "beginner|intermediate|advanced",
    "career_background": "职业背景描述",
    "content_preference": ["text", "video", "interactive", "project"]
  },
  "additional_context": "额外补充信息（可选）"
}
```

## 响应格式 (SSE)

### 数据格式
每条消息格式：
```
data: <JSON>\n\n
```

### 事件类型

#### 1. chunk - 流式文本片段
```json
{
  "type": "chunk",
  "content": "部分文本内容",
  "agent": "intent_analyzer"
}
```

**agent 可能值：**
- `intent_analyzer` - 需求分析师
- `curriculum_architect` - 课程架构师

#### 2. complete - 阶段完成
```json
{
  "type": "complete",
  "data": {
    // 结构化数据，根据 agent 不同而不同
  },
  "agent": "intent_analyzer"
}
```

**intent_analyzer 的 complete 数据：**
```json
{
  "type": "complete",
  "data": {
    "parsed_goal": "结构化的学习目标",
    "key_technologies": ["Python", "FastAPI", "..."],
    "difficulty_profile": "难度画像分析",
    "time_constraint": "时间约束分析",
    "recommended_focus": ["重点1", "重点2"]
  },
  "agent": "intent_analyzer"
}
```

**curriculum_architect 的 complete 数据：**
```json
{
  "type": "complete",
  "data": {
    "framework": {
      "roadmap_id": "uuid",
      "title": "学习路线图标题",
      "stages": [...],
      "total_estimated_hours": 120,
      "recommended_completion_weeks": 12
    },
    "design_rationale": "设计理由说明"
  },
  "agent": "curriculum_architect"
}
```

#### 3. error - 错误
```json
{
  "type": "error",
  "error": "错误信息",
  "agent": "intent_analyzer"
}
```

#### 4. done - 全部完成
```json
{
  "type": "done",
  "summary": {
    "intent_analysis": {...},
    "framework": {...},
    "design_rationale": "..."
  }
}
```

## 使用示例

### Python (httpx)

```python
import httpx
import json

async def test_streaming():
    url = "http://localhost:8000/api/v1/roadmaps/generate-stream"
    
    request_data = {
        "user_id": "user-123",
        "session_id": "session-456",
        "preferences": {
            "learning_goal": "学习 Python Web 开发",
            "available_hours_per_week": 10,
            "motivation": "职业转型",
            "current_level": "beginner",
            "career_background": "市场营销经验",
            "content_preference": ["text", "interactive"]
        }
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", url, json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    
                    if event["type"] == "chunk":
                        print(event["content"], end="", flush=True)
                    elif event["type"] == "complete":
                        print(f"\n{event['agent']} 完成")
                    elif event["type"] == "done":
                        print("\n全部完成！")
                        break
```

### JavaScript (fetch + EventSource)

```javascript
// 使用 fetch + ReadableStream
async function testStreaming() {
  const response = await fetch('http://localhost:8000/api/v1/roadmaps/generate-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: 'user-123',
      session_id: 'session-456',
      preferences: {
        learning_goal: '学习 Python Web 开发',
        available_hours_per_week: 10,
        motivation: '职业转型',
        current_level: 'beginner',
        career_background: '市场营销经验',
        content_preference: ['text', 'interactive']
      }
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.substring(6));
        
        if (event.type === 'chunk') {
          process.stdout.write(event.content);
        } else if (event.type === 'complete') {
          console.log(`\n${event.agent} 完成`);
        } else if (event.type === 'done') {
          console.log('\n全部完成！');
          return;
        }
      }
    }
  }
}
```

### curl

```bash
curl -N -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "session_id": "session-456",
    "preferences": {
      "learning_goal": "学习 Python Web 开发",
      "available_hours_per_week": 10,
      "motivation": "职业转型",
      "current_level": "beginner",
      "career_background": "市场营销经验",
      "content_preference": ["text", "interactive"]
    }
  }' \
  http://localhost:8000/api/v1/roadmaps/generate-stream
```

## 流程说明

1. **建立连接**：客户端发送 POST 请求
2. **需求分析阶段**：
   - 发送多个 `chunk` 事件（实时文本）
   - 发送 1 个 `complete` 事件（分析结果）
3. **框架设计阶段**：
   - 发送多个 `chunk` 事件（实时文本）
   - 发送 1 个 `complete` 事件（设计结果）
4. **完成**：发送 `done` 事件（最终汇总）

## 错误处理

### 客户端错误处理

```python
try:
    async with client.stream("POST", url, json=request_data) as response:
        if response.status_code != 200:
            print(f"HTTP 错误: {response.status_code}")
            return
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                
                if event["type"] == "error":
                    print(f"服务器错误: {event['error']}")
                    break
except httpx.ConnectError:
    print("无法连接到服务器")
except Exception as e:
    print(f"客户端错误: {e}")
```

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 连接超时 | 服务器未启动 | 确保后端服务运行中 |
| JSON 解析错误 | LLM 输出格式错误 | 检查 prompt 模板 |
| HTTP 500 | 服务器内部错误 | 查看服务器日志 |

## 性能特性

### 响应时间对比

| 指标 | 非流式 API | 流式 API |
|------|-----------|---------|
| 首次响应 | 30-40秒 | <1秒 |
| 用户感知 | 漫长等待 | 实时反馈 |
| 总耗时 | 30-40秒 | 30-40秒（相同） |

### 资源消耗

- **内存**：流式和非流式消耗相同
- **CPU**：流式和非流式消耗相同
- **网络**：流式略高（SSE 协议开销）

## 与非流式 API 的对比

### `/generate` (非流式)
- ✅ 简单易用
- ✅ 完整的工作流支持
- ❌ 等待时间长
- ❌ 无进度反馈

### `/generate-stream` (流式)
- ✅ 实时反馈
- ✅ 用户体验好
- ✅ 透明的生成过程
- ⚠️ 仅支持前两个阶段

## 最佳实践

1. **超时设置**：建议设置 300 秒超时
2. **错误处理**：监听 `error` 事件
3. **连接管理**：流结束后关闭连接
4. **UI 展示**：逐字显示 chunk 内容
5. **断线重连**：实现自动重连机制

## 测试

使用提供的测试脚本：

```bash
# 启动后端服务
cd backend
uvicorn app.main:app --reload

# 在另一个终端运行测试
python scripts/test_streaming.py
```

## 注意事项

1. **长连接**：SSE 需要保持长连接，注意负载均衡器配置
2. **代理配置**：Nginx 需要禁用缓冲（X-Accel-Buffering: no）
3. **浏览器兼容**：所有现代浏览器都支持 SSE
4. **CORS**：跨域请求需要正确配置 CORS 头
5. **编码**：所有文本使用 UTF-8 编码

## 故障排查

### 连接立即断开
- 检查防火墙设置
- 检查 Nginx 配置（禁用缓冲）
- 检查超时设置

### 收不到数据
- 检查请求格式
- 检查服务器日志
- 验证 LLM API 密钥

### 数据格式错误
- 检查 SSE 格式（data: + \n\n）
- 检查 JSON 编码
- 检查字符转义

## 相关文件

- 实现代码：
  - `app/agents/base.py` - 流式调用基础
  - `app/agents/intent_analyzer.py` - 需求分析流式
  - `app/agents/curriculum_architect.py` - 框架设计流式
  - `app/api/v1/roadmap.py` - SSE 端点
- 测试脚本：`scripts/test_streaming.py`
- 配置文件：`.env`

## 更新日志

### 2024-11-27
- 初始版本发布
- 支持需求分析和框架设计流式传输
- 添加完整的错误处理

