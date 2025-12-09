'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { EmptyState } from '@/components/common/empty-state';
import { RoadmapCard, CoverImage, MyRoadmap, CommunityRoadmap } from '@/components/roadmap';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  BookOpen,
  ArrowRight,
  Sparkles,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { getUserRoadmaps } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/store/auth-store';

// Mock data - Community Roadmaps
const communityRoadmaps: CommunityRoadmap[] = [
  {
    id: 'cr-1',
    title: 'Machine Learning Engineer Path',
    author: {
      name: 'Alex Chen',
      avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=64&h=64&fit=crop',
    },
    likes: 1284,
    views: 15420,
    tags: ['Python', 'ML', 'Advanced'],
    topic: 'machine learning',
  },
  {
    id: 'cr-2',
    title: 'DevOps Engineering Fundamentals',
    author: {
      name: 'Sarah Kim',
      avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=64&h=64&fit=crop',
    },
    likes: 892,
    views: 10250,
    tags: ['Docker', 'CI/CD', 'Cloud'],
    topic: 'devops',
  },
  {
    id: 'cr-3',
    title: 'Frontend Development with Vue.js',
    author: {
      name: 'Mike Johnson',
      avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&h=64&fit=crop',
    },
    likes: 756,
    views: 8930,
    tags: ['Vue.js', 'JavaScript', 'Beginner'],
    topic: 'vue',
  },
  {
    id: 'cr-4',
    title: 'iOS App Development with Swift',
    author: {
      name: 'Emily Davis',
      avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop',
    },
    likes: 623,
    views: 7840,
    tags: ['Swift', 'iOS', 'Mobile'],
    topic: 'ios',
  },
  {
    id: 'cr-5',
    title: 'System Design Interview Prep',
    author: {
      name: 'David Wang',
      avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=64&h=64&fit=crop',
    },
    likes: 2156,
    views: 24680,
    tags: ['Architecture', 'Interview', 'Advanced'],
    topic: 'software',
  },
  {
    id: 'cr-6',
    title: 'Cybersecurity Fundamentals',
    author: {
      name: 'Lisa Brown',
      avatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=64&h=64&fit=crop',
    },
    likes: 534,
    views: 6720,
    tags: ['Security', 'Networking', 'Beginner'],
    topic: 'cybersecurity',
  },
];

// Create New Roadmap Card (matching size)
function CreateRoadmapCard() {
  return (
    <Link href="/new" className="group flex-shrink-0 w-[220px]">
      <Card className="overflow-hidden h-full border-2 border-dashed border-sage-200 hover:border-sage-400 hover:bg-sage-50/50 transition-all duration-300 flex flex-col items-center justify-center">
        <div className="aspect-[16/9] w-full bg-sage-50 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-sage-100 flex items-center justify-center group-hover:bg-sage-200 transition-colors">
            <Plus size={24} className="text-sage-600" />
          </div>
        </div>
        <CardContent className="p-4 text-center">
          <h3 className="font-serif font-medium text-sm text-foreground mb-1">
            Create New
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Start learning journey
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

// Horizontal Scroll Container with Navigation
function HorizontalScrollSection({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    
    const scrollAmount = 240; // card width + gap
    const newScrollLeft = direction === 'left' 
      ? el.scrollLeft - scrollAmount 
      : el.scrollLeft + scrollAmount;
    
    el.scrollTo({ left: newScrollLeft, behavior: 'smooth' });
    
    // Update button states after scroll animation
    setTimeout(checkScroll, 350);
  };

  return (
    <div className={`relative group/scroll ${className}`}>
      {/* Left Navigation Button */}
      {canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/95 shadow-lg border border-border/50 flex items-center justify-center text-foreground/70 hover:text-foreground hover:bg-white transition-all opacity-0 group-hover/scroll:opacity-100 -translate-x-1/2"
        >
          <ChevronLeft size={20} />
        </button>
      )}

      {/* Scrollable Container */}
      <div
        ref={scrollRef}
        onScroll={checkScroll}
        className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 scroll-smooth"
      >
        {children}
      </div>

      {/* Right Navigation Button */}
      {canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/95 shadow-lg border border-border/50 flex items-center justify-center text-foreground/70 hover:text-foreground hover:bg-white transition-all opacity-0 group-hover/scroll:opacity-100 translate-x-1/2"
        >
          <ChevronRight size={20} />
        </button>
      )}

      {/* Fade edges */}
      <div className="absolute left-0 top-0 bottom-2 w-8 bg-gradient-to-r from-background to-transparent pointer-events-none opacity-0 group-hover/scroll:opacity-100 transition-opacity" />
      <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-background to-transparent pointer-events-none" />
    </div>
  );
}

// Section Header Component
function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  action,
}: {
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  action?: {
    label: string;
    href: string;
  };
}) {
  return (
    <div className="flex items-end justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-sage-100 flex items-center justify-center">
          <Icon size={18} className="text-sage-600" />
        </div>
        <div>
          <h2 className="text-lg font-serif font-bold text-foreground">{title}</h2>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </div>
      {action && (
        <Link
          href={action.href}
          className="flex items-center gap-1 text-sm text-sage-600 hover:text-sage-700 font-medium transition-colors"
        >
          {action.label}
          <ArrowRight size={14} />
        </Link>
      )}
    </div>
  );
}

// Main Home Page Component
export default function HomePage() {
  const { history, setHistory } = useRoadmapStore();
  const { getUserId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [showCommunity, setShowCommunity] = useState(true);
  
  // Fetch user roadmaps on mount
  useEffect(() => {
    const fetchRoadmaps = async () => {
      const userId = getUserId();
      if (!userId) {
        console.error('[Home] No user ID');
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        const response = await getUserRoadmaps(userId);
        // Map API response to store format
        const historyData = response.roadmaps.map((item) => {
          let status = item.status || 'completed';
          
          return {
            roadmap_id: item.roadmap_id,
            title: item.title,
            created_at: item.created_at,
            total_concepts: item.total_concepts,
            completed_concepts: item.completed_concepts,
            topic: item.topic || undefined,
            status,
            task_id: item.task_id,
            task_status: item.task_status,
            current_step: item.current_step,
          };
        });
        setHistory(historyData as any);
      } catch (error) {
        console.error('Failed to fetch roadmaps:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchRoadmaps();
  }, [getUserId, setHistory]);
  
  // Map history to roadmap format for display
  const allRoadmaps: MyRoadmap[] = history.map((item) => ({
    id: item.roadmap_id,
    title: item.title,
    status: item.status || 'completed',
    totalConcepts: item.total_concepts || 0,
    completedConcepts: item.completed_concepts || 0,
    totalHours: 0,
    lastAccessedAt: item.created_at || new Date().toISOString(),
    topic: item.topic || item.title.toLowerCase(),
    taskId: (item as any).task_id || null,
    taskStatus: (item as any).task_status || null,
    currentStep: (item as any).current_step || null,
  }));
  
  // 只显示前 4 个路线图
  const displayedRoadmaps = allRoadmaps.slice(0, 4);
  const hasMore = allRoadmaps.length > 4;
  const hasRoadmaps = allRoadmaps.length > 0;

  return (
    <ScrollArea className="h-full">
      <div className="max-w-6xl mx-auto py-8 px-6">
        {/* Welcome Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sage-600 mb-2">
            <Sparkles size={16} />
            <span className="text-sm font-medium">Welcome back</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-serif font-bold text-foreground mb-1">
            Continue Your Learning Journey
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Pick up where you left off or explore new roadmaps created by the community.
          </p>
        </div>

        {/* Section A: My Roadmaps */}
        <section className="mb-10">
          <SectionHeader
            icon={BookOpen}
            title="My Learning Journeys"
            subtitle={hasRoadmaps ? `${allRoadmaps.length} roadmaps` : undefined}
            action={hasMore ? { label: 'View all', href: '/roadmaps' } : undefined}
          />

          {hasRoadmaps ? (
            <HorizontalScrollSection>
              <CreateRoadmapCard />
              {displayedRoadmaps.map((roadmap) => (
                <RoadmapCard key={roadmap.id} roadmap={roadmap} type="my" showActions={false} />
              ))}
            </HorizontalScrollSection>
          ) : (
            <EmptyState
              icon={BookOpen}
              title="No roadmaps yet"
              description="Create your first personalized learning roadmap to get started."
              action={{
                label: 'Create Roadmap',
                onClick: () => {
                  window.location.href = '/new';
                },
              }}
            />
          )}
        </section>

        {/* Section B: Community Picks (with animation) */}
        <AnimatePresence>
          {showCommunity && (
            <motion.section
              initial={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 100 }}
              transition={{ duration: 0.5 }}
            >
              <SectionHeader
                icon={TrendingUp}
                title="Popular on Muset"
                subtitle="Discover roadmaps loved by the community"
                action={{ label: 'Explore all', href: '/app/explore' }}
              />

              <HorizontalScrollSection>
                {communityRoadmaps.map((roadmap) => (
                  <RoadmapCard key={roadmap.id} roadmap={roadmap} type="community" showActions={false} />
                ))}
              </HorizontalScrollSection>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Bottom Spacing */}
        <div className="h-8" />
      </div>
    </ScrollArea>
  );
}
