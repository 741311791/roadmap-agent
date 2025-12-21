'use client';

import React, { useEffect } from 'react';
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
  Save,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAvailableTechnologies } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/store/auth-store';
import { useUserProfileStore } from '@/lib/store/user-profile-store';
import { useAutoSave, useSaveStatus } from '@/lib/hooks/use-auto-save';
import { TechAssessmentDialog } from '@/components/profile';
import type { TechStackItem } from '@/lib/api/endpoints';

// Types
type LearningStyleType = 'visual' | 'text' | 'audio' | 'hands_on';

interface TechStackRowItem extends TechStackItem {
  id: string;
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

/**
 * 用于将技术栈名称转换为显示标签的辅助函数
 */
function getTechLabel(value: string, availableTechs: string[]): string {
  // 首先检查是否在预定义列表中
  const predefined = TECHNOLOGIES.find(t => t.value === value);
  if (predefined) return predefined.label;
  
  // 如果是自定义的，首字母大写
  return value.charAt(0).toUpperCase() + value.slice(1);
}

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
  // Auth
  const { getUserId } = useAuthStore();
  const userId = getUserId();
  
  // Profile Store
  const { profile, loadProfile, updateProfile, addTechStack, updateTechStack: updateTech, removeTechStack, toggleLearningStyle, setLearningStyles } = useUserProfileStore();
  
  // Auto-save
  useAutoSave({
    debounceMs: 2000,
    enabled: true,
  });
  
  // Save status
  const { status: saveStatus, message: saveMessage } = useSaveStatus();
  
  // Available technologies from database
  const [availableTechnologies, setAvailableTechnologies] = React.useState<string[]>([]);
  
  // Assessment dialog state
  const [assessmentDialogOpen, setAssessmentDialogOpen] = React.useState(false);
  const [selectedTechForAssessment, setSelectedTechForAssessment] = React.useState<{
    technology: string;
    proficiency: string;
  } | null>(null);

  // 加载用户画像
  useEffect(() => {
    if (!userId) {
      console.error('[Profile] No user ID');
      return;
    }
    
    const loadData = async () => {
      try {
        // 并行加载用户画像和可用技术栈列表
        const [, techsResponse] = await Promise.all([
          loadProfile(userId),
          getAvailableTechnologies().catch(err => {
            console.error('Failed to load available technologies:', err);
            return { technologies: [], count: 0 };
          })
        ]);
        
        // 设置可用技术栈
        setAvailableTechnologies(techsResponse.technologies);
      } catch (error) {
        console.error('Failed to load data:', error);
      }
    };

    loadData();
  }, [userId, loadProfile]);
  
  // 将tech_stack转换为带id的格式（用于UI）
  const techStackWithIds: TechStackRowItem[] = React.useMemo(() => {
    if (!profile?.tech_stack) return [];
    return profile.tech_stack.map((item, index) => ({
      ...item,
      id: `tech-${item.technology}-${index}`,
    }));
  }, [profile?.tech_stack]);

  const addTechnology = () => {
    const newItem: TechStackItem = {
      technology: '',
      proficiency: 'beginner',
    };
    addTechStack(newItem);
  };

  const removeTechnology = (technology: string) => {
    removeTechStack(technology);
  };

  const updateTechnology = (
    oldTechnology: string,
    field: keyof TechStackItem,
    value: string
  ) => {
    if (field === 'technology') {
      // 如果改变了technology名称，需要特殊处理
      if (oldTechnology === '') {
        // 新添加的项，直接更新
        addTechStack({ technology: value, proficiency: 'beginner' });
      } else {
        // 已存在的项，删除旧的，添加新的
        removeTechStack(oldTechnology);
        const oldItem = profile?.tech_stack.find(t => t.technology === oldTechnology);
        addTechStack({ 
          technology: value, 
          proficiency: (oldItem?.proficiency || 'beginner') as 'beginner' | 'intermediate' | 'expert'
        });
      }
    } else {
      // 更新proficiency
      updateTech(oldTechnology, { [field]: value as any });
    }
  };

  const handleAssess = (technology: string, proficiency: string) => {
    setSelectedTechForAssessment({ technology, proficiency });
    setAssessmentDialogOpen(true);
  };

  const selectAllLearningStyles = () => {
    if (profile?.learning_style.length === LEARNING_STYLES.length) {
      setLearningStyles([]);
    } else {
      setLearningStyles(LEARNING_STYLES.map((s) => s.value));
    }
  };

  if (!profile) {
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
          
          {/* Auto-save indicator */}
          {saveStatus !== 'idle' && (
            <div className="flex items-center justify-center gap-2 text-sm">
              {saveStatus === 'saving' && (
                <>
                  <Loader2 className="w-3 h-3 animate-spin text-sage-600" />
                  <span className="text-muted-foreground">{saveMessage}</span>
                </>
              )}
              {saveStatus === 'saved' && (
                <>
                  <CheckCircle2 className="w-3 h-3 text-sage-600" />
                  <span className="text-sage-600">{saveMessage}</span>
                </>
              )}
              {saveStatus === 'error' && (
                <>
                  <span className="text-destructive text-xs">{saveMessage}</span>
                </>
              )}
            </div>
          )}
        </div>

        <div className="space-y-8">
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
                  checked={profile.ai_personalization}
                  onCheckedChange={(checked) => updateProfile({ ai_personalization: checked })}
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
                <Select 
                  value={profile.industry || ''} 
                  onValueChange={(value) => updateProfile({ industry: value })}
                >
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
                <Select 
                  value={profile.current_role || ''} 
                  onValueChange={(value) => updateProfile({ current_role: value })}
                >
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
              {techStackWithIds.map((item) => (
                <TechStackRow
                  key={item.id}
                  item={item}
                  allTechStack={techStackWithIds}
                  availableTechnologies={availableTechnologies}
                  onUpdate={updateTechnology}
                  onRemove={removeTechnology}
                  onAssess={handleAssess}
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
                      value={profile.primary_language}
                      onValueChange={(value) => updateProfile({ primary_language: value })}
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
                      value={profile.secondary_language || ''}
                      onValueChange={(value) => updateProfile({ secondary_language: value })}
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
                    {profile.weekly_commitment_hours} hours
                  </span>
                </div>
                <Slider
                  value={[profile.weekly_commitment_hours]}
                  onValueChange={([value]) => updateProfile({ weekly_commitment_hours: value })}
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
                  {profile.learning_style.length === LEARNING_STYLES.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {LEARNING_STYLES.map((style) => (
                  <LearningStyleCard
                    key={style.value}
                    style={style}
                    isSelected={profile.learning_style.includes(style.value)}
                    onSelect={() => toggleLearningStyle(style.value)}
                  />
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Tech Assessment Dialog */}
      {selectedTechForAssessment && (
        <TechAssessmentDialog
          open={assessmentDialogOpen}
          onOpenChange={setAssessmentDialogOpen}
          technology={selectedTechForAssessment.technology}
          proficiency={selectedTechForAssessment.proficiency}
        />
      )}
    </div>
  );
}

// Tech Stack Row Component
function TechStackRow({
  item,
  allTechStack,
  availableTechnologies,
  onUpdate,
  onRemove,
  onAssess,
}: {
  item: TechStackRowItem;
  allTechStack: TechStackRowItem[];
  availableTechnologies: string[];
  onUpdate: (oldTechnology: string, field: keyof TechStackItem, value: string) => void;
  onRemove: (technology: string) => void;
  onAssess: (technology: string, proficiency: string) => void;
}) {
  const [isCustomInput, setIsCustomInput] = React.useState(false);
  const [customValue, setCustomValue] = React.useState('');
  
  // 只使用数据库中有测验题目的技术栈（使用预定义常量提供更好的label）
  const allTechOptions = React.useMemo(() => {
    return availableTechnologies.map(tech => ({
      value: tech,
      label: getTechLabel(tech, availableTechnologies),
    }));
  }, [availableTechnologies]);
  
  // 检查当前技术栈是否在选项中
  const currentTechExists = item.technology && allTechOptions.some(t => t.value === item.technology);
  
  // 构建完整的选项列表（包括当前自定义值）
  const displayOptions = React.useMemo(() => {
    const options = [...allTechOptions];
    // 如果当前值是自定义的（不在预定义列表中），添加到选项中
    if (item.technology && !currentTechExists) {
      options.unshift({
        value: item.technology,
        label: `${item.technology} (Custom)`,
      });
    }
    return options;
  }, [allTechOptions, item.technology, currentTechExists]);
  
  return (
    <Card className="border shadow-sm bg-white">
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          {/* Technology Select with Custom Input */}
          <div className="w-40">
            {isCustomInput ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && customValue.trim()) {
                      onUpdate(item.technology, 'technology', customValue.trim());
                      setIsCustomInput(false);
                      setCustomValue('');
                    } else if (e.key === 'Escape') {
                      setIsCustomInput(false);
                      setCustomValue('');
                    }
                  }}
                  onBlur={() => {
                    // 失去焦点时，如果有内容则保存
                    if (customValue.trim()) {
                      onUpdate(item.technology, 'technology', customValue.trim());
                      setIsCustomInput(false);
                      setCustomValue('');
                    }
                  }}
                  placeholder="Enter technology name"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  autoFocus
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setIsCustomInput(false);
                    setCustomValue('');
                  }}
                >
                  ✕
                </Button>
              </div>
            ) : (
              <Select
                value={item.technology}
                onValueChange={(value) => {
                  if (value === '__custom__') {
                    setIsCustomInput(true);
                    setCustomValue('');
                  } else if (value === '__edit_custom__') {
                    // 编辑当前自定义值
                    setIsCustomInput(true);
                    setCustomValue(item.technology);
                  } else {
                    onUpdate(item.technology, 'technology', value);
                  }
                }}
              >
                <SelectTrigger className="bg-white">
                  <SelectValue placeholder="Select technology" />
                </SelectTrigger>
                <SelectContent>
                  {displayOptions.map((tech) => {
                    // 检查该技术是否已被其他行选择
                    const isSelected = allTechStack.some(
                      (stackItem) => stackItem.technology === tech.value && stackItem.id !== item.id
                    );
                    
                    return (
                      <SelectItem 
                        key={tech.value} 
                        value={tech.value}
                        disabled={isSelected}
                        className={cn(isSelected && 'opacity-50 cursor-not-allowed')}
                      >
                        {tech.label}
                        {isSelected && ' (selected)'}
                      </SelectItem>
                    );
                  })}
                  {/* 如果当前是自定义值，提供编辑选项 */}
                  {item.technology && !currentTechExists && (
                    <SelectItem value="__edit_custom__" className="text-sage-600 font-medium">
                      ✏️ Edit Custom
                    </SelectItem>
                  )}
                  <SelectItem value="__custom__" className="text-sage-600 font-medium">
                    + Custom Technology
                  </SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Proficiency Selector */}
          <div className="flex-1">
            <ProficiencySelector
              value={item.proficiency}
              onChange={(value) => onUpdate(item.technology, 'proficiency', value)}
            />
          </div>

          {/* Assess Button */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5 text-sage-600 border-sage-300 hover:bg-sage-50"
            onClick={() => onAssess(item.technology, item.proficiency)}
            disabled={!item.technology || !item.proficiency}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Assess
          </Button>

          {/* Delete Button */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => onRemove(item.technology)}
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
