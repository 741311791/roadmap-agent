import React from 'react';
import { Plus, Send, Bot, Sparkles, Clock, Settings, PanelRightClose, PanelRightOpen } from 'lucide-react';

interface RightSidebarProps {
    width: number;
    onResizeStart: () => void;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
}

const AgentTag = ({ label, color }: { label: string, color: string }) => (
    <div className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap flex items-center gap-1 ${color}`}>
        <Sparkles size={10} />
        {label}
    </div>
);

const PromptSuggestion = ({ icon: Icon, text }: { icon: any, text: string }) => (
    <div className="flex items-center gap-3 text-xs text-foreground/70 hover:text-foreground cursor-pointer group">
        <Icon size={14} className="text-sage-500 group-hover:scale-110 transition-transform" />
        <span>{text}</span>
    </div>
);

const Tooltip = ({ children, text }: { children: React.ReactNode, text: string }) => (
    <div className="relative group">
        {children}
        <div className="absolute right-full mr-2 px-2 py-1 bg-primary text-primary-foreground text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
            {text}
        </div>
    </div>
);

const RightSidebar: React.FC<RightSidebarProps> = ({ width, onResizeStart, isCollapsed, onToggleCollapse }) => {
    return (
        <div
            style={{ width }}
            className="flex flex-col bg-background border-l border-border/5 relative flex-shrink-0 transition-all duration-300"
        >
            {/* Resize Handle - only show when expanded */}
            {!isCollapsed && (
                <div
                    className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-sage-500/20 transition-colors z-10"
                    onMouseDown={onResizeStart}
                />
            )}

            {isCollapsed ? (
                // Collapsed state - vertical icon stack
                <div className="flex flex-col items-center py-6 h-full gap-4">
                    <button
                        onClick={onToggleCollapse}
                        className="w-10 h-10 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
                        title="Expand AI Assistant"
                    >
                        <PanelRightOpen size={18} className="text-foreground/60" />
                    </button>

                    <div className="h-px w-8 bg-primary/10"></div>

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
            ) : (
                // Full content when expanded
                <>
                    {/* Agent Header */}
                    <div className="h-14 flex items-center justify-between px-4 border-b border-border/5">
                        <button
                            onClick={onToggleCollapse}
                            className="w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
                            title="Collapse AI Assistant"
                        >
                            <PanelRightClose size={16} className="text-foreground/60" />
                        </button>
                        <div className="flex items-center gap-2">
                            <Plus size={18} className="text-foreground/40" />
                        </div>
                        <div className="flex items-center gap-4 text-foreground/40">
                            <div className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">L</div>
                            <div className="w-4 h-4 rounded-full border border-current"></div>
                        </div>
                    </div>

                    {/* Agent Content */}
                    <div className="flex-1 flex flex-col p-6 overflow-y-auto">
                        <div className="mt-8 mb-8 text-center">
                            <div className="w-16 h-16 bg-primary rounded-full mx-auto flex items-center justify-center text-primary-foreground mb-4 shadow-lg shadow-charcoal/20">
                                <Bot size={32} />
                            </div>
                            <h2 className="font-serif font-bold text-xl mb-1">Muset is thinking with you</h2>
                        </div>

                        {/* Chat Input Area */}
                        <div className="mt-auto">
                            <div className="bg-white rounded-3xl p-4 shadow-sm border border-border/5 relative">
                                <textarea
                                    className="w-full bg-transparent resize-none outline-none text-sm min-h-[80px] placeholder:text-foreground/30"
                                    placeholder="Drop an idea, let's shape..."
                                />
                                <div className="flex items-center justify-between mt-2">
                                    <button className="text-foreground/40 hover:text-foreground transition-colors">@</button>
                                    <div className="flex items-center gap-2">
                                        <button className="w-8 h-8 bg-primary/5 rounded-full flex items-center justify-center text-foreground/60 hover:bg-primary/10 transition-colors">
                                            <Plus size={16} />
                                        </button>
                                        <button className="w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center hover:scale-105 transition-transform">
                                            <Send size={14} />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Agent Suggestions */}
                            <div className="flex gap-2 mt-4 overflow-x-auto pb-2 scrollbar-hide">
                                <AgentTag label="Gemini 3 Pro" color="bg-sage-100 text-sage-700" />
                                <AgentTag label="Nano Banana Pro" color="bg-yellow-100 text-yellow-700" />
                            </div>

                            {/* Suggested Prompts */}
                            <div className="mt-6 space-y-3">
                                <PromptSuggestion icon={Sparkles} text="Draft a 3-month plan for learning Rust" />
                                <PromptSuggestion icon={Bot} text="Explain the concept of 'Ownership' in Rust" />
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default RightSidebar;
