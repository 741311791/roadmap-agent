'use client';

import { useState } from 'react';
import { ProfileSidebar, type LearnerProfile } from '@/components/profile';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  User,
  Mail,
  Calendar,
  Award,
  BookOpen,
  Clock,
  TrendingUp,
  Edit3,
  CheckCircle2,
} from 'lucide-react';

// Mock user data - in real app, this would come from API/auth
const mockUser = {
  name: 'Learner',
  email: 'learner@example.com',
  joinedAt: '2024-09-15T00:00:00Z',
  plan: 'Free',
  totalRoadmaps: 3,
  completedRoadmaps: 1,
  totalHoursLearned: 45,
  conceptsMastered: 26,
  currentStreak: 7,
  longestStreak: 14,
};

// Mock learner profile - in real app, this would come from the current roadmap or user preferences
const mockLearnerProfile: LearnerProfile = {
  parsed_goal:
    '从零开始学习 Python Web 开发，重点掌握 FastAPI 和异步编程，最终能够独立开发一个完整的 Web 应用以支持职业转型',
  key_technologies: [
    'Python',
    'FastAPI',
    'async/await',
    'RESTful API',
    'Pydantic',
    'SQLAlchemy',
    'PostgreSQL',
    'JWT 认证',
  ],
  difficulty_profile:
    '编程初学者，有市场营销背景但无技术经验，需从基础入手，循序渐进学习',
  recommended_focus: [
    'Python 基础语法与函数式编程',
    'FastAPI 核心概念与路由设计',
    '异步编程原理与实践',
    '数据库集成与数据模型设计',
    '用户认证与 API 安全',
    '构建并部署完整 Web 项目',
  ],
  weekly_hours: 10,
  duration_months: '4-6 months',
  intensity_percent: 65,
  level_range: 'Beginner → Intermediate',
};

// Format date consistently
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-sage-200 to-sage-400 flex items-center justify-center text-white font-serif font-bold text-3xl shadow-lg">
            {mockUser.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold text-foreground">{mockUser.name}</h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Mail size={14} />
                {mockUser.email}
              </span>
              <span className="flex items-center gap-1">
                <Calendar size={14} />
                Joined {formatDate(mockUser.joinedAt)}
              </span>
            </div>
            <Badge variant="sage" className="mt-2">
              {mockUser.plan} Plan
            </Badge>
          </div>
        </div>
        <Button variant="outline" className="gap-2">
          <Edit3 size={16} /> Edit Profile
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard icon={BookOpen} label="Roadmaps" value={mockUser.totalRoadmaps} />
        <StatCard icon={CheckCircle2} label="Completed" value={mockUser.completedRoadmaps} />
        <StatCard icon={Clock} label="Hours Learned" value={mockUser.totalHoursLearned} />
        <StatCard icon={Award} label="Concepts Mastered" value={mockUser.conceptsMastered} />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="learning">Learning Profile</TabsTrigger>
          <TabsTrigger value="achievements">Achievements</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-3 gap-6">
            {/* Learning Streak */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-serif flex items-center gap-2">
                  <TrendingUp size={18} className="text-sage" />
                  Learning Streak
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-4">
                  <p className="text-5xl font-bold text-sage-600">{mockUser.currentStreak}</p>
                  <p className="text-sm text-muted-foreground mt-1">days in a row</p>
                  <p className="text-xs text-muted-foreground mt-4">
                    Best: {mockUser.longestStreak} days
                  </p>
                </div>
                {/* Weekly activity */}
                <div className="flex justify-center gap-1 mt-4">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => (
                    <div key={day} className="text-center">
                      <div
                        className={`w-8 h-8 rounded-lg ${
                          i < mockUser.currentStreak % 7
                            ? 'bg-sage-500'
                            : i === mockUser.currentStreak % 7
                            ? 'bg-sage-300'
                            : 'bg-muted'
                        }`}
                      />
                      <span className="text-[10px] text-muted-foreground">{day}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Progress Summary */}
            <Card className="col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-serif">Progress Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <ProgressItem
                    label="Full-Stack Web Development"
                    progress={33}
                    detail="8/24 concepts"
                  />
                  <ProgressItem
                    label="Python for Data Science"
                    progress={100}
                    detail="Completed"
                  />
                  <ProgressItem
                    label="System Design Basics"
                    progress={15}
                    detail="3/20 concepts"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Learning Profile Tab */}
        <TabsContent value="learning">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h2 className="text-xl font-serif font-bold mb-4">Your Learning Profile</h2>
              <p className="text-sm text-muted-foreground mb-6">
                This profile was generated based on your learning goals and preferences. It helps us
                personalize your roadmap content.
              </p>
              <ProfileSidebar profile={mockLearnerProfile} />
            </div>
            <div>
              <h2 className="text-xl font-serif font-bold mb-4">Preferences</h2>
              <Card>
                <CardContent className="pt-6 space-y-6">
                  <PreferenceItem
                    label="Learning Style"
                    value="Interactive & Project-based"
                    description="You prefer hands-on learning with real projects"
                  />
                  <PreferenceItem
                    label="Content Language"
                    value="中文 / English"
                    description="Bilingual content for better understanding"
                  />
                  <PreferenceItem
                    label="Difficulty Adjustment"
                    value="Auto-adapt"
                    description="Content difficulty adjusts based on your progress"
                  />
                  <PreferenceItem
                    label="Quiz Frequency"
                    value="After each concept"
                    description="Regular knowledge checks to reinforce learning"
                  />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Achievements Tab */}
        <TabsContent value="achievements">
          <div className="grid grid-cols-4 gap-4">
            <AchievementCard
              icon="🎯"
              title="First Steps"
              description="Complete your first concept"
              unlocked
            />
            <AchievementCard
              icon="🔥"
              title="On Fire"
              description="7-day learning streak"
              unlocked
            />
            <AchievementCard
              icon="📚"
              title="Bookworm"
              description="Complete 10 tutorials"
              unlocked
            />
            <AchievementCard
              icon="🏆"
              title="Roadmap Master"
              description="Complete a full roadmap"
              unlocked
            />
            <AchievementCard
              icon="💡"
              title="Quick Learner"
              description="Complete 5 concepts in one day"
              unlocked={false}
            />
            <AchievementCard
              icon="🌟"
              title="Perfectionist"
              description="Score 100% on 10 quizzes"
              unlocked={false}
            />
            <AchievementCard
              icon="🚀"
              title="Speed Runner"
              description="Finish roadmap under estimated time"
              unlocked={false}
            />
            <AchievementCard
              icon="🎓"
              title="Scholar"
              description="Complete 3 roadmaps"
              unlocked={false}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-sage-100 flex items-center justify-center">
            <Icon className="w-5 h-5 text-sage-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressItem({
  label,
  progress,
  detail,
}: {
  label: string;
  progress: number;
  detail: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">{detail}</span>
      </div>
      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            progress === 100 ? 'bg-green-500' : 'bg-sage-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

function PreferenceItem({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Badge variant="secondary">{value}</Badge>
    </div>
  );
}

function AchievementCard({
  icon,
  title,
  description,
  unlocked,
}: {
  icon: string;
  title: string;
  description: string;
  unlocked: boolean;
}) {
  return (
    <Card className={unlocked ? '' : 'opacity-50'}>
      <CardContent className="pt-6 text-center">
        <div className="text-4xl mb-2">{icon}</div>
        <h3 className="font-serif font-bold text-sm">{title}</h3>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
        {unlocked && (
          <Badge variant="success" className="mt-2">
            Unlocked
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}

