'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Bot, FileText, Send, Sparkles, BrainCircuit, ChevronRight, Copy, Check, Lightbulb, Loader2, StopCircle, AlertCircle, Lock, Wrench } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useMentorChat, type LearningNote } from '@/lib/hooks/api/use-mentor-chat';
import { useAuthStore } from '@/lib/store/auth-store';

/**
 * 功能开发中标志
 * 设置为 true 时，AI Mentor 功能将被禁用并显示开发中提示
 */
const IS_FEATURE_IN_DEVELOPMENT = true;

/**
 * MentorSidecarProps - AI 导师侧边栏组件属性
 */
interface MentorSidecarProps {
  /** 自定义样式类名 */
  className?: string;
  /** 当前学习上下文（概念名称等） */
  conceptContext?: string;
  /** 路线图 ID */
  roadmapId?: string;
  /** 当前概念 ID */
  conceptId?: string;
  /** 是否折叠 */
  isCollapsed?: boolean;
  /** 折叠状态切换回调 */
  onToggleCollapse?: () => void;
}

/**
 * MentorSidecar - 沉浸式学习页面的右侧 AI 导师侧边栏
 * 
 * 功能:
 * - AI Mentor 标签页: 与 AI 导师对话（SSE流式输出）
 * - Smart Notes 标签页: 自动生成的学习笔记
 * - 上下文感知的对话（基于当前学习内容）
 * - 支持折叠/展开
 * - 快捷提示词
 */
export function MentorSidecar({ 
  className, 
  conceptContext, 
  roadmapId,
  conceptId,
  isCollapsed, 
  onToggleCollapse 
}: MentorSidecarProps) {
  // Auth
  const { getUserId } = useAuthStore();
  const userId = getUserId();

  // 聊天 Hook
  const {
    messages,
    isStreaming,
    error,
    lastFailedMessage,
    sendMessage,
    stopStreaming,
    retryLastMessage,
    getNotes,
  } = useMentorChat({
    userId: userId || 'anonymous',
    roadmapId: roadmapId || '',
    conceptId,
  });

  // 本地状态
  const [input, setInput] = useState('');
  const [notes, setNotes] = useState<LearningNote[]>([]);
  const [isLoadingNotes, setIsLoadingNotes] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 平滑滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 当消息更新或流式输出时自动滚动
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 加载笔记
  useEffect(() => {
    if (roadmapId) {
      setIsLoadingNotes(true);
      getNotes(conceptId).then(setNotes).finally(() => setIsLoadingNotes(false));
    }
  }, [roadmapId, conceptId, getNotes]);

  // 发送消息
  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput('');
  }, [input, isStreaming, sendMessage]);

  // 键盘事件
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // 快捷提示词
  const quickPrompts = [
    { icon: Lightbulb, text: "Explain this", prompt: "Can you explain this concept using a real-life analogy?" },
    { icon: Sparkles, text: "Give example", prompt: "Can you give me a practical code example?" },
  ];

  // 发送快捷提示词
  const handleQuickPrompt = (prompt: string) => {
    if (isStreaming) return;
    sendMessage(prompt);
  };

  // 如果折叠状态，只显示一个折叠按钮
  if (isCollapsed) {
    return (
      <div className={cn(
        "h-full flex flex-col items-center justify-center",
        "bg-card/80 border-l border-border w-12",
        className
      )}>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="hover:bg-sage-50 hover:text-sage-700 transition-colors"
        >
          <ChevronRight className="w-4 h-4 rotate-180" />
        </Button>
      </div>
    );
  }

  // 功能开发中 - 显示占位界面
  if (IS_FEATURE_IN_DEVELOPMENT) {
    return (
      <div className={cn(
        "h-full flex flex-col",
        "bg-card/80 border-l border-border",
        className
      )}>
        {/* Header */}
        <div className="p-2 border-b border-border flex items-center gap-2">
          <div className="flex-1 bg-muted/50 border border-border rounded-lg p-1 flex">
            <div className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-sage-100 text-sage-700 rounded-md text-sm font-medium">
              <Bot className="w-4 h-4" />
              AI Mentor
            </div>
            <div className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-muted-foreground text-sm">
              <FileText className="w-4 h-4" />
              Smart Notes
            </div>
          </div>
          
          {/* Collapse Button */}
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-8 w-8 shrink-0 hover:bg-sage-50 hover:text-sage-700 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* 开发中提示内容 */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-20 h-20 rounded-full bg-sage-50 border-2 border-sage-200 flex items-center justify-center mb-6">
            <Wrench className="w-10 h-10 text-sage-400" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-foreground mb-2">
            Coming Soon
          </h3>
          <p className="text-sm text-muted-foreground max-w-[200px] mb-4 leading-relaxed">
            Our AI Mentor feature is being polished to deliver you the best learning experience.
          </p>
          <div className="flex items-center gap-2 text-xs text-sage-600 bg-sage-50 px-3 py-1.5 rounded-full">
            <Lock className="w-3 h-3" />
            <span>Under Development</span>
          </div>
        </div>

        {/* 禁用的输入区域 */}
        <div className="p-4 border-t border-border bg-background/50">
          <div className="relative">
            <Input
              value=""
              placeholder="AI Mentor coming soon..."
              disabled
              className="bg-muted/50 border-border pr-10 opacity-50 cursor-not-allowed"
            />
            <Button
              size="icon"
              variant="ghost"
              className="absolute right-1 top-1 h-8 w-8 opacity-50 cursor-not-allowed"
              disabled
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Stay tuned for updates!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "h-full flex flex-col",
      "bg-card/80 border-l border-border",
      className
    )}>
      <Tabs defaultValue="mentor" className="flex-1 flex flex-col">
        {/* Header with Tabs and Collapse Button */}
        <div className="p-2 border-b border-border flex items-center gap-2">
          <TabsList className="flex-1 bg-muted/50 border border-border">
            <TabsTrigger 
              value="mentor" 
              className="flex-1 gap-2 transition-all data-[state=active]:bg-sage-100 data-[state=active]:text-sage-700"
            >
              <Bot className="w-4 h-4" />
              AI Mentor
            </TabsTrigger>
            <TabsTrigger 
              value="notes" 
              className="flex-1 gap-2 transition-all data-[state=active]:bg-amber-50 data-[state=active]:text-amber-700"
            >
              <FileText className="w-4 h-4" />
              Smart Notes
            </TabsTrigger>
          </TabsList>
          
          {/* Collapse Button */}
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-8 w-8 shrink-0 hover:bg-sage-50 hover:text-sage-700 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          )}
        </div>

        <TabsContent value="mentor" className="flex-1 flex flex-col mt-0 p-0">
          {/* Quick Prompts - 快捷提示词 */}
          <div className="p-3 border-b border-border bg-background/50">
            <div className="flex gap-2">
              {quickPrompts.map((prompt, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickPrompt(prompt.prompt)}
                  disabled={isStreaming}
                  className="flex-1 gap-1.5 text-xs h-8 hover:bg-sage-50 hover:text-sage-700 hover:border-sage-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title={isStreaming ? "Please wait for AI to finish" : prompt.prompt}
                >
                  <prompt.icon className="w-3 h-3" />
                  {prompt.text}
                </Button>
              ))}
            </div>
          </div>

          <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
            <div className="space-y-4">
              {/* 初始欢迎消息 */}
              {messages.length === 0 && !isStreaming && (
                <MessageBubble 
                  message={{
                    role: 'assistant',
                    content: conceptContext 
                      ? `Hi! I'm your AI Mentor. I see you're studying **${conceptContext}**. Feel free to ask me anything – I'll explain it using everyday analogies to make it easier to understand!`
                      : "Hi! I'm your AI Mentor. Select a concept from the left panel, and I'll help you understand it using real-life analogies. Just ask away!"
                  }} 
                  isStreaming={false}
                />
              )}
              
              {/* 消息列表 */}
              {messages.map((msg, i) => (
                <MessageBubble 
                  key={msg.message_id || i} 
                  message={{
                    role: msg.role === 'assistant' ? 'assistant' : 'user',
                    content: msg.content,
                  }}
                  isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                />
              ))}
              
              {/* AI 思考中状态 */}
              {isStreaming && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
                <MessageBubble 
                  message={{
                    role: 'assistant',
                    content: '',
                  }}
                  isStreaming={true}
                  isThinking={true}
                />
              )}
              
              {/* 错误提示 */}
              {error && (
                <div className="flex gap-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium mb-1">Failed to send message</p>
                    <p className="text-xs opacity-90">{error}</p>
                    {lastFailedMessage && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={retryLastMessage}
                        className="mt-2 h-7 text-xs border-red-300 hover:bg-red-100"
                      >
                        Retry
                      </Button>
                    )}
                  </div>
                </div>
              )}
              
              {/* 滚动锚点 */}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
          
          {/* Fixed Input at Bottom */}
          <div className="p-4 border-t border-border bg-background">
            <div className="relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isStreaming ? "AI is thinking..." : "Ask anything..."}
                disabled={isStreaming}
                className="bg-background border-border pr-10 focus-visible:ring-sage-300 text-foreground placeholder:text-muted-foreground disabled:opacity-60 disabled:cursor-not-allowed"
              />
              {isStreaming ? (
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute right-1 top-1 h-8 w-8 hover:bg-red-50 hover:text-red-700 transition-colors"
                  onClick={stopStreaming}
                  title="Stop generation"
                >
                  <StopCircle className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute right-1 top-1 h-8 w-8 hover:bg-sage-50 hover:text-sage-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  onClick={handleSend}
                  disabled={!input.trim()}
                  title={input.trim() ? "Send message" : "Type a message first"}
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
            {/* 提示文字 */}
            <div className="flex items-center justify-between mt-2">
              {isStreaming ? (
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  AI is generating response...
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Press <kbd className="px-1.5 py-0.5 text-[10px] bg-muted border border-border rounded">Enter</kbd> to send
                </p>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="notes" className="flex-1 flex flex-col mt-0 p-0">
          {isLoadingNotes ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : notes.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
              <div className="text-center p-6">
                <FileText className="w-12 h-12 mx-auto mb-3 text-amber-200" />
                <p className="font-serif text-foreground">No notes yet</p>
                <p className="text-xs mt-2 text-muted-foreground">
                  Ask me to "take notes" during our chat, and I'll save key points here.
                </p>
              </div>
            </div>
          ) : (
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                {notes.map((note) => (
                  <NoteCard key={note.note_id} note={note} />
                ))}
              </div>
            </ScrollArea>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

/**
 * 消息气泡属性
 */
interface MessageBubbleProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
  };
  isStreaming?: boolean;
  isThinking?: boolean;
}

/**
 * MessageBubble - 消息气泡组件（支持代码块复制和流式动画）
 */
function MessageBubble({ message, isStreaming = false, isThinking = false }: MessageBubbleProps) {
  const isAI = message.role === 'assistant';
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null);
  
  // 检测代码块 (简单实现，实际项目应使用 markdown parser)
  const hasCodeBlocks = message.content.includes('```');
  
  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };
  
  // 简单解析代码块和Markdown
  const renderContent = () => {
    // 显示思考中动画
    if (isThinking) {
      return (
        <div className="flex items-center gap-2 text-muted-foreground">
          <span className="flex gap-1">
            <span className="w-2 h-2 bg-sage-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-sage-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-sage-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          <span className="text-sm">Thinking...</span>
        </div>
      );
    }
    
    if (!message.content) {
      return <span className="text-muted-foreground italic">...</span>;
    }
    
    let content = message.content;
    
    // 处理 **bold** 语法
    content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    if (!hasCodeBlocks) {
      return (
        <>
          <span dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          {isStreaming && <span className="inline-block w-2 h-4 bg-sage-500 animate-pulse ml-0.5" />}
        </>
      );
    }
    
    const parts = message.content.split('```');
    return (
      <>
        {parts.map((part, idx) => {
          if (idx % 2 === 0) {
            // 普通文本
            const htmlContent = part
              .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
              .replace(/\n/g, '<br/>');
            return <span key={idx} dangerouslySetInnerHTML={{ __html: htmlContent }} />;
          } else {
            // 代码块
            const lines = part.split('\n');
            const language = lines[0] || 'plaintext';
            const code = lines.slice(1).join('\n');
            
            return (
              <div key={idx} className="relative group my-2">
                <pre className="bg-muted/50 border border-border rounded-lg p-3 text-xs overflow-x-auto">
                  <code className="text-foreground/90">{code}</code>
                </pre>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => handleCopyCode(code, idx)}
                  className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-background"
                >
                  {copiedIndex === idx ? (
                    <Check className="w-3 h-3 text-green-600" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
                {language && language !== 'plaintext' && (
                  <span className="absolute top-2 left-2 text-xs text-muted-foreground">
                    {language}
                  </span>
                )}
              </div>
            );
          }
        })}
        {isStreaming && <span className="inline-block w-2 h-4 bg-sage-500 animate-pulse ml-0.5" />}
      </>
    );
  };
  
  return (
    <div className={cn(
      "flex gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
      !isAI && "flex-row-reverse"
    )}>
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0 border transition-colors",
        isAI 
          ? "bg-sage-100 border-sage-200 text-sage-600" 
          : "bg-amber-50 border-amber-200 text-amber-600"
      )}>
        {isAI ? (
          isStreaming || isThinking ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <BrainCircuit className="w-4 h-4" />
          )
        ) : (
          <div className="w-2 h-2 rounded-full bg-current" />
        )}
      </div>
      {/* Message Content */}
      <div className={cn(
        "p-3 rounded-lg text-sm max-w-[85%] leading-relaxed transition-colors",
        isAI
          ? "bg-sage-50 border border-sage-100 text-foreground rounded-tl-sm"
          : "bg-amber-50/50 border border-amber-100 text-foreground/90 rounded-tr-sm"
      )}>
        {renderContent()}
      </div>
    </div>
  );
}

/**
 * NoteCard - 笔记卡片组件
 */
function NoteCard({ note }: { note: LearningNote }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  return (
    <Card className="p-4 border-amber-200 bg-gradient-to-br from-amber-50 to-background">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-sm text-foreground line-clamp-1">
          {note.title || 'Learning Note'}
        </h4>
        <span className="text-xs text-muted-foreground">
          {new Date(note.created_at).toLocaleDateString()}
        </span>
      </div>
      
      <div 
        className={cn(
          "text-sm text-foreground/80 leading-relaxed",
          !isExpanded && "line-clamp-3"
        )}
      >
        {note.content}
      </div>
      
      {note.content.length > 150 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 h-6 text-xs text-amber-700 hover:text-amber-800 hover:bg-amber-100 p-0"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </Button>
      )}
      
      {note.tags.length > 0 && (
        <div className="flex gap-1 mt-2 flex-wrap">
          {note.tags.map((tag, idx) => (
            <span 
              key={idx}
              className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}
