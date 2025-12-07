'use client';

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StreamingMessageProps {
  content: string;
  className?: string;
  typingSpeed?: number; // ms per character
}

/**
 * StreamingMessage - 流式消息组件
 * 
 * 功能:
 * - 打字机效果
 * - 实时 Markdown 渲染（简化版）
 * - 流畅动画
 */
export function StreamingMessage({
  content,
  className,
  typingSpeed = 10
}: StreamingMessageProps) {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    // 如果内容没有变化，不需要重新打字
    if (content === displayedContent) {
      setIsTyping(false);
      return;
    }

    // 逐字显示（简化版，实际可以更复杂）
    let currentIndex = displayedContent.length;
    
    const interval = setInterval(() => {
      if (currentIndex < content.length) {
        setDisplayedContent(content.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, typingSpeed);

    return () => clearInterval(interval);
  }, [content, typingSpeed, displayedContent]);

  return (
    <div className={cn('relative', className)}>
      <p className="whitespace-pre-wrap break-words">
        {displayedContent}
        {isTyping && (
          <span className="inline-flex items-center ml-1">
            <Loader2 className="w-3 h-3 animate-spin" />
          </span>
        )}
      </p>
      
      {/* 打字光标动画 */}
      {isTyping && (
        <span
          className={cn(
            'inline-block w-0.5 h-4 bg-current ml-1',
            'animate-pulse'
          )}
          aria-hidden="true"
        />
      )}
    </div>
  );
}

/**
 * TypingIndicator - 打字指示器
 * 显示 "对方正在输入..." 的动画
 */
export function TypingIndicator({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-1.5 px-4 py-2', className)}>
      <div className="flex gap-1">
        <span
          className="w-2 h-2 rounded-full bg-current animate-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <span
          className="w-2 h-2 rounded-full bg-current animate-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <span
          className="w-2 h-2 rounded-full bg-current animate-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>
      <span className="text-sm text-muted-foreground ml-2">
        AI 正在思考...
      </span>
    </div>
  );
}

/**
 * StreamBuffer - 流式缓冲区显示
 * 用于调试或显示实时流式数据
 */
export function StreamBuffer({
  buffer,
  className
}: {
  buffer: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'font-mono text-xs bg-muted/50 p-3 rounded border',
        'max-h-32 overflow-y-auto',
        className
      )}
    >
      <pre className="whitespace-pre-wrap break-all">
        {buffer || '(空)'}
      </pre>
    </div>
  );
}

