# CORS 跨域问题排查清单

## 问题描述
前端部署在 Vercel (`https://www.fastlearning.app`)，后端部署在 Railway (`https://roadmap-agent-production.up.railway.app`)，出现 CORS 错误。

## 已完成的修复

### ✅ 1. 后端代码修复
- **文件**: `backend/app/main.py`
- **修改**: 将硬编码的 CORS origins 改为从配置读取
- **Commit**: `eb8ecd9` - "fix: use CORS_ORIGINS from settings and remove deprecated migration doc"

```python
# 修改前
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        ...
    ],
    ...
)

# 修改后
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 从环境变量读取
    ...
)
```

## 待检查项

### 🔍 2. Railway 环境变量配置

**步骤**：
1. 登录 Railway Dashboard
2. 进入项目 `roadmap-agent-production`
3. 点击后端服务
4. 切换到 **Variables** 标签页
5. 检查是否存在 `CORS_ORIGINS` 变量

**期望值**：
```json
["https://www.fastlearning.app"]
```

**注意事项**：
- ✅ 必须使用 JSON 数组格式
- ✅ 必须使用双引号 `"`，不是单引号 `'`
- ✅ 必须包含完整 URL（包括 `https://`）
- ✅ 不要有尾部逗号
- ✅ 域名不要有尾部斜杠 `/`

**错误示例**：
```
❌ https://www.fastlearning.app              # 缺少数组括号
❌ ['https://www.fastlearning.app']          # 单引号无效
❌ ["www.fastlearning.app"]                  # 缺少协议
❌ ["https://www.fastlearning.app/"]         # 多余的尾部斜杠
❌ ["https://www.fastlearning.app", ]        # 尾部逗号
```

### 🔍 3. Railway 部署状态

检查 Railway 是否已经部署了最新的代码（commit `eb8ecd9`）：

```bash
# 在 Railway 的部署日志中查找
git rev-parse HEAD
# 应该显示: eb8ecd9 或更新的 commit hash
```

**如果不是最新代码**：
1. 在 Railway Dashboard 点击 **Deploy** 按钮
2. 或者推送一个新的 commit 触发自动部署

### 🔍 4. 验证 CORS 响应头

在浏览器 DevTools Console 中运行：

```javascript
// 测试 OPTIONS 预检请求
fetch('https://roadmap-agent-production.up.railway.app/api/v1/auth/jwt/login', {
  method: 'OPTIONS',
  headers: {
    'Origin': 'https://www.fastlearning.app',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'content-type',
  }
}).then(r => {
  console.log('Status:', r.status);
  console.log('CORS Headers:');
  console.log('  Allow-Origin:', r.headers.get('access-control-allow-origin'));
  console.log('  Allow-Methods:', r.headers.get('access-control-allow-methods'));
  console.log('  Allow-Headers:', r.headers.get('access-control-allow-headers'));
  console.log('  Allow-Credentials:', r.headers.get('access-control-allow-credentials'));
});
```

**期望输出**：
```
Status: 200
CORS Headers:
  Allow-Origin: https://www.fastlearning.app
  Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
  Allow-Headers: accept, accept-encoding, authorization, content-type, ...
  Allow-Credentials: true
```

**如果输出不正确**：
- `null` 或 `*` → 环境变量未生效
- `404` → 路由配置问题
- 其他错误 → 检查后端日志

### 🔍 5. 检查前端配置

确认 Vercel 环境变量：

1. 登录 Vercel Dashboard
2. 进入项目 → Settings → Environment Variables
3. 检查 `NEXT_PUBLIC_API_URL`

**期望值**：
```
NEXT_PUBLIC_API_URL=https://roadmap-agent-production.up.railway.app
```

**注意**：
- 不要包含 `/api/v1` 后缀（代码会自动添加）
- 不要有尾部斜杠

### 🔍 6. 检查 Railway 服务状态

访问健康检查端点：

```bash
curl https://roadmap-agent-production.up.railway.app/health
```

**期望输出**：
```json
{"status":"healthy","version":"1.0.0"}
```

### 🔍 7. 检查 Railway 部署日志

在 Railway Dashboard → Deployments → 最新部署 → Logs：

搜索以下关键字：
- `CORS_ORIGINS` - 查看环境变量是否被读取
- `application_startup` - 确认服务启动成功
- 错误信息（红色日志）

## 常见原因

### 原因 1: 环境变量未配置
**症状**: CORS 错误，OPTIONS 请求返回 `null`
**解决**: 在 Railway 添加 `CORS_ORIGINS` 环境变量

### 原因 2: 环境变量格式错误
**症状**: CORS 错误，但环境变量已配置
**解决**: 检查 JSON 格式是否正确（双引号、无尾部逗号）

### 原因 3: 代码未部署
**症状**: 环境变量已配置，但 CORS 仍然错误
**解决**: 手动触发 Railway 重新部署

### 原因 4: 多个域名不匹配
**症状**: 有时成功，有时失败
**解决**: 确保 CORS_ORIGINS 包含所有可能的前端域名

### 原因 5: Railway 缓存问题
**症状**: 所有配置都正确，但仍然失败
**解决**: 
1. 删除环境变量
2. 等待 30 秒
3. 重新添加环境变量
4. 重新部署

## 调试命令

### 测试 CORS 预检请求
```bash
curl -X OPTIONS \
  https://roadmap-agent-production.up.railway.app/api/v1/auth/jwt/login \
  -H "Origin: https://www.fastlearning.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

期望看到响应头：
```
< access-control-allow-origin: https://www.fastlearning.app
< access-control-allow-credentials: true
< access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
```

### 测试实际 POST 请求
```bash
curl -X POST \
  https://roadmap-agent-production.up.railway.app/api/v1/auth/jwt/login \
  -H "Origin: https://www.fastlearning.app" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test" \
  -v
```

### 查看当前配置（如果有访问权限）
```bash
# SSH 到 Railway 容器
railway run env | grep CORS
```

## 完整解决方案

如果以上所有检查都通过，但问题仍然存在，可能需要：

### 方案 A: 添加更多域名变体
```json
[
  "https://www.fastlearning.app",
  "https://fastlearning.app",
  "https://www-fastlearning-app.vercel.app"
]
```

### 方案 B: 临时使用通配符（仅测试）
```json
["*"]
```

⚠️ **安全警告**: 生产环境不要使用 `["*"]`，仅用于测试确认是否是域名匹配问题。

### 方案 C: 检查 FastAPI 版本兼容性
```bash
# 在 Railway 容器中检查
pip show fastapi
```

确保使用的是最新稳定版本。

## 下一步行动

请按照以上清单逐项检查，并告诉我：

1. ✅ Railway 环境变量 `CORS_ORIGINS` 的当前值
2. ✅ Railway 最新部署的 commit hash
3. ✅ 测试 CORS 预检请求的输出结果
4. ✅ Railway 部署日志中是否有错误

这些信息能帮助我快速定位问题根源。



