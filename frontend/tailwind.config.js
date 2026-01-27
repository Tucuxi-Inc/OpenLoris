/** @type {import('tailwindcss').Config} */
export default {
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
      // Tufte-inspired color palette
      colors: {
        // Backgrounds
        cream: {
          DEFAULT: '#FFFEF8',
          50: '#FFFEF8',
          100: '#FAF9F6',
          200: '#F5F4F0',
        },
        // Text colors
        ink: {
          DEFAULT: '#1A1A1A',
          primary: '#1A1A1A',
          secondary: '#4A4A4A',
          tertiary: '#6B6B6B',
          muted: '#8B8B8B',
        },
        // Accent colors (used sparingly)
        loris: {
          DEFAULT: '#8B5A2B',
          brown: '#8B5A2B',
        },
        // Status colors (muted, not bright)
        status: {
          success: '#2E5E4E',
          warning: '#8B6914',
          error: '#8B2E2E',
        },
        // Rules and borders
        rule: {
          light: '#E5E4E0',
          medium: '#C5C4C0',
          dark: '#1A1A1A',
        },
        // shadcn/ui compatibility
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
      },
      // Typography - serif for body, mono for data
      fontFamily: {
        serif: ['Georgia', 'Times New Roman', 'Times', 'serif'],
        mono: ['IBM Plex Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      // Type scale
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.5' }],
        sm: ['0.875rem', { lineHeight: '1.5' }],
        base: ['1rem', { lineHeight: '1.75' }],
        lg: ['1.125rem', { lineHeight: '1.75' }],
        xl: ['1.25rem', { lineHeight: '1.5' }],
        '2xl': ['1.5rem', { lineHeight: '1.4' }],
        '3xl': ['1.875rem', { lineHeight: '1.3' }],
        '4xl': ['2.25rem', { lineHeight: '1.2' }],
      },
      // Subtle border radius (not pill-shaped)
      borderRadius: {
        sm: '2px',
        DEFAULT: '2px',
        md: '4px',
        lg: 'var(--radius)',
      },
      // Spacing scale
      spacing: {
        18: '4.5rem',
        22: '5.5rem',
      },
      // Max width for readable text
      maxWidth: {
        prose: '65ch',
      },
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
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.6s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
