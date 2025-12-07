import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowRight, Sparkles, BookOpen, Users, Zap } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background bg-noise">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold">
              M
            </div>
            <span className="font-serif font-bold text-xl">Muset</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/methodology" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Methodology
            </Link>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Pricing
            </Link>
            <Link href="/home" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Home
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/home">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/new">
              <Button variant="sage" size="sm">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-sage-100 rounded-full text-sage-800 text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            AI-Powered Learning Paths
          </div>
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-serif font-bold text-foreground leading-tight mb-6">
            Master Any Skill with{' '}
            <span className="text-sage-600">Personalized</span> Roadmaps
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            Tell us what you want to learn. Our AI agents will craft a complete
            curriculum with tutorials, quizzes, and curated resources tailored
            to your goals.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/new">
              <Button variant="sage" size="lg" className="gap-2">
                Create Your Roadmap <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/methodology">
              <Button variant="outline" size="lg">
                Learn More
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6 bg-card">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-serif font-bold text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Our multi-agent system collaborates to create the perfect learning
              experience for you.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={BookOpen}
              title="Curriculum Design"
              description="AI architects analyze your goals and create a structured learning path with clear milestones."
            />
            <FeatureCard
              icon={Sparkles}
              title="Content Generation"
              description="Tutorial generators create in-depth content, while resource recommenders find the best learning materials."
            />
            <FeatureCard
              icon={Zap}
              title="Adaptive Learning"
              description="Chat with AI to modify content, get explanations, or adjust difficulty based on your progress."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-serif font-bold text-foreground mb-4">
            Start Learning Today
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Join thousands of learners who have accelerated their growth with
            personalized roadmaps.
          </p>
          <Link href="/new">
            <Button variant="sage" size="lg" className="gap-2">
              Create Free Roadmap <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
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
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="/methodology" className="hover:text-foreground transition-colors">
              Methodology
            </Link>
            <Link href="/pricing" className="hover:text-foreground transition-colors">
              Pricing
            </Link>
            <Link href="/home" className="hover:text-foreground transition-colors">
              Home
            </Link>
            <span>© 2024 Muset. All rights reserved.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl border border-border bg-background hover:shadow-md transition-shadow">
      <div className="w-12 h-12 rounded-lg bg-sage-100 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-sage-600" />
      </div>
      <h3 className="text-xl font-serif font-semibold text-foreground mb-2">
        {title}
      </h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

