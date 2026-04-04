'use client';

import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import type { PublicRoadmapFeature } from '@/lib/api/roadmap-public';

interface UpcomingSectionProps {
  features: PublicRoadmapFeature[];
}

/**
 * 规划中功能区
 */
export function UpcomingSection({ features }: UpcomingSectionProps) {
  const t = useTranslations('publicRoadmap');

  if (features.length === 0) {
    return null;
  }

  return (
    <section className="mt-8 pt-14">
      <div className="flex items-center gap-4">
        <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-[#a67a2a]">
          {t('upcoming.eyebrow')}
        </span>
        <span className="h-px flex-1 bg-gradient-to-r from-[rgba(175,130,62,0.35)] to-transparent" />
      </div>

      <div className="mt-5 max-w-3xl">
        <h2 className="font-serif text-4xl font-semibold tracking-[-0.02em] text-foreground md:text-5xl">
          {t('upcoming.title')}
        </h2>
        <p className="mt-4 text-lg leading-8 text-muted-foreground">
          {t('upcoming.description')}
        </p>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {features.map((feature) => (
          <article
            key={feature.id}
            className={cn(
              'rounded-[1.25rem] border border-dashed bg-card/90 p-5 transition-all duration-200 hover:-translate-y-0.5',
              feature.status === 'in_progress'
                ? 'border-sage-300 shadow-[0_10px_28px_rgba(96,117,96,0.08)]'
                : 'border-border shadow-sm hover:border-[rgba(175,130,62,0.3)] hover:shadow-[0_10px_24px_rgba(175,130,62,0.10)]'
            )}
          >
            <div className="flex items-start gap-4">
              <span
                className={cn(
                  'mt-1.5 h-2 w-2 shrink-0 rounded-full',
                  feature.status === 'in_progress' ? 'bg-sage-600 shadow-[0_0_0_5px_rgba(96,117,96,0.12)]' : 'bg-stone-300'
                )}
              />
              <div className="min-w-0 flex-1">
                <h3 className="text-[15px] font-medium leading-6 text-foreground">{feature.title}</h3>

                <div className="mt-3 flex flex-wrap gap-2">
                  {feature.status !== 'in_progress' ? (
                    <span className="inline-flex rounded-full bg-[rgba(175,130,62,0.12)] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-[#a67a2a] ring-1 ring-[rgba(175,130,62,0.22)]">
                      {t('status.planned')}
                    </span>
                  ) : null}

                  {feature.labels.map((label) => (
                    <span
                      key={label}
                      className="inline-flex rounded-md border border-border bg-background/70 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm leading-7 text-muted-foreground">
              {feature.description}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
