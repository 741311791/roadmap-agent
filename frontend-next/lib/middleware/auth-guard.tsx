/**
 * 认证路由守卫（性能优化版）
 * 
 * 保护需要登录的页面，自动重定向到登录页
 * 
 * 优化点：
 * - 移除不必要的延迟和状态
 * - 使用 useMemo 缓存计算结果
 * - 简化渲染逻辑，减少重渲染
 */
'use client';

import { useEffect, useState, useMemo } from 'react';
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
  const { isAuthenticated, refreshUser } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);
  
  // 缓存公开路由检查结果
  const isPublic = useMemo(() => isPublicRoute(pathname), [pathname]);
  
  useEffect(() => {
    // 公开路由直接跳过检查
    if (isPublic) {
      setIsChecking(false);
      return;
    }
    
    console.log('[AuthGuard] Checking auth for path:', pathname);
    
    // 刷新用户状态（同步操作，从 localStorage 读取）
    refreshUser();
    
    // 检查认证状态
    if (!isAuthenticated) {
      console.log('[AuthGuard] ❌ Unauthorized, redirecting to login');
      router.push('/login?redirect=' + encodeURIComponent(pathname));
    } else {
      console.log('[AuthGuard] ✅ Access granted');
      setIsChecking(false);
    }
  }, [pathname, isAuthenticated, isPublic, refreshUser, router]);
  
  // 公开路由直接渲染
  if (isPublic) {
    return <>{children}</>;
  }
  
  // 未登录时显示加载状态
  if (!isAuthenticated || isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    );
  }
  
  // 已登录，渲染子组件
  return <>{children}</>;
}

