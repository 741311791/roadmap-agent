# WebSocket 修复快速测试指南

## 🎯 目标

验证 WebSocket 连接修复是否成功，无需安装额外依赖。

## ✅ 前置条件

1. 后端服务运行在 `http://localhost:8000`
2. 前端服务运行在 `http://localhost:3000`

## 📋 测试步骤

### 步骤 1：检查服务状态

```bash
# 检查后端
curl http://localhost:8000/health

# 期望输出：
# {"status":"healthy","version":"1.0.0"}
```

如果后端未运行，启动它：

```bash
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 2：浏览器测试（推荐）

1. **打开浏览器控制台**
   - Chrome/Edge: F12 或 Cmd+Option+I (Mac)
   - 切换到 "Console" 标签

2. **访问路线图创建页面**
   ```
   http://localhost:3000/app/new
   ```

3. **填写表单并提交**
   - 学习目标：随便输入一个（如 "学习 Python"）
   - 选择难度级别
   - 点击 "Generate Roadmap" 按钮

4. **观察控制台输出**

   **✅ 修复成功的日志**：
   ```
   [WS] Connecting to: ws://localhost:8000/api/v1/ws/xxx-xxx-xxx
   [WS] Connected
   [WS] Message: connected
   [WS] Message: current_status
   [WS] Message: progress
   [WS] Current status: processing intent_analysis
   ```

   **❌ 修复前的错误日志**：
   ```
   [WS] Connecting to: ws://localhost:8000/ws/xxx-xxx-xxx
   [WS] Connection closed: 404
   [WS] Reconnecting in 2000ms...
   [WS] Connecting to: ws://localhost:8000/ws/xxx-xxx-xxx
   ... (无限重复)
   ```

5. **检查 Network 标签**
   - 切换到 "Network" 标签
   - 筛选器选择 "WS" (WebSocket)
   - 应该看到一个绿色的 WebSocket 连接
   - 点击查看消息内容

   **✅ 成功标志**：
   - Status: 101 Switching Protocols
   - 连接保持打开状态
   - Messages 标签显示收发的消息

### 步骤 3：后端日志检查

在运行后端的终端窗口中，观察日志：

**✅ 修复成功的日志**：
```
2025-12-07 12:30:00 [info] websocket_connected task_id=xxx-xxx-xxx total_connections=1
INFO:     127.0.0.1:xxxxx - "WebSocket /api/v1/ws/xxx-xxx-xxx" [accepted]
INFO:     connection open
2025-12-07 12:30:00 [info] roadmap_generation_requested user_id=...
2025-12-07 12:30:01 [info] task_status_updated status=processing step=intent_analysis
```

**❌ 修复前的错误日志**：
```
INFO:     127.0.0.1:xxxxx - "WebSocket /ws/xxx-xxx-xxx" [accepted]
2025-12-07 12:27:10 [info] websocket_connected task_id=xxx-xxx-xxx total_connections=1
INFO:     connection open
INFO:     connection closed
2025-12-07 12:27:10 [error] websocket_get_status_error error= task_id=xxx-xxx-xxx
2025-12-07 12:27:10 [error] websocket_error error='Cannot call "send" once a close message has been sent.'
... (不断重复)
```

### 步骤 4：功能验证

**完整流程测试**：

1. 提交路线图生成表单
2. 等待自动跳转到路线图详情页（约 10-15 秒）
3. 观察页面上的进度更新：
   - ✅ "Analyzing learning goals..." 
   - ✅ "Designing curriculum structure..."
   - ✅ "Generating learning content..."

**成功标志**：
- 页面自动跳转
- 实时显示生成进度
- 最终显示完整的路线图

## 🔍 常见问题排查

### 问题 1：仍然看到 `/ws/` 而不是 `/api/v1/ws/`

**原因**：前端代码未更新或浏览器缓存

**解决**：
```bash
# 清除浏览器缓存并硬刷新
# Chrome/Edge: Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows/Linux)

# 或重启前端开发服务器
cd /Users/louie/Documents/Vibecoding/roadmap-agent/frontend-next
# Ctrl+C 停止
npm run dev
```

### 问题 2：后端仍然报错 "Cannot call send"

**原因**：后端代码未更新或需要重启

**解决**：
```bash
# 重启后端服务
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend
# Ctrl+C 停止
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 问题 3：连接成功但无消息

**可能原因**：
- 任务可能已经完成
- Redis 连接问题
- 任务执行失败

**检查**：
```bash
# 查询任务状态
curl http://localhost:8000/api/v1/roadmaps/{TASK_ID}/status

# 检查 Redis 是否运行
redis-cli ping
# 期望输出: PONG
```

## 📊 测试结果记录

完成测试后，记录结果：

```markdown
## 测试结果

- [ ] 步骤 1: 服务状态 ✅/❌
- [ ] 步骤 2: 浏览器测试 ✅/❌
  - URL 是否包含 `/api/v1/ws/`? ___
  - 是否成功连接? ___
  - 是否收到消息? ___
- [ ] 步骤 3: 后端日志 ✅/❌
  - 是否有 websocket_error? ___
  - 连接是否保持打开? ___
- [ ] 步骤 4: 功能验证 ✅/❌
  - 是否自动跳转? ___
  - 是否显示进度? ___
  - 是否生成成功? ___

测试时间: ___________
测试人员: ___________
环境: 开发/测试/生产
```

## 🎉 成功标准

**修复成功的关键指标**：

1. ✅ WebSocket URL 包含 `/api/v1/ws/`
2. ✅ 连接状态显示为 "Connected"
3. ✅ 能够接收 `connected`、`progress` 等消息
4. ✅ 后端日志无 `websocket_error`
5. ✅ 无频繁的 connection open/closed
6. ✅ 路线图生成功能正常工作

## 🚀 下一步

修复验证成功后：

1. ✅ 提交代码更改
   ```bash
   git add .
   git commit -m "fix: 修复 WebSocket 连接循环错误

   - 修正前端 WebSocket URL (添加 /api/v1 前缀)
   - 改进后端异常处理 (检查连接状态)
   - 解决无限重连循环问题
   
   Fixes: #xxx"
   ```

2. ✅ 更新团队
   - 通知团队修复已完成
   - 分享测试步骤
   - 更新相关文档

3. ✅ 监控生产环境
   - 观察 WebSocket 连接成功率
   - 检查错误日志是否减少
   - 收集用户反馈

---

**创建时间**：2025-12-07  
**预计测试时间**：5-10 分钟

