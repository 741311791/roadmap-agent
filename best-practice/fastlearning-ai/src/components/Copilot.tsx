import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Bot, HelpCircle, FileText, CheckCircle2, MessageSquare, Plus, ChevronDown, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Message, ChatSession } from '../types';
import { cn } from '../lib/utils';

interface CopilotProps {
  session?: ChatSession;
  sessions: ChatSession[];
  currentTargetId: string;
  onSendMessage: (content: string) => void;
  onNewSession: () => void;
  onSwitchSession: (id: string) => void;
  isGenerating: boolean;
  onPreviewArtifact: (id: string) => void;
}

export const Copilot: React.FC<CopilotProps> = ({ 
  session, 
  sessions, 
  currentTargetId,
  onSendMessage, 
  onNewSession,
  onSwitchSession,
  isGenerating, 
  onPreviewArtifact 
}) => {
  const [input, setInput] = useState('');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const targetSessions = sessions.filter(s => s.targetId === currentTargetId).sort((a, b) => b.createdAt - a.createdAt);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [session?.messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isGenerating) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">
      <div className="p-4 border-b border-slate-100 flex items-center justify-between relative">
        <button 
          onClick={() => setIsHistoryOpen(!isHistoryOpen)}
          className="flex items-center gap-2 hover:bg-slate-50 px-2 py-1.5 rounded-lg transition-colors"
        >
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white">
            <Sparkles size={18} />
          </div>
          <div className="text-left">
            <h2 className="font-display font-semibold text-slate-800 text-sm flex items-center gap-1">
              {session?.title || 'LUI Copilot'}
              <ChevronDown size={14} className="text-slate-400" />
            </h2>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">{currentTargetId === 'roadmap' ? 'Roadmap' : 'Chapter'} Chat</p>
          </div>
        </button>

        <button 
          onClick={onNewSession}
          className="p-2 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
          title="New Chat"
        >
          <Plus size={18} />
        </button>

        <AnimatePresence>
          {isHistoryOpen && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute top-full left-4 mt-2 w-72 bg-white border border-slate-200 shadow-xl rounded-xl p-2 z-50"
            >
              <div className="px-3 py-2 border-b border-slate-100 mb-2 flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                  <MessageSquare size={12} />
                  Chat History
                </h3>
              </div>
              <div className="max-h-64 overflow-y-auto space-y-1">
                {targetSessions.length === 0 ? (
                  <p className="text-xs text-slate-500 px-3 py-4 text-center">No history yet.</p>
                ) : (
                  targetSessions.map(s => (
                    <button
                      key={s.id}
                      onClick={() => {
                        onSwitchSession(s.id);
                        setIsHistoryOpen(false);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-lg flex flex-col gap-1 transition-colors",
                        s.id === session?.id ? "bg-brand-50" : "hover:bg-slate-50"
                      )}
                    >
                      <span className={cn(
                        "text-sm font-medium line-clamp-1",
                        s.id === session?.id ? "text-brand-700" : "text-slate-700"
                      )}>{s.title}</span>
                      <span className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(s.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
        {session?.messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "flex gap-3",
              msg.role === 'user' ? "flex-row-reverse" : "flex-row"
            )}
          >
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
              msg.role === 'user' ? "bg-slate-100 text-slate-600" : "bg-brand-50 text-brand-600"
            )}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={cn(
              "max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed",
              msg.role === 'user' 
                ? "bg-brand-600 text-white rounded-tr-none" 
                : "bg-slate-50 text-slate-700 border border-slate-100 rounded-tl-none"
            )}>
              {msg.content}
              
              {msg.type === 'quiz' && (
                <div className="mt-4 p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-2 text-brand-600 font-medium">
                    <HelpCircle size={16} />
                    <span>Knowledge Check</span>
                  </div>
                  <p className="font-medium mb-3">{msg.data.question}</p>
                  <div className="space-y-2">
                    {msg.data.options.map((opt: string, idx: number) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const isCorrect = idx === msg.data.correctAnswer;
                          onSendMessage(`I think the answer is: ${opt}. ${isCorrect ? "Correct!" : "Incorrect."}`);
                        }}
                        className="w-full text-left p-2 rounded-lg border border-slate-100 hover:border-brand-300 hover:bg-brand-50 transition-colors text-xs"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {msg.type === 'artifact' && (
                <div className="mt-4 p-3 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center">
                      <FileText size={20} />
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">{msg.data.title}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider">{msg.data.type}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => onPreviewArtifact(msg.data.id)}
                    className="px-3 py-1.5 bg-slate-900 text-white text-xs rounded-lg hover:bg-slate-800 transition-colors"
                  >
                    Preview
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        ))}
        {isGenerating && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center">
              <Bot size={16} />
            </div>
            <div className="bg-slate-50 p-3 rounded-2xl rounded-tl-none flex gap-1 items-center">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-slate-100">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all text-sm"
          />
          <button
            type="submit"
            disabled={!input.trim() || isGenerating}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-50 disabled:hover:bg-brand-600 transition-colors"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
};
