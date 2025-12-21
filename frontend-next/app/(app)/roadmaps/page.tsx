'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
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
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
import { getUserRoadmaps, deleteRoadmap } from '@/lib/api/endpoints';
import { cn } from '@/lib/utils';

type ViewMode = 'grid' | 'list';

export default function MyRoadmapsPage() {
  const { history, setHistory } = useRoadmapStore();
  const { getUserId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [roadmapToDelete, setRoadmapToDelete] = useState<string | null>(null);
  
  const itemsPerPage = viewMode === 'grid' ? 12 : 20;
  
  // Fetch user roadmaps
  useEffect(() => {
    const fetchRoadmaps = async () => {
      const userId = getUserId();
      if (!userId) {
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        const response = await getUserRoadmaps(userId);
        const historyData = response.roadmaps.map((item) => ({
          roadmap_id: item.roadmap_id,
          title: item.title,
          created_at: item.created_at,
          total_concepts: item.total_concepts,
          completed_concepts: item.completed_concepts,
          topic: item.topic || undefined,
          status: item.status || 'completed',
        }));
        setHistory(historyData as any);
      } catch (error) {
        console.error('Failed to fetch roadmaps:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchRoadmaps();
  }, [getUserId, setHistory]);
  
  // Map history to roadmap format (只包含已完成的路线图)
  const allRoadmaps: MyRoadmap[] = history
    .filter(item => item.status !== 'generating')  // 过滤掉生成中的任务
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
  
  // Pagination
  const totalPages = Math.ceil(allRoadmaps.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const displayedRoadmaps = allRoadmaps.slice(startIndex, endIndex);
  
  // Handle delete
  const handleDeleteClick = (roadmapId: string) => {
    setRoadmapToDelete(roadmapId);
    setDeleteDialogOpen(true);
  };
  
  const handleDeleteConfirm = async () => {
    if (!roadmapToDelete) return;
    
    const userId = getUserId();
    if (!userId) return;
    
      try {
        await deleteRoadmap(roadmapToDelete, userId);
        
        // Refresh the list
        const response = await getUserRoadmaps(userId);
        const historyData = response.roadmaps.map((item) => ({
          roadmap_id: item.roadmap_id,
          title: item.title,
          created_at: item.created_at,
          total_concepts: item.total_concepts,
          completed_concepts: item.completed_concepts,
          topic: item.topic || undefined,
          status: item.status || 'completed',
        }));
        setHistory(historyData as any);
      
      // Reset to page 1 if current page becomes empty
      const newTotalPages = Math.ceil(historyData.length / itemsPerPage);
      if (currentPage > newTotalPages && newTotalPages > 0) {
        setCurrentPage(newTotalPages);
      }
    } catch (error) {
      console.error('Failed to delete roadmap:', error);
      alert('删除失败，请稍后重试');
    } finally {
      setDeleteDialogOpen(false);
      setRoadmapToDelete(null);
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
          <ChevronLeft className="w-4 h-4" /> Back to Home
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <BookOpen size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                My Learning Journeys
              </h1>
              <p className="text-sm text-muted-foreground">
                {allRoadmaps.length} {allRoadmaps.length === 1 ? 'roadmap' : 'roadmaps'} in total
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
                <Plus size={16} /> New Roadmap
              </Button>
            </Link>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">Loading roadmaps...</p>
            </div>
          </div>
        ) : allRoadmaps.length === 0 ? (
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
                      showActions={true}
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

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认删除路线图？</AlertDialogTitle>
              <AlertDialogDescription>
                此路线图将被移至回收站，30 天后自动永久删除。您可以在回收站中恢复它。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteConfirm}
                className="bg-red-600 hover:bg-red-700"
              >
                删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </ScrollArea>
  );
}
