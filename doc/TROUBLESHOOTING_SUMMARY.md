# 问题排查总结 - 路线图生成失败与 404 错误

## 🎯 问题描述

用户报告的问题：
1. 前端生成路线图后，轮询任务状态一直返回 404
2. 数据库中任务状态是 `failed`
3. 错误信息：`OperationalError: consuming input failed: could not receive data from server: Operation timed out`

## 🔍 诊断过程

### Step 1: 验证 API 接口

**测试结果**: ✅ API 接口正常工作

```bash
curl "http://localhost:8000/api/v1/roadmaps/007b3301-4e95-49fa-ab80-fcd8fe022654/status"
```

返回正确的失败状态，**不是 404**。

**结论**: API 路由配置正确，接口可以正常查询任务状态。

### Step 2: 检查数据库中的失败任务

**查询结果**: 找到 3 个失败的任务

```sql
SELECT task_id, status, error_message FROM roadmap_tasks WHERE status = 'failed'
```

**失败模式**:
- 任务 1: 超时失败（18 秒后）
- 任务 2: 超时失败（19 秒后）  
- 任务 3: 配置错误（已修复）

**共同特征**: 数据库连接超时

### Step 3: 分析数据库连接配置

**发现的问题**:

| 问题 | 影响 | 严重性 |
|------|------|--------|
| 连接池大小偏小 (pool_size=10) | 高并发时连接耗尽 | 🔴 高 |
| 缺少连接回收配置 | 长时间连接过期 | 🔴 高 |
| 缺少超时配置 | 无限等待，资源泄漏 | 🔴 高 |
| 缺少命令超时 | 慢查询阻塞连接 | 🟡 中 |

### Step 4: 检查表结构

**重要发现**:
- `roadmap_tasks` 表使用 `task_id` 字段（主键）
- `execution_logs` 表使用 `trace_id` 字段
- 两者的值相同，但字段名不同

**影响**: 代码中需要注意字段名的一致性

## 🔧 修复措施

### 修复 1: 优化数据库连接池配置 ✅

**文件**: `backend/app/db/session.py`

**修改内容**:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,  # ⬆️ 10 → 20
    max_overflow=40,  # ⬆️ 20 → 40
    pool_pre_ping=True,
    pool_recycle=3600,  # ✨ 新增：1小时回收连接
    pool_timeout=30,  # ✨ 新增：获取连接超时
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",
        },
        "command_timeout": 60,  # ✨ 新增：命令超时 60秒
        "timeout": 30,  # ✨ 新增：连接超时 30秒
    },
)
```

**效果**:
- 🚀 支持更多并发连接 (最多 60 个)
- ⏱️ 及时释放超时连接
- ♻️ 定期回收过期连接
- 🛡️ 防止慢查询阻塞

### 修复 2: 前端 404 问题诊断 🔍

**当前状态**: API 接口验证正常，404 可能由以下原因导致：

1. **前端使用了错误的 task_id**
   - 检查生成任务后是否正确保存 task_id
   - 检查 localStorage/state 中的 task_id

2. **前端 API 路径错误**
   - 正确路径: `/api/v1/roadmaps/{task_id}/status`
   - 检查 `lib/api/endpoints.ts` 中的 `getRoadmapStatus` 函数

3. **CORS 或网络问题**
   - 检查浏览器 Network 标签
   - 确认实际发送的 URL

**建议**: 需要用户提供：
- 浏览器控制台的完整错误日志
- Network 标签中的完整请求 URL
- 前端生成时保存的 task_id

## 📊 测试计划

### 1. 验证数据库连接池修复

```bash
# 启动新的生成任务
curl -X POST "http://localhost:8000/api/v1/roadmaps/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "user_query": "学习 Python Web 开发",
    "preferences": {
      "weekly_commitment_hours": 10,
      "learning_style": ["visual", "hands_on"],
      "primary_language": "zh"
    }
  }'

# 获取返回的 task_id 并查询状态
# 观察是否还会出现超时错误
```

### 2. 监控连接池使用情况

建议添加健康检查端点：

```python
# backend/app/main.py
@app.get("/health/db")
async def db_health():
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
    }
```

### 3. 前端测试

1. 打开浏览器开发者工具
2. 生成新的路线图
3. 观察控制台日志和 Network 标签
4. 记录：
   - 生成时返回的 task_id
   - 轮询时使用的完整 URL
   - 任何 404 错误的详细信息

## 📈 预期改进

| 指标 | 修复前 | 修复后（预期） |
|------|--------|----------------|
| 数据库超时错误 | 高频 | 低频/消除 |
| 并发处理能力 | 30 连接 | 60 连接 |
| 连接稳定性 | 差（无回收） | 好（1小时回收） |
| 错误恢复时间 | 无限制 | 30-60秒 |

## ⚠️ 注意事项

1. **自动重启**: 后端使用 `--reload` 模式，修改会自动生效
2. **测试建议**: 重新尝试生成路线图，观察是否还会超时
3. **监控**: 建议添加连接池监控，及时发现问题
4. **进一步优化**: 如果问题持续，需要：
   - 检查 PostgreSQL 服务器性能
   - 优化慢查询
   - 检查网络稳定性

## 📝 相关文档

- [DATABASE_TIMEOUT_FIX.md](./DATABASE_TIMEOUT_FIX.md) - 详细的修复说明
- [PROFILE_API_FIX.md](./PROFILE_API_FIX.md) - Profile API 修复记录

## 🎯 下一步行动

1. ✅ 数据库连接池配置已优化
2. ⏳ 等待后端自动重启完成（3-5秒）
3. 🧪 建议用户重新测试生成路线图功能
4. 🔍 如果前端仍然显示 404，需要提供：
   - 完整的浏览器控制台日志
   - Network 标签中的请求详情
   - 生成任务返回的 task_id

## 联系方式

如有问题，请提供以下信息：
- 浏览器控制台完整日志
- 网络请求的完整 URL
- task_id 值
- 错误发生的具体步骤

---

**修复时间**: 2025-12-07 11:28  
**修复状态**: ✅ 数据库连接池已优化，等待测试验证  
**影响范围**: 所有涉及数据库操作的功能
