'use client';

import { useLocale, useTranslations } from 'next-intl';

import type { Locale } from '@/i18n/config';
import { cn } from '@/lib/utils';
import { FeatureCard } from './feature-card';
import type { PublicRoadmapMilestone } from '@/lib/api/roadmap-public';

interface MilestoneBlockProps {
  milestone: PublicRoadmapMilestone;
  isCurrent?: boolean;
}

/**
 * 单个里程碑区块
 */
export function MilestoneBlock({ milestone, isCurrent = false }: MilestoneBlockProps) {
  const locale = useLocale() as Locale;
  const t = useTranslations('publicRoadmap');
  const dateLabel = milestone.start_date
    ? new Date(milestone.start_date).toLocaleDateString(locale === 'zh' ? 'zh-CN' : 'en-US', {
        year: 'numeric',
        month: 'short',
      })
    : t('timeline.tbd');

  const normalizedDateLabel = locale === 'zh' ? dateLabel : dateLabel.toUpperCase();

  const statusLabelMap: Record<PublicRoadmapMilestone['status'], string> = {
    completed: t('status.released'),
    active: t('status.inProgress'),
    upcoming: t('status.planned'),
  };

  return (
    <div className="pb-14">
      {isCurrent ? (
        <div className="mb-6 ml-0 inline-flex items-center gap-3 rounded-md border border-sage-200 bg-sage-50/80 px-4 py-2 md:ml-28">
          <span className="h-2 w-2 rounded-full bg-sage-600 shadow-[0_0_0_5px_rgba(96,117,96,0.12)]" />
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-sage-700">
            {t('timeline.currentIndicator')}
          </span>
        </div>
      ) : null}

      <section className="grid grid-cols-[72px_minmax(0,1fr)] gap-5 md:grid-cols-[96px_minmax(0,1fr)] md:gap-8">
        <div className="relative flex flex-col items-center">
          <span
            className={cn(
              'relative z-10 mt-1 h-5 w-5 rounded-full border-2 bg-background',
              milestone.status === 'completed' && 'border-foreground bg-foreground shadow-[0_0_0_6px_rgba(40,34,24,0.08)]',
              milestone.status === 'active' && 'border-sage-600 bg-background shadow-[0_0_0_6px_rgba(96,117,96,0.12)]',
              milestone.status === 'upcoming' && 'border-dashed border-stone-400 bg-card'
            )}
          />
          <span className="mt-4 rotate-180 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground [writing-mode:vertical-rl]">
            {normalizedDateLabel}
          </span>
        </div>

        <div>
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
            <div className="max-w-3xl">
              <h2 className="font-serif text-[2rem] font-semibold leading-[1.15] tracking-[-0.02em] text-foreground md:text-[2.4rem]">
                {milestone.title}
              </h2>
              <p className="mt-3 max-w-2xl text-[15px] leading-7 text-muted-foreground">
                {milestone.description}
              </p>
            </div>
            <span
              className={cn(
                'mt-1 inline-flex rounded-full px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em]',
                milestone.status === 'completed' && 'bg-foreground/6 text-foreground ring-1 ring-foreground/10',
                milestone.status === 'active' && 'bg-sage-50 text-sage-700 ring-1 ring-sage-200',
                milestone.status === 'upcoming' && 'bg-[rgba(175,130,62,0.12)] text-[#a67a2a] ring-1 ring-[rgba(175,130,62,0.22)]'
              )}
            >
              {statusLabelMap[milestone.status]}
            </span>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {milestone.features.map((feature) => (
              <FeatureCard key={feature.id} feature={feature} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
