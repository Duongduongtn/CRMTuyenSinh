import type { Config } from 'tailwindcss'

// Tokens đồng bộ với wireframes-html/index.html + docs/02-design-system.md.
// 1 accent duy nhất (emerald/brand), 1 palette ink/paper, 1 radius scale,
// 1 easing duy nhất `out-expo` cho mọi motion (300ms base).

export default <Config>{
  content: [
    './app.vue',
    './components/**/*.{vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './assets/**/*.css',
  ],
  theme: {
    extend: {
      fontFamily: {
        // Be Vietnam Pro — tối ưu cho dấu tiếng Việt (ư, ơ, ờ, ễ, ặ, ỹ)
        // Geist ASCII fallback + system stack. Dấu phụ canh đúng baseline,
        // không cắt phần trên, hỗ trợ tabular-nums cho số tiền.
        sans: ['"Be Vietnam Pro"', '"Geist Sans"', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      colors: {
        // Ink: text 4 cấp độ dùng cho body/heading/meta/disabled
        ink: {
          DEFAULT: '#0F1F1A',
          60: '#56635E',
          40: '#8A958F',
          20: '#B8C0BC',
        },
        // Paper: 3 nền (default, alt subtle, tint accent nhẹ)
        paper: {
          DEFAULT: '#FFFFFF',
          alt: '#F7FAF9',
          tint: '#F0FAF4',
        },
        // Line: 3 border (soft, base, strong)
        line: {
          soft: '#EDF1EF',
          base: '#E0E6E3',
          strong: '#0F1F1A',
        },
        // Brand emerald — 1 accent duy nhất theo taste-skill
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
        narrow: '768px',
        base: '1240px',
        wide: '1440px',
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.035em',
        tight: '-0.025em',
        wider: '0.14em',
      },
    },
  },
  plugins: [],
}
