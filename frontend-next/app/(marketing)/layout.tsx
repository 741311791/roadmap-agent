/**
 * 营销页面布局
 * 用于首页、定价页、方法论页等公开页面
 */
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 营销页面使用简单的布局，不需要侧边栏等应用UI */}
      {children}
    </div>
  );
}


