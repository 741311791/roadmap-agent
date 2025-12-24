# Quiz 和 Resources 重试功能测试计划

## 测试目标

验证 Quiz 和 Resources 的重试功能是否会出现类似 Tutorial 的"卡在加载状态"问题。

## 测试准备

### 前置条件

1. 有一个路线图，其中至少有一个概念：
   - `resources_status = 'failed'` 或 `resources_id = null`
   - `quiz_status = 'failed'` 或 `quiz_id = null`

2. 用户已登录并有有效的学习偏好设置

### 测试环境

- 浏览器：Chrome/Safari
- 打开开发者工具的 Console 和 Network 标签页
- 启动后端服务（端口 8000）
- 启动前端服务（开发模式）

## 测试用例

### 用例 1：Resources 基本重试流程 ✅

**步骤**：
1. 打开路线图沉浸式页面
2. 选择一个 `resources_status = 'failed'` 的概念
3. 切换到 "Learning Resources" 标签
4. 应该看到"重新获取资源"按钮
5. 点击按钮

**预期行为**：
```
初始状态：显示 FailedContentAlert（红色错误框 + 重试按钮）
    ↓
点击重试按钮
    ↓
按钮文本变为"重试中..."，按钮禁用
    ↓ [2-5秒]
后端生成完成
    ↓
[关键点] 页面应该显示以下状态之一：
  - 选项 A：直接显示资源列表 ✅ 最佳
  - 选项 B：短暂显示"暂未生成" → 自动切换到资源列表 ✅ 可接受
  - 选项 C：永久卡在"暂未生成"状态 ❌ BUG
```

**验证点**：
- [ ] 按钮状态正确切换
- [ ] 最终能看到资源列表（不卡住）
- [ ] 资源内容是新生成的
- [ ] 没有控制台错误

**预期 Console 输出**：
```
[RetryContentButton] 订阅 WebSocket: xxx
[RetryContentButton] 收到 current_status 事件: {...}
[RetryContentButton] 收到 concept_complete 事件: {...}
[LearningStage] Resources loading triggered, resources_id: xxx
```

**预期 Network 请求**：
1. `POST /api/v1/roadmaps/{id}/concepts/{id}/resources/retry` - 重试请求
2. `WebSocket` 连接到 `/api/v1/ws/{task_id}`
3. `GET /api/v1/roadmaps/{id}` - refetchRoadmap
4. `GET /api/v1/roadmaps/{id}/concepts/{id}/resources` - 获取资源列表

### 用例 2：Quiz 基本重试流程 ✅

**步骤**：
1. 打开路线图沉浸式页面
2. 选择一个 `quiz_status = 'failed'` 的概念
3. 切换到 "Quiz" 标签
4. 应该看到"重新生成测验"按钮
5. 点击按钮

**预期行为**：
```
初始状态：显示 FailedContentAlert
    ↓
点击重试按钮
    ↓
按钮文本变为"重试中..."
    ↓ [2-5秒]
后端生成完成
    ↓
页面应该显示测验题目列表
```

**验证点**：
- [ ] 按钮状态正确切换
- [ ] 最终能看到测验题目（不卡住）
- [ ] 测验内容是新生成的
- [ ] 没有控制台错误

### 用例 3：快速标签切换 ⚠️

**目的**：测试状态同步的健壮性

**步骤**：
1. 在 "Learning Resources" 标签页
2. 点击"重新获取资源"按钮
3. **立即**切换到 "Quiz" 标签（不等待完成）
4. 等待 5 秒
5. 切换回 "Learning Resources" 标签

**预期行为**：
```
点击 Resources 重试
    ↓
立即切换到 Quiz 标签
    ↓
Quiz 显示"暂未生成"（因为 quiz_id 还是 null）
    ↓
[后台] Resources 重试完成
    ↓
[后台] refetchRoadmap() 更新路线图数据
    ↓
切换回 Resources 标签
    ↓
✅ 应该看到资源列表（不是加载状态）
```

**验证点**：
- [ ] 不会导致错误或崩溃
- [ ] Resources 能正确加载
- [ ] Quiz 状态不受影响

### 用例 4：并发重试 ⚠️

**目的**：测试多个内容类型同时重试的情况

**步骤**：
1. 打开一个所有内容都 failed 的概念
2. 切换到 "Immersive Text" 标签
3. 点击"重新生成教程"
4. 立即切换到 "Learning Resources" 标签
5. 点击"重新获取资源"
6. 立即切换到 "Quiz" 标签
7. 点击"重新生成测验"

**预期行为**：
- 三个重试任务应该独立进行
- 不应该互相干扰
- 最终所有内容都能正确加载

**验证点**：
- [ ] 三个任务都能成功完成
- [ ] 没有请求冲突或错误
- [ ] 所有内容都能正确显示

### 用例 5：网络延迟场景 ⚠️

**目的**：测试在慢速网络下的行为

**步骤**：
1. 打开 Chrome DevTools → Network 标签
2. 选择 "Slow 3G" 网络限速
3. 执行用例 1 或用例 2

**预期行为**：
- 虽然速度慢，但最终应该能完成
- 用户能看到明确的加载状态
- 不会超时或卡死

**验证点**：
- [ ] 加载时间较长但最终成功
- [ ] 没有超时错误
- [ ] 用户体验可接受

### 用例 6：重试失败场景 ❌

**目的**：测试后端生成失败时的处理

**步骤**：
1. 临时修改后端代码，让资源生成必定失败
2. 执行重试操作

**预期行为**：
```
点击重试
    ↓
按钮显示"重试中..."
    ↓
后端返回失败
    ↓
[关键点] 应该显示：
  - 错误提示
  - 重试按钮恢复可用状态
  - 允许用户再次尝试
```

**验证点**：
- [ ] 显示明确的错误信息
- [ ] 重试按钮恢复可用
- [ ] 可以再次重试
- [ ] 没有进入永久加载状态

### 用例 7：后端超时场景 ⏱️

**目的**：测试长时间无响应时的处理

**步骤**：
1. 临时修改后端代码，让生成过程延迟 60 秒
2. 执行重试操作
3. 观察 30 秒后的行为

**预期行为**：
- WebSocket 连接应该保持
- 页面不应该假设失败
- 如果有超时，应该有明确提示

**验证点**：
- [ ] 没有假阳性的失败提示
- [ ] WebSocket 连接稳定
- [ ] 最终能收到完成通知

## 常见问题排查

### 问题：页面卡在"暂未生成"状态

**可能原因**：
1. `refetchRoadmap()` 失败或延迟
2. `useEffect` 的依赖没有正确触发
3. `concept` prop 没有更新

**排查步骤**：
```javascript
// 在 LearningStage 组件中添加调试日志
useEffect(() => {
  console.log('[Debug] Resources useEffect triggered', {
    activeFormat,
    conceptId: concept?.concept_id,
    resourcesId: concept?.resources_id,
    roadmapId,
  });
  // ... 现有逻辑
}, [activeFormat, concept?.concept_id, concept?.resources_id, roadmapId]);
```

**检查**：
- [ ] 日志中 `resourcesId` 是否从 null 变为有值？
- [ ] `useEffect` 是否在 ID 变化后触发？
- [ ] 网络请求是否发送？

### 问题：短暂显示"暂未生成"后才加载

**原因**：
这是正常的状态传播延迟，不是 bug。

**优化方案**（如果需要）：
- 在重试成功后立即显示加载状态
- 不等待 `refetchRoadmap()` 完成

### 问题：重复加载资源

**可能原因**：
- `useEffect` 被触发多次
- `concept` 对象引用频繁变化

**排查**：
```javascript
// 添加调用计数
const loadCountRef = useRef(0);
useEffect(() => {
  loadCountRef.current++;
  console.log('[Debug] Resources load count:', loadCountRef.current);
  // ...
}, [activeFormat, concept?.concept_id, concept?.resources_id, roadmapId]);
```

## 测试总结模板

```
测试日期：____
测试人员：____
环境：____

| 用例 | 状态 | 问题描述 | 严重程度 |
|------|------|----------|----------|
| 用例 1 | ✅/❌ |          | High/Medium/Low |
| 用例 2 | ✅/❌ |          | High/Medium/Low |
| 用例 3 | ✅/❌ |          | High/Medium/Low |
| 用例 4 | ✅/❌ |          | High/Medium/Low |
| 用例 5 | ✅/❌ |          | High/Medium/Low |
| 用例 6 | ✅/❌ |          | High/Medium/Low |
| 用例 7 | ✅/❌ |          | High/Medium/Low |

总体结论：
- [ ] 所有核心用例通过
- [ ] 发现 ___ 个高优先级问题
- [ ] 发现 ___ 个中优先级问题
- [ ] 发现 ___ 个低优先级问题

是否需要修复：是/否
```

## 结论

根据代码分析，**Quiz 和 Resources 的重试逻辑应该是安全的**，因为：

1. ✅ `useEffect` 依赖了动态的 ID (`resources_id`, `quiz_id`)
2. ✅ 重试成功后 ID 会从 null 变为有值
3. ✅ React 会检测到依赖变化并触发重新加载

但仍然建议执行上述测试用例，确保在实际场景中没有边界情况导致问题。

如果测试发现任何用例失败，请参考 `TUTORIAL_RELOAD_AFTER_RETRY_FIX.md` 中的修复方案。
