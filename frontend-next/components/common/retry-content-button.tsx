'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { RefreshCw, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { 
  retryTutorial, 
  retryResources, 
  retryQuiz,
  type RetryContentRequest,
  type RetryContentResponse,
} from '@/lib/api/endpoints';
import type { LearningPreferences } from '@/types/generated/models';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { TaskWebSocket } from '@/lib/api/websocket';

type ContentType = 'tutorial' | 'resources' | 'quiz';

interface RetryContentButtonProps {
  /** 路线图 ID */
  roadmapId: string;
  /** 概念 ID */
  conceptId: string;
  /** 内容类型 */
  contentType: ContentType;
  /** 用户学习偏好 */
  preferences: LearningPreferences;
  /** 重试成功回调 */
  onSuccess?: (response: RetryContentResponse) => void;
  /** 重试失败回调 */
  onError?: (error: Error) => void;
  /** 自定义样式 */
  className?: string;
  /** 按钮变体 */
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  /** 按钮尺寸 */
  size?: 'default' | 'sm' | 'lg' | 'icon';
  /** 是否显示文字 */
  showLabel?: boolean;
}

const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  tutorial: '重新生成教程',
  resources: '重新获取资源',
  quiz: '重新生成测验',
};

/**
 * RetryContentButton - 单概念内容重试按钮
 * 
 * 用于在教程/资源/测验生成失败时显示，允许用户重新生成该内容。
 * 
 * 使用示例：
 * ```tsx
 * <RetryContentButton
 *   roadmapId="xxx"
 *   conceptId="yyy"
 *   contentType="tutorial"
 *   preferences={userPreferences}
 *   onSuccess={(res) => console.log('重试成功', res)}
 * />
 * ```
 */
export function RetryContentButton({
  roadmapId,
  conceptId,
  contentType,
  preferences,
  onSuccess,
  onError,
  className,
  variant = 'outline',
  size = 'sm',
  showLabel = true,
}: RetryContentButtonProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const { updateConceptStatus } = useRoadmapStore();
  const wsRef = useRef<TaskWebSocket | null>(null);

  // 清理 WebSocket 连接
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    };
  }, []);

  const handleRetry = async () => {
    setIsRetrying(true);
    
    // 乐观更新：立即将状态设置为 'generating'
    const statusKey = contentType === 'tutorial' 
      ? 'tutorial_status' 
      : contentType === 'resources' 
        ? 'resources_status' 
        : 'quiz_status';
    
    updateConceptStatus(conceptId, { [statusKey]: 'generating' });
    console.log(`[RetryContentButton] 乐观更新状态: ${contentType} -> generating`);
    
    try {
      const request: RetryContentRequest = { preferences };
      
      let response: RetryContentResponse;
      
      switch (contentType) {
        case 'tutorial':
          response = await retryTutorial(roadmapId, conceptId, request);
          break;
        case 'resources':
          response = await retryResources(roadmapId, conceptId, request);
          break;
        case 'quiz':
          response = await retryQuiz(roadmapId, conceptId, request);
          break;
      }
      
      if (response.success) {
        const taskId = response.data?.task_id as string | undefined;
        
        // 如果后端返回了 task_id，订阅 WebSocket 实时更新
        if (taskId) {
          console.log(`[RetryContentButton] 订阅 WebSocket: ${taskId}`);
          
          // 创建 WebSocket 连接
          const ws = new TaskWebSocket(taskId, {
            onConceptStart: (event) => {
              console.log(`[RetryContentButton] 收到 concept_start 事件:`, event);
              // 状态已通过乐观更新设置，这里可以更新UI显示额外信息
            },
            
            onConceptComplete: (event) => {
              console.log(`[RetryContentButton] 收到 concept_complete 事件:`, event);
              // 更新状态为 'completed'
              updateConceptStatus(conceptId, { [statusKey]: 'completed' });
              // 触发成功回调
              onSuccess?.(response);
              // 断开 WebSocket
              ws.disconnect();
              setIsRetrying(false);
            },
            
            onConceptFailed: (event) => {
              console.error(`[RetryContentButton] 收到 concept_failed 事件:`, event);
              // 更新状态为 'failed'
              updateConceptStatus(conceptId, { [statusKey]: 'failed' });
              // 触发错误回调
              onError?.(new Error(event.error || '生成失败'));
              // 断开 WebSocket
              ws.disconnect();
              setIsRetrying(false);
            },
            
            onError: (event) => {
              console.error(`[RetryContentButton] WebSocket 错误:`, event);
              // WebSocket 错误不影响重试状态，因为后端仍在处理
            },
            
            onClosing: (event) => {
              console.log(`[RetryContentButton] WebSocket 关闭:`, event);
              // 连接关闭，清理引用
              wsRef.current = null;
            },
          });
          
          // 连接 WebSocket
          ws.connect(false); // 不需要历史事件
          wsRef.current = ws;
          
          // 注意：不在这里设置 isRetrying = false
          // 等待 WebSocket 事件来更新状态
        } else {
          // 没有 task_id，直接更新为 completed（向后兼容）
          console.warn(`[RetryContentButton] 后端未返回 task_id，直接更新状态`);
          updateConceptStatus(conceptId, { [statusKey]: 'completed' });
          onSuccess?.(response);
          setIsRetrying(false);
        }
      } else {
        // 生成失败，恢复为 'failed'
        updateConceptStatus(conceptId, { [statusKey]: 'failed' });
        setIsRetrying(false);
        throw new Error(response.message || '重试失败');
      }
    } catch (error) {
      console.error(`[RetryContentButton] 重试 ${contentType} 失败:`, error);
      // 发生错误，恢复为 'failed'
      updateConceptStatus(conceptId, { [statusKey]: 'failed' });
      onError?.(error instanceof Error ? error : new Error('重试失败'));
      setIsRetrying(false);
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleRetry}
      disabled={isRetrying}
      className={cn('gap-2', className)}
    >
      {isRetrying ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <RefreshCw className="w-4 h-4" />
      )}
      {showLabel && (
        <span>{isRetrying ? '重试中...' : CONTENT_TYPE_LABELS[contentType]}</span>
      )}
    </Button>
  );
}

/**
 * GeneratingContentAlert - 内容正在生成中提示
 * 
 * 显示正在生成中的加载状态
 */
export function GeneratingContentAlert({
  contentType,
  message,
  className,
}: {
  contentType: ContentType;
  message?: string;
  className?: string;
}) {
  const defaultMessage = {
    tutorial: '教程内容正在生成中',
    resources: '学习资源正在获取中',
    quiz: '测验题目正在生成中',
  };

  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-4 py-12 px-6 text-center',
      'bg-sage-50 dark:bg-sage-950/20 rounded-xl border border-sage-200 dark:border-sage-900',
      className
    )}>
      <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-sage-600 dark:text-sage-400 animate-spin" />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-medium text-sage-800 dark:text-sage-200">
          {message || defaultMessage[contentType]}
        </h3>
        <p className="text-sm text-sage-600 dark:text-sage-400">
          这可能需要几分钟时间，请稍候...
        </p>
      </div>
      {/* 可选：添加进度条或动画 */}
      <div className="w-48 h-1 bg-sage-200 dark:bg-sage-800 rounded-full overflow-hidden">
        <div className="h-full bg-sage-500 dark:bg-sage-400 animate-pulse rounded-full" style={{ width: '60%' }} />
      </div>
    </div>
  );
}

/**
 * FailedContentAlert - 内容生成失败提示
 * 
 * 显示失败提示并提供重试按钮
 */
export function FailedContentAlert({
  roadmapId,
  conceptId,
  contentType,
  preferences,
  message,
  onSuccess,
  onError,
  className,
}: {
  roadmapId: string;
  conceptId: string;
  contentType: ContentType;
  preferences: LearningPreferences;
  message?: string;
  onSuccess?: (response: RetryContentResponse) => void;
  onError?: (error: Error) => void;
  className?: string;
}) {
  const defaultMessage = {
    tutorial: '教程内容生成失败',
    resources: '学习资源获取失败',
    quiz: '测验题目生成失败',
  };

  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-4 py-12 px-6 text-center',
      'bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-200 dark:border-red-900',
      className
    )}>
      <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
        <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-medium text-red-800 dark:text-red-200">
          {message || defaultMessage[contentType]}
        </h3>
        <p className="text-sm text-red-600 dark:text-red-400">
          您可以尝试重新生成此内容
        </p>
      </div>
      <RetryContentButton
        roadmapId={roadmapId}
        conceptId={conceptId}
        contentType={contentType}
        preferences={preferences}
        onSuccess={onSuccess}
        onError={onError}
        variant="default"
        size="default"
      />
    </div>
  );
}

