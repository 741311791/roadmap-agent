'use client';

import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';

/**
 * 路线图详情页路由级加载态。
 *
 * 在页面切换期间优先展示骨架屏，避免用户点击“查看路线图”后出现空白等待。
 */
export default function RoadmapDetailLoading() {
  const t = useTranslations('roadmapDetail');

  return (
    <div className="h-screen w-full overflow-hidden bg-background text-foreground">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[10%] -left-[5%] h-[40%] w-[40%] rounded-full opacity-30 blur-[100px]"
          style={{ backgroundColor: 'hsl(140 20% 85%)' }}
        />
        <div
          className="absolute bottom-[-5%] right-[-5%] h-[35%] w-[35%] rounded-full opacity-20 blur-[80px]"
          style={{ backgroundColor: 'hsl(40 30% 90%)' }}
        />
        <div className="absolute inset-0 bg-noise opacity-[0.015]" />
      </div>

      <div className="relative z-10 flex h-full">
        <aside className="hidden h-full w-[280px] border-r border-border/60 bg-background/80 px-5 py-6 backdrop-blur lg:flex lg:flex-col">
          <Skeleton className="mb-6 h-8 w-36 rounded-xl" />
          <div className="space-y-4">
            <Skeleton className="h-4 w-24 rounded" />
            <Skeleton className="h-10 w-full rounded-2xl" />
            <Skeleton className="h-10 w-[88%] rounded-2xl" />
            <Skeleton className="h-10 w-[82%] rounded-2xl" />
          </div>
          <div className="mt-8 space-y-3">
            <Skeleton className="h-3 w-20 rounded" />
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-3 border-b border-border/50 px-6 py-5 backdrop-blur">
            <div className="relative">
              <Loader2 className="h-5 w-5 animate-spin text-sage-600 dark:text-sage-400" />
              <div className="absolute inset-0 rounded-full border border-sage-300/70 animate-ping dark:border-sage-700/70" />
            </div>
            <span className="font-serif text-lg">{t('loadingRoadmap')}</span>
          </div>

          <div className="flex-1 px-6 py-6">
            <div className="mx-auto flex h-full max-w-5xl flex-col gap-6">
              <div className="rounded-3xl border border-border/60 bg-background/85 p-6 shadow-sm backdrop-blur">
                <Skeleton className="mb-4 h-9 w-1/2 rounded-xl" />
                <Skeleton className="mb-2 h-4 w-full rounded" />
                <Skeleton className="mb-2 h-4 w-[94%] rounded" />
                <Skeleton className="h-4 w-[72%] rounded" />
              </div>

              <div className="grid flex-1 gap-6 lg:grid-cols-[1.35fr_0.85fr]">
                <section className="rounded-3xl border border-border/60 bg-background/85 p-6 shadow-sm backdrop-blur">
                  <div className="mb-6 flex items-center justify-between">
                    <Skeleton className="h-8 w-40 rounded-xl" />
                    <Skeleton className="h-8 w-24 rounded-full" />
                  </div>
                  <div className="space-y-4">
                    <Skeleton className="h-28 w-full rounded-3xl" />
                    <Skeleton className="h-24 w-full rounded-3xl" />
                    <Skeleton className="h-32 w-full rounded-3xl" />
                  </div>
                </section>

                <section className="rounded-3xl border border-border/60 bg-background/85 p-6 shadow-sm backdrop-blur">
                  <Skeleton className="mb-5 h-8 w-32 rounded-xl" />
                  <div className="space-y-4">
                    <Skeleton className="h-20 w-full rounded-2xl" />
                    <Skeleton className="h-20 w-full rounded-2xl" />
                    <Skeleton className="h-20 w-full rounded-2xl" />
                    <Skeleton className="h-20 w-[88%] rounded-2xl" />
                  </div>
                </section>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
