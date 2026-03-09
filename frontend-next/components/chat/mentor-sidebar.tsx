'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, PanelRightClose, Send } from 'lucide-react';

import { AgentModeSwitcher } from '@/components/chat/agent-mode-switcher';
import { MentorMarkdownMessage } from '@/components/chat/mentor-markdown-message';
import { ToolCallCard } from '@/components/chat/tool-call-card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import {
  useMentorRuntime,
  type MentorAgentMode,
} from '@/lib/runtime/mentor-runtime-provider';

interface MentorSidebarProps {
  conceptId: string | null;
  conceptName?: string | null;
  agentMode: MentorAgentMode;
  onAgentModeChange: (mode: MentorAgentMode) => void;
  onClose: () => void;
}

/**
 * Mentor 聊天侧边栏。
 */
export function MentorSidebar({
  conceptId,
  conceptName = null,
  agentMode,
  onAgentModeChange,
  onClose,
}: MentorSidebarProps) {
  const { messages, isStreaming, isHistoryLoading, error, sendMessage } = useMentorRuntime();
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);

  const contextTitle = useMemo(() => {
    if (!conceptId) return '当前范围：整体路线图';
    return `当前概念：${conceptName || conceptId}`;
  }, [conceptId, conceptName]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    const message = input.trim();
    setInput('');
    await sendMessage(message);
  };

  return (
    <div className="flex h-full flex-col border-l bg-background/95 backdrop-blur">
      <div className="shrink-0 border-b p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">AI Mentor</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <PanelRightClose className="h-4 w-4" />
          </Button>
        </div>
        <AgentModeSwitcher
          mode={agentMode}
          onModeChange={onAgentModeChange}
          disabled={isStreaming}
        />
        <p className="text-xs text-muted-foreground">{contextTitle}</p>
      </div>

      <ScrollArea className="flex-1 p-3">
        <div className="space-y-3">
          {isHistoryLoading && (
            <div className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
              正在恢复历史对话...
            </div>
          )}
          {messages.length === 0 && (
            <div className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
              已连接 Mentor，对当前路线图可直接提问或要求引导式练习。
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`space-y-2 ${message.role === 'user' ? 'text-right' : 'text-left'}`}
            >
              <div
                className={
                  message.role === 'user'
                    ? 'inline-block max-w-[90%] rounded-lg bg-primary px-3 py-2 text-xs text-primary-foreground'
                    : 'inline-block max-w-[95%] rounded-lg bg-muted px-3 py-2 text-foreground'
                }
              >
                {message.role === 'assistant' ? (
                  <MentorMarkdownMessage
                    content={message.text || (isStreaming ? '思考中...' : '')}
                    className="text-xs"
                  />
                ) : (
                  message.text
                )}
              </div>

              {message.toolCalls.length > 0 && (
                <div className="space-y-2">
                  {message.toolCalls.map((toolCall) => (
                    <ToolCallCard key={toolCall.toolCallId} toolCall={toolCall} />
                  ))}
                </div>
              )}
            </div>
          ))}

          <div ref={endRef} />
        </div>
      </ScrollArea>

      <div className="shrink-0 border-t p-3 space-y-2">
        {error && (
          <p className="text-xs text-destructive">错误：{error}</p>
        )}
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入你的问题..."
            className="min-h-[72px] resize-none text-sm"
            disabled={isStreaming}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
          />
          <Button
            size="icon"
            className="shrink-0"
            disabled={isStreaming || !input.trim()}
            onClick={() => void handleSend()}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

