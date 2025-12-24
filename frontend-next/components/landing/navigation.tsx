'use client';

/**
 * 导航栏组件 - 基于 Magic UI 风格
 * 
 * 特点：
 * - 响应式设计
 * - 固定在顶部
 * - 毛玻璃效果
 * - 使用 Fast Learning logo
 */

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-card/90 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
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

        {/* Desktop Menu */}
        <div className="hidden md:flex items-center gap-8">
          <Link
            href="/methodology"
            className="text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
          >
            Methodology
          </Link>
          <Link
            href="/pricing"
            className="text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
          >
            Pricing
          </Link>
          <Link
            href="/about"
            className="text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
          >
            About
          </Link>
          <Link href="/login">
            <Button
              variant="outline"
              size="sm"
              className="btn-ghost"
            >
              Login
            </Button>
          </Link>
        </div>

        {/* Mobile Menu Toggle */}
        <button
          className="md:hidden p-2 text-muted-foreground hover:text-sage transition-colors"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden bg-card border-t border-border"
          >
            <div className="px-6 py-4 space-y-4">
              <Link
                href="/methodology"
                className="block text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Methodology
              </Link>
              <Link
                href="/pricing"
                className="block text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Pricing
              </Link>
              <Link
                href="/about"
                className="block text-sm font-medium text-muted-foreground hover:text-sage transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                About
              </Link>
              <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button
                  variant="outline"
                  className="w-full btn-ghost"
                >
                  Login
                </Button>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

