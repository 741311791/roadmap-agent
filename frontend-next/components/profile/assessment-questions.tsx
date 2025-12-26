'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TechAssessment } from '@/types/assessment';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface AssessmentQuestionsProps {
  assessment: TechAssessment | null;
  answers: Record<number, string>;
  onAnswerChange: (answers: Record<number, string>) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}

/**
 * QuestionMarkdown - 为测验题目内容提供的轻量级 Markdown 渲染器
 * 支持代码块语法高亮，适用于包含代码的题目和选项
 */
function QuestionMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        // 代码块渲染
        code({ node, className, children, ...props }) {
          const isInline = !className?.includes('language-');
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          const code = String(children).replace(/\n$/, '');

          if (!isInline && language) {
            // 多行代码块 - 精简样式，移除冗余标签栏
            return (
              <div className="my-2 rounded-lg overflow-hidden border border-slate-700/30 bg-slate-950/95 shadow-sm">
                <pre className="p-3 overflow-x-auto text-sm">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            );
          }

          // 行内代码 - 增强对比度
          return (
            <code
              className="px-2 py-0.5 rounded-md bg-sage-50 text-sage-900 text-sm font-mono border border-sage-300/50 font-semibold"
              {...props}
            >
              {children}
            </code>
          );
        },
        // 段落样式
        p({ children }) {
          return <span className="block leading-relaxed">{children}</span>;
        },
        // 禁用其他不需要的元素以保持紧凑
        h1: ({ children }) => <strong className="text-lg">{children}</strong>,
        h2: ({ children }) => <strong className="text-base">{children}</strong>,
        h3: ({ children }) => <strong className="text-base">{children}</strong>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export function AssessmentQuestions({
  assessment,
  answers,
  onAnswerChange,
  onSubmit,
  isSubmitting,
}: AssessmentQuestionsProps) {
  if (!assessment) {
    return null;
  }

  const answeredCount = Object.keys(answers).length;
  const totalQuestions = assessment.total_questions;
  const allAnswered = answeredCount === totalQuestions;

  const getProficiencyBadgeVariant = (proficiency?: string) => {
    switch (proficiency) {
      case 'beginner':
        return 'bg-emerald-50 text-emerald-700 border-emerald-300';
      case 'intermediate':
        return 'bg-amber-50 text-amber-700 border-amber-300';
      case 'expert':
        return 'bg-rose-50 text-rose-700 border-rose-300';
      default:
        return 'bg-stone-50 text-stone-700 border-stone-300';
    }
  };

  const getProficiencyLabel = (proficiency?: string) => {
    switch (proficiency) {
      case 'beginner':
        return 'BEGINNER';
      case 'intermediate':
        return 'INTERMEDIATE';
      case 'expert':
        return 'EXPERT';
      default:
        return 'GENERAL';
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Header */}
      <div className="flex items-center justify-between sticky top-0 bg-background py-3 z-10 border-b">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Progress: {answeredCount} / {totalQuestions} questions
          </p>
        </div>
        <Badge variant={allAnswered ? 'default' : 'secondary'} className="text-xs">
          {allAnswered ? 'Completed' : 'In Progress'}
        </Badge>
      </div>

      {/* Questions List */}
      <div className="space-y-5">
        {assessment.questions.map((question, index) => {
          const isMultipleChoice = question.type === 'multiple_choice';
          const currentAnswer = answers[index];

          return (
            <div 
              key={index} 
              className="p-6 rounded-2xl border border-sage-100 bg-gradient-to-br from-white to-sage-50/30 shadow-sm hover:shadow-md transition-shadow duration-300"
            >
              {/* Question Header */}
              <div className="flex items-start gap-4 mb-5">
                {/* Question Number Badge */}
                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-sage-600 flex items-center justify-center text-sm font-serif font-bold text-white shadow-sm">
                  {index + 1}
                </div>

                {/* Question Content */}
                <div className="flex-1 pt-0.5">
                  {/* Proficiency Badge */}
                  <div className="flex items-center gap-3 mb-3">
                    <span className={cn(
                      "inline-flex px-3 py-1.5 rounded-lg text-xs font-bold border-2 uppercase tracking-wider shadow-sm",
                      getProficiencyBadgeVariant(question.proficiency_level)
                    )}>
                      {getProficiencyLabel(question.proficiency_level)}
                    </span>
                    <span className="text-xs text-slate-600 uppercase tracking-wide font-semibold">
                      {isMultipleChoice ? '✓ Select All' : '◉ Choose One'}
                    </span>
                  </div>

                  {/* Question Text */}
                  <div className="text-base font-medium text-foreground leading-relaxed font-serif">
                    <QuestionMarkdown content={question.question} />
                  </div>
                </div>
              </div>

              {/* Options */}
              <div className="space-y-4 pl-10">
                {isMultipleChoice ? (
                  // Multiple Choice (Checkboxes)
                  <div className="space-y-3">
                    {question.options.map((option, optIndex) => {
                      const selectedOptions = currentAnswer ? currentAnswer.split('|') : [];
                      const isChecked = selectedOptions.includes(option);
                      const optionLetter = String.fromCharCode(65 + optIndex);

                      return (
                        <label
                          key={optIndex}
                          className={cn(
                            "group flex items-center gap-4 px-5 py-4 rounded-xl border-2 transition-all duration-200 cursor-pointer",
                            "hover:border-sage-400 hover:bg-sage-50/80 hover:shadow-md hover:-translate-y-0.5",
                            isChecked 
                              ? "border-sage-600 bg-gradient-to-br from-sage-50 to-sage-100 shadow-lg ring-2 ring-sage-200" 
                              : "border-sage-200 bg-white hover:border-sage-300"
                          )}
                        >
                          <div className={cn(
                            "flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 text-sm font-bold",
                            isChecked 
                              ? "bg-sage-600 text-white shadow-md scale-110" 
                              : "bg-gradient-to-br from-sage-50 to-sage-100 text-sage-700 group-hover:from-sage-100 group-hover:to-sage-200"
                          )}>
                            {isChecked ? <CheckCircle2 className="w-5 h-5" /> : optionLetter}
                          </div>
                          <div className="flex-1 leading-relaxed text-foreground text-sm">
                            <QuestionMarkdown content={option} />
                          </div>
                          <Checkbox
                            id={`q${index}-opt${optIndex}`}
                            checked={isChecked}
                            onCheckedChange={(checked) => {
                              let newSelected = [...selectedOptions];
                              if (checked) {
                                newSelected.push(option);
                              } else {
                                newSelected = newSelected.filter((o) => o !== option);
                              }
                              onAnswerChange({
                                ...answers,
                                [index]: newSelected.join('|'),
                              });
                            }}
                            className="sr-only"
                          />
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  // Single Choice (Radio)
                  <RadioGroup
                    value={currentAnswer || ''}
                    onValueChange={(value) => {
                      onAnswerChange({
                        ...answers,
                        [index]: value,
                      });
                    }}
                  >
                    <div className="space-y-3">
                      {question.options.map((option, optIndex) => {
                        const isSelected = currentAnswer === option;
                        const optionLetter = String.fromCharCode(65 + optIndex);

                        return (
                          <label
                            key={optIndex}
                            htmlFor={`q${index}-opt${optIndex}`}
                            className={cn(
                              "group flex items-center gap-4 px-5 py-4 rounded-xl border-2 transition-all duration-200 cursor-pointer",
                              "hover:border-sage-400 hover:bg-sage-50/80 hover:shadow-md hover:-translate-y-0.5",
                              isSelected 
                                ? "border-sage-600 bg-gradient-to-br from-sage-50 to-sage-100 shadow-lg ring-2 ring-sage-200" 
                                : "border-sage-200 bg-white hover:border-sage-300"
                            )}
                          >
                            <div className={cn(
                              "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 text-xs font-semibold",
                              isSelected ? "bg-sage-600 text-white" : "bg-sage-100 text-sage-600 group-hover:bg-sage-200"
                            )}>
                              {optionLetter}
                            </div>
                            <div className="flex-1 leading-relaxed text-foreground text-sm">
                              <QuestionMarkdown content={option} />
                            </div>
                            <RadioGroupItem
                              value={option}
                              id={`q${index}-opt${optIndex}`}
                              className="sr-only"
                            />
                          </label>
                        );
                      })}
                    </div>
                  </RadioGroup>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Submit Button */}
      <div className="pt-6 border-t">
        <Button
          onClick={onSubmit}
          disabled={!allAnswered || isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? 'Evaluating...' : 'Submit Assessment'}
        </Button>
        {!allAnswered && (
          <p className="text-sm text-muted-foreground text-center mt-3">
            Please answer all questions before submitting
          </p>
        )}
      </div>
    </div>
  );
}

