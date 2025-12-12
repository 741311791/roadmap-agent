'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { RefreshCw, Loader2, AlertCircle, Clock, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { RetryContentButton } from './retry-content-button';
import { checkRoadmapStatusQuick } from '@/lib/api/endpoints';
import type { LearningPreferences } from '@/types/generated/models';
import type { RetryContentResponse } from '@/lib/api/endpoints';

type ContentType = 'tutorial' | 'resources' | 'quiz';

interface StaleStatusDetectorProps {
  /** 路线图 ID */
  roadmapId: string;
  /** 概念 ID */
  conceptId: string;
  /** 内容类型 */
  contentType: ContentType;
  /** 当前状态 */
  status: 'pending' | 'generating';
  /** 用户学习偏好 */
  preferences?: LearningPreferences;
  /** 超时时间（秒），默认 120 秒 */
  timeoutSeconds?: number;
  /** 重试成功回调 */
  onSuccess?: (response: RetryContentResponse) => void;
  /** 自定义样式 */
  className?: string;
}

/**
 * StaleStatusDetector - 僵尸状态检测器
 * 
 * 用于检测 pending/generating 状态是否已经过期（可能由于任务异常中断）。
 * 如果超时，会提示用户重新生成内容。
 */
export function StaleStatusDetector({
  roadmapId,
  conceptId,
  contentType,
  status,
  preferences,
  timeoutSeconds = 120,
  onSuccess,
  className,
}: StaleStatusDetectorProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isStale, setIsStale] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [quickCheckDone, setQuickCheckDone] = useState(false);

  const contentTypeLabels = {
    tutorial: { name: 'Tutorial', verb: 'Generating', gerund: 'generation' },
    resources: { name: 'Learning Resources', verb: 'Fetching', gerund: 'fetch' },
    quiz: { name: 'Quiz', verb: 'Generating', gerund: 'generation' },
  };

  const label = contentTypeLabels[contentType];

  // 组件加载时立即进行快速检查
  useEffect(() => {
    const quickCheck = async () => {
      try {
        console.log('[StaleStatusDetector] Starting quick status check...');
        const result = await checkRoadmapStatusQuick(roadmapId);
        
        console.log('[StaleStatusDetector] Quick check result:', result);
        
        // 检查当前概念是否在僵尸状态列表中
        const isConceptStale = result.stale_concepts.some(
          (stale) => 
            stale.concept_id === conceptId && 
            stale.content_type === contentType
        );
        
        if (isConceptStale) {
          console.warn('[StaleStatusDetector] Stale status detected');
          setIsStale(true);
        } else if (!result.has_active_task) {
          console.log('[StaleStatusDetector] No active task, status might need refresh');
        }
        
        setQuickCheckDone(true);
      } catch (error) {
        console.error('[StaleStatusDetector] Quick check failed:', error);
        setQuickCheckDone(true);
      }
    };
    
    quickCheck();
  }, [roadmapId, conceptId, contentType]);

  // 计时器：每秒递增（作为兜底检测）
  useEffect(() => {
    if (isStale) return;
    
    const timer = setInterval(() => {
      setElapsedTime((prev) => {
        const next = prev + 1;
        if (next >= timeoutSeconds && !isStale) {
          setIsStale(true);
          console.warn(
            `[StaleStatusDetector] Timeout detected: ${contentType} in ${status} for ${timeoutSeconds}s`
          );
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [contentType, status, timeoutSeconds, isStale]);

  // 格式化时间显示
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // 如果未超时，显示正常加载状态
  if (!isStale) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-6 py-16 px-6 text-center',
          'bg-gradient-to-br from-sage-50 to-sage-100/50 dark:from-sage-950/20 dark:to-sage-900/10',
          'rounded-2xl border border-sage-200/50 dark:border-sage-800/50 shadow-sm',
          className
        )}
      >
        {/* Loading Icon */}
        <div className="relative">
          <div className="absolute inset-0 bg-sage-400/20 dark:bg-sage-600/20 rounded-full blur-xl animate-pulse" />
          <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-sage-100 to-sage-200 dark:from-sage-900/50 dark:to-sage-800/50 flex items-center justify-center shadow-lg">
            <Loader2 className="w-10 h-10 text-sage-600 dark:text-sage-400 animate-spin" />
          </div>
        </div>

        {/* Message */}
        <div className="space-y-2 max-w-md">
          <h3 className="text-xl font-semibold text-sage-900 dark:text-sage-100">
            {label.verb} {label.name}
          </h3>
          <p className="text-sm text-sage-600 dark:text-sage-400 leading-relaxed">
            This may take a few moments. Please wait while we prepare your content...
          </p>
        </div>

        {/* Timer */}
        <div className="flex items-center gap-2 px-4 py-2 bg-sage-100/50 dark:bg-sage-900/30 rounded-full">
          <Clock className="w-4 h-4 text-sage-500 dark:text-sage-400" />
          <span className="text-sm font-medium text-sage-700 dark:text-sage-300">
            {formatTime(elapsedTime)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full max-w-xs">
          <div className="h-1.5 bg-sage-200 dark:bg-sage-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sage-500 to-sage-600 dark:from-sage-400 dark:to-sage-500 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${Math.min((elapsedTime / timeoutSeconds) * 100, 95)}%` }}
            />
          </div>
        </div>

        {/* Hint */}
        <p className="text-xs text-sage-500 dark:text-sage-500 flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5" />
          Status updates are delivered in real-time
        </p>
      </div>
    );
  }

  // 超时后显示警告和重试选项
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-6 py-16 px-6 text-center',
        'bg-gradient-to-br from-red-50 to-orange-50/50 dark:from-red-950/20 dark:to-orange-950/10',
        'rounded-2xl border-2 border-red-200/70 dark:border-red-800/50 shadow-lg',
        className
      )}
    >
      {/* Warning Icon */}
      <div className="relative">
        <div className="absolute inset-0 bg-red-400/20 dark:bg-red-600/20 rounded-full blur-xl animate-pulse" />
        <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-red-100 to-orange-100 dark:from-red-900/50 dark:to-orange-900/50 flex items-center justify-center shadow-lg">
          <AlertCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
        </div>
      </div>
      
      {/* Message */}
      <div className="space-y-3 max-w-md">
        <h3 className="text-xl font-semibold text-red-900 dark:text-red-100">
          {label.name} {label.gerund.charAt(0).toUpperCase() + label.gerund.slice(1)} Timeout
        </h3>
        <p className="text-sm text-red-700 dark:text-red-300 leading-relaxed">
          The {label.name.toLowerCase()} has been in "{status === 'pending' ? 'pending' : 'generating'}" state for over {Math.floor(timeoutSeconds / 60)} minutes.
        </p>
        <p className="text-xs text-red-600 dark:text-red-400">
          This may be due to a background task interruption. We recommend retrying the {label.gerund}.
        </p>
      </div>

      {/* Timer Badge */}
      <div className="flex items-center gap-2 px-4 py-2 bg-red-100/50 dark:bg-red-900/30 rounded-full">
        <Clock className="w-4 h-4 text-red-500 dark:text-red-400" />
        <span className="text-sm font-medium text-red-700 dark:text-red-300">
          Waited {formatTime(elapsedTime)}
        </span>
      </div>

      {/* Action Buttons */}
      {preferences ? (
        <div className="flex items-center gap-3 mt-2">
          <RetryContentButton
            roadmapId={roadmapId}
            conceptId={conceptId}
            contentType={contentType}
            preferences={preferences}
            onSuccess={onSuccess}
            variant="default"
            size="default"
            className="bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white shadow-md"
            showLabel={true}
          />
          <Button
            variant="outline"
            size="default"
            onClick={() => setShowDetails(!showDetails)}
            className="gap-2 border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            {showDetails ? 'Hide Details' : 'View Details'}
          </Button>
        </div>
      ) : (
        <div className="p-4 bg-red-100 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-200">
            Unable to retry: Missing user preferences
          </p>
        </div>
      )}

      {/* Diagnostic Details (Collapsible) */}
      {showDetails && (
        <div className="w-full mt-4 p-5 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 text-left">
          <h4 className="text-sm font-semibold text-red-900 dark:text-red-100 mb-3 flex items-center gap-2">
            <Info className="w-4 h-4" />
            Diagnostic Information
          </h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-start gap-2">
              <span className="text-red-500 font-bold">•</span>
              <span className="text-red-800 dark:text-red-200">
                <strong>Roadmap ID:</strong> <code className="ml-1 bg-red-100 dark:bg-red-800/50 px-2 py-0.5 rounded font-mono">{roadmapId}</code>
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-500 font-bold">•</span>
              <span className="text-red-800 dark:text-red-200">
                <strong>Concept ID:</strong> <code className="ml-1 bg-red-100 dark:bg-red-800/50 px-2 py-0.5 rounded font-mono">{conceptId}</code>
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-500 font-bold">•</span>
              <span className="text-red-800 dark:text-red-200">
                <strong>Current Status:</strong> <code className="ml-1 bg-red-100 dark:bg-red-800/50 px-2 py-0.5 rounded font-mono">{status}</code>
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-500 font-bold">•</span>
              <span className="text-red-800 dark:text-red-200">
                <strong>Wait Time:</strong> {formatTime(elapsedTime)} ({elapsedTime}s)
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-500 font-bold">•</span>
              <span className="text-red-800 dark:text-red-200">
                <strong>Timeout Threshold:</strong> {formatTime(timeoutSeconds)} ({timeoutSeconds}s)
              </span>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-red-200 dark:border-red-800">
            <p className="text-xs font-semibold text-red-800 dark:text-red-200 mb-2">
              Possible Causes:
            </p>
            <ul className="space-y-1 text-xs text-red-700 dark:text-red-300">
              <li className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5">→</span>
                <span>Background generation task was interrupted</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5">→</span>
                <span>Server restarted during generation</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5">→</span>
                <span>WebSocket connection lost</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5">→</span>
                <span>Task queue processing error</span>
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
