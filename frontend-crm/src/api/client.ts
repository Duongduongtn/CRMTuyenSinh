/**
 * Axios client cho BE Django.
 *
 * - `withCredentials: true` để gửi/nhận session cookie cùng origin (dev: localhost qua Vite proxy, prod: cùng subdomain crm.).
 * - Interceptor request: đọc cookie `csrftoken` và set header `X-CSRFToken` cho mọi
 *   POST/PUT/PATCH/DELETE — Django CsrfViewMiddleware yêu cầu.
 * - Interceptor response: 401/403 trên endpoint protected → đẩy về /login.
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const BASE = import.meta.env.VITE_API_BASE || ''

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete'])

export const api: AxiosInstance = axios.create({
  baseURL: `${BASE}/api`,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
  // 25s — đủ cho query report nặng. Hơn nữa thì cancel.
  timeout: 25_000,
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const method = (config.method || 'get').toLowerCase()
  if (UNSAFE_METHODS.has(method)) {
    const token = getCookie('csrftoken')
    if (token && config.headers) {
      config.headers.set('X-CSRFToken', token)
    }
  }
  return config
})

let authRedirectTimer: number | null = null

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    const url: string = error?.config?.url || ''
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/csrf')
    // 401/403 trên endpoint không phải login → session hết hạn / chưa đăng nhập.
    // Đẩy về /login, nhưng tránh redirect lặp nếu đang ở /login.
    if ((status === 401 || status === 403) && !isAuthEndpoint) {
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        if (authRedirectTimer) window.clearTimeout(authRedirectTimer)
        authRedirectTimer = window.setTimeout(() => {
          const next = encodeURIComponent(window.location.pathname + window.location.search)
          window.location.assign(`/login?next=${next}`)
        }, 50)
      }
    }
    return Promise.reject(error)
  },
)

/** Lấy CSRF cookie trước khi POST đầu tiên (login). */
export async function ensureCsrf(): Promise<void> {
  await api.get('/auth/csrf')
}
