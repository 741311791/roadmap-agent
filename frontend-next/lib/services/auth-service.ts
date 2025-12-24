/**
 * 认证服务
 * 
 * 提供基于 JWT 的用户认证功能。
 * 支持邮箱+密码登录、令牌刷新、登出等操作。
 * 
 * @author Fast Learning Team
 */

import { apiClient } from '@/lib/api/client';

export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  password_expires_at?: string | null;
  created_at?: string | null;
}

// 兼容旧版 User 类型
export interface LegacyUser {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  avatar?: string;
}

/**
 * 预定义的测试账号（保持向后兼容）
 * 
 * 仅在开发环境且未启用真实认证时使用
 */
const MOCK_USERS: LegacyUser[] = [
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
];

/**
 * 认证服务类
 * 
 * 管理用户登录状态和会话信息
 */
class AuthService {
  private static readonly USER_KEY = 'fast_learning_user';
  private static readonly TOKEN_KEY = 'fast_learning_token';
  
  /**
   * 使用邮箱和密码登录
   * 
   * 调用后端 FastAPI Users JWT 登录端点
   * 
   * @param email - 用户邮箱
   * @param password - 密码
   * @returns 登录是否成功
   */
  async loginWithPassword(email: string, password: string): Promise<boolean> {
    try {
      // FastAPI Users 使用 OAuth2 密码流，需要发送 form-urlencoded 数据
      const formData = new URLSearchParams();
      formData.append('username', email);  // FastAPI Users 使用 username 字段
      formData.append('password', password);
      
      const response = await apiClient.post<{ access_token: string; token_type: string }>(
        '/auth/jwt/login',
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      
      const { access_token } = response.data;
      
      // 保存令牌
      this.setToken(access_token);
      
      // 获取用户信息
      const user = await this.fetchCurrentUser();
      if (user) {
        this.setUser(user);
        console.log('[AuthService] Login successful:', user.email);
        return true;
      }
      
      return false;
    } catch (error: any) {
      console.error('[AuthService] Login failed:', error);
      throw error;
    }
  }
  
  /**
   * 从后端获取当前用户信息
   */
  async fetchCurrentUser(): Promise<User | null> {
    try {
      const response = await apiClient.get<User>('/users/me');
      return response.data;
    } catch (error) {
      console.error('[AuthService] Failed to fetch current user:', error);
      return null;
    }
  }
  
  /**
   * 获取当前登录用户（从本地存储）
   * 
   * @returns 当前用户信息，未登录返回 null
   */
  getCurrentUser(): User | null {
    if (typeof window === 'undefined') {
      return null;
    }
    
    const stored = localStorage.getItem(AuthService.USER_KEY);
    if (!stored) {
      return null;
    }
    
    try {
      return JSON.parse(stored) as User;
    } catch (error) {
      console.error('[AuthService] Failed to parse user:', error);
      return null;
    }
  }
  
  /**
   * 保存用户信息到本地存储
   */
  private setUser(user: User): void {
    localStorage.setItem(AuthService.USER_KEY, JSON.stringify(user));
  }
  
  /**
   * 获取访问令牌
   */
  getToken(): string | null {
    if (typeof window === 'undefined') {
      return null;
    }
    return localStorage.getItem(AuthService.TOKEN_KEY);
  }
  
  /**
   * 保存访问令牌
   */
  private setToken(token: string): void {
    localStorage.setItem(AuthService.TOKEN_KEY, token);
  }
  
  /**
   * 模拟登录（选择测试账号）- 保持向后兼容
   * 
   * @param userId - 要登录的用户 ID
   * @returns 成功返回用户信息，失败返回 null
   * @deprecated 使用 loginWithPassword 替代
   */
  login(userId: string): User | null {
    const mockUser = MOCK_USERS.find(u => u.id === userId);
    if (!mockUser) {
      console.error('[AuthService] Mock user not found:', userId);
      return null;
    }
    
    // 转换为新的 User 格式
    const user: User = {
      id: mockUser.id,
      username: mockUser.username,
      email: mockUser.email,
      is_active: true,
      is_superuser: mockUser.role === 'admin',
      is_verified: true,
    };
    
    this.setUser(user);
    console.log('[AuthService] Mock login:', user.username);
    return user;
  }
  
  /**
   * 登出
   * 
   * 清除本地存储的用户信息和令牌
   */
  logout(): void {
    if (typeof window === 'undefined') {
      return;
    }
    
    localStorage.removeItem(AuthService.USER_KEY);
    localStorage.removeItem(AuthService.TOKEN_KEY);
    console.log('[AuthService] User logged out');
  }
  
  /**
   * 异步登出（调用后端接口）
   */
  async logoutAsync(): Promise<void> {
    try {
      await apiClient.post('/auth/jwt/logout');
    } catch (error) {
      console.error('[AuthService] Logout API call failed:', error);
    } finally {
      this.logout();
    }
  }
  
  /**
   * 获取所有可用的测试账号
   * 
   * @returns 测试账号列表
   * @deprecated 生产环境不应使用
   */
  getAvailableUsers(): LegacyUser[] {
    return MOCK_USERS;
  }
  
  /**
   * 检查是否已登录
   * 
   * @returns true 表示已登录
   */
  isAuthenticated(): boolean {
    return this.getCurrentUser() !== null && this.getToken() !== null;
  }
  
  /**
   * 获取当前 user_id（用于 API 调用）
   * 
   * @returns 当前用户 ID，未登录返回 null
   */
  getCurrentUserId(): string | null {
    const user = this.getCurrentUser();
    return user?.id || null;
  }
  
  /**
   * 检查用户是否是管理员
   * 
   * @returns true 表示是管理员
   */
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.is_superuser === true;
  }
  
  /**
   * 检查令牌是否已过期（简单检查）
   * 
   * 注意：这只是简单检查令牌是否存在，
   * 实际过期检查应该由后端处理 401 响应
   */
  isTokenValid(): boolean {
    const token = this.getToken();
    if (!token) {
      return false;
    }
    
    // 简单的 JWT 解析检查（不验证签名）
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000;  // JWT exp 是秒，转换为毫秒
      return Date.now() < exp;
    } catch {
      return false;
    }
  }
}

// 导出单例实例
export const authService = new AuthService();

// 导出类型
export type { User as AuthUser };
