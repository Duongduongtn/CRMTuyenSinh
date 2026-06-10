import type { Config } from 'tailwindcss'

// CRM SPA dùng cùng design tokens với FE public (docs/02-design-system.md):
// emerald accent, ink/paper palette, out-expo easing, Be Vietnam Pro.
// 1 accent duy nhất, KHÔNG gradient, KHÔNG shadow nặng.

export default <Config>{
  content: [
    './index.html',
    './src/**/*.{vue,ts}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      colors: {
        ink: {
          DEFAULT: '#0F1F1A',
          60: '#56635E',
          40: '#8A958F',
          20: '#B8C0BC',
        },
        paper: {
          DEFAULT: '#FFFFFF',
          alt: '#F7FAF9',
          tint: '#F0FAF4',
        },
        line: {
          soft: '#EDF1EF',
          base: '#E0E6E3',
          strong: '#0F1F1A',
        },
        brand: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          200: '#BBF7D0',
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D',
          800: '#166534',
          900: '#14532D',
          950: '#052E16',
        },
        warm: { amber: '#D97706' },
        danger: { DEFAULT: '#B91C1C', soft: '#FEE2E2' },
        success: { DEFAULT: '#15803D', soft: '#DCFCE7' },
        warning: { DEFAULT: '#B45309', soft: '#FEF3C7' },
        info: { DEFAULT: '#0E7490', soft: '#CFFAFE' },
      },
      borderRadius: {
        sm: '0.375rem',
        md: '0.625rem',
        lg: '1rem',
        xl: '1.25rem',
        '2xl': '1.5rem',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      transitionDuration: {
        DEFAULT: '300ms',
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.035em',
        tight: '-0.025em',
        wider: '0.14em',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      animation: {
        'fade-in': 'fade-in 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-right': 'slide-in-right 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
