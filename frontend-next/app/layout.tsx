import type { Metadata } from 'next';
import { Inter, Playfair_Display, Noto_Sans_SC, Noto_Serif_SC } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
});

// 思源黑体 - 用于正文和UI元素
const notoSansSC = Noto_Sans_SC({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-noto-sans-sc',
  display: 'swap',
});

// 思源宋体 - 用于标题
const notoSerifSC = Noto_Serif_SC({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-serif-sc',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Muset - AI-Powered Learning Roadmap',
  description: 'Generate personalized learning roadmaps with AI agents',
  keywords: ['learning', 'roadmap', 'AI', 'education', 'personalized learning'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${playfair.variable} ${notoSansSC.variable} ${notoSerifSC.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

