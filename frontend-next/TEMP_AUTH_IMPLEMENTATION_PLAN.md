# 临时认证系统 - 实施计划

## 📊 分析总结

### 当前问题
1. ❌ **7 个文件硬编码 `temp-user-001`**
2. ❌ **无登录页面和用户界面**
3. ❌ **无法测试多用户场景**
4. ❌ **代码耦合度高，难以升级**

### 推荐方案
**基于 LocalStorage 的临时会话系统**

---

## 🎯 核心特性

### 1. **简单的"伪登录"**
- 选择预设的测试账号
- 信息存储在 localStorage
- 页面刷新后自动保持登录状态

### 2. **多测试账号支持**
```typescript
admin-001     👨‍💼 Admin User      (管理员)
test-user-001 👤 Test User 1     (测试用户)
test-user-002 👨 Test User 2     (测试用户)
test-user-003 👩 Test User 3     (测试用户)
```

### 3. **完整的认证流程**
```
访问受保护页面 → 检查登录状态 → 未登录重定向到 /login
     ↓
选择测试账号 → 保存到 localStorage → 跳转回原页面
     ↓
API 请求自动附加 user_id → 后端处理
```

### 4. **易于升级**
所有认证逻辑集中在 `auth-service.ts`，将来只需替换这一个文件即可。

---

## 📁 需要创建的文件

### 核心服务 (3 个文件)

1. **lib/services/auth-service.ts** (180 行)
   - 用户登录/登出逻辑
   - LocalStorage 管理
   - 预设测试账号

2. **lib/store/auth-store.ts** (80 行)
   - Zustand 状态管理
   - 持久化配置
   - 用户状态同步

3. **lib/middleware/auth-guard.tsx** (60 行)
   - 路由保护
   - 自动重定向
   - 加载状态处理

### UI 组件 (2 个文件)

4. **app/login/page.tsx** (120 行)
   - 登录页面
   - 账号选择器
   - 重定向逻辑

5. **components/user-menu.tsx** (80 行)
   - 用户头像/名称显示
   - 下拉菜单
   - 登出按钮

---

## 🔧 需要修改的文件

### API 层 (1 个文件)

6. **lib/api/client.ts**
   ```typescript
   // 添加 user_id header
   + const userId = authService.getCurrentUserId();
   + if (userId) {
   +   config.headers['X-User-ID'] = userId;
   + }
   ```

### 页面组件 (7 个文件) - 移除硬编码

7. **app/(app)/new/page.tsx**
8. **app/(app)/profile/page.tsx**
9. **app/(app)/roadmaps/create/page.tsx**
10. **app/(app)/home/page.tsx**
11. **components/chat/chat-modification.tsx**
12. **components/tutorial/tutorial-dialog.tsx**
13. **components/roadmap/retry-failed-button.tsx**

**修改模式**：
```typescript
// Before ❌
const USER_ID = 'temp-user-001';
const userId = USER_ID;

// After ✅
import { useAuthStore } from '@/lib/store/auth-store';
const { getUserId } = useAuthStore();
const userId = getUserId();
```

### 布局文件 (1 个文件)

14. **app/layout.tsx 或 app/(app)/layout.tsx**
    ```typescript
    import { AuthGuard } from '@/lib/middleware/auth-guard';
    
    export default function Layout({ children }) {
      return (
        <AuthGuard>
          {children}
        </AuthGuard>
      );
    }
    ```

---

## 🚀 实施顺序

### Step 1: 创建认证基础 (30 分钟)
```bash
✅ 创建 lib/services/auth-service.ts
✅ 创建 lib/store/auth-store.ts
✅ 创建 lib/middleware/auth-guard.tsx
```

### Step 2: 创建登录 UI (20 分钟)
```bash
✅ 创建 app/login/page.tsx
✅ 创建 components/user-menu.tsx
```

### Step 3: 更新 API Client (10 分钟)
```bash
✅ 修改 lib/api/client.ts
```

### Step 4: 移除硬编码 (40 分钟)
```bash
✅ 修改 app/(app)/new/page.tsx
✅ 修改 app/(app)/profile/page.tsx
✅ 修改 app/(app)/roadmaps/create/page.tsx
✅ 修改 app/(app)/home/page.tsx
✅ 修改 components/chat/chat-modification.tsx
✅ 修改 components/tutorial/tutorial-dialog.tsx
✅ 修改 components/roadmap/retry-failed-button.tsx
```

### Step 5: 集成到布局 (10 分钟)
```bash
✅ 修改 app/(app)/layout.tsx
✅ 在导航栏添加 UserMenu
```

### Step 6: 测试验证 (20 分钟)
```bash
✅ 测试登录流程
✅ 测试路由守卫
✅ 测试多账号切换
✅ 测试 API 请求
```

**总计时间**: 约 2-2.5 小时

---

## ✅ 验收标准

### 功能测试
- [ ] 访问 http://localhost:3000 自动跳转到 /login
- [ ] 可以选择任意测试账号登录
- [ ] 登录后正确显示用户信息
- [ ] 刷新页面保持登录状态
- [ ] 点击登出后清除登录状态
- [ ] 切换账号后 user_id 正确更新

### 代码质量
- [ ] 无硬编码的 user_id
- [ ] 所有受保护页面被 AuthGuard 包裹
- [ ] API 请求自动包含 user_id
- [ ] TypeScript 无类型错误

### 用户体验
- [ ] 登录页面美观友好
- [ ] 用户菜单功能完整
- [ ] 加载状态显示正确
- [ ] 重定向逻辑流畅

---

## 📋 检查清单

### 创建新文件
- [ ] lib/services/auth-service.ts
- [ ] lib/store/auth-store.ts
- [ ] lib/middleware/auth-guard.tsx
- [ ] app/login/page.tsx
- [ ] components/user-menu.tsx

### 修改现有文件
- [ ] lib/api/client.ts (添加 user_id header)
- [ ] app/(app)/new/page.tsx (移除硬编码)
- [ ] app/(app)/profile/page.tsx (移除硬编码)
- [ ] app/(app)/roadmaps/create/page.tsx (移除硬编码)
- [ ] app/(app)/home/page.tsx (移除硬编码)
- [ ] components/chat/chat-modification.tsx (移除硬编码)
- [ ] components/tutorial/tutorial-dialog.tsx (移除硬编码)
- [ ] components/roadmap/retry-failed-button.tsx (移除硬编码)
- [ ] app/(app)/layout.tsx (添加 AuthGuard 和 UserMenu)

### 测试验证
- [ ] 登录流程测试
- [ ] 路由守卫测试
- [ ] 多账号切换测试
- [ ] API 调用测试
- [ ] 持久化测试（刷新页面）

---

## 🎓 开发指南

### 如何使用

#### 1. 开发时
```bash
npm run dev
# 自动跳转到 /login
# 选择 admin-001 登录
# 开始开发
```

#### 2. 切换测试用户
```typescript
// 右上角点击用户菜单 → Logout
// 重新选择其他测试账号
```

#### 3. 在组件中获取 user_id
```typescript
import { useAuthStore } from '@/lib/store/auth-store';

export default function MyComponent() {
  const { getUserId } = useAuthStore();
  
  const handleAction = () => {
    const userId = getUserId();
    if (!userId) {
      alert('Please login first');
      return;
    }
    
    // 使用 userId
    await someApi(userId, ...);
  };
}
```

---

## 🔮 未来升级

当需要真实认证时：

### 1. 替换 auth-service.ts
```typescript
// 从 mock 账号改为真实 API
async login(email: string, password: string) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  
  const { user, token } = await response.json();
  localStorage.setItem('auth_token', token);
  // ...
}
```

### 2. 更新 API client
```typescript
// 从 X-User-ID 改为 Authorization Bearer
const token = localStorage.getItem('auth_token');
if (token) {
  config.headers['Authorization'] = `Bearer ${token}`;
}
```

### 3. 更新登录页面
```typescript
// 从账号选择器改为表单输入
<input type="email" />
<input type="password" />
<button>Login</button>
```

**其他代码完全不需要修改！** ✨

---

## 💡 最佳实践

### DO ✅
- 使用 `getUserId()` 获取当前用户 ID
- 在受保护的页面使用 AuthGuard
- 在导航栏显示用户信息
- 提供清晰的登出功能

### DON'T ❌
- 不要硬编码 user_id
- 不要绕过 AuthGuard
- 不要在多处重复认证逻辑
- 不要将认证逻辑耦合到业务组件

---

## 🎯 总结

这个临时认证方案提供了：

✅ **完整的认证体验** - 登录、登出、用户菜单
✅ **灵活的测试能力** - 多个测试账号
✅ **清晰的代码结构** - 易于理解和维护
✅ **平滑的升级路径** - 一个文件替换即可

**推荐立即开始实施！** 🚀

---

## 📞 需要帮助？

如果在实施过程中遇到问题：

1. 查看 `TEMP_AUTH_DESIGN.md` 详细设计文档
2. 参考现有的 Zustand store 实现
3. 检查浏览器控制台的错误信息

**准备好了吗？让我帮你实施这个方案！** ✨

