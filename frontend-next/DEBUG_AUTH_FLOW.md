# 认证流程诊断指南

## 问题描述
用户点击 Sign In 按钮后没有看到选择账号的页面，直接跳转到 home 页面。

## 可能的原因

### 1. LocalStorage 中已有用户信息
如果浏览器的 localStorage 中已经保存了用户登录信息，系统会认为你已经登录，直接跳过登录页面。

**检查方法**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 "Application" 标签
3. 左侧找到 "Local Storage" → `http://localhost:3000`
4. 查看是否有以下 key：
   - `muset-auth-storage` (Zustand 持久化的认证状态)
   - `muset_current_user` (AuthService 保存的用户信息)

**解决方法**:
```javascript
// 在浏览器控制台运行以下命令清除登录状态
localStorage.clear();
// 然后刷新页面
location.reload();
```

### 2. 路由守卫逻辑问题
`AuthGuard` 组件可能在检查认证状态时出现了逻辑错误。

**检查要点**:
- `isAuthenticated` 的判断逻辑
- `refreshUser()` 是否正确读取 localStorage
- 公开路由配置是否正确

### 3. 登录页面的自动跳转逻辑
登录页面本身有一个 useEffect，如果检测到已登录会自动跳转。

```typescript
// app/login/page.tsx
useEffect(() => {
  if (isAuthenticated) {
    console.log('[Login] Already authenticated, redirecting to:', redirectUrl);
    router.push(redirectUrl);
  }
}, [isAuthenticated, router, redirectUrl]);
```

## 诊断步骤

### Step 1: 检查当前登录状态
在浏览器控制台运行：
```javascript
// 检查 localStorage
console.log('Auth Storage:', localStorage.getItem('muset-auth-storage'));
console.log('Current User:', localStorage.getItem('muset_current_user'));
```

### Step 2: 清除所有登录状态
```javascript
localStorage.clear();
sessionStorage.clear();
location.reload();
```

### Step 3: 重新访问应用
1. 打开 http://localhost:3000
2. 应该会自动跳转到 `/login`
3. 看到 4 个测试账号选择按钮
4. 点击任意账号完成登录

### Step 4: 查看控制台日志
登录流程应该输出以下日志：
```
[AuthGuard] Unauthorized access, redirecting to login
[Login] Login successful, redirecting to: /home
[AuthStore] User logged in: Admin User
```

## 测试场景

### 场景 1: 首次访问（未登录）
**预期行为**:
1. 访问 http://localhost:3000
2. AuthGuard 检测到未登录
3. 自动跳转到 `/login`
4. 显示 4 个测试账号
5. 点击账号登录
6. 跳转到 `/home`

### 场景 2: 已登录用户访问
**预期行为**:
1. 访问 http://localhost:3000
2. AuthGuard 检测到已登录
3. 直接显示 `/home` 页面（不跳转到登录页）

### 场景 3: 已登录用户访问 /login
**预期行为**:
1. 访问 http://localhost:3000/login
2. 登录页面检测到已登录
3. 自动跳转到 `/home`（或 redirect 参数指定的页面）

## 修复建议

如果问题持续存在，可能需要：

1. **改进路由守卫的检查逻辑**
   - 确保 `refreshUser()` 正确执行
   - 添加更多调试日志

2. **改进登录页面的状态检查**
   - 延迟自动跳转，给用户看到页面的机会
   - 添加 "You're already logged in" 提示

3. **添加登出功能的快捷方式**
   - 在登录页面添加"清除登录状态"按钮
   - 方便开发和测试

## 快速解决方案

如果你想快速看到登录页面，运行以下命令：

**在浏览器控制台**:
```javascript
// 清除登录状态
localStorage.clear();
// 跳转到登录页
window.location.href = '/login';
```

**或者在终端**:
```bash
# 打开浏览器的隐私模式 (Incognito/Private)
# 访问 http://localhost:3000
# 隐私模式不会保存 localStorage，每次都是全新状态
```







