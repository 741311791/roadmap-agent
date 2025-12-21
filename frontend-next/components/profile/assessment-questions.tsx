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

interface AssessmentQuestionsProps {
  assessment: TechAssessment | null;
  answers: Record<number, string>;
  onAnswerChange: (answers: Record<number, string>) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
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
        return 'bg-sage-50 text-sage-700 border-sage-200';
      case 'intermediate':
        return 'bg-stone-100 text-stone-700 border-stone-200';
      case 'expert':
        return 'bg-stone-800 text-white border-stone-700';
      default:
        return 'bg-stone-50 text-stone-600 border-stone-200';
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
                  <div className="flex items-center gap-2 mb-3">
                    <span className={cn(
                      "inline-flex px-2.5 py-1 rounded-md text-[10px] font-semibold border uppercase tracking-wider",
                      getProficiencyBadgeVariant(question.proficiency_level)
                    )}>
                      {getProficiencyLabel(question.proficiency_level)}
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                      {isMultipleChoice ? 'Select All' : 'Choose One'}
                    </span>
                  </div>

                  {/* Question Text */}
                  <p className="text-base font-medium text-foreground leading-relaxed font-serif">
                    {question.question}
                  </p>
                </div>
              </div>

              {/* Options */}
              <div className="space-y-3 pl-14">
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
                            "group flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all duration-200 cursor-pointer text-sm",
                            "hover:border-sage-400 hover:bg-sage-50 hover:shadow-sm",
                            isChecked ? "border-sage-500 bg-sage-100 shadow-sm" : "border-sage-200/80 bg-white/80"
                          )}
                        >
                          <div className={cn(
                            "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 text-xs font-semibold",
                            isChecked ? "bg-sage-600 text-white" : "bg-sage-100 text-sage-600 group-hover:bg-sage-200"
                          )}>
                            {isChecked ? <CheckCircle2 className="w-4 h-4" /> : optionLetter}
                          </div>
                          <span className="flex-1 leading-relaxed text-foreground">
                            {option}
                          </span>
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
                              "group flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all duration-200 cursor-pointer text-sm",
                              "hover:border-sage-400 hover:bg-sage-50 hover:shadow-sm",
                              isSelected ? "border-sage-500 bg-sage-100 shadow-sm" : "border-sage-200/80 bg-white/80"
                            )}
                          >
                            <div className={cn(
                              "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 text-xs font-semibold",
                              isSelected ? "bg-sage-600 text-white" : "bg-sage-100 text-sage-600 group-hover:bg-sage-200"
                            )}>
                              {optionLetter}
                            </div>
                            <span className="flex-1 leading-relaxed text-foreground">
                              {option}
                            </span>
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

