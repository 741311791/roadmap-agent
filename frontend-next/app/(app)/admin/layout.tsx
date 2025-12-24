/**
 * Admin 路由布局保护
 * 
 * 仅允许超级管理员访问 /admin 路由下的所有页面
 */
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store/auth-store';
import { Loader2 } from 'lucide-react';

interface AdminLayoutProps {
  children: React.ReactNode;
}

/**
 * Admin 布局组件
 * 
 * 权限检查：
 * - 未登录：重定向到登录页
 * - 已登录但非超级管理员：重定向到首页
 * - 超级管理员：正常渲染
 */
export default function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const { user, isAuthenticated, isAdmin } = useAuthStore();

  useEffect(() => {
    // 检查登录状态
    if (!isAuthenticated || !user) {
      console.log('[AdminLayout] Not authenticated, redirecting to login');
      router.push('/login?redirect=/admin/waitlist');
      return;
    }

    // 检查是否是超级管理员
    if (!isAdmin()) {
      console.log('[AdminLayout] Not superuser, redirecting to home');
      router.push('/home');
      return;
    }

    console.log('[AdminLayout] Access granted for superuser:', user.email);
  }, [isAuthenticated, user, router, isAdmin]);

  // 显示加载状态
  if (!isAuthenticated || !user || !isAdmin()) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Checking permissions...</p>
        </div>
      </div>
    );
  }

  // 渲染子组件
  return <>{children}</>;
}

