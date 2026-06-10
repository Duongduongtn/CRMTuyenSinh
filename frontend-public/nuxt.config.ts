// Nuxt 3 config — FE public CRM tuyển sinh lái xe.
// Mục tiêu: SSG (nuxt generate) cho landing + chi tiết khóa, SSR cho /dh/[token].
// Brand info đọc từ /api/site-settings — KHÔNG hardcode.

export default defineNuxtConfig({
  compatibilityDate: '2026-06-10',
  devtools: { enabled: true },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxt/image',
    '@vueuse/nuxt',
  ],

  // Self-host fonts + main CSS
  css: [
    '@fontsource/geist-sans/400.css',
    '@fontsource/geist-sans/500.css',
    '@fontsource/geist-sans/600.css',
    '@fontsource/geist-sans/700.css',
    '@fontsource/geist-sans/800.css',
    '@fontsource/geist-mono/400.css',
    '~/assets/css/main.css',
  ],

  // Public runtime config — đọc qua useRuntimeConfig() trong composables.
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3000',
      studentUrl: process.env.NUXT_PUBLIC_STUDENT_URL || 'http://localhost:3001',
    },
  },

  // SSG: pre-render landing + list khóa + 9 detail khóa. /dh/[token] để SSR.
  nitro: {
    prerender: {
      crawlLinks: true,
      routes: ['/', '/khoa-hoc', '/robots.txt', '/sitemap.xml'],
      // Fail-safe — không crash build nếu BE chưa chạy lúc generate
      failOnError: false,
      ignore: ['/dh'],
    },
  },

  // Route rules — /dh/* không SSG, render runtime
  routeRules: {
    '/': { prerender: true },
    '/khoa-hoc/**': { prerender: true },
    '/dh/**': { ssr: true, prerender: false },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'vi' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#047857' },
        { name: 'format-detection', content: 'telephone=no' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico' },
      ],
    },
    pageTransition: { name: 'fade', mode: 'out-in' },
  },

  image: {
    quality: 85,
    format: ['avif', 'webp', 'jpg'],
    screens: {
      xs: 360,
      sm: 480,
      md: 768,
      lg: 1024,
      xl: 1280,
      '2xl': 1536,
    },
    domains: ['images.unsplash.com', 'localhost'],
  },

  // Tailwind config nằm ở ./tailwind.config.ts
  tailwindcss: {
    cssPath: '~/assets/css/main.css',
    configPath: '~/tailwind.config.ts',
    viewer: false,
  },

  typescript: {
    strict: true,
  },
})
