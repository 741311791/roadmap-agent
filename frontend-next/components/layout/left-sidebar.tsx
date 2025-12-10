'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search,
  Home,
  User,
  Settings,
  Bot,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ChevronDown,
  ChevronRight,
  Trash2,
  ListTodo,
  BookOpen,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { UserMenu } from '@/components/user-menu';

interface LeftSidebarProps {
  className?: string;
}

// Tooltip component for collapsed state
function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  return (
    <div className="relative group">
      {children}
      <div className="absolute left-full ml-2 px-2 py-1 bg-primary text-primary-foreground text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
        {text}
      </div>
    </div>
  );
}

// Navigation item component
function NavItem({
  icon: Icon,
  label,
  href,
  active = false,
  isCollapsed = false,
}: {
  icon: React.ElementType;
  label: string;
  href: string;
  active?: boolean;
  isCollapsed?: boolean;
}) {
  const content = (
    <Link
      href={href}
      className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors',
        isCollapsed && 'justify-center',
        active
          ? 'bg-primary/5 text-foreground font-medium'
          : 'text-foreground/60 hover:bg-primary/5 hover:text-foreground'
      )}
    >
      <Icon size={18} />
      {!isCollapsed && <span className="text-sm">{label}</span>}
    </Link>
  );

  return isCollapsed ? <Tooltip text={label}>{content}</Tooltip> : content;
}

export function LeftSidebar({ className }: LeftSidebarProps) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isRecentExpanded, setIsRecentExpanded] = useState(true);
  
  const { history } = useRoadmapStore();

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + '/');

  // Get recent 3 roadmaps from store, sorted by created_at (most recent first)
  const recentRoadmaps = history
    .slice()
    .filter((item) => item.created_at) // 过滤掉没有 created_at 的项
    .sort((a, b) => new Date(b.created_at!).getTime() - new Date(a.created_at!).getTime())
    .slice(0, 3)
    .map((item) => ({
      id: item.roadmap_id,
      title: item.title,
    }));

  return (
    <div
      className={cn(
        'flex flex-col bg-background border-r border-border/5 relative flex-shrink-0 transition-all duration-300',
        isCollapsed ? 'w-[70px]' : 'w-[260px]',
        className
      )}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border/5">
        {!isCollapsed ? (
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs">
              M
            </div>
            <span className="font-serif font-bold text-lg tracking-tight">Muset</span>
          </Link>
        ) : (
          <Link href="/" className="mx-auto">
            <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs">
              M
            </div>
          </Link>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={cn(
            'w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors',
            isCollapsed && 'absolute top-4 right-2'
          )}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
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
            <input
              type="text"
              placeholder="Quick search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent text-sm outline-none w-full placeholder:text-foreground/30"
            />
          </div>
        </div>
      )}

      {/* New Roadmap Button */}
      {!isCollapsed ? (
        <div className="px-4 pb-2">
          <Link href="/new">
            <Button variant="sage" className="w-full gap-2">
              <Plus size={16} /> New Roadmap
            </Button>
          </Link>
        </div>
      ) : (
        <div className="px-2 py-2 flex justify-center">
          <Tooltip text="New Roadmap">
            <Link href="/new">
              <Button variant="sage" size="icon" className="w-10 h-10">
                <Plus size={18} />
              </Button>
            </Link>
          </Tooltip>
        </div>
      )}

      {/* Navigation */}
      <ScrollArea className="flex-1 px-2">
        <nav className="space-y-1">
          {!isCollapsed && (
            <div className="px-2 py-1 text-xs font-bold text-foreground/40 uppercase tracking-wider mt-4 mb-2">
              Workspace
            </div>
          )}
          {isCollapsed && <div className="h-4" />}

          <NavItem
            icon={Home}
            label="Home"
            href="/home"
            active={isActive('/home')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={BookOpen}
            label="My Roadmaps"
            href="/roadmaps"
            active={isActive('/roadmaps')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={ListTodo}
            label="Tasks"
            href="/tasks"
            active={isActive('/tasks')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={User}
            label="Profile"
            href="/profile"
            active={isActive('/profile')}
            isCollapsed={isCollapsed}
          />

          {/* Recent Section */}
          {!isCollapsed ? (
            <>
              <div className="px-2 py-1 mt-8 mb-2 flex items-center justify-between">
                <div className="text-xs font-bold text-foreground/40 uppercase tracking-wider">
                  Recent
                </div>
                <button
                  onClick={() => setIsRecentExpanded(!isRecentExpanded)}
                  className="w-5 h-5 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
                  title={isRecentExpanded ? 'Collapse' : 'Expand'}
                >
                  {isRecentExpanded ? (
                    <ChevronDown size={14} className="text-foreground/40" />
                  ) : (
                    <ChevronRight size={14} className="text-foreground/40" />
                  )}
                </button>
              </div>
              {isRecentExpanded && (
                <>
                  {recentRoadmaps.length > 0 ? (
                    <div className="space-y-1">
                      {recentRoadmaps.map((roadmap) => (
                        <NavItem
                          key={roadmap.id}
                          icon={Bot}
                          label={roadmap.title}
                          href={`/roadmap/${roadmap.id}`}
                          active={isActive(`/roadmap/${roadmap.id}`)}
                          isCollapsed={false}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="px-2 py-2 text-xs text-foreground/30">
                      No recent roadmaps
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <>
              {recentRoadmaps.length > 0 && (
                <>
                  <div className="h-8" />
                  {recentRoadmaps.map((roadmap) => (
                    <NavItem
                      key={roadmap.id}
                      icon={Bot}
                      label={roadmap.title}
                      href={`/roadmap/${roadmap.id}`}
                      active={isActive(`/roadmap/${roadmap.id}`)}
                      isCollapsed={true}
                    />
                  ))}
                </>
              )}
            </>
          )}
        </nav>
      </ScrollArea>

      {/* Trash Button (Above User Footer) */}
      <div className="px-4 pb-2 border-t border-border/5">
        {!isCollapsed ? (
          <NavItem
            icon={Trash2}
            label="Trash"
            href="/trash"
            active={isActive('/trash')}
            isCollapsed={false}
          />
        ) : (
          <div className="flex justify-center">
            <Tooltip text="Trash">
              <Link
                href="/trash"
                className={cn(
                  'flex items-center justify-center px-3 py-2 rounded-lg cursor-pointer transition-colors',
                  isActive('/trash')
                    ? 'bg-primary/5 text-foreground font-medium'
                    : 'text-foreground/60 hover:bg-primary/5 hover:text-foreground'
                )}
              >
                <Trash2 size={18} />
              </Link>
            </Tooltip>
          </div>
        )}
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-border/5">
        <UserMenu />
      </div>
    </div>
  );
}

