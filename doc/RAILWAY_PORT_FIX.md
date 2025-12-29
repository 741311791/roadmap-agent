# Railway 端口配置问题修复指南

## 问题诊断

### 症状
- ✅ 应用启动成功：`INFO: Uvicorn running on http://0.0.0.0:8080`
- ❌ Railway 报错：`"connection refused"` (重试 3 次)
- ❌ HTTP 502 错误：`"Application failed to respond"`

### 根本原因
Railway 的负载均衡器无法连接到应用容器。虽然应用监听在端口 8080，但 Railway 的网络配置可能存在问题。

## 解决方案

### ✅ 方案 1：添加 railway.toml 配置（推荐）

我已经创建了 `backend/railway.toml` 文件，配置了：
- 明确的健康检查路径：`/health`
- 健康检查超时：300 秒
- 自动重启策略
- 明确的启动命令

**下一步**：
1. 提交并推送这个文件到 GitHub
2. Railway 会自动重新部署
3. 检查是否解决问题

### ✅ 方案 2：在 Railway Dashboard 配置端口

如果 `railway.toml` 不生效，手动配置：

1. **登录 Railway Dashboard**
2. **进入项目** → 选择后端服务
3. **Settings** → 找到 **Networking** 部分
4. **确认以下设置**：
   - ✅ Generate Domain 已启用
   - ✅ 端口检测为自动或手动设置为 `$PORT`

### ✅ 方案 3：检查必需的环境变量

在 Railway **Variables** 中确保以下变量已配置：

#### 🔴 关键环境变量（必须配置）

```bash
# ==================== CORS 配置（修复跨域问题）====================
CORS_ORIGINS=["https://www.fastlearning.app"]

# ==================== 数据库配置（Railway 自动注入）====================
# 这些变量 Railway PostgreSQL 插件会自动提供，无需手动配置
# POSTGRES_HOST=xxx
# POSTGRES_PORT=5432
# POSTGRES_USER=xxx
# POSTGRES_PASSWORD=xxx
# POSTGRES_DB=xxx

# ==================== LLM API Keys（必须配置）====================
# A1: Intent Analyzer (需求分析师)
ANALYZER_API_KEY=sk-proj-xxx...  # OpenAI API Key

# A2: Curriculum Architect (课程架构师)
ARCHITECT_API_KEY=sk-ant-xxx...  # Anthropic Claude API Key

# A3: Structure Validator (结构审查员)
VALIDATOR_API_KEY=sk-proj-xxx...  # OpenAI API Key

# A2E: Roadmap Editor (路线图编辑师)
EDITOR_API_KEY=sk-ant-xxx...  # Anthropic Claude API Key

# A4: Tutorial Generator (教程生成器)
GENERATOR_API_KEY=sk-ant-xxx...  # Anthropic Claude API Key

# A5: Resource Recommender (资源推荐师)
RECOMMENDER_API_KEY=sk-proj-xxx...  # OpenAI API Key

# A6: Quiz Generator (测验生成器)
QUIZ_API_KEY=sk-proj-xxx...  # OpenAI API Key

# ==================== Redis 配置（Railway 自动注入）====================
# 如果使用 Railway Redis 插件，这些变量会自动提供
# REDIS_HOST=xxx
# REDIS_PORT=6379
# REDIS_PASSWORD=xxx

# ==================== MinIO/S3 配置（必须配置）====================
S3_ENDPOINT_URL=http://47.111.115.130:9000  # 你的 MinIO 地址
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin123
S3_BUCKET_NAME=roadmap-content

# ==================== JWT 认证（必须配置）====================
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-$(openssl rand -hex 32)

# ==================== 邮件服务（可选）====================
# 如果需要发送邀请邮件
RESEND_API_KEY=re_xxx...
RESEND_FROM_EMAIL=noreply@fastlearning.app
FRONTEND_URL=https://www.fastlearning.app

# ==================== 管理员账户（可选）====================
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password
ADMIN_USERNAME=admin

# ==================== Web Search（可选）====================
# 多个 Tavily API Keys（逗号分隔或 JSON 数组）
TAVILY_API_KEY_LIST=["tvly-xxx","tvly-yyy","tvly-zzz"]
# 或单个 Key
# TAVILY_API_KEY=tvly-xxx...

# 是否启用 DuckDuckGo 备用搜索
USE_DUCKDUCKGO_FALLBACK=true

# ==================== 工作流控制（可选）====================
# 跳过结构验证（加快生成速度，但可能影响质量）
SKIP_STRUCTURE_VALIDATION=false

# 跳过人工审核（自动批准所有路线图）
SKIP_HUMAN_REVIEW=false

# 跳过教程生成（仅生成路线图框架）
SKIP_TUTORIAL_GENERATION=false

# 跳过资源推荐
SKIP_RESOURCE_RECOMMENDATION=false

# 跳过测验生成
SKIP_QUIZ_GENERATION=false

# ==================== 任务恢复配置（可选）====================
ENABLE_TASK_RECOVERY=true
TASK_RECOVERY_MAX_AGE_HOURS=24
TASK_RECOVERY_MAX_CONCURRENT=3

# ==================== 端口配置（可选）====================
# Railway 通常会自动设置，如果有问题可以明确指定
# PORT=8000
```

## 快速修复步骤

### 步骤 1：提交 railway.toml
```bash
cd /Users/louie/Documents/Vibecoding/roadmap-agent
git add backend/railway.toml doc/RAILWAY_PORT_FIX.md
git commit -m "fix: add Railway config with healthcheck and restart policy"
git push origin main
```

### 步骤 2：在 Railway 添加 CORS_ORIGINS
1. 登录 Railway Dashboard
2. 进入后端服务 → Variables
3. 点击 **New Variable**
4. 添加：
   ```
   Name: CORS_ORIGINS
   Value: ["https://www.fastlearning.app"]
   ```
5. 点击 **Add**

### 步骤 3：等待自动部署完成
- Railway 会检测到新的 commit
- 自动触发重新部署
- 等待 3-5 分钟

### 步骤 4：验证修复
```bash
# 运行诊断脚本
./scripts/test_cors.sh
```

期望输出：
```
✅ 后端服务运行正常
✅ CORS Allow-Origin 配置正确
✅ CORS Allow-Credentials 配置正确
✅ POST 方法已允许
```

## 如果问题仍未解决

### 诊断步骤

#### 1. 检查 Railway 部署日志
在 Railway Dashboard → Deployments → 最新部署 → Build Logs & Deploy Logs

查找：
- ❌ 端口绑定失败
- ❌ 健康检查超时
- ❌ 容器重启循环

#### 2. 检查健康检查
```bash
curl https://roadmap-agent-production.up.railway.app/health
```

期望返回：
```json
{"status":"healthy","version":"1.0.0"}
```

#### 3. 手动触发重新部署
在 Railway Dashboard 点击 **Deploy** → **Redeploy**

#### 4. 临时禁用健康检查（调试用）
在 `railway.toml` 中注释掉 healthcheck 行：
```toml
# healthcheckPath = "/health"
# healthcheckTimeout = 300
```

推送后重新部署。

## 常见问题

### Q1: Railway 一直显示 "Starting"
**原因**：健康检查超时或容器无法启动
**解决**：
1. 检查所有必需的环境变量是否已配置
2. 检查数据库和 Redis 连接是否正常
3. 增加 `healthcheckTimeout` 到 600

### Q2: 部署成功但仍然 502
**原因**：端口映射问题
**解决**：
1. 在 Railway Variables 中明确设置 `PORT=8000`
2. 删除 railway.toml 中的 startCommand（使用 Dockerfile CMD）
3. 重新部署

### Q3: 环境变量未生效
**原因**：Railway 缓存或格式错误
**解决**：
1. 删除变量，等待 30 秒，重新添加
2. 检查 JSON 格式（双引号，无尾部逗号）
3. 手动触发重新部署

## 监控和日志

### 实时日志查看
在 Railway Dashboard → 服务 → Logs 查看实时日志

### 关键日志标记
- ✅ `application_startup` - 应用启动成功
- ✅ `Uvicorn running on` - 服务监听端口
- ❌ `Error` - 错误信息
- ⚠️  `Warning` - 警告信息

## 联系支持

如果以上所有方法都无法解决问题，可能是 Railway 平台的问题。

可以：
1. 在 Railway Discord 社区寻求帮助
2. 提交 Railway Support Ticket
3. 检查 Railway Status Page（status.railway.app）

## 总结

修复清单：
- [x] ✅ 创建 railway.toml 配置文件
- [ ] 🔲 提交并推送到 GitHub
- [ ] 🔲 在 Railway 添加 CORS_ORIGINS 环境变量
- [ ] 🔲 等待自动部署完成
- [ ] 🔲 运行 ./scripts/test_cors.sh 验证
- [ ] 🔲 在浏览器测试前端登录功能

完成以上步骤后，CORS 问题应该彻底解决！














