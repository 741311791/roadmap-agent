'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
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
  Mail,
  Megaphone,
  Key,
  Activity,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
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
  const t = useTranslations();
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isRecentExpanded, setIsRecentExpanded] = useState(true);
  
  const { history } = useRoadmapStore();
  const { user, isAdmin } = useAuthStore();

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
      <div
        className={cn(
          'border-b border-border/5 transition-all duration-300',
          isCollapsed ? 'h-20 flex flex-col items-center justify-center gap-2 py-2' : 'h-14 flex items-center justify-between px-4'
        )}
      >
        {!isCollapsed ? (
          <>
            <Link href="/" className="flex items-center gap-2">
              <div className="relative w-8 h-8">
                <Image
                  src="/logo/svg_noword.svg"
                  alt="Fast Learning"
                  fill
                  className="object-contain"
                />
              </div>
              <div className="relative w-32 h-6">
                <Image
                  src="/logo/svg_onlyword.svg"
                  alt="Fast Learning"
                  fill
                  className="object-contain object-left"
                />
              </div>
            </Link>
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
              title={t('nav.collapseTooltip')}
            >
              <PanelLeftClose size={16} className="text-foreground/60" />
            </button>
          </>
        ) : (
          <>
            <Link href="/" className="flex items-center justify-center">
              <div className="relative w-8 h-8">
                <Image
                  src="/logo/svg_noword.svg"
                  alt="Fast Learning"
                  fill
                  className="object-contain"
                />
              </div>
            </Link>
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="w-6 h-6 flex items-center justify-center hover:bg-primary/5 rounded transition-colors"
              title={t('nav.expandTooltip')}
            >
              <PanelLeftOpen size={16} className="text-foreground/60" />
            </button>
          </>
        )}
      </div>

      {/* Search */}
      {!isCollapsed && (
        <div className="p-4">
          <div className="bg-white rounded-xl px-3 py-2 flex items-center gap-2 border border-border/5 shadow-sm">
            <Search size={16} className="text-foreground/40" />
            <input
              type="text"
              placeholder={t('common.search')}
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
              <Plus size={16} /> {t('common.newRoadmap')}
            </Button>
          </Link>
        </div>
      ) : (
        <div className="px-2 py-2 flex justify-center">
          <Tooltip text={t('common.newRoadmap')}>
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
              {t('nav.workspace')}
            </div>
          )}
          {isCollapsed && <div className="h-4" />}

          <NavItem
            icon={Home}
            label={t('common.home')}
            href="/home"
            active={isActive('/home')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={BookOpen}
            label={t('common.myRoadmaps')}
            href="/roadmaps"
            active={isActive('/roadmaps')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={ListTodo}
            label={t('common.tasks')}
            href="/tasks"
            active={isActive('/tasks')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={User}
            label={t('common.profile')}
            href="/profile"
            active={isActive('/profile')}
            isCollapsed={isCollapsed}
          />
          <NavItem
            icon={Trash2}
            label={t('common.trash')}
            href="/trash"
            active={isActive('/trash')}
            isCollapsed={isCollapsed}
          />

          {/* Admin Section - 仅超级管理员可见 */}
          {isAdmin() && (
            <>
              {!isCollapsed && (
                <div className="px-2 py-1 text-xs font-bold text-foreground/40 uppercase tracking-wider mt-6 mb-2">
                  {t('nav.admin')}
                </div>
              )}
              {isCollapsed && <div className="h-4" />}
              
              <NavItem
                icon={Mail}
                label={t('admin.waitlistManagement')}
                href="/admin/waitlist"
                active={isActive('/admin/waitlist')}
                isCollapsed={isCollapsed}
              />
              <NavItem
                icon={Megaphone}
                label={t('admin.customerEmailsManagement')}
                href="/admin/customer-emails"
                active={isActive('/admin/customer-emails')}
                isCollapsed={isCollapsed}
              />
              <NavItem
                icon={Key}
                label={t('admin.apiKeysManagement')}
                href="/admin/api-keys"
                active={isActive('/admin/api-keys')}
                isCollapsed={isCollapsed}
              />
              <NavItem
                icon={Activity}
                label={t('admin.celeryMonitor')}
                href="/admin/celery-monitor"
                active={isActive('/admin/celery-monitor')}
                isCollapsed={isCollapsed}
              />
            </>
          )}

          {/* Recent Section */}
          {!isCollapsed ? (
            <>
              <div className="px-2 py-1 mt-8 mb-2 flex items-center justify-between">
                <div className="text-xs font-bold text-foreground/40 uppercase tracking-wider">
                  {t('nav.recent')}
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
                      {t('nav.noRecentRoadmaps')}
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

      {/* User Footer */}
      <div className="p-4 border-t border-border/5">
        <UserMenu compact />
      </div>
    </div>
  );
}

