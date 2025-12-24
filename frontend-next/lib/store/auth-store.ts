/**
 * 认证状态管理 Store
 * 
 * 使用 Zustand 管理用户登录状态
 * 支持持久化到 localStorage
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
  loginWithPassword: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  logoutAsync: () => Promise<void>;
  refreshUser: () => void;
  
  // 工具方法
  getUserId: () => string | null;
  isAdmin: () => boolean;
}

/**
 * 认证 Store
 * 
 * 管理用户登录状态，自动持久化到 localStorage
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      isAuthenticated: false,
      
      /**
       * 模拟登录（测试账号）- 保持向后兼容
       * 
       * @param userId - 用户 ID
       * @returns 成功返回 true
       * @deprecated 使用 loginWithPassword 替代
       */
      login: (userId: string) => {
        const user = authService.login(userId);
        if (user) {
          set({ user, isAuthenticated: true });
          console.log('[AuthStore] User logged in (mock):', user.username);
          return true;
        }
        console.error('[AuthStore] Login failed for user:', userId);
        return false;
      },
      
      /**
       * 使用邮箱和密码登录
       * 
       * @param email - 用户邮箱
       * @param password - 密码
       * @returns 成功返回 true
       */
      loginWithPassword: async (email: string, password: string) => {
        try {
          const success = await authService.loginWithPassword(email, password);
          if (success) {
            const user = authService.getCurrentUser();
            if (user) {
              set({ user, isAuthenticated: true });
              console.log('[AuthStore] User logged in:', user.email);
              return true;
            }
          }
          return false;
        } catch (error) {
          console.error('[AuthStore] Login failed:', error);
          throw error;
        }
      },
      
      /**
       * 登出（同步）
       * 
       * 清除用户状态
       */
      logout: () => {
        authService.logout();
        set({ user: null, isAuthenticated: false });
        console.log('[AuthStore] User logged out');
      },
      
      /**
       * 登出（异步，调用后端接口）
       */
      logoutAsync: async () => {
        await authService.logoutAsync();
        set({ user: null, isAuthenticated: false });
        console.log('[AuthStore] User logged out (async)');
      },
      
      /**
       * 刷新用户信息
       * 
       * 从 localStorage 重新读取用户信息
       */
      refreshUser: () => {
        const user = authService.getCurrentUser();
        const token = authService.getToken();
        const isAuthenticated = user !== null && token !== null;
        
        set({ user, isAuthenticated });
        
        if (user) {
          console.log('[AuthStore] User refreshed:', user.username);
        } else {
          console.log('[AuthStore] No user session found');
        }
      },
      
      /**
       * 获取当前用户 ID
       * 
       * @returns 用户 ID 或 null
       */
      getUserId: () => {
        const { user } = get();
        return user?.id || null;
      },
      
      /**
       * 检查是否是管理员
       * 
       * @returns true 表示是管理员
       */
      isAdmin: () => {
        const { user } = get();
        return user?.is_superuser === true;
      },
    }),
    {
      name: 'fast-learning-auth-storage',
      // 只持久化必要的状态
      partialize: (state) => ({ 
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);













