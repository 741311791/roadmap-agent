'use client';

/**
 * Home Client Page - 主页客户端内容
 *
 * 说明：
 * - 保持当前基于前端认证的取数模式
 * - 页面入口改为服务端壳，便于后续逐步推进 SSR / RSC
 */

import { useEffect } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { ScrollArea } from '@/components/ui/scroll-area';
import { EmptyState } from '@/components/common/empty-state';
import { MyLearningCard, CreateLearningCard, FeaturedRoadmapCard, FeaturedRoadmap } from '@/components/roadmap';
import { Button } from '@/components/ui/button';
import {
  BookOpen,
  ArrowRight,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useFeaturedRoadmapsQuery, useMyRoadmapsQuery } from '@/lib/hooks/api/use-dashboard-queries';

function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  showViewAll = false,
  viewAllHref,
}: {
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  showViewAll?: boolean;
  viewAllHref?: string;
}) {
  const t = useTranslations();
  return (
    <div className="flex items-end justify-between mb-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-sage-100 flex items-center justify-center">
          <Icon size={20} className="text-sage-600" />
        </div>
        <div>
          <h2 className="text-xl font-serif font-bold text-foreground">{title}</h2>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </div>
      {showViewAll && viewAllHref && (
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="text-sage-600 hover:text-sage-700 hover:bg-sage-50 font-medium"
        >
          <Link href={viewAllHref} className="flex items-center gap-1">
            {t('common.viewAll')}
            <ArrowRight size={16} />
          </Link>
        </Button>
      )}
    </div>
  );
}

export function HomeClientPage() {
  const t = useTranslations();
  const { history, setHistory } = useRoadmapStore();
  const { data: myRoadmapsResponse, isLoading } = useMyRoadmapsQuery({ limit: 4, offset: 0 });
  const { data: featuredResponse, isLoading: isFeaturedLoading } = useFeaturedRoadmapsQuery({ limit: 5, offset: 0 });

  useEffect(() => {
    if (!myRoadmapsResponse) {
      return;
    }

    const historyData = myRoadmapsResponse.items.map((item) => ({
      roadmap_id: item.roadmap_id,
      title: item.title,
      created_at: item.created_at,
      cover_image_url: item.cover_image_url ?? null,
      total_concepts: item.total_concepts,
      completed_concepts: item.completed_concepts,
      topic: item.topic || undefined,
      status: item.status || 'completed',
      task_id: item.task_id,
      task_status: item.task_status,
      current_step: item.current_step,
      stages: item.stages || null,
    }));
    setHistory(historyData as any);
  }, [myRoadmapsResponse, setHistory]);

  const featuredRoadmaps: FeaturedRoadmap[] = (featuredResponse?.items || [])
    .filter(item => item.status === 'completed')
    .map((item) => ({
      id: item.roadmap_id,
      title: item.title,
      topic: item.topic || item.title.toLowerCase(),
      coverImageUrl: item.cover_image_url ?? null,
      author: {
        name: 'Admin',
        avatar: undefined,
      },
      stats: {
        likes: Math.floor(Math.random() * 1000),
        views: Math.floor(Math.random() * 5000),
        bookmarks: Math.floor(Math.random() * 500),
        learners: Math.floor(Math.random() * 2000),
      },
      tags: item.topic ? [item.topic] : [],
      totalConcepts: item.total_concepts || 0,
      totalHours: Math.ceil((item.total_concepts || 0) * 0.5),
      difficulty: 'intermediate' as const,
      isTrending: Math.random() > 0.7,
      createdAt: item.created_at || new Date().toISOString(),
      stages: item.stages?.map(stage => ({
        name: stage.name,
        description: stage.description || undefined,
        order: stage.order,
      })),
    }));

  const allRoadmaps = history
    .filter(item => item.status !== 'generating')
    .map((item) => ({
      id: item.roadmap_id,
      title: item.title,
      status: item.status || 'completed',
      totalConcepts: item.total_concepts || 0,
      completedConcepts: item.completed_concepts || 0,
      totalHours: 0,
      lastAccessedAt: item.created_at || new Date().toISOString(),
      topic: item.topic || item.title.toLowerCase(),
      coverImageUrl: (item as any).cover_image_url ?? null,
      taskId: (item as any).task_id || null,
      taskStatus: (item as any).task_status || null,
      currentStep: (item as any).current_step || null,
      stages: (item as any).stages || null,
    }));

  const displayedRoadmaps = allRoadmaps.slice(0, 3);
  const hasMoreRoadmaps = allRoadmaps.length > 3;
  const hasRoadmaps = allRoadmaps.length > 0;
  const displayedFeatured = featuredRoadmaps.slice(0, 4);
  const hasMoreFeatured = featuredRoadmaps.length > 4;

  return (
    <ScrollArea className="h-full">
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-10">
          <div className="flex items-center gap-2 text-sage-600 mb-2">
            <Sparkles size={16} />
            <span className="text-sm font-medium">{t('header.welcomeBack')}</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground mb-2">
            {t('header.continueJourney')}
          </h1>
          <p className="text-base text-muted-foreground max-w-2xl">
            {t('header.pickUpDesc')}
          </p>
        </div>

        <section className="mb-16">
          <SectionHeader
            icon={BookOpen}
            title={t('roadmap.myLearningJourneys')}
            subtitle={hasRoadmaps ? `${allRoadmaps.length} ${t('roadmap.roadmap_other')}` : undefined}
            showViewAll={hasMoreRoadmaps}
            viewAllHref="/roadmaps"
          />

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">{t('roadmap.loadingRoadmaps')}</p>
              </div>
            </div>
          ) : hasRoadmaps ? (
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  <div className="w-[280px] sm:w-auto flex-shrink-0">
                    <CreateLearningCard />
                  </div>

                  {displayedRoadmaps.map((roadmap) => (
                    <div key={roadmap.id} className="w-[280px] sm:w-auto flex-shrink-0">
                      <MyLearningCard
                        id={roadmap.id}
                        title={roadmap.title}
                        topic={roadmap.topic}
                        status={roadmap.status}
                        totalConcepts={roadmap.totalConcepts}
                        completedConcepts={roadmap.completedConcepts}
                        lastAccessedAt={roadmap.lastAccessedAt}
                        taskId={roadmap.taskId}
                        taskStatus={roadmap.taskStatus}
                        currentStep={roadmap.currentStep}
                        showActions={false}
                        stages={roadmap.stages}
                        coverImageUrl={roadmap.coverImageUrl}
                        enableFlip={false}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {hasRoadmaps && (
                <div className="sm:hidden flex justify-center mt-2 gap-1">
                  {[...Array(Math.min(displayedRoadmaps.length + 1, 4))].map((_, index) => (
                    <div key={index} className="w-1.5 h-1.5 rounded-full bg-sage-200" />
                  ))}
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              icon={BookOpen}
              title={t('roadmap.noRoadmapsYet')}
              description={t('roadmap.createFirstRoadmap')}
              action={{
                label: t('common.createRoadmap'),
                onClick: () => {
                  window.location.href = '/new';
                },
              }}
            />
          )}
        </section>

        <section className="mb-8">
          <SectionHeader
            icon={TrendingUp}
            title={t('roadmap.featuredRoadmaps')}
            subtitle={t('roadmap.featuredDesc')}
            showViewAll={hasMoreFeatured}
            viewAllHref="/explore"
          />

          {isFeaturedLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <div className="w-10 h-10 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">{t('roadmap.loadingFeatured')}</p>
              </div>
            </div>
          ) : displayedFeatured.length > 0 ? (
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displayedFeatured.map((roadmap) => (
                    <div key={roadmap.id} className="w-[280px] sm:w-auto flex-shrink-0">
                      <FeaturedRoadmapCard
                        roadmap={roadmap}
                        coverImageUrl={roadmap.coverImageUrl ?? null}
                        enableFlip={false}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="sm:hidden flex justify-center mt-2 gap-1">
                {[...Array(Math.min(displayedFeatured.length, 4))].map((_, index) => (
                  <div key={index} className="w-1.5 h-1.5 rounded-full bg-sage-200" />
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-16 bg-sage-50 rounded-xl border-2 border-dashed border-sage-200">
              <TrendingUp className="w-12 h-12 text-sage-300 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">{t('roadmap.noFeaturedAvailable')}</p>
              <p className="text-xs text-muted-foreground mt-1">{t('roadmap.checkBackSoon')}</p>
            </div>
          )}
        </section>

        <div className="h-12" />
      </div>

      <style jsx global>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </ScrollArea>
  );
}
