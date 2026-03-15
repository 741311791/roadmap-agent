/**
 * 认证路由守卫（性能优化版）
 * 
 * 保护需要登录的页面，自动重定向到登录页
 * 
 * 优化点：
 * - 受保护页面不再等待 `/users/me` 返回后才渲染
 * - 仅在 store hydrate 完成后判断登录态，避免误跳转
 * - 将用户刷新改为后台同步，避免每次路由切换串行阻塞
 */
'use client';

import { useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/store/auth-store';
import { Loader2 } from 'lucide-react';

// 公开路由（无需登录）
const PUBLIC_ROUTES = [
  '/login',
  '/about',
  '/pricing',
  '/font-test', // 字体测试页面
  '/methodology', // 方法论页面
];

/**
 * 检查路径是否为公开路由
 * 
 * 注意：'/' 根路径特殊处理，只匹配精确路径
 */
function isPublicRoute(pathname: string): boolean {
  // 精确匹配根路径
  if (pathname === '/') {
    return true;
  }
  
  // 检查是否匹配其他公开路由
  return PUBLIC_ROUTES.some(route => {
    if (route === '/') {
      return pathname === '/';
    }
    // 精确匹配或匹配子路径（带斜杠）
    return pathname === route || pathname.startsWith(route + '/');
  });
}

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * 认证守卫组件（性能优化版）
 * 
 * 优化点：
 * - 移除不必要的状态和延迟
 * - 使用 useMemo 缓存公开路由检查
 * - 简化渲染逻辑
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, hasHydrated, refreshUser } = useAuthStore();
  
  // 缓存公开路由检查结果
  const isPublic = useMemo(() => isPublicRoute(pathname), [pathname]);
  
  useEffect(() => {
    if (isPublic || !hasHydrated) {
      return;
    }

    if (!isAuthenticated) {
      console.log('[AuthGuard] ❌ Unauthorized, redirecting to login');
      router.replace('/login?redirect=' + encodeURIComponent(pathname));
    }
  }, [pathname, hasHydrated, isAuthenticated, isPublic, router]);

  useEffect(() => {
    if (!hasHydrated || !isAuthenticated) {
      return;
    }

    void refreshUser();
  }, [hasHydrated, isAuthenticated, refreshUser]);
  
  // 公开路由直接渲染
  if (isPublic) {
    return <>{children}</>;
  }
  
  // 等待持久化状态恢复，避免刷新页面时先误判为未登录
  if (!hasHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Restoring session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    );
  }
  
  // 已登录，渲染子组件
  return <>{children}</>;
}

