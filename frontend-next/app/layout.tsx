import type { Metadata } from 'next';
import { Inter, Playfair_Display } from 'next/font/google';
import './globals.css';
import './fonts.css'; // 本地字体配置
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  preload: true, // 启用预加载，减少字体延迟
  adjustFontFallback: true, // 自动计算回退字体，避免布局偏移
});

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
  preload: true, // 启用预加载
  adjustFontFallback: true,
});

// 中文字体现在通过 fonts.css 从本地加载
// 不再需要从 Google Fonts 导入

export const metadata: Metadata = {
  title: 'Fast Learning - Master Any Skill with AI',
  description: 'Master any skill in record time with AI-powered personalized learning roadmaps',
  keywords: ['fast learning', 'roadmap', 'AI', 'education', 'personalized learning', 'skill mastery'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${playfair.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

