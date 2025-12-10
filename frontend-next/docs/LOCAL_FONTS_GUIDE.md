# 本地字体配置指南 - Noto Sans SC & Noto Serif SC

## 当前项目使用的字重

根据 `app/layout.tsx` 配置：

### Noto Sans SC（思源黑体）
```typescript
weight: ['300', '400', '500', '600', '700']
```

**需要的字体文件**：
- `NotoSansSC-Light.otf` (300) - 细体
- `NotoSansSC-Regular.otf` (400) - 常规体
- `NotoSansSC-Medium.otf` (500) - 中等粗细
- `NotoSansSC-SemiBold.otf` (600) - 半粗体
- `NotoSansSC-Bold.otf` (700) - 粗体

### Noto Serif SC（思源宋体）
```typescript
weight: ['400', '500', '600', '700']
```

**需要的字体文件**：
- `NotoSerifSC-Regular.otf` (400) - 常规体
- `NotoSerifSC-Medium.otf` (500) - 中等粗细
- `NotoSerifSC-SemiBold.otf` (600) - 半粗体
- `NotoSerifSC-Bold.otf` (700) - 粗体

---

## 🎯 推荐配置（优化版）

**建议只保留核心字重**，大幅减少文件体积：

### 最小配置（推荐）
```typescript
// Noto Sans SC - 只保留 3 个字重
weight: ['400', '600', '700']

// 需要的文件：
// - NotoSansSC-Regular.otf (400)
// - NotoSansSC-SemiBold.otf (600) 
// - NotoSansSC-Bold.otf (700)
```

```typescript
// Noto Serif SC - 只保留 2 个字重
weight: ['400', '700']

// 需要的文件：
// - NotoSerifSC-Regular.otf (400)
// - NotoSerifSC-Bold.otf (700)
```

**理由**：
- 400 (Regular) - 正文必需
- 600/700 (SemiBold/Bold) - 标题和强调
- 300 (Light) 和 500 (Medium) 使用较少，可以用 CSS 替代

**预期节省**：
- 中文字体每个文件约 10-15MB
- 减少 3 个字重 = 节省约 30-45MB

---

## 📁 文件结构

创建如下目录结构：

```
frontend-next/
├── public/
│   └── fonts/
│       ├── noto-sans-sc/
│       │   ├── NotoSansSC-Regular.otf
│       │   ├── NotoSansSC-SemiBold.otf
│       │   └── NotoSansSC-Bold.otf
│       └── noto-serif-sc/
│           ├── NotoSerifSC-Regular.otf
│           └── NotoSerifSC-Bold.otf
└── app/
    └── fonts.css  (新建)
```

---

## 🔧 配置步骤

### 步骤 1：创建字体目录并复制文件

```bash
# 创建目录
mkdir -p public/fonts/noto-sans-sc
mkdir -p public/fonts/noto-serif-sc

# 复制字体文件（根据你的下载位置调整路径）
# Noto Sans SC
cp ~/Downloads/Noto_Sans_SC/NotoSansSC-Regular.otf public/fonts/noto-sans-sc/
cp ~/Downloads/Noto_Sans_SC/NotoSansSC-SemiBold.otf public/fonts/noto-sans-sc/
cp ~/Downloads/Noto_Sans_SC/NotoSansSC-Bold.otf public/fonts/noto-sans-sc/

# Noto Serif SC
cp ~/Downloads/Noto_Serif_SC/NotoSerifSC-Regular.otf public/fonts/noto-serif-sc/
cp ~/Downloads/Noto_Serif_SC/NotoSerifSC-Bold.otf public/fonts/noto-serif-sc/
```

### 步骤 2：创建字体 CSS 文件

创建 `app/fonts.css`：

```css
/* Noto Sans SC - 思源黑体 */
@font-face {
  font-family: 'Noto Sans SC';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/noto-sans-sc/NotoSansSC-Regular.otf') format('opentype');
}

@font-face {
  font-family: 'Noto Sans SC';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/fonts/noto-sans-sc/NotoSansSC-SemiBold.otf') format('opentype');
}

@font-face {
  font-family: 'Noto Sans SC';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/fonts/noto-sans-sc/NotoSansSC-Bold.otf') format('opentype');
}

/* Noto Serif SC - 思源宋体 */
@font-face {
  font-family: 'Noto Serif SC';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/noto-serif-sc/NotoSerifSC-Regular.otf') format('opentype');
}

@font-face {
  font-family: 'Noto Serif SC';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/fonts/noto-serif-sc/NotoSerifSC-Bold.otf') format('opentype');
}
```

### 步骤 3：修改 `app/layout.tsx`

```typescript
import type { Metadata } from 'next';
import { Inter, Playfair_Display } from 'next/font/google';
import './globals.css';
import './fonts.css'; // 👈 导入本地字体
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

// 👇 移除 Google Fonts 的中文字体导入
// 不再需要 Noto_Sans_SC 和 Noto_Serif_SC

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
        className={`${inter.variable} ${playfair.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### 步骤 4：更新 `tailwind.config.ts`

确保 Tailwind 配置包含本地字体：

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'var(--font-inter)',
          'Noto Sans SC', // 👈 本地字体
          'system-ui',
          '-apple-system',
          'sans-serif',
        ],
        serif: [
          'var(--font-playfair)',
          'Noto Serif SC', // 👈 本地字体
          'serif',
        ],
      },
    },
  },
  plugins: [],
};

export default config;
```

---

## ✅ 验证

1. **重启开发服务器**：
```bash
npm run dev
```

2. **检查字体加载**：
   - 打开浏览器开发者工具 (F12)
   - 切换到 Network 标签
   - 过滤 "font"
   - 应该看到本地字体文件从 `/fonts/` 加载

3. **测试显示效果**：
   - 访问 http://localhost:3000
   - 检查中文字体是否正确显示
   - 尝试不同字重的文本

---

## 🎨 字重使用建议

根据你的设计系统，建议使用方式：

| 字重 | 用途 | Tailwind 类 |
|------|------|-------------|
| 400 (Regular) | 正文、段落文字 | `font-normal` |
| 600 (SemiBold) | 子标题、卡片标题 | `font-semibold` |
| 700 (Bold) | 主标题、重要强调 | `font-bold` |

如果当前代码中使用了 300 或 500：
- `font-light` (300) → 改用 `font-normal` (400)
- `font-medium` (500) → 改用 `font-semibold` (600)

---

## 📦 文件大小对比

### Google Fonts 方案
- 运行时从 CDN 加载
- 首次加载可能较慢（尤其在国内）
- 5 个字重 × 2 个字体 = ~100-150MB 总下载量

### 本地字体方案（推荐配置）
- 3 个 Noto Sans SC 字重：~30-45MB
- 2 个 Noto Serif SC 字重：~20-30MB
- **总计：~50-75MB**
- ✅ 用户只下载一次
- ✅ 离线可用
- ✅ 加载速度快

---

## 🚀 性能优化建议

1. **启用字体子集化**（advanced）：
   使用 `fonttools` 工具只包含常用汉字：
   ```bash
   pip install fonttools brotli
   pyftsubset NotoSansSC-Regular.otf \
     --text-file=common-chars.txt \
     --output-file=NotoSansSC-Regular-subset.woff2 \
     --flavor=woff2
   ```

2. **使用 WOFF2 格式**：
   - 比 OTF/TTF 小 30-50%
   - 所有现代浏览器都支持

3. **添加 preload**：
   在 `app/layout.tsx` 中添加：
   ```typescript
   export default function RootLayout() {
     return (
       <html>
         <head>
           <link
             rel="preload"
             href="/fonts/noto-sans-sc/NotoSansSC-Regular.otf"
             as="font"
             type="font/otf"
             crossOrigin="anonymous"
           />
         </head>
         {/* ... */}
       </html>
     );
   }
   ```

---

## 常见问题

### Q: 字体文件太大怎么办？
A: 
1. 使用 WOFF2 格式而不是 OTF
2. 进行字体子集化
3. 只保留必需的字重（400, 600, 700）

### Q: 需要支持繁体中文吗？
A: Noto Sans SC/Serif SC 主要针对简体中文。如需繁体，使用 Noto Sans TC/Serif TC。

### Q: 如何确保 Tailwind 的 font-weight 正确映射？
A: Tailwind 的 font-weight 会自动匹配 `@font-face` 中声明的 `font-weight`。

---

## 总结

✅ **推荐方案**（最小配置）：
- Noto Sans SC: Regular (400), SemiBold (600), Bold (700)
- Noto Serif SC: Regular (400), Bold (700)
- 总共 5 个字体文件，约 50-75MB

这样配置既能满足设计需求，又能保持良好的性能！

