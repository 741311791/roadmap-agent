'use client';

/**
 * Footer 组件
 * 
 * 基于 Magic UI footer-5 设计
 * 包含 logo、链接、社交媒体和版权信息
 * 使用全局设计令牌
 */

import React from 'react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import Image from 'next/image';
import { Github, Twitter, MessageCircle } from 'lucide-react';

export function Footer() {
  const t = useTranslations('footer');
  const tMarketing = useTranslations('marketing');
  
  const navigation = {
    product: [
      { name: tMarketing('methodology'), href: '/methodology' },
      { name: tMarketing('pricing'), href: '/pricing' },
      { name: tMarketing('about'), href: '/about' },
    ],
    resources: [
      { name: t('documentation'), href: '#' },
      { name: t('blog'), href: '#' },
      { name: t('helpCenter'), href: '#' },
    ],
    legal: [
      { name: t('privacyPolicy'), href: '#' },
      { name: t('termsOfService'), href: '#' },
      { name: t('cookiePolicy'), href: '#' },
    ],
    social: [
      {
        name: 'GitHub',
        href: '#',
        icon: Github,
      },
      {
        name: 'Twitter',
        href: '#',
        icon: Twitter,
      },
      {
        name: 'Discord',
        href: '#',
        icon: MessageCircle,
      },
    ],
  };

  return (
    <footer className="bg-card border-t border-border">
      <div className="max-w-7xl mx-auto px-6 py-12 lg:py-16">
        {/* 主要内容 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 lg:gap-12 mb-8">
          {/* Logo 和描述 */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="relative w-40 h-24">
                <Image
                  src="/logo/svg_word.svg"
                  alt="Fast Learning"
                  fill
                  className="object-contain object-left"
                />
              </div>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">
              {t('description')}
            </p>
            {/* 社交媒体 */}
            <div className="flex items-center gap-4">
              {navigation.social.map((item) => {
                const Icon = item.icon;
                return (
                  <a
                    key={item.name}
                    href={item.href}
                    className="text-muted-foreground hover:text-sage transition-colors"
                    aria-label={item.name}
                  >
                    <Icon className="w-5 h-5" />
                  </a>
                );
              })}
            </div>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">{t('product')}</h3>
            <ul className="space-y-3">
              {navigation.product.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className="text-sm text-muted-foreground hover:text-sage transition-colors"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">{t('resources')}</h3>
            <ul className="space-y-3">
              {navigation.resources.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className="text-sm text-muted-foreground hover:text-sage transition-colors"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">{t('legal')}</h3>
            <ul className="space-y-3">
              {navigation.legal.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className="text-sm text-muted-foreground hover:text-sage transition-colors"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* 底部版权 */}
        <div className="pt-8 border-t border-border">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} {t('copyright')}
            </p>
            <p className="text-sm text-muted-foreground">
              {t('madeWith')}{' '}
              <span className="text-sage" aria-label="love">
                ♥
              </span>{' '}
              {t('forLearners')}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
