'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Check, X, Loader2, Clock, BookOpen } from 'lucide-react';

interface HumanReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskId: string;
  roadmapId: string;
  roadmapTitle: string;
  stagesCount: number;
  onApprove: () => Promise<void>;
  onReject: (feedback: string) => Promise<void>;
  isSubmitting?: boolean;
}

/**
 * HumanReviewDialog - 人工审核对话框
 * 
 * 当工作流进入 human_review 阶段时弹出，
 * 允许用户批准或拒绝路线图框架。
 */
export function HumanReviewDialog({
  open,
  onOpenChange,
  taskId,
  roadmapId,
  roadmapTitle,
  stagesCount,
  onApprove,
  onReject,
  isSubmitting = false,
}: HumanReviewDialogProps) {
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const handleApprove = async () => {
    await onApprove();
    onOpenChange(false);
  };

  const handleReject = async () => {
    if (!showFeedback) {
      setShowFeedback(true);
      return;
    }
    await onReject(feedback);
    setFeedback('');
    setShowFeedback(false);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setShowFeedback(false);
    setFeedback('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-500" />
            人工审核
          </DialogTitle>
          <DialogDescription>
            请审核生成的路线图框架，确认后将开始生成学习内容
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Roadmap Info */}
          <div className="p-4 bg-muted/50 rounded-lg space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">路线图标题</p>
              <p className="font-medium">{roadmapTitle}</p>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="secondary" className="gap-1">
                <Clock className="w-3 h-3" />
                {stagesCount} 个阶段
              </Badge>
              <span className="text-xs text-muted-foreground">
                ID: {roadmapId.slice(0, 20)}...
              </span>
            </div>
          </div>

          {/* Feedback Input (shown when rejecting) */}
          {showFeedback && (
            <div className="space-y-2">
              <p className="text-sm font-medium">请说明需要修改的内容：</p>
              <Textarea
                placeholder="例如：希望增加更多实践项目、减少理论内容比例..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={4}
                className="resize-none"
              />
              <p className="text-xs text-muted-foreground">
                您的反馈将帮助我们优化路线图结构
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {showFeedback ? (
            <>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isSubmitting}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={isSubmitting || !feedback.trim()}
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <X className="w-4 h-4 mr-2" />
                )}
                提交修改意见
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleReject}
                disabled={isSubmitting}
              >
                <X className="w-4 h-4 mr-2" />
                需要修改
              </Button>
              <Button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="bg-green-600 hover:bg-green-700"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                批准并继续
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

