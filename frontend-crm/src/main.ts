import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import { router } from './router'
import './assets/css/main.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      gcTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(VueQueryPlugin, { queryClient })

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    app,
    dsn: sentryDsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
    tracesSampleRate: parseFloat(
      import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || '0.1',
    ),
    sendDefaultPii: false,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
    ],
  })
}

app.mount('#app')
