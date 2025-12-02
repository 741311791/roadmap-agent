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
} from 'lucide-react';
import { getRoadmap, approveRoadmap } from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useUIStore } from '@/lib/store/ui-store';
import { TutorialDialog } from '@/components/tutorial/tutorial-dialog';
import { 
  PhaseProgress, 
  ConceptCard, 
  RoadmapSkeletonView,
  StageSkeletonCard,
  HumanReviewDialog,
  RetryFailedButton,
} from '@/components/roadmap';
import { 
  GenerationPhase, 
  mapStepToPhase,
  parseStepWithSubStatus,
  GENERATION_PHASES,
  HumanReviewSubStatus,
} from '@/types/custom/phases';
import type { ViewMode } from '@/types/custom/ui';
import type { Stage, Module, Concept, LearningPreferences } from '@/types/generated/models';

export default function RoadmapDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const roadmapId = params.id as string;

  // Check for live generation mode from URL params
  const taskIdFromUrl = searchParams.get('task_id');
  const isGeneratingFromUrl = searchParams.get('generating') === 'true';

  // Store state
  const { 
    currentRoadmap, 
    setRoadmap, 
    setLoading, 
    setError, 
    isLoading, 
    error, 
    selectedConceptId, 
    selectConcept,
    updateConceptStatus,
    activeTaskId,
    activeGenerationPhase,
    isLiveGenerating,
    setActiveTask,
    setActiveGenerationPhase,
    setLiveGenerating,
    clearLiveGeneration,
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
    motivation: '系统学习',
    current_level: 'intermediate',
    career_background: '',
    content_preference: ['text', 'hands_on'],
  };
  
  // WebSocket ref
  const wsRef = useRef<TaskWebSocket | null>(null);
  const retryWsRef = useRef<TaskWebSocket | null>(null);
  const initialLoadCompleteRef = useRef(false);

  // Load roadmap data
  const loadRoadmap = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getRoadmap(roadmapId);
      setRoadmap(data);
      // Expand all stages and modules by default
      setExpandedStages(new Set(data.stages.map((s: Stage) => s.stage_id)));
      setExpandedModules(
        new Set(data.stages.flatMap((s: Stage) => s.modules.map((m: Module) => m.module_id)))
      );
      initialLoadCompleteRef.current = true;
      
      // Calculate initial stats
      const allConcepts = data.stages.flatMap((s: Stage) =>
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
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '加载失败';
      setError(errorMsg);
    }
  }, [roadmapId, setRoadmap, setLoading, setError]);

  // Initial load
  useEffect(() => {
    loadRoadmap();
  }, [loadRoadmap]);

  // Set up WebSocket for live generation updates
  useEffect(() => {
    const taskId = taskIdFromUrl || activeTaskId;
    const shouldConnect = (isGeneratingFromUrl || isLiveGenerating) && taskId;

    if (!shouldConnect || !initialLoadCompleteRef.current) {
      return;
    }

    // Set initial phase if coming from generation
    if (isGeneratingFromUrl && !currentPhase) {
      setCurrentPhase('content_generation');
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
          setActiveGenerationPhase(phaseState.phase);
          
          // Handle human_review step - show dialog
          if (phaseState.phase === 'human_review' && phaseState.subStatus === 'waiting') {
            setShowHumanReviewDialog(true);
          }
        }
      },

      onConceptStart: (event) => {
        console.log('[Roadmap WS] Concept start:', event);
        // Update concept status to generating
        updateConceptStatus(event.concept_id, { content_status: 'generating' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          total: event.progress.total,
        }));
      },

      onConceptComplete: (event) => {
        console.log('[Roadmap WS] Concept complete:', event);
        // Update concept status to completed
        updateConceptStatus(event.concept_id, { content_status: 'completed' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          completed: prev.completed + 1,
        }));
      },

      onConceptFailed: (event) => {
        console.log('[Roadmap WS] Concept failed:', event);
        // Update concept status to failed
        updateConceptStatus(event.concept_id, { content_status: 'failed' });
        
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
        loadRoadmap();
      },

      onCompleted: (event) => {
        console.log('[Roadmap WS] Generation completed:', event);
        setCurrentPhase('completed');
        setLiveGenerating(false);
        clearLiveGeneration();
        
        // Final refresh to ensure all data is up to date
        loadRoadmap();
        
        // Clean up URL params
        if (typeof window !== 'undefined') {
          const url = new URL(window.location.href);
          url.searchParams.delete('task_id');
          url.searchParams.delete('generating');
          window.history.replaceState({}, '', url.toString());
        }
      },

      onFailed: (event) => {
        console.error('[Roadmap WS] Generation failed:', event);
        setLiveGenerating(false);
        clearLiveGeneration();
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
    taskIdFromUrl, 
    isGeneratingFromUrl, 
    activeTaskId, 
    isLiveGenerating,
    currentPhase,
    updateConceptStatus,
    setActiveGenerationPhase,
    setLiveGenerating,
    clearLiveGeneration,
    loadRoadmap,
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
            await loadRoadmap();
          }
        }
      },

      onConceptStart: (event) => {
        console.log('[Retry WS] Concept start:', event);
        // Update concept status to generating
        updateConceptStatus(event.concept_id, { content_status: 'generating' });
      },

      onConceptComplete: (event) => {
        console.log('[Retry WS] Concept complete:', event);
        // Update concept status to completed
        updateConceptStatus(event.concept_id, { content_status: 'completed' });
        
        // Update stats
        setGenerationStats(prev => ({
          ...prev,
          completed: prev.completed + 1,
        }));
      },

      onConceptFailed: (event) => {
        console.log('[Retry WS] Concept failed:', event);
        // Update concept status to failed
        updateConceptStatus(event.concept_id, { content_status: 'failed' });
        
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
        // loadRoadmap 会重新计算 failedStats
        await loadRoadmap();
        
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
  }, [retryTaskId, isRetrying, updateConceptStatus, loadRoadmap]);

  // Human review handlers
  const handleApproveReview = async () => {
    if (!taskIdFromUrl && !activeTaskId) return;
    
    setIsSubmittingReview(true);
    try {
      await approveRoadmap(taskIdFromUrl || activeTaskId!, true);
      setShowHumanReviewDialog(false);
      // Phase will be updated via WebSocket
    } catch (error) {
      console.error('Failed to approve roadmap:', error);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleRejectReview = async (feedback: string) => {
    if (!taskIdFromUrl && !activeTaskId) return;
    
    setIsSubmittingReview(true);
    try {
      await approveRoadmap(taskIdFromUrl || activeTaskId!, false, feedback);
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
          updateConceptStatus(concept.concept_id, { content_status: 'generating' });
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
    loadRoadmap();
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

  const isGenerating = isLiveGenerating || isGeneratingFromUrl || (currentPhase && currentPhase !== 'completed');
  
  // 重试按钮显示条件：有失败项且不在重试中，且（已完成 或 不在主动生成中）
  // 注意：即使 URL 有 generating=true，只要不是真正在生成（isLiveGenerating），就可以显示重试按钮
  const shouldShowRetryButton = 
    (failedStats.tutorial > 0 || failedStats.resources > 0 || failedStats.quiz > 0) && 
    !isRetrying && 
    (currentPhase === 'completed' || currentPhase === null || !isLiveGenerating);

  // Debug: Log retry button visibility conditions
  useEffect(() => {
    console.log('[Roadmap] Retry button conditions:', {
      failedStats,
      isRetrying,
      currentPhase,
      isLiveGenerating,
      shouldShowRetryButton,
    });
  }, [failedStats, isRetrying, currentPhase, isLiveGenerating, shouldShowRetryButton]);

  // Loading state
  if (isLoading && !currentRoadmap) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Show skeleton during initial load */}
        <div className="mb-8">
          <div className="h-10 w-3/4 bg-muted rounded animate-pulse mb-4" />
          <div className="h-4 w-1/2 bg-muted rounded animate-pulse" />
        </div>
        <RoadmapSkeletonView />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-red-600">
              <p className="text-lg font-semibold mb-2">加载失败</p>
              <p className="text-sm text-muted-foreground mb-4">{error}</p>
              <Button onClick={loadRoadmap} className="gap-2">
                <RefreshCw className="w-4 h-4" />
                重试
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No roadmap found
  if (!currentRoadmap) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <p className="text-lg">未找到路线图</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Generation Phase Progress (shown during live generation) */}
      {isGenerating && (
        <Card className="mb-6 border-blue-200 bg-gradient-to-r from-blue-50/50 to-transparent dark:from-blue-900/20">
          <CardContent className="py-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  正在生成学习内容
                </p>
                <p className="text-xs text-muted-foreground">
                  {generationStats.completed} / {generationStats.total} 个概念已完成
                  {generationStats.failed > 0 && ` (${generationStats.failed} 个失败)`}
                </p>
              </div>
            </div>
            <PhaseProgress 
              currentPhase={currentPhase} 
              subStatus={phaseSubStatus}
              failedCount={generationStats.failed}
            />
          </CardContent>
        </Card>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between mb-2">
          <h1 className="text-3xl font-bold">{currentRoadmap.title}</h1>
          {/* Retry Failed Button */}
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
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>{currentRoadmap.total_estimated_hours} 小时</span>
          </div>
          <div className="flex items-center gap-1">
            <span>推荐完成时间: {currentRoadmap.recommended_completion_weeks} 周</span>
          </div>
          {/* Failed items warning */}
          {generationStats.failed > 0 && (currentPhase === 'completed' || !isLiveGenerating) && (
            <div className="flex items-center gap-1 text-amber-600">
              <AlertTriangle className="h-4 w-4" />
              <span>{generationStats.failed} 个概念生成失败</span>
            </div>
          )}
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">
              {isGenerating || isRetrying ? '内容生成进度' : '学习进度'}
            </span>
            <span className="text-sm text-muted-foreground">
              {Math.round(calculateProgress())}%
            </span>
          </div>
          <Progress value={calculateProgress()} className="h-2" />
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="mb-6">
        <Tabs value={viewMode} onValueChange={(v: string) => setViewMode(v as ViewMode)}>
          <TabsList>
            <TabsTrigger value="list">
              <List className="h-4 w-4 mr-2" />
              列表视图
            </TabsTrigger>
            <TabsTrigger value="flow">
              <Network className="h-4 w-4 mr-2" />
              流程图视图
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      <ScrollArea className="h-[calc(100vh-300px)]">
        {viewMode === 'list' ? (
          <div className="space-y-6">
            {currentRoadmap.stages
              .sort((a: Stage, b: Stage) => a.order - b.order)
              .map((stage: Stage) => (
                <Card key={stage.stage_id} className="overflow-hidden">
                  <CardHeader 
                    className="cursor-pointer hover:bg-muted/30 transition-colors" 
                    onClick={() => toggleStage(stage.stage_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {expandedStages.has(stage.stage_id) ? (
                          <ChevronDown className="h-5 w-5 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-muted-foreground" />
                        )}
                        <CardTitle className="text-xl">{stage.name}</CardTitle>
                        <Badge variant="outline" className="ml-2">
                          阶段 {stage.order}
                        </Badge>
                      </div>
                      <StageProgressBadge 
                        modules={stage.modules} 
                        isGenerating={isGenerating || false}
                      />
                    </div>
                    {expandedStages.has(stage.stage_id) && stage.description && (
                      <p className="text-sm text-muted-foreground mt-2 ml-7">
                        {stage.description}
                      </p>
                    )}
                  </CardHeader>

                  {expandedStages.has(stage.stage_id) && (
                    <CardContent className="space-y-4 pt-0">
                      {stage.modules.map((module: Module) => (
                        <div key={module.module_id} className="border rounded-lg bg-card">
                          <div
                            className="p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                            onClick={() => toggleModule(module.module_id)}
                          >
                            <div className="flex items-center gap-2">
                              {expandedModules.has(module.module_id) ? (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                              )}
                              <h3 className="font-semibold">{module.name}</h3>
                              <Badge variant="secondary" className="ml-auto">
                                {module.concepts.length} 个概念
                              </Badge>
                            </div>
                            {expandedModules.has(module.module_id) && module.description && (
                              <p className="text-sm text-muted-foreground mt-2 ml-6">
                                {module.description}
                              </p>
                            )}
                          </div>

                          {expandedModules.has(module.module_id) && (
                            <div className="p-4 pt-0 space-y-2">
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
                          )}
                        </div>
                      ))}
                    </CardContent>
                  )}
                </Card>
              ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <Network className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">流程图视图</p>
              <p className="text-sm mt-2">此功能正在开发中</p>
              <Button variant="outline" className="mt-4" onClick={() => setViewMode('list' as ViewMode)}>
                返回列表视图
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
        taskId={taskIdFromUrl || activeTaskId || ''}
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
      <Badge variant="secondary" className="bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
        生成中 {completed}/{total}
      </Badge>
    );
  }

  if (completed === total) {
    return (
      <Badge variant="secondary" className="bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300">
        已完成
      </Badge>
    );
  }

  return (
    <Badge variant="secondary">
      {completed}/{total}
    </Badge>
  );
}
