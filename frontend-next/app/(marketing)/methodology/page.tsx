import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Brain, Users, Sparkles, Target, BookOpen, MessageSquare } from 'lucide-react';

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-background bg-noise">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold">
              M
            </div>
            <span className="font-serif font-bold text-xl">Muset</span>
          </Link>
          <Link href="/new">
            <Button variant="sage" size="sm">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </Link>
          <h1 className="text-5xl font-serif font-bold text-foreground mb-6">
            Our Methodology
          </h1>
          <p className="text-xl text-muted-foreground leading-relaxed">
            Muset uses a sophisticated multi-agent system to create personalized
            learning experiences. Here&apos;s how our AI agents work together to help
            you learn effectively.
          </p>
        </div>
      </section>

      {/* Agent Architecture */}
      <section className="py-16 px-6 bg-card">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-foreground mb-12 text-center">
            Multi-Agent Architecture
          </h2>
          <div className="grid gap-8">
            <AgentCard
              icon={Brain}
              name="Intent Analyzer"
              role="A1"
              description="Analyzes your learning goals, extracts key technologies, and creates a difficulty profile based on your background and time constraints."
            />
            <AgentCard
              icon={Target}
              name="Curriculum Architect"
              role="A2"
              description="Designs a structured roadmap with stages, modules, and concepts. Ensures logical progression and prerequisite relationships."
            />
            <AgentCard
              icon={BookOpen}
              name="Tutorial Generator"
              role="A4"
              description="Creates in-depth tutorials for each concept with theory, examples, and exercises tailored to your learning preferences."
            />
            <AgentCard
              icon={Users}
              name="Resource Recommender"
              role="A5"
              description="Finds and curates the best external resources - articles, videos, courses, and tools - for each topic."
            />
            <AgentCard
              icon={Sparkles}
              name="Quiz Generator"
              role="A6"
              description="Creates quizzes with various question types to test your understanding and reinforce learning."
            />
            <AgentCard
              icon={MessageSquare}
              name="Modification Agents"
              role="A7+"
              description="Allow you to modify tutorials, resources, and quizzes through natural language chat."
            />
          </div>
        </div>
      </section>

      {/* Process Flow */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-foreground mb-12 text-center">
            The Learning Process
          </h2>
          <div className="space-y-6">
            <ProcessStep
              number={1}
              title="Share Your Goals"
              description="Tell us what you want to learn, your current level, available time, and preferred learning style."
            />
            <ProcessStep
              number={2}
              title="AI Designs Your Path"
              description="Our agents collaborate to create a personalized curriculum with clear milestones and dependencies."
            />
            <ProcessStep
              number={3}
              title="Learn at Your Pace"
              description="Work through tutorials, complete quizzes, and explore curated resources in the order that works for you."
            />
            <ProcessStep
              number={4}
              title="Adapt and Refine"
              description="Chat with AI to modify content, get explanations, or adjust the curriculum as your needs evolve."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs">
              M
            </div>
            <span className="font-serif font-semibold">Muset</span>
          </div>
          <span className="text-sm text-muted-foreground">
            © 2024 Muset. All rights reserved.
          </span>
        </div>
      </footer>
    </div>
  );
}

function AgentCard({
  icon: Icon,
  name,
  role,
  description,
}: {
  icon: React.ElementType;
  name: string;
  role: string;
  description: string;
}) {
  return (
    <div className="flex gap-6 p-6 rounded-xl border border-border bg-background">
      <div className="flex-shrink-0">
        <div className="w-14 h-14 rounded-lg bg-sage-100 flex items-center justify-center">
          <Icon className="w-7 h-7 text-sage-600" />
        </div>
      </div>
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-xl font-serif font-semibold text-foreground">
            {name}
          </h3>
          <span className="px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground rounded">
            {role}
          </span>
        </div>
        <p className="text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function ProcessStep({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-6">
      <div className="flex-shrink-0">
        <div className="w-10 h-10 rounded-full bg-sage-600 text-white flex items-center justify-center font-serif font-bold">
          {number}
        </div>
      </div>
      <div>
        <h3 className="text-xl font-serif font-semibold text-foreground mb-2">
          {title}
        </h3>
        <p className="text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

