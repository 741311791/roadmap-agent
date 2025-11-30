import React from 'react';
import { Search, Home, User, Settings, Bot, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

interface LeftSidebarProps {
    width: number;
    onResizeStart: () => void;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
}

const Tooltip = ({ children, text }: { children: React.ReactNode, text: string }) => (
    <div className="relative group">
        {children}
        <div className="absolute left-full ml-2 px-2 py-1 bg-primary text-primary-foreground text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
            {text}
        </div>
    </div>
);

const NavItem = ({ icon: Icon, label, active = false, isCollapsed = false, onClick }: { icon: any, label: string, active?: boolean, isCollapsed?: boolean, onClick?: () => void }) => {
    const content = (
        <div
            onClick={onClick}
            className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2 rounded-lg cursor-pointer transition-colors ${active ? 'bg-primary/5 text-foreground font-medium' : 'text-foreground/60 hover:bg-primary/5 hover:text-foreground'}`}
        >
            <Icon size={18} />
            {!isCollapsed && <span className="text-sm">{label}</span>}
        </div>
    );

    return isCollapsed ? <Tooltip text={label}>{content}</Tooltip> : content;
};

const LeftSidebar: React.FC<LeftSidebarProps> = ({ width, onResizeStart, isCollapsed, onToggleCollapse }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const isActive = (path: string) => location.pathname === path;

    return (
        <div
            style={{ width }}
            className="flex flex-col bg-background border-r border-border/5 relative flex-shrink-0 transition-all duration-300"
        >
            {/* Header */}
            <div className="h-14 flex items-center justify-between px-4 border-b border-border/5">
                {!isCollapsed && (
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs">M</div>
                        <span className="font-serif font-bold text-lg tracking-tight">Muset</span>
                    </div>
                )}
                {isCollapsed && (
                    <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs mx-auto">M</div>
                )}
                <button
                    onClick={onToggleCollapse}
                    className={`${isCollapsed ? 'absolute top-4 right-2' : ''} w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors`}
                    title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    {isCollapsed ? (
                        <PanelLeftOpen size={16} className="text-foreground/60" />
                    ) : (
                        <PanelLeftClose size={16} className="text-foreground/60" />
                    )}
                </button>
            </div>

            {/* Search */}
            {!isCollapsed && (
                <div className="p-4">
                    <div className="bg-white rounded-xl px-3 py-2 flex items-center gap-2 border border-border/5 shadow-sm">
                        <Search size={16} className="text-foreground/40" />
                        <input type="text" placeholder="Quick search..." className="bg-transparent text-sm outline-none w-full placeholder:text-foreground/30" />
                    </div>
                </div>
            )}

            {/* Navigation */}
            <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
                {!isCollapsed && <div className="px-2 py-1 text-xs font-bold text-foreground/40 uppercase tracking-wider mt-4 mb-2">Workspace</div>}
                {isCollapsed && <div className="h-4"></div>}

                <NavItem
                    icon={Home}
                    label="Home"
                    active={isActive('/agents/home')}
                    isCollapsed={isCollapsed}
                    onClick={() => navigate('/agents/home')}
                />
                <NavItem
                    icon={User}
                    label="Profile"
                    active={isActive('/agents/profile')}
                    isCollapsed={isCollapsed}
                    onClick={() => navigate('/agents/profile')}
                />

                {!isCollapsed && <div className="px-2 py-1 text-xs font-bold text-foreground/40 uppercase tracking-wider mt-8 mb-2">Recent</div>}
                {isCollapsed && <div className="h-8"></div>}

                <NavItem icon={Bot} label="Python Mastery" isCollapsed={isCollapsed} onClick={() => navigate('/agents/home/demo')} />
                <NavItem icon={Bot} label="React Architecture" isCollapsed={isCollapsed} onClick={() => navigate('/agents/home/demo')} />
                <NavItem icon={Bot} label="System Design 101" isCollapsed={isCollapsed} onClick={() => navigate('/agents/home/demo')} />
            </nav>

            {/* User Footer */}
            <div className="p-4 border-t border-border/5">
                {isCollapsed ? (
                    <Tooltip text="Louie - Settings">
                        <div className="w-8 h-8 rounded-full bg-sage-200 flex items-center justify-center text-foreground font-bold text-xs mx-auto cursor-pointer hover:bg-sage-300 transition-colors">L</div>
                    </Tooltip>
                ) : (
                    <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-primary/5 cursor-pointer transition-colors">
                        <div className="w-8 h-8 rounded-full bg-sage-200 flex items-center justify-center text-foreground font-bold text-xs">L</div>
                        <div className="flex-1 overflow-hidden">
                            <div className="text-sm font-medium truncate">Louie</div>
                            <div className="text-xs text-foreground/50 truncate">Pro Plan</div>
                        </div>
                        <Settings size={16} className="text-foreground/40" />
                    </div>
                )}
            </div>

            {/* Resize Handle */}
            {!isCollapsed && (
                <div
                    className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-sage-500/20 transition-colors z-10"
                    onMouseDown={onResizeStart}
                />
            )}
        </div>
    );
};

export default LeftSidebar;
