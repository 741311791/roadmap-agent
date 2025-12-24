import { SiteHeader } from '@/components/landing/site-header';
import { Footer } from '@/components/landing/footer';

/**
 * 营销页面统一布局
 * 
 * 所有落地页子页面（首页、定价、方法论、关于等）共享此布局：
 * - 顶部导航栏 (SiteHeader)
 * - 主体内容区域 (children)
 * - 底部页脚 (Footer)
 */
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 统一导航栏 */}
      <SiteHeader />
      
      {/* 页面主体内容 */}
      <main className="flex-1">
        {children}
      </main>
      
      {/* 统一页脚 */}
      <Footer />
    </div>
  );
}


