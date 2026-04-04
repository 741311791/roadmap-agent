'use client';

import { useMemo, useState } from 'react';
import { ArrowUpRight, Check } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { useVoting } from './hooks/use-voting';
import { IdeaSubmitModal } from './idea-submit-modal';
import { PlanningItemRow } from './planning-item-row';

const PODIUM_ACCENTS = [
  'border-[rgba(196,152,48,0.35)] bg-[linear-gradient(135deg,rgba(196,152,48,0.08),rgba(255,255,255,0.6))]',
  'border-sage-200 bg-[linear-gradient(135deg,rgba(96,117,96,0.10),rgba(255,255,255,0.6))]',
  'border-[rgba(170,107,82,0.22)] bg-[linear-gradient(135deg,rgba(170,107,82,0.08),rgba(255,255,255,0.6))]',
];

/**
 * 社区投票榜单
 */
export function VotingBoard() {
  const t = useTranslations('publicRoadmap.voting');
  const [isIdeaModalOpen, setIsIdeaModalOpen] = useState(false);
  const {
    topItems,
    remainingItems,
    isVoting,
    isSubmittingIdea,
    isVoted,
    handleVote,
    handleSubmitIdea,
  } = useVoting();

  const rankedTopItems = useMemo(
    () =>
      topItems.map((item, index) => ({
        ...item,
        rank: index + 1,
      })),
    [topItems]
  );

  return (
    <section className="bg-background">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-sage-700">
              {t('eyebrow')}
            </span>
            <h2 className="mt-5 text-4xl font-semibold leading-tight text-foreground md:text-6xl">
              {t.rich('title', {
                highlight: (chunks) => <span className="italic text-sage">{chunks}</span>,
              })}
            </h2>
            <p className="mt-5 text-lg leading-8 text-muted-foreground">
              {t('description')}
            </p>
          </div>

          <Button type="button" variant="sage" size="lg" onClick={() => setIsIdeaModalOpen(true)}>
            {t('submitIdea')}
          </Button>
        </div>

        <div className="mt-10 grid gap-4 xl:grid-cols-3">
          {rankedTopItems.map((item, index) => {
            const hasVoted = isVoted(item.id);
            return (
              <article
                key={item.id}
                className={`rounded-3xl border p-6 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md ${PODIUM_ACCENTS[index]}`}
              >
                <p className="font-serif text-5xl font-semibold italic text-foreground/80">#{item.rank}</p>
                <h3 className="mt-6 text-xl font-medium text-foreground">{item.title}</h3>
                <p className="mt-4 text-sm leading-7 text-muted-foreground">{item.description}</p>

                <div className="mt-8 flex items-center justify-between gap-4">
                  <div>
                    <p className="font-mono text-sm text-muted-foreground">{t('votes', { count: item.vote_count })}</p>
                    <div className="mt-3 h-1.5 w-28 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-sage-600 transition-all"
                        style={{ width: `${Math.min(item.vote_count / 140, 1) * 100}%` }}
                      />
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant={hasVoted ? 'outline' : 'sage'}
                    onClick={() => handleVote(item.id)}
                    disabled={hasVoted || isVoting}
                    className="gap-2"
                  >
                    {hasVoted ? <Check className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                    {hasVoted ? t('voted') : t('vote')}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>

        <div className="mt-10 space-y-1">
          {remainingItems.map((item, index) => (
            <PlanningItemRow
              key={item.id}
              item={item}
              rank={index + 4}
              hasVoted={isVoted(item.id)}
              isVoting={isVoting}
              onVote={handleVote}
            />
          ))}
        </div>
      </div>

      <IdeaSubmitModal
        open={isIdeaModalOpen}
        onOpenChange={setIsIdeaModalOpen}
        isSubmitting={isSubmittingIdea}
        onSubmit={handleSubmitIdea}
      />
    </section>
  );
}
