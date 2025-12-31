# Railway 环境变量配置指南

## 🚨 紧急修复：数据库连接池配置

**问题：** Railway部署后出现 `QueuePool limit of size 40 overflow 20 reached` 错误

**原因：** 多进程架构导致连接需求超出数据库容量（18进程 × 60连接 = 1,080 > 200）

**解决：** 在所有服务中添加以下环境变量

---

## 必须添加的环境变量

### 1. roadmap-agent-api

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=3
```

### 2. celery-logs

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=3
```

### 3. celery-content

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=3
```

### 4. celery-workflow

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=3
```

---

## Railway 操作步骤

### 方式一：通过 UI 界面（推荐）

1. 打开 Railway 项目
2. 对每个服务进行以下操作：
   - 点击服务卡片
   - 切换到 **Variables** 标签
   - 点击 **New Variable**
   - 添加 `DB_POOL_SIZE` = `5`
   - 添加 `DB_MAX_OVERFLOW` = `3`
3. Railway 会自动触发重新部署

### 方式二：通过 Railway CLI

```bash
# 安装 Railway CLI（如果还没有）
npm i -g @railway/cli

# 登录
railway login

# 链接到项目
railway link

# 为每个服务添加环境变量
railway variables --service roadmap-agent-api set DB_POOL_SIZE=5 DB_MAX_OVERFLOW=3
railway variables --service celery-logs set DB_POOL_SIZE=5 DB_MAX_OVERFLOW=3
railway variables --service celery-content set DB_POOL_SIZE=5 DB_MAX_OVERFLOW=3
railway variables --service celery-workflow set DB_POOL_SIZE=5 DB_MAX_OVERFLOW=3
```

---

## 验证修复

### 1. 检查部署状态

确保所有服务重新部署成功：
- ✅ roadmap-agent-api
- ✅ celery-logs
- ✅ celery-content
- ✅ celery-workflow

### 2. 创建测试任务

在前端创建一个新的路线图生成任务，观察是否能够：
1. 成功进入内容生成阶段
2. 不再出现连接池错误
3. 正常完成所有步骤

### 3. 查看日志

```bash
# 通过 Railway CLI
railway logs --service celery-content

# 或在 Railway UI 中查看 Logs 标签

# 应该看到正常的日志，而不是：
# ❌ QueuePool limit of size 40 overflow 20 reached
```

### 4. 健康检查

```bash
# 访问健康检查端点
curl https://your-api.railway.app/health

# 检查数据库连接池状态
{
  "database": {
    "pool_size": 5,          # ← 应该是 5
    "max_overflow": 3,       # ← 应该是 3
    "checked_out": 2,        # ← 应该 < 8
    "overflow": 0            # ← 应该 = 0 或很小
  }
}
```

---

## 连接数计算

### 修复前（错误配置）

```
每进程连接数 = 40 + 20 = 60
总进程数 = 4 + 4 + 6 + 4 = 18

总连接需求 = 18 × 60 = 1,080
Railway容量 ≈ 200

结果：1,080 > 200  →  连接池耗尽 ❌
```

### 修复后（正确配置）

```
每进程连接数 = 5 + 3 = 8
总进程数 = 18

总连接需求 = 18 × 8 = 144
Railway容量 ≈ 200

结果：144 < 200 （余量28%） →  正常 ✅
```

---

## 性能影响

**Q: 降低连接池会影响性能吗？**

**A: 不会。** 内容生成任务的瓶颈在 LLM API（20秒），而非数据库（<300ms）。

**时间占比分析：**
- 🐌 LLM API调用：~20秒（98%）
- ⚡ 数据库操作：~300ms（2%）

即使连接池从60降到8，对整体性能的影响可忽略不计。

---

## 故障排查

### 问题1：仍然出现连接池错误

**可能原因：**
- 环境变量未生效（需要重新部署）
- 旧的Worker进程还在运行

**解决方法：**
```bash
# 1. 验证环境变量
railway variables --service celery-content

# 2. 强制重新部署
railway up --service celery-content
```

### 问题2：内容生成变慢

**可能原因：**
- 不太可能是连接池问题（见上面的性能分析）
- 更可能是 LLM API 速率限制

**排查方法：**
```bash
# 查看日志中的LLM调用时间
railway logs --service celery-content | grep "llm_call_duration"
```

### 问题3：连接池不足警告

如果监控显示 `overflow > 0` 持续出现，可以适当增加：

```bash
# 谨慎增加，每次加1-2
DB_POOL_SIZE=7
DB_MAX_OVERFLOW=4
```

---

## 相关文档

- 详细分析：`backend/docs/20251231_Railway连接池耗尽修复.md`
- 部署指南：`backend/RAILWAY_DEPLOYMENT.md`
- 事件循环修复：`backend/docs/20251231_数据库引擎事件循环感知修复.md`

---

## 联系支持

如果按照本指南操作后仍有问题，请提供以下信息：

1. Railway服务日志截图
2. `/health` 端点返回的JSON
3. PostgreSQL连接数限制（Railway Dashboard → PostgreSQL → Metrics）

