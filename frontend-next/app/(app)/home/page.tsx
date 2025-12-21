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
import { ScrollArea } from '@/components/ui/scroll-area';
import { EmptyState } from '@/components/common/empty-state';
import { RoadmapCard, FeaturedRoadmapCard, MyRoadmap, FeaturedRoadmap } from '@/components/roadmap';
import { Button } from '@/components/ui/button';
import {
  BookOpen,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Plus,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { getUserRoadmaps, getFeaturedRoadmaps } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/store/auth-store';

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
            View All
            <ArrowRight size={16} />
          </Link>
        </Button>
      )}
    </div>
  );
}

// Main Home Page Component
export default function HomePage() {
  const { history, setHistory } = useRoadmapStore();
  const { getUserId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [featuredRoadmaps, setFeaturedRoadmaps] = useState<FeaturedRoadmap[]>([]);
  const [isFeaturedLoading, setIsFeaturedLoading] = useState(true);
  
  // Fetch user roadmaps on mount
  useEffect(() => {
    const fetchRoadmaps = async () => {
      const userId = getUserId();
      if (!userId) {
        console.error('[Home] No user ID');
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        const response = await getUserRoadmaps(userId);
        // Map API response to store format
        const historyData = response.roadmaps.map((item) => {
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
          };
        });
        setHistory(historyData as any);
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
        const response = await getFeaturedRoadmaps(8, 0); // 获取8个，以便判断是否需要 View All
        const featuredData: FeaturedRoadmap[] = response.roadmaps
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
  const allRoadmaps: MyRoadmap[] = history
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
            <span className="text-sm font-medium">Welcome back</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground mb-2">
            Continue Your Learning Journey
          </h1>
          <p className="text-base text-muted-foreground max-w-2xl">
            Pick up where you left off or explore featured roadmaps from the community.
          </p>
        </div>

        {/* Section A: My Learning Journeys */}
        <section className="mb-16">
          <SectionHeader
            icon={BookOpen}
            title="My Learning Journeys"
            subtitle={hasRoadmaps ? `${allRoadmaps.length} ${allRoadmaps.length === 1 ? 'roadmap' : 'roadmaps'}` : undefined}
            showViewAll={hasMoreRoadmaps}
            viewAllHref="/roadmaps"
          />

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">Loading roadmaps...</p>
              </div>
            </div>
          ) : hasRoadmaps ? (
            /* 单行横向滚动布局 */
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {/* Create New Button Card */}
                  <Link href="/new" className="group block w-[280px] sm:w-auto flex-shrink-0">
                    <div className="relative w-full overflow-hidden rounded-xl border-2 border-dashed border-sage-300 bg-card shadow-lg transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 hover:border-sage-500 h-full">
                      {/* 顶部装饰区域 - 与CoverImage保持相同比例 */}
                      <div className="aspect-[16/9] relative overflow-hidden bg-gradient-to-br from-sage-50 via-white to-sage-100">
                        {/* 背景装饰 */}
                        <div className="absolute inset-0 opacity-30">
                          <div className="absolute top-0 left-0 w-24 h-24 bg-sage-300 rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2 group-hover:scale-150 transition-transform duration-700" />
                          <div className="absolute bottom-0 right-0 w-24 h-24 bg-sage-400 rounded-full blur-3xl transform translate-x-1/2 translate-y-1/2 group-hover:scale-150 transition-transform duration-700" />
                        </div>
                        
                        {/* 居中的图标 */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-sage-100 to-sage-200 flex items-center justify-center group-hover:from-sage-200 group-hover:to-sage-300 transition-all duration-300 shadow-lg group-hover:shadow-xl group-hover:scale-110">
                            <Plus size={24} className="text-sage-600 group-hover:text-sage-700 transition-colors" />
                          </div>
                        </div>
                      </div>

                      {/* 底部内容区域 */}
                      <div className="p-4 bg-white/95 backdrop-blur-sm">
                        {/* 标题区域 - 与RoadmapCard对齐 */}
                        <div className="flex items-start gap-2 mb-2">
                          <div className="w-3.5 h-3.5 opacity-0" /> {/* 占位符，对齐Sparkles图标 */}
                          <h3 className="font-serif font-medium text-sm text-center text-foreground group-hover:text-sage-700 transition-colors min-h-[40px] flex-1 flex items-center justify-center">
                            Create New Roadmap
                          </h3>
                        </div>
                        
                        {/* 副标题区域 - 对齐进度条区域 */}
                        <div className="space-y-2 mb-3">
                          <div className="text-center">
                            <p className="text-[10px] text-muted-foreground">
                              Start your learning journey
                            </p>
                          </div>
                          {/* 占位符，保持与进度条相同的高度 */}
                          <div className="h-2 opacity-0" />
                        </div>
                        
                        {/* 底部占位区域 - 对齐状态栏 */}
                        <div className="flex items-center justify-between opacity-0">
                          <span className="text-[10px] px-2 py-0.5">placeholder</span>
                          <span className="text-[10px]">placeholder</span>
                        </div>
                      </div>
                    </div>
                  </Link>

                  {/* User's Roadmaps */}
                  {displayedRoadmaps.map((roadmap) => (
                    <div key={roadmap.id} className="w-[280px] sm:w-auto flex-shrink-0">
                      <RoadmapCard
                        roadmap={roadmap}
                        type="my"
                        showActions={false}
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
              title="No roadmaps yet"
              description="Create your first personalized learning roadmap to get started."
              action={{
                label: 'Create Roadmap',
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
            title="Featured Roadmaps"
            subtitle="Discover curated learning paths from the community"
            showViewAll={hasMoreFeatured}
            viewAllHref="/explore"
          />

          {isFeaturedLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <div className="w-10 h-10 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">Loading featured roadmaps...</p>
              </div>
            </div>
          ) : displayedFeatured.length > 0 ? (
            /* 单行横向滚动布局 */
            <div className="relative -mx-4 px-4 sm:mx-0 sm:px-0">
              <div className="overflow-x-auto overflow-y-visible pb-4 scrollbar-hide">
                <div className="flex gap-4 min-w-max sm:min-w-0 sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displayedFeatured.map((roadmap) => (
                    <div key={roadmap.id} className="w-[280px] sm:w-auto flex-shrink-0">
                      <FeaturedRoadmapCard roadmap={roadmap} />
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
              <p className="text-sm text-muted-foreground">No featured roadmaps available yet</p>
              <p className="text-xs text-muted-foreground mt-1">Check back soon for curated content!</p>
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
