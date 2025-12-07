'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageList } from './message-list';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { 
  Send, 
  Loader2, 
  Minimize2, 
  Maximize2,
  X,
  Bot,
  MessageCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/lib/store/chat-store';

interface ChatWidgetProps {
  roadmapId?: string;
  conceptId?: string;
  onClose?: () => void;
  className?: string;
  defaultMinimized?: boolean;
}

/**
 * ChatWidget - AI 聊天窗口组件
 * 
 * 功能:
 * - 消息收发
 * - 流式输出支持
 * - 上下文管理
 * - 最小化/最大化
 * - 输入验证
 */
export function ChatWidget({
  roadmapId,
  conceptId,
  onClose,
  className,
  defaultMinimized = false
}: ChatWidgetProps) {
  const [isMinimized, setIsMinimized] = useState(defaultMinimized);
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    isStreaming,
    addMessage,
    setContext
  } = useChatStore();

  // 设置上下文
  useEffect(() => {
    setContext(roadmapId || null, conceptId || null);
  }, [roadmapId, conceptId, setContext]);

  // 自动聚焦输入框
  useEffect(() => {
    if (!isMinimized && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isMinimized]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;

    // 添加用户消息
    addMessage({
      role: 'user',
      content: input.trim()
    });

    // 清空输入
    setInput('');

    // TODO: 调用 API 发送消息
    // 这里应该调用 useContentModification hook
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 最小化时显示浮动按钮
  if (isMinimized) {
    return (
      <Button
        onClick={() => setIsMinimized(false)}
        className={cn(
          'fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg',
          'hover:scale-110 transition-transform',
          className
        )}
      >
        <MessageCircle className="w-6 h-6" />
      </Button>
    );
  }

  return (
    <Card className={cn(
      'fixed bottom-6 right-6 w-96 h-[600px] shadow-2xl',
      'flex flex-col overflow-hidden',
      className
    )}>
      {/* 头部 */}
      <CardHeader className="pb-3 border-b shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base">AI 助手</CardTitle>
              {conceptId && (
                <p className="text-xs text-muted-foreground truncate">
                  当前概念
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1">
            {isStreaming && (
              <Badge variant="secondary" className="mr-2 animate-pulse">
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                思考中
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMinimized(true)}
            >
              <Minimize2 className="w-4 h-4" />
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      {/* 消息列表 */}
      <CardContent className="flex-1 overflow-hidden p-4">
        <MessageList messages={messages} />
      </CardContent>

      {/* 输入区域 */}
      <div className="border-t p-4 shrink-0">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift+Enter 换行)"
            className="min-h-[80px] max-h-[120px] resize-none"
            disabled={isStreaming}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="shrink-0"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          按 Enter 发送，Shift+Enter 换行
        </p>
      </div>
    </Card>
  );
}

/**
 * CompactChatWidget - 紧凑版聊天窗口
 * 用于侧边栏集成
 */
export function CompactChatWidget({
  roadmapId,
  conceptId,
  className
}: Omit<ChatWidgetProps, 'onClose' | 'defaultMinimized'>) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    isStreaming,
    addMessage,
    setContext
  } = useChatStore();

  useEffect(() => {
    setContext(roadmapId || null, conceptId || null);
  }, [roadmapId, conceptId, setContext]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    addMessage({ role: 'user', content: input.trim() });
    setInput('');
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* 消息列表 */}
      <div className="flex-1 overflow-hidden px-4 py-2">
        <MessageList messages={messages} compact />
      </div>

      {/* 输入区域 */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入消息..."
            className="min-h-[60px] resize-none text-sm"
            disabled={isStreaming}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="sm"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

