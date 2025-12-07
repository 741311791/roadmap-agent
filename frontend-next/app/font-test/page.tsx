/**
 * 字体测试页面
 * 用于验证本地字体是否正确加载
 */

export default function FontTestPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-foreground">
            本地字体加载测试
          </h1>
          <p className="text-muted-foreground">
            验证 Noto Sans SC 和 Noto Serif SC 字体是否正确加载
          </p>
        </div>

        {/* Noto Sans SC Tests */}
        <section className="space-y-6 p-6 border rounded-lg">
          <h2 className="text-2xl font-bold text-sage-700">
            Noto Sans SC (思源黑体) - 正文字体
          </h2>
          
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-light (300)</p>
              <p className="font-light text-lg">
                轻盈优雅的中文排版 - The quick brown fox jumps over the lazy dog
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-normal (400) - 默认正文</p>
              <p className="font-normal text-lg">
                这是标准的正文字体，适合长篇阅读。人工智能正在改变我们的生活方式。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-medium (500)</p>
              <p className="font-medium text-lg">
                中等粗细的字体，适合副标题和强调文本。学习路线图生成系统。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-semibold (600)</p>
              <p className="font-semibold text-lg">
                半粗体字体，常用于卡片标题和导航。个性化学习路径规划。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-bold (700)</p>
              <p className="font-bold text-lg">
                粗体字体，用于主要标题和重要强调。AI驱动的教育创新平台。
              </p>
            </div>
          </div>
        </section>

        {/* Noto Serif SC Tests */}
        <section className="space-y-6 p-6 border rounded-lg">
          <h2 className="text-2xl font-serif font-bold text-sage-700">
            Noto Serif SC (思源宋体) - 标题字体
          </h2>
          
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-serif font-normal (400)</p>
              <p className="font-serif font-normal text-lg">
                宋体的优雅气质，适合标题和引用文本。知识改变命运。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-serif font-medium (500)</p>
              <p className="font-serif font-medium text-lg">
                中等粗细的宋体，兼具典雅与现代感。终身学习的重要性。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-serif font-semibold (600)</p>
              <p className="font-serif font-semibold text-lg">
                半粗宋体，适合重要标题。构建个性化学习体系。
              </p>
            </div>

            <div className="p-4 bg-muted rounded">
              <p className="text-xs text-muted-foreground mb-2">font-serif font-bold (700)</p>
              <p className="font-serif font-bold text-xl">
                粗宋体，最适合大标题。开启智能学习新时代
              </p>
            </div>
          </div>
        </section>

        {/* Mixed Usage Example */}
        <section className="space-y-6 p-6 border rounded-lg bg-sage-50">
          <h2 className="text-3xl font-serif font-bold text-charcoal">
            混合使用示例
          </h2>
          
          <div className="space-y-4">
            <h3 className="text-xl font-serif font-semibold text-sage-700">
              为什么选择 AI 学习助手？
            </h3>
            <p className="text-base leading-relaxed text-foreground">
              在这个快速变化的时代，传统的学习方式已经无法满足个性化的需求。
              我们的平台利用先进的人工智能技术，为每位学习者量身定制专属的学习路线图。
            </p>
            <ul className="space-y-2 ml-6">
              <li className="font-medium">✨ 智能分析学习目标和背景</li>
              <li className="font-medium">🎯 生成个性化学习路径</li>
              <li className="font-medium">📚 推荐优质学习资源</li>
              <li className="font-medium">💡 实时调整学习计划</li>
            </ul>
          </div>
        </section>

        {/* Technical Info */}
        <section className="p-6 border rounded-lg bg-blue-50">
          <h3 className="text-lg font-bold mb-4">🔍 开发者信息</h3>
          <div className="space-y-2 text-sm font-mono">
            <p>✅ 字体来源：本地托管 (public/fonts/)</p>
            <p>✅ 加载方式：@font-face (app/fonts.css)</p>
            <p>✅ Noto Sans SC 字重：300, 400, 500, 600, 700</p>
            <p>✅ Noto Serif SC 字重：400, 500, 600, 700</p>
            <p>✅ 字体格式：TrueType (.ttf)</p>
            <p>✅ 加载策略：font-display: swap</p>
          </div>
          <div className="mt-4 p-4 bg-white rounded">
            <p className="text-sm text-muted-foreground mb-2">
              打开浏览器开发者工具 (F12) → Network → 过滤 "font"
            </p>
            <p className="text-sm text-muted-foreground">
              你应该看到字体文件从 <code className="bg-gray-200 px-1 rounded">/fonts/</code> 路径加载
            </p>
          </div>
        </section>

        {/* Back Button */}
        <div className="text-center">
          <a
            href="/"
            className="inline-block px-6 py-3 bg-sage-600 text-white rounded-lg hover:bg-sage-700 transition-colors"
          >
            返回首页
          </a>
        </div>
      </div>
    </div>
  );
}

