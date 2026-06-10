import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchMe, login as apiLogin, logout as apiLogout, type User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const groups = computed(() => user.value?.groups ?? [])
  const isAdmin = computed(() => user.value?.is_superuser || groups.value.includes('admin'))
  const isSale = computed(() => groups.value.includes('sale'))
  const isAccountant = computed(() => groups.value.includes('accountant'))
  const isClerk = computed(() => groups.value.includes('clerk'))

  function hasGroup(name: string): boolean {
    return groups.value.includes(name)
  }

  function hasAnyGroup(names: string[]): boolean {
    if (isAdmin.value) return true
    return names.some((n) => groups.value.includes(n))
  }

  async function bootstrap(): Promise<void> {
    if (initialized.value) return
    loading.value = true
    try {
      user.value = await fetchMe()
    } catch {
      user.value = null
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  async function login(username: string, password: string): Promise<void> {
    user.value = await apiLogin(username, password)
    initialized.value = true
  }

  async function logout(): Promise<void> {
    try {
      await apiLogout()
    } finally {
      user.value = null
    }
  }

  return {
    user,
    loading,
    initialized,
    isAuthenticated,
    groups,
    isAdmin,
    isSale,
    isAccountant,
    isClerk,
    hasGroup,
    hasAnyGroup,
    bootstrap,
    login,
    logout,
  }
})
