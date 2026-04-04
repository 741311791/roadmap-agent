'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Skeleton } from '@/components/ui/skeleton';
import type { Locale } from '@/i18n/config';
import { cn } from '@/lib/utils';
import { MilestoneBlock } from './milestone-block';
import { UpcomingSection } from './upcoming-section';
import { useRoadmapData } from './hooks/use-roadmap-data';

const MILESTONES_PAGE_SIZE = 5;

/**
 * 产品路书时间轴主容器
 */
export function RoadmapTimeline() {
  const locale = useLocale() as Locale;
  const t = useTranslations('publicRoadmap');
  const { data, isLoading } = useRoadmapData(locale);
  const [visibleMilestoneCount, setVisibleMilestoneCount] = useState(MILESTONES_PAGE_SIZE);

  const stats = useMemo(() => {
    const milestones = data?.milestones ?? [];
    const features = milestones.flatMap((milestone) => milestone.features);

    return {
      milestoneCount: milestones.length,
      releasedCount: features.filter((feature) => feature.status === 'released').length,
      inProgressCount: features.filter((feature) => feature.status === 'in_progress').length,
      planningCount: (data?.upcoming_features.length ?? 0) + features.filter((feature) => feature.status === 'planned').length,
    };
  }, [data]);

  const currentMilestoneId = useMemo(() => {
    return data?.milestones.find((item) => item.status === 'active')?.id ?? null;
  }, [data]);

  const visibleMilestones = useMemo(() => {
    return (data?.milestones ?? []).slice(0, visibleMilestoneCount);
  }, [data?.milestones, visibleMilestoneCount]);

  const upcomingFeatures = useMemo(() => {
    if (!data) {
      return [];
    }

    const inProgressFeatures = data.milestones.flatMap((milestone) =>
      milestone.features.filter((feature) => feature.status === 'in_progress')
    );

    return [...inProgressFeatures, ...data.upcoming_features];
  }, [data]);

  const totalMilestoneCount = data?.milestones.length ?? 0;
  const hasLoadedAllMilestones = totalMilestoneCount > 0 && visibleMilestoneCount >= totalMilestoneCount;
  const canLoadMoreMilestones = totalMilestoneCount > visibleMilestoneCount;

  useEffect(() => {
    setVisibleMilestoneCount(MILESTONES_PAGE_SIZE);
  }, [data?.milestones]);

  /**
   * 每次追加展示 5 个里程碑，与设计稿的渐进展开交互保持一致。
   */
  function handleLoadMoreMilestones() {
    setVisibleMilestoneCount((current) => current + MILESTONES_PAGE_SIZE);
  }

  return (
    <section className="relative overflow-hidden bg-background">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(96,117,96,0.12),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(120,100,76,0.08),transparent_28%)]" />
      <div className="absolute inset-0 -z-10 bg-noise opacity-[0.06]" />

      <div className="mx-auto max-w-7xl px-6 pb-24 pt-28 md:pb-28 md:pt-36">
        <header className="max-w-4xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-sage-700">
            {t('timeline.eyebrow')}
          </span>
          <h1 className="mt-5 text-5xl font-semibold leading-[1.05] text-foreground md:text-7xl">
            {t.rich('timeline.title', {
              highlight: (chunks) => <span className="italic text-sage">{chunks}</span>,
              br: () => <br />,
            })}
          </h1>
          <p className="mt-6 max-w-3xl text-xl leading-9 text-muted-foreground">
            {t('timeline.description')}
          </p>
        </header>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label={t('timeline.stats.milestones')} value={stats.milestoneCount} />
          <StatCard label={t('timeline.stats.featuresShipped')} value={stats.releasedCount} />
          <StatCard label={t('timeline.stats.inProgress')} value={stats.inProgressCount} />
          <StatCard label={t('timeline.stats.plannedNext')} value={stats.planningCount} />
        </div>

        <div className="relative mt-14">
          <div className="absolute bottom-0 left-9 top-0 hidden w-px bg-border md:left-12 md:block" />

          {isLoading ? (
            <div className="space-y-8">
              {[1, 2, 3].map((item) => (
                <div key={item} className="grid gap-6 md:grid-cols-[96px_minmax(0,1fr)]">
                  <div className="hidden md:flex justify-center">
                    <Skeleton className="h-5 w-5 rounded-full" />
                  </div>
                  <div>
                    <Skeleton className="h-10 w-72" />
                    <Skeleton className="mt-4 h-6 w-full max-w-2xl" />
                    <div className="mt-6 grid gap-4">
                      <Skeleton className="h-28 rounded-3xl" />
                      <Skeleton className="h-28 rounded-3xl" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {visibleMilestones.map((milestone) => (
                <MilestoneBlock
                  key={milestone.id}
                  milestone={milestone}
                  isCurrent={milestone.id === currentMilestoneId}
                />
              ))}
            </div>
          )}
        </div>

        {!isLoading && totalMilestoneCount > 0 ? (
          <div className="mt-2 flex flex-col items-center gap-4">
            {canLoadMoreMilestones ? (
              <button
                type="button"
                onClick={handleLoadMoreMilestones}
                className="group flex flex-col items-center gap-1.5 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground transition-colors duration-200 hover:text-sage-700"
              >
                <span>{t('timeline.loadMoreMilestones', { count: MILESTONES_PAGE_SIZE })}</span>
                <span className="flex flex-col items-center gap-0.5 opacity-60 transition-all duration-300 group-hover:translate-y-0.5 group-hover:opacity-100">
                  <span className="h-3 w-px bg-current" />
                  <svg width="8" height="5" viewBox="0 0 8 5" fill="none" className="shrink-0">
                    <path d="M1 1L4 4L7 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </button>
            ) : null}

            {hasLoadedAllMilestones ? (
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                {t('timeline.allMilestonesLoaded')}
              </p>
            ) : null}
          </div>
        ) : null}

        {data ? <UpcomingSection features={upcomingFeatures} /> : null}
      </div>
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: number;
}

/**
 * 页头统计卡片
 */
function StatCard({ label, value }: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-3xl border border-border bg-card/90 px-6 py-5 shadow-sm backdrop-blur-sm',
        'transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md'
      )}
    >
      <p className="font-serif text-4xl font-semibold text-foreground">{value}</p>
      <p className="mt-2 text-sm uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
    </div>
  );
}
