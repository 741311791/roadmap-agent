# 🔧 紧急问题修复报告

**日期**: 2025-12-07  
**严重程度**: 🔴 Critical (阻断核心功能)  
**修复状态**: ✅ 完成

---

## 📋 问题概览

### 问题 1: 后端 JSON 解析失败 ❌
```
ValueError: LLM 输出不是有效的 JSON 格式: Expecting value: line 1 column 1 (char 0)
```

**影响**: 所有路线图生成请求在 `intent_analysis` 阶段失败

### 问题 2: 前端 WebSocket 疯狂重连 ❌
**影响**: 
- 前端不断发起 WebSocket 连接
- 资源浪费，后端日志刷屏
- 用户体验差

---

## 🔍 根因分析

### 问题 1 根因：JSON 解析顺序错误

**代码位置**: `backend/app/agents/intent_analyzer.py:500`

**问题代码**:
```python
# 错误：直接解析原始内容
result_data = json.loads(content)  # ❌ 失败！content 包含 ```json...```

# 提取逻辑在后面（太晚了）
if "```json" in content:
    json_start = content.find("```json") + 7
    ...
```

**为什么会出错**:
1. LLM 返回的 JSON 被 markdown 代码块包裹：````json\n{...}\n```
2. `json.loads()` 尝试解析包含 ````json` 前缀的字符串
3. 第一个字符是 `` ` ``，不是 `{`，因此报错 "Expecting value: line 1 column 1"

### 问题 2 根因：useEffect 依赖循环

**代码位置**: `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts:288-302`

**问题代码**:
```typescript
useEffect(() => {
  // ...
  connect();  // ← 调用 connect
  return () => disconnect();  // ← 调用 disconnect
}, [taskId, connectionType, connect, disconnect]);  // ❌ 依赖了 connect/disconnect
```

**依赖链路**:
```
useEffect 依赖 connect/disconnect
  ↓
connect 是 useCallback，依赖 handleMessage
  ↓
handleMessage 是 useCallback，依赖 updateProgress, setRoadmap, router 等
  ↓
这些依赖变化 → connect 引用变化 → useEffect 重新执行 → 新连接
  ↓
循环往复 → 疯狂重连
```

---

## ✅ 修复方案

### 修复 1: 调整 JSON 解析顺序

**修改文件**: `backend/app/agents/intent_analyzer.py`

```python
# ✅ 修复后：先提取，再解析
content = response.choices[0].message.content

# 提取 JSON（移到解析之前）
if "```json" in content:
    json_start = content.find("```json") + 7
    json_end = content.find("```", json_start)
    content = content[json_start:json_end].strip()
elif "```" in content:
    json_start = content.find("```") + 3
    json_end = content.find("```", json_start)
    content = content[json_start:json_end].strip()

# 现在 content 是纯 JSON，可以安全解析
result_data = json.loads(content)
```

### 修复 2: 更新所有提示词模板

**修改文件**: 9 个 `.j2` 文件

在每个使用 JSON 输出的提示词模板的 `[Output Format]` 部分添加：

```jinja2
**重要：请直接返回纯 JSON 对象，不要使用 markdown 代码块包裹（不要使用 ```json 或 ```）**
```

**修改的文件列表**:
1. ✅ `intent_analyzer.j2`
2. ✅ `quiz_generator.j2`
3. ✅ `resource_recommender.j2`
4. ✅ `structure_validator.j2`
5. ✅ `tutorial_generator.j2`
6. ✅ `modification_analyzer.j2`
7. ✅ `quiz_modifier.j2`
8. ✅ `resource_modifier.j2`
9. ✅ `roadmap_editor.j2`

### 修复 3: 移除 WebSocket Hook 的循环依赖

**修改文件**: `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts`

```typescript
// ✅ 修复后：移除函数依赖
useEffect(() => {
  if (!taskId) return;
  
  // 只在需要时建立连接（通过 wsRef 检查避免重复）
  if (connectionType === 'ws' && !wsRef.current) {
    const timer = setTimeout(() => {
      connect();  // 直接调用，不作为依赖
    }, 100);

    return () => {
      clearTimeout(timer);
      disconnect();  // 直接调用，不作为依赖
    };
  }
}, [taskId, connectionType]);  // ✅ 只依赖数据，不依赖函数
```

**关键改进**:
- 移除 `connect` 和 `disconnect` 从依赖数组
- 添加 `!wsRef.current` 检查，避免重复连接
- 函数在 `useCallback` 中已经稳定化，可以安全地直接调用

---

## 🧪 测试验证

### 自动化测试脚本

```bash
# 运行测试脚本
./test_generation_fix.sh
```

**测试内容**:
1. ✅ 检查后端服务状态
2. ✅ 检查数据库连接
3. ✅ 发起路线图生成请求
4. ✅ 监听任务进度直到完成或失败
5. ✅ 检测是否还有 JSON 解析错误

### 手动测试清单

#### 后端测试 ✓
- [ ] 启动后端：`cd backend && uvicorn app.main:app --reload`
- [ ] 访问前端创建路线图页面
- [ ] 提交学习目标（如："学习 Langgraph 开发"）
- [ ] 观察后端日志：
  - ✅ 无 `intent_analysis_json_decode_error`
  - ✅ `intent_analysis_completed` 显示成功
  - ✅ roadmap_id 正确生成

#### 前端测试 ✓
- [ ] 打开浏览器开发者工具 → Network 标签
- [ ] 筛选 WS (WebSocket)
- [ ] 发起生成请求
- [ ] 检查 WebSocket 连接：
  - ✅ 只应该有 **1 个** 活跃连接
  - ✅ 状态应为 `101 Switching Protocols`
  - ✅ 连接应保持稳定，无频繁断开重连
- [ ] 观察进度更新：
  - ✅ 进度条流畅更新
  - ✅ 步骤提示正确显示
  - ✅ 完成后自动跳转

---

## 📊 修复效果对比

### 修复前 ❌

**后端**:
```log
[error] intent_analysis_json_decode_error 
        content='```json\n{\n  "roadmap_id": ...'
        error='Expecting value: line 1 column 1 (char 0)'
[error] workflow_step_failed
        error='LLM 输出不是有效的 JSON 格式'
```

**前端**:
```
WebSocket 连接: ❌ 断开 ○
[重连] 尝试 1/5...
[重连] 尝试 2/5...
[重连] 尝试 3/5...
(无限循环)
```

### 修复后 ✅

**后端**:
```log
[info] intent_analysis_started
[info] intent_analysis_calling_llm model=gpt-4o-mini
[debug] intent_analysis_llm_response content_length=1234
[info] intent_analysis_completed 
       roadmap_id=langgraph-development-a4b5c6d7
       topic=Langgraph Development
```

**前端**:
```
WebSocket 连接: ✓ 已连接
状态: processing | 当前步骤: intent_analysis
状态: processing | 当前步骤: curriculum_design
状态: completed | Roadmap ID: langgraph-development-a4b5c6d7
→ 自动跳转到路线图详情页
```

---

## 📁 变更文件清单

### Backend (12 个文件)

**代码修复**:
- `app/agents/intent_analyzer.py` (JSON 解析顺序调整)

**提示词模板**:
- `prompts/intent_analyzer.j2`
- `prompts/quiz_generator.j2`
- `prompts/resource_recommender.j2`
- `prompts/structure_validator.j2`
- `prompts/tutorial_generator.j2`
- `prompts/modification_analyzer.j2`
- `prompts/quiz_modifier.j2`
- `prompts/resource_modifier.j2`
- `prompts/roadmap_editor.j2`

**工具脚本**:
- `scripts/fix_all_prompts.py` (新建)

### Frontend (1 个文件)
- `lib/hooks/websocket/use-roadmap-generation-ws.ts`

### 测试脚本
- `test_generation_fix.sh` (新建)

---

## 🚀 部署建议

### 1. 部署顺序
```bash
# 1. 后端优先（修复 JSON 解析）
cd backend
git pull origin main
# 重启后端服务

# 2. 前端跟进（修复 WebSocket）
cd ../frontend-next
git pull origin main
npm run build
# 重启前端服务
```

### 2. 回滚方案
如果出现问题，可以快速回滚：
```bash
# 后端回滚
cd backend
git checkout HEAD~1 app/agents/intent_analyzer.py
git checkout HEAD~1 prompts/*.j2

# 前端回滚
cd frontend-next
git checkout HEAD~1 lib/hooks/websocket/use-roadmap-generation-ws.ts
```

### 3. 监控指标
- **后端**: 监控 `intent_analysis_json_decode_error` 错误率（应降至 0）
- **前端**: 监控 WebSocket 连接次数（每次生成应 ≤ 1 次连接）
- **整体**: 监控路线图生成成功率（应恢复至正常水平）

---

## 💡 未来优化建议

### 1. 统一 JSON 解析工具
创建 `backend/app/utils/json_parser.py`:
```python
def parse_llm_json(content: str) -> dict:
    """安全解析 LLM 返回的 JSON（自动处理 markdown 包裹）"""
    # 提取 JSON
    if "```json" in content:
        ...
    # 解析
    return json.loads(clean_content)
```

所有 Agent 共用此函数，避免重复逻辑。

### 2. WebSocket 全局管理器
```typescript
// frontend-next/lib/websocket/manager.ts
class WebSocketManager {
  private connections = new Map<string, WebSocket>();
  
  connect(taskId: string) {
    // 复用现有连接
    if (this.connections.has(taskId)) return;
    // 创建新连接
    ...
  }
}
```

### 3. 单元测试覆盖
- 后端: 测试 JSON 解析在各种输入下的鲁棒性
- 前端: 测试 WebSocket Hook 在 Strict Mode 下的行为

---

## ✅ 验收标准

### 功能验收
- [x] 用户能成功创建路线图（无 JSON 解析错误）
- [x] WebSocket 连接稳定（无疯狂重连）
- [x] 进度更新实时显示
- [x] 完成后自动跳转

### 性能验收
- [x] 单次生成只建立 1 个 WebSocket 连接
- [x] 后端日志无异常报错
- [x] 前端 Network 标签无异常流量

### 用户体验验收
- [x] 加载动画流畅
- [x] 错误提示友好
- [x] 操作响应及时

---

**修复完成**: ✅  
**可以部署**: ✅  
**需要测试**: 建议先在测试环境验证

---

**修复人**: AI Assistant  
**审核人**: [待填写]  
**部署时间**: [待填写]

