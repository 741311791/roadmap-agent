'use client';

import { useState } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import { MediaEmbed } from './media-embed';
import type { PublicRoadmapFeature } from '@/lib/api/roadmap-public';

interface FeatureCardProps {
  feature: PublicRoadmapFeature;
}

const STATUS_ACCENTS: Record<PublicRoadmapFeature['status'], string> = {
  released: 'bg-foreground',
  in_progress: 'bg-sage-600 shadow-[0_0_0_5px_rgba(96,117,96,0.12)]',
  planned: 'bg-stone-300',
};

/**
 * 单个功能卡片
 */
export function FeatureCard({ feature }: FeatureCardProps) {
  const t = useTranslations('publicRoadmap');
  const [expanded, setExpanded] = useState(false);

  const statusLabelMap: Record<PublicRoadmapFeature['status'], string> = {
    released: t('status.released'),
    in_progress: t('status.inProgress'),
    planned: t('status.planned'),
  };

  return (
    <article
      className={cn(
        'rounded-[1.25rem] border border-border bg-card/90 transition-all duration-300 hover:border-stone-300 hover:shadow-[0_10px_30px_rgba(40,34,24,0.07)]',
        expanded && 'border-sage-200 shadow-[0_18px_40px_rgba(96,117,96,0.12)] md:col-span-2',
        feature.status === 'planned' && !expanded && 'opacity-75'
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-start gap-4 px-5 py-4 text-left"
      >
        <span
          className={cn(
            'mt-1.5 h-2 w-2 shrink-0 rounded-full',
            STATUS_ACCENTS[feature.status]
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-3">
            <h3 className="flex-1 text-[15px] font-medium leading-6 text-foreground">{feature.title}</h3>
          </div>

          {feature.labels.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {feature.labels.map((label) => (
                <span
                  key={label}
                  className="inline-flex rounded-md border border-border bg-background/70 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground"
                >
                  {label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <ChevronDown
          className={cn(
            'mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-300',
            expanded && 'rotate-180'
          )}
        />
      </button>

      <div
        className={cn(
          'grid transition-[grid-template-rows] duration-300 ease-out',
          expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border px-5 py-5">
            <div className="mb-4 inline-flex rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground ring-1 ring-border">
              {statusLabelMap[feature.status]}
            </div>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
              {feature.description || t('feature.moreDetailsSoon')}
            </p>

            <MediaEmbed title={feature.title} url={feature.demo_url} className="mt-5" />

            {feature.linear_url ? (
              <div className="mt-4">
                <a
                  href={feature.linear_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-medium text-sage-700 transition-colors hover:text-sage-800"
                >
                  <span>{t('feature.openInLinear')}</span>
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}
