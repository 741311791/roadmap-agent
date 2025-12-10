# 临时认证系统设计方案

## 📋 需求分析

### 当前状态
- ❌ 无用户登录/注册功能
- ❌ 所有页面硬编码使用 `temp-user-001`
- ❌ 无权限控制
- ✅ 后端已有 User 和 UserProfile 表结构
- ✅ 后端接受任意 user_id，无验证

### 目标
1. ✅ **模拟真实认证场景** - 为将来的 OAuth/JWT 系统预留接口
2. ✅ **简化开发流程** - 管理员账号快速登录，无需注册
3. ✅ **保持代码整洁** - 认证逻辑集中管理，易于替换
4. ✅ **支持多用户测试** - 可切换不同测试账号

---

## 🎯 解决方案：基于 LocalStorage 的临时会话系统

### 核心设计理念

**"伪认证"模式**：
- 前端通过简单的账号选择器模拟登录
- 使用 localStorage 存储当前用户信息
- 所有 API 请求自动附加 user_id
- 后端无需修改，继续接受任意 user_id

**优势**：
1. ✅ 不需要开发真实的认证后端
2. ✅ 前端代码结构为将来的真实认证做好准备
3. ✅ 可以轻松切换测试用户
4. ✅ 开发体验好，无需反复登录

---

## 🏗️ 架构设计

### 1. 认证服务层 (`lib/services/auth-service.ts`)

```typescript
/**
 * 临时认证服务
 * 
 * 未来替换为真实 OAuth/JWT 认证时，只需修改此文件
 */

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  avatar?: string;
}

// 预定义的测试账号
const MOCK_USERS: User[] = [
  {
    id: 'admin-001',
    username: 'Admin User',
    email: 'admin@muset.ai',
    role: 'admin',
    avatar: '👨‍💼',
  },
  {
    id: 'test-user-001',
    username: 'Test User 1',
    email: 'test1@muset.ai',
    role: 'user',
    avatar: '👤',
  },
  {
    id: 'test-user-002',
    username: 'Test User 2',
    email: 'test2@muset.ai',
    role: 'user',
    avatar: '👨',
  },
  {
    id: 'test-user-003',
    username: 'Test User 3',
    email: 'test3@muset.ai',
    role: 'user',
    avatar: '👩',
  },
];

class AuthService {
  private static readonly STORAGE_KEY = 'muset_current_user';
  
  /**
   * 获取当前登录用户
   */
  getCurrentUser(): User | null {
    if (typeof window === 'undefined') return null;
    
    const stored = localStorage.getItem(AuthService.STORAGE_KEY);
    if (!stored) return null;
    
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  }
  
  /**
   * 模拟登录（选择测试账号）
   */
  login(userId: string): User | null {
    const user = MOCK_USERS.find(u => u.id === userId);
    if (!user) return null;
    
    localStorage.setItem(AuthService.STORAGE_KEY, JSON.stringify(user));
    return user;
  }
  
  /**
   * 登出
   */
  logout(): void {
    localStorage.removeItem(AuthService.STORAGE_KEY);
  }
  
  /**
   * 获取所有可用的测试账号
   */
  getAvailableUsers(): User[] {
    return MOCK_USERS;
  }
  
  /**
   * 检查是否已登录
   */
  isAuthenticated(): boolean {
    return this.getCurrentUser() !== null;
  }
  
  /**
   * 获取当前 user_id（API 调用使用）
   */
  getCurrentUserId(): string | null {
    const user = this.getCurrentUser();
    return user?.id || null;
  }
}

export const authService = new AuthService();
```

---

### 2. Zustand Auth Store (`lib/store/auth-store.ts`)

```typescript
/**
 * 认证状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, type User } from '@/lib/services/auth-service';

interface AuthState {
  // 状态
  user: User | null;
  isAuthenticated: boolean;
  
  // 操作
  login: (userId: string) => boolean;
  logout: () => void;
  refreshUser: () => void;
  
  // 工具方法
  getUserId: () => string | null;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      isAuthenticated: false,
      
      // 登录
      login: (userId: string) => {
        const user = authService.login(userId);
        if (user) {
          set({ user, isAuthenticated: true });
          return true;
        }
        return false;
      },
      
      // 登出
      logout: () => {
        authService.logout();
        set({ user: null, isAuthenticated: false });
      },
      
      // 刷新用户信息（从 localStorage 读取）
      refreshUser: () => {
        const user = authService.getCurrentUser();
        set({ 
          user, 
          isAuthenticated: user !== null 
        });
      },
      
      // 获取当前 user_id
      getUserId: () => {
        const { user } = get();
        return user?.id || null;
      },
    }),
    {
      name: 'muset-auth-storage',
      partialize: (state) => ({ 
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

---

### 3. 路由守卫中间件 (`lib/middleware/auth-guard.tsx`)

```typescript
/**
 * 认证路由守卫
 * 
 * 保护需要登录的页面
 */
'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/store/auth-store';

// 公开路由（无需登录）
const PUBLIC_ROUTES = [
  '/',
  '/login',
  '/about',
  '/pricing',
];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, refreshUser } = useAuthStore();
  
  useEffect(() => {
    // 刷新用户状态
    refreshUser();
    
    // 检查是否需要登录
    const isPublicRoute = PUBLIC_ROUTES.some(route => 
      pathname === route || pathname.startsWith(route)
    );
    
    if (!isPublicRoute && !isAuthenticated) {
      // 重定向到登录页
      router.push('/login?redirect=' + encodeURIComponent(pathname));
    }
  }, [pathname, isAuthenticated, refreshUser, router]);
  
  // 未登录且非公开路由时，显示加载状态
  if (!isAuthenticated && !PUBLIC_ROUTES.some(r => pathname.startsWith(r))) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
}
```

---

### 4. 简单登录页面 (`app/login/page.tsx`)

```typescript
/**
 * 临时登录页面
 * 
 * 选择测试账号"登录"
 */
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/lib/store/auth-store';
import { authService } from '@/lib/services/auth-service';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  
  const availableUsers = authService.getAvailableUsers();
  const redirectUrl = searchParams.get('redirect') || '/home';
  
  // 如果已登录，直接跳转
  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectUrl);
    }
  }, [isAuthenticated, router, redirectUrl]);
  
  const handleLogin = (userId: string) => {
    setIsLoading(true);
    
    const success = login(userId);
    if (success) {
      // 延迟一下，显示登录动画
      setTimeout(() => {
        router.push(redirectUrl);
      }, 500);
    } else {
      setIsLoading(false);
      alert('Login failed');
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-50 to-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="text-4xl mb-4">🎓</div>
          <CardTitle className="text-2xl font-serif">Welcome to Muset</CardTitle>
          <CardDescription>
            Select a test account to continue (Dev Mode)
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-3">
          {availableUsers.map((user) => (
            <Button
              key={user.id}
              variant="outline"
              className="w-full justify-start h-auto py-4 text-left"
              onClick={() => handleLogin(user.id)}
              disabled={isLoading}
            >
              <div className="flex items-center gap-3 w-full">
                <div className="text-3xl">{user.avatar}</div>
                <div className="flex-1">
                  <div className="font-semibold">{user.username}</div>
                  <div className="text-xs text-muted-foreground">{user.email}</div>
                  {user.role === 'admin' && (
                    <div className="text-xs text-sage-600 font-medium mt-1">
                      👑 Administrator
                    </div>
                  )}
                </div>
              </div>
            </Button>
          ))}
          
          <div className="pt-4 border-t">
            <p className="text-xs text-center text-muted-foreground">
              ℹ️ This is a temporary dev login. Real authentication will be added later.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

### 5. 更新 API Client (`lib/api/client.ts`)

```typescript
// 在请求拦截器中自动添加 user_id

import { authService } from '@/lib/services/auth-service';

// 请求拦截器
apiClient.interceptors.request.use((config) => {
  // 添加追踪 ID
  const traceId = crypto.randomUUID();
  config.headers['X-Trace-ID'] = traceId;
  
  // 🆕 自动添加 user_id header（临时方案）
  const userId = authService.getCurrentUserId();
  if (userId) {
    config.headers['X-User-ID'] = userId;
  }
  
  // 未来：添加 JWT token
  // const token = localStorage.getItem('auth_token');
  // if (token) {
  //   config.headers['Authorization'] = `Bearer ${token}`;
  // }
  
  return config;
});
```

---

### 6. 移除硬编码 USER_ID

#### Before (❌):
```typescript
// app/(app)/new/page.tsx
const USER_ID = 'temp-user-001';

const userId = USER_ID;
```

#### After (✅):
```typescript
// app/(app)/new/page.tsx
import { useAuthStore } from '@/lib/store/auth-store';

export default function NewPage() {
  const { getUserId } = useAuthStore();
  
  const handleGenerate = () => {
    const userId = getUserId();
    if (!userId) {
      alert('Please login first');
      return;
    }
    
    // ... rest of the code
  };
}
```

---

### 7. 用户信息显示组件 (`components/user-menu.tsx`)

```typescript
/**
 * 用户菜单组件
 */
'use client';

import { useAuthStore } from '@/lib/store/auth-store';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LogOut, User, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function UserMenu() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  
  if (!user) return null;
  
  const handleLogout = () => {
    logout();
    router.push('/login');
  };
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          <span className="text-xl">{user.avatar}</span>
          <span className="hidden md:inline">{user.username}</span>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">{user.username}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
            {user.role === 'admin' && (
              <p className="text-xs text-sage-600">👑 Administrator</p>
            )}
          </div>
        </DropdownMenuLabel>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={() => router.push('/profile')}>
          <User className="mr-2 h-4 w-4" />
          <span>Profile</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={() => router.push('/settings')}>
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={handleLogout} className="text-red-600">
          <LogOut className="mr-2 h-4 w-4" />
          <span>Logout</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## 📦 文件结构

```
frontend-next/
├── lib/
│   ├── services/
│   │   └── auth-service.ts        # 🆕 认证服务
│   ├── store/
│   │   └── auth-store.ts          # 🆕 认证状态管理
│   └── middleware/
│       └── auth-guard.tsx         # 🆕 路由守卫
├── app/
│   ├── login/
│   │   └── page.tsx               # 🆕 登录页面
│   ├── layout.tsx                 # 🔄 添加 AuthGuard
│   └── (app)/
│       ├── new/page.tsx           # 🔄 使用 useAuthStore
│       ├── profile/page.tsx       # 🔄 使用 useAuthStore
│       └── roadmaps/create/page.tsx # 🔄 使用 useAuthStore
└── components/
    └── user-menu.tsx              # 🆕 用户菜单
```

---

## 🔄 迁移步骤

### Phase 1: 创建认证基础设施
1. ✅ 创建 `auth-service.ts`
2. ✅ 创建 `auth-store.ts`
3. ✅ 创建 `auth-guard.tsx`
4. ✅ 创建 `login/page.tsx`

### Phase 2: 更新 API Client
1. ✅ 在 `client.ts` 中添加 user_id header

### Phase 3: 移除硬编码
1. ✅ 更新 `app/(app)/new/page.tsx`
2. ✅ 更新 `app/(app)/profile/page.tsx`
3. ✅ 更新 `app/(app)/roadmaps/create/page.tsx`
4. ✅ 更新 `app/(app)/home/page.tsx`
5. ✅ 更新 `components/chat/chat-modification.tsx`
6. ✅ 更新 `components/tutorial/tutorial-dialog.tsx`

### Phase 4: 添加 UI 组件
1. ✅ 创建 `user-menu.tsx`
2. ✅ 在导航栏中添加用户菜单
3. ✅ 在 layout.tsx 中添加 AuthGuard

---

## 🚀 使用流程

### 开发者使用
1. 访问 http://localhost:3000
2. 自动重定向到 /login
3. 选择测试账号（推荐使用 admin-001）
4. 开始开发和测试

### 切换用户
1. 点击右上角用户菜单
2. 选择 "Logout"
3. 重新选择其他测试账号

---

## ✨ 优势

### 1. **易于开发**
- ✅ 无需每次刷新重新登录
- ✅ 可以快速切换测试用户
- ✅ localStorage 自动持久化

### 2. **代码整洁**
- ✅ 认证逻辑集中在 auth-service.ts
- ✅ 使用 Zustand 统一管理状态
- ✅ 组件中无硬编码 user_id

### 3. **易于迁移**
- ✅ 将来只需替换 auth-service.ts 的实现
- ✅ 组件代码无需修改
- ✅ API client 已预留 token 位置

### 4. **符合真实场景**
- ✅ 有登录页面
- ✅ 有路由守卫
- ✅ 有用户菜单
- ✅ 支持登出操作

---

## 🔮 未来升级路径

### 升级到真实认证时：

1. **替换 auth-service.ts**:
```typescript
// 从模拟账号切换到真实 API
async login(email: string, password: string): Promise<User | null> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  
  const { user, token } = await response.json();
  localStorage.setItem('auth_token', token);
  localStorage.setItem(AuthService.STORAGE_KEY, JSON.stringify(user));
  
  return user;
}
```

2. **更新 API client**:
```typescript
// 从 X-User-ID header 切换到 Authorization Bearer token
config.headers['Authorization'] = `Bearer ${token}`;
```

3. **其他代码无需修改** ✨

---

## 📝 总结

这个临时认证方案：

✅ **满足当前需求** - 管理员可以快速登录进行开发
✅ **模拟真实场景** - 有完整的登录流程和权限控制
✅ **代码整洁** - 无硬编码，易于维护
✅ **易于升级** - 为真实认证系统预留接口
✅ **开发友好** - 无需后端修改，纯前端实现

推荐使用 **admin-001** 作为主要开发账号！

