'use client';

import { useState } from 'react';
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
} from 'lucide-react';

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
  { id: 'text', label: 'Articles & Documentation', icon: '📚' },
  { id: 'video', label: 'Video Tutorials', icon: '🎬' },
  { id: 'interactive', label: 'Interactive Exercises', icon: '💻' },
  { id: 'project', label: 'Project-Based Learning', icon: '🛠️' },
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
  const [formData, setFormData] = useState<FormData>({
    learningGoal: '',
    currentLevel: 'beginner',
    availableHours: 10,
    motivation: '',
    careerBackground: '',
    contentPreferences: ['text', 'interactive'],
  });

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

    // Simulate generation progress
    const progressInterval = setInterval(() => {
      setGenerationProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 500);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 4000));

    clearInterval(progressInterval);
    setGenerationProgress(100);
    setIsGenerating(false);

    // Navigate to the generated roadmap
    setTimeout(() => {
      router.push('/app/roadmap/demo');
    }, 500);
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
              <label className="block text-sm font-medium mb-2">
                Preferred Content Types
              </label>
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
                    <span className="text-xl mr-2">{option.icon}</span>
                    <span className="font-medium">{option.label}</span>
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
            <div className="w-20 h-20 bg-sage-100 rounded-full mx-auto flex items-center justify-center mb-6">
              <Loader2 className="w-10 h-10 text-sage-600 animate-spin" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
              Crafting Your Roadmap
            </h2>
            <p className="text-muted-foreground mb-8">
              Our AI agents are working together to create your personalized curriculum...
            </p>
            <div className="max-w-md mx-auto">
              <Progress value={Math.min(generationProgress, 100)} className="h-2" />
              <p className="text-sm text-muted-foreground mt-2">
                {generationProgress < 30 && 'Analyzing learning goals...'}
                {generationProgress >= 30 && generationProgress < 60 && 'Designing curriculum structure...'}
                {generationProgress >= 60 && generationProgress < 90 && 'Generating tutorials...'}
                {generationProgress >= 90 && 'Finalizing roadmap...'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

