'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/common/empty-state';
import { Plus, Clock, CheckCircle2, BookOpen, ArrowRight } from 'lucide-react';

// Format date consistently to avoid hydration mismatch
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Mock data - in real app, this would come from API/store
const mockRoadmaps = [
  {
    id: 'demo',
    title: 'Full-Stack Web Development',
    status: 'in_progress',
    totalConcepts: 24,
    completedConcepts: 8,
    totalHours: 120,
    lastAccessedAt: '2024-11-28T10:30:00Z',
  },
  {
    id: 'demo2',
    title: 'Python for Data Science',
    status: 'completed',
    totalConcepts: 18,
    completedConcepts: 18,
    totalHours: 80,
    lastAccessedAt: '2024-11-20T15:00:00Z',
  },
];

export default function DashboardPage() {
  const [roadmaps] = useState(mockRoadmaps);

  if (roadmaps.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <EmptyState
          icon={BookOpen}
          title="No roadmaps yet"
          description="Create your first personalized learning roadmap to get started."
          action={{
            label: 'Create Roadmap',
            onClick: () => {
              window.location.href = '/app/new';
            },
          }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-serif font-bold text-foreground">My Roadmaps</h1>
          <p className="text-muted-foreground mt-1">
            Continue learning or create a new roadmap
          </p>
        </div>
        <Link href="/app/new">
          <Button variant="sage" className="gap-2">
            <Plus size={16} /> New Roadmap
          </Button>
        </Link>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Total Roadmaps"
          value={roadmaps.length}
          icon={BookOpen}
        />
        <StatCard
          label="Hours Invested"
          value={roadmaps.reduce((sum, r) => sum + (r.completedConcepts / r.totalConcepts) * r.totalHours, 0).toFixed(0)}
          icon={Clock}
        />
        <StatCard
          label="Concepts Mastered"
          value={roadmaps.reduce((sum, r) => sum + r.completedConcepts, 0)}
          icon={CheckCircle2}
        />
      </div>

      {/* Roadmap List */}
      <div className="space-y-4">
        {roadmaps.map((roadmap) => (
          <RoadmapCard key={roadmap.id} roadmap={roadmap} />
        ))}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-sage-100 flex items-center justify-center">
            <Icon className="w-5 h-5 text-sage-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RoadmapCard({
  roadmap,
}: {
  roadmap: {
    id: string;
    title: string;
    status: string;
    totalConcepts: number;
    completedConcepts: number;
    totalHours: number;
    lastAccessedAt: string;
  };
}) {
  const progress = (roadmap.completedConcepts / roadmap.totalConcepts) * 100;
  const isCompleted = roadmap.status === 'completed';

  return (
    <Link href={`/app/roadmap/${roadmap.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-xl font-serif">{roadmap.title}</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Last accessed {formatDate(roadmap.lastAccessedAt)}
              </p>
            </div>
            <Badge variant={isCompleted ? 'success' : 'sage'}>
              {isCompleted ? 'Completed' : 'In Progress'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <BookOpen size={14} />
                {roadmap.completedConcepts}/{roadmap.totalConcepts} concepts
              </span>
              <span className="flex items-center gap-1">
                <Clock size={14} />
                {roadmap.totalHours}h total
              </span>
            </div>
            <div className="flex items-center gap-4">
              {/* Progress Bar */}
              <div className="w-32 h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-sage-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-sm font-medium text-foreground">
                {progress.toFixed(0)}%
              </span>
              <ArrowRight size={16} className="text-muted-foreground" />
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

