'use client';

/**
 * Home Page - 主页
 * 
 * 展示用户的学习旅程和精选路线图
 * 
 * 布局：
 * - My Learning Journeys: 单行展示，最多4个（包含 Create 卡片）
 * - Featured Roadmaps: 单行展示，最多4个
 * - 响应式设计：支持 horizontal scroll
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { ScrollArea } from '@/components/ui/scroll-area';
import { EmptyState } from '@/components/common/empty-state';
import { MyLearningCard, CreateLearningCard, FeaturedRoadmapCard, MyRoadmap, FeaturedRoadmap } from '@/components/roadmap';
import { Button } from '@/components/ui/button';
import {
  BookOpen,
  ArrowRight,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { roadmapsApi } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/store/auth-store';
import { batchFetchCoverImagesFromAPI } from '@/lib/cover-image';

// Section Header Component
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

// Main Home Page Component
export default function HomePage() {
  const t = useTranslations();
  const { history, setHistory } = useRoadmapStore();
  const { getUserId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [featuredRoadmaps, setFeaturedRoadmaps] = useState<FeaturedRoadmap[]>([]);
  const [isFeaturedLoading, setIsFeaturedLoading] = useState(true);
  const [coverImageMap, setCoverImageMap] = useState<Map<string, string | null>>(new Map());
  const [featuredCoverImageMap, setFeaturedCoverImageMap] = useState<Map<string, string | null>>(new Map());
  
  // Fetch user roadmaps on mount
  useEffect(() => {
    const fetchRoadmaps = async () => {
      try {
        setIsLoading(true);
        // Home 页面只需要显示最新的 3 个路线图（+ 1个 Create 卡片）
        // 为了判断是否有更多路线图（显示 View All），多获取 1 个
        const response = await roadmapsApi.getMyRoadmaps({ limit: 4, offset: 0 });
        // Map API response to store format
        const historyData = response.items.map((item) => {
          let status = item.status || 'completed';
          
          return {
            roadmap_id: item.roadmap_id,
            title: item.title,
            created_at: item.created_at,
            total_concepts: item.total_concepts,
            completed_concepts: item.completed_concepts,
            topic: item.topic || undefined,
            status,
            task_id: item.task_id,
            task_status: item.task_status,
            current_step: item.current_step,
            stages: item.stages || null, // 保留 stages 数据
          };
        });
        setHistory(historyData as any);
        
        // 批量获取封面图
        const roadmapIds = historyData
          .filter(item => item.status !== 'generating')
          .map(item => item.roadmap_id);
        if (roadmapIds.length > 0) {
          const coverImages = await batchFetchCoverImagesFromAPI(roadmapIds);
          setCoverImageMap(coverImages);
        }
      } catch (error) {
        console.error('Failed to fetch roadmaps:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchRoadmaps();
  }, [getUserId, setHistory]);
  
  // Fetch featured roadmaps (from Featured API)
  useEffect(() => {
    const fetchFeaturedRoadmaps = async () => {
      try {
        setIsFeaturedLoading(true);
        // Home 页面显示 4 个精选路线图
        // 为了判断是否有更多（显示 View All），多获取 1 个
        const response = await roadmapsApi.getFeatured({ limit: 5, offset: 0 });
        const featuredData: FeaturedRoadmap[] = response.items
          .filter(item => item.status === 'completed') // 只显示已完成的路线图
          .map((item) => ({
            id: item.roadmap_id,
            title: item.title,
            topic: item.topic || item.title.toLowerCase(),
            author: {
              name: 'Admin', // TODO: 从 API 获取真实作者信息
              avatar: undefined,
            },
            stats: {
              likes: Math.floor(Math.random() * 1000), // TODO: 从 API 获取真实统计数据
              views: Math.floor(Math.random() * 5000),
              bookmarks: Math.floor(Math.random() * 500),
              learners: Math.floor(Math.random() * 2000),
            },
            tags: item.topic ? [item.topic] : [],
            totalConcepts: item.total_concepts || 0,
            totalHours: Math.ceil((item.total_concepts || 0) * 0.5), // 估算小时数：每个概念约0.5小时
            difficulty: 'intermediate' as const,
            isTrending: Math.random() > 0.7, // 随机标记为趋势
            createdAt: item.created_at || new Date().toISOString(),
            stages: item.stages?.map(stage => ({
              name: stage.name,
              description: stage.description || undefined,
              order: stage.order,
            })),
          }));
        setFeaturedRoadmaps(featuredData);
        
        // 批量获取精选路线图的封面图
        const roadmapIds = featuredData.map(item => item.id);
        if (roadmapIds.length > 0) {
          const coverImages = await batchFetchCoverImagesFromAPI(roadmapIds);
          setFeaturedCoverImageMap(coverImages);
        }
      } catch (error) {
        console.error('Failed to fetch featured roadmaps:', error);
        setFeaturedRoadmaps([]);
      } finally {
        setIsFeaturedLoading(false);
      }
    };
    
    fetchFeaturedRoadmaps();
  }, []);
  
  // Map history to roadmap format for display (过滤掉生成中的路线图)
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
      taskId: (item as any).task_id || null,
      taskStatus: (item as any).task_status || null,
      currentStep: (item as any).current_step || null,
      stages: (item as any).stages || null,
    }));
  
  // My Learning Journeys: 最多显示3个（+ Create 卡片 = 4个）
  const displayedRoadmaps = allRoadmaps.slice(0, 3);
  const hasMoreRoadmaps = allRoadmaps.length > 3;
  const hasRoadmaps = allRoadmaps.length > 0;

  // Featured Roadmaps: 最多显示4个
  const displayedFeatured = featuredRoadmaps.slice(0, 4);
  const hasMoreFeatured = featuredRoadmaps.length > 4;

  return (
    <ScrollArea className="h-full">
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Welcome Header */}
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

        {/* Section A: My Learning Journeys */}
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
            /* 单行横向滚动布局 */
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {/* Create New Button Card */}
                  <div className="w-[280px] sm:w-auto flex-shrink-0">
                    <CreateLearningCard />
                  </div>

                  {/* User's Roadmaps */}
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
                        coverImageUrl={coverImageMap.get(roadmap.id) || undefined}
                      />
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Scroll indicator for mobile */}
              {hasRoadmaps && (
                <div className="sm:hidden flex justify-center mt-2 gap-1">
                  {[...Array(Math.min(displayedRoadmaps.length + 1, 4))].map((_, i) => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-sage-200" />
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

        {/* Section B: Featured Roadmaps */}
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
            /* 单行横向滚动布局 */
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displayedFeatured.map((roadmap) => (
                    <div key={roadmap.id} className="w-[280px] sm:w-auto flex-shrink-0">
                      <FeaturedRoadmapCard 
                        roadmap={roadmap}
                        coverImageUrl={featuredCoverImageMap.get(roadmap.id) || undefined}
                      />
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Scroll indicator for mobile */}
              <div className="sm:hidden flex justify-center mt-2 gap-1">
                {[...Array(Math.min(displayedFeatured.length, 4))].map((_, i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-sage-200" />
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

        {/* Bottom Spacing */}
        <div className="h-12" />
      </div>
      
      {/* Custom scrollbar styles */}
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
