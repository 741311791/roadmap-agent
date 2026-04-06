import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
    // Streamdown 在 dist 内拼接 Tailwind 类名，需纳入扫描（与官方 DeerFlow 对 streamdown 的 @source 一致）
    './node_modules/streamdown/dist/**/*.js',
  ],
  theme: {
    extend: {
      // Editorial Cream & Sage Color System
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        /** Streamdown 代码块工具栏/外壳使用 bg-sidebar、border-sidebar（shadcn 语义） */
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar))',
          foreground: 'hsl(var(--sidebar-foreground))',
          border: 'hsl(var(--sidebar-border))',
        },
        // Custom Sage Green Palette
        sage: {
          50: '#f6f7f6',
          100: '#e3e7e3',
          200: '#c7d0c7',
          300: '#a3b1a3',
          400: '#7d8f7d',
          500: '#607560',
          600: '#4c5d4c',
          700: '#3f4c3f',
          800: '#353f35',
          900: '#2e362e',
        },
        // Charcoal for text
        charcoal: {
          DEFAULT: '#1C1917',
          light: '#44403c',
        },
      },
      // Typography with Chinese support
      // 统一使用 Noto Sans SC 作为中文字体，避免视觉割裂
      fontFamily: {
        sans: [
          'var(--font-inter)',
          'Noto Sans SC', // 本地字体 - 统一的中文字体
          '-apple-system',
          'BlinkMacSystemFont',
          'system-ui',
          'sans-serif',
        ],
        serif: [
          'var(--font-playfair)',
          'Noto Sans SC', // 中文也使用 Noto Sans SC，保持一致性
          'Georgia',
          'serif',
        ],
      },
      // Border Radius
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      // Animations
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-in-from-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        'slide-in-from-left': {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'translateX(0)' },
        },
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'pulse-slow': {
          '0%, 100%': { 
            opacity: '1',
            transform: 'scale(1)',
          },
          '50%': { 
            opacity: '0.85',
            transform: 'scale(1.02)',
          },
        },
        'shine': {
          '0%': { 'background-position': '0% 0%' },
          '50%': { 'background-position': '100% 100%' },
          '100%': { 'background-position': '0% 0%' },
        },
        /** Deer-Flow 官方 StreamingIndicator 同款圆点跳动 */
        bouncing: {
          to: {
            opacity: '0.1',
            transform: 'translateY(-8px)',
          },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-in-out',
        'slide-in-right': 'slide-in-from-right 0.3s ease-out',
        'slide-in-left': 'slide-in-from-left 0.3s ease-out',
        'pulse-subtle': 'pulse-subtle 2s ease-in-out infinite',
        'pulse-slow': 'pulse-slow 2.5s ease-in-out infinite',
        'shine': 'shine var(--duration) infinite linear',
        bouncing: 'bouncing 0.5s infinite alternate',
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
    require('@tailwindcss/typography'),
  ],
};

export default config;

