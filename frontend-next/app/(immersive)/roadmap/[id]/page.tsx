'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { 
  ResizablePanelGroup, 
  ResizablePanel, 
  ResizableHandle 
} from '@/components/ui/resizable';
import { KnowledgeRail } from '@/components/roadmap/immersive/knowledge-rail';
import { LearningStage } from '@/components/roadmap/immersive/learning-stage';
import { MentorSidecar } from '@/components/roadmap/immersive/mentor-sidecar';
import { GenerationProgressStepper, GenerationLog } from '@/components/roadmap/generation-progress-stepper';
import { useRoadmap } from '@/lib/hooks/api/use-roadmap';
import { useRoadmapStore, GenerationPhase } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
import { 
  getRoadmapActiveTask, 
  getLatestTutorial, 
  downloadTutorialContent,
  getUserProfile
} from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';
import type { RoadmapFramework, Concept, Stage, Module, LearningPreferences } from '@/types/generated/models';
import { Loader2, AlertCircle, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { isConceptIdValid, findConceptById, calculateRoadmapProgress } from '@/lib/utils/roadmap-helpers';

/**
 * RoadmapDetailPage - 沉浸式路线图详情页
 * 
 * 布局:
 * - 左侧: KnowledgeRail (知识导航栏)
 * - 中间: LearningStage (学习舞台)
 * - 右侧: MentorSidecar (AI 导师侧边栏)
 */
export default function RoadmapDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const roadmapId = params.id as string;

  // Auth Store
  const { getUserId } = useAuthStore();

  // Global Store
  const { 
    currentRoadmap, 
    setRoadmap, 
    selectedConceptId, 
    selectConcept,
    updateConceptStatus
  } = useRoadmapStore();

  // Data Fetching
  const { 
    data: roadmapData, 
    isLoading: roadmapLoading, 
    error: roadmapError,
    refetch: refetchRoadmap
  } = useRoadmap(roadmapId);

  // Local State
  const [tutorialContent, setTutorialContent] = useState<string | undefined>(undefined);
  const [activeTask, setActiveTask] = useState<{ taskId: string; status: string } | null>(null);
  const [userPreferences, setUserPreferences] = useState<LearningPreferences | undefined>(undefined);
  
  // Generation progress state
  const [generationPhase, setGenerationPhase] = useState<GenerationPhase>('idle');
  const [generationProgress, setGenerationProgress] = useState(0);
  const [currentGenerationStep, setCurrentGenerationStep] = useState<string | null>(null);
  const [generationLogs, setGenerationLogs] = useState<GenerationLog[]>([]);

  // WebSocket ref
  const wsRef = useRef<TaskWebSocket | null>(null);

  // 1. Sync Roadmap Data to Store
  useEffect(() => {
    if (roadmapData) {
      setRoadmap(roadmapData as RoadmapFramework);
    }
  }, [roadmapData, setRoadmap]);

  // 1.5. URL → State 单向同步：从 URL 参数中读取 conceptId 并自动选中
  // 这是唯一的同步方向，避免循环
  useEffect(() => {
    if (!roadmapData) return;
    
    const conceptIdFromUrl = searchParams.get('concept');
    
    // 只在 URL 参数与当前 state 不一致时才更新
    if (conceptIdFromUrl !== selectedConceptId) {
      if (conceptIdFromUrl) {
        // URL 中有 concept 参数，验证并选中
        if (isConceptIdValid(roadmapData as RoadmapFramework, conceptIdFromUrl)) {
          console.log('[RoadmapDetail] Syncing concept from URL:', conceptIdFromUrl);
          selectConcept(conceptIdFromUrl);
        } else {
          console.warn('[RoadmapDetail] Invalid concept ID in URL:', conceptIdFromUrl);
        }
      } else {
        // URL 中没有 concept 参数，清空选中状态
        console.log('[RoadmapDetail] Clearing concept selection (no URL param)');
        selectConcept(null);
      }
    }
  }, [roadmapData, searchParams, selectedConceptId, selectConcept]);

  // 1.6. Concept 选择处理器：直接更新 URL（而不是直接更新 state）
  // URL 变化会通过上面的 effect 自动同步到 state，避免循环
  const handleConceptSelect = useCallback((conceptId: string | null) => {
    const newUrl = conceptId
      ? `/roadmap/${roadmapId}?concept=${encodeURIComponent(conceptId)}`
      : `/roadmap/${roadmapId}`;
    
    console.log('[RoadmapDetail] Navigating to concept:', conceptId);
    router.push(newUrl, { scroll: false });
  }, [roadmapId, router]);

  // 2. Load User Preferences for Retry Functionality
  useEffect(() => {
    const loadUserPreferences = async () => {
      const userId = getUserId();
      if (!userId) return;
      
      try {
        const profile = await getUserProfile(userId);
        // 构建 LearningPreferences 对象
        setUserPreferences({
          learning_goal: roadmapData?.title || 'Learning',
          available_hours_per_week: profile.weekly_commitment_hours || 10,
          current_level: 'intermediate', // 默认值
          career_background: profile.current_role || 'Not specified',
          motivation: 'Continue learning',
          content_preference: (profile.learning_style || ['text', 'visual']) as any,
          preferred_language: profile.primary_language || 'zh-CN',
        });
      } catch (error) {
        console.error('[RoadmapDetail] Failed to load user preferences:', error);
      }
    };
    
    if (roadmapData) {
      loadUserPreferences();
    }
  }, [roadmapData, getUserId]);

  // 3. Check for Active Task on Mount
  useEffect(() => {
    if (!roadmapData) return;
    
    const checkActiveTask = async () => {
      try {
        const task = await getRoadmapActiveTask(roadmapId);
        if (task.has_active_task && task.task_id) {
          setActiveTask({ 
            taskId: task.task_id, 
            status: task.status ?? 'pending' 
          });
        }
      } catch (e) {
        console.error('Failed to check active task:', e);
      }
    };
    
    checkActiveTask();
  }, [roadmapId, roadmapData]);

  // 4. Setup WebSocket for Real-time Updates
  useEffect(() => {
    if (!activeTask?.taskId) return;

    const addLog = (phase: string, message: string, level: 'info' | 'success' | 'warning' | 'error' = 'info') => {
      setGenerationLogs(prev => [
        ...prev,
        {
          timestamp: new Date().toISOString(),
          phase,
          message,
          level,
        },
      ]);
    };

    const ws = new TaskWebSocket(activeTask.taskId, {
      onStatus: (event) => {
        console.log('[WS] Status:', event);
        // 更新当前步骤
        if (event.current_step) {
          setCurrentGenerationStep(event.current_step);
        }
      },
      onProgress: (event) => {
        console.log('[WS] Progress:', event);
        // 更新阶段
        const step = event.step;
        if (step === 'intent_analysis') {
          setGenerationPhase('intent_analysis');
          setGenerationProgress(10);
        } else if (step === 'curriculum_design') {
          setGenerationPhase('curriculum_design');
          setGenerationProgress(30);
        } else if (step === 'structure_validation') {
          setGenerationPhase('structure_validation');
          setGenerationProgress(50);
        } else if (step === 'human_review') {
          setGenerationPhase('human_review');
          setGenerationProgress(60);
        } else if (step === 'content_generation') {
          setGenerationPhase('content_generation');
          setGenerationProgress(70);
        }
        
        // 添加日志
        if (event.message) {
          addLog(step, event.message, 'info');
        }
        
        // 更新当前步骤描述
        if (event.message) {
          setCurrentGenerationStep(event.message);
        }
      },
      onConceptStart: (event) => {
        console.log('[WS] Concept start:', event);
        addLog(
          'content_generation',
          `Generating ${event.content_type} for "${event.concept_name}"`,
          'info'
        );
        
        if (event.concept_id) {
          const contentType = event.content_type;
          const statusKey = contentType === 'resources' 
            ? 'resources_status' 
            : contentType === 'quiz' 
              ? 'quiz_status' 
              : 'content_status';
          updateConceptStatus(event.concept_id, { [statusKey]: 'generating' });
        }
        
        // 更新进度百分比
        if (event.progress) {
          const progress = 70 + (event.progress.percentage * 0.3); // 70-100%
          setGenerationProgress(progress);
        }
      },
      onConceptComplete: (event) => {
        console.log('[WS] Concept complete:', event);
        addLog(
          'content_generation',
          `Completed ${event.content_type} for "${event.concept_name}"`,
          'success'
        );
        
        if (event.concept_id) {
          const contentType = event.content_type;
          const statusKey = contentType === 'resources' 
            ? 'resources_status' 
            : contentType === 'quiz' 
              ? 'quiz_status' 
              : 'content_status';
          updateConceptStatus(event.concept_id, { [statusKey]: 'completed' });
          refetchRoadmap();
        }
      },
      onConceptFailed: (event) => {
        console.log('[WS] Concept failed:', event);
        addLog(
          'content_generation',
          `Failed to generate ${event.content_type} for "${event.concept_name}": ${event.error}`,
          'error'
        );
        
        if (event.concept_id) {
          const contentType = event.content_type;
          const statusKey = contentType === 'resources' 
            ? 'resources_status' 
            : contentType === 'quiz' 
              ? 'quiz_status' 
              : 'content_status';
          updateConceptStatus(event.concept_id, { [statusKey]: 'failed' });
        }
      },
      onBatchStart: (event) => {
        console.log('[WS] Batch start:', event);
        addLog(
          'content_generation',
          `Starting batch ${event.batch_index + 1}/${event.total_batches} (${event.batch_size} concepts)`,
          'info'
        );
      },
      onBatchComplete: (event) => {
        console.log('[WS] Batch complete:', event);
        addLog(
          'content_generation',
          `Batch ${event.batch_index + 1}/${event.total_batches} completed (${event.progress.completed}/${event.progress.total})`,
          'success'
        );
        refetchRoadmap();
      },
      onHumanReview: (event) => {
        console.log('[WS] Human review required:', event);
        setGenerationPhase('human_review');
        addLog(
          'human_review',
          `Roadmap "${event.roadmap_title}" is ready for review`,
          'info'
        );
      },
      onCompleted: (event) => {
        console.log('[WS] Task completed:', event);
        setGenerationPhase('completed');
        setGenerationProgress(100);
        addLog(
          'completed',
          `Generation completed successfully!`,
          'success'
        );
        refetchRoadmap();
        setActiveTask(null);
      },
      onFailed: (event) => {
        console.log('[WS] Task failed:', event);
        setGenerationPhase('failed');
        addLog(
          'failed',
          `Generation failed: ${event.error || event.error_message || 'Unknown error'}`,
          'error'
        );
      }
    });

    wsRef.current = ws;
    ws.connect(true); // 包含历史消息

    return () => {
      ws.disconnect();
    };
  }, [activeTask?.taskId, updateConceptStatus, refetchRoadmap]);

  // 5. Fetch Tutorial Content when Concept Selected
  // 提取为独立函数，以便在重试成功后手动触发
  const loadTutorialContent = useCallback(async (conceptId: string) => {
    setTutorialContent(undefined); // 先清空显示加载状态
    try {
      const meta = await getLatestTutorial(roadmapId, conceptId);
      if (meta?.content_url) {
        const text = await downloadTutorialContent(meta.content_url);
        setTutorialContent(text);
      } else {
        setTutorialContent('# No content available yet\n\nThis concept is still being generated or is pending.');
      }
    } catch (err) {
      console.error('Failed to load tutorial content:', err);
      setTutorialContent('# Error loading content\n\nPlease try again later.');
    }
  }, [roadmapId]);

  useEffect(() => {
    if (!selectedConceptId) {
      setTutorialContent(undefined);
      return;
    }

    loadTutorialContent(selectedConceptId);
  }, [selectedConceptId, loadTutorialContent]);

  // Helper: Find concept object by ID
  const getActiveConcept = useCallback((): Concept | null => {
    return findConceptById(currentRoadmap, selectedConceptId || '');
  }, [currentRoadmap, selectedConceptId]);

  // Helper: Calculate overall progress
  const overallProgress = calculateRoadmapProgress(currentRoadmap);

  // Loading State
  if (roadmapLoading) {
    return (
      <div className="h-screen w-full bg-background flex items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="animate-spin w-5 h-5 text-sage-600" />
        <span className="font-serif text-lg">Loading...</span>
      </div>
    );
  }

  // Error State
  if (roadmapError) {
    return (
      <div className="h-screen w-full bg-background flex items-center justify-center text-muted-foreground gap-3">
        <AlertCircle className="w-5 h-5 text-destructive" />
        <span className="font-serif text-lg">Failed to load roadmap.</span>
      </div>
    );
  }

  // 如果有活跃任务且任务状态不是 completed 或 partial_failure，显示生成进度页面
  const isGenerating = activeTask && 
    activeTask.status !== 'completed' && 
    activeTask.status !== 'partial_failure';

  if (isGenerating) {
    return (
      <div className="min-h-screen w-full bg-background text-foreground">
        {/* 导航栏 */}
        <div className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="max-w-4xl mx-auto px-6 py-4">
            <div className="flex items-center gap-4">
              <Link href="/home">
                <Button variant="ghost" size="sm" className="gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  Back to Home
                </Button>
              </Link>
              <div className="h-4 w-px bg-border" />
              <div>
                <h1 className="text-lg font-serif font-semibold">
                  {currentRoadmap?.title || 'Generating Roadmap'}
                </h1>
                <p className="text-sm text-muted-foreground">
                  Your personalized learning roadmap is being generated
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 生成进度内容 */}
        <div className="max-w-4xl mx-auto px-6 py-8">
          <GenerationProgressStepper
            phase={generationPhase}
            progress={generationProgress}
            currentStep={currentGenerationStep}
            logs={generationLogs}
          />
        </div>
      </div>
    );
  }

  // 如果路线图还没加载完成
  if (!currentRoadmap) {
    return (
      <div className="h-screen w-full bg-background flex items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="animate-spin w-5 h-5 text-sage-600" />
        <span className="font-serif text-lg">Loading roadmap...</span>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-background text-foreground overflow-hidden relative font-sans">
      {/* Subtle Background Pattern */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Soft Sage Gradient - 左上角 */}
        <div 
          className="absolute -top-[10%] -left-[5%] w-[40%] h-[40%] rounded-full blur-[100px] opacity-30"
          style={{ backgroundColor: 'hsl(140 20% 85%)' }}
        />
        {/* Warm Cream Accent - 右下角 */}
        <div 
          className="absolute bottom-[-5%] right-[-5%] w-[35%] h-[35%] rounded-full blur-[80px] opacity-20"
          style={{ backgroundColor: 'hsl(40 30% 90%)' }}
        />
        {/* Noise Texture */}
        <div className="absolute inset-0 bg-noise opacity-[0.015]" />
      </div>

      {/* Main Layout */}
      <div className="relative z-10 h-full">
        <ResizablePanelGroup direction="horizontal">
          {/* LEFT: Knowledge Rail */}
          <ResizablePanel defaultSize={20} minSize={15} maxSize={30} className="min-w-[240px]">
            <KnowledgeRail
              roadmap={currentRoadmap}
              activeConceptId={selectedConceptId}
              onSelectConcept={handleConceptSelect}
              generationProgress={overallProgress}
            />
          </ResizablePanel>

          <ResizableHandle 
            withHandle 
            className={cn(
              "w-px bg-border",
              "hover:bg-sage-300 transition-colors duration-200",
              "data-[resize-handle-active]:bg-sage-400"
            )} 
          />

          {/* CENTER: Learning Stage */}
          <ResizablePanel defaultSize={55} className="min-w-[400px]">
            <LearningStage
              concept={getActiveConcept()}
              tutorialContent={tutorialContent}
              roadmapId={roadmapId}
              userPreferences={userPreferences}
              onRetrySuccess={async () => {
                // 重试成功后，重新加载路线图数据和教程内容
                // 注意：需要等待路线图数据更新完成后再加载教程内容
                await refetchRoadmap();
                if (selectedConceptId) {
                  // 手动触发教程内容重新加载
                  loadTutorialContent(selectedConceptId);
                }
              }}
            />
          </ResizablePanel>

          <ResizableHandle 
            withHandle 
            className={cn(
              "w-px bg-border",
              "hover:bg-sage-300 transition-colors duration-200",
              "data-[resize-handle-active]:bg-sage-400"
            )} 
          />

          {/* RIGHT: Mentor Sidecar */}
          <ResizablePanel defaultSize={25} minSize={20} maxSize={35} className="min-w-[300px]">
            <MentorSidecar conceptContext={getActiveConcept()?.name} />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
