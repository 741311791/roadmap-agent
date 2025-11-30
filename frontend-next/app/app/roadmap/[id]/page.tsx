'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Layers,
  Clock,
  Calendar,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  Loader2,
} from 'lucide-react';

type ContentStatus = 'pending' | 'generating' | 'completed' | 'failed';
type Difficulty = 'easy' | 'medium' | 'hard';

interface MockConcept {
  concept_id: string;
  name: string;
  description: string;
  estimated_hours: number;
  difficulty: Difficulty;
  content_status: ContentStatus;
}

interface MockModule {
  module_id: string;
  name: string;
  description: string;
  concepts: MockConcept[];
}

interface MockStage {
  stage_id: string;
  name: string;
  description: string;
  order: number;
  modules: MockModule[];
}

interface MockRoadmap {
  roadmap_id: string;
  title: string;
  total_estimated_hours: number;
  recommended_completion_weeks: number;
  stages: MockStage[];
}

// Mock roadmap data - in real app, this would come from API/store
const mockRoadmap: MockRoadmap = {
  roadmap_id: 'demo',
  title: 'Full-Stack Web Development Mastery',
  total_estimated_hours: 120,
  recommended_completion_weeks: 16,
  stages: [
    {
      stage_id: 's1',
      name: 'Frontend Fundamentals',
      description: 'Master the basics of web development',
      order: 1,
      modules: [
        {
          module_id: 'm1',
          name: 'HTML & CSS',
          description: 'Building blocks of the web',
          concepts: [
            {
              concept_id: 'c1',
              name: 'HTML Structure & Semantics',
              description: 'Learn semantic HTML elements and document structure',
              estimated_hours: 3,
              difficulty: 'easy' as const,
              content_status: 'completed' as const,
            },
            {
              concept_id: 'c2',
              name: 'CSS Box Model & Layout',
              description: 'Understanding the box model, flexbox, and grid',
              estimated_hours: 4,
              difficulty: 'medium' as const,
              content_status: 'completed' as const,
            },
            {
              concept_id: 'c3',
              name: 'Responsive Design',
              description: 'Media queries and mobile-first approach',
              estimated_hours: 3,
              difficulty: 'medium' as const,
              content_status: 'pending' as const,
            },
          ],
        },
        {
          module_id: 'm2',
          name: 'JavaScript Essentials',
          description: 'Core JavaScript concepts',
          concepts: [
            {
              concept_id: 'c4',
              name: 'Variables & Data Types',
              description: 'Understanding JavaScript fundamentals',
              estimated_hours: 2,
              difficulty: 'easy' as const,
              content_status: 'pending' as const,
            },
            {
              concept_id: 'c5',
              name: 'Functions & Scope',
              description: 'Function declarations, expressions, and closures',
              estimated_hours: 4,
              difficulty: 'medium' as const,
              content_status: 'pending' as const,
            },
          ],
        },
      ],
    },
    {
      stage_id: 's2',
      name: 'React Framework',
      description: 'Modern frontend development with React',
      order: 2,
      modules: [
        {
          module_id: 'm3',
          name: 'React Core',
          description: 'React fundamentals and hooks',
          concepts: [
            {
              concept_id: 'c6',
              name: 'Components & Props',
              description: 'Building reusable UI components',
              estimated_hours: 3,
              difficulty: 'easy' as const,
              content_status: 'pending' as const,
            },
            {
              concept_id: 'c7',
              name: 'State & Hooks',
              description: 'Managing state with useState and useEffect',
              estimated_hours: 5,
              difficulty: 'medium' as const,
              content_status: 'pending' as const,
            },
          ],
        },
      ],
    },
  ],
};

export default function RoadmapDetailPage() {
  const params = useParams();
  const [expandedStages, setExpandedStages] = useState<string[]>(['s1']);
  const [expandedModules, setExpandedModules] = useState<string[]>(['m1']);

  const roadmap = mockRoadmap; // In real app: useRoadmapStore(state => state.currentRoadmap)

  // Calculate progress
  const allConcepts = roadmap.stages.flatMap((s) =>
    s.modules.flatMap((m) => m.concepts)
  );
  const completedCount = allConcepts.filter(
    (c) => c.content_status === 'completed'
  ).length;
  const progress = (completedCount / allConcepts.length) * 100;

  const toggleStage = (stageId: string) => {
    setExpandedStages((prev) =>
      prev.includes(stageId)
        ? prev.filter((id) => id !== stageId)
        : [...prev, stageId]
    );
  };

  const toggleModule = (moduleId: string) => {
    setExpandedModules((prev) =>
      prev.includes(moduleId)
        ? prev.filter((id) => id !== moduleId)
        : [...prev, moduleId]
    );
  };

  const getStatusIcon = (status: ContentStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-sage-600" />;
      case 'generating':
        return <Loader2 className="w-5 h-5 text-yellow-600 animate-spin" />;
      default:
        return <Circle className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'hard':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="max-w-4xl mx-auto py-12 px-6">
        {/* Back Navigation */}
        <Link
          href="/app/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-serif font-bold text-foreground mb-4">
            {roadmap.title}
          </h1>

          {/* Stats Badges */}
          <div className="flex items-center gap-3 flex-wrap mb-6">
            <Badge variant="sage" className="gap-1">
              <Layers size={14} />
              {roadmap.stages.length} Stages
            </Badge>
            <Badge variant="outline" className="gap-1">
              <Clock size={14} />
              {roadmap.total_estimated_hours} Hours
            </Badge>
            <Badge variant="outline" className="gap-1">
              <Calendar size={14} />
              {roadmap.recommended_completion_weeks} Weeks
            </Badge>
          </div>

          {/* Progress */}
          <div className="flex items-center gap-4">
            <Progress value={progress} className="flex-1 h-3" />
            <span className="text-sm font-medium text-foreground">
              {completedCount}/{allConcepts.length} completed
            </span>
          </div>
        </div>

        {/* Roadmap Tree */}
        <div className="space-y-4">
          {roadmap.stages.map((stage) => (
            <Card key={stage.stage_id}>
              <CardHeader
                className="cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleStage(stage.stage_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedStages.includes(stage.stage_id) ? (
                      <ChevronDown className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-muted-foreground" />
                    )}
                    <div>
                      <CardTitle className="text-lg font-serif">
                        Stage {stage.order}: {stage.name}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {stage.description}
                      </p>
                    </div>
                  </div>
                  <Badge variant="secondary">
                    {stage.modules.reduce(
                      (sum, m) => sum + m.concepts.length,
                      0
                    )}{' '}
                    concepts
                  </Badge>
                </div>
              </CardHeader>

              {expandedStages.includes(stage.stage_id) && (
                <CardContent className="pt-0">
                  <div className="space-y-3 ml-8">
                    {stage.modules.map((module) => (
                      <div
                        key={module.module_id}
                        className="border border-border rounded-lg overflow-hidden"
                      >
                        <button
                          className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
                          onClick={() => toggleModule(module.module_id)}
                        >
                          <div className="flex items-center gap-2">
                            {expandedModules.includes(module.module_id) ? (
                              <ChevronDown className="w-4 h-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            )}
                            <span className="font-medium">{module.name}</span>
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {module.concepts.length} concepts
                          </span>
                        </button>

                        {expandedModules.includes(module.module_id) && (
                          <div className="border-t border-border">
                            {module.concepts.map((concept) => (
                              <Link
                                key={concept.concept_id}
                                href={`/app/roadmap/${params.id}/learn/${concept.concept_id}`}
                                className="flex items-center gap-4 px-4 py-3 hover:bg-muted/50 transition-colors border-b border-border last:border-b-0"
                              >
                                {getStatusIcon(concept.content_status)}
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium truncate">
                                    {concept.name}
                                  </div>
                                  <div className="text-sm text-muted-foreground truncate">
                                    {concept.description}
                                  </div>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                  <span
                                    className={`text-xs px-2 py-0.5 rounded-full ${getDifficultyColor(
                                      concept.difficulty
                                    )}`}
                                  >
                                    {concept.difficulty}
                                  </span>
                                  <span className="text-sm text-muted-foreground">
                                    {concept.estimated_hours}h
                                  </span>
                                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                                </div>
                              </Link>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      </div>
    </ScrollArea>
  );
}

