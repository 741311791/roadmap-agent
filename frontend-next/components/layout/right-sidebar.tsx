'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Plus,
  Send,
  Bot,
  Sparkles,
  Clock,
  Settings,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';

interface RightSidebarProps {
  className?: string;
}

// Tooltip component
function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  return (
    <div className="relative group">
      {children}
      <div className="absolute right-full mr-2 px-2 py-1 bg-primary text-primary-foreground text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
        {text}
      </div>
    </div>
  );
}

// Agent tag component
function AgentTag({ label, color }: { label: string; color: string }) {
  return (
    <div
      className={cn(
        'px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap flex items-center gap-1',
        color
      )}
    >
      <Sparkles size={10} />
      {label}
    </div>
  );
}

// Prompt suggestion component
function PromptSuggestion({
  icon: Icon,
  text,
  onClick,
}: {
  icon: React.ElementType;
  text: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 text-xs text-foreground/70 hover:text-foreground cursor-pointer group text-left w-full"
    >
      <Icon size={14} className="text-sage-500 group-hover:scale-110 transition-transform flex-shrink-0" />
      <span>{text}</span>
    </button>
  );
}

export function RightSidebar({ className }: RightSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    // TODO: Implement chat functionality
    console.log('Submit:', inputValue);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (isCollapsed) {
    return (
      <div
        className={cn(
          'flex flex-col items-center py-6 h-full gap-4 bg-background border-l border-border/5 w-[70px]',
          className
        )}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="w-10 h-10 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
          title="Expand AI Assistant"
        >
          <PanelRightOpen size={18} className="text-foreground/60" />
        </button>

        <div className="h-px w-8 bg-primary/10" />

        <Tooltip text="New Chat">
          <button className="w-10 h-10 bg-primary text-primary-foreground rounded-full flex items-center justify-center hover:scale-105 transition-transform">
            <Plus size={18} />
          </button>
        </Tooltip>

        <Tooltip text="History">
          <button className="w-10 h-10 flex items-center justify-center hover:bg-primary/5 rounded-full transition-colors">
            <Clock size={18} className="text-foreground/60" />
          </button>
        </Tooltip>

        <Tooltip text="Settings">
          <button className="w-10 h-10 flex items-center justify-center hover:bg-primary/5 rounded-full transition-colors">
            <Settings size={18} className="text-foreground/60" />
          </button>
        </Tooltip>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col bg-background border-l border-border/5 w-[350px]',
        className
      )}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border/5">
        <button
          onClick={() => setIsCollapsed(true)}
          className="w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
          title="Collapse AI Assistant"
        >
          <PanelRightClose size={16} className="text-foreground/60" />
        </button>
        <span className="text-sm font-medium">AI Assistant</span>
        <button className="w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors">
          <Plus size={16} className="text-foreground/40" />
        </button>
      </div>

      {/* Chat Content */}
      <ScrollArea className="flex-1 p-6">
        <div className="flex flex-col h-full">
          {/* Welcome State */}
          <div className="mt-8 mb-8 text-center">
            <div className="w-16 h-16 bg-primary rounded-full mx-auto flex items-center justify-center text-primary-foreground mb-4 shadow-lg shadow-charcoal/20">
              <Bot size={32} />
            </div>
            <h2 className="font-serif font-bold text-xl mb-1">
              Muset is thinking with you
            </h2>
            <p className="text-sm text-muted-foreground">
              Ask questions about your roadmap or request modifications
            </p>
          </div>

          {/* Suggested Prompts */}
          <div className="mt-auto space-y-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Suggestions
            </div>
            <div className="space-y-3">
              <PromptSuggestion
                icon={Sparkles}
                text="Explain this concept in simpler terms"
              />
              <PromptSuggestion
                icon={Bot}
                text="Add more practical examples"
              />
              <PromptSuggestion
                icon={Sparkles}
                text="Generate more quiz questions"
              />
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-border/5">
        <div className="bg-white rounded-3xl p-4 shadow-sm border border-border/5">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full bg-transparent resize-none outline-none text-sm min-h-[80px] placeholder:text-foreground/30"
            placeholder="Ask anything about your learning..."
          />
          <div className="flex items-center justify-between mt-2">
            <button className="text-foreground/40 hover:text-foreground transition-colors">
              @
            </button>
            <div className="flex items-center gap-2">
              <button className="w-8 h-8 bg-primary/5 rounded-full flex items-center justify-center text-foreground/60 hover:bg-primary/10 transition-colors">
                <Plus size={16} />
              </button>
              <button
                onClick={handleSubmit}
                disabled={!inputValue.trim()}
                className="w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-50 disabled:hover:scale-100"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Agent Tags */}
        <div className="flex gap-2 mt-4 overflow-x-auto pb-2 scrollbar-hide">
          <AgentTag label="Tutorial Helper" color="bg-sage-100 text-sage-700" />
          <AgentTag label="Quiz Master" color="bg-yellow-100 text-yellow-700" />
        </div>
      </div>
    </div>
  );
}

