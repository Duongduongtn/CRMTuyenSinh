import type { Config } from 'tailwindcss'

// Cùng tokens với FE public — giữ design consistency.
// 1 accent emerald, 1 ink/paper palette, font Be Vietnam Pro cho tiếng Việt.

export default <Config>{
  content: [
    './app.vue',
    './error.vue',
    './components/**/*.{vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './assets/**/*.css',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
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
      maxWidth: {
        narrow: '480px',
        base: '640px',
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.035em',
        tight: '-0.025em',
      },
    },
  },
  plugins: [],
}
