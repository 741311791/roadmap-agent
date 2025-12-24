'use client';

/**
 * 站点导航栏 (Site Header)
 * 
 * 对应 Magic UI Pro Header 1 风格的实现：
 * - 固定顶部 + 毛玻璃效果
 * - 响应式布局
 * - 移动端侧边抽屉 (Sheet)
 * - 平滑动画
 */

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle, 
  SheetTrigger 
} from '@/components/ui/sheet';
import { Menu, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, useScroll, useMotionValueEvent } from 'motion/react';

const navLinks = [
  { name: 'Home', href: '/' },
  { name: 'Methodology', href: '/methodology' },
  { name: 'Pricing', href: '/pricing' },
  { name: 'About', href: '/about' },
];

export function SiteHeader() {
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);

  useMotionValueEvent(scrollY, "change", (latest) => {
    setIsScrolled(latest > 20);
  });

  return (
    <motion.header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 border-b transition-colors duration-200",
        isScrolled 
          ? "bg-background/80 backdrop-blur-md border-border supports-[backdrop-filter]:bg-background/60" 
          : "bg-transparent border-transparent"
      )}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Left: Logo */}
        <Link href="/" className="flex items-center gap-2 relative z-50">
          {/* Desktop: Icon + Text */}
          <div className="hidden md:flex items-center gap-2">
            <div className="relative w-9 h-9">
              <Image
                src="/logo/svg_noword.svg"
                alt="Logo"
                fill
                className="object-contain"
                priority
              />
            </div>
            <div className="relative w-40 h-8">
              <Image
                src="/logo/svg_onlyword.svg"
                alt="Fast Learning"
                fill
                className="object-contain object-left"
                priority
              />
            </div>
          </div>
          {/* Mobile: Icon Only */}
          <div className="relative w-8 h-8 md:hidden">
            <Image
              src="/logo/svg_noword.svg"
              alt="Fast Learning"
              fill
              className="object-contain"
              priority
            />
          </div>
        </Link>

        {/* Center: Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
            >
              {link.name}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-foreground transition-all duration-300 group-hover:w-full" />
            </Link>
          ))}
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Log in
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Trigger */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="w-5 h-5" />
                <span className="sr-only">Toggle menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] sm:w-[400px]">
              <SheetHeader>
                <SheetTitle className="text-left">
                  <div className="flex items-center gap-2">
                    <div className="relative w-8 h-8">
                      <Image
                        src="/logo/svg_noword.svg"
                        alt="Logo"
                        fill
                        className="object-contain"
                      />
                    </div>
                    <div className="relative w-36 h-7">
                      <Image
                        src="/logo/svg_onlyword.svg"
                        alt="Fast Learning"
                        fill
                        className="object-contain object-left"
                      />
                    </div>
                  </div>
                </SheetTitle>
              </SheetHeader>
              <div className="flex flex-col gap-6 mt-8">
                <nav className="flex flex-col gap-4">
                  {navLinks.map((link) => (
                    <Link
                      key={link.name}
                      href={link.href}
                      className="text-lg font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link.name}
                    </Link>
                  ))}
                </nav>
                <div className="flex flex-col gap-3 mt-auto">
                  <Link href="/login" className="w-full">
                    <Button variant="outline" className="w-full justify-center">
                      Log in
                    </Button>
                  </Link>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </motion.header>
  );
}

