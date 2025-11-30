import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Check } from 'lucide-react';

export default function PricingPage() {
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
          <Link href="/app/new">
            <Button variant="sage" size="sm">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </Link>
          <h1 className="text-5xl font-serif font-bold text-foreground mb-6">
            Simple Pricing
          </h1>
          <p className="text-xl text-muted-foreground">
            Start learning for free. Upgrade when you need more.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-8">
          <PricingCard
            name="Free"
            price="$0"
            description="Perfect for getting started"
            features={[
              '1 active roadmap',
              'Basic tutorials',
              'Community support',
              'Limited AI modifications',
            ]}
            buttonText="Get Started"
            buttonVariant="outline"
          />
          <PricingCard
            name="Pro"
            price="$19"
            period="/month"
            description="For serious learners"
            features={[
              'Unlimited roadmaps',
              'Full tutorial access',
              'Priority support',
              'Unlimited AI modifications',
              'Export to PDF/Markdown',
              'Progress tracking',
            ]}
            buttonText="Start Pro Trial"
            buttonVariant="sage"
            highlighted
          />
          <PricingCard
            name="Team"
            price="$49"
            period="/month"
            description="For teams and organizations"
            features={[
              'Everything in Pro',
              'Team collaboration',
              'Admin dashboard',
              'Custom branding',
              'API access',
              'Dedicated support',
            ]}
            buttonText="Contact Sales"
            buttonVariant="outline"
          />
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-6 bg-card">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-foreground mb-12 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <FAQItem
              question="Can I cancel my subscription anytime?"
              answer="Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period."
            />
            <FAQItem
              question="What happens to my roadmaps if I downgrade?"
              answer="Your roadmaps are never deleted. On the free plan, you can view all existing roadmaps but can only have one active at a time."
            />
            <FAQItem
              question="Is there a student discount?"
              answer="Yes! Students with a valid .edu email get 50% off Pro plans. Contact support to apply."
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

function PricingCard({
  name,
  price,
  period,
  description,
  features,
  buttonText,
  buttonVariant,
  highlighted,
}: {
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  buttonText: string;
  buttonVariant: 'sage' | 'outline';
  highlighted?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-6 ${
        highlighted
          ? 'border-sage-600 bg-sage-50 ring-2 ring-sage-600'
          : 'border-border bg-background'
      }`}
    >
      {highlighted && (
        <span className="inline-block px-3 py-1 text-xs font-medium bg-sage-600 text-white rounded-full mb-4">
          Most Popular
        </span>
      )}
      <h3 className="text-xl font-serif font-semibold text-foreground">{name}</h3>
      <div className="mt-4 mb-2">
        <span className="text-4xl font-bold text-foreground">{price}</span>
        {period && <span className="text-muted-foreground">{period}</span>}
      </div>
      <p className="text-sm text-muted-foreground mb-6">{description}</p>
      <ul className="space-y-3 mb-8">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-2">
            <Check className="w-5 h-5 text-sage-600 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-foreground">{feature}</span>
          </li>
        ))}
      </ul>
      <Link href="/app/new" className="block">
        <Button variant={buttonVariant} className="w-full">
          {buttonText}
        </Button>
      </Link>
    </div>
  );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
  return (
    <div className="border-b border-border pb-6">
      <h3 className="text-lg font-serif font-semibold text-foreground mb-2">
        {question}
      </h3>
      <p className="text-muted-foreground">{answer}</p>
    </div>
  );
}

