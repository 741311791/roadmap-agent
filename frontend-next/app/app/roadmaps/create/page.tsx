'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Loader2, CheckCircle2, AlertCircle, User } from 'lucide-react';
import { generateFullRoadmapStream, getUserProfile, type UserProfileData } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest, LearningPreferences } from '@/types/generated/models';
import type { RoadmapGenerationEvent } from '@/types/custom/sse';
import Link from 'next/link';

// 硬编码的用户 ID（TODO: 替换为真实用户认证）
const USER_ID = 'temp-user-001';

export default function CreateRoadmapPage() {
  const router = useRouter();
  const {
    setGenerating,
    setGenerationPhase,
    appendGenerationBuffer,
    clearGenerationBuffer,
    updateTutorialProgress,
    addToHistory,
  } = useRoadmapStore();

  const [formData, setFormData] = useState<LearningPreferences>({
    learning_goal: '',
    available_hours_per_week: 10,
    motivation: '',
    current_level: 'beginner',
    career_background: '',
    content_preference: [],
  });

  const [isGenerating, setIsGeneratingLocal] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [phaseBuffer, setPhaseBuffer] = useState<string>('');
  const [tutorialStatus, setTutorialStatus] = useState<{
    completed: number;
    total: number;
  }>({ completed: 0, total: 0 });
  const [currentBatch, setCurrentBatch] = useState<{
    index: number;
    total: number;
  }>({ index: 0, total: 0 });

  // Profile state
  const [userProfile, setUserProfile] = useState<UserProfileData | null>(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [hasCompletedProfile, setHasCompletedProfile] = useState(false);

  const phaseBufferRef = useRef<HTMLDivElement>(null);

  // Load user profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        setIsProfileLoading(true);
        const profile = await getUserProfile(USER_ID);
        setUserProfile(profile);
        
        // Check if profile is "complete"
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
            available_hours_per_week: profile.weekly_commitment_hours || 10,
            content_preference: profile.learning_style?.length > 0 
              ? profile.learning_style as any
              : prev.content_preference,
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

  // Auto scroll to bottom of phase buffer
  useEffect(() => {
    if (phaseBufferRef.current) {
      phaseBufferRef.current.scrollTop = phaseBufferRef.current.scrollHeight;
    }
  }, [phaseBuffer]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.learning_goal.trim()) {
      alert('Please enter a learning goal');
      return;
    }

    setIsGeneratingLocal(true);
    setGenerating(true);
    setCurrentPhase('preparing');
    setPhaseBuffer('');
    clearGenerationBuffer();

    const userRequest: UserRequest = {
      user_id: USER_ID,
      session_id: crypto.randomUUID(),
      preferences: {
        ...formData,
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
      await generateFullRoadmapStream(
        userRequest,
        {
          onEvent: (event: RoadmapGenerationEvent) => {
            switch (event.type) {
              case 'chunk':
                setCurrentPhase(event.agent);
                setGenerationPhase(event.agent === 'intent_analyzer' ? 'analyzing' : 'designing');
                setPhaseBuffer((prev) => prev + event.content);
                appendGenerationBuffer(event.content);
                break;

              case 'complete':
                // Agent completed
                clearGenerationBuffer();
                setPhaseBuffer('');
                break;

              case 'tutorials_start':
                setCurrentPhase('tutorials');
                setGenerationPhase('generating_tutorials');
                setTutorialStatus({ completed: 0, total: event.total_count });
                updateTutorialProgress(0, event.total_count);
                setCurrentBatch({ index: 0, total: Math.ceil(event.total_count / event.batch_size) });
                break;

              case 'batch_start':
                setCurrentBatch({ index: event.batch_index, total: event.total_batches });
                break;

              case 'tutorial_start':
                console.log(`Starting tutorial: ${event.concept_name}`);
                break;

              case 'tutorial_complete':
                setTutorialStatus((prev) => ({
                  ...prev,
                  completed: prev.completed + 1,
                }));
                updateTutorialProgress(tutorialStatus.completed + 1, tutorialStatus.total);
                break;

              case 'tutorial_error':
                console.error(`Tutorial error for ${event.concept_id}:`, event.error);
                break;

              case 'batch_complete':
                console.log(`Batch ${event.batch_index} complete:`, event.progress);
                break;

              case 'tutorials_done':
                console.log('All tutorials complete:', event.summary);
                break;

              case 'done':
                setCurrentPhase('done');
                setGenerationPhase('done');

                // Add to history
                if (event.roadmap_id && event.summary?.framework) {
                  const framework = event.summary.framework as any;
                  addToHistory({
                    roadmap_id: event.roadmap_id,
                    title: framework.title || formData.learning_goal,
                    created_at: new Date().toISOString(),
                    status: 'completed',
                    total_concepts: tutorialStatus.total,
                    completed_concepts: tutorialStatus.completed,
                  });

                  // Navigate to roadmap detail page
                  setTimeout(() => {
                    router.push(`/app/roadmap/${event.roadmap_id}`);
                  }, 1500);
                }
                break;

              case 'error':
                alert(`Error: ${event.message}`);
                setIsGeneratingLocal(false);
                setGenerating(false);
                setCurrentPhase('error');
                break;
            }
          },
          onComplete: () => {
            setIsGeneratingLocal(false);
            setGenerating(false);
          },
          onError: (error) => {
            alert(`Error: ${error.message}`);
            setIsGeneratingLocal(false);
            setGenerating(false);
            setCurrentPhase('error');
          },
        }
      );
    } catch (error) {
      console.error('Generation failed:', error);
      alert(`Generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setIsGeneratingLocal(false);
      setGenerating(false);
    }
  };

  const handleContentPreferenceToggle = (type: string) => {
    setFormData((prev) => ({
      ...prev,
      content_preference: prev.content_preference.includes(type as any)
        ? prev.content_preference.filter((t) => t !== type)
        : [...prev.content_preference, type as any],
    }));
  };

  const getPhaseTitle = (phase: string) => {
    switch (phase) {
      case 'preparing':
        return 'Preparing...';
      case 'intent_analyzer':
        return 'Analyzing learning requirements...';
      case 'curriculum_architect':
        return 'Designing curriculum...';
      case 'tutorials':
        return 'Generating tutorials...';
      case 'done':
        return 'Complete!';
      case 'error':
        return 'Error occurred';
      default:
        return phase;
    }
  };

  const calculateOverallProgress = () => {
    if (!isGenerating) return 0;
    if (currentPhase === 'done') return 100;
    if (currentPhase === 'preparing') return 5;
    if (currentPhase === 'intent_analyzer') return 15;
    if (currentPhase === 'curriculum_architect') return 30;
    if (currentPhase === 'tutorials' && tutorialStatus.total > 0) {
      return 30 + (tutorialStatus.completed / tutorialStatus.total) * 70;
    }
    return 30;
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">创建学习路线图</h1>
        <p className="text-muted-foreground">
          告诉我们你的学习目标,我们将为你生成个性化的学习路线图
        </p>
      </div>

      {/* Profile Guidance Card */}
      {!isGenerating && !isProfileLoading && !hasCompletedProfile && (
        <Card className="mb-6 border-primary/20 bg-primary/5">
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">完善你的学习画像</p>
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

      {!isGenerating ? (
        <Card>
          <CardHeader>
            <CardTitle>学习需求</CardTitle>
            <CardDescription>请填写以下信息,帮助我们了解你的学习需求</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Learning Goal */}
              <div className="space-y-2">
                <Label htmlFor="learning_goal">学习目标 *</Label>
                <Input
                  id="learning_goal"
                  placeholder="例如: 成为全栈 Web 开发工程师"
                  value={formData.learning_goal}
                  onChange={(e) =>
                    setFormData({ ...formData, learning_goal: e.target.value })
                  }
                  required
                />
              </div>

              {/* Current Level */}
              <div className="space-y-2">
                <Label htmlFor="current_level">当前水平 *</Label>
                <Select
                  value={formData.current_level}
                  onValueChange={(value) =>
                    setFormData({ ...formData, current_level: value as any })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beginner">初学者</SelectItem>
                    <SelectItem value="intermediate">中级</SelectItem>
                    <SelectItem value="advanced">高级</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Available Hours */}
              <div className="space-y-2">
                <Label htmlFor="available_hours_per_week">
                  每周可学习时间 (小时) *
                </Label>
                <Input
                  id="available_hours_per_week"
                  type="number"
                  min="1"
                  max="168"
                  value={formData.available_hours_per_week}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      available_hours_per_week: parseInt(e.target.value) || 10,
                    })
                  }
                  required
                />
              </div>

              {/* Motivation */}
              <div className="space-y-2">
                <Label htmlFor="motivation">学习动机</Label>
                <Textarea
                  id="motivation"
                  placeholder="例如: 想要转行进入科技行业,希望获得更好的职业发展机会"
                  value={formData.motivation}
                  onChange={(e) =>
                    setFormData({ ...formData, motivation: e.target.value })
                  }
                  rows={3}
                />
              </div>

              {/* Career Background */}
              <div className="space-y-2">
                <Label htmlFor="career_background">职业背景</Label>
                <Input
                  id="career_background"
                  placeholder="例如: 计算机科学本科,有2年前端开发经验"
                  value={formData.career_background}
                  onChange={(e) =>
                    setFormData({ ...formData, career_background: e.target.value })
                  }
                />
              </div>

              {/* Content Preference */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                <Label>内容偏好</Label>
                  <button
                    type="button"
                    onClick={() => {
                      const allTypes = ['visual', 'text', 'audio', 'hands_on'];
                      if (formData.content_preference.length === 4) {
                        setFormData({ ...formData, content_preference: [] });
                      } else {
                        setFormData({ ...formData, content_preference: allTypes as any });
                      }
                    }}
                    className="text-sm text-primary hover:underline"
                  >
                    {formData.content_preference.length === 4 ? '取消全选' : '以上都可以'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { type: 'visual', label: '视觉类', desc: '视频教程、图解' },
                    { type: 'text', label: '文本类', desc: '文档、文章' },
                    { type: 'audio', label: '音频类', desc: '播客、有声内容' },
                    { type: 'hands_on', label: '实操类', desc: '互动练习、项目' },
                  ].map(({ type, label, desc }) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => handleContentPreferenceToggle(type)}
                      className={`px-4 py-3 rounded-md border transition-colors text-left ${
                        formData.content_preference.includes(type as any)
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-background hover:bg-accent'
                      }`}
                    >
                      <div className="font-medium">{label}</div>
                      <div className={`text-xs ${formData.content_preference.includes(type as any) ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>{desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <Button type="submit" className="w-full" size="lg">
                生成路线图
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Overall Progress */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {currentPhase === 'done' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : currentPhase === 'error' ? (
                  <AlertCircle className="h-5 w-5 text-red-600" />
                ) : (
                  <Loader2 className="h-5 w-5 animate-spin" />
                )}
                {getPhaseTitle(currentPhase)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Progress value={calculateOverallProgress()} className="h-2" />
              <p className="text-sm text-muted-foreground mt-2">
                整体进度: {Math.round(calculateOverallProgress())}%
              </p>
            </CardContent>
          </Card>

          {/* Phase Output */}
          {phaseBuffer && currentPhase !== 'tutorials' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">实时输出</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  ref={phaseBufferRef}
                  className="bg-muted p-4 rounded-md max-h-64 overflow-y-auto font-mono text-sm whitespace-pre-wrap"
                >
                  {phaseBuffer}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tutorial Progress */}
          {currentPhase === 'tutorials' && tutorialStatus.total > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">教程生成进度</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>
                      批次 {currentBatch.index} / {currentBatch.total}
                    </span>
                    <span>
                      {tutorialStatus.completed} / {tutorialStatus.total} 个教程
                    </span>
                  </div>
                  <Progress
                    value={(tutorialStatus.completed / tutorialStatus.total) * 100}
                    className="h-2"
                  />
                </div>

                <div className="grid grid-cols-10 gap-2">
                  {Array.from({ length: tutorialStatus.total }, (_, i) => (
                    <div
                      key={i}
                      className={`h-3 rounded ${
                        i < tutorialStatus.completed
                          ? 'bg-green-500'
                          : 'bg-gray-200'
                      }`}
                      title={`教程 ${i + 1}`}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {currentPhase === 'done' && (
            <div className="text-center text-muted-foreground">
              正在跳转到路线图详情页...
            </div>
          )}
        </div>
      )}
    </div>
  );
}

