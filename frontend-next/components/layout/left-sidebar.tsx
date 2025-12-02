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
} from 'lucide-react';

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

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + '/');

  // Mock recent roadmaps - in real app, this would come from store
  const recentRoadmaps = [
    { id: 'demo', title: 'Python Mastery' },
    { id: 'demo2', title: 'React Architecture' },
    { id: 'demo3', title: 'System Design 101' },
  ];

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
          <Link href="/app/new">
            <Button variant="sage" className="w-full gap-2">
              <Plus size={16} /> New Roadmap
            </Button>
          </Link>
        </div>
      ) : (
        <div className="px-2 py-2 flex justify-center">
          <Tooltip text="New Roadmap">
            <Link href="/app/new">
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
            href="/app/home"
            active={isActive('/app/home')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={User}
            label="Profile"
            href="/app/profile"
            active={isActive('/app/profile')}
            isCollapsed={isCollapsed}
          />

          {!isCollapsed && (
            <div className="px-2 py-1 text-xs font-bold text-foreground/40 uppercase tracking-wider mt-8 mb-2">
              Recent
            </div>
          )}
          {isCollapsed && <div className="h-8" />}

          {recentRoadmaps.map((roadmap) => (
            <NavItem
              key={roadmap.id}
              icon={Bot}
              label={roadmap.title}
              href={`/app/roadmap/${roadmap.id}`}
              active={isActive(`/app/roadmap/${roadmap.id}`)}
              isCollapsed={isCollapsed}
            />
          ))}
        </nav>
      </ScrollArea>

      {/* User Footer */}
      <div className="p-4 border-t border-border/5">
        {isCollapsed ? (
          <Tooltip text="User - Settings">
            <Link href="/app/settings" className="block">
              <div className="w-8 h-8 rounded-full bg-sage-200 flex items-center justify-center text-foreground font-bold text-xs mx-auto cursor-pointer hover:bg-sage-300 transition-colors">
                L
              </div>
            </Link>
          </Tooltip>
        ) : (
          <Link
            href="/app/settings"
            className="flex items-center gap-3 p-2 rounded-xl hover:bg-primary/5 cursor-pointer transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-sage-200 flex items-center justify-center text-foreground font-bold text-xs">
              L
            </div>
            <div className="flex-1 overflow-hidden">
              <div className="text-sm font-medium truncate">Learner</div>
              <div className="text-xs text-foreground/50 truncate">Free Plan</div>
            </div>
            <Settings size={16} className="text-foreground/40" />
          </Link>
        )}
      </div>
    </div>
  );
}

