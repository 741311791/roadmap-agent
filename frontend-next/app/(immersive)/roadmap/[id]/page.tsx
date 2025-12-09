'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { 
  ResizablePanelGroup, 
  ResizablePanel, 
  ResizableHandle 
} from '@/components/ui/resizable';
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
  getUserProfile
} from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';
import type { RoadmapFramework, Concept, Stage, Module, LearningPreferences } from '@/types/generated/models';
import { Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

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

  // WebSocket ref
  const wsRef = useRef<TaskWebSocket | null>(null);

  // 1. Sync Roadmap Data to Store
  useEffect(() => {
    if (roadmapData) {
      setRoadmap(roadmapData as RoadmapFramework);
    }
  }, [roadmapData, setRoadmap]);

  // 2. Load User Preferences for Retry Functionality
  useEffect(() => {
    const loadUserPreferences = async () => {
      const userId = getUserId();
      if (!userId) return;
      
      try {
        const profile = await getUserProfile(userId);
        // 构建 LearningPreferences 对象
        setUserPreferences({
          learning_goal: roadmapData?.learning_goal || '',
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

    const ws = new TaskWebSocket(activeTask.taskId, {
      onConceptStart: (event) => {
        if (event.concept_id) {
          updateConceptStatus(event.concept_id, { tutorial_status: 'generating' });
        }
      },
      onConceptComplete: (event) => {
        if (event.concept_id) {
          updateConceptStatus(event.concept_id, { tutorial_status: 'completed' });
        }
      },
      onConceptFailed: (event) => {
        if (event.concept_id) {
          updateConceptStatus(event.concept_id, { tutorial_status: 'failed' });
        }
      },
      onBatchComplete: () => {
        refetchRoadmap();
      },
      onCompleted: () => {
        refetchRoadmap();
        setActiveTask(null);
      }
    });

    wsRef.current = ws;
    ws.connect(false);

    return () => {
      ws.disconnect();
    };
  }, [activeTask?.taskId, updateConceptStatus, refetchRoadmap]);

  // 5. Fetch Tutorial Content when Concept Selected
  useEffect(() => {
    if (!selectedConceptId) {
      setTutorialContent(undefined);
      return;
    }

    const loadContent = async () => {
      setTutorialContent(undefined);
      try {
        const meta = await getLatestTutorial(roadmapId, selectedConceptId);
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
    };

    loadContent();
  }, [selectedConceptId, roadmapId]);

  // 6. Poll Roadmap Data when Content is Generating
  useEffect(() => {
    if (!currentRoadmap) return;

    // 检查是否有任何概念正在生成内容
    const hasGeneratingContent = currentRoadmap.stages.some(stage =>
      stage.modules.some(module =>
        module.concepts.some(concept =>
          concept.content_status === 'generating' ||
          concept.resources_status === 'generating' ||
          concept.quiz_status === 'generating'
        )
      )
    );

    if (!hasGeneratingContent) return;

    console.log('[RoadmapDetail] 检测到生成中的内容，启动定时刷新');

    // 每 5 秒刷新一次路线图数据
    const pollInterval = setInterval(() => {
      console.log('[RoadmapDetail] 定时刷新路线图数据');
      refetchRoadmap();
    }, 5000);

    return () => {
      console.log('[RoadmapDetail] 清理定时刷新');
      clearInterval(pollInterval);
    };
  }, [currentRoadmap, refetchRoadmap]);

  // Helper: Find concept object by ID
  const getActiveConcept = useCallback((): Concept | null => {
    if (!currentRoadmap || !selectedConceptId) return null;
    
    for (const stage of currentRoadmap.stages) {
      for (const module of stage.modules) {
        const concept = module.concepts.find(c => c.concept_id === selectedConceptId);
        if (concept) return concept;
      }
    }
    return null;
  }, [currentRoadmap, selectedConceptId]);

  // Helper: Calculate overall progress
  const calculateProgress = useCallback(() => {
    if (!currentRoadmap) return 0;
    
    const allConcepts = currentRoadmap.stages.flatMap(
      (s: Stage) => s.modules.flatMap((m: Module) => m.concepts)
    );
    
    if (allConcepts.length === 0) return 0;
    
    const completed = allConcepts.filter(
      (c: Concept) => c.content_status === 'completed'
    ).length;
    
    return (completed / allConcepts.length) * 100;
  }, [currentRoadmap]);

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
  if (roadmapError || !currentRoadmap) {
    return (
      <div className="h-screen w-full bg-background flex items-center justify-center text-muted-foreground gap-3">
        <AlertCircle className="w-5 h-5 text-destructive" />
        <span className="font-serif text-lg">Failed to load roadmap.</span>
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
              onSelectConcept={selectConcept}
              generationProgress={calculateProgress()}
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
              onRetrySuccess={() => {
                // 重试成功后，重新加载路线图数据和教程内容
                refetchRoadmap();
                if (selectedConceptId) {
                  setTutorialContent(undefined); // 清空内容，触发重新加载
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
