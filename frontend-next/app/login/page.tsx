/**
 * 临时登录页面
 * 
 * 选择测试账号进行"登录"（开发模式）
 */
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/lib/store/auth-store';
import { authService } from '@/lib/services/auth-service';
import { Loader2, Info } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  
  const availableUsers = authService.getAvailableUsers();
  const redirectUrl = searchParams.get('redirect') || '/home';
  
  // 如果已登录，显示提示并延迟跳转（让用户看到反馈）
  useEffect(() => {
    if (isAuthenticated) {
      console.log('[Login] ✅ Already authenticated, will redirect to:', redirectUrl);
      // 延迟跳转，显示"您已登录"的状态
      const timer = setTimeout(() => {
        console.log('[Login] Redirecting now...');
        router.push(redirectUrl);
      }, 1500);
      
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, router, redirectUrl]);
  
  const handleLogin = (userId: string) => {
    setIsLoading(true);
    setSelectedUserId(userId);
    
    const success = login(userId);
    if (success) {
      console.log('[Login] Login successful, redirecting to:', redirectUrl);
      // 延迟一下，显示登录动画
      setTimeout(() => {
        router.push(redirectUrl);
      }, 500);
    } else {
      console.error('[Login] Login failed for user:', userId);
      setIsLoading(false);
      setSelectedUserId(null);
      alert('Login failed. Please try again.');
    }
  };
  
  // 如果已登录，显示"已登录"状态
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-50 via-background to-sage-50/30 p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader className="text-center space-y-4">
            <div className="text-5xl mb-2">✅</div>
            <CardTitle className="text-2xl font-serif font-bold text-charcoal">
              Already Logged In
            </CardTitle>
            <CardDescription className="text-base">
              Welcome back, {user.username}!<br />
              <span className="text-xs text-sage-600">Redirecting you now...</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center py-6">
            <Loader2 className="w-8 h-8 animate-spin text-sage-600" />
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-50 via-background to-sage-50/30 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-4">
          <div className="text-5xl mb-2">🎓</div>
          <CardTitle className="text-3xl font-serif font-bold text-charcoal">
            Welcome to Fast Learning
          </CardTitle>
          <CardDescription className="text-base">
            Select a test account to continue<br />
            <span className="text-xs text-sage-600">(Development Mode)</span>
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-3">
          {availableUsers.map((user) => (
            <Button
              key={user.id}
              variant="outline"
              className="w-full justify-start h-auto py-4 text-left hover:bg-sage-50 hover:border-sage-300 transition-all"
              onClick={() => handleLogin(user.id)}
              disabled={isLoading}
            >
              <div className="flex items-center gap-3 w-full">
                {/* Avatar */}
                <div className="text-4xl flex-shrink-0">
                  {user.avatar}
                </div>
                
                {/* User Info */}
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-foreground flex items-center gap-2">
                    {user.username}
                    {user.role === 'admin' && (
                      <span className="text-xs px-2 py-0.5 bg-sage-100 text-sage-700 rounded-full">
                        👑 Admin
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground truncate">
                    {user.email}
                  </div>
                </div>
                
                {/* Loading Indicator */}
                {isLoading && selectedUserId === user.id && (
                  <Loader2 className="w-5 h-5 animate-spin text-sage-600 flex-shrink-0" />
                )}
              </div>
            </Button>
          ))}
          
          {/* Info Footer */}
          <div className="pt-4 border-t mt-4">
            <div className="flex items-start gap-2 text-xs text-muted-foreground bg-blue-50 p-3 rounded-lg">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-600" />
              <p>
                This is a <strong>temporary development login</strong>. 
                Real user authentication with OAuth/JWT will be added in the future.
                No passwords are required or stored.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

