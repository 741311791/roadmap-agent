'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Check, X, Loader2, Clock, BookOpen, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { approveRoadmap } from '@/lib/api/endpoints';

interface HumanReviewCardProps {
  taskId: string;
  roadmapId: string;
  roadmapTitle: string;
  stagesCount: number;
  isActive: boolean; // current_step === "human_review"
  onReviewComplete?: () => void;
}

/**
 * HumanReviewCard - 人工审核卡片（扁平式设计）
 * 
 * 当工作流进入 human_review 阶段时在时间线中激活，
 * 允许用户批准或拒绝路线图框架。
 * 
 * 状态流转：
 * - waiting: 等待用户操作
 * - submitting: 正在提交审核结果
 * - approved: 已批准（显示成功状态）
 * - rejected: 已拒绝（显示反馈提交状态）
 */
export function HumanReviewCard({
  taskId,
  roadmapId,
  roadmapTitle,
  stagesCount,
  isActive,
  onReviewComplete,
}: HumanReviewCardProps) {
  const [status, setStatus] = useState<'waiting' | 'submitting' | 'approved' | 'rejected'>('waiting');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 跟踪上一次的 isActive 状态，用于检测重新激活
  const prevIsActiveRef = useRef<boolean>(false);
  
  /**
   * 当卡片重新激活时，重置审核状态
   * 场景：用户reject后，编辑完成，工作流再次回到review节点
   */
  useEffect(() => {
    // 检测：从非激活状态 → 激活状态
    const isReactivating = !prevIsActiveRef.current && isActive;
    
    // 当重新激活且已完成审核时，重置为 waiting
    if (isReactivating && (status === 'approved' || status === 'rejected')) {
      console.log('[HumanReviewCard] Resetting status to waiting on reactivation');
      setStatus('waiting');
      setFeedback('');
      setShowFeedback(false);
      setError(null);
    }
    
    prevIsActiveRef.current = isActive;
  }, [isActive, status]);

  const handleApprove = async () => {
    try {
      setStatus('submitting');
      setError(null);
      
      await approveRoadmap(taskId, true);
      
      setStatus('approved');
      onReviewComplete?.();
    } catch (err: any) {
      console.error('Failed to approve roadmap:', err);
      setError(err.message || 'Failed to approve roadmap');
      setStatus('waiting');
    }
  };

  const handleReject = async () => {
    if (!showFeedback) {
      setShowFeedback(true);
      return;
    }

    if (!feedback.trim()) {
      setError('Please provide feedback for rejection');
      return;
    }

    try {
      setStatus('submitting');
      setError(null);
      
      await approveRoadmap(taskId, false, feedback);
      
      // 反馈提交成功后，重置为 waiting 状态，让工作流自然过渡
      // 不显示 'rejected' 状态的确认卡片
      setStatus('waiting');
      setShowFeedback(false);
      setFeedback('');
      onReviewComplete?.();
    } catch (err: any) {
      console.error('Failed to reject roadmap:', err);
      setError(err.message || 'Failed to submit feedback');
      setStatus('waiting');
    }
  };

  const handleCancel = () => {
    setShowFeedback(false);
    setFeedback('');
    setError(null);
  };

  // 已批准状态
  if (status === 'approved') {
    return (
      <Card className="border-2 border-accent/30 bg-accent/5">
        <CardContent className="py-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
              <Check className="w-5 h-5 text-accent" />
            </div>
            <div className="flex-1 space-y-1">
              <h3 className="font-medium text-foreground">Roadmap Approved</h3>
              <p className="text-sm text-accent/80">
                The roadmap framework has been approved. Content generation will continue automatically.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // 移除 rejected 状态的显示
  // 用户提交反馈后，直接让工作流过渡到下一步，不显示中间确认卡片

  // 等待审核状态（激活状态）
  return (
    <Card
      className={cn(
        'border-2 transition-all',
        isActive ? 'border-accent bg-accent/5 shadow-lg' : 'border-border bg-card',
      )}
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-accent" />
          Human Review Required
        </CardTitle>
        <CardDescription>
          Please review the generated roadmap framework. Once approved, content generation will begin.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 路线图信息展示 */}
        <div className="p-4 bg-muted/50 rounded-lg space-y-3">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Roadmap Title</p>
            <p className="font-medium truncate" title={roadmapTitle}>{roadmapTitle}</p>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant="secondary" className="gap-1">
              <Clock className="w-3 h-3" />
              {stagesCount} stages
            </Badge>
            <span className="text-xs text-muted-foreground truncate" title={roadmapId}>
              ID: {roadmapId.substring(0, 20)}...
            </span>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* 反馈输入框（拒绝时显示） */}
        {showFeedback && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Please describe the changes you need:</p>
            <Textarea
              placeholder="e.g., add more projects, reduce theory-heavy content..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={4}
              className="resize-none"
              disabled={status === 'submitting'}
            />
            <p className="text-xs text-muted-foreground">
              Your feedback will help us refine the roadmap structure.
            </p>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center justify-end gap-2 pt-2">
          {showFeedback ? (
            <>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={status === 'submitting'}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={status === 'submitting' || !feedback.trim()}
              >
                {status === 'submitting' ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <X className="w-4 h-4 mr-2" />
                )}
                Submit Changes
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleReject}
                disabled={status === 'submitting'}
              >
                <X className="w-4 h-4 mr-2" />
                Needs Changes
              </Button>
              <Button
                onClick={handleApprove}
                disabled={status === 'submitting'}
                className="bg-accent hover:bg-accent/90 text-accent-foreground"
              >
                {status === 'submitting' ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Approve and Continue
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

