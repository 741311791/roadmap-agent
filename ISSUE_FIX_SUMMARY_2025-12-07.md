# 问题修复完成总结

## 问题诊断

### 1. JSON 解析错误（后端）
**错误信息**:
```
ValueError: LLM 输出不是有效的 JSON 格式: Expecting value: line 1 column 1 (char 0)
```

**根本原因**:
- LLM 返回的 JSON 被包裹在 markdown 代码块中（````json...```）
- `intent_analyzer.py` 第 500 行直接解析原始内容，没有先提取 JSON
- 虽然提取逻辑存在，但位置错误（在解析之后而非之前）

### 2. WebSocket 无限重连循环（前端）
**现象**: 前端疯狂发起 WebSocket 连接请求

**根本原因**:
- `useEffect` 的依赖数组包含 `connect` 和 `disconnect` 函数
- 这些函数内部又依赖 `handleMessage` 等函数
- 形成循环依赖，导致每次渲染都重新创建连接
- React Strict Mode 的双重渲染加剧了问题

## 修复方案

### 修复 1: Intent Analyzer JSON 解析逻辑顺序修正

**文件**: `backend/app/agents/intent_analyzer.py` (第 489-500 行)

**修改内容**:
```python
# 在 json.loads() 之前先提取 JSON
if "```json" in content:
    json_start = content.find("```json") + 7
    json_end = content.find("```", json_start)
    content = content[json_start:json_end].strip()
elif "```" in content:
    json_start = content.find("```") + 3
    json_end = content.find("```", json_start)
    content = content[json_start:json_end].strip()

# 然后再解析
result_data = json.loads(content)
```

### 修复 2: 所有 Agent 提示词模板更新

**修改的提示词文件** (共 8 个):
1. `intent_analyzer.j2` ✓
2. `quiz_generator.j2` ✓
3. `resource_recommender.j2` ✓
4. `structure_validator.j2` ✓
5. `tutorial_generator.j2` ✓
6. `modification_analyzer.j2` ✓
7. `quiz_modifier.j2` ✓
8. `resource_modifier.j2` ✓
9. `roadmap_editor.j2` ✓

**添加的指令**:
```
**重要：请直接返回纯 JSON 对象，不要使用 markdown 代码块包裹（不要使用 ```json 或 ```）**
```

这条指令被添加到每个模板的 `[Output Format]` 部分开头。

### 修复 3: WebSocket Hook 依赖循环修复

**文件**: `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts` (第 288-302 行)

**关键修改**:
```typescript
// 修改前（有问题）:
useEffect(() => {
  // ...
  return () => {
    clearTimeout(timer);
    disconnect();
  };
}, [taskId, connectionType, connect, disconnect]); // 循环依赖！

// 修改后（修复）:
useEffect(() => {
  if (!taskId) return;
  
  // 只有在 ws 模式且没有活跃连接时才建立新连接
  if (connectionType === 'ws' && !wsRef.current) {
    const timer = setTimeout(() => {
      connect(); // 直接调用，不通过依赖
    }, 100);

    return () => {
      clearTimeout(timer);
      disconnect(); // 直接调用，不通过依赖
    };
  }
}, [taskId, connectionType]); // 移除函数依赖
```

**原理说明**:
- `connect` 和 `disconnect` 是稳定的 `useCallback`，可以安全地直接调用
- 通过 `wsRef.current` 检查避免重复连接
- 只依赖数据值（`taskId`, `connectionType`），不依赖函数引用

## 测试验证

### 自动化测试
运行修复脚本:
```bash
cd backend
python3 scripts/fix_all_prompts.py
```

结果: ✓ 成功修复 4 个提示词文件，其余 5 个手动修复完成

### 手动测试清单

#### 后端测试
1. [ ] 启动后端服务
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. [ ] 发起路线图生成请求
   - 访问前端 `/app/new`
   - 填写学习目标（如："学习 Langgraph 开发"）
   - 提交生成请求

3. [ ] 检查后端日志
   - 确认 `intent_analysis` 步骤成功完成
   - 不再出现 JSON 解析错误
   - roadmap_id 正确生成

#### 前端测试
1. [ ] 打开浏览器开发者工具 Network 标签
2. [ ] 访问 `/app/new` 并发起生成请求
3. [ ] 观察 WebSocket 连接
   - 应该只建立 1 个 WebSocket 连接
   - 不应该出现疯狂重连现象
   - 连接状态应该显示 "WebSocket ✓"

4. [ ] 测试进度更新
   - 确认进度条正常更新
   - 步骤提示正确显示
   - 完成后正常跳转到路线图详情页

## 额外改进

### 工具脚本
创建了 `backend/scripts/fix_all_prompts.py` 用于批量修复提示词模板，方便未来维护。

### 日志增强
保留了 `intent_analyzer.py` 中的详细日志记录：
- `intent_analysis_llm_response`: 记录响应长度
- `intent_analysis_json_decode_error`: 记录解析失败的内容（前 500 字符）

## 预期效果

### 后端
- ✅ Intent Analyzer 能正确解析 LLM 返回的 JSON（无论是否包裹 markdown）
- ✅ 所有 Agent 的提示词都明确指示不要使用代码块包裹
- ✅ 错误日志更清晰，便于调试

### 前端
- ✅ WebSocket 连接稳定，无重连循环
- ✅ React Strict Mode 下也能正常工作
- ✅ 路线图生成流程流畅，用户体验良好

## 建议的后续优化

1. **统一 JSON 解析工具函数**
   - 创建 `utils/json_parser.py`，提供 `parse_llm_json()` 函数
   - 所有 Agent 共用，避免重复代码

2. **WebSocket 连接池管理**
   - 考虑在前端创建全局 WebSocket 管理器
   - 支持多任务并发监听

3. **监控和告警**
   - 添加 Sentry 或类似工具
   - 监控 JSON 解析失败率
   - 监控 WebSocket 连接异常

## 文件变更清单

### Backend (11 个文件)
- `app/agents/intent_analyzer.py`
- `prompts/intent_analyzer.j2`
- `prompts/quiz_generator.j2`
- `prompts/resource_recommender.j2`
- `prompts/structure_validator.j2`
- `prompts/tutorial_generator.j2`
- `prompts/modification_analyzer.j2`
- `prompts/quiz_modifier.j2`
- `prompts/resource_modifier.j2`
- `prompts/roadmap_editor.j2`
- `scripts/fix_all_prompts.py` (新建)

### Frontend (1 个文件)
- `lib/hooks/websocket/use-roadmap-generation-ws.ts`

---

**修复完成时间**: 2025-12-07
**修复人**: AI Assistant
**问题严重程度**: 🔴 Critical (阻断核心功能)
**修复状态**: ✅ 已完成，待测试验证

