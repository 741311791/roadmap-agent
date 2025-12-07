'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Loader2, BookOpen, Library, HelpCircle } from 'lucide-react';
import { retryFailedContent, type RetryFailedRequest } from '@/lib/api/endpoints';
import type { LearningPreferences } from '@/types/generated/models';

interface FailedStats {
  tutorial: number;
  resources: number;
  quiz: number;
}

interface RetryFailedButtonProps {
  roadmapId: string;
  userId: string;
  preferences: LearningPreferences;
  failedStats: FailedStats;
  onRetryStarted?: (taskId: string) => void;
  onRetryCompleted?: () => void;
  className?: string;
}

type ContentType = 'tutorial' | 'resources' | 'quiz';

const CONTENT_TYPE_INFO: Record<ContentType, { label: string; icon: React.ReactNode }> = {
  tutorial: { label: 'Tutorials', icon: <BookOpen className="w-4 h-4" /> },
  resources: { label: 'Resources', icon: <Library className="w-4 h-4" /> },
  quiz: { label: 'Quizzes', icon: <HelpCircle className="w-4 h-4" /> },
};

/**
 * RetryFailedButton - 重试失败任务按钮
 * 
 * 显示失败统计，允许用户选择要重试的内容类型
 */
export function RetryFailedButton({
  roadmapId,
  userId,
  preferences,
  failedStats,
  onRetryStarted,
  onRetryCompleted,
  className,
}: RetryFailedButtonProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<ContentType[]>(['tutorial', 'resources', 'quiz']);

  const totalFailed = failedStats.tutorial + failedStats.resources + failedStats.quiz;

  // 如果没有失败项，不显示按钮
  if (totalFailed === 0) {
    return null;
  }

  const toggleType = (type: ContentType) => {
    setSelectedTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const getSelectedCount = () => {
    return selectedTypes.reduce((sum, type) => sum + failedStats[type], 0);
  };

  const handleRetry = async () => {
    if (selectedTypes.length === 0) return;

    setIsSubmitting(true);
    try {
      const request: RetryFailedRequest = {
        user_id: userId,
        preferences,
        content_types: selectedTypes,
      };
      
      const result = await retryFailedContent(roadmapId, request);
      
      if (result.task_id) {
        onRetryStarted?.(result.task_id);
      }
      
      setOpen(false);
    } catch (error) {
      console.error('Failed to start retry:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={className}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry failed items
          <Badge variant="destructive" className="ml-2">
            {totalFailed}
          </Badge>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-blue-500" />
            Retry failed items
          </DialogTitle>
          <DialogDescription>
            Select content types to regenerate. Successful content stays untouched.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Content type selection */}
          <div className="space-y-3">
            {(Object.keys(CONTENT_TYPE_INFO) as ContentType[]).map((type) => {
              const count = failedStats[type];
              const info = CONTENT_TYPE_INFO[type];
              const isSelected = selectedTypes.includes(type);
              const isDisabled = count === 0;

              return (
                <div
                  key={type}
                  className={`
                    flex items-center justify-between p-3 rounded-lg border
                    ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-muted/50'}
                    ${isSelected && !isDisabled ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20' : ''}
                  `}
                  onClick={() => !isDisabled && toggleType(type)}
                >
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={isSelected && !isDisabled}
                      disabled={isDisabled}
                      onCheckedChange={() => toggleType(type)}
                    />
                    <div className="flex items-center gap-2">
                      {info.icon}
                      <span className="font-medium">{info.label}</span>
                    </div>
                  </div>
                  <Badge variant={count > 0 ? 'destructive' : 'secondary'}>
                    {count} failed
                  </Badge>
                </div>
              );
            })}
          </div>

          {/* Summary */}
          <div className="p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              Will retry <span className="font-semibold text-foreground">{getSelectedCount()}</span> failed items
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleRetry}
            disabled={isSubmitting || selectedTypes.length === 0 || getSelectedCount() === 0}
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Start retry
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

