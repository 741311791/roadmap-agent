'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, BookOpen, Plus } from 'lucide-react';

export default function MyRoadmapsPage() {
  return (
    <ScrollArea className="h-full">
      <div className="max-w-6xl mx-auto py-8 px-6">
        {/* Back Navigation */}
        <Link
          href="/app/home"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Home
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <BookOpen size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                My Learning Journeys
              </h1>
              <p className="text-sm text-muted-foreground">
                All your roadmaps in one place
              </p>
            </div>
          </div>
          <Link href="/app/new">
            <Button variant="sage" className="gap-2">
              <Plus size={16} /> New Roadmap
            </Button>
          </Link>
        </div>

        {/* Placeholder Content */}
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-20 h-20 rounded-full bg-sage-100 flex items-center justify-center mb-6">
            <BookOpen size={32} className="text-sage-400" />
          </div>
          <h2 className="text-xl font-serif font-semibold text-foreground mb-2">
            Coming Soon
          </h2>
          <p className="text-muted-foreground max-w-md mb-6">
            This page will display all your learning roadmaps with filtering and search capabilities.
          </p>
          <Link href="/app/home">
            <Button variant="outline">
              Return to Home
            </Button>
          </Link>
        </div>
      </div>
    </ScrollArea>
  );
}

