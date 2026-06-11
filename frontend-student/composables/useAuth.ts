// Auth composable — JWT access (15p) + refresh (7 ngày) qua localStorage.
// Refresh tự động khi access hết hạn.
//
// Sprint 3 Tuần 7 gói B (2026-06-12): bỏ OTP ZNS, login = SĐT + 6 số cuối
// CCCD (xem memory student-auth-flow).

const STORAGE_ACCESS = 'crm_student_access'
const STORAGE_REFRESH = 'crm_student_refresh'
const STORAGE_ACCOUNT = 'crm_student_account'

export interface StudentAccount {
  id: number
  phone: string
  display_name: string
}

export interface LoginLockedError {
  code: 'account_locked'
  remaining_seconds: number
  detail: string
}

export interface LoginInvalidError {
  code: 'invalid_credentials'
  detail: string
}

const accountState = ref<StudentAccount | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)

const hydrate = () => {
  if (!import.meta.client) return
  accessToken.value = localStorage.getItem(STORAGE_ACCESS)
  refreshToken.value = localStorage.getItem(STORAGE_REFRESH)
  const accStr = localStorage.getItem(STORAGE_ACCOUNT)
  if (accStr) {
    try { accountState.value = JSON.parse(accStr) }
    catch { accountState.value = null }
  }
}

const persist = (access: string, refresh: string, account: StudentAccount) => {
  if (!import.meta.client) return
  accessToken.value = access
  refreshToken.value = refresh
  accountState.value = account
  localStorage.setItem(STORAGE_ACCESS, access)
  localStorage.setItem(STORAGE_REFRESH, refresh)
  localStorage.setItem(STORAGE_ACCOUNT, JSON.stringify(account))
}

const clear = () => {
  accessToken.value = null
  refreshToken.value = null
  accountState.value = null
  if (import.meta.client) {
    localStorage.removeItem(STORAGE_ACCESS)
    localStorage.removeItem(STORAGE_REFRESH)
    localStorage.removeItem(STORAGE_ACCOUNT)
  }
}

export const useAuth = () => {
  const { public: { apiBase } } = useRuntimeConfig()

  if (import.meta.client && !accessToken.value && localStorage.getItem(STORAGE_ACCESS)) {
    hydrate()
  }

  const login = async (phone: string, last6Cccd: string) => {
    const resp = await $fetch<{
      access: string
      refresh: string
      account: StudentAccount
    }>(`${apiBase}/student/auth/login`, {
      method: 'POST',
      body: { phone, last6_cccd: last6Cccd },
    })
    persist(resp.access, resp.refresh, resp.account)
    return resp
  }

  const refreshAccess = async (): Promise<boolean> => {
    if (!refreshToken.value) return false
    try {
      const resp = await $fetch<{ access: string }>(
        `${apiBase}/student/auth/refresh`,
        { method: 'POST', body: { refresh: refreshToken.value } },
      )
      accessToken.value = resp.access
      if (import.meta.client) localStorage.setItem(STORAGE_ACCESS, resp.access)
      return true
    } catch {
      clear()
      return false
    }
  }

  const logout = () => {
    clear()
    navigateTo('/dang-nhap')
  }

  const isAuthenticated = computed(() => !!accessToken.value)

  return {
    account: readonly(accountState),
    accessToken: readonly(accessToken),
    isAuthenticated,
    login,
    refreshAccess,
    logout,
    hydrate,
  }
}

/**
 * Wrapper $fetch tự gắn Authorization header + auto refresh khi 401.
 */
export const useApi = () => {
  const { public: { apiBase } } = useRuntimeConfig()
  const { refreshAccess, logout } = useAuth()

  const request = async <T>(
    path: string,
    opts: Parameters<typeof $fetch>[1] = {},
  ): Promise<T> => {
    const headers = new Headers(opts.headers || {})
    if (accessToken.value) {
      headers.set('Authorization', `Bearer ${accessToken.value}`)
    }
    try {
      return await $fetch<T>(`${apiBase}${path}`, {
        ...opts,
        headers,
      })
    } catch (err: any) {
      if (err?.response?.status === 401) {
        const ok = await refreshAccess()
        if (ok && accessToken.value) {
          headers.set('Authorization', `Bearer ${accessToken.value}`)
          return await $fetch<T>(`${apiBase}${path}`, { ...opts, headers })
        }
        logout()
      }
      throw err
    }
  }

  return { request }
}
