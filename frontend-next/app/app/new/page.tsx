'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Clock,
  Target,
  BookOpen,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { generateRoadmapAsync, getUserProfile, type UserProfileData } from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest } from '@/types/generated/models';
import Link from 'next/link';
import { User } from 'lucide-react';
import { mapStepToPhase } from '@/types/custom/phases';

// 硬编码的用户 ID（TODO: 替换为真实用户认证）
const USER_ID = 'temp-user-001';

type Step = 'goal' | 'preferences' | 'generating' | 'preview';

interface FormData {
  learningGoal: string;
  currentLevel: 'beginner' | 'intermediate' | 'advanced';
  availableHours: number;
  motivation: string;
  careerBackground: string;
  contentPreferences: string[];
}

const contentOptions = [
  { id: 'visual', label: 'Visual', labelZh: '视觉类', icon: '🎬', desc: '视频教程、图解、演示' },
  { id: 'text', label: 'Text', labelZh: '文本类', icon: '📚', desc: '文档、文章、书籍' },
  { id: 'audio', label: 'Audio', labelZh: '音频类', icon: '🎧', desc: '播客、有声内容' },
  { id: 'hands_on', label: 'Hands-on', labelZh: '实操类', icon: '🛠️', desc: '互动练习、项目实战' },
];

const levelOptions = [
  { id: 'beginner', label: 'Beginner', description: 'New to this topic' },
  { id: 'intermediate', label: 'Intermediate', description: 'Some experience' },
  { id: 'advanced', label: 'Advanced', description: 'Looking to master' },
];

export default function NewRoadmapPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('goal');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState<string>('初始化...');
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const wsRef = useRef<TaskWebSocket | null>(null);
  const hasNavigatedRef = useRef(false); // Track if we've already navigated
  
  // Roadmap store (no longer needed for live generation tracking)
  
  // Profile state
  const [userProfile, setUserProfile] = useState<UserProfileData | null>(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [hasCompletedProfile, setHasCompletedProfile] = useState(false);
  
  const [formData, setFormData] = useState<FormData>({
    learningGoal: '',
    currentLevel: 'beginner',
    availableHours: 10,
    motivation: '',
    careerBackground: '',
    contentPreferences: ['visual', 'text'],
  });

  // Load user profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        setIsProfileLoading(true);
        const profile = await getUserProfile(USER_ID);
        setUserProfile(profile);
        
        // Check if profile is "complete" (has at least some meaningful data)
        const isComplete = !!(
          profile.industry ||
          profile.current_role ||
          (profile.tech_stack && profile.tech_stack.length > 0) ||
          (profile.learning_style && profile.learning_style.length > 0)
        );
        setHasCompletedProfile(isComplete);
        
        // Pre-fill form with profile data if available
        if (isComplete) {
          setFormData((prev) => ({
            ...prev,
            availableHours: profile.weekly_commitment_hours || 10,
            contentPreferences: profile.learning_style?.length > 0 
              ? profile.learning_style 
              : prev.contentPreferences,
          }));
        }
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setIsProfileLoading(false);
      }
    };

    loadProfile();
  }, []);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, []);

  const handleNext = () => {
    if (step === 'goal') {
      setStep('preferences');
    } else if (step === 'preferences') {
      handleGenerate();
    }
  };

  const handleBack = () => {
    if (step === 'preferences') {
      setStep('goal');
    }
  };

  const handleGenerate = async () => {
    setStep('generating');
    setIsGenerating(true);
    setGenerationProgress(0);
    setGenerationStatus('初始化...');
    setGenerationError(null);
    setTaskId(null);
    hasNavigatedRef.current = false; // Reset navigation flag

    // Use consistent user ID across the app
    // TODO: Replace with real user authentication
    const userId = USER_ID;
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Build API request - include user profile data if available
    const request: UserRequest = {
      user_id: userId,
      session_id: sessionId,
      preferences: {
        learning_goal: formData.learningGoal,
        available_hours_per_week: formData.availableHours,
        motivation: formData.motivation || '个人兴趣',
        current_level: formData.currentLevel,
        career_background: formData.careerBackground || '未指定',
        content_preference: formData.contentPreferences as any,
        // Include profile data if available
        ...(userProfile && hasCompletedProfile ? {
          industry: userProfile.industry,
          current_role: userProfile.current_role,
          tech_stack: userProfile.tech_stack,
          preferred_language: userProfile.primary_language,
        } : {}),
      },
    };

    try {
      // Step 1: Call non-streaming API to start generation task
      setGenerationStatus('正在提交生成请求...');
      setGenerationProgress(5);
      
      const response = await generateRoadmapAsync(request);
      const newTaskId = response.task_id;
      setTaskId(newTaskId);
      
      console.log('[Generate] Task created:', newTaskId);
      setGenerationStatus('任务已创建，正在连接实时更新...');
      setGenerationProgress(10);

      // Step 2: Connect WebSocket to receive real-time updates
      const ws = new TaskWebSocket(newTaskId, {
        onConnected: (event) => {
          console.log('[WS] Connected:', event.message);
          setGenerationStatus('已连接，等待生成进度...');
          
          // Request current status immediately after connection
          // This ensures we don't miss any early events
          ws.requestStatus();
        },

        onStatus: (event) => {
          console.log('[WS] Status:', event);
          
          // Early navigation if roadmap_id is already available in status
          if (event.roadmap_id && !hasNavigatedRef.current && event.status !== 'completed') {
            hasNavigatedRef.current = true;
            console.log('[Generate] Early navigation from status, roadmap_id:', event.roadmap_id);
            
            router.push(`/app/roadmap/${event.roadmap_id}`);
            return;
          }
          
          // Map status to progress
          if (event.status === 'completed' && event.roadmap_id) {
            setGenerationProgress(100);
            setGenerationStatus('路线图生成完成！');
            setIsGenerating(false);
            
            // Navigate to roadmap
            setTimeout(() => {
              router.push(`/app/roadmap/${event.roadmap_id}`);
            }, 1000);
            
            // Disconnect WebSocket
            ws.disconnect();
          } else if (event.status === 'failed') {
            setGenerationError('生成任务失败');
            setIsGenerating(false);
            ws.disconnect();
          } else if (event.status === 'human_review_pending') {
            setGenerationStatus('等待人工审核...');
            setGenerationProgress(50);
          } else if (event.status === 'processing') {
            // Update based on current step
            updateProgressFromStep(event.current_step);
          }
        },

        onProgress: (event) => {
          console.log('[WS] Progress:', event);
          // Use message from backend if available
          const message = event.message || undefined;
          updateProgressFromStep(event.step, undefined, message);
          
          // Extract additional info from data
          if (event.data) {
            if (event.data.stages_count) {
              setGenerationStatus(`${message || event.step} (${event.data.stages_count} 个阶段)`);
            }
            if (event.data.total_concepts) {
              setGenerationStatus(`${message} (${event.data.total_concepts} 个概念)`);
            }
            
            // EARLY NAVIGATION: When roadmap_id is available (curriculum_design complete)
            // Navigate to roadmap page immediately without waiting for content generation
            if (event.data.roadmap_id && !hasNavigatedRef.current) {
              hasNavigatedRef.current = true;
              const roadmapId = event.data.roadmap_id;
              
              console.log('[Generate] Early navigation triggered, roadmap_id:', roadmapId);
              
              // Navigate to roadmap page (it will detect active task automatically)
              router.push(`/app/roadmap/${roadmapId}`);
            }
          }
        },

        onCompleted: (event) => {
          console.log('[WS] Completed:', event);
          setGenerationProgress(100);
          
          // Show completion stats
          let statusMsg = '路线图生成完成！';
          if (event.tutorials_count !== undefined) {
            statusMsg = `生成完成！共 ${event.tutorials_count} 个教程`;
            if (event.failed_count && event.failed_count > 0) {
              statusMsg += `（${event.failed_count} 个失败）`;
            }
          }
          setGenerationStatus(statusMsg);
          setIsGenerating(false);
          
          // Navigate to roadmap
          if (event.roadmap_id) {
            setTimeout(() => {
              router.push(`/app/roadmap/${event.roadmap_id}`);
            }, 1500);
          }
          
          ws.disconnect();
        },

        onFailed: (event) => {
          console.log('[WS] Failed:', event);
          setGenerationError(event.error || event.error_message || '生成失败');
          setIsGenerating(false);
          ws.disconnect();
        },

        onHumanReview: (event) => {
          console.log('[WS] Human review required:', event);
          setGenerationStatus(`需要人工审核: ${event.roadmap_title}`);
          setGenerationProgress(50);
          // TODO: Handle human review flow - show review UI
        },

        // Concept-level events for detailed progress
        onConceptStart: (event) => {
          console.log('[WS] Concept start:', event);
          const { progress } = event;
          // Map concept progress to overall progress (60-95%)
          const overallProgress = 60 + (progress.percentage * 0.35);
          setGenerationProgress(overallProgress);
          setGenerationStatus(`生成内容: ${event.concept_name} (${progress.current}/${progress.total})`);
        },

        onConceptComplete: (event) => {
          console.log('[WS] Concept complete:', event);
          // Just log, progress will be updated by batch_complete
        },

        onConceptFailed: (event) => {
          console.log('[WS] Concept failed:', event);
          // Don't stop generation, just log warning
        },

        onBatchStart: (event) => {
          console.log('[WS] Batch start:', event);
          setGenerationStatus(`处理批次 ${event.batch_index}/${event.total_batches}...`);
        },

        onBatchComplete: (event) => {
          console.log('[WS] Batch complete:', event);
          const { progress } = event;
          // Map batch progress to overall progress (60-95%)
          const overallProgress = 60 + (progress.percentage * 0.35);
          setGenerationProgress(overallProgress);
          setGenerationStatus(`内容生成: ${progress.completed}/${progress.total} 完成`);
        },

        onError: (event) => {
          console.error('[WS] Error:', event);
          setGenerationError(event.message);
          setIsGenerating(false);
        },

        onClosing: (event) => {
          console.log('[WS] Closing:', event.reason, event.message);
        },
      });

      wsRef.current = ws;
      ws.connect(true); // Include history to get current status

    } catch (error) {
      console.error('[Generation Error]', error);
      setGenerationError(error instanceof Error ? error.message : '启动生成失败');
      setIsGenerating(false);
    }
  };

  // Helper function to update progress based on step name
  const updateProgressFromStep = (step: string | null, progress?: number, message?: string) => {
    if (!step) return;

    const stepProgress: Record<string, { progress: number; status: string }> = {
      'queued': { progress: 10, status: '任务已排队...' },
      'intent_analysis': { progress: 20, status: '分析学习目标...' },
      'curriculum_design': { progress: 40, status: '设计课程结构...' },
      'framework_generation': { progress: 50, status: '生成路线图框架...' },
      'tutorial_generation': { progress: 60, status: '生成教程内容...' },
      'resource_recommendation': { progress: 75, status: '推荐学习资源...' },
      'quiz_generation': { progress: 85, status: '生成测验题目...' },
      'finalizing': { progress: 95, status: '完成处理...' },
      'completed': { progress: 100, status: '生成完成！' },
    };

    const stepInfo = stepProgress[step];
    if (stepInfo) {
      setGenerationProgress(progress ?? stepInfo.progress);
      setGenerationStatus(message || stepInfo.status);
    } else {
      // Unknown step, just update message if provided
      if (message) {
        setGenerationStatus(message);
      }
      if (progress !== undefined) {
        setGenerationProgress(progress);
      }
    }
  };

  const toggleContentPreference = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      contentPreferences: prev.contentPreferences.includes(id)
        ? prev.contentPreferences.filter((p) => p !== id)
        : [...prev.contentPreferences, id],
    }));
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-sage-100 rounded-full text-sage-800 text-sm font-medium mb-4">
          <Sparkles className="w-4 h-4" />
          AI-Powered Generation
        </div>
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Create Your Learning Roadmap
        </h1>
        <p className="text-lg text-muted-foreground">
          Tell us what you want to learn and we&apos;ll craft a personalized curriculum.
        </p>
      </div>

      {/* Profile Guidance Card */}
      {step !== 'generating' && !isProfileLoading && !hasCompletedProfile && (
        <Card className="mb-6 border-sage-200 bg-sage-50/50">
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-sage-100 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-sage-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">
                  完善你的学习画像
                </p>
                <p className="text-xs text-muted-foreground">
                  填写个人画像可以帮助我们生成更加个性化的学习路线图
                </p>
              </div>
              <Link href="/app/profile">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <User className="w-4 h-4" />
                  填写画像
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step Progress */}
      {step !== 'generating' && (
        <div className="flex items-center justify-center gap-2 mb-8">
          {['goal', 'preferences'].map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === s
                    ? 'bg-sage-600 text-white'
                    : i < ['goal', 'preferences'].indexOf(step)
                    ? 'bg-sage-200 text-sage-800'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {i + 1}
              </div>
              {i < 1 && <div className="w-12 h-0.5 bg-muted mx-2" />}
            </div>
          ))}
        </div>
      )}

      {/* Step Content */}
      {step === 'goal' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-sage-600" />
              What do you want to learn?
            </CardTitle>
            <CardDescription>
              Describe your learning goal in detail. The more specific, the better.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Learning Goal</label>
              <textarea
                value={formData.learningGoal}
                onChange={(e) =>
                  setFormData({ ...formData, learningGoal: e.target.value })
                }
                placeholder="e.g., I want to become a full-stack web developer with React and Node.js"
                className="w-full min-h-[120px] p-4 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Current Level</label>
              <div className="grid grid-cols-3 gap-3">
                {levelOptions.map((level) => (
                  <button
                    key={level.id}
                    onClick={() =>
                      setFormData({
                        ...formData,
                        currentLevel: level.id as FormData['currentLevel'],
                      })
                    }
                    className={`p-4 rounded-lg border text-left transition-colors ${
                      formData.currentLevel === level.id
                        ? 'border-sage-600 bg-sage-50'
                        : 'border-border hover:border-sage-300'
                    }`}
                  >
                    <div className="font-medium">{level.label}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {level.description}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleNext}
                disabled={!formData.learningGoal.trim()}
                variant="sage"
                className="gap-2"
              >
                Continue <ArrowRight size={16} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 'preferences' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-sage-600" />
              Learning Preferences
            </CardTitle>
            <CardDescription>
              Help us customize your learning experience.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                <Clock size={14} className="inline mr-1" />
                Hours per week you can dedicate
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="40"
                  value={formData.availableHours}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      availableHours: parseInt(e.target.value),
                    })
                  }
                  className="flex-1 h-2 bg-muted rounded-lg appearance-none cursor-pointer"
                />
                <span className="w-16 text-center font-medium">
                  {formData.availableHours}h/week
                </span>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium">
                Preferred Content Types
              </label>
                <button
                  type="button"
                  onClick={() => {
                    if (formData.contentPreferences.length === contentOptions.length) {
                      setFormData({ ...formData, contentPreferences: [] });
                    } else {
                      setFormData({ ...formData, contentPreferences: contentOptions.map(o => o.id) });
                    }
                  }}
                  className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
                >
                  {formData.contentPreferences.length === contentOptions.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {contentOptions.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => toggleContentPreference(option.id)}
                    className={`p-4 rounded-lg border text-left transition-colors ${
                      formData.contentPreferences.includes(option.id)
                        ? 'border-sage-600 bg-sage-50'
                        : 'border-border hover:border-sage-300'
                    }`}
                  >
                    <div className="flex items-center mb-1">
                    <span className="text-xl mr-2">{option.icon}</span>
                      <span className="font-medium">{option.labelZh}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">{option.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Why do you want to learn this? (optional)
              </label>
              <textarea
                value={formData.motivation}
                onChange={(e) =>
                  setFormData({ ...formData, motivation: e.target.value })
                }
                placeholder="e.g., Career change, side project, personal interest..."
                className="w-full min-h-[80px] p-4 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div className="flex justify-between">
              <Button onClick={handleBack} variant="outline" className="gap-2">
                <ArrowLeft size={16} /> Back
              </Button>
              <Button onClick={handleNext} variant="sage" className="gap-2">
                Generate Roadmap <Sparkles size={16} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 'generating' && (
        <Card>
          <CardContent className="py-16 text-center">
            {generationError ? (
              <>
                <div className="w-20 h-20 bg-red-100 rounded-full mx-auto flex items-center justify-center mb-6">
                  <AlertCircle className="w-10 h-10 text-red-600" />
                </div>
                <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
                  生成失败
                </h2>
                <p className="text-red-600 mb-8">
                  {generationError}
                </p>
                <Button
                  onClick={() => {
                    setStep('preferences');
                    setGenerationError(null);
                    setGenerationProgress(0);
                  }}
                  variant="outline"
                  className="gap-2"
                >
                  <ArrowLeft size={16} /> 返回修改
                </Button>
              </>
            ) : generationProgress >= 100 ? (
              <>
                <div className="w-20 h-20 bg-green-100 rounded-full mx-auto flex items-center justify-center mb-6">
                  <CheckCircle2 className="w-10 h-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
                  路线图生成完成！
                </h2>
                <p className="text-muted-foreground mb-8">
                  正在跳转到您的学习路线图...
                </p>
              </>
            ) : (
              <>
            <div className="w-20 h-20 bg-sage-100 rounded-full mx-auto flex items-center justify-center mb-6">
              <Loader2 className="w-10 h-10 text-sage-600 animate-spin" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
                  正在生成您的学习路线图
            </h2>
            <p className="text-muted-foreground mb-8">
                  AI 智能体正在协同工作，为您打造个性化的学习课程...
            </p>
            <div className="max-w-md mx-auto">
              <Progress value={Math.min(generationProgress, 100)} className="h-2" />
              <p className="text-sm text-muted-foreground mt-2">
                    {generationStatus}
              </p>
            </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

