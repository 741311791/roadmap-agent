# Editorial Design System - Quick Reference

## 🎨 Color Classes

| Element | Class | Example |
|---------|-------|---------|
| Background | `bg-background` | Page canvas (warm cream) |
| Text | `text-foreground` | Primary text (charcoal) |
| Muted Text | `text-muted-foreground` | Secondary info |
| Primary Button | `bg-primary text-primary-foreground` | Main CTAs |
| Sage Accent | `text-sage` or `bg-sage` | Brand highlights |
| Card | `bg-card` or `glass-panel` | Content containers |
| Border | `border-border` | Subtle separators |

## 📝 Typography

```tsx
// ✅ Headings - ALWAYS use serif
<h1 className="font-serif text-5xl">...</h1>
<h2 className="font-serif text-4xl">...</h2>
<h3 className="font-serif text-3xl">...</h3>

// Body text - Default sans (no need to specify)
<p className="text-foreground">...</p>
```

## 🔘 Button Patterns

```tsx
// Primary CTA
<button className="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-md">
  Sign Up
</button>

// Sage Accent
<button className="bg-sage text-white hover:bg-sage/90 px-6 py-3 rounded-md">
  Explore
</button>

// Ghost/Outline
<button className="border border-border hover:bg-muted px-6 py-3 rounded-md">
  Learn More
</button>
```

## 🪟 Components

```tsx
// Glass Panel
<div className="glass-panel p-6">
  <h3 className="font-serif text-2xl">Title</h3>
  <p className="text-muted-foreground">Description</p>
</div>

// Glass Input
<input className="glass-input w-full" placeholder="..." />
```

## 🟢 Sage Usage

Use sage for:
- Brand/product names: `<span className="text-sage">Concrete Path</span>`
- Keywords: `<span className="text-sage">strategic design</span>`
- Success states
- Hover accents

## 🚫 Don't Do

❌ Hardcoded colors: `bg-[#FFFCF9]`  
❌ Sans-serif headings: `<h1 className="font-sans">`  
❌ Random colors: `text-blue-500`  
❌ Pure black: `text-black`

## ✅ Always Do

✅ Use design tokens: `bg-background text-foreground`  
✅ Serif headings: `<h1 className="font-serif">`  
✅ Sage for brand: `text-sage`  
✅ Warm charcoal: `text-foreground`
