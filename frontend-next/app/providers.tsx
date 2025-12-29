'use client';

/**
 * Providers - 应用全局Provider配置
 * 
 * 优化：增强TanStack Query缓存策略，提升性能
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { Toaster } from 'sonner';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // ========================================
            // 优化：增强缓存策略
            // ========================================
            staleTime: 5 * 60 * 1000,    // 5分钟缓存，减少重复请求
            gcTime: 30 * 60 * 1000,      // 30分钟后垃圾回收
            refetchOnWindowFocus: false, // 避免频繁刷新
            retry: 1,                     // 减少重试次数，加快失败反馈
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
          },
          mutations: {
            retry: 0, // Mutations不重试
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster 
        position="top-right"
        expand={true}
        richColors
        closeButton
      />
    </QueryClientProvider>
  );
}

