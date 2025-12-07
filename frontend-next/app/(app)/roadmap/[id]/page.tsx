'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Clock,
  ChevronDown,
  ChevronRight,
  List,
  Network,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { getRoadmap, approveRoadmap, getRoadmapActiveTask, getRoadmapStatus } from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';
import { useRoadmap } from '@/lib/hooks/api/use-roadmap';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useUIStore } from '@/lib/store/ui-store';
import { TutorialDialog } from '@/components/tutorial/tutorial-dialog';
import { 
  PhaseProgress,
  CompactPhaseIndicator,
  ConceptCard, 
  RoadmapSkeletonView,
  HumanReviewDialog,
  RetryFailedButton,
} from '@/components/roadmap';
import { 
  GenerationPhase, 
  parseStepWithSubStatus,
  HumanReviewSubStatus,
} from '@/types/custom/phases';
import type { ViewMode } from '@/types/custom/ui';
import type { Stage, Module, Concept, LearningPreferences, RoadmapFramework } from '@/types/generated/models';
import { cn } from '@/lib/utils';

const PHASE_LABELS: Record<string, string> = {
  intent_analysis: 'Intent Analysis',
  curriculum_design: 'Curriculum Design',
  human_review: 'Human Review',
  content_generation: 'Content Generation',
  completed: 'Completed',
};

export default function RoadmapDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const roadmapId = params.id as string;

  // Use React Query Hook to fetch roadmap
  const { 
    data: roadmapData, 
    isLoading: roadmapLoading, 
    error: roadmapError, 
    refetch: refetchRoadmap 
  } = useRoadmap(roadmapId);

  // Task ID state (fetched from roadmap's active task)
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isLiveGenerating, setIsLiveGenerating] = useState(false);

  // Store state
  const { 
    currentRoadmap, 
    setRoadmap, 
    setLoading, 
    setError, 
    selectedConceptId, 
    selectConcept,
    updateConceptStatus,
  } = useRoadmapStore();
  
  const viewMode = useUIStore((state) => state.viewMode);
  const setViewMode = useUIStore((state) => state.setViewMode);

  // Local state
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());
  const [currentPhase, setCurrentPhase] = useState<GenerationPhase | null>(null);
  const [phaseSubStatus, setPhaseSubStatus] = useState<HumanReviewSubStatus>(null);
  const [generationStats, setGenerationStats] = useState<{
    completed: number;
    total: number;
    failed: number;
  }>({ completed: 0, total: 0, failed: 0 });
  
  // Human review dialog state
  const [showHumanReviewDialog, setShowHumanReviewDialog] = useState(false);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  
  // Failed content stats (for retry button)
  const [failedStats, setFailedStats] = useState({
    tutorial: 0,
    resources: 0,
    quiz: 0,
  });
  
  // Retry task state
  const [retryTaskId, setRetryTaskId] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  
  // User preferences (would typically come from user profile/store)
  const userPreferences: LearningPreferences = {
    learning_goal: currentRoadmap?.title || '',
    available_hours_per_week: 10,
    motivation: 'Systematic learning',
    current_level: 'intermediate',
    career_background: '',
    content_preference: ['text', 'hands_on'],
  };
  
  // WebSocket refs
  const wsRef = useRef<TaskWebSocket | null>(null);
  const retryWsRef = useRef<TaskWebSocket | null>(null);
  const initialLoadCompleteRef = useRef(false);

  // Sync roadmapData to store and expand states
  useEffect(() => {
    if (!roadmapData) return;
    
    // Type guard to ensure roadmapData is RoadmapFramework
    const roadmap = roadmapData as RoadmapFramework;
    if (!roadmap.stages) return;
    
    setRoadmap(roadmap);
    
    // Expand all stages and modules by default
    setExpandedStages(new Set(roadmap.stages.map((s: Stage) => s.stage_id)));
    setExpandedModules(
      new Set(roadmap.stages.flatMap((s: Stage) => s.modules.map((m: Module) => m.module_id)))
    );

    // Calculate initial stats
    const allConcepts = roadmap.stages.flatMap((s: Stage) =>
      s.modules.flatMap((m: Module) => m.concepts)
    );
    const completed = allConcepts.filter((c: Concept) => c.content_status === 'completed').length;
    const failed = allConcepts.filter((c: Concept) => c.content_status === 'failed').length;
    setGenerationStats({
      completed,
      total: allConcepts.length,
      failed,
    });
    
    // Calculate failed stats by content type
    let tutorialFailed = 0;
    let resourcesFailed = 0;
    let quizFailed = 0;
    for (const concept of allConcepts) {
      if ((concept as any).content_status === 'failed') tutorialFailed++;
      if ((concept as any).resources_status === 'failed') resourcesFailed++;
      if ((concept as any).quiz_status === 'failed') quizFailed++;
    }
    setFailedStats({
      tutorial: tutorialFailed,
      resources: resourcesFailed,
      quiz: quizFailed,
    });

    initialLoadCompleteRef.current = true;
  }, [roadmapData, setRoadmap]);

  // Check for active task when roadmap is loaded
  useEffect(() => {
    if (!roadmapData || !initialLoadCompleteRef.current) return;

    const checkActiveTask = async () => {
      try {
        const activeTask = await getRoadmapActiveTask(roadmapId);
        if (activeTask.has_active_task && activeTask.task_id) {
          console.log('[Roadmap] Found active task:', activeTask.task_id, activeTask.status);
          setTaskId(activeTask.task_id);
          
          // Set up WebSocket or polling based on task status
          if (activeTask.status === 'processing') {
            setIsPolling(true);
            setIsLiveGenerating(true);
            
            // Determine initial phase from current step
            const phaseState = parseStepWithSubStatus(activeTask.current_step || '', undefined);
            if (phaseState) {
              setCurrentPhase(phaseState.phase);
            }
          } else if (activeTask.status === 'human_review_pending') {
            setCurrentPhase('human_review');
            setPhaseSubStatus('waiting');
            setShowHumanReviewDialog(true);
          }
        } else {
          console.log('[Roadmap] No active task found');
          setTaskId(null);
          setIsPolling(false);
          setIsLiveGenerating(false);
        }
      } catch (err) {
        // Active task query might fail, ignore and just show roadmap
        console.warn('Failed to check active task:', err);
      }
    };

    checkActiveTask();
  }, [roadmapData, roadmapId]);

  // Poll task status if task is processing
  useEffect(() => {
    if (!isPolling || !taskId || !initialLoadCompleteRef.current) {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await getRoadmapStatus(taskId);
        
        // Update phase based on current step
        const phaseState = parseStepWithSubStatus(status.current_step || '', undefined);
        if (phaseState) {
          setCurrentPhase(phaseState.phase);
        }
        
        // If task is completed or failed, stop polling
        if (status.status === 'completed' || status.status === 'failed' || (status.status as string) === 'partial_failure') {
          setIsPolling(false);
          setIsLiveGenerating(false);
          setCurrentPhase('completed');
          // Refresh roadmap data
          refetchRoadmap();
        } else if (!currentRoadmap && status.roadmap_id) {
          // If roadmap doesn't exist yet but task has roadmap_id, try to load it
          console.log('[Roadmap] Task has roadmap_id, attempting to load roadmap...');
          refetchRoadmap();
        }
      
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [isPolling, taskId, currentRoadmap, roadmapId, refetchRoadmap]);

  // Set up WebSocket for live generation updates
  useEffect(() => {
    const shouldConnect = isLiveGenerating && taskId;

    if (!shouldConnect || !initialLoadCompleteRef.current) {
      return;
    }

    console.log('[Roadmap] Setting up WebSocket for task:', taskId);

    const ws = new TaskWebSocket(taskId, {
      onConnected: (event) => {
        console.log('[Roadmap WS] Connected:', event.message);
      },

      onProgress: (event) => {
        console.log('[Roadmap WS] Progress:', event);
        const subStatus = (event as any).sub_status as string | undefined;
        const phaseState = parseStepWithSubStatus(event.step, subStatus);
        if (phaseState) {
          setCurrentPhase(phaseState.phase);
          setPhaseSubStatus(phaseState.subStatus || null);
          
          // Handle human_review step - show dialog
          if (phaseState.phase === 'human_review' && phaseState.subStatus === 'waiting') {
            setShowHumanReviewDialog(true);
          }
        }
      },

      onConceptStart: (event) => {
        console.log('[Roadmap WS] Concept start:', event);
        // Update concept status to generating
        updateConceptStatus(event.concept_id, { tutorial_status: 'generating' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          total: event.progress.total,
        }));
      },

      onConceptComplete: (event) => {
        console.log('[Roadmap WS] Concept complete:', event);
        // Update concept status to completed
        updateConceptStatus(event.concept_id, { tutorial_status: 'completed' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          completed: prev.completed + 1,
        }));
      },

      onConceptFailed: (event) => {
        console.log('[Roadmap WS] Concept failed:', event);
        // Update concept status to failed
        updateConceptStatus(event.concept_id, { tutorial_status: 'failed' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          failed: prev.failed + 1,
        }));
        
        // Update failed stats (assume tutorial for now, will be refreshed on batch complete)
        setFailedStats(prev => ({
          ...prev,
          tutorial: prev.tutorial + 1,
        }));
      },

      onBatchComplete: (event) => {
        console.log('[Roadmap WS] Batch complete:', event);
        // Refresh roadmap data to get latest state
        refetchRoadmap();
      },

      onCompleted: (event) => {
        console.log('[Roadmap WS] Generation completed:', event);
        setCurrentPhase('completed');
        setIsLiveGenerating(false);
        setIsPolling(false);
        
        // Final refresh to ensure all data is up to date
        refetchRoadmap();
      },

      onFailed: (event) => {
        console.error('[Roadmap WS] Generation failed:', event);
        setIsLiveGenerating(false);
        setIsPolling(false);
      },

      onError: (event) => {
        console.error('[Roadmap WS] Error:', event);
      },

      onClosing: (event) => {
        console.log('[Roadmap WS] Closing:', event.reason);
      },
    });

    wsRef.current = ws;
    ws.connect(false); // Don't include history, we already have the roadmap

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    };
  }, [
    taskId, 
    isLiveGenerating,
    isPolling,
    currentPhase,
    updateConceptStatus,
    refetchRoadmap,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
      if (retryWsRef.current) {
        retryWsRef.current.disconnect();
      }
    };
  }, []);

  // Handle retry task WebSocket
  useEffect(() => {
    if (!retryTaskId || !isRetrying) return;

    console.log('[Roadmap] Setting up WebSocket for retry task:', retryTaskId);

    const ws = new TaskWebSocket(retryTaskId, {
      onConnected: (event) => {
        console.log('[Retry WS] Connected:', event.message);
      },

      onProgress: async (event) => {
        console.log('[Retry WS] Progress:', event);
        
        // 处理 retry_completed 事件，更新失败统计并刷新数据
        const eventData = event.data as Record<string, unknown> | undefined;
        if (event.step === 'retry_completed' && eventData?.remaining_failed) {
          const remaining = eventData.remaining_failed as { tutorial: number; resources: number; quiz: number };
          setFailedStats(remaining);
          
          // 更新总体统计
          const totalFailed = remaining.tutorial + remaining.resources + remaining.quiz;
          setGenerationStats(prev => ({
            ...prev,
            failed: totalFailed,
          }));
          
          console.log('[Retry WS] Updated failed stats:', remaining);
          
          // 如果 framework 已更新，立即刷新 roadmap 数据
          if (eventData.framework_updated) {
            console.log('[Retry WS] Framework updated, refreshing roadmap data...');
            await refetchRoadmap();
          }
        }
      },

      onConceptStart: (event) => {
        console.log('[Retry WS] Concept start:', event);
        // Update concept status to generating
        updateConceptStatus(event.concept_id, { tutorial_status: 'generating' });
      },

      onConceptComplete: (event) => {
        console.log('[Retry WS] Concept complete:', event);
        // Update concept status to completed
        updateConceptStatus(event.concept_id, { tutorial_status: 'completed' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          completed: prev.completed + 1,
        }));
      },

      onConceptFailed: (event) => {
        console.log('[Retry WS] Concept failed:', event);
        // Update concept status to failed
        updateConceptStatus(event.concept_id, { tutorial_status: 'failed' });
        
        // Update failed stats
        setGenerationStats(prev => ({
          ...prev,
          failed: prev.failed + 1,
        }));
        
        setFailedStats(prev => ({
          ...prev,
          tutorial: prev.tutorial + 1,
        }));
      },

      onCompleted: async (event) => {
        console.log('[Retry WS] Retry completed:', event);
        setIsRetrying(false);
        setRetryTaskId(null);
        
        // 强制刷新以获取最新的 framework_data
        // refetchRoadmap 会重新计算 failedStats
        await refetchRoadmap();
        
        console.log('[Retry WS] Roadmap data refreshed after retry');
      },

      onFailed: (event) => {
        console.error('[Retry WS] Retry failed:', event);
        setIsRetrying(false);
        setRetryTaskId(null);
      },

      onError: (event) => {
        console.error('[Retry WS] Error:', event);
      },
    });

    retryWsRef.current = ws;
    ws.connect(false);

    return () => {
      if (retryWsRef.current) {
        retryWsRef.current.disconnect();
        retryWsRef.current = null;
      }
    };
  }, [retryTaskId, isRetrying, updateConceptStatus, refetchRoadmap]);

  // Human review handlers
  const handleApproveReview = async () => {
    if (!taskId) return;
    
    setIsSubmittingReview(true);
    try {
      await approveRoadmap(taskId, true);
      setShowHumanReviewDialog(false);
      // Phase will be updated via WebSocket
    } catch (error) {
      console.error('Failed to approve roadmap:', error);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleRejectReview = async (feedback: string) => {
    if (!taskId) return;
    
    setIsSubmittingReview(true);
    try {
      await approveRoadmap(taskId, false, feedback);
      setShowHumanReviewDialog(false);
      setPhaseSubStatus('editing');
      // Phase will be updated via WebSocket
    } catch (error) {
      console.error('Failed to reject roadmap:', error);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // Retry handlers
  const handleRetryStarted = (taskId: string) => {
    console.log('[Roadmap] Retry started, task_id:', taskId);
    setRetryTaskId(taskId);
    setIsRetrying(true);
    
    // 立即更新失败概念的状态为 'generating'
    if (currentRoadmap) {
      const allConcepts = currentRoadmap.stages.flatMap((s: Stage) =>
        s.modules.flatMap((m: Module) => m.concepts)
      );
      
      // 更新所有失败概念的状态
      for (const concept of allConcepts) {
        const conceptAny = concept as any;
        if (conceptAny.content_status === 'failed' || 
            conceptAny.resources_status === 'failed' || 
            conceptAny.quiz_status === 'failed') {
          updateConceptStatus(concept.concept_id, { tutorial_status: 'generating' });
        }
      }
      
      // 重置失败统计（重试中）
      setGenerationStats(prev => ({
        ...prev,
        failed: 0,
      }));
      
      setFailedStats({
        tutorial: 0,
        resources: 0,
        quiz: 0,
      });
    }
  };

  const handleRetryCompleted = () => {
    console.log('[Roadmap] Retry completed');
    setIsRetrying(false);
    setRetryTaskId(null);
    refetchRoadmap();
  };

  const toggleStage = (stageId: string) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(stageId)) {
        next.delete(stageId);
      } else {
        next.add(stageId);
      }
      return next;
    });
  };

  const toggleModule = (moduleId: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  };

  const calculateProgress = () => {
    if (!currentRoadmap) return 0;
    const allConcepts = currentRoadmap.stages.flatMap((s: Stage) =>
      s.modules.flatMap((m: Module) => m.concepts)
    );
    if (allConcepts.length === 0) return 0;
    const completedConcepts = allConcepts.filter(
      (c: Concept) => c.content_status === 'completed'
    ).length;
    return (completedConcepts / allConcepts.length) * 100;
  };

  const isGenerating = isLiveGenerating || isPolling || (currentPhase && currentPhase !== 'completed');
  
  // 重试按钮显示条件
  const shouldShowRetryButton = 
    (failedStats.tutorial > 0 || failedStats.resources > 0 || failedStats.quiz > 0) && 
    !isRetrying && 
    (currentPhase === 'completed' || currentPhase === null || !isLiveGenerating);

  // Loading state or generating state
  if ((roadmapLoading && !currentRoadmap) || (isLiveGenerating && !currentRoadmap)) {
    return (
      <div className="container mx-auto px-4 py-12 max-w-5xl">
        {/* Compact Phase Indicator */}
        {currentPhase && (
          <div className="mb-8 p-5 rounded-xl bg-white/60 dark:bg-zinc-900/60 backdrop-blur-md border border-zinc-200/60 dark:border-zinc-800/60 shadow-sm">
            <CompactPhaseIndicator 
              currentPhase={currentPhase} 
              failedCount={0}
            />
          </div>
        )}
        
        <div className="mb-10 space-y-4">
          <div className="h-12 w-2/3 bg-muted/40 rounded-lg animate-pulse" />
          <div className="h-4 w-1/3 bg-muted/30 rounded animate-pulse" />
          {isLiveGenerating && (
            <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Generating roadmap, please wait...</span>
            </div>
          )}
        </div>
        <RoadmapSkeletonView />
      </div>
    );
  }

  // Error state
  if (roadmapError) {
    return (
      <div className="container mx-auto px-4 py-20 flex justify-center">
        <Card className="w-full max-w-md bg-white/50 dark:bg-zinc-900/50 backdrop-blur-md border-red-100 dark:border-red-900/30">
          <CardContent className="py-12 flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-4">
               <AlertCircle className="w-6 h-6 text-red-500" />
            </div>
            <p className="text-lg font-serif font-medium text-zinc-900 dark:text-zinc-50 mb-2">Load failed</p>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
              {roadmapError instanceof Error ? roadmapError.message : 'Load failed'}
            </p>
            <Button onClick={() => refetchRoadmap()} variant="outline" className="gap-2">
              <RefreshCw className="w-4 h-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No roadmap found
  if (!currentRoadmap) {
    return (
      <div className="container mx-auto px-4 py-20 flex justify-center">
         <div className="text-center text-zinc-400">
           <p className="text-lg font-serif">Roadmap not found</p>
         </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      
      {/* Compact Phase Indicator */}
      {(isGenerating && currentPhase) && (
        <div className="mb-8 p-5 rounded-xl bg-white/60 dark:bg-zinc-900/60 backdrop-blur-md border border-zinc-200/60 dark:border-zinc-800/60 shadow-sm">
          <CompactPhaseIndicator 
            currentPhase={currentPhase} 
            failedCount={generationStats.failed}
          />
        </div>
      )}
      
      {/* Header Section */}
      <div className="mb-10 relative">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-6">
          <div className="space-y-3 flex-1">
             <h1 className="text-3xl md:text-4xl font-serif font-semibold text-zinc-900 dark:text-zinc-50 tracking-tight leading-tight">
               {currentRoadmap.title}
             </h1>

             <div className="flex items-center gap-6 text-sm text-zinc-500 dark:text-zinc-400">
                <div className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4 opacity-70" />
                  <span>{currentRoadmap.total_estimated_hours} hours</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="opacity-70">Duration:</span>
                  <span>{currentRoadmap.recommended_completion_weeks} weeks</span>
                </div>
                {generationStats.failed > 0 && !isGenerating && (
                  <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-500">
                     <AlertTriangle className="h-4 w-4" />
                     <span>{generationStats.failed} concepts failed</span>
                  </div>
                )}
             </div>
          </div>

          {/* Actions & Retry */}
          <div className="flex items-center gap-3">
             {shouldShowRetryButton && (
                <RetryFailedButton
                  roadmapId={roadmapId}
                  userId="default-user"
                  preferences={userPreferences}
                  failedStats={failedStats}
                  onRetryStarted={handleRetryStarted}
                  onRetryCompleted={handleRetryCompleted}
                />
             )}
          </div>
        </div>

        {/* Progress Bar - Slim & Elegant */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-zinc-500 dark:text-zinc-400">
            <span>{isGenerating || isRetrying ? 'Content generation progress' : 'Learning progress'}</span>
            <span>{Math.round(calculateProgress())}%</span>
          </div>
          <Progress 
            value={calculateProgress()} 
            className="h-1.5 bg-zinc-100 dark:bg-zinc-800" 
            indicatorClassName="bg-sage-600 dark:bg-sage-500"
          />
        </div>
      </div>

      {/* Detailed Generation Progress (Glass Card) */}
      {isGenerating && currentPhase === 'content_generation' && (
        <div className="mb-8 p-6 rounded-xl bg-white/60 dark:bg-zinc-900/60 backdrop-blur-md border border-blue-100/50 dark:border-blue-900/20 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-pulse" />
              </div>
              <div>
                <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                  Generating learning content
                </p>
                <p className="text-xs text-zinc-500">
                  {generationStats.completed} / {generationStats.total} concepts completed
                  {generationStats.failed > 0 && ` (${generationStats.failed} failed)`}
                </p>
              </div>
            </div>
            <PhaseProgress 
              currentPhase={currentPhase} 
              subStatus={phaseSubStatus}
              failedCount={generationStats.failed}
            />
        </div>
      )}

      {/* View Mode Toggle */}
      <div className="mb-8 border-b border-zinc-200/50 dark:border-zinc-800/50 pb-1">
        <Tabs value={viewMode} onValueChange={(v: string) => setViewMode(v as ViewMode)} className="w-auto">
          <TabsList className="bg-transparent p-0 h-auto">
            <TabsTrigger 
              value="list" 
              className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-sage-600 data-[state=active]:text-sage-700 dark:data-[state=active]:text-sage-300 rounded-none px-4 py-2 text-zinc-500 transition-all"
            >
              <List className="h-4 w-4 mr-2" />
              Knowledge Outline
            </TabsTrigger>
            <TabsTrigger 
              value="flow" 
              className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-sage-600 data-[state=active]:text-sage-700 dark:data-[state=active]:text-sage-300 rounded-none px-4 py-2 text-zinc-500 transition-all"
            >
              <Network className="h-4 w-4 mr-2" />
              Knowledge Graph (coming soon)
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      <ScrollArea className="h-[calc(100vh-320px)] pr-4 -mr-4">
        {viewMode === 'list' ? (
          <div className="space-y-6 pb-20">
            {currentRoadmap.stages
              .sort((a: Stage, b: Stage) => a.order - b.order)
              .map((stage: Stage) => (
                <Card 
                  key={stage.stage_id} 
                  className="overflow-hidden border-zinc-200/60 dark:border-zinc-800/60 bg-white/60 dark:bg-zinc-900/60 backdrop-blur-xl shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <CardHeader 
                    className="cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors p-6" 
                    onClick={() => toggleStage(stage.stage_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="text-zinc-400">
                           {expandedStages.has(stage.stage_id) ? (
                             <ChevronDown className="h-5 w-5" />
                           ) : (
                             <ChevronRight className="h-5 w-5" />
                           )}
                        </div>
                        <div>
                          <CardTitle className="text-xl font-serif font-semibold text-zinc-900 dark:text-zinc-50 tracking-tight">{stage.name}</CardTitle>
                          {stage.description && (
                             <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1.5 font-normal leading-relaxed">
                               {stage.description}
                             </p>
                          )}
                        </div>
                      </div>
                      <StageProgressBadge 
                        modules={stage.modules} 
                        isGenerating={isGenerating || false}
                      />
                    </div>
                  </CardHeader>

                  <div className={cn(
                      "grid transition-all duration-300 ease-in-out",
                      expandedStages.has(stage.stage_id) ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                    )}>
                    <div className="overflow-hidden">
                      <CardContent className="space-y-4 pt-0 p-6">
                        {stage.modules.map((module: Module) => (
                          <div 
                            key={module.module_id} 
                            className="group rounded-xl border border-transparent bg-white/40 dark:bg-zinc-800/40 hover:bg-white/80 dark:hover:bg-zinc-800/80 hover:border-zinc-200/50 dark:hover:border-zinc-700/50 backdrop-blur-sm transition-all duration-200"
                          >
                            <div
                              className="p-5 cursor-pointer"
                              onClick={() => toggleModule(module.module_id)}
                            >
                              <div className="flex items-center gap-3">
                                <div className="text-zinc-400 group-hover:text-zinc-600 transition-colors">
                                   {expandedModules.has(module.module_id) ? (
                                     <ChevronDown className="h-4 w-4" />
                                   ) : (
                                     <ChevronRight className="h-4 w-4" />
                                   )}
                                </div>
                                <div className="flex-1">
                                   <div className="flex items-center justify-between mb-1">
                                      <h3 className="text-base font-medium text-zinc-800 dark:text-zinc-200">{module.name}</h3>
                                      <Badge variant="secondary" className="bg-zinc-100/80 dark:bg-zinc-800/80 text-zinc-500 text-xs font-normal">
                                        {module.concepts.length} concepts
                                      </Badge>
                                   </div>
                                   {expandedModules.has(module.module_id) && module.description && (
                                     <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
                                       {module.description}
                                     </p>
                                   )}
                                </div>
                              </div>
                            </div>

                            <div className={cn(
                                "grid transition-all duration-300 ease-in-out",
                                expandedModules.has(module.module_id) ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                              )}>
                                <div className="overflow-hidden">
                                  <div className="p-5 pt-0 space-y-3 pl-12">
                                    {module.concepts.map((concept: Concept) => (
                                      <ConceptCard
                                        key={concept.concept_id}
                                        concept={concept}
                                        onClick={() => {
                                          if (concept.content_status === 'completed') {
                                            selectConcept(concept.concept_id);
                                          }
                                        }}
                                      />
                                    ))}
                                  </div>
                                </div>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </div>
                  </div>
                </Card>
              ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full min-h-[400px]">
            <div className="text-center text-zinc-400">
              <Network className="h-16 w-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg font-serif mb-2">Knowledge Graph</p>
              <p className="text-sm">This feature is under development</p>
              <Button variant="link" className="mt-4 text-sage-600" onClick={() => setViewMode('list' as ViewMode)}>
                Back to Knowledge Outline
              </Button>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Tutorial Dialog */}
      {selectedConceptId && (
        <TutorialDialog
          roadmapId={roadmapId}
          conceptId={selectedConceptId}
          onClose={() => selectConcept(null)}
        />
      )}

      {/* Human Review Dialog */}
      <HumanReviewDialog
        open={showHumanReviewDialog}
        onOpenChange={setShowHumanReviewDialog}
        taskId={taskId || ''}
        roadmapId={roadmapId}
        roadmapTitle={currentRoadmap.title}
        stagesCount={currentRoadmap.stages.length}
        onApprove={handleApproveReview}
        onReject={handleRejectReview}
        isSubmitting={isSubmittingReview}
      />
    </div>
  );
}

/**
 * StageProgressBadge - Shows completion status for a stage
 */
interface ConceptStatus {
  content_status?: string;
}

interface ModuleWithConcepts {
  concepts: ConceptStatus[];
}

function StageProgressBadge({ 
  modules, 
  isGenerating 
}: { 
  modules: ModuleWithConcepts[];
  isGenerating?: boolean;
}) {
  const allConcepts = modules.flatMap((m: ModuleWithConcepts) => m.concepts);
  const completed = allConcepts.filter((c: ConceptStatus) => c.content_status === 'completed').length;
  const generating = allConcepts.filter((c: ConceptStatus) => c.content_status === 'generating').length;
  const total = allConcepts.length;

  if (isGenerating && generating > 0) {
    return (
      <Badge variant="secondary" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-100 dark:border-blue-900/50 font-normal">
        Generating {completed}/{total}
      </Badge>
    );
  }

  if (completed === total) {
    return (
      <Badge variant="secondary" className="bg-sage-50 text-sage-700 dark:bg-sage-900/30 dark:text-sage-300 border border-sage-100 dark:border-sage-900/50 font-normal">
        Completed
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 font-normal">
      {completed}/{total}
    </Badge>
  );
}
