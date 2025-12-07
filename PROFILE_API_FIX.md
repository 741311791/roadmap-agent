# Profile API 修复报告

## 问题描述

前端 Profile 页面保存用户画像时出现 404 错误：

```
PUT http://localhost:8000/api/v1/users/admin-001/profile 404 (Not Found)
```

## 根本原因

后端在 `backend/app/api/v1/roadmap.py` 中定义了 `users_router`，包含了用户画像相关的接口：

- `GET /users/{user_id}/profile` - 获取用户画像
- `PUT /users/{user_id}/profile` - 保存/更新用户画像

但是这个路由器没有在 `backend/app/api/v1/router.py` 中注册到主路由，导致这些接口无法访问。

## 修复方案

在 `backend/app/api/v1/router.py` 中添加 `users_router` 的导入和注册：

```python
from .roadmap import users_router

# ...

# 用户相关（画像等）
router.include_router(users_router)
```

## 测试验证

### 1. 保存用户画像

```bash
curl -X PUT "http://localhost:8000/api/v1/users/admin-001/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "current_role": "senior_dev",
    "tech_stack": [{"technology": "python", "proficiency": "expert"}],
    "primary_language": "zh",
    "secondary_language": "en",
    "weekly_commitment_hours": 10,
    "learning_style": ["visual", "hands_on"],
    "ai_personalization": true
  }'
```

**响应：**
```json
{
  "user_id": "admin-001",
  "industry": null,
  "current_role": "senior_dev",
  "tech_stack": [{"technology": "python", "proficiency": "expert"}],
  "primary_language": "zh",
  "secondary_language": "en",
  "weekly_commitment_hours": 10,
  "learning_style": ["visual", "hands_on"],
  "ai_personalization": true,
  "created_at": "2025-12-07T00:03:13.712906",
  "updated_at": "2025-12-07T00:03:15.224137"
}
```

### 2. 获取用户画像

```bash
curl -X GET "http://localhost:8000/api/v1/users/admin-001/profile"
```

**响应：**
```json
{
  "user_id": "admin-001",
  "industry": null,
  "current_role": "senior_dev",
  "tech_stack": [{"technology": "python", "proficiency": "expert"}],
  "primary_language": "zh",
  "secondary_language": "en",
  "weekly_commitment_hours": 10,
  "learning_style": ["visual", "hands_on"],
  "ai_personalization": true,
  "created_at": "2025-12-07T00:03:13.712906",
  "updated_at": "2025-12-07T00:03:15.224137"
}
```

## 修复状态

✅ **已修复** - 2025-12-07

## 相关文件

- `backend/app/api/v1/router.py` - 添加 users_router 注册
- `backend/app/api/v1/roadmap.py` - users_router 定义位置
- `frontend-next/app/(app)/profile/page.tsx` - 前端 Profile 页面
- `frontend-next/lib/api/endpoints.ts` - 前端 API 调用

## 注意事项

由于使用了 `--reload` 参数启动后端服务，修改会自动生效，无需手动重启服务。

---

## 后续修复：Industry 字段保存为空

### 问题描述

虽然路由问题已修复，但发现 `industry` 字段保存到数据库时始终为空（`null`）。

### 根本原因

前端在提交用户画像时，`onSubmit` 函数中遗漏了 `industry` 字段。虽然前端页面有 industry 的状态管理和表单输入，但在调用 `saveUserProfile` API 时没有包含这个字段。

**问题代码位置：** `frontend-next/app/(app)/profile/page.tsx` 第 276-289 行

```typescript
// ❌ 缺少 industry 字段
await saveUserProfile(userId, {
  current_role: currentRole || null,
  tech_stack: techStack.filter(...).map(...),
  primary_language: primaryLanguage,
  secondary_language: secondaryLanguage || null,
  weekly_commitment_hours: weeklyHours[0],
  learning_style: learningStyles,
  ai_personalization: aiEnabled,
});
```

### 修复方案

在 `saveUserProfile` 调用中添加 `industry` 字段：

```typescript
// ✅ 添加 industry 字段
await saveUserProfile(userId, {
  industry: industry || null,  // 👈 添加此行
  current_role: currentRole || null,
  tech_stack: techStack
    .filter((item) => item.technology)
    .map((item) => ({
      technology: item.technology,
      proficiency: item.proficiency,
    })),
  primary_language: primaryLanguage,
  secondary_language: secondaryLanguage || null,
  weekly_commitment_hours: weeklyHours[0],
  learning_style: learningStyles,
  ai_personalization: aiEnabled,
});
```

### 验证测试

```bash
# 1. 保存包含 industry 的用户画像
curl -X PUT "http://localhost:8000/api/v1/users/admin-001/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "technology",
    "current_role": "senior_dev",
    "tech_stack": [{"technology": "python", "proficiency": "expert"}],
    "primary_language": "zh",
    "secondary_language": "en",
    "weekly_commitment_hours": 10,
    "learning_style": ["visual", "hands_on"],
    "ai_personalization": true
  }'

# 响应中 industry 字段正确返回
# "industry": "technology" ✅

# 2. 验证 industry 已持久化到数据库
curl -s -X GET "http://localhost:8000/api/v1/users/admin-001/profile" | grep industry
# 输出: "industry": "technology"  ✅
```

### 修复状态

✅ **已修复** - 2025-12-07

### 总结

两个问题已全部修复：

1. ✅ **路由问题**：users_router 未注册到主路由 → 已在 `router.py` 中注册
2. ✅ **Industry 字段问题**：前端提交时遗漏该字段 → 已在 `page.tsx` 中添加

现在前端 Profile 页面可以完整保存所有用户画像字段，包括 `industry`。
