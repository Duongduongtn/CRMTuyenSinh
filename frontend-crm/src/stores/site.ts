import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSiteSettings, type SiteSettings } from '@/api/site'

export const useSiteStore = defineStore('site', () => {
  const settings = ref<SiteSettings | null>(null)
  const loading = ref(false)

  async function load(): Promise<void> {
    if (settings.value || loading.value) return
    loading.value = true
    try {
      settings.value = await fetchSiteSettings()
    } catch {
      // Cho phép app vẫn chạy với fallback brand name nếu BE chưa khởi tạo SiteSettings.
    } finally {
      loading.value = false
    }
  }

  return { settings, loading, load }
})
