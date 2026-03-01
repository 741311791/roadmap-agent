'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
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
  // 处理换行符：将 \n 转换为 Markdown 换行（两个空格 + \n）
  const formattedContent = content.replace(/\n/g, '  \n');
  
  return (
    <div className="w-full min-w-0 overflow-hidden">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 代码块渲染
          code({ node, className, children, ...props }) {
            const isInline = !className?.includes('language-');
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';

            if (!isInline && language) {
              // 多行代码块：父容器显式限宽，pre 内部横向滚动
              return (
                <div className="my-2 rounded-lg border border-slate-700/30 bg-slate-950/95 shadow-sm w-full max-w-full overflow-hidden">
                  <pre className="p-2 sm:p-3 overflow-x-auto max-w-full text-xs leading-relaxed">
                    <code className={cn(className, 'whitespace-pre')} {...props}>
                      {children}
                    </code>
                  </pre>
                </div>
              );
            }

            // 行内代码：break-all 防止长字符串撑破布局
            return (
              <code
                className="px-1.5 py-0.5 rounded bg-sage-50 text-sage-900 text-xs font-mono border border-sage-300/50 font-semibold break-all"
                {...props}
              >
                {children}
              </code>
            );
          },
          // 段落：block 展示，限制最大宽度
          p({ children }) {
            return <span className="block leading-relaxed break-words">{children}</span>;
          },
          br() {
            return <br />;
          },
          h1: ({ children }) => <strong className="text-base">{children}</strong>,
          h2: ({ children }) => <strong className="text-sm">{children}</strong>,
          h3: ({ children }) => <strong className="text-sm">{children}</strong>,
        }}
      >
        {formattedContent}
      </ReactMarkdown>
    </div>
  );
}

export function AssessmentQuestions({
  assessment,
  answers,
  onAnswerChange,
  onSubmit,
  isSubmitting,
}: AssessmentQuestionsProps) {
  const t = useTranslations('profile.assessment');

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
        return t('levelBeginner');
      case 'intermediate':
        return t('levelIntermediate');
      case 'expert':
        return t('levelExpert');
      default:
        return t('levelGeneral');
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* 进度头部 */}
      <div className="flex items-center justify-between gap-2 py-2 border-b">
        <p className="text-xs sm:text-sm font-medium text-muted-foreground shrink-0">
          {t('progress', { answered: answeredCount, total: totalQuestions })}
        </p>
        <Badge variant={allAnswered ? 'default' : 'secondary'} className="text-xs shrink-0">
          {allAnswered ? t('completed') : t('inProgress')}
        </Badge>
      </div>

      {/* 题目列表 */}
      <div className="space-y-4 sm:space-y-5">
        {assessment.questions.map((question, index) => {
          const isMultipleChoice = question.type === 'multiple_choice';
          const currentAnswer = answers[index];

          return (
            <div 
              key={index} 
              className="p-3 sm:p-5 rounded-xl border border-sage-100 bg-gradient-to-br from-white to-sage-50/30 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden"
            >
              {/* 题目头部 */}
              <div className="flex items-start gap-3 mb-3 sm:mb-4">
                {/* 题号徽章 */}
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sage-600 flex items-center justify-center text-xs font-serif font-bold text-white shadow-sm">
                  {index + 1}
                </div>

                {/* 题目内容区域 */}
                <div className="flex-1 min-w-0 overflow-hidden">
                  {/* 难度和类型徽章 */}
                  <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2">
                    <span className={cn(
                      "inline-flex px-2 py-0.5 rounded text-xs font-bold border-2 uppercase tracking-wider shadow-sm whitespace-nowrap",
                      getProficiencyBadgeVariant(question.proficiency_level)
                    )}>
                      {getProficiencyLabel(question.proficiency_level)}
                    </span>
                    <span className="text-xs text-slate-500 font-medium whitespace-nowrap">
                      {isMultipleChoice ? `✓ ${t('typeMultiple')}` : `◉ ${t('typeSingle')}`}
                    </span>
                  </div>

                  {/* 题目文本 */}
                  <div className="text-sm font-medium text-foreground leading-relaxed font-serif break-words overflow-hidden">
                    <QuestionMarkdown content={question.question} />
                  </div>
                </div>
              </div>

              {/* 选项列表 */}
              <div className="space-y-2 sm:space-y-3">
                {isMultipleChoice ? (
                  // 多选题（Checkbox）
                  <div className="space-y-2">
                    {question.options.map((option, optIndex) => {
                      const selectedOptions = currentAnswer ? currentAnswer.split('|') : [];
                      const isChecked = selectedOptions.includes(option);
                      const optionLetter = String.fromCharCode(65 + optIndex);

                      return (
                        <label
                          key={optIndex}
                          className={cn(
                            "group flex items-start gap-2 sm:gap-3 px-3 py-2.5 rounded-lg border-2 transition-all duration-200 cursor-pointer",
                            "hover:border-sage-400 hover:bg-sage-50/80",
                            isChecked 
                              ? "border-sage-600 bg-gradient-to-br from-sage-50 to-sage-100 ring-1 ring-sage-200" 
                              : "border-sage-200 bg-white"
                          )}
                        >
                          <div className={cn(
                            "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5 transition-all duration-200 text-xs font-bold",
                            isChecked 
                              ? "bg-sage-600 text-white" 
                              : "bg-sage-50 text-sage-700 border border-sage-200 group-hover:bg-sage-100"
                          )}>
                            {isChecked ? <CheckCircle2 className="w-3.5 h-3.5" /> : optionLetter}
                          </div>
                          <div className="flex-1 min-w-0 overflow-hidden leading-relaxed text-foreground text-sm break-words">
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
                  // 单选题（Radio）
                  <RadioGroup
                    value={currentAnswer || ''}
                    onValueChange={(value) => {
                      onAnswerChange({
                        ...answers,
                        [index]: value,
                      });
                    }}
                  >
                    <div className="space-y-2">
                      {question.options.map((option, optIndex) => {
                        const isSelected = currentAnswer === option;
                        const optionLetter = String.fromCharCode(65 + optIndex);

                        return (
                          <label
                            key={optIndex}
                            htmlFor={`q${index}-opt${optIndex}`}
                            className={cn(
                              "group flex items-start gap-2 sm:gap-3 px-3 py-2.5 rounded-lg border-2 transition-all duration-200 cursor-pointer",
                              "hover:border-sage-400 hover:bg-sage-50/80",
                              isSelected 
                                ? "border-sage-600 bg-gradient-to-br from-sage-50 to-sage-100 ring-1 ring-sage-200" 
                                : "border-sage-200 bg-white"
                            )}
                          >
                            <div className={cn(
                              "flex-shrink-0 w-6 h-6 rounded flex items-center justify-center mt-0.5 transition-all duration-200 text-xs font-semibold",
                              isSelected ? "bg-sage-600 text-white" : "bg-sage-100 text-sage-600 group-hover:bg-sage-200"
                            )}>
                              {optionLetter}
                            </div>
                            <div className="flex-1 min-w-0 overflow-hidden leading-relaxed text-foreground text-sm break-words">
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

      {/* 提交按钮 */}
      <div className="pt-4 border-t">
        <Button
          onClick={onSubmit}
          disabled={!allAnswered || isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? t('evaluating') : t('submit')}
        </Button>
        {!allAnswered && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            {t('answerAllRequired')}
          </p>
        )}
      </div>
    </div>
  );
}

