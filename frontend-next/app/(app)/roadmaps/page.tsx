'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { EmptyState } from '@/components/common/empty-state';
import { RoadmapCard, RoadmapListItem, MyRoadmap } from '@/components/roadmap';
import { ChevronLeft, BookOpen, Plus, LayoutGrid, List } from 'lucide-react';
import { roadmapsApi } from '@/lib/api/endpoints';
import { useMyRoadmapsQuery } from '@/lib/hooks/api/use-dashboard-queries';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type ViewMode = 'grid' | 'list';

export default function MyRoadmapsPage() {
  const t = useTranslations('roadmapsList');
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [roadmapToDelete, setRoadmapToDelete] = useState<string | null>(null);
  
  const itemsPerPage = viewMode === 'grid' ? 12 : 20;

  const mapRoadmaps = (items: Awaited<ReturnType<typeof roadmapsApi.getMyRoadmaps>>['items']): MyRoadmap[] =>
    items
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
        coverImageUrl: item.cover_image_url ?? null,
      }));

  const { data, isLoading } = useMyRoadmapsQuery({
    limit: itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage,
  });

  const roadmaps = mapRoadmaps(data?.items || []);
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / itemsPerPage));
  const displayedRoadmaps = roadmaps;
  
  // Handle delete
  const handleDeleteClick = (roadmapId: string) => {
    setRoadmapToDelete(roadmapId);
    setDeleteDialogOpen(true);
  };
  
  const handleDeleteConfirm = async () => {
    if (!roadmapToDelete) return;
    
    try {
      await roadmapsApi.delete(roadmapToDelete);
      if (displayedRoadmaps.length === 1 && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      }
      await queryClient.invalidateQueries({ queryKey: ['roadmaps', 'my'] });

      toast.success('Roadmap deleted');
    } catch (error) {
      console.error('Failed to delete roadmap:', error);
      toast.error(t('deleteFailed'));
    } finally {
      setDeleteDialogOpen(false);
      setRoadmapToDelete(null);
    }
  };

  // 触发单个路线图封面图生成
  const handleGenerateCover = async (roadmapId: string) => {
    try {
      await roadmapsApi.generateCoverImage(roadmapId);
      toast.success('Cover image generation started');
    } catch {
      toast.error('Failed to start cover image generation');
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="max-w-6xl mx-auto py-8 px-6">
        {/* Back Navigation */}
        <Link
          href="/home"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> {t('backToHome')}
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <BookOpen size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                {t('title')}
              </h1>
              <p className="text-sm text-muted-foreground">
                {total} {total === 1 ? t('roadmap') : t('roadmaps')} {t('inTotal')}
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
            
            {/* Create Button */}
            <Link href="/new">
              <Button variant="sage" className="gap-2">
                <Plus size={16} /> {t('newRoadmap')}
              </Button>
            </Link>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">{t('loadingRoadmaps')}</p>
            </div>
          </div>
        ) : total === 0 ? (
          <EmptyState
            icon={BookOpen}
            title={t('noRoadmapsYet')}
            description={t('createFirstRoadmap')}
            action={{
              label: t('createRoadmap'),
              onClick: () => {
                window.location.href = '/new';
              },
            }}
          />
        ) : (
          <>
            {/* Grid View */}
            {viewMode === 'grid' && (
              <div className="grid grid-cols-1 sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4 mb-8">
                {displayedRoadmaps.map((roadmap) => (
                  <div key={roadmap.id} className="w-full">
                    <RoadmapCard
                      roadmap={roadmap}
                      type="my"
                      onDelete={handleDeleteClick}
                      onGenerateCover={handleGenerateCover}
                      showActions={true}
                      coverImageUrl={(roadmap as any).coverImageUrl ?? null}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* List View */}
            {viewMode === 'list' && (
              <div className="space-y-3 mb-8">
                {displayedRoadmaps.map((roadmap) => (
                  <RoadmapListItem
                    key={roadmap.id}
                    roadmap={roadmap}
                    onDelete={handleDeleteClick}
                    onGenerateCover={handleGenerateCover}
                    coverImageUrl={(roadmap as any).coverImageUrl ?? null}
                  />
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
                  {t('previous')}
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
                  {t('next')}
                </Button>
              </div>
            )}
          </>
        )}

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('deleteConfirmTitle')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('deleteConfirmDescription')}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteConfirm}
                className="bg-red-600 hover:bg-red-700"
              >
                {t('delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </ScrollArea>
  );
}
