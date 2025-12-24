'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import type { Concept, LearningPreferences } from '@/types/generated/models';
import type { ResourcesResponse, QuizResponse } from '@/types/generated/services';
import { getConceptResources, getConceptQuiz, updateConceptProgress, submitQuizAttempt } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { FailedContentAlert } from '@/components/common/retry-content-button';
import { GeneratingContentLoader } from '@/components/common/generating-content-loader';
import { StaleStatusDetector } from '@/components/common/stale-status-detector';
import { 
  Sparkles, 
  BookOpen, 
  Clock, 
  BookOpenText,
  Presentation,
  Mic,
  Network,
  ChevronRight,
  Lock,
  ExternalLink,
  Video,
  FileText as FileTextIcon,
  BookMarked,
  Code,
  Award,
  CheckCircle2,
  Circle,
  Loader2 as Loader2Icon,
  Loader2,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

/**
 * Content Type for retry tracking
 */
type ContentType = 'tutorial' | 'resources' | 'quiz';

/**
 * Learning Format Types
 */
type LearningFormat = 'immersive-text' | 'learning-resources' | 'quiz' | 'slides' | 'audio' | 'mindmap';

interface LearningFormatOption {
  id: LearningFormat;
  label: string;
  icon: React.ElementType;
  available: boolean;
  description?: string;
}

const LEARNING_FORMATS: LearningFormatOption[] = [
  { id: 'immersive-text', label: 'Immersive Text', icon: BookOpenText, available: true, description: 'Rich reading experience' },
  { id: 'learning-resources', label: 'Learning Resources', icon: BookOpen, available: true, description: 'Curated learning materials' },
  { id: 'quiz', label: 'Quiz', icon: Sparkles, available: true, description: 'Test your knowledge' },
  { id: 'slides', label: 'Slides & Narration', icon: Presentation, available: false, description: 'Visual presentation' },
  { id: 'audio', label: 'Audio Lesson', icon: Mic, available: false, description: 'Podcast-style lesson' },
  { id: 'mindmap', label: 'Mindmap', icon: Network, available: false, description: 'Visual knowledge graph' },
];

/**
 * LearningFormatTabs - 学习形式选项卡
 */
function LearningFormatTabs({ 
  activeFormat, 
  onFormatChange 
}: { 
  activeFormat: LearningFormat;
  onFormatChange: (format: LearningFormat) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-2 p-4 bg-gradient-to-b from-stone-50 to-transparent rounded-xl mb-6">
      {LEARNING_FORMATS.map((format) => {
        const Icon = format.icon;
        const isActive = activeFormat === format.id;
        const isAvailable = format.available;
        
        return (
          <button
            key={format.id}
            onClick={() => isAvailable && onFormatChange(format.id)}
            disabled={!isAvailable}
            className={cn(
              "flex flex-col items-center gap-2 px-5 py-3 rounded-xl transition-all duration-300 min-w-[100px]",
              isActive 
                ? "bg-white shadow-md border-2 border-sage-400 scale-105" 
                : isAvailable
                  ? "hover:bg-white/60 border-2 border-transparent hover:border-sage-200"
                  : "opacity-50 cursor-not-allowed border-2 border-transparent"
            )}
            title={format.description}
          >
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
              isActive 
                ? "bg-sage-100" 
                : isAvailable 
                  ? "bg-stone-100 group-hover:bg-sage-50" 
                  : "bg-stone-100"
            )}>
              {isAvailable ? (
                <Icon className={cn(
                  "w-5 h-5 transition-colors",
                  isActive ? "text-sage-600" : "text-stone-500"
                )} />
              ) : (
                <Lock className="w-4 h-4 text-stone-400" />
              )}
            </div>
            <span className={cn(
              "text-xs font-medium transition-colors",
              isActive ? "text-sage-700" : "text-stone-600"
            )}>
              {format.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * TOCItem - 目录项类型
 */
interface TOCItem {
  id: string;
  title: string;
  level: number;
}

/**
 * TableOfContents - 可折叠目录组件
 * 固定在 LearningStage 左侧边缘中间位置，默认收起，鼠标悬停时展开
 */
function TableOfContents({ 
  items, 
  onItemClick 
}: { 
  items: TOCItem[];
  onItemClick: (id: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (items.length === 0) return null;

  return (
    <div 
      className={cn(
        "absolute left-0 top-1/2 -translate-y-1/2 z-50 transition-all duration-300 ease-out",
        isExpanded ? "w-[260px]" : "w-[24px]"
      )}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      {/* Collapsed Tab - Minimal hint */}
      <div className={cn(
        "absolute left-0 top-1/2 -translate-y-1/2 transition-all duration-300",
        isExpanded ? "opacity-0 pointer-events-none" : "opacity-60 hover:opacity-100"
      )}>
        <div className="flex flex-col items-center gap-1.5 py-6 px-1 bg-sage-100/40 hover:bg-sage-100/60 rounded-r-lg border-r-2 border-sage-300/40 hover:border-sage-400/60 transition-all cursor-pointer">
          <ChevronRight className="w-3 h-3 text-sage-500" />
          <div className="h-12 w-[1px] bg-sage-300/50"></div>
          <span className="text-[10px] text-sage-500 font-medium tabular-nums">
            {items.length}
          </span>
        </div>
      </div>

      {/* Expanded Content */}
      <div className={cn(
        "rounded-r-xl border border-sage-200 bg-white/95 backdrop-blur-sm shadow-lg transition-all duration-300",
        isExpanded ? "opacity-100" : "opacity-0 pointer-events-none"
      )}>
        {/* Compact Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-sage-100 bg-sage-50/50">
          <span className="text-xs font-medium text-sage-700">目录</span>
          <span className="text-[10px] text-sage-400 ml-auto tabular-nums">
            {items.length}
          </span>
        </div>

        {/* Scrollable Nav */}
        <ScrollArea className="max-h-[65vh]">
          <nav className="p-2">
            <ul className="space-y-0.5">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => onItemClick(item.id)}
                    className={cn(
                      "w-full text-left px-2.5 py-1.5 rounded-md text-xs transition-colors hover:bg-sage-50 text-stone-600 hover:text-sage-700",
                      item.level === 2 && "font-medium",
                      item.level === 3 && "pl-4 text-stone-500",
                      item.level >= 4 && "pl-6 text-stone-400 text-[11px]"
                    )}
                  >
                    <span className="line-clamp-2">{item.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </ScrollArea>
      </div>
    </div>
  );
}

/**
 * DynamicHeader - 动态视觉头部组件
 * 展示概念的标题、描述和预估时间，带有优雅的渐变背景
 */
function DynamicHeader({ concept }: { concept: Concept }) {
  return (
    <div className="relative w-full h-48 md:h-56 rounded-xl overflow-hidden mb-6 border border-sage-200 shadow-sm">
      {/* Sage Gradient Background */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(135deg, hsl(140 25% 88%) 0%, hsl(140 20% 92%) 40%, hsl(40 20% 96%) 100%)'
        }}
      />
      <div className="absolute inset-0 bg-noise opacity-[0.03]" />
      
      {/* Subtle Decorative Shapes */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 rounded-full blur-3xl opacity-40"
        style={{ backgroundColor: 'hsl(140 25% 80%)' }}
      />
      <div 
        className="absolute top-1/4 right-1/4 w-32 h-32 rounded-full blur-2xl opacity-30"
        style={{ backgroundColor: 'hsl(40 30% 88%)' }}
      />
      
      {/* Content */}
      <div className="relative z-10 h-full flex flex-col justify-end p-6 md:p-8">
        <div className="flex items-center gap-3 mb-3">
          <span className="px-3 py-1 rounded-full bg-sage-600 text-[10px] uppercase tracking-widest text-white font-medium">
            Interactive Lesson
          </span>
          {concept.estimated_hours && (
            <span className="flex items-center gap-1.5 text-xs text-sage-700">
              <Clock className="w-3 h-3" />
              {concept.estimated_hours}h
            </span>
          )}
        </div>
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight mb-2">
          {concept.name}
        </h1>
        <p className="text-muted-foreground text-sm max-w-2xl line-clamp-2 leading-relaxed">
          {concept.description}
        </p>
      </div>
    </div>
  );
}

/**
 * extractTOCFromMarkdown - 从 Markdown 内容中提取目录
 */
function extractTOCFromMarkdown(content: string): TOCItem[] {
  if (!content) return [];
  
  const headingRegex = /^(#{2,4})\s+(.+)$/gm;
  const items: TOCItem[] = [];
  let match;
  
  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length;
    const title = match[2].replace(/[*_`]/g, '').trim();
    // Create a consistent ID that matches what will be generated in the DOM
    const id = title
      .toLowerCase()
      .replace(/[^\u4e00-\u9fa5\w\s-]/g, '') // Keep Chinese characters, word chars, spaces, hyphens
      .replace(/\s+/g, '-')
      .replace(/--+/g, '-') // Replace multiple hyphens with single hyphen
      .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
    
    items.push({ id, title, level });
  }
  
  return items;
}

/**
 * generateHeadingId - 从标题文本生成一致的 ID
 */
function generateHeadingId(text: string | React.ReactNode): string {
  const textContent = typeof text === 'string' ? text : String(text);
  return textContent
    .toLowerCase()
    .replace(/[^\u4e00-\u9fa5\w\s-]/g, '') // Keep Chinese characters, word chars, spaces, hyphens
    .replace(/\s+/g, '-')
    .replace(/--+/g, '-') // Replace multiple hyphens with single hyphen
    .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
}

/**
 * ResourceCard - 学习资源卡片组件
 */
function ResourceCard({ 
  resource, 
  index 
}: { 
  resource: ResourcesResponse['resources'][0];
  index: number;
}) {
  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Video className="w-4 h-4" />;
      case 'article':
        return <FileTextIcon className="w-4 h-4" />;
      case 'book':
        return <BookMarked className="w-4 h-4" />;
      case 'course':
        return <Award className="w-4 h-4" />;
      case 'documentation':
        return <BookOpen className="w-4 h-4" />;
      case 'tool':
        return <Code className="w-4 h-4" />;
      default:
        return <FileTextIcon className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'video':
        return 'bg-red-50 text-red-600 border-red-200';
      case 'article':
        return 'bg-blue-50 text-blue-600 border-blue-200';
      case 'book':
        return 'bg-purple-50 text-purple-600 border-purple-200';
      case 'course':
        return 'bg-green-50 text-green-600 border-green-200';
      case 'documentation':
        return 'bg-amber-50 text-amber-600 border-amber-200';
      case 'tool':
        return 'bg-cyan-50 text-cyan-600 border-cyan-200';
      default:
        return 'bg-stone-50 text-stone-600 border-stone-200';
    }
  };

  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block p-4 rounded-xl border border-sage-200 bg-white hover:bg-sage-50/50 hover:border-sage-300 transition-all hover:shadow-sm"
    >
      <div className="flex items-start gap-3">
        {/* Index Badge */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-sage-100 flex items-center justify-center text-xs font-medium text-sage-700">
          {index + 1}
        </div>

        <div className="flex-1 min-w-0">
          {/* Title & External Link */}
          <div className="flex items-start gap-2 mb-2">
            <h3 className="text-sm font-medium text-foreground group-hover:text-sage-700 transition-colors line-clamp-2 flex-1">
              {resource.title}
            </h3>
            <ExternalLink className="w-4 h-4 text-sage-400 group-hover:text-sage-600 transition-colors flex-shrink-0 mt-0.5" />
          </div>

          {/* Description */}
          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
            {resource.description}
          </p>

          {/* Type Badge & Relevance */}
          <div className="flex items-center gap-2">
            <span className={cn(
              "inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium border",
              getTypeColor(resource.type)
            )}>
              {getResourceIcon(resource.type)}
              {resource.type}
            </span>
            <div className="flex items-center gap-1">
              <div className="flex gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-1 h-1 rounded-full",
                      i < Math.round(resource.relevance_score * 5)
                        ? "bg-amber-400"
                        : "bg-stone-200"
                    )}
                  />
                ))}
              </div>
              <span className="text-[10px] text-muted-foreground">
                {Math.round(resource.relevance_score * 100)}% match
              </span>
            </div>
          </div>
        </div>
      </div>
    </a>
  );
}

/**
 * ResourceList - 学习资源列表组件
 */
function ResourceList({ 
  resources, 
  isLoading, 
  error,
  roadmapId,
  conceptId,
  userPreferences,
  onRetrySuccess
}: { 
  resources: ResourcesResponse['resources'];
  isLoading: boolean;
  error: string | null;
  roadmapId?: string;
  conceptId?: string;
  userPreferences?: LearningPreferences;
  onRetrySuccess?: () => void;
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2Icon className="w-8 h-8 text-sage-500 animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Loading learning resources...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
          <BookOpen className="w-8 h-8 text-red-400" />
        </div>
        <h3 className="text-lg font-medium text-stone-700 mb-2">Failed to Load Resources</h3>
        <p className="text-sm text-stone-500 max-w-md">{error}</p>
      </div>
    );
  }

  if (!resources || resources.length === 0) {
    // 如果有重试所需的参数，显示重试按钮
    if (roadmapId && conceptId && userPreferences) {
      return (
        <FailedContentAlert
          roadmapId={roadmapId}
          conceptId={conceptId}
          contentType="resources"
          preferences={userPreferences}
          message="学习资源暂未生成"
          onSuccess={onRetrySuccess}
        />
      );
    }
    
    // 否则显示默认的空状态提示
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
          <BookOpen className="w-8 h-8 text-stone-400" />
        </div>
        <h3 className="text-lg font-medium text-stone-700 mb-2">No Resources Available</h3>
        <p className="text-sm text-stone-500 max-w-md">
          Learning resources are being generated. Please check back later.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="mb-6">
        <h2 className="text-xl font-serif font-bold text-foreground mb-2">
          Curated Learning Resources
        </h2>
        <p className="text-sm text-muted-foreground">
          {resources.length} handpicked resources to deepen your understanding
        </p>
      </div>
      {resources.map((resource, index) => (
        <ResourceCard key={`${resource.url}-${index}`} resource={resource} index={index} />
      ))}
    </div>
  );
}

/**
 * QuizQuestionCard - 测验问题卡片
 * 高端杂志风格设计：统一 sage 色系，细腻的阴影和过渡效果
 */
function QuizQuestionCard({ 
  question, 
  index,
  isAnswered,
  selectedAnswers,
  onAnswerSelect
}: { 
  question: QuizResponse['questions'][0];
  index: number;
  isAnswered: boolean;
  selectedAnswers: number[];
  onAnswerSelect: (optionIndex: number) => void;
}) {
  const isMultipleChoice = question.question_type === 'multiple_choice';
  const isTrueFalse = question.question_type === 'true_false';
  const isCorrect = isAnswered && 
    selectedAnswers.length === question.correct_answer.length &&
    selectedAnswers.every(a => question.correct_answer.includes(a));

  // 高端杂志风格的难度颜色配色 - 使用 sage 主色系
  const getDifficultyStyle = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-sage-50 text-sage-700 border-sage-200';
      case 'medium':
        return 'bg-stone-100 text-stone-700 border-stone-200';
      case 'hard':
        return 'bg-stone-800 text-white border-stone-700';
      default:
        return 'bg-stone-50 text-stone-600 border-stone-200';
    }
  };

  // 获取题型显示文本
  const getQuestionTypeLabel = () => {
    if (isTrueFalse) return 'True / False';
    if (isMultipleChoice) return 'Select All';
    return 'Choose One';
  };

  return (
    <div className="p-6 rounded-2xl border border-sage-100 bg-gradient-to-br from-white to-sage-50/30 shadow-sm hover:shadow-md transition-shadow duration-300">
      {/* Question Header */}
      <div className="flex items-start gap-4 mb-5">
        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-sage-600 flex items-center justify-center text-sm font-serif font-bold text-white shadow-sm">
          {index + 1}
        </div>
        <div className="flex-1 pt-0.5">
          <div className="flex items-center gap-2 mb-3">
            <span className={cn(
              "inline-flex px-2.5 py-1 rounded-md text-[10px] font-semibold border uppercase tracking-wider",
              getDifficultyStyle(question.difficulty)
            )}>
              {question.difficulty}
            </span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
              {getQuestionTypeLabel()}
            </span>
          </div>
          <p className="text-base font-medium text-foreground leading-relaxed font-serif">
            {question.question}
          </p>
        </div>
      </div>

      {/* Options */}
      <div className="space-y-3 mb-5 pl-14">
        {question.options.map((option, optionIndex) => {
          const isSelected = selectedAnswers.includes(optionIndex);
          const isCorrectOption = question.correct_answer.includes(optionIndex);
          const showCorrect = isAnswered && isCorrectOption;
          const showWrong = isAnswered && isSelected && !isCorrectOption;

          // 选项字母标识
          const optionLetter = String.fromCharCode(65 + optionIndex);

          return (
            <button
              key={optionIndex}
              onClick={() => !isAnswered && onAnswerSelect(optionIndex)}
              disabled={isAnswered}
              className={cn(
                "group w-full text-left px-4 py-3.5 rounded-xl border transition-all duration-200 text-sm",
                !isAnswered && "hover:border-sage-400 hover:bg-sage-50 hover:shadow-sm cursor-pointer",
                isAnswered && "cursor-default",
                isSelected && !isAnswered && "border-sage-500 bg-sage-100 shadow-sm",
                !isSelected && !isAnswered && "border-sage-200/80 bg-white/80",
                showCorrect && "border-sage-500 bg-sage-100",
                showWrong && "border-stone-400 bg-stone-50",
                isAnswered && !isSelected && !isCorrectOption && "opacity-40"
              )}
            >
              <div className="flex items-center gap-3">
                <div className={cn(
                  "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 text-xs font-semibold",
                  showCorrect && "bg-sage-600 text-white",
                  showWrong && "bg-stone-500 text-white",
                  isSelected && !isAnswered && "bg-sage-600 text-white",
                  !isSelected && !isAnswered && "bg-sage-100 text-sage-600 group-hover:bg-sage-200"
                )}>
                  {showCorrect ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : showWrong ? (
                    <Circle className="w-4 h-4" />
                  ) : (
                    optionLetter
                  )}
                </div>
                <span className={cn(
                  "flex-1 leading-relaxed",
                  showCorrect && "text-sage-800 font-medium",
                  showWrong && "text-stone-600",
                  !isAnswered && "text-foreground"
                )}>
                  {option}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Explanation (shown after answering) */}
      {isAnswered && (
        <div className={cn(
          "ml-14 p-4 rounded-xl border-l-4 transition-all duration-300",
          isCorrect 
            ? "bg-sage-50 border-sage-500" 
            : "bg-stone-50 border-stone-400"
        )}>
          <div className="flex items-start gap-3">
            <Award className={cn(
              "w-5 h-5 flex-shrink-0 mt-0.5",
              isCorrect ? "text-sage-600" : "text-stone-500"
            )} />
            <div className="flex-1">
              <p className={cn(
                "text-sm font-semibold mb-1.5",
                isCorrect ? "text-sage-800" : "text-stone-700"
              )}>
                {isCorrect ? "Excellent!" : "Keep Learning"}
              </p>
              <p className="text-sm text-stone-600 leading-relaxed">
                {question.explanation}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * QuizList - 测验列表组件
 */
function QuizList({ 
  quiz, 
  isLoading, 
  error,
  roadmapId,
  conceptId,
  userPreferences,
  onRetrySuccess
}: { 
  quiz: QuizResponse | null;
  isLoading: boolean;
  error: string | null;
  roadmapId?: string;
  conceptId?: string;
  userPreferences?: LearningPreferences;
  onRetrySuccess?: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<string>>(new Set());

  const handleAnswerSelect = (questionId: string, optionIndex: number, isMultipleChoice: boolean) => {
    if (submittedQuestions.has(questionId)) return;

    setAnswers(prev => {
      const current = prev[questionId] || [];
      if (isMultipleChoice) {
        // Toggle selection for multiple choice
        if (current.includes(optionIndex)) {
          return { ...prev, [questionId]: current.filter(i => i !== optionIndex) };
        } else {
          return { ...prev, [questionId]: [...current, optionIndex] };
        }
      } else {
        // Replace selection for single choice
        return { ...prev, [questionId]: [optionIndex] };
      }
    });
  };

  const handleSubmitAnswer = (questionId: string) => {
    setSubmittedQuestions(prev => new Set([...prev, questionId]));
  };

  const getScore = () => {
    if (!quiz) return { correct: 0, total: 0 };
    let correct = 0;
    quiz.questions.forEach(q => {
      if (submittedQuestions.has(q.question_id)) {
        const userAnswers = answers[q.question_id] || [];
        if (
          userAnswers.length === q.correct_answer.length &&
          userAnswers.every(a => q.correct_answer.includes(a))
        ) {
          correct++;
        }
      }
    });
    return { correct, total: submittedQuestions.size };
  };

  // Auto-submit quiz attempt when all questions are answered
  const allAnswered = quiz ? submittedQuestions.size === quiz.total_questions : false;
  
  useEffect(() => {
    if (!allAnswered || !quiz || !roadmapId || !conceptId) return;
    
    const submitAttempt = async () => {
      const score = getScore();
      
      // Calculate incorrect question indices
      const incorrectIndices: number[] = [];
      quiz.questions.forEach((question, index) => {
        const userAnswers = answers[question.question_id] || [];
        const isCorrect = 
          userAnswers.length === question.correct_answer.length &&
          userAnswers.every(a => question.correct_answer.includes(a));
        
        if (!isCorrect) {
          incorrectIndices.push(index);
        }
      });
      
      try {
        await submitQuizAttempt(roadmapId, conceptId, {
          quiz_id: quiz.quiz_id,
          total_questions: quiz.total_questions,
          correct_answers: score.correct,
          score_percentage: (score.correct / quiz.total_questions) * 100,
          incorrect_question_indices: incorrectIndices
        });
        console.log('[QuizList] Quiz attempt submitted successfully');
      } catch (error) {
        console.error('Failed to submit quiz attempt:', error);
      }
    };
    
    submitAttempt();
  }, [allAnswered, quiz, roadmapId, conceptId, answers, submittedQuestions]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2Icon className="w-8 h-8 text-sage-500 animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Loading quiz...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
          <Sparkles className="w-8 h-8 text-red-400" />
        </div>
        <h3 className="text-lg font-medium text-stone-700 mb-2">Failed to Load Quiz</h3>
        <p className="text-sm text-stone-500 max-w-md">{error}</p>
      </div>
    );
  }

  if (!quiz || quiz.questions.length === 0) {
    // 如果有重试所需的参数，显示重试按钮
    if (roadmapId && conceptId && userPreferences) {
      return (
        <FailedContentAlert
          roadmapId={roadmapId}
          conceptId={conceptId}
          contentType="quiz"
          preferences={userPreferences}
          message="测验题目暂未生成"
          onSuccess={onRetrySuccess}
        />
      );
    }
    
    // 否则显示默认的空状态提示
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
          <Sparkles className="w-8 h-8 text-stone-400" />
        </div>
        <h3 className="text-lg font-medium text-stone-700 mb-2">No Quiz Available</h3>
        <p className="text-sm text-stone-500 max-w-md">
          Quiz questions are being generated. Please check back later.
        </p>
      </div>
    );
  }

  const score = getScore();
  const scorePercentage = score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0;

  return (
    <div className="space-y-5">
      {/* Quiz Header - 高端杂志风格 */}
      <div className="mb-8 pb-6 border-b border-sage-100">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-sage-600 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-serif font-bold text-foreground">
              Knowledge Check
            </h2>
            <p className="text-sm text-muted-foreground">
              {quiz.total_questions} questions to test your understanding
            </p>
          </div>
        </div>
        
        {/* Progress Bar - 优雅的进度显示 */}
        {submittedQuestions.size > 0 && !allAnswered && (
          <div className="mt-4 flex items-center gap-4">
            <div className="flex-1 h-1.5 bg-sage-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-sage-500 to-sage-600 transition-all duration-700 ease-out"
                style={{ width: `${(submittedQuestions.size / quiz.total_questions) * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium text-sage-700 tabular-nums min-w-[3rem] text-right">
              {submittedQuestions.size}/{quiz.total_questions}
            </span>
          </div>
        )}

        {/* Score Display - 完成后的优雅展示 */}
        {allAnswered && (
          <div className="mt-6 p-6 rounded-2xl bg-gradient-to-br from-sage-50 via-white to-sage-50/50 border border-sage-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-sage-600 flex items-center justify-center shadow-sm">
                  <Award className="w-7 h-7 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-0.5">Quiz Complete</p>
                  <p className="text-3xl font-serif font-bold text-sage-800">
                    {score.correct}<span className="text-lg text-muted-foreground font-normal">/{score.total}</span>
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-4xl font-serif font-bold text-sage-700">
                  {scorePercentage}%
                </p>
                <p className="text-xs text-muted-foreground mt-1 uppercase tracking-wider">
                  {scorePercentage >= 80 ? 'Excellent' : scorePercentage >= 60 ? 'Good Job' : 'Keep Learning'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Questions */}
      {quiz.questions.map((question, index) => {
        const isAnswered = submittedQuestions.has(question.question_id);
        const selectedAnswers = answers[question.question_id] || [];
        const hasSelection = selectedAnswers.length > 0;

        return (
          <div key={question.question_id}>
            <QuizQuestionCard
              question={question}
              index={index}
              isAnswered={isAnswered}
              selectedAnswers={selectedAnswers}
              onAnswerSelect={(optionIndex) => 
                handleAnswerSelect(
                  question.question_id, 
                  optionIndex, 
                  question.question_type === 'multiple_choice'
                )
              }
            />
            {!isAnswered && hasSelection && (
              <div className="mt-3 flex justify-end">
                <Button
                  onClick={() => handleSubmitAnswer(question.question_id)}
                  size="sm"
                  className="bg-sage-600 hover:bg-sage-700 text-white shadow-sm hover:shadow transition-all px-5"
                >
                  Submit Answer
                </Button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * LearningStageProps - 学习舞台组件属性
 */
interface LearningStageProps {
  /** 当前选中的概念 */
  concept: Concept | null;
  /** 自定义样式类名 */
  className?: string;
  /** 教程 Markdown 内容 */
  tutorialContent?: string;
  /** 路线图 ID (用于获取资源和测验) */
  roadmapId?: string;
  /** 用户学习偏好（用于重试生成） */
  userPreferences?: LearningPreferences;
  /** 内容重试成功回调（用于刷新数据） */
  onRetrySuccess?: () => void;
}

/**
 * LearningStage - 沉浸式学习页面的中央学习区域
 * 
 * 功能:
 * - 展示动态视觉头部
 * - 学习形式选项卡（Immersive Text / Learning Resources / Quiz / Slides / Audio / Mindmap）
 * - 可折叠的目录导航
 * - 渲染 Markdown 教程内容（支持代码高亮）
 * - 显示学习资源推荐
 * - 显示测验题目
 * - 提供"标记完成"操作
 */
export function LearningStage({ concept, className, tutorialContent, roadmapId, userPreferences, onRetrySuccess }: LearningStageProps) {
  const [activeFormat, setActiveFormat] = useState<LearningFormat>('immersive-text');
  
  // Learning progress state
  const { conceptProgressMap, updateConceptProgress: updateProgressInStore, updateConceptStatus } = useRoadmapStore();
  const [isTogglingProgress, setIsTogglingProgress] = useState(false);
  
  // Resources state
  const [resources, setResources] = useState<ResourcesResponse | null>(null);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState<string | null>(null);

  // Quiz state
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState<string | null>(null);
  
  // 检测内容生成状态
  // 注意：不再使用本地重试状态，完全依赖后端状态和WebSocket更新
  const tutorialFailed = concept?.content_status === 'failed';
  const tutorialGenerating = concept?.content_status === 'generating';
  const tutorialPending = concept?.content_status === 'pending';
  
  const resourcesFailed = concept?.resources_status === 'failed';
  const resourcesGenerating = concept?.resources_status === 'generating';
  const resourcesPending = concept?.resources_status === 'pending';
  
  const quizFailed = concept?.quiz_status === 'failed';
  const quizGenerating = concept?.quiz_status === 'generating';
  const quizPending = concept?.quiz_status === 'pending';
  
  // Extract TOC from markdown content
  const tocItems = useMemo(() => {
    return extractTOCFromMarkdown(tutorialContent || '');
  }, [tutorialContent]);

  // Handle TOC item click - scroll to heading
  const handleTOCClick = useCallback((id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // Reset resources and quiz data when concept changes
  useEffect(() => {
    setResources(null);
    setResourcesError(null);
    setQuiz(null);
    setQuizError(null);
  }, [concept?.concept_id]);

  // 检查是否有正在进行的重试任务
  // 当切换到对应tab或concept变化时，检查backend是否有active task
  useEffect(() => {
    if (!roadmapId || !concept) return;

    let isMounted = true; // 防止组件卸载后更新状态

    const checkActiveRetryTasks = async () => {
      try {
        const { checkRoadmapStatusQuick } = await import('@/lib/api/endpoints');
        const result = await checkRoadmapStatusQuick(roadmapId);

        // 检查组件是否仍然挂载
        if (!isMounted) return;

        if (result.has_active_task && result.active_tasks) {
          // 检查是否有当前concept的active task
          const currentConceptTasks = result.active_tasks.filter(
            (task: any) => task.concept_id === concept.concept_id
          );

          // 更新各个content type的状态
          currentConceptTasks.forEach((task: any) => {
            if (task.content_type === 'tutorial' && task.status === 'processing') {
              if (concept.content_status !== 'generating') {
                console.log('[LearningStage] Found active tutorial task, updating status to generating');
                updateConceptStatus(concept.concept_id, { content_status: 'generating' });
              }
            } else if (task.content_type === 'resources' && task.status === 'processing') {
              if (concept.resources_status !== 'generating') {
                console.log('[LearningStage] Found active resources task, updating status to generating');
                updateConceptStatus(concept.concept_id, { resources_status: 'generating' });
              }
            } else if (task.content_type === 'quiz' && task.status === 'processing') {
              if (concept.quiz_status !== 'generating') {
                console.log('[LearningStage] Found active quiz task, updating status to generating');
                updateConceptStatus(concept.concept_id, { quiz_status: 'generating' });
              }
            }
          });
        }
      } catch (error) {
        console.error('[LearningStage] Failed to check active tasks:', error);
      }
    };

    checkActiveRetryTasks();

    return () => {
      isMounted = false; // 清理函数：标记组件已卸载
    };
  }, [roadmapId, concept?.concept_id, activeFormat]);

  // Fetch resources when tab is activated or concept changes
  useEffect(() => {
    // 只有当 resources_id 存在时才尝试获取资源
    // 如果 resources_id 为 null，说明资源还未生成或生成失败，应显示重试按钮
    if (activeFormat === 'learning-resources' && concept && roadmapId && concept.resources_id) {
      setResourcesLoading(true);
      setResourcesError(null);
      
      getConceptResources(roadmapId, concept.concept_id)
        .then(data => {
          setResources(data);
          setResourcesLoading(false);
        })
        .catch(err => {
          console.error('Failed to load resources:', err);
          setResourcesError(err.message || 'Failed to load learning resources');
          setResourcesLoading(false);
        });
    }
  }, [activeFormat, concept?.concept_id, concept?.resources_id, roadmapId]);

  // Fetch quiz when tab is activated or concept changes
  useEffect(() => {
    // 只有当 quiz_id 存在时才尝试获取测验
    // 如果 quiz_id 为 null，说明测验还未生成或生成失败，应显示重试按钮
    if (activeFormat === 'quiz' && concept && roadmapId && concept.quiz_id) {
      setQuizLoading(true);
      setQuizError(null);
      
      getConceptQuiz(roadmapId, concept.concept_id)
        .then(data => {
          setQuiz(data);
          setQuizLoading(false);
        })
        .catch(err => {
          console.error('Failed to load quiz:', err);
          setQuizError(err.message || 'Failed to load quiz');
          setQuizLoading(false);
        });
    }
  }, [activeFormat, concept?.concept_id, concept?.quiz_id, roadmapId]);

  // Compute concept completion status
  const isConceptCompleted = concept ? (conceptProgressMap[concept.concept_id] || false) : false;

  // Handle toggle completion
  const handleToggleComplete = async () => {
    if (!roadmapId || !concept) return;
    
    setIsTogglingProgress(true);
    try {
      const newStatus = !isConceptCompleted;
      await updateConceptProgress(roadmapId, concept.concept_id, newStatus);
      updateProgressInStore(concept.concept_id, newStatus);
    } catch (error) {
      console.error('Failed to toggle concept completion:', error);
    } finally {
      setIsTogglingProgress(false);
    }
  };

  if (!concept) {
    return (
      <div className={cn("h-full flex items-center justify-center text-muted-foreground bg-background", className)}>
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-sage-50 mx-auto flex items-center justify-center mb-4 border border-sage-100">
            <BookOpen className="w-8 h-8 text-sage-400" />
          </div>
          <p className="font-serif text-lg text-foreground">Select a concept to begin</p>
          <p className="text-sm mt-2 text-muted-foreground">Choose from the knowledge rail on the left</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("h-full flex flex-col bg-background relative", className)}>
      <ScrollArea className="flex-1">
        <div className="max-w-3xl mx-auto px-6 py-10">
          {/* Title Card */}
          <DynamicHeader concept={concept} />
          
          {/* Learning Format Tabs */}
          <LearningFormatTabs 
            activeFormat={activeFormat}
            onFormatChange={setActiveFormat}
          />

          {/* Content Area based on active format */}
          {activeFormat === 'immersive-text' && (
            <>
              {/* Collapsible Table of Contents - Fixed to left edge */}
              {tutorialContent && (
                <TableOfContents 
                  items={tocItems}
                  onItemClick={handleTOCClick}
                />
              )}
              
              {tutorialGenerating || tutorialPending ? (
                /* 教程正在生成中，使用僵尸状态检测器 */
                roadmapId && concept && userPreferences ? (
                  <StaleStatusDetector
                    roadmapId={roadmapId}
                    conceptId={concept.concept_id}
                    contentType="tutorial"
                    status={concept.content_status}
                    preferences={userPreferences}
                    timeoutSeconds={120}
                  onSuccess={() => onRetrySuccess?.()}
                  />
                ) : (
                  <GeneratingContentLoader contentType="tutorial" />
                )
              ) : tutorialFailed && roadmapId && concept && userPreferences ? (
                /* 教程生成失败，显示重试按钮 */
                <FailedContentAlert
                  roadmapId={roadmapId}
                  conceptId={concept.concept_id}
                  contentType="tutorial"
                  preferences={userPreferences}
                  onSuccess={() => onRetrySuccess?.()}
                />
              ) : tutorialContent ? (
                /* 编辑风格的文章排版 - 浅色主题 */
                <article className="prose prose-stone max-w-none 
                  prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-foreground
                  prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-4 prose-h2:border-b prose-h2:border-border prose-h2:pb-3
                  prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3
                  prose-h4:text-lg prose-h4:mt-6 prose-h4:mb-2
                  prose-p:leading-relaxed prose-p:text-foreground/85 prose-p:mb-4
                  prose-strong:text-foreground prose-strong:font-semibold
                  prose-ul:text-foreground/85 prose-ol:text-foreground/85
                  prose-li:marker:text-sage-500
                  prose-pre:bg-stone-900 prose-pre:border prose-pre:border-stone-800 prose-pre:rounded-lg prose-pre:text-stone-100
                  prose-code:text-sage-700 prose-code:bg-sage-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-normal prose-code:before:content-[''] prose-code:after:content-['']
                  prose-a:text-sage-600 prose-a:no-underline hover:prose-a:underline hover:prose-a:text-sage-700
                  prose-blockquote:border-l-sage-300 prose-blockquote:bg-sage-50/50 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:text-foreground/70"
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      // Add id to headings for TOC navigation
                      h2: ({ children, ...props }) => {
                        const id = generateHeadingId(children);
                        return <h2 id={id} {...props}>{children}</h2>;
                      },
                      h3: ({ children, ...props }) => {
                        const id = generateHeadingId(children);
                        return <h3 id={id} {...props}>{children}</h3>;
                      },
                      h4: ({ children, ...props }) => {
                        const id = generateHeadingId(children);
                        return <h4 id={id} {...props}>{children}</h4>;
                      },
                      // Fix code block text color & support Mermaid diagrams
                      code: ({ inline, className, children, ...props }: any) => {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const code = String(children).replace(/\n$/, '');
                        
                        // 检查是否是 Mermaid 图表
                        if (!inline && language === 'mermaid') {
                          const MermaidDiagram = require('@/components/tutorial/mermaid-diagram').MermaidDiagram;
                          return <MermaidDiagram chart={code} />;
                        }
                        
                        if (!inline && match) {
                          // Block code - use default styling with explicit color
                          return (
                            <code className={className} style={{ color: 'inherit' }} {...props}>
                              {children}
                            </code>
                          );
                        }
                        // Inline code
                        return <code className={className} {...props}>{children}</code>;
                      },
                      pre: ({ children, ...props }: any) => {
                        // 检查是否包含 Mermaid 图表
                        // 方法1: 检查 code 标签的 className
                        const codeChild = Array.isArray(children) ? children[0] : children;
                        const className = codeChild?.props?.className || '';
                        const isMermaid = className.includes('language-mermaid');
                        
                        if (isMermaid) {
                          // Mermaid 图表不需要 pre 包裹（避免黑色边框）
                          return <>{children}</>;
                        }
                        
                        // 普通代码块使用 pre 标签
                        return (
                          <pre {...props} style={{ backgroundColor: '#1c1917', color: '#e7e5e4' }}>
                            {children}
                          </pre>
                        );
                      }
                    }}
                  >
                    {tutorialContent}
                  </ReactMarkdown>
                </article>
              ) : (
                <div className="space-y-4">
                  <div className="h-4 bg-muted rounded w-3/4 animate-pulse" />
                  <div className="h-4 bg-muted rounded w-full animate-pulse" />
                  <div className="h-4 bg-muted rounded w-5/6 animate-pulse" />
                  <div className="h-32 bg-muted/70 rounded w-full animate-pulse mt-8" />
                </div>
              )}
            </>
          )}

          {/* Placeholder for other formats */}
          {activeFormat === 'learning-resources' && (
            resourcesGenerating || resourcesPending ? (
              /* 资源推荐正在生成中，使用僵尸状态检测器 */
              roadmapId && concept && userPreferences ? (
                <StaleStatusDetector
                  roadmapId={roadmapId}
                  conceptId={concept.concept_id}
                  contentType="resources"
                  status={concept.resources_status}
                  preferences={userPreferences}
                  timeoutSeconds={120}
                  onSuccess={() => onRetrySuccess?.()}
                />
              ) : (
                <GeneratingContentLoader contentType="resources" />
              )
            ) : resourcesFailed && roadmapId && concept && userPreferences ? (
              /* 资源推荐生成失败，显示重试按钮 */
              <FailedContentAlert
                roadmapId={roadmapId}
                conceptId={concept.concept_id}
                contentType="resources"
                preferences={userPreferences}
                  onSuccess={() => onRetrySuccess?.()}
              />
            ) : (
              <ResourceList 
                resources={resources?.resources || []}
                isLoading={resourcesLoading}
                error={resourcesError}
                roadmapId={roadmapId}
                conceptId={concept?.concept_id}
                userPreferences={userPreferences}
                onRetrySuccess={onRetrySuccess}
              />
            )
          )}

          {activeFormat === 'quiz' && (
            quizGenerating || quizPending ? (
              /* 测验正在生成中，使用僵尸状态检测器 */
              roadmapId && concept && userPreferences ? (
                <StaleStatusDetector
                  roadmapId={roadmapId}
                  conceptId={concept.concept_id}
                  contentType="quiz"
                  status={concept.quiz_status}
                  preferences={userPreferences}
                  timeoutSeconds={120}
                  onSuccess={() => onRetrySuccess?.()}
                />
              ) : (
                <GeneratingContentLoader contentType="quiz" />
              )
            ) : quizFailed && roadmapId && concept && userPreferences ? (
              /* 测验生成失败，显示重试按钮 */
              <FailedContentAlert
                roadmapId={roadmapId}
                conceptId={concept.concept_id}
                contentType="quiz"
                preferences={userPreferences}
                  onSuccess={() => onRetrySuccess?.()}
              />
            ) : (
              <QuizList 
                quiz={quiz}
                isLoading={quizLoading}
                error={quizError}
                roadmapId={roadmapId}
                conceptId={concept?.concept_id}
                userPreferences={userPreferences}
                onRetrySuccess={onRetrySuccess}
              />
            )
          )}

          {activeFormat === 'slides' && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
                <Presentation className="w-8 h-8 text-stone-400" />
              </div>
              <h3 className="text-lg font-medium text-stone-700 mb-2">Slides & Narration</h3>
              <p className="text-sm text-stone-500 max-w-md">
                Interactive slides with voice narration will be available here. This feature is under development.
              </p>
            </div>
          )}

          {activeFormat === 'audio' && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
                <Mic className="w-8 h-8 text-stone-400" />
              </div>
              <h3 className="text-lg font-medium text-stone-700 mb-2">Audio Lesson</h3>
              <p className="text-sm text-stone-500 max-w-md">
                Podcast-style audio lessons will be available here. This feature is under development.
              </p>
            </div>
          )}

          {activeFormat === 'mindmap' && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
                <Network className="w-8 h-8 text-stone-400" />
              </div>
              <h3 className="text-lg font-medium text-stone-700 mb-2">Mindmap</h3>
              <p className="text-sm text-stone-500 max-w-md">
                Visual knowledge graphs will be available here. This feature is under development.
              </p>
            </div>
          )}

          {/* Footer Actions */}
          <div className="mt-20 pt-8 border-t border-border flex justify-between items-center">
            <div className="text-sm text-muted-foreground">
              You&apos;ve reached the end of this lesson.
            </div>
            <Button 
              variant="outline" 
              className={cn(
                "gap-2 transition-all",
                isConceptCompleted 
                  ? "border-green-300 bg-green-50 text-green-700 hover:bg-green-100 hover:border-green-400"
                  : "border-sage-300 text-sage-700 hover:bg-sage-50 hover:text-sage-800 hover:border-sage-400"
              )}
              onClick={handleToggleComplete}
              disabled={isTogglingProgress}
            >
              {isTogglingProgress ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isConceptCompleted ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {isConceptCompleted ? "Completed" : "Mark as Complete"}
            </Button>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
