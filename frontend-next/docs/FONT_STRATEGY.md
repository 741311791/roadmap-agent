# Font Strategy - 字体使用策略

## Overview

本项目采用统一的字体加载策略，确保英文和中文内容都有良好的视觉一致性。

## Font Configuration

### English Fonts (英文字体)

- **Sans-serif**: `Inter` - 用于正文、UI 元素
- **Serif**: `Playfair Display` - 用于标题、强调文本

### Chinese Fonts (中文字体)

- **统一字体**: `Noto Sans SC` (思源黑体) - **所有中文内容统一使用此字体**

## Why Noto Sans SC Only?

为避免视觉割裂感，我们决定：

1. ✅ **统一性**: 所有中文内容（无论在标题还是正文）都使用 Noto Sans SC
2. ✅ **可读性**: Noto Sans SC 作为无衬线字体，在各种字重下都有良好的可读性
3. ✅ **性能**: 减少字体文件加载，降低页面体积
4. ❌ **不使用 Noto Serif SC**: 避免中文衬线字体造成的视觉不一致

## Font Loading Strategy

### 1. Local Fonts (本地字体)

中文字体通过本地文件加载（`/public/fonts/`），包含以下字重：

```
Noto Sans SC:
  - Light (300)
  - Regular (400)
  - Medium (500)
  - SemiBold (600)
  - Bold (700)
```

配置文件：`app/fonts.css`

### 2. Google Fonts CDN

英文字体通过 Google Fonts CDN 加载：

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700;800&display=swap');
```

配置文件：`app/globals.css`

### 3. Font Fallback Chain (字体降级链)

在 `tailwind.config.ts` 中配置：

```typescript
fontFamily: {
  sans: [
    'var(--font-inter)',        // Google Fonts - 英文
    'Noto Sans SC',             // 本地字体 - 中文
    '-apple-system',            // 系统备选
    'BlinkMacSystemFont',
    'system-ui',
    'sans-serif',
  ],
  serif: [
    'var(--font-playfair)',     // Google Fonts - 英文标题
    'Noto Sans SC',             // 中文也使用 Noto Sans SC
    'Georgia',                  // 系统备选
    'serif',
  ],
}
```

## Usage in Components

### For Regular Text (正文)

```tsx
<p className="font-sans">
  This is English text. 这是中文文本。
</p>
```

- 英文显示为 `Inter`
- 中文显示为 `Noto Sans SC`

### For Headings (标题)

```tsx
<h1 className="font-serif">
  Heading Text 标题文本
</h1>
```

- 英文显示为 `Playfair Display` (衬线)
- 中文显示为 `Noto Sans SC` (无衬线) - **保持一致性**

### Font Weight Classes

```tsx
<div className="font-light">   {/* 300 */}
<div className="font-normal">  {/* 400 */}
<div className="font-medium">  {/* 500 */}
<div className="font-semibold">{/* 600 */}
<div className="font-bold">    {/* 700 */}
```

所有字重在 Noto Sans SC 中都有对应的字体文件。

## Typography Hierarchy

### Default Styles (在 globals.css 中定义)

```css
h1, h2, h3 {
  @apply font-serif font-semibold tracking-tight;
}

h4, h5, h6 {
  @apply font-serif font-medium;
}
```

**重要**: 虽然标题使用 `font-serif` class，但中文字符会自动降级到 `Noto Sans SC`，确保视觉一致性。

## Performance Optimization

### 1. Font Display Strategy

```css
font-display: swap;
```

使用 `swap` 策略，确保文本立即显示，避免 FOIT (Flash of Invisible Text)。

### 2. Preloading

在 `layout.tsx` 中启用预加载：

```typescript
const inter = Inter({
  preload: true,
  adjustFontFallback: true,
});
```

### 3. Subset Optimization

- Google Fonts 仅加载 Latin 子集
- 中文字体使用本地完整文件（无法进一步子集化）

## Maintenance

### Adding New Font Weights

如需添加新的 Noto Sans SC 字重：

1. 下载对应的 `.ttf` 文件到 `/public/fonts/`
2. 在 `app/fonts.css` 中添加 `@font-face` 声明
3. 确保 `font-weight` 值正确对应

### Removing Fonts

已删除的字体：
- ❌ Noto Serif SC (所有字重) - 2025-12-10

## Troubleshooting

### Issue: Chinese text looks different in titles vs body

**Solution**: 确认所有中文都使用 Noto Sans SC，不要混用其他字体。

### Issue: Font not loading

**Checklist**:
1. ✅ 检查字体文件是否存在于 `/public/fonts/`
2. ✅ 检查 `fonts.css` 中的路径是否正确
3. ✅ 清除浏览器缓存并重新加载
4. ✅ 检查开发者工具的 Network 面板

### Issue: Visual inconsistency

**Solution**: 所有组件都应通过 Tailwind 的 `font-sans` 或 `font-serif` 来使用字体，不要直接硬编码字体名称。

## Summary

- 🎯 **统一策略**: 所有中文使用 Noto Sans SC
- 🚀 **性能优化**: 本地加载 + CDN 结合
- 🎨 **视觉一致**: 避免字体混用造成割裂感
- 📦 **精简体积**: 移除不必要的字体文件

---

**Last Updated**: 2025-12-10
**Author**: Cursor AI

