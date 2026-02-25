'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useTranslations, useFormatter } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import { ChevronLeft, Trash2, RotateCcw, AlertTriangle } from 'lucide-react';
import { useAuthStore } from '@/lib/store/auth-store';
import { roadmapsApi } from '@/lib/api/endpoints';
import type { RoadmapSummary, RoadmapHistoryItem } from '@/lib/api/endpoints';
import { getCoverImage, getGradientFallback, getTopicInitial } from '@/lib/cover-image';

// 计算剩余天数
function calculateDaysRemaining(deletedAt: string): number {
  const deleted = new Date(deletedAt);
  const now = new Date();
  const expiryDate = new Date(deleted);
  expiryDate.setDate(expiryDate.getDate() + 30); // 30 天后过期
  
  const diffMs = expiryDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  
  return Math.max(0, diffDays);
}

interface TrashItemProps {
  roadmap: RoadmapHistoryItem;
  onRestore: () => void;
  onPermanentDelete: () => void;
}

function TrashItem({ roadmap, onRestore, onPermanentDelete }: TrashItemProps) {
  const t = useTranslations('trash');
  const format = useFormatter();
  const [imageError, setImageError] = useState(false);
  const imageUrl = getCoverImage(roadmap.topic || roadmap.title);
  const gradient = getGradientFallback(roadmap.title);
  const initial = getTopicInitial(roadmap.title);
  
  const daysRemaining = roadmap.deleted_at 
    ? calculateDaysRemaining(roadmap.deleted_at) 
    : 30;
  const deletedTime = roadmap.deleted_at 
    ? format.dateTime(new Date(roadmap.deleted_at), {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : 'Unknown';

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border border-border/30 bg-background">
      {/* 封面缩略图 */}
      <div className="flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden opacity-60">
        {!imageError ? (
          <Image
            src={imageUrl}
            alt={roadmap.title}
            width={96}
            height={64}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className={`w-full h-full ${gradient.className} flex items-center justify-center`}>
            <span className={`text-lg font-serif font-bold ${gradient.text} opacity-80`}>
              {initial}
            </span>
          </div>
        )}
      </div>

      {/* 内容区域 */}
      <div className="flex-1 min-w-0">
        <h3 className="font-serif font-medium text-base text-foreground/70 truncate mb-1">
          {roadmap.title}
        </h3>
        
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground text-xs">
            {t('deletedAt')} {deletedTime}
          </span>
          <span className="text-xs text-muted-foreground/50">•</span>
          <Badge 
            variant="outline" 
            className={`text-xs ${
              daysRemaining <= 7 
                ? 'border-red-300 text-red-600 bg-red-50' 
                : 'border-amber-300 text-amber-600 bg-amber-50'
            }`}
          >
            {t('daysRemaining', { days: daysRemaining })}
          </Badge>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={onRestore}
        >
          <RotateCcw className="h-4 w-4" />
          {t('restore')}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={onPermanentDelete}
        >
          <Trash2 className="h-4 w-4" />
          {t('permanentDelete')}
        </Button>
      </div>
    </div>
  );
}

export default function TrashPage() {
  const t = useTranslations('trash');
  const { getUserId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [deletedRoadmaps, setDeletedRoadmaps] = useState<RoadmapHistoryItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [permanentDeleteDialogOpen, setPermanentDeleteDialogOpen] = useState(false);
  const [roadmapToDelete, setRoadmapToDelete] = useState<string | null>(null);
  
  const itemsPerPage = 20;
  
  // Fetch deleted roadmaps
  const fetchDeletedRoadmaps = async () => {
    try {
      setIsLoading(true);
      const response = await roadmapsApi.getMyTrash();
      setDeletedRoadmaps(response.items);
    } catch (error) {
      console.error('Failed to fetch deleted roadmaps:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDeletedRoadmaps();
  }, []);
  
  // Pagination
  const totalPages = Math.ceil(deletedRoadmaps.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const displayedRoadmaps = deletedRoadmaps.slice(startIndex, endIndex);
  
  // Handle restore
  const handleRestore = async (roadmapId: string) => {
    const userId = getUserId();
    if (!userId) return;
    
    try {
      // ✅ 不再传递userId，后端从JWT Token自动提取
      await roadmapsApi.restore(roadmapId);
      await fetchDeletedRoadmaps();
      
      // Reset to page 1 if current page becomes empty
      const newTotalPages = Math.ceil((deletedRoadmaps.length - 1) / itemsPerPage);
      if (currentPage > newTotalPages && newTotalPages > 0) {
        setCurrentPage(newTotalPages);
      }
    } catch (error) {
      console.error('Failed to restore roadmap:', error);
      alert(t('restoreFailed'));
    }
  };
  
  // Handle permanent delete
  const handlePermanentDeleteClick = (roadmapId: string) => {
    setRoadmapToDelete(roadmapId);
    setPermanentDeleteDialogOpen(true);
  };
  
  const handlePermanentDeleteConfirm = async () => {
    if (!roadmapToDelete) return;
    
    const userId = getUserId();
    if (!userId) return;
    
    try {
      // ✅ 不再传递userId，后端从JWT Token自动提取
      await roadmapsApi.permanentDelete(roadmapToDelete);
      await fetchDeletedRoadmaps();
      
      // Reset to page 1 if current page becomes empty
      const newTotalPages = Math.ceil((deletedRoadmaps.length - 1) / itemsPerPage);
      if (currentPage > newTotalPages && newTotalPages > 0) {
        setCurrentPage(newTotalPages);
      }
    } catch (error) {
      console.error('Failed to permanently delete roadmap:', error);
      alert(t('deleteFailed'));
    } finally {
      setPermanentDeleteDialogOpen(false);
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
          <ChevronLeft className="w-4 h-4" /> {t('backToHome')}
        </Link>

        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
            <Trash2 size={24} className="text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-foreground">
              {t('title')}
            </h1>
            <p className="text-sm text-muted-foreground">
              {deletedRoadmaps.length} {deletedRoadmaps.length === 1 ? t('item') : t('items')} {t('itemsInTrash')}
            </p>
          </div>
        </div>

        {/* Warning Banner */}
        {deletedRoadmaps.length > 0 && (
          <div className="flex items-start gap-3 p-4 mb-6 rounded-lg bg-amber-50 border border-amber-200">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              <p className="font-medium text-amber-900 mb-1">
                {t('warningTitle')}
              </p>
              <p className="text-amber-700">
                {t('warningDescription')}
              </p>
            </div>
          </div>
        )}

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">{t('loading')}</p>
            </div>
          </div>
        ) : deletedRoadmaps.length === 0 ? (
          <EmptyState
            icon={Trash2}
            title={t('emptyTitle')}
            description={t('emptyDescription')}
          />
        ) : (
          <>
            {/* Trash Items List */}
            <div className="space-y-3 mb-8">
              {displayedRoadmaps.map((roadmap) => (
                <TrashItem
                  key={roadmap.roadmap_id}
                  roadmap={roadmap}
                  onRestore={() => handleRestore(roadmap.roadmap_id)}
                  onPermanentDelete={() => handlePermanentDeleteClick(roadmap.roadmap_id)}
                />
              ))}
            </div>

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
                      className={`w-9 h-9 ${
                        currentPage === page ? 'bg-sage-600 hover:bg-sage-700' : ''
                      }`}
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

        {/* Permanent Delete Confirmation Dialog */}
        <AlertDialog open={permanentDeleteDialogOpen} onOpenChange={setPermanentDeleteDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="h-5 w-5" />
                {t('deleteDialogTitle')}
              </AlertDialogTitle>
              <AlertDialogDescription dangerouslySetInnerHTML={{ __html: t('deleteDialogDescription') }} />
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handlePermanentDeleteConfirm}
                className="bg-red-600 hover:bg-red-700"
              >
                {t('permanentDelete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </ScrollArea>
  );
}
