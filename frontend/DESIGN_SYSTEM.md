# Editorial Cream & Sage Design System Guidelines

## 🎨 Visual Identity

This project uses the **"Editorial/Old Money"** aesthetic — sophisticated, warm, minimalist, and authoritative, inspired by high-end newspaper and magazine design.

---

## 📐 Core Design Principles

### 1. **Always Use Design Tokens (No Hardcoded Values)**

❌ **NEVER:**
```tsx
<div className="bg-[#FFFCF9] text-[#1C1917]">
```

✅ **ALWAYS:**
```tsx
<div className="bg-background text-foreground">
```

### 2. **Typography Hierarchy**

**Headings (H1-H3):**
- **MUST** use `font-serif` (Playfair Display)
- Conveys editorial authority

```tsx
// ✅ Correct
<h1 className="font-serif text-5xl font-semibold">Editorial Title</h1>
<h2 className="font-serif text-4xl">Subheading</h2>

// ❌ Wrong
<h1 className="font-sans">Title</h1>
```

**Body Text:**
- Uses `font-sans` (Inter) by default
- No need to specify unless overriding

### 3. **Color Usage Rules**

| Element | Tailwind Class | Purpose |
|---------|---------------|----------|
| **Main Background** | `bg-background` | Warm cream canvas (#FFFCF9) |
| **Body Text** | `text-foreground` | Soft charcoal (#1C1917) |
| **Primary CTA** | `bg-primary text-primary-foreground` | Charcoal button with white text |
| **Sage Accent** | `text-sage` or `bg-sage` | For highlights, special keywords, or brand elements |
| **Muted Text** | `text-muted-foreground` | Secondary information |
| **Borders** | `border-border` | Subtle separators |

### 4. **Sage Green Accent Guidelines**

Use **Sage** (`text-sage`, `bg-sage`) for:
- Brand/product names (e.g., "Concrete Path")
- Important keywords or highlights
- Hover states on interactive elements
- Icons indicating success or positive actions

```tsx
// ✅ Strategic sage usage
<p className="text-foreground">
  Welcome to <span className="text-sage font-semibold">Concrete Path</span>
</p>

<button className="bg-sage text-white hover:bg-sage/90">
  Get Started
</button>
```

### 5. **Button Patterns**

**Primary CTA (Main Actions):**
```tsx
<button className="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-md font-medium">
  Sign Up
</button>
```

**Sage Accent Button (Special Actions):**
```tsx
<button className="bg-sage text-white hover:bg-sage/90 px-6 py-3 rounded-md font-medium">
  Explore Features
</button>
```

**Ghost/Outline (Secondary Actions):**
```tsx
<button className="bg-transparent border border-border hover:bg-muted px-6 py-3 rounded-md">
  Learn More
</button>
```

### 6. **Shape & Spacing**

- **Border Radius:** Use `rounded-md` or `rounded-lg` (NOT `rounded-full` unless intentional)
- **Padding:** Generous whitespace enhances the editorial feel
- **Shadows:** Use sparingly (`shadow-sm`) for subtle elevation

### 7. **Component Patterns**

**Glass Panel (Cards, Modals):**
```tsx
<div className="glass-panel p-6">
  <h3 className="font-serif text-2xl mb-4">Card Title</h3>
  <p className="text-muted-foreground">Description text</p>
</div>
```

**Input Fields:**
```tsx
<input 
  type="text" 
  className="glass-input w-full"
  placeholder="Enter your email"
/>
```

---

## 🚫 Anti-Patterns (Avoid These)

1. **Don't Use:** Generic tech colors (bright blue, purple gradients)
2. **Don't Use:** Pure black (`#000`) — use `text-foreground` instead
3. **Don't Use:** Fully rounded buttons (`rounded-full`) — keep it subtle
4. **Don't Use:** Heavy shadows or neon effects
5. **Don't Use:** Random color utilities like `text-blue-500`

---

## ✅ Quick Reference Checklist

Before committing a component:

- [ ] Headings use `font-serif`
- [ ] No hardcoded hex/RGB colors
- [ ] CTAs use `bg-primary` or `bg-sage`
- [ ] Text uses `text-foreground` or `text-muted-foreground`
- [ ] Borders use `border-border`
- [ ] Cards use `glass-panel` or `bg-card`
- [ ] Inputs use `glass-input` or proper border tokens

---

## 📚 Available Design Tokens

### Colors (via Tailwind)
- `bg-background`, `text-foreground`
- `bg-primary`, `text-primary-foreground`
- `bg-sage`, `text-sage` (Custom accent)
- `bg-muted`, `text-muted-foreground`
- `bg-card`, `text-card-foreground`
- `border-border`, `border-input`

### Typography
- `font-sans` — Inter (body text)
- `font-serif` — Playfair Display (headings)

### Utilities
- `glass-panel` — Semi-transparent card with backdrop blur
- `glass-input` — Elegant input with subtle background
- `btn-primary` — Primary button style
- `btn-sage` — Sage accent button
- `btn-ghost` — Outline/ghost button

---

## 🎯 Goal

Every component should feel like it belongs in a premium editorial publication — clean, sophisticated, and timeless.
