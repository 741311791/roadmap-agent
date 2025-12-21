'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { EmptyState } from '@/components/common/empty-state';
import { RoadmapCard, MyRoadmap } from '@/components/roadmap';
import { ChevronLeft, TrendingUp, LayoutGrid, List } from 'lucide-react';
import { getFeaturedRoadmaps } from '@/lib/api/endpoints';
import { cn } from '@/lib/utils';

type ViewMode = 'grid' | 'list';

/**
 * Explore 页面
 * 
 * 展示精选的学习路线图，帮助用户发现优质内容
 */
export default function ExplorePage() {
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [currentPage, setCurrentPage] = useState(1);
  const [featuredRoadmaps, setFeaturedRoadmaps] = useState<MyRoadmap[]>([]);
  
  const itemsPerPage = viewMode === 'grid' ? 12 : 20;
  
  // Fetch featured roadmaps
  useEffect(() => {
    const fetchFeaturedRoadmaps = async () => {
      try {
        setIsLoading(true);
        const response = await getFeaturedRoadmaps(100, 0); // 获取所有精选路线图
        const featuredData: MyRoadmap[] = response.roadmaps
          .filter(item => item.status === 'completed') // 只显示已完成的路线图
          .map((item) => ({
            id: item.roadmap_id,
            title: item.title,
            status: item.status || 'completed',
            totalConcepts: item.total_concepts || 0,
            completedConcepts: item.completed_concepts || 0,
            totalHours: 0,
            lastAccessedAt: item.created_at || new Date().toISOString(),
            topic: item.topic || item.title.toLowerCase(),
          }));
        setFeaturedRoadmaps(featuredData);
      } catch (error) {
        console.error('Failed to fetch featured roadmaps:', error);
        setFeaturedRoadmaps([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchFeaturedRoadmaps();
  }, []);
  
  // Pagination
  const totalPages = Math.ceil(featuredRoadmaps.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const displayedRoadmaps = featuredRoadmaps.slice(startIndex, endIndex);

  return (
    <ScrollArea className="h-full">
      <div className="max-w-6xl mx-auto py-8 px-6">
        {/* Back Navigation */}
        <Link
          href="/home"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Home
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <TrendingUp size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                Explore Featured Roadmaps
              </h1>
              <p className="text-sm text-muted-foreground">
                {featuredRoadmaps.length} {featuredRoadmaps.length === 1 ? 'roadmap' : 'roadmaps'} available
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 p-1 bg-secondary/50 rounded-lg">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  setViewMode('grid');
                  setCurrentPage(1);
                }}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  setViewMode('list');
                  setCurrentPage(1);
                }}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">Loading featured roadmaps...</p>
            </div>
          </div>
        ) : featuredRoadmaps.length === 0 ? (
          <EmptyState
            icon={TrendingUp}
            title="No featured roadmaps available"
            description="Check back later for curated learning paths."
            action={{
              label: 'Go Back',
              onClick: () => {
                window.location.href = '/home';
              },
            }}
          />
        ) : (
          <>
            {/* Grid View */}
            {viewMode === 'grid' && (
              <div className="grid grid-cols-1 sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4 mb-8">
                {displayedRoadmaps.map((roadmap) => (
                  <RoadmapCard
                    key={roadmap.id}
                    roadmap={roadmap}
                    type="my"
                    showActions={false}
                  />
                ))}
              </div>
            )}

            {/* List View */}
            {viewMode === 'list' && (
              <div className="space-y-3 mb-8">
                {displayedRoadmaps.map((roadmap) => (
                  <Link
                    key={roadmap.id}
                    href={`/roadmap/${roadmap.id}`}
                    className="block p-4 bg-card border border-border rounded-lg hover:shadow-lg transition-all hover:-translate-y-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-serif font-medium text-foreground mb-1 hover:text-sage-700 transition-colors">
                          {roadmap.title}
                        </h3>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>{roadmap.totalConcepts} concepts</span>
                          <span>•</span>
                          <span>{roadmap.topic}</span>
                        </div>
                      </div>
                      <div className="text-xs text-sage-600 font-medium bg-sage-50 px-3 py-1 rounded-full">
                        View
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <Button
                      key={page}
                      variant={currentPage === page ? 'default' : 'ghost'}
                      size="sm"
                      className={cn(
                        'w-9 h-9',
                        currentPage === page && 'bg-sage-600 hover:bg-sage-700'
                      )}
                      onClick={() => setCurrentPage(page)}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </ScrollArea>
  );
}

