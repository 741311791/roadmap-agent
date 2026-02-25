'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Check } from 'lucide-react';

export default function PricingPage() {
  const t = useTranslations('pricingPage');
  
  return (
    <div className="bg-background bg-noise">
      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-serif font-bold text-foreground mb-6">
            {t('title')}
          </h1>
          <p className="text-xl text-muted-foreground">
            {t('subtitle')}
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-8">
          <PricingCard
            name={t('free')}
            price={t('freePrice')}
            description={t('freeDesc')}
            features={[
              t('freeFeature1'),
              t('freeFeature2'),
              t('freeFeature3'),
              t('freeFeature4'),
            ]}
            buttonText={t('getStarted')}
            buttonVariant="outline"
          />
          <PricingCard
            name={t('pro')}
            price={t('proPrice')}
            period={t('perMonth')}
            description={t('proDesc')}
            features={[
              t('proFeature1'),
              t('proFeature2'),
              t('proFeature3'),
              t('proFeature4'),
              t('proFeature5'),
              t('proFeature6'),
            ]}
            buttonText={t('startProTrial')}
            buttonVariant="sage"
            highlighted
            highlightedText={t('mostPopular')}
          />
          <PricingCard
            name={t('team')}
            price={t('teamPrice')}
            period={t('perMonth')}
            description={t('teamDesc')}
            features={[
              t('teamFeature1'),
              t('teamFeature2'),
              t('teamFeature3'),
              t('teamFeature4'),
              t('teamFeature5'),
              t('teamFeature6'),
            ]}
            buttonText={t('contactSales')}
            buttonVariant="outline"
          />
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-6 bg-card">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-foreground mb-12 text-center">
            {t('faqTitle')}
          </h2>
          <div className="space-y-6">
            <FAQItem
              question={t('faq1Q')}
              answer={t('faq1A')}
            />
            <FAQItem
              question={t('faq2Q')}
              answer={t('faq2A')}
            />
            <FAQItem
              question={t('faq3Q')}
              answer={t('faq3A')}
            />
          </div>
        </div>
      </section>
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
  highlightedText,
}: {
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  buttonText: string;
  buttonVariant: 'sage' | 'outline';
  highlighted?: boolean;
  highlightedText?: string;
}) {
  return (
    <div
      className={`rounded-xl border p-6 ${
        highlighted
          ? 'border-sage-600 bg-sage-50 ring-2 ring-sage-600'
          : 'border-border bg-background'
      }`}
    >
      {highlighted && highlightedText && (
        <span className="inline-block px-3 py-1 text-xs font-medium bg-sage-600 text-white rounded-full mb-4">
          {highlightedText}
        </span>
      )}
      <h3 className="text-xl font-serif font-semibold text-foreground">{name}</h3>
      <div className="mt-4 mb-2">
        <span className="text-4xl font-bold text-foreground">{price}</span>
        {period && <span className="text-muted-foreground">{period}</span>}
      </div>
      <p className="text-sm text-muted-foreground mb-6">{description}</p>
      <ul className="space-y-3 mb-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start gap-2">
            <Check className="w-5 h-5 text-sage-600 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-foreground">{feature}</span>
          </li>
        ))}
      </ul>
      <Link href="/new" className="block">
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

