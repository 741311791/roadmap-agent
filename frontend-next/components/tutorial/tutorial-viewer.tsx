'use client';

import { useState, useEffect } from 'react';
import { MarkdownRenderer } from './markdown-renderer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  BookOpen, 
  Clock, 
  CheckCircle2, 
  ChevronRight,
  Target,
  Lightbulb,
  ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Tutorial } from '@/types/generated/models';

interface TutorialViewerProps {
  tutorial: Tutorial;
  onComplete?: () => void;
  onNext?: () => void;
  className?: string;
  readingProgress?: number;
  onProgressUpdate?: (progress: number) => void;
}

/**
 * TutorialViewer - 教程查看器组件
 * 
 * 功能:
 * - Markdown 内容渲染
 * - 代码高亮
 * - 目录导航
 * - 阅读进度追踪
 * - 学习目标展示
 * - 下一步建议
 */
export function TutorialViewer({
  tutorial,
  onComplete,
  onNext,
  className,
  readingProgress = 0,
  onProgressUpdate
}: TutorialViewerProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  // 监听滚动进度
  useEffect(() => {
    const handleScroll = () => {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.scrollY;
      const progress = (scrollTop / (documentHeight - windowHeight)) * 100;
      
      setScrollProgress(Math.min(100, Math.max(0, progress)));
      onProgressUpdate?.(progress);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [onProgressUpdate]);

  // 生成目录
  const tableOfContents = tutorial.sections.map(section => ({
    id: section.section_id,
    title: section.title,
    order: section.order
  }));

  // 合并所有章节内容用于渲染
  const fullContent = tutorial.sections
    .sort((a, b) => a.order - b.order)
    .map(section => `## ${section.title}\n\n${section.content}`)
    .join('\n\n');

  return (
    <div className={cn('space-y-6', className)}>
      {/* 教程头部信息 */}
      <TutorialHeader 
        tutorial={tutorial}
        scrollProgress={scrollProgress}
      />

      {/* 主内容区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧：目录（桌面端） */}
        <aside className="hidden lg:block lg:col-span-1">
          <TableOfContents
            sections={tableOfContents}
            activeSection={activeSection}
            onSectionClick={(sectionId) => {
              setActiveSection(sectionId);
              // 滚动到对应章节
              const element = document.getElementById(sectionId);
              element?.scrollIntoView({ behavior: 'smooth' });
            }}
          />
        </aside>

        {/* 中间：教程内容 */}
        <main className="lg:col-span-3 space-y-6">
          {/* 学习目标 */}
          {tutorial.learning_objectives && tutorial.learning_objectives.length > 0 && (
            <LearningObjectives objectives={tutorial.learning_objectives} />
          )}

          {/* Markdown 内容 */}
          <Card>
            <CardContent className="pt-6">
              <MarkdownRenderer content={fullContent} />
            </CardContent>
          </Card>

          {/* 关键要点 */}
          {tutorial.key_takeaways && tutorial.key_takeaways.length > 0 && (
            <KeyTakeaways takeaways={tutorial.key_takeaways} />
          )}

          {/* 下一步建议 */}
          {tutorial.next_steps && tutorial.next_steps.length > 0 && (
            <NextSteps 
              steps={tutorial.next_steps}
              onComplete={onComplete}
              onNext={onNext}
            />
          )}
        </main>
      </div>
    </div>
  );
}

/**
 * TutorialHeader - 教程头部信息
 */
function TutorialHeader({
  tutorial,
  scrollProgress
}: {
  tutorial: Tutorial;
  scrollProgress: number;
}) {
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300';
      case 'hard':
        return 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-2xl mb-2">{tutorial.title}</CardTitle>
              <p className="text-muted-foreground">{tutorial.summary}</p>
            </div>
            <Badge className={getDifficultyColor(tutorial.difficulty)}>
              {tutorial.difficulty}
            </Badge>
          </div>

          {/* 元数据 */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>{tutorial.estimated_time_minutes} 分钟</span>
            </div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              <span>{tutorial.sections.length} 个章节</span>
            </div>
            {tutorial.prerequisites && tutorial.prerequisites.length > 0 && (
              <div className="flex items-center gap-2">
                <span>前置要求: {tutorial.prerequisites.length}</span>
              </div>
            )}
          </div>

          {/* 阅读进度条 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">阅读进度</span>
              <span className="font-medium">{Math.round(scrollProgress)}%</span>
            </div>
            <Progress value={scrollProgress} className="h-2" />
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

/**
 * TableOfContents - 目录导航
 */
function TableOfContents({
  sections,
  activeSection,
  onSectionClick
}: {
  sections: Array<{ id: string; title: string; order: number }>;
  activeSection: string | null;
  onSectionClick: (id: string) => void;
}) {
  return (
    <Card className="sticky top-4">
      <CardHeader>
        <CardTitle className="text-base">目录</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => onSectionClick(section.id)}
            className={cn(
              'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
              'hover:bg-muted',
              activeSection === section.id && 'bg-primary/10 text-primary font-medium'
            )}
          >
            <div className="flex items-center gap-2">
              <ChevronRight className="w-4 h-4 shrink-0" />
              <span className="truncate">{section.title}</span>
            </div>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

/**
 * LearningObjectives - 学习目标
 */
function LearningObjectives({ objectives }: { objectives: string[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Target className="w-5 h-5" />
          学习目标
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {objectives.map((objective, index) => (
            <li key={index} className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <span className="text-sm">{objective}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/**
 * KeyTakeaways - 关键要点
 */
function KeyTakeaways({ takeaways }: { takeaways: string[] }) {
  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Lightbulb className="w-5 h-5" />
          关键要点
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {takeaways.map((takeaway, index) => (
            <li key={index} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium shrink-0">
                {index + 1}
              </div>
              <span className="text-sm pt-0.5">{takeaway}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/**
 * NextSteps - 下一步建议
 */
function NextSteps({
  steps,
  onComplete,
  onNext
}: {
  steps: string[];
  onComplete?: () => void;
  onNext?: () => void;
}) {
  return (
    <Card className="bg-muted/30">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <ArrowRight className="w-5 h-5" />
          下一步
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2">
          {steps.map((step, index) => (
            <li key={index} className="flex items-start gap-3 text-sm">
              <span className="text-muted-foreground">{index + 1}.</span>
              <span>{step}</span>
            </li>
          ))}
        </ul>

        <Separator />

        <div className="flex items-center gap-3">
          {onComplete && (
            <Button onClick={onComplete} className="flex-1">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              标记为已完成
            </Button>
          )}
          {onNext && (
            <Button onClick={onNext} variant="outline" className="flex-1">
              下一个概念
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

