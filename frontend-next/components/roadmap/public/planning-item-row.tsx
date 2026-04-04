'use client';

import { ArrowUpRight, Check } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { UseVotingItem } from './hooks/use-voting';

interface PlanningItemRowProps {
  item: UseVotingItem;
  rank: number;
  hasVoted: boolean;
  isVoting: boolean;
  onVote: (itemId: number) => void;
}

/**
 * 待规划需求列表行
 */
export function PlanningItemRow({
  item,
  rank,
  hasVoted,
  isVoting,
  onVote,
}: PlanningItemRowProps) {
  const t = useTranslations('publicRoadmap.voting');

  return (
    <article className="grid items-center gap-4 rounded-2xl px-4 py-4 transition-all duration-200 hover:bg-card/70 hover:shadow-[0_8px_24px_rgba(40,34,24,0.05)] md:grid-cols-[40px_minmax(0,1fr)_96px_120px]">
      <div className="font-mono text-sm text-muted-foreground">#{rank}</div>

      <div className="min-w-0">
        <div className="flex items-start gap-2">
          <h3 className="text-sm font-medium text-foreground md:text-base">{item.title}</h3>
          {rank <= 3 ? (
            <span className="rounded-full bg-sage-50 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-sage-700">
              Top {rank}
            </span>
          ) : null}
        </div>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">
          {item.description}
        </p>
      </div>

      <div className="flex items-center gap-3 md:justify-end">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary md:max-w-[72px]">
          <div
            className="h-full rounded-full bg-sage-600 transition-all"
            style={{ width: `${Math.min(item.vote_count / 140, 1) * 100}%` }}
          />
        </div>
        <span className="font-mono text-sm text-muted-foreground">{item.vote_count}</span>
      </div>

      <div className="md:justify-self-end">
        <Button
          type="button"
          variant={hasVoted ? 'outline' : 'sage'}
          size="sm"
          className={cn('gap-2', hasVoted && 'text-muted-foreground')}
          disabled={hasVoted || isVoting}
          onClick={() => onVote(item.id)}
        >
          {hasVoted ? <Check className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
          {hasVoted ? t('voted') : t('vote')}
        </Button>
      </div>
    </article>
  );
}
