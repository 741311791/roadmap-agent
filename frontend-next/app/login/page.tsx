'use client';

/**
 * 登录页面
 * 
 * 极简设计风格，支持邮箱+密码登录。
 */

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/lib/store/auth-store';
import { authService } from '@/lib/services/auth-service';
import { Loader2, Brain, AlertCircle, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, user } = useAuthStore();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const redirectUrl = searchParams.get('redirect') || '/home';
  
  // 如果已登录，跳转到目标页面
  useEffect(() => {
    if (isAuthenticated) {
      console.log('[Login] Already authenticated, redirecting to:', redirectUrl);
      router.push(redirectUrl);
    }
  }, [isAuthenticated, router, redirectUrl]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    // 基本验证
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const success = await authService.loginWithPassword(email, password);
      
      if (success) {
        console.log('[Login] Login successful, redirecting to:', redirectUrl);
        router.push(redirectUrl);
      } else {
        setError('Invalid email or password');
      }
    } catch (err: any) {
      console.error('[Login] Login error:', err);
      
      // 处理特定错误
      if (err.response?.status === 400) {
        const detail = err.response?.data?.detail;
        if (detail?.includes('expired')) {
          setError('Your temporary password has expired. Please contact the administrator for a new invitation.');
        } else if (detail?.includes('LOGIN_BAD_CREDENTIALS')) {
          setError('Invalid email or password');
        } else {
          setError(detail || 'Login failed');
        }
      } else if (err.response?.status === 422) {
        setError('Please enter a valid email address');
      } else {
        setError('Login failed. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  // 如果已登录，显示跳转状态
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8f5f0]">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Loader2 className="w-8 h-8 animate-spin text-sage-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting...</p>
        </motion.div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen flex flex-col bg-[#f8f5f0]">
      {/* 背景纹理 */}
      <div className="fixed inset-0 opacity-[0.02] bg-noise -z-10" />
      
      {/* 顶部导航 */}
      <nav className="fixed top-0 left-0 right-0 z-50 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link 
            href="/" 
            className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>
        </div>
      </nav>
      
      {/* 主内容区域 */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-[400px]"
        >
          {/* Logo 和标题 */}
          <div className="text-center mb-10">
            <Link href="/" className="inline-flex items-center gap-2.5 group mb-6">
              <div className="w-12 h-12 bg-sage-500 rounded-full flex items-center justify-center shadow-sm group-hover:shadow-md transition-all">
                <Brain className="w-6 h-6 text-white" />
              </div>
            </Link>
            <h1 className="text-3xl font-serif font-bold text-foreground mb-2">
              Welcome Back
            </h1>
            <p className="text-muted-foreground">
              Sign in to continue your learning journey
            </p>
          </div>
          
          {/* 登录表单卡片 */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-sage-200/50 p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* 错误提示 */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl text-red-700"
                >
                  <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm">{error}</p>
                </motion.div>
              )}
              
              {/* 邮箱输入 */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-foreground">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className="h-12 px-4 bg-white border-sage-200 focus:border-sage-400 focus:ring-sage-400/20 rounded-xl"
                  autoComplete="email"
                  autoFocus
                />
              </div>
              
              {/* 密码输入 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-foreground">
                    Password
                  </Label>
                  {/* 暂时隐藏忘记密码链接 */}
                  {/* <Link 
                    href="/forgot-password" 
                    className="text-xs text-sage-600 hover:text-sage-700 transition-colors"
                  >
                    Forgot password?
                  </Link> */}
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  className="h-12 px-4 bg-white border-sage-200 focus:border-sage-400 focus:ring-sage-400/20 rounded-xl"
                  autoComplete="current-password"
                />
              </div>
              
              {/* 登录按钮 */}
              <Button
                type="submit"
                variant="sage"
                className="w-full h-12 rounded-xl font-semibold text-base shadow-sm hover:shadow-md transition-all"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>
            
            {/* Beta 提示 */}
            <div className="mt-6 pt-6 border-t border-sage-100">
              <p className="text-center text-xs text-muted-foreground">
                Fast Learning is currently in private beta.
                <br />
                <Link href="/" className="text-sage-600 hover:text-sage-700 transition-colors">
                  Join the waitlist
                </Link>
                {' '}to get early access.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
      
      {/* 底部 */}
      <footer className="py-6 text-center text-xs text-muted-foreground">
        © 2024 Fast Learning. All rights reserved.
      </footer>
    </div>
  );
}
