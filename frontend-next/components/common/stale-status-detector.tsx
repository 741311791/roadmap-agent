'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { RefreshCw, Loader2, AlertTriangle, Clock } from 'lucide-react';
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
 * 
 * 使用场景：
 * - 任务在生成过程中服务器崩溃
 * - 任务被手动中断
 * - WebSocket 连接断开导致状态未更新
 * - 任何导致状态"卡住"的异常情况
 * 
 * 使用示例：
 * ```tsx
 * {resourcesGenerating || resourcesPending ? (
 *   <StaleStatusDetector
 *     roadmapId={roadmapId}
 *     conceptId={concept.concept_id}
 *     contentType="resources"
 *     status={concept.resources_status}
 *     preferences={userPreferences}
 *     timeoutSeconds={120}
 *     onSuccess={() => onRetrySuccess?.()}
 *   />
 * ) : (
 *   // 正常内容显示
 * )}
 * ```
 */
export function StaleStatusDetector({
  roadmapId,
  conceptId,
  contentType,
  status,
  preferences,
  timeoutSeconds = 120, // 默认 2 分钟超时
  onSuccess,
  className,
}: StaleStatusDetectorProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isStale, setIsStale] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [quickCheckDone, setQuickCheckDone] = useState(false);

  const contentTypeLabels = {
    tutorial: { name: '教程', verb: '生成' },
    resources: { name: '学习资源', verb: '获取' },
    quiz: { name: '测验', verb: '生成' },
  };

  const label = contentTypeLabels[contentType];

  // 组件加载时立即进行快速检查
  useEffect(() => {
    const quickCheck = async () => {
      try {
        console.log('[StaleStatusDetector] 开始快速检查僵尸状态...');
        const result = await checkRoadmapStatusQuick(roadmapId);
        
        console.log('[StaleStatusDetector] 快速检查结果:', result);
        
        // 检查当前概念是否在僵尸状态列表中
        const isConceptStale = result.stale_concepts.some(
          (stale) => 
            stale.concept_id === conceptId && 
            stale.content_type === contentType
        );
        
        if (isConceptStale) {
          console.warn('[StaleStatusDetector] 检测到僵尸状态，立即显示警告');
          setIsStale(true);
        } else if (!result.has_active_task) {
          // 没有活跃任务，但概念也不在僵尸列表中
          // 可能是状态已经更新但前端未刷新
          console.log('[StaleStatusDetector] 任务已完成但概念不在僵尸列表，可能需要刷新');
        }
        
        setQuickCheckDone(true);
      } catch (error) {
        console.error('[StaleStatusDetector] 快速检查失败:', error);
        // 检查失败，降级到计时器检测
        setQuickCheckDone(true);
      }
    };
    
    quickCheck();
  }, [roadmapId, conceptId, contentType]);

  // 计时器：每秒递增（作为兜底检测）
  useEffect(() => {
    // 如果快速检查已经发现僵尸状态，不启动计时器
    if (isStale) return;
    
    const timer = setInterval(() => {
      setElapsedTime((prev) => {
        const next = prev + 1;
        // 检查是否超时（兜底机制）
        if (next >= timeoutSeconds && !isStale) {
          setIsStale(true);
          console.warn(
            `[StaleStatusDetector] 超时检测触发: ${contentType} 已处于 ${status} 状态超过 ${timeoutSeconds} 秒`
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
          'flex flex-col items-center justify-center gap-4 py-12 px-6 text-center',
          'bg-sage-50 dark:bg-sage-950/20 rounded-xl border border-sage-200 dark:border-sage-900',
          className
        )}
      >
        <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-sage-600 dark:text-sage-400 animate-spin" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-medium text-sage-800 dark:text-sage-200">
            {label.name}正在{label.verb}中
          </h3>
          <p className="text-sm text-sage-600 dark:text-sage-400">
            这可能需要几分钟时间，请稍候...
          </p>
          <div className="flex items-center justify-center gap-2 mt-3 text-xs text-sage-500">
            <Clock className="w-3 h-3" />
            <span>已等待 {formatTime(elapsedTime)}</span>
          </div>
        </div>
        {/* 进度条动画 */}
        <div className="w-48 h-1 bg-sage-200 dark:bg-sage-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-sage-500 dark:bg-sage-400 animate-pulse rounded-full transition-all duration-1000"
            style={{ width: `${Math.min((elapsedTime / timeoutSeconds) * 100, 95)}%` }}
          />
        </div>
      </div>
    );
  }

  // 超时后显示警告和重试选项
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 py-12 px-6 text-center',
        'bg-amber-50 dark:bg-amber-950/20 rounded-xl border-2 border-amber-300 dark:border-amber-800',
        className
      )}
    >
      <div className="w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
        <AlertTriangle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
      </div>
      
      <div className="space-y-2">
        <h3 className="text-lg font-medium text-amber-900 dark:text-amber-200">
          {label.name}{label.verb}超时
        </h3>
        <p className="text-sm text-amber-700 dark:text-amber-400">
          {label.name}已处于"{status === 'pending' ? '排队中' : '生成中'}"状态超过 {Math.floor(timeoutSeconds / 60)} 分钟
        </p>
        <p className="text-xs text-amber-600 dark:text-amber-500 max-w-md">
          这可能是由于后台任务异常中断。建议您重新{label.verb}{label.name}。
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-500">
        <Clock className="w-3 h-3" />
        <span>已等待 {formatTime(elapsedTime)}</span>
      </div>

      {/* 操作按钮 */}
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
            className="bg-amber-600 hover:bg-amber-700 text-white"
          />
          <Button
            variant="outline"
            size="default"
            onClick={() => setShowDetails(!showDetails)}
            className="gap-2"
          >
            {showDetails ? '隐藏详情' : '查看详情'}
          </Button>
        </div>
      ) : (
        <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
          <p className="text-xs text-amber-800 dark:text-amber-300">
            无法自动重试：缺少用户学习偏好
          </p>
        </div>
      )}

      {/* 详细信息（可折叠） */}
      {showDetails && (
        <div className="w-full mt-4 p-4 bg-amber-100 dark:bg-amber-900/30 rounded-lg text-left">
          <h4 className="text-sm font-medium text-amber-900 dark:text-amber-200 mb-2">
            诊断信息
          </h4>
          <ul className="space-y-1.5 text-xs text-amber-800 dark:text-amber-300">
            <li className="flex items-start gap-2">
              <span className="text-amber-500">•</span>
              <span><strong>路线图 ID:</strong> <code className="bg-amber-200 dark:bg-amber-800 px-1 py-0.5 rounded">{roadmapId}</code></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500">•</span>
              <span><strong>概念 ID:</strong> <code className="bg-amber-200 dark:bg-amber-800 px-1 py-0.5 rounded">{conceptId}</code></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500">•</span>
              <span><strong>当前状态:</strong> <code className="bg-amber-200 dark:bg-amber-800 px-1 py-0.5 rounded">{status}</code></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500">•</span>
              <span><strong>等待时间:</strong> {formatTime(elapsedTime)} ({elapsedTime} 秒)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500">•</span>
              <span><strong>超时阈值:</strong> {formatTime(timeoutSeconds)} ({timeoutSeconds} 秒)</span>
            </li>
          </ul>
          
          <div className="mt-3 pt-3 border-t border-amber-300 dark:border-amber-700">
            <p className="text-xs text-amber-700 dark:text-amber-400">
              <strong>可能原因：</strong>
            </p>
            <ul className="mt-1 space-y-0.5 text-xs text-amber-600 dark:text-amber-500">
              <li>• 后台生成任务被异常中断</li>
              <li>• 服务器在生成过程中重启</li>
              <li>• WebSocket 连接断开导致状态未更新</li>
              <li>• 任务队列处理异常</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
