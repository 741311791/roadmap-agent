'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
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
        return 'secondary' as const;
      case 'intermediate':
        return 'default' as const;
      case 'expert':
        return 'destructive' as const;
      default:
        return 'outline' as const;
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
      <div className="flex items-center justify-between sticky top-0 bg-background py-2 z-10 border-b">
        <div>
          <p className="text-sm text-muted-foreground">
            已答 {answeredCount} / {totalQuestions} 题
          </p>
        </div>
        <Badge variant={allAnswered ? 'default' : 'secondary'}>
          {allAnswered ? '已完成' : '进行中'}
        </Badge>
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        {assessment.questions.map((question, index) => {
          const isMultipleChoice = question.type === 'multiple_choice';
          const currentAnswer = answers[index];

          return (
            <Card key={index} className="border shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  {/* Proficiency Level Badge */}
                  <Badge
                    variant={getProficiencyBadgeVariant(question.proficiency_level)}
                    className="mt-1 shrink-0"
                  >
                    {getProficiencyLabel(question.proficiency_level)}
                  </Badge>

                  <div className="flex-1 space-y-4">
                    {/* Question Text */}
                    <p className="font-medium text-base leading-relaxed">
                      {index + 1}. {question.question}
                    </p>

                    {/* Options */}
                    {isMultipleChoice ? (
                      // Multiple Choice (Checkboxes)
                      <div className="space-y-2.5">
                        {question.options.map((option, optIndex) => {
                          const selectedOptions = currentAnswer ? currentAnswer.split('|') : [];
                          const isChecked = selectedOptions.includes(option);

                          return (
                            <div
                              key={optIndex}
                              className="flex items-center space-x-2.5 p-2 rounded-md hover:bg-muted/50 transition-colors"
                            >
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
                              />
                              <Label
                                htmlFor={`q${index}-opt${optIndex}`}
                                className="flex-1 cursor-pointer text-sm"
                              >
                                {option}
                              </Label>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      // Single Choice or True/False (Radio)
                      <RadioGroup
                        value={currentAnswer || ''}
                        onValueChange={(value) => {
                          onAnswerChange({
                            ...answers,
                            [index]: value,
                          });
                        }}
                      >
                        <div className="space-y-2.5">
                          {question.options.map((option, optIndex) => (
                            <div
                              key={optIndex}
                              className="flex items-center space-x-2.5 p-2 rounded-md hover:bg-muted/50 transition-colors"
                            >
                              <RadioGroupItem
                                value={option}
                                id={`q${index}-opt${optIndex}`}
                              />
                              <Label
                                htmlFor={`q${index}-opt${optIndex}`}
                                className="flex-1 cursor-pointer text-sm"
                              >
                                {option}
                              </Label>
                            </div>
                          ))}
                        </div>
                      </RadioGroup>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Submit Button */}
      <div className="sticky bottom-0 bg-background pt-4 pb-2 border-t">
        <Button
          onClick={onSubmit}
          disabled={!allAnswered || isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? '评估中...' : '提交测验'}
        </Button>
        {!allAnswered && (
          <p className="text-sm text-muted-foreground text-center mt-2">
            请回答所有题目后提交
          </p>
        )}
      </div>
    </div>
  );
}

