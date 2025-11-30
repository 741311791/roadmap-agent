import type { Config } from 'tailwindcss'
import { fontFamily } from 'tailwindcss/defaultTheme'

export default {
    darkMode: ['class'],
    content: [
        './index.html',
        './src/**/*.{js,ts,jsx,tsx}',
    ],
    theme: {
        container: {
            center: true,
            padding: '2rem',
            screens: {
                '2xl': '1400px',
            },
        },
        extend: {
            colors: {
                /* ===== SHADCN/UI COLOR SYSTEM ===== */
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

                /* ===== CUSTOM: SAGE GREEN (Brand Accent) ===== */
                sage: {
                    DEFAULT: 'hsl(var(--sage))',
                    foreground: 'hsl(var(--primary-foreground))', // White text on sage
                    50: 'hsl(140 15% 95%)',  // Ultra light sage
                    100: 'hsl(140 15% 90%)', // Very light sage
                    200: 'hsl(140 15% 80%)', // Light sage
                    300: 'hsl(140 15% 70%)',
                    400: 'hsl(140 15% 60%)',
                    500: 'hsl(var(--sage))', // Default sage (55%)
                    600: 'hsl(140 15% 45%)',
                    700: 'hsl(140 15% 35%)',
                    800: 'hsl(140 15% 25%)',
                    900: 'hsl(140 15% 15%)', // Deep sage
                },

                /* ===== CHART COLORS ===== */
                chart: {
                    '1': 'hsl(var(--chart-1))',
                    '2': 'hsl(var(--chart-2))',
                    '3': 'hsl(var(--chart-3))',
                    '4': 'hsl(var(--chart-4))',
                    '5': 'hsl(var(--chart-5))',
                },
            },

            /* ===== TYPOGRAPHY: EDITORIAL FONTS ===== */
            fontFamily: {
                sans: ['Inter', ...fontFamily.sans],
                serif: ['Playfair Display', ...fontFamily.serif],
            },

            /* ===== BORDER RADIUS ===== */
            borderRadius: {
                lg: 'var(--radius)',      // 0.5rem
                md: 'calc(var(--radius) - 2px)',
                sm: 'calc(var(--radius) - 4px)',
            },

            /* ===== ANIMATIONS (Editorial subtle movements) ===== */
            keyframes: {
                'fade-in': {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'slide-in-right': {
                    '0%': { transform: 'translateX(100%)' },
                    '100%': { transform: 'translateX(0)' },
                },
                'accordion-down': {
                    from: { height: '0' },
                    to: { height: 'var(--radix-accordion-content-height)' },
                },
                'accordion-up': {
                    from: { height: 'var(--radix-accordion-content-height)' },
                    to: { height: '0' },
                },
            },
            animation: {
                'fade-in': 'fade-in 0.5s ease-out',
                'slide-in-right': 'slide-in-right 0.3s ease-out',
                'accordion-down': 'accordion-down 0.2s ease-out',
                'accordion-up': 'accordion-up 0.2s ease-out',
            },
        },
    },
    plugins: [
        require('tailwindcss-animate'),
        require('@tailwindcss/typography'),
    ],
} satisfies Config
