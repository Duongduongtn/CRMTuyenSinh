// Nuxt 3 PWA — Học viên CRM tuyển sinh lái xe.
// CSR (không SSG), mobile-first, JWT auth qua localStorage.
// API base trỏ về Django dev local hoặc prod crm.<domain>/api.

export default defineNuxtConfig({
  compatibilityDate: '2026-06-10',
  devtools: { enabled: true },
  // SSR mặc định cho compatibility Nuxt 3.21 + Vite 7.
  // Auth gating chạy ở client-side (middleware đã `import.meta.client` check),
  // routes chỉ render shell trên server rồi hydrate.
  // KHÔNG prerender — học viên app cần dữ liệu động.
  routeRules: {
    '/**': { ssr: true, prerender: false },
  },

  modules: [
    '@nuxtjs/tailwindcss',
    '@vueuse/nuxt',
    '@vite-pwa/nuxt',
  ],

  css: [
    '@fontsource/be-vietnam-pro/400.css',
    '@fontsource/be-vietnam-pro/500.css',
    '@fontsource/be-vietnam-pro/600.css',
    '@fontsource/be-vietnam-pro/700.css',
    '~/assets/css/main.css',
  ],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
      publicUrl: process.env.NUXT_PUBLIC_PUBLIC_URL || 'http://localhost:3000',
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'vi' },
      title: 'Học viên · Trung tâm Đào tạo Lái xe',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover' },
        { name: 'theme-color', content: '#15803D' },
        { name: 'format-detection', content: 'telephone=no' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico' },
      ],
    },
    pageTransition: { name: 'slide', mode: 'out-in' },
  },

  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'Học viên Lái xe',
      short_name: 'HV Lái xe',
      description: 'Cổng học viên trung tâm đào tạo lái xe',
      theme_color: '#15803D',
      background_color: '#FFFFFF',
      display: 'standalone',
      orientation: 'portrait',
      scope: '/',
      start_url: '/',
      lang: 'vi-VN',
      icons: [
        { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
        { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
      ],
    },
    workbox: {
      navigateFallback: '/',
      // Không cache API: HV cần dữ liệu mới nhất
      runtimeCaching: [
        {
          urlPattern: /\/api\//,
          handler: 'NetworkOnly',
        },
      ],
    },
    devOptions: {
      enabled: false,
    },
  },

  tailwindcss: {
    cssPath: '~/assets/css/main.css',
    configPath: '~/tailwind.config.ts',
    viewer: false,
  },

  typescript: {
    strict: true,
  },
})
