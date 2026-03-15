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
  hasHydrated: boolean;
  lastRefreshAt: number | null;
  
  // 操作
  login: (userId: string) => boolean;
  loginWithPassword: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  logoutAsync: () => Promise<void>;
  /**
   * 从后端 API 重新拉取最新用户信息并同步到 store 和 localStorage。
   * 替代旧版只读 localStorage 的实现，确保刷新后数据始终与后端一致。
   */
  refreshUser: (options?: { force?: boolean }) => Promise<void>;
  /**
   * 用 API 返回的最新用户数据直接更新 store 和 localStorage。
   * 保存头像/用户名后立即调用，无需额外网络请求。
   */
  updateUser: (user: User) => void;
  setHasHydrated: (hasHydrated: boolean) => void;
  
  // 工具方法
  getUserId: () => string | null;
  isAdmin: () => boolean;
}

const AUTH_REFRESH_TTL_MS = 5 * 60 * 1000;

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
      hasHydrated: false,
      lastRefreshAt: null,
      
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
              set({
                user,
                isAuthenticated: true,
                lastRefreshAt: Date.now(),
              });
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
        set({
          user: null,
          isAuthenticated: false,
          lastRefreshAt: null,
        });
        console.log('[AuthStore] User logged out');
      },
      
      /**
       * 登出（异步，调用后端接口）
       */
      logoutAsync: async () => {
        await authService.logoutAsync();
        set({
          user: null,
          isAuthenticated: false,
          lastRefreshAt: null,
        });
        console.log('[AuthStore] User logged out (async)');
      },
      
      /**
       * 从后端 API 重新拉取最新用户信息并同步到 store 和 localStorage。
       *
       * 修复点：旧实现只读 localStorage 旧数据，刷新页面后头像/用户名恢复原样。
       * 新实现调用 GET /users/me，将最新数据同时写入 localStorage 和 Zustand store。
       */
      refreshUser: async (options) => {
        const token = authService.getToken();
        if (!token) {
          set({
            user: null,
            isAuthenticated: false,
            lastRefreshAt: null,
          });
          return;
        }

        const { lastRefreshAt } = get();
        const shouldUseCache =
          !options?.force &&
          typeof lastRefreshAt === 'number' &&
          Date.now() - lastRefreshAt < AUTH_REFRESH_TTL_MS;

        if (shouldUseCache) {
          return;
        }

        const user = await authService.fetchCurrentUser();
        if (user) {
          authService.saveUser(user);
          set({
            user,
            isAuthenticated: true,
            lastRefreshAt: Date.now(),
          });
          console.log('[AuthStore] User refreshed from API:', user.username);
        } else {
          set({
            user: null,
            isAuthenticated: false,
            lastRefreshAt: null,
          });
          console.log('[AuthStore] Failed to refresh user from API, auth state cleared');
        }
      },

      /**
       * 用 API 返回的最新用户数据直接更新 store 和 localStorage。
       *
       * 保存头像/用户名后立即调用此方法，左下角 UserMenu 及页面标题会立即响应，
       * 无需额外一次 GET /users/me 请求。
       */
      updateUser: (user: User) => {
        authService.saveUser(user);
        set({
          user,
          lastRefreshAt: Date.now(),
        });
        console.log('[AuthStore] User updated:', user.username);
      },

      setHasHydrated: (hasHydrated: boolean) => {
        set({ hasHydrated });
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
        lastRefreshAt: state.lastRefreshAt,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);













