'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { 
  ResizablePanelGroup, 
  ResizablePanel, 
  ResizableHandle 
} from '@/components/ui/resizable';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { KnowledgeRail } from '@/components/roadmap/immersive/knowledge-rail';
import { LearningStage } from '@/components/roadmap/immersive/learning-stage';
import { MentorSidecar } from '@/components/roadmap/immersive/mentor-sidecar';
import { useRoadmap } from '@/lib/hooks/api/use-roadmap';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
import { 
  getRoadmapActiveTask, 
  getLatestTutorial, 
  downloadTutorialContent,
  getUserProfile,
  getRoadmapProgress
} from '@/lib/api/endpoints';
import type { RoadmapFramework, Concept, Stage, Module, LearningPreferences } from '@/types/generated/models';
import { Loader2, AlertCircle, ArrowLeft, Menu } from 'lucide-react';
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
    updateConceptStatus,
    setConceptProgressMap
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
  const [activeTask, setActiveTask] = useState<{ taskId: string; status: string; taskType?: string } | null>(null);
  const [userPreferences, setUserPreferences] = useState<LearningPreferences | undefined>(undefined);

  // UI State - 折叠状态和抽屉状态
  const [isMentorCollapsed, setIsMentorCollapsed] = useState(false);
  const [isKnowledgeRailOpen, setIsKnowledgeRailOpen] = useState(false);

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

  // 2.5. Load Learning Progress
  useEffect(() => {
    if (!roadmapData || !roadmapId) return;
    
    const loadProgress = async () => {
      try {
        const progressList = await getRoadmapProgress(roadmapId);
        const progressMap: Record<string, boolean> = {};
        progressList.forEach(p => {
          progressMap[p.concept_id] = p.is_completed;
        });
        setConceptProgressMap(progressMap);
      } catch (error) {
        console.error('[RoadmapDetail] Failed to load progress:', error);
      }
    };
    
    loadProgress();
  }, [roadmapData, roadmapId, setConceptProgressMap]);

  // 3. Check for Active Task on Mount
  useEffect(() => {
    if (!roadmapData) return;
    
    const checkActiveTask = async () => {
      try {
        const task = await getRoadmapActiveTask(roadmapId);
        if (task.has_active_task && task.task_id) {
          setActiveTask({ 
            taskId: task.task_id, 
            status: task.status ?? 'pending',
            taskType: task.task_type ?? undefined
          });
        }
      } catch (e) {
        console.error('Failed to check active task:', e);
      }
    };
    
    checkActiveTask();
  }, [roadmapId, roadmapData]);


  // 5. Fetch Tutorial Content when Concept Selected
  // 提取为独立函数，以便在重试成功后手动触发
  const loadTutorialContent = useCallback(async (conceptId: string) => {
    setTutorialContent(undefined); // 先清空显示加载状态
    try {
      const meta = await getLatestTutorial(roadmapId, conceptId);
      if (meta && meta.content_status === 'completed') {
        // 通过后端代理下载内容（解决 CORS 问题）
        const text = await downloadTutorialContent(roadmapId, conceptId);
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

  // 6. 重定向逻辑：只有初始路线图生成任务才重定向到任务详情页
  // 单内容重试任务（retry_tutorial/retry_resources/retry_quiz）留在当前页面实时更新
  // 必须放在所有 early return 之前，遵守 Hooks 规则
  useEffect(() => {
    const isGenerating = activeTask && 
      activeTask.status !== 'completed' && 
      activeTask.status !== 'partial_failure';

    // 只有初始路线图生成任务（task_type === 'creation'）才触发重定向
    // 单内容重试任务不触发重定向，留在当前页面实时更新
    const isInitialGeneration = activeTask?.taskType === 'creation' || !activeTask?.taskType;

    if (isGenerating && activeTask?.taskId && isInitialGeneration) {
      console.log('[RoadmapDetail] Initial roadmap generation task is still processing, redirecting to task detail page');
      router.push(`/tasks/${activeTask.taskId}`);
    } else if (isGenerating && activeTask?.taskId && !isInitialGeneration) {
      console.log('[RoadmapDetail] Content retry task is processing, staying on current page for real-time updates');
    }
  }, [activeTask, router]);

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

      {/* Mobile Menu Button - 仅在小屏幕显示 */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <Sheet open={isKnowledgeRailOpen} onOpenChange={setIsKnowledgeRailOpen}>
          <SheetTrigger asChild>
            <Button 
              variant="outline" 
              size="icon"
              className="bg-background/95 backdrop-blur-sm shadow-lg border-sage-200 hover:bg-sage-50"
            >
              <Menu className="w-5 h-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-[280px]">
            <KnowledgeRail
              roadmap={currentRoadmap}
              activeConceptId={selectedConceptId}
              onSelectConcept={(id) => {
                handleConceptSelect(id);
                setIsKnowledgeRailOpen(false); // 选择后关闭抽屉
              }}
              generationProgress={overallProgress}
            />
          </SheetContent>
        </Sheet>
      </div>

      {/* Main Layout */}
      <div className="relative z-10 h-full">
        <ResizablePanelGroup direction="horizontal">
          {/* LEFT: Knowledge Rail - 在大屏幕显示 */}
          <ResizablePanel 
            defaultSize={20} 
            minSize={15} 
            maxSize={30} 
            className="min-w-[240px] hidden lg:block"
          >
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
              "w-px bg-border hidden lg:block",
              "hover:bg-sage-300 transition-colors duration-200",
              "data-[resize-handle-active]:bg-sage-400"
            )} 
          />

          {/* CENTER: Learning Stage */}
          <ResizablePanel defaultSize={55} className="min-w-[320px]">
            <LearningStage
              concept={getActiveConcept()}
              tutorialContent={tutorialContent}
              roadmapId={roadmapId}
              userPreferences={userPreferences}
              onRetrySuccess={async () => {
                // WebSocket已经通过updateConceptStatus更新了store中的状态为completed
                // 现在可以安全地refetch以获取最新的content_url等数据
                await refetchRoadmap();
                // 重新加载教程内容
                if (selectedConceptId) {
                  loadTutorialContent(selectedConceptId);
                }
              }}
            />
          </ResizablePanel>

          <ResizableHandle 
            withHandle 
            className={cn(
              "w-px bg-border hidden md:block",
              "hover:bg-sage-300 transition-colors duration-200",
              "data-[resize-handle-active]:bg-sage-400"
            )} 
          />

          {/* RIGHT: Mentor Sidecar - 在中等及以上屏幕显示 */}
          <ResizablePanel 
            defaultSize={isMentorCollapsed ? 3 : 25} 
            minSize={isMentorCollapsed ? 3 : 20} 
            maxSize={isMentorCollapsed ? 3 : 35} 
            className={cn(
              isMentorCollapsed ? "min-w-[48px]" : "min-w-[300px]",
              "hidden md:block"
            )}
          >
            <MentorSidecar 
              conceptContext={getActiveConcept()?.name}
              roadmapId={roadmapId}
              conceptId={selectedConceptId || undefined}
              isCollapsed={isMentorCollapsed}
              onToggleCollapse={() => setIsMentorCollapsed(!isMentorCollapsed)}
            />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
