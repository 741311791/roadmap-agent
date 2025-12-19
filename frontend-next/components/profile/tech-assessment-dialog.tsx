'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, History, Sparkles } from 'lucide-react';
import { getTechAssessment, evaluateTechAssessment, getUserProfile } from '@/lib/api/endpoints';
import { AssessmentQuestions } from './assessment-questions';
import { AssessmentResult } from './assessment-result';
import { CapabilityAnalysisReport } from './capability-analysis-report';
import { CapabilityHistoryDialog } from './capability-history-dialog';
import type { 
  TechAssessment, 
  AssessmentEvaluationResult,
  CapabilityAnalysisResult,
  TechStackItemWithAnalysis 
} from '@/types/assessment';
import { useAuthStore } from '@/lib/store/auth-store';

interface TechAssessmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  technology: string;
  proficiency: string;
}

export function TechAssessmentDialog({
  open,
  onOpenChange,
  technology,
  proficiency,
}: TechAssessmentDialogProps) {
  const { getUserId } = useAuthStore();
  const userId = getUserId();

  const [assessment, setAssessment] = useState<TechAssessment | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<AssessmentEvaluationResult | null>(null);
  const [analysisResult, setAnalysisResult] = useState<CapabilityAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // 历史报告相关状态
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [historicalAnalysis, setHistoricalAnalysis] = useState<(CapabilityAnalysisResult & { analyzed_at: string }) | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // 加载题目和历史报告
  useEffect(() => {
    if (open && technology && proficiency) {
      fetchQuestions();
      fetchHistoricalAnalysis();
    }
  }, [open, technology, proficiency]);

  const fetchQuestions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getTechAssessment(technology, proficiency);
      setAssessment(data);
      setAnswers({});
      setResult(null);
    } catch (err: any) {
      console.error('Failed to fetch assessment:', err);
      setError(err.message || 'Failed to load assessment');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!assessment || Object.keys(answers).length !== assessment.total_questions) {
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      
      // 将answers对象转换为数组（按题目顺序）
      const answersArray = Array.from({ length: assessment.total_questions }, (_, i) => answers[i] || '');
      
      const evaluationResult = await evaluateTechAssessment(
        technology,
        proficiency,
        assessment.assessment_id,
        answersArray
      );
      
      setResult(evaluationResult);
    } catch (err: any) {
      console.error('Failed to evaluate assessment:', err);
      setError(err.message || 'Failed to evaluate assessment');
    } finally {
      setIsSubmitting(false);
    }
  };

  const fetchHistoricalAnalysis = async () => {
    if (!userId) return;

    try {
      setIsLoadingHistory(true);
      const profile = await getUserProfile(userId);
      
      if (profile && profile.tech_stack) {
        const techItem = profile.tech_stack.find(
          (item: TechStackItemWithAnalysis) => 
            item.technology === technology && item.proficiency === proficiency
        );

        if (techItem?.capability_analysis) {
          setHistoricalAnalysis({
            ...techItem.capability_analysis,
            technology,
            proficiency_level: proficiency,
          } as CapabilityAnalysisResult & { analyzed_at: string });
        } else {
          setHistoricalAnalysis(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch historical analysis:', err);
      setHistoricalAnalysis(null);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleAnalysisComplete = (analysis: CapabilityAnalysisResult) => {
    setAnalysisResult(analysis);
    // 刷新历史记录
    fetchHistoricalAnalysis();
  };

  const handleViewHistory = () => {
    if (historicalAnalysis) {
      setHistoryDialogOpen(true);
    }
  };

  const handleClose = () => {
    setAssessment(null);
    setAnswers({});
    setResult(null);
    setAnalysisResult(null);
    setError(null);
    onOpenChange(false);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="text-2xl font-serif">
                {technology} - {proficiency} Assessment
              </DialogTitle>
              
              {/* View historical report button */}
              {historicalAnalysis && !result && !analysisResult && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleViewHistory}
                  disabled={isLoadingHistory}
                  className="gap-2"
                >
                  <History className="w-4 h-4" />
                  View Last Analysis
                </Button>
              )}
            </div>
          </DialogHeader>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sage-600" />
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-destructive">{error}</p>
            </div>
          ) : analysisResult ? (
            // 显示能力分析报告
            <CapabilityAnalysisReport
              result={analysisResult}
              onClose={handleClose}
              showActions={true}
            />
          ) : !result ? (
            <AssessmentQuestions
              assessment={assessment}
              answers={answers}
              onAnswerChange={setAnswers}
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
            />
          ) : (
            <AssessmentResult
              result={result}
              technology={technology}
              proficiency={proficiency}
              assessmentId={assessment?.assessment_id || ''}
              answers={Array.from({ length: assessment?.total_questions || 0 }, (_, i) => answers[i] || '')}
              userId={userId || ''}
              onClose={handleClose}
              onAnalysisComplete={handleAnalysisComplete}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* 历史报告对话框 */}
      {historicalAnalysis && (
        <CapabilityHistoryDialog
          open={historyDialogOpen}
          onOpenChange={setHistoryDialogOpen}
          technology={technology}
          proficiency={proficiency}
          capabilityAnalysis={historicalAnalysis}
        />
      )}
    </>
  );
}

