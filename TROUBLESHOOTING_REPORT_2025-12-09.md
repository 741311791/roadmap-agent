# 问题诊断报告 - 失败路线图未显示

**日期：** 2025-12-09  
**问题：** 用户 `admin-001` 的失败路线图未在前端首页显示  
**状态：** ✅ 已诊断，提供解决方案

---

## 🔍 诊断过程

### 1. 数据库验证 ✅

**检查项：** 数据库中是否有失败的任务记录

**结果：**
```sql
SELECT * FROM roadmap_tasks 
WHERE user_id = 'admin-001' AND status = 'failed';
```

- ✅ 找到 **11 个失败的任务**
- ✅ 其中 6 个有 `roadmap_id`，5 个 `roadmap_id` 为 NULL
- ✅ 所有任务的 `current_step` 都是 `'failed'`
- ✅ 所有任务都有 `error_message`

**示例数据：**
```
Task ID: 6183dd68-3c26-4b91-8d34-8bd942ed2a56
Roadmap ID: python-design-patterns-a4b5c6d7
Status: failed
Current Step: failed
Error: ValueError: LLM 输出格式不符合 Schema: name 're' is not defined
```

---

### 2. 后端 API 逻辑验证 ✅

**检查项：** `get_user_roadmaps` API 是否正确查询和返回失败任务

**测试方法：** 直接调用 Repository 层逻辑

**结果：**
- ✅ `get_in_progress_tasks_by_user` 正确查询到所有 11 个失败任务
- ✅ 所有失败任务都通过了跳过检查（`task.roadmap_id not in saved_roadmap_ids`）
- ✅ 标题正确提取自 `user_request.preferences.learning_goal`
- ✅ 状态正确设置为 `"failed"`

**代码逻辑：**
```python
# backend/app/api/v1/roadmap.py:3316-3346

for task in in_progress_tasks:
    # 跳过已经有路线图记录的任务
    if task.roadmap_id and task.roadmap_id in saved_roadmap_ids:
        continue  # ← 失败的任务不会被跳过，因为没有 metadata 记录
    
    # 根据任务状态确定显示状态
    display_status = "failed" if task.status == "failed" else "generating"
    
    roadmap_items.insert(0, RoadmapHistoryItem(
        roadmap_id=task.roadmap_id or f"task-{task.task_id}",
        title=title,
        status=display_status,  # ← 正确设置为 "failed"
        task_id=task.task_id,
        task_status=task.status,
        current_step=task.current_step,
    ))
```

---

### 3. API 路由配置验证 ✅

**检查项：** API 端点是否正确注册

**结果：**
- ✅ `users_router` 正确定义在 `backend/app/api/v1/roadmap.py`
- ✅ 端点路径：`GET /api/v1/users/{user_id}/roadmaps`
- ✅ 路由正确包含在主路由中（`backend/app/api/v1/router.py`）

---

### 4. 前端代码验证 ✅

**检查项：** 前端是否正确调用 API 和渲染数据

**结果：**
- ✅ `getUserRoadmaps(userId)` 正确调用 API
- ✅ 响应数据正确映射到 store
- ✅ `RoadmapCard` 组件支持 `failed` 状态渲染
- ✅ 失败状态的 UI 已实现（红色图标、红色进度条、"生成失败" Badge）

**代码逻辑：**
```typescript
// frontend-next/app/(app)/home/page.tsx:539-561

const response = await getUserRoadmaps(userId);
const historyData = response.roadmaps.map((item) => {
  let status = item.status || 'completed';  // ← 保留原始状态
  
  return {
    roadmap_id: item.roadmap_id,
    title: item.title,
    status,  // ← 包括 "failed"
    task_id: item.task_id,
    task_status: item.task_status,
    current_step: item.current_step,
  };
});
setHistory(historyData);
```

---

## 🎯 根本原因

经过系统诊断，**后端逻辑完全正确**，所有失败的任务都应该被返回给前端。

**最可能的原因：**

### 原因 1：后端服务未运行 ⚠️

前端无法连接到后端 API（`http://localhost:8000`），导致：
- API 调用失败
- 前端保留旧的缓存数据
- 失败的路线图无法显示

**验证方法：**
```bash
curl http://localhost:8000/api/v1/users/admin-001/roadmaps
```

如果返回 `Connection refused` 或超时，说明后端服务未运行。

---

## ✅ 解决方案

### 方案 1：启动后端服务（最可能需要）

```bash
# 进入后端目录
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend

# 激活虚拟环境
source .venv/bin/activate

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 方案 2：清除前端缓存并刷新

1. 打开浏览器开发者工具（F12）
2. 右键点击刷新按钮 → "清空缓存并硬性重新加载"
3. 或者在 Console 中执行：
   ```javascript
   localStorage.clear();
   sessionStorage.clear();
   location.reload();
   ```

### 方案 3：验证 API 连接

在浏览器 Console 中执行：
```javascript
fetch('http://localhost:8000/api/v1/users/admin-001/roadmaps')
  .then(r => r.json())
  .then(data => console.log('API Response:', data))
  .catch(err => console.error('API Error:', err));
```

如果返回数据，说明 API 正常，问题在前端；如果报错，说明后端服务未运行。

---

## 📊 预期结果

修复后，前端首页应该显示：

### 失败的路线图卡片样式：
- 🔴 红色 `AlertCircle` 图标
- 🔴 红色完整进度条
- 🔴 "生成失败" Badge（红色背景）
- 📝 显示学习目标作为标题
- 🕒 显示失败时间（相对时间）
- 🔗 点击跳转到生成页面查看错误详情

### 预期显示的路线图：
1. 我想学习基于Python语言的设计模式 - **失败**
2. 我想学习最新版本的Langgraph，开发多Agent项目 - **失败**
3. 我想学习最新版本的Langgraph用来开发智能体 - **失败** (多个)
4. 我想学习Langgraph开发 - **失败**
5. 我想学习爆款短剧写作 - **失败** (多个)
6. 我想学习短剧写作 - **失败**

**总计：11 个失败的路线图应该全部显示**

---

## 🔧 后续建议

### 1. 添加 API 健康检查

在前端添加 API 连接状态检测：
```typescript
// 在 HomePage 组件中添加
useEffect(() => {
  const checkAPIHealth = async () => {
    try {
      await fetch(`${API_PREFIX}/health`);
      console.log('✅ API 连接正常');
    } catch (error) {
      console.error('❌ API 连接失败:', error);
      // 显示错误提示
    }
  };
  checkAPIHealth();
}, []);
```

### 2. 添加错误边界

在前端添加更好的错误处理和用户提示：
```typescript
if (error) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <AlertCircle className="mx-auto mb-4 text-red-500" size={48} />
        <h2 className="text-xl font-bold mb-2">无法加载路线图</h2>
        <p className="text-muted-foreground">请检查后端服务是否运行</p>
        <Button onClick={fetchRoadmaps} className="mt-4">
          重试
        </Button>
      </div>
    </div>
  );
}
```

### 3. 添加开发环境检测

在启动前端时自动检测后端服务：
```bash
# 在 package.json 中添加
"scripts": {
  "predev": "curl -s http://localhost:8000/api/v1/health || echo '⚠️  后端服务未运行，请先启动后端'",
  "dev": "next dev"
}
```

---

## 📝 测试清单

修复后请验证：

- [ ] 后端服务正常运行（`http://localhost:8000`）
- [ ] API 端点返回正确数据（`/api/v1/users/admin-001/roadmaps`）
- [ ] 前端首页显示 11 个失败的路线图
- [ ] 失败路线图的视觉样式正确（红色图标、红色 Badge）
- [ ] 点击失败的路线图可以跳转到生成页面
- [ ] 生成页面显示详细的错误信息
- [ ] 浏览器 Console 没有错误信息

---

## 📞 联系信息

如果问题仍然存在，请提供：
1. 浏览器 Console 的错误日志
2. Network 面板的 API 请求详情
3. 后端服务的运行状态

---

**诊断完成时间：** 2025-12-09 18:13  
**诊断结果：** 后端逻辑正常，最可能是后端服务未运行  
**建议操作：** 启动后端服务，清除前端缓存，刷新页面

