'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
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
  User,
  Eye,
  FileText,
  Headphones,
  Wrench,
} from 'lucide-react';
import { getUserProfile, getRoadmapStatus, type UserProfileData } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useRoadmapGeneration } from '@/lib/hooks/api/use-roadmap-generation';
import { useAuthStore } from '@/lib/store/auth-store';
import type { UserRequest } from '@/types/generated/models';
import Link from 'next/link';

type Step = 'goal' | 'preferences' | 'generating';

interface FormData {
  learningGoal: string;
  currentLevel: 'beginner' | 'intermediate' | 'advanced';
  availableHours: number;
  motivation: string;
  careerBackground: string;
  contentPreferences: string[];
}

const contentOptions = [
  { id: 'visual', label: 'Visual', icon: Eye, desc: 'Videos, diagrams, demonstrations' },
  { id: 'text', label: 'Text', icon: FileText, desc: 'Documentation, articles, books' },
  { id: 'audio', label: 'Audio', icon: Headphones, desc: 'Podcasts, audio content' },
  { id: 'hands_on', label: 'Hands-on', icon: Wrench, desc: 'Interactive exercises, projects' },
];

const levelOptions = [
  { id: 'beginner', label: 'Beginner', description: 'New to this topic' },
  { id: 'intermediate', label: 'Intermediate', description: 'Some experience' },
  { id: 'advanced', label: 'Advanced', description: 'Looking to master' },
];

// Step to progress mapping
const stepProgress: Record<string, { progress: number; status: string }> = {
  'queued': { progress: 10, status: 'Task queued...' },
  'intent_analysis': { progress: 20, status: 'Analyzing learning goals...' },
  'curriculum_design': { progress: 40, status: 'Designing curriculum structure...' },
  'structure_validation': { progress: 50, status: 'Validating roadmap structure...' },
  'human_review': { progress: 55, status: 'Awaiting human review...' },
  'content_generation_queued': { progress: 65, status: 'Queueing content generation...' },
  'content_generation': { progress: 70, status: 'Generating learning content...' },
  'tutorial_generation': { progress: 75, status: 'Generating tutorial content...' },
  'resource_recommendation': { progress: 85, status: 'Recommending resources...' },
  'quiz_generation': { progress: 90, status: 'Generating quiz questions...' },
  'finalizing': { progress: 95, status: 'Finalizing...' },
  'completed': { progress: 100, status: 'Generation complete!' },
};

export default function NewRoadmapClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState<Step>('goal');
  
  // Auth
  const { getUserId } = useAuthStore();
  
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

  // Use new Hooks
  const { generationProgress, currentStep, error: storeError, updateProgress } = useRoadmapStore();
  const { mutate: generateRoadmap, isPending } = useRoadmapGeneration();
  const [taskId, setTaskId] = useState<string | null>(null);
  
  // 从 URL 参数恢复任务（用于继续未完成的路线图生成）
  const resumeTaskId = searchParams.get('task_id');

  // AbortController for request cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // 如果 URL 中有 task_id，自动恢复到生成页面
  useEffect(() => {
    if (resumeTaskId && !taskId) {
      console.log('[NewRoadmap] Resuming task from URL:', resumeTaskId);
      
      // 先获取任务状态
      getRoadmapStatus(resumeTaskId)
        .then((status) => {
          console.log('[NewRoadmap] Task status:', status);
          
          const taskStatus = status.status;
          
          // 如果任务已完成或部分失败，跳转到路线图详情页
          if ((taskStatus === 'completed' || taskStatus === 'partial_failure') && status.roadmap_id) {
            console.log('[NewRoadmap] Task finished with status:', taskStatus, 'Navigating to roadmap:', status.roadmap_id);
            router.push(`/roadmap/${status.roadmap_id}`);
            return;
          }
          
          // 如果任务还在进行中，直接跳转到任务详情页
          if (taskStatus === 'processing' || taskStatus === 'pending' || taskStatus === 'human_review_pending') {
            console.log('[NewRoadmap] Task in progress, navigating to task detail:', resumeTaskId);
            router.push(`/tasks/${resumeTaskId}`);
            return;
          }
          
          // 如果任务失败，显示错误
          if (taskStatus === 'failed') {
            console.error('[NewRoadmap] Task failed:', status.error_message);
            return;
          }
        })
        .catch((error) => {
          console.error('[NewRoadmap] Failed to get task status:', error);
        });
    }
  }, [resumeTaskId, taskId, router, updateProgress]);

  // Load user profile on mount with abort controller
  useEffect(() => {
    const loadProfile = async () => {
      const userId = getUserId();
      if (!userId) {
        console.error('[NewRoadmap] No user ID, cannot load profile');
        setIsProfileLoading(false);
        return;
      }
      
      // Cancel previous request
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();
      
      try {
        setIsProfileLoading(true);
        const profile = await getUserProfile(userId);
        
        // Check if component is still mounted
        if (!abortControllerRef.current?.signal.aborted) {
          setUserProfile(profile);
          
          // Check if profile is "complete"
          const isComplete = !!(
            profile.industry ||
            profile.current_role ||
            (profile.tech_stack && profile.tech_stack.length > 0) ||
            (profile.learning_style && profile.learning_style.length > 0)
          );
          setHasCompletedProfile(isComplete);
          
          // Pre-fill form with profile data
          if (isComplete) {
            setFormData((prev) => ({
              ...prev,
              availableHours: profile.weekly_commitment_hours || 10,
              contentPreferences: profile.learning_style?.length > 0 
                ? profile.learning_style 
                : prev.contentPreferences,
            }));
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Failed to load profile:', error);
        }
      } finally {
        if (!abortControllerRef.current?.signal.aborted) {
          setIsProfileLoading(false);
        }
      }
    };

    loadProfile();

    // Cleanup on unmount
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [getUserId]);

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

  const handleGenerate = () => {
    // 不再切换到generating步骤，因为会立即跳转

    const userId = getUserId();
    if (!userId) {
      alert('Please login first');
      router.push('/login');
      return;
    }
    
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Build API request
    const request: UserRequest = {
      user_id: userId,
      session_id: sessionId,
      preferences: {
        learning_goal: formData.learningGoal,
        available_hours_per_week: formData.availableHours,
        motivation: formData.motivation || 'Personal interest',
        current_level: formData.currentLevel,
        career_background: formData.careerBackground || 'Not specified',
        content_preference: formData.contentPreferences as any,
        // Include profile data if available
        ...(userProfile && hasCompletedProfile ? {
          industry: userProfile.industry,
          current_role: userProfile.current_role,
          tech_stack: userProfile.tech_stack?.map(item => ({
            name: item.technology,
            proficiency: (item.proficiency === 'expert' ? 'advanced' : item.proficiency) as 'beginner' | 'intermediate' | 'advanced',
          })),
          preferred_language: userProfile.primary_language,
        } : {}),
      },
    };

    // Call mutation to start generation
    generateRoadmap(request, {
      onSuccess: (response) => {
        console.log('[Generate] Task created:', response.task_id);
        setTaskId(response.task_id); // Setting task_id will automatically start WebSocket
        
        // 立即跳转到任务详情页
        router.push(`/tasks/${response.task_id}`);
      },
      onError: (error) => {
        console.error('[Generate] Error:', error);
      },
    });
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
                  Complete your learning profile
                </p>
                <p className="text-xs text-muted-foreground">
                  A complete profile helps us generate more personalized learning roadmaps
                </p>
              </div>
              <Link href="/profile">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <User className="w-4 h-4" />
                  Complete Profile
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step Progress */}
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
                {contentOptions.map((option) => {
                  const Icon = option.icon;
                  return (
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
                        <Icon className="w-5 h-5 mr-2" />
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">{option.desc}</div>
                    </button>
                  );
                })}
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
              <Button 
                onClick={handleNext} 
                variant="sage" 
                className="gap-2"
                disabled={isPending}
              >
                {isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    Generate Roadmap <Sparkles size={16} />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

