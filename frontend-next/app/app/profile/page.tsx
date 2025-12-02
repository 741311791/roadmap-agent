'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ShieldCheck,
  Briefcase,
  Code2,
  Languages,
  GraduationCap,
  Plus,
  Sparkles,
  Trash2,
  Eye,
  FileText,
  Headphones,
  Wrench,
  Check,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getUserProfile, saveUserProfile } from '@/lib/api/endpoints';

// 硬编码的用户 ID（TODO: 替换为真实用户认证）
const USER_ID = 'temp-user-001';

// Types
interface TechStackItem {
  id: string;
  technology: string;
  proficiency: 'beginner' | 'intermediate' | 'expert';
}

type LearningStyleType = 'visual' | 'text' | 'audio' | 'hands_on';

interface ProfileFormData {
  aiPersonalization: boolean;
  industry: string;
  currentRole: string;
  techStack: TechStackItem[];
  primaryLanguage: string;
  secondaryLanguage: string;
  weeklyCommitment: number;
  learningStyles: LearningStyleType[];  // 支持多选
}

// Constants
const INDUSTRIES = [
  { value: 'technology', label: 'Technology' },
  { value: 'finance', label: 'Finance' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'education', label: 'Education' },
  { value: 'retail', label: 'Retail' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'consulting', label: 'Consulting' },
  { value: 'media', label: 'Media & Entertainment' },
  { value: 'other', label: 'Other' },
];

const ROLES = [
  { value: 'student', label: 'Student' },
  { value: 'junior_dev', label: 'Junior Developer' },
  { value: 'mid_dev', label: 'Mid-Level Developer' },
  { value: 'senior_dev', label: 'Senior Developer' },
  { value: 'tech_lead', label: 'Tech Lead' },
  { value: 'engineering_manager', label: 'Engineering Manager' },
  { value: 'product_manager', label: 'Product Manager' },
  { value: 'designer', label: 'Designer' },
  { value: 'data_scientist', label: 'Data Scientist' },
  { value: 'career_changer', label: 'Career Changer' },
  { value: 'other', label: 'Other' },
];

const TECHNOLOGIES = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'react', label: 'React' },
  { value: 'vue', label: 'Vue.js' },
  { value: 'angular', label: 'Angular' },
  { value: 'nextjs', label: 'Next.js' },
  { value: 'nodejs', label: 'Node.js' },
  { value: 'java', label: 'Java' },
  { value: 'csharp', label: 'C#' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'swift', label: 'Swift' },
  { value: 'kotlin', label: 'Kotlin' },
  { value: 'sql', label: 'SQL' },
  { value: 'docker', label: 'Docker' },
  { value: 'kubernetes', label: 'Kubernetes' },
  { value: 'aws', label: 'AWS' },
  { value: 'gcp', label: 'Google Cloud' },
  { value: 'azure', label: 'Azure' },
];

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文 (Chinese)' },
  { value: 'es', label: 'Español (Spanish)' },
  { value: 'ja', label: '日本語 (Japanese)' },
  { value: 'ko', label: '한국어 (Korean)' },
  { value: 'fr', label: 'Français (French)' },
  { value: 'de', label: 'Deutsch (German)' },
  { value: 'pt', label: 'Português (Portuguese)' },
];

const LEARNING_STYLES: {
  value: LearningStyleType;
  label: string;
  icon: React.ElementType;
  description: string;
}[] = [
  {
    value: 'visual',
    label: 'Visual',
    icon: Eye,
    description: 'Video tutorials, diagrams, demos',
  },
  {
    value: 'text',
    label: 'Text',
    icon: FileText,
    description: 'Documentation, articles, books',
  },
  {
    value: 'audio',
    label: 'Audio',
    icon: Headphones,
    description: 'Podcasts, audio content',
  },
  {
    value: 'hands_on',
    label: 'Hands-on',
    icon: Wrench,
    description: 'Interactive exercises, projects',
  },
];

export default function ProfilePage() {
  const [aiEnabled, setAiEnabled] = useState(true);
  const [techStack, setTechStack] = useState<TechStackItem[]>([]);
  const [weeklyHours, setWeeklyHours] = useState([10]);
  const [learningStyles, setLearningStyles] = useState<LearningStyleType[]>([]);
  const [industry, setIndustry] = useState<string>('');
  const [currentRole, setCurrentRole] = useState<string>('');
  const [primaryLanguage, setPrimaryLanguage] = useState<string>('zh');
  const [secondaryLanguage, setSecondaryLanguage] = useState<string>('');
  
  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const { handleSubmit, setValue } = useForm<ProfileFormData>({
    defaultValues: {
      aiPersonalization: true,
      industry: '',
      currentRole: '',
      primaryLanguage: 'zh',
      secondaryLanguage: '',
      weeklyCommitment: 10,
      learningStyles: [],
    },
  });

  // 加载用户画像
  useEffect(() => {
    const loadProfile = async () => {
      try {
        setIsLoading(true);
        const profile = await getUserProfile(USER_ID);
        
        // 填充表单数据
        setAiEnabled(profile.ai_personalization);
        setIndustry(profile.industry || '');
        setCurrentRole(profile.current_role || '');
        setPrimaryLanguage(profile.primary_language || 'zh');
        setSecondaryLanguage(profile.secondary_language || '');
        setWeeklyHours([profile.weekly_commitment_hours || 10]);
        setLearningStyles((profile.learning_style || []) as LearningStyleType[]);
        
        // 转换技术栈数据
        if (profile.tech_stack && profile.tech_stack.length > 0) {
          setTechStack(
            profile.tech_stack.map((item, index) => ({
              id: `tech-${index}`,
              technology: item.technology,
              proficiency: item.proficiency as 'beginner' | 'intermediate' | 'expert',
            }))
          );
        }
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, []);

  const addTechnology = () => {
    const newItem: TechStackItem = {
      id: `tech-${Date.now()}`,
      technology: '',
      proficiency: 'beginner',
    };
    setTechStack([...techStack, newItem]);
  };

  const removeTechnology = (id: string) => {
    setTechStack(techStack.filter((item) => item.id !== id));
  };

  const updateTechnology = (
    id: string,
    field: keyof TechStackItem,
    value: string
  ) => {
    setTechStack(
      techStack.map((item) =>
        item.id === id ? { ...item, [field]: value } : item
      )
    );
  };

  const toggleLearningStyle = (style: LearningStyleType) => {
    setLearningStyles((prev) =>
      prev.includes(style)
        ? prev.filter((s) => s !== style)
        : [...prev, style]
    );
  };

  const selectAllLearningStyles = () => {
    if (learningStyles.length === LEARNING_STYLES.length) {
      setLearningStyles([]);
    } else {
      setLearningStyles(LEARNING_STYLES.map((s) => s.value));
    }
  };

  const onSubmit = async () => {
    try {
      setIsSaving(true);
      setSaveSuccess(false);

      await saveUserProfile(USER_ID, {
        industry: industry || null,
        current_role: currentRole || null,
        tech_stack: techStack
          .filter((item) => item.technology)
          .map((item) => ({
            technology: item.technology,
            proficiency: item.proficiency,
          })),
        primary_language: primaryLanguage,
        secondary_language: secondaryLanguage || null,
        weekly_commitment_hours: weeklyHours[0],
        learning_style: learningStyles,
        ai_personalization: aiEnabled,
      });

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save profile:', error);
      alert('Failed to save. Please try again later.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-sage-600" />
          <p className="mt-4 text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl md:text-5xl font-serif font-bold text-charcoal">
            Your Profile
          </h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            Customize your learning experience. We use this to tailor your
            roadmap and recommendations.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Section 1: AI Personalization */}
          <Card className="bg-sage-50 border-0 shadow-none">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-sage-100 flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5 text-sage-600" />
                  </div>
                  <div>
                    <h2 className="text-xl font-serif font-semibold text-charcoal">
                      AI Personalization
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Allow AI to analyze your progress for better
                      recommendations.
                    </p>
                  </div>
                </div>
                <Switch
                  checked={aiEnabled}
                  onCheckedChange={setAiEnabled}
                  aria-label="Toggle AI personalization"
                />
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Professional Background */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-sage-600" />
              <h2 className="text-xl font-serif font-semibold text-charcoal">
                Professional Background
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Industry
                </Label>
                <Select value={industry} onValueChange={setIndustry}>
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select option" />
                  </SelectTrigger>
                  <SelectContent>
                    {INDUSTRIES.map((ind) => (
                      <SelectItem key={ind.value} value={ind.value}>
                        {ind.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Current Role
                </Label>
                <Select value={currentRole} onValueChange={setCurrentRole}>
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select option" />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          {/* Section 3: Current Tech Stack */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Code2 className="w-5 h-5 text-sage-600" />
                <h2 className="text-xl font-serif font-semibold text-charcoal">
                  Current Tech Stack
                </h2>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addTechnology}
                className="gap-1.5"
              >
                <Plus className="w-4 h-4" />
                Add Technology
              </Button>
            </div>

            <div className="space-y-3">
              {techStack.map((item) => (
                <TechStackRow
                  key={item.id}
                  item={item}
                  onUpdate={updateTechnology}
                  onRemove={removeTechnology}
                />
              ))}
            </div>
          </section>

          {/* Section 4: Language Preferences */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Languages className="w-5 h-5 text-sage-600" />
              <h2 className="text-xl font-serif font-semibold text-charcoal">
                Language Preferences
              </h2>
            </div>
            <Card className="border shadow-sm">
              <CardContent className="p-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                      Primary Language
                    </Label>
                    <Select
                      value={primaryLanguage}
                      onValueChange={setPrimaryLanguage}
                    >
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select option" />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang.value} value={lang.value}>
                            {lang.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                      Secondary Language
                    </Label>
                    <Select
                      value={secondaryLanguage}
                      onValueChange={setSecondaryLanguage}
                    >
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select option" />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang.value} value={lang.value}>
                            {lang.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
          </section>

          {/* Section 5: Learning Habits */}
          <section className="space-y-6">
            <div className="flex items-center gap-2">
              <GraduationCap className="w-5 h-5 text-sage-600" />
              <h2 className="text-xl font-serif font-semibold text-charcoal">
                Learning Habits
              </h2>
            </div>

            {/* Weekly Commitment Slider */}
            <Card className="border shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">
                    Weekly Commitment
                  </Label>
                  <span className="text-lg font-serif font-semibold text-charcoal">
                    {weeklyHours[0]} hours
                  </span>
                </div>
                <Slider
                  value={weeklyHours}
                  onValueChange={setWeeklyHours}
                  min={2}
                  max={40}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Casual (5h)</span>
                  <span>Intense (40h)</span>
                </div>
              </CardContent>
            </Card>

            {/* Learning Style Selection - Multi-select */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">
                  Preferred Learning Style (select multiple)
                </Label>
                <button
                  type="button"
                  onClick={selectAllLearningStyles}
                  className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
                >
                  {learningStyles.length === LEARNING_STYLES.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {LEARNING_STYLES.map((style) => (
                  <LearningStyleCard
                    key={style.value}
                    style={style}
                    isSelected={learningStyles.includes(style.value)}
                    onSelect={() => toggleLearningStyle(style.value)}
                  />
                ))}
              </div>
            </div>
          </section>

          {/* Save Button */}
          <div className="flex justify-center pt-4">
            <Button
              type="submit"
              disabled={isSaving}
              className="bg-charcoal hover:bg-charcoal-light text-white px-8 py-2.5 min-w-[160px]"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : saveSuccess ? (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Saved
                </>
              ) : (
                'Save Profile'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Tech Stack Row Component
function TechStackRow({
  item,
  onUpdate,
  onRemove,
}: {
  item: TechStackItem;
  onUpdate: (id: string, field: keyof TechStackItem, value: string) => void;
  onRemove: (id: string) => void;
}) {
  return (
    <Card className="border shadow-sm bg-white">
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          {/* Technology Select */}
          <div className="w-40">
            <Select
              value={item.technology}
              onValueChange={(value) => onUpdate(item.id, 'technology', value)}
            >
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Select tech" />
              </SelectTrigger>
              <SelectContent>
                {TECHNOLOGIES.map((tech) => (
                  <SelectItem key={tech.value} value={tech.value}>
                    {tech.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Proficiency Selector */}
          <div className="flex-1">
            <ProficiencySelector
              value={item.proficiency}
              onChange={(value) => onUpdate(item.id, 'proficiency', value)}
            />
          </div>

          {/* Assess Button */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5 text-sage-600 border-sage-300 hover:bg-sage-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Assess
          </Button>

          {/* Delete Button */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => onRemove(item.id)}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Proficiency Selector Component
function ProficiencySelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const levels = [
    { value: 'beginner', label: 'Beginner' },
    { value: 'intermediate', label: 'Intermediate' },
    { value: 'expert', label: 'Expert' },
  ];

  const currentIndex = levels.findIndex((l) => l.value === value);

  return (
    <div className="flex items-center gap-2">
      {/* Progress Track */}
      <div className="flex-1 relative">
        {/* Labels row */}
        <div className="flex justify-between text-xs text-muted-foreground mb-2 px-2">
          {levels.map((level) => (
            <span
              key={level.value}
              className={cn(
                'uppercase tracking-wider transition-colors',
                value === level.value && 'text-sage-600 font-medium'
              )}
            >
              {level.label}
            </span>
          ))}
        </div>
        {/* Track and dots container */}
        <div className="relative h-4 flex items-center">
          {/* Track background - inset to align with dot centers */}
          <div className="absolute left-2 right-2 h-2 bg-secondary rounded-full" />
          {/* Progress fill */}
          <div
            className="absolute left-2 h-2 bg-sage-500 rounded-full transition-all duration-300"
            style={{ 
              width: currentIndex === 0 
                ? '0%' 
                : `calc(${(currentIndex / (levels.length - 1)) * 100}% - 16px)` 
            }}
          />
          {/* Dots using flexbox - evenly distributed */}
          <div className="relative w-full flex justify-between items-center">
            {levels.map((level, index) => (
              <button
                key={level.value}
                type="button"
                onClick={() => onChange(level.value)}
                className={cn(
                  'w-4 h-4 rounded-full border-2 transition-all z-10 flex-shrink-0',
                  index <= currentIndex
                    ? 'bg-sage-500 border-sage-500'
                    : 'bg-white border-secondary hover:border-sage-300'
                )}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Learning Style Card Component
function LearningStyleCard({
  style,
  isSelected,
  onSelect,
}: {
  style: {
    value: string;
    label: string;
    icon: React.ElementType;
    description: string;
  };
  isSelected: boolean;
  onSelect: () => void;
}) {
  const Icon = style.icon;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'relative p-4 rounded-lg border-2 transition-all text-center',
        isSelected
          ? 'bg-sage-50 border-sage-400'
          : 'bg-white border-border hover:border-sage-200'
      )}
    >
      {isSelected && (
        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-sage-500 flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}
      <div
        className={cn(
          'w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center',
          isSelected ? 'bg-sage-200' : 'bg-muted'
        )}
      >
        <Icon
          className={cn(
            'w-5 h-5',
            isSelected ? 'text-sage-700' : 'text-muted-foreground'
          )}
        />
      </div>
      <span
        className={cn(
          'font-medium text-sm block',
          isSelected ? 'text-sage-700' : 'text-foreground'
        )}
      >
        {style.label}
      </span>
    </button>
  );
}
