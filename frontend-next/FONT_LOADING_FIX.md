# Google Fonts 加载错误修复方案

## 问题描述
Next.js 启动时出现 `AbortError: The user aborted a request` 错误，原因是加载中文 Google Fonts 超时。

## 解决方案（按推荐顺序）

### 🎯 方案 1：禁用构建时字体预加载（最快，推荐用于开发）

修改 `app/layout.tsx`，为字体配置添加 `preload: false`：

```typescript
const notoSansSC = Noto_Sans_SC({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-noto-sans-sc',
  display: 'swap',
  preload: false,  // 👈 添加此行
});

const notoSerifSC = Noto_Serif_SC({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-serif-sc',
  display: 'swap',
  preload: false,  // 👈 添加此行
});
```

**优点**：
- 立即解决启动问题
- 字体仍会在浏览器端加载
- 不影响功能

**缺点**：
- 首次加载时可能有轻微的字体闪烁（FOUT）

---

### 🌐 方案 2：使用中文 CDN 镜像（推荐用于生产）

使用国内可访问的字体 CDN：

1. 在 `public/fonts/` 目录创建字体文件（如果有本地字体）
2. 或使用 CSS 方式加载字体：

```typescript
// app/layout.tsx
// 移除 next/font/google 的中文字体导入

// 在 globals.css 中添加：
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;500;600;700&display=swap');

// 或使用 CDN 镜像（推荐）：
@import url('https://fonts.loli.net/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;500;600;700&display=swap');
```

---

### ⚙️ 方案 3：增加超时时间

在 `next.config.js` 中配置：

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 增加字体加载超时时间
  experimental: {
    fetchTimeout: 60000, // 60 秒
  },
  
  // ... 其他配置
};
```

---

## 快速修复命令（方案 1）

直接应用方案 1，无需手动编辑：

```bash
# 由 AI 助手执行
```

## 验证

修复后运行：
```bash
npm run dev
```

应该可以正常启动，没有 AbortError。

## 后续优化建议

对于生产环境，建议：
1. 使用本地托管的字体文件
2. 只加载需要的字重
3. 使用 `font-display: swap` 确保文本始终可见
4. 考虑使用系统字体作为回退

