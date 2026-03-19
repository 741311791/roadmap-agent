'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown,
  Bot,
  CircleUserRound,
  Compass,
  History,
  PanelRightClose,
  Plus,
  Send,
  Sparkles,
} from 'lucide-react';

import { AgentModeSwitcher } from '@/components/chat/agent-mode-switcher';
import { MentorMarkdownMessage } from '@/components/chat/mentor-markdown-message';
import { ToolCallCard } from '@/components/chat/tool-call-card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  useMentorRuntime,
  type MentorAgentMode,
  type MentorModelName,
} from '@/lib/runtime/mentor-runtime-provider';
import { cn } from '@/lib/utils';

interface MentorSidebarProps {
  conceptId: string | null;
  conceptName?: string | null;
  agentMode: MentorAgentMode;
  modelName: MentorModelName;
  onAgentModeChange: (mode: MentorAgentMode) => void;
  onModelNameChange: (modelName: MentorModelName) => void;
  onClose: () => void;
}

const QUICK_PROMPTS = [
  '帮我总结这个概念的核心知识点',
  '请给我一份 20 分钟学习计划',
  '请用一个生活类比解释当前概念',
  '请出 3 个循序渐进的小练习',
];

function TypingIndicator() {
  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1.5">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </div>
  );
}

/**
 * Mentor 聊天侧边栏。
 */
export function MentorSidebar({
  conceptId,
  conceptName = null,
  agentMode,
  modelName,
  onAgentModeChange,
  onModelNameChange,
  onClose,
}: MentorSidebarProps) {
  const {
    messages,
    sessionSummaries,
    isStreaming,
    isHistoryLoading,
    error,
    sendMessage,
    switchSession,
    clearMessages,
    activeSessionId,
  } = useMentorRuntime();
  const [input, setInput] = useState('');
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const contextTitle = useMemo(() => {
    if (!conceptId) return '当前范围：整体路线图';
    return `当前概念：${conceptName || conceptId}`;
  }, [conceptId, conceptName]);

  const subtitle = useMemo(
    () => (agentMode === 'companion' ? '陪你拆解问题并给可执行建议' : '用引导式提问帮助你真正掌握'),
    [agentMode]
  );

  const formatSessionTime = (updatedAt: string) => {
    const date = new Date(updatedAt);
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(
      2,
      '0'
    )}:${String(date.getMinutes()).padStart(2, '0')}`;
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: isStreaming ? 'auto' : 'smooth',
      block: 'end',
    });
  }, [messages, isStreaming]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = '0px';
    const nextHeight = Math.min(textarea.scrollHeight, 180);
    textarea.style.height = `${nextHeight}px`;
  }, [input]);

  const handleScroll = () => {
    const node = scrollRef.current;
    if (!node) return;
    const distanceToBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
    setShowScrollToBottom(distanceToBottom > 120);
  };

  const scrollToBottom = () => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    const message = input.trim();
    setInput('');
    await sendMessage(message);
  };

  const handleQuickPrompt = async (prompt: string) => {
    if (isStreaming) return;
    await sendMessage(prompt);
  };

  const handleNewChat = () => {
    clearMessages();
    setInput('');
  };

  return (
    <div className="relative flex h-full flex-col border-l bg-background/95 backdrop-blur">
      <div className="shrink-0 border-b bg-gradient-to-b from-primary/[0.06] to-background px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/15">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold">AI Mentor</p>
                <p className="text-[11px] text-muted-foreground">{subtitle}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleNewChat}
              disabled={isStreaming}
              title="新建对话"
            >
              <Plus className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} title="关闭">
              <PanelRightClose className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          <AgentModeSwitcher
            mode={agentMode}
            onModeChange={onAgentModeChange}
            disabled={isStreaming}
          />
          <Select
            value={modelName}
            onValueChange={(value) => onModelNameChange(value as MentorModelName)}
            disabled={isStreaming}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="选择模型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="qwen-plus">qwen-plus</SelectItem> {/* pragma: allowlist secret */}
              <SelectItem value="qwen-max">qwen-max</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center justify-between gap-2">
            <Badge variant="outline" className="max-w-[80%] gap-1 truncate rounded-md text-[11px]">
              <Compass className="h-3 w-3" />
              <span className="truncate">{contextTitle}</span>
            </Badge>
            <Badge variant={isStreaming ? 'secondary' : 'outline'} className="rounded-md text-[11px]">
              {isStreaming ? '回复中' : activeSessionId ? '已连接' : '新会话'}
            </Badge>
          </div>
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-4"
      >
        <div className="space-y-4 pb-4">
          {isHistoryLoading && (
            <div className="rounded-xl border border-dashed p-4 text-xs text-muted-foreground">
              正在恢复历史对话…
            </div>
          )}

          {messages.length === 0 && (
            <div className="space-y-3 rounded-xl border border-dashed p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" />
                <span>已连接 Mentor，试试这些问题：</span>
              </div>
              <div className="grid gap-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <Button
                    key={prompt}
                    variant="outline"
                    size="sm"
                    className="h-auto justify-start whitespace-normal py-2 text-left text-xs"
                    disabled={isStreaming}
                    onClick={() => void handleQuickPrompt(prompt)}
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {sessionSummaries.length > 0 && (
            <div className="space-y-2 rounded-xl border p-3">
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <History className="h-3.5 w-3.5" />
                <span>历史会话</span>
              </div>
              <div className="space-y-1">
                {sessionSummaries.slice(0, 8).map((session) => (
                  <button
                    key={session.session_id}
                    type="button"
                    disabled={isStreaming}
                    className={cn(
                      'w-full rounded-lg border px-2 py-1.5 text-left transition-colors',
                      activeSessionId === session.session_id
                        ? 'border-primary/40 bg-primary/10'
                        : 'hover:bg-muted'
                    )}
                    onClick={() => void switchSession(session.session_id)}
                  >
                    <div className="line-clamp-1 text-xs text-foreground">
                      {session.last_message_preview || '空会话'}
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{formatSessionTime(session.updated_at)}</span>
                      <span>{session.message_count} 条</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'space-y-2',
                message.role === 'user' ? 'ml-8' : 'mr-8'
              )}
            >
              <div className={cn('flex items-start gap-2', message.role === 'user' && 'justify-end')}>
                {message.role === 'assistant' && (
                  <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-muted">
                    <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                )}

                <div
                  className={cn(
                    'max-w-[92%] rounded-2xl px-3 py-2',
                    message.role === 'user'
                      ? 'rounded-tr-md bg-primary text-primary-foreground'
                      : 'rounded-tl-md bg-muted text-foreground'
                  )}
                >
                  {message.role === 'assistant' ? (
                    message.text ? (
                      <MentorMarkdownMessage content={message.text} className="text-xs" />
                    ) : isStreaming ? (
                      <TypingIndicator />
                    ) : null
                  ) : (
                    <p className="whitespace-pre-wrap text-xs leading-relaxed">{message.text}</p>
                  )}
                </div>

                {message.role === 'user' && (
                  <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-primary/15">
                    <CircleUserRound className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}
              </div>

              {message.toolCalls.length > 0 && (
                <div className="ml-9 space-y-2">
                  {message.toolCalls.map((toolCall) => (
                    <ToolCallCard key={toolCall.toolCallId} toolCall={toolCall} />
                  ))}
                </div>
              )}
            </div>
          ))}

          <div ref={endRef} />
        </div>
      </div>

      {showScrollToBottom && (
        <Button
          size="sm"
          variant="outline"
          className="absolute bottom-28 right-4 z-10 rounded-full shadow-md"
          onClick={scrollToBottom}
        >
          <ArrowDown className="mr-1 h-3.5 w-3.5" />
          回到底部
        </Button>
      )}

      <div className="shrink-0 border-t bg-background/95 px-3 py-3">
        {error && (
          <div className="mb-2 rounded-md border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
            错误：{error}
          </div>
        )}

        <div className="flex items-end gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入你的问题，Enter 发送，Shift + Enter 换行…"
            className="max-h-[180px] min-h-[44px] resize-none text-sm leading-relaxed"
            disabled={isStreaming}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
          />
          <Button
            size="sm"
            className="mb-0.5 shrink-0 gap-1"
            disabled={isStreaming || !input.trim()}
            onClick={() => void handleSend()}
          >
            <Send className="h-4 w-4" />
            发送
          </Button>
        </div>

        <div className="my-2 h-px w-full bg-border" />
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Enter 发送，Shift + Enter 换行</span>
          <span>{input.length} 字</span>
        </div>
      </div>
    </div>
  );
}

