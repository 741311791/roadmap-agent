'use client';

import { Target, Clock, CheckCircle2, Code2, TrendingUp } from 'lucide-react';

// Type definition for learner profile
export interface LearnerProfile {
  parsed_goal: string;
  key_technologies: string[];
  difficulty_profile: string;
  time_constraint?: string;
  recommended_focus: string[];
  // Optional progress fields
  weekly_hours?: number;
  duration_months?: string;
  intensity_percent?: number;
  level_range?: string;
}

// Color mapping for technology badges - unified to Design System
const getTechColor = (tech: string): string => {
  const techLower = tech.toLowerCase();
  // Use Sage for primary tech
  if (
    techLower.includes('python') ||
    techLower.includes('fastapi') ||
    techLower.includes('pydantic') ||
    techLower.includes('react') ||
    techLower.includes('next') ||
    techLower.includes('typescript')
  ) {
    return 'bg-sage-100 text-sage-800 border-sage-200';
  }
  // Use Muted/Secondary for others to maintain editorial feel
  return 'bg-muted text-muted-foreground border-border';
};

interface ProfileSidebarProps {
  profile: LearnerProfile;
  className?: string;
}

export function ProfileSidebar({ profile, className = '' }: ProfileSidebarProps) {
  const weeklyHours = profile.weekly_hours ?? 10;
  const durationMonths = profile.duration_months ?? '4-6 months';
  const intensityPercent = profile.intensity_percent ?? 65;
  const levelRange = profile.level_range ?? 'Beginner → Intermediate';

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Card 1: Learning Goal (North Star) - Enhanced */}
      <div className="relative overflow-hidden bg-gradient-to-br from-sage-50 via-background to-background rounded-2xl border border-sage-200 p-4 shadow-sm">
        <div className="absolute top-0 right-0 w-32 h-32 bg-sage-100/50 rounded-full blur-3xl" />

        <div className="relative">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-sage text-primary-foreground rounded-lg flex items-center justify-center shadow-sm">
              <Target size={16} />
            </div>
            <h3 className="text-base font-serif font-bold text-foreground">Learning Goal</h3>
          </div>
          <p className="font-serif text-sm text-foreground/80 leading-relaxed">
            {profile.parsed_goal}
          </p>
        </div>
      </div>

      {/* Card 2: Tech Stack (Tags Cloud) - Colored Badges */}
      <div className="bg-card rounded-2xl border border-border p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Code2 size={16} className="text-sage" />
          <h3 className="text-base font-serif font-bold text-foreground">Key Technologies</h3>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {profile.key_technologies.map((tech, index) => (
            <span
              key={index}
              className={`px-2.5 py-1 border rounded-md text-[10px] font-medium hover:bg-sage-50 transition-colors ${getTechColor(tech)}`}
            >
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Card 3: Profile & Constraints */}
      <div className="bg-card rounded-2xl border border-border p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp size={16} className="text-sage" />
          <h3 className="text-base font-serif font-bold text-foreground">Learning Profile</h3>
        </div>

        {/* Time Commitment */}
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Clock size={14} className="text-muted-foreground" />
            <span className="text-xs font-semibold text-foreground">Time Commitment</span>
          </div>
          <p className="text-xs text-muted-foreground mb-1.5">
            {weeklyHours} hours per week · {durationMonths}
          </p>
          <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-sage h-full rounded-full transition-all"
              style={{ width: `${intensityPercent}%` }}
            />
          </div>
          <p className="text-[10px] text-muted-foreground mt-1">
            {intensityPercent < 40 ? 'Low' : intensityPercent < 70 ? 'Medium' : 'High'} intensity
          </p>
        </div>

        {/* Difficulty */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-foreground">Difficulty Level</span>
            <span className="px-1.5 py-0.5 bg-sage-100 text-sage-800 text-[10px] font-medium rounded-md">
              {levelRange}
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            {profile.difficulty_profile}
          </p>
        </div>
      </div>

      {/* Card 4: Focus Areas (Checklist) */}
      <div className="bg-card rounded-2xl border border-border p-4 shadow-sm">
        <h3 className="text-base font-serif font-bold text-foreground mb-3">Recommended Focus</h3>
        <div className="space-y-2">
          {profile.recommended_focus.map((focus, index) => (
            <div key={index} className="flex items-start gap-2">
              <CheckCircle2 size={14} className="text-sage flex-shrink-0 mt-0.5" />
              <span className="text-xs text-foreground/80 leading-relaxed">{focus}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ProfileSidebar;

