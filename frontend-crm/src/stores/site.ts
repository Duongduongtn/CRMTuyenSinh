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

  // 1 nguồn brand cho mọi UI (sidebar / login / topbar / header tile).
  // Ưu tiên short_name (vd "Thành Đạt") → name dài (vd "Trung tâm tuyển sinh Thành Đạt") → fallback.
  function resolveBrandName(fallback = 'CRM nội bộ'): string {
    return settings.value?.brand_short_name || settings.value?.brand_name || fallback
  }

  return { settings, loading, load, resolveBrandName }
})
