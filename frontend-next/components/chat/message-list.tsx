'use client';

import { useRef, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { User, Bot } from 'lucide-react';
import { StreamingMessage } from './streaming-message';
import type { ChatMessage } from '@/types/custom/store';

interface MessageListProps {
  messages: ChatMessage[];
  className?: string;
  compact?: boolean;
}

/**
 * MessageList - 聊天消息列表组件
 * 
 * 功能:
 * - 消息滚动
 * - 自动滚动到底部
 * - 角色区分
 * - 时间戳显示
 * - 支持流式消息
 */
export function MessageList({ 
  messages, 
  className,
  compact = false 
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className={cn(
        'flex items-center justify-center h-full',
        'text-muted-foreground text-sm',
        className
      )}>
        开始对话，我可以帮你修改路线图内容
      </div>
    );
  }

  return (
    <ScrollArea className={cn('h-full', className)}>
      <div ref={scrollRef} className="space-y-4 pr-4">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            compact={compact}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

/**
 * MessageBubble - 单个消息气泡
 */
function MessageBubble({ 
  message, 
  compact 
}: { 
  message: ChatMessage;
  compact?: boolean;
}) {
  const isUser = message.role === 'user';
  const isStreaming = message.metadata?.isStreaming;

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser && 'flex-row-reverse'
      )}
    >
      {/* 头像 */}
      {!compact && (
        <Avatar className={cn(
          'w-8 h-8 shrink-0',
          isUser ? 'bg-primary' : 'bg-muted'
        )}>
          {isUser ? (
            <User className="w-4 h-4 text-primary-foreground" />
          ) : (
            <Bot className="w-4 h-4 text-muted-foreground" />
          )}
        </Avatar>
      )}

      {/* 消息内容 */}
      <div
        className={cn(
          'flex flex-col gap-1 max-w-[80%]',
          isUser && 'items-end'
        )}
      >
        {/* 消息气泡 */}
        <div
          className={cn(
            'px-4 py-2 rounded-lg',
            isUser ? [
              'bg-primary text-primary-foreground',
              'rounded-tr-none'
            ] : [
              'bg-muted',
              'rounded-tl-none'
            ],
            compact && 'px-3 py-1.5 text-sm'
          )}
        >
          {isStreaming ? (
            <StreamingMessage content={message.content} />
          ) : (
            <p className="whitespace-pre-wrap break-words">
              {message.content}
            </p>
          )}
        </div>

        {/* 时间戳 */}
        <span className="text-xs text-muted-foreground px-1">
          {formatTimestamp(message.timestamp)}
        </span>

        {/* 修改结果（如果有） */}
        {message.metadata?.modifications && (
          <ModificationResults modifications={message.metadata.modifications} />
        )}
      </div>
    </div>
  );
}

/**
 * ModificationResults - 修改结果展示
 */
function ModificationResults({
  modifications
}: {
  modifications: Array<{
    type: string;
    targetId: string;
    targetName: string;
    success: boolean;
  }>;
}) {
  return (
    <div className="space-y-1 mt-2">
      {modifications.map((mod, index) => (
        <div
          key={index}
          className={cn(
            'text-xs px-2 py-1 rounded flex items-center gap-2',
            mod.success
              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
              : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
          )}
        >
          <span className={cn(
            'w-1.5 h-1.5 rounded-full',
            mod.success ? 'bg-green-500' : 'bg-red-500'
          )} />
          <span>
            {mod.success ? '✓' : '✗'} {mod.type}: {mod.targetName}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // 小于 1 分钟
  if (diff < 60000) {
    return '刚刚';
  }

  // 小于 1 小时
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes} 分钟前`;
  }

  // 小于 24 小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours} 小时前`;
  }

  // 同一年
  if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // 完整日期
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

