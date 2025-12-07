'use client';

import React, { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Bot, FileText, Send, Sparkles, BrainCircuit } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * 消息类型定义
 */
interface ChatMessage {
  role: 'ai' | 'user';
  content: string;
}

/**
 * MentorSidecarProps - AI 导师侧边栏组件属性
 */
interface MentorSidecarProps {
  /** 自定义样式类名 */
  className?: string;
  /** 当前学习上下文（概念名称等） */
  conceptContext?: string;
}

/**
 * MentorSidecar - 沉浸式学习页面的右侧 AI 导师侧边栏
 * 
 * 功能:
 * - AI Mentor 标签页: 与 AI 导师对话
 * - Smart Notes 标签页: 自动生成的学习笔记
 * - 上下文感知的对话（基于当前学习内容）
 */
export function MentorSidecar({ className, conceptContext }: MentorSidecarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { 
      role: 'ai', 
      content: "Hi! I'm your AI Mentor. I noticed you're looking at React Lifecycle methods. The dependency array in `useEffect` is often a source of bugs. Want me to explain why?" 
    }
  ]);
  const [input, setInput] = useState('');

  const handleSend = useCallback(() => {
    if (!input.trim()) return;
    
    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    
    // Mock AI response (实际应调用 AI API)
    setTimeout(() => {
      setMessages(prev => [
        ...prev, 
        { role: 'ai', content: "That's a great question. In the virtual DOM..." }
      ]);
    }, 1000);
  }, [input]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div className={cn(
      "h-full flex flex-col",
      "bg-card/80 border-l border-border",
      className
    )}>
      <Tabs defaultValue="mentor" className="flex-1 flex flex-col">
        <div className="p-2 border-b border-border">
          <TabsList className="w-full bg-muted/50 border border-border">
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
        </div>

        <TabsContent value="mentor" className="flex-1 flex flex-col mt-0 p-0">
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              
              {/* Context Card - Quiz Widget */}
              <QuizCard />
            </div>
          </ScrollArea>
          
          <div className="p-4 border-t border-border">
            <div className="relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything..."
                className="bg-background border-border pr-10 focus-visible:ring-sage-300 text-foreground placeholder:text-muted-foreground"
              />
              <Button
                size="icon"
                variant="ghost"
                className="absolute right-1 top-1 h-8 w-8 hover:bg-sage-50 hover:text-sage-700 transition-colors"
                onClick={handleSend}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="notes" className="flex-1 flex flex-col mt-0 p-0">
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            <div className="text-center p-6">
              <FileText className="w-12 h-12 mx-auto mb-3 text-amber-200" />
              <p className="font-serif text-foreground">AI will automatically generate notes as you progress.</p>
              <p className="text-xs mt-2 text-muted-foreground">Your insights, organized effortlessly</p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

/**
 * MessageBubble - 消息气泡组件
 */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isAI = message.role === 'ai';
  
  return (
    <div className={cn("flex gap-3", !isAI && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0 border transition-colors",
        isAI 
          ? "bg-sage-100 border-sage-200 text-sage-600" 
          : "bg-muted border-border text-muted-foreground"
      )}>
        {isAI ? (
          <BrainCircuit className="w-4 h-4" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-current" />
        )}
      </div>
      {/* Message Content */}
      <div className={cn(
        "p-3 rounded-2xl text-sm max-w-[85%] leading-relaxed",
        isAI
          ? "bg-sage-50 border border-sage-100 text-foreground rounded-tl-none"
          : "bg-muted border border-border text-foreground/90 rounded-tr-none"
      )}>
        {message.content}
      </div>
    </div>
  );
}

/**
 * QuizCard - 测验卡片组件
 */
function QuizCard() {
  return (
    <Card 
      className="p-4 mt-4 border-sage-200 bg-gradient-to-br from-sage-50 to-background"
    >
      <div className="flex items-center gap-2 mb-3 text-sage-700 text-xs uppercase tracking-widest font-semibold">
        <Sparkles className="w-3 h-3" />
        Quiz Time
      </div>
      <p className="text-sm text-foreground mb-4 leading-relaxed">
        What happens if you return a function from useEffect?
      </p>
      <div className="space-y-2">
        <button className="w-full text-left text-xs p-3 rounded-lg bg-white hover:bg-sage-50 hover:text-sage-800 transition-colors border border-border hover:border-sage-300">
          A. It runs on mount
        </button>
        <button className="w-full text-left text-xs p-3 rounded-lg bg-white hover:bg-sage-50 hover:text-sage-800 transition-colors border border-border hover:border-sage-300">
          B. It runs on cleanup
        </button>
      </div>
    </Card>
  );
}
