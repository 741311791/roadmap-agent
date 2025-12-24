# Featured Roadmaps 功能设置指南

## 📋 功能概述

Featured Roadmaps 功能允许在首页展示精选的学习路线图，帮助用户发现优质内容。

### 架构设计

```
Frontend (Home/Explore) 
    ↓
GET /api/v1/featured/roadmaps
    ↓
查询 users 表 (email = admin@example.com)
    ↓
获取该用户的 roadmap_metadata 数据
    ↓
返回精选路线图列表
```

---

## 🚀 快速设置

### 1. 创建 Featured User

使用以下任一方式创建 `admin@example.com` 用户：

#### 方式 A: 使用 Python 脚本（推荐）

```bash
cd backend
uv run python scripts/create_admin.py
```

按提示输入：
- Email: `admin@example.com`
- Username: `Admin` (或任意名称)
- Password: 设置一个安全密码

#### 方式 B: 使用 API 端点

```bash
curl -X POST "http://localhost:8000/api/v1/admin/create-superuser" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-secure-password"
  }'
```

**注意**: 此端点仅在系统中没有超级管理员时可用。

### 2. 为 Featured User 创建路线图

使用 `admin@example.com` 账号登录前端，创建一些高质量的学习路线图。

**建议**:
- 创建 5-10 个涵盖不同技术栈的路线图
- 确保路线图内容完整、结构清晰
- 选择热门技术主题（如 Python、React、Machine Learning 等）

### 3. 验证功能

访问首页 `/home`，应该能看到 "Featured Roadmaps" 模块展示精选内容。

---

## 🔧 API 端点详情

### GET `/api/v1/featured/roadmaps`

获取精选路线图列表

**Query Parameters:**
- `limit` (int, 可选): 返回数量限制，默认 50
- `offset` (int, 可选): 分页偏移，默认 0

**Response:**

```json
{
  "roadmaps": [
    {
      "roadmap_id": "roadmap-001",
      "title": "Python Web Development",
      "created_at": "2024-01-01T00:00:00",
      "total_concepts": 28,
      "completed_concepts": 0,
      "topic": "python web",
      "status": "completed"
    }
  ],
  "total": 1,
  "featured_user_id": "user-001",
  "featured_user_email": "admin@example.com"
}
```

**Error Responses:**

- `404 Not Found`: Featured user 不存在
  ```json
  {
    "detail": "Featured user with email admin@example.com not found. Please create this user first using the admin API."
  }
  ```

---

## 📱 前端集成

### Home 页面

```typescript
import { getFeaturedRoadmaps } from '@/lib/api/endpoints';

// 获取精选路线图（最多8个）
const response = await getFeaturedRoadmaps(8, 0);
```

### Explore 页面

```typescript
import { getFeaturedRoadmaps } from '@/lib/api/endpoints';

// 获取所有精选路线图
const response = await getFeaturedRoadmaps(100, 0);
```

---

## 🔐 安全考虑

### 当前实现

- Featured user 邮箱硬编码为 `admin@example.com`
- 仅返回已完成且未删除的路线图
- 不暴露用户敏感信息

### 未来改进建议

1. **配置化**: 将 Featured user 邮箱移至环境变量
   ```python
   FEATURED_USER_EMAIL = os.getenv("FEATURED_USER_EMAIL", "admin@example.com")
   ```

2. **多用户支持**: 支持多个 Featured users
   ```python
   FEATURED_USER_EMAILS = ["admin@example.com", "curator@example.com"]
   ```

3. **标记系统**: 在 `roadmap_metadata` 表添加 `is_featured` 字段
   ```sql
   ALTER TABLE roadmap_metadata ADD COLUMN is_featured BOOLEAN DEFAULT FALSE;
   ```

4. **审核机制**: 添加管理员审核流程，手动标记精选内容

---

## 🐛 故障排查

### 问题 1: Featured Roadmaps 不显示

**可能原因**:
- Featured user 不存在
- Featured user 没有创建路线图
- 路线图状态不是 "completed"

**解决方案**:
```bash
# 检查 Featured user 是否存在
curl http://localhost:8000/api/v1/featured/roadmaps

# 查看返回的错误信息
# 如果是 404，按照"快速设置"步骤创建用户
```

### 问题 2: API 返回空列表

**可能原因**:
- Featured user 的路线图都被软删除了
- 路线图状态不是 "completed"

**解决方案**:
1. 登录 `admin@example.com` 账号
2. 检查回收站，恢复被删除的路线图
3. 或创建新的路线图

### 问题 3: 前端报错 "Failed to fetch featured roadmaps"

**可能原因**:
- 后端服务未启动
- CORS 配置问题
- 网络连接问题

**解决方案**:
```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查 CORS 配置 (backend/app/main.py)
# 确保前端域名在 allow_origins 列表中
```

---

## 📊 数据库查询

### 查看 Featured User 信息

```sql
SELECT id, email, username, created_at 
FROM users 
WHERE email = 'admin@example.com';
```

### 查看 Featured User 的路线图

```sql
SELECT 
    rm.roadmap_id,
    rm.title,
    rm.created_at,
    rm.deleted_at,
    (SELECT COUNT(*) 
     FROM jsonb_array_elements(rm.framework_data->'stages') AS stage,
          jsonb_array_elements(stage->'modules') AS module,
          jsonb_array_elements(module->'concepts') AS concept
    ) AS total_concepts
FROM roadmap_metadata rm
JOIN users u ON rm.user_id = u.id
WHERE u.email = 'admin@example.com'
  AND rm.deleted_at IS NULL
ORDER BY rm.created_at DESC;
```

---

## 📝 维护建议

### 定期更新

1. **每月审核**: 检查 Featured 路线图的质量和时效性
2. **内容更新**: 根据技术趋势更新精选内容
3. **性能监控**: 监控 API 响应时间，必要时添加缓存

### 内容质量标准

精选路线图应满足：
- ✅ 结构完整（包含 Stages → Modules → Concepts）
- ✅ 内容丰富（每个 Concept 有教程、资源、测验）
- ✅ 主题热门（覆盖主流技术栈）
- ✅ 难度适中（适合大多数学习者）

---

## 🔄 版本历史

- **v1.0** (2025-01-XX): 初始实现，基于 `admin@example.com` 用户
- **Future**: 计划支持多用户、标记系统、审核机制

---

## 📞 支持

如有问题，请查看：
- [API 文档](./backend/app/api/v1/endpoints/README.md)
- [数据库设计](./backend/docs/DATABASE_OPTIMIZATION_ANALYSIS.md)
- [前端 API 客户端](./frontend-next/lib/api/endpoints.ts)

