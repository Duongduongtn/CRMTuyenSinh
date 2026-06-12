/**
 * API admin cho SiteSettings (Singleton thông tin trung tâm).
 *
 * BE endpoint:
 *   GET   /api/admin/site-settings/   : superuser, trả full field text/number + URL ảnh.
 *   PATCH /api/admin/site-settings/   : superuser, partial update field text/number.
 *
 * Ảnh (logo/favicon/og_image) tạm thời chỉnh trong Django admin tới khi build
 * upload UI — endpoint này chỉ trả URL read-only.
 */
import { api } from './client'

export interface SiteSettingsAdmin {
  // Thương hiệu
  brand_name: string
  brand_short_name: string
  slogan: string
  description: string
  // Liên hệ
  hotline: string
  hotline_display: string
  email: string
  address_line: string
  ward: string
  district: string
  city: string
  map_lat: string | null
  map_lng: string | null
  map_embed_url: string
  working_hours_text: string
  // Mạng xã hội
  facebook_url: string
  zalo_oa_id: string
  zalo_url: string
  youtube_url: string
  tiktok_url: string
  // Ngân hàng
  bank_code: string
  bank_account_number: string
  bank_account_name: string
  // Pháp lý
  license_info: string
  company_full_name: string
  tax_code: string
  // SEO
  meta_title_default: string
  meta_description_default: string
  // Stats
  stat_students_count: number
  stat_pass_rate_percent: number
  stat_years_experience: number
  stat_practice_area_m2: number
  // Read-only URL ảnh
  logo_url: string
  favicon_url: string
  og_image_url: string
}

export type SiteSettingsAdminPatch = Partial<
  Omit<SiteSettingsAdmin, 'logo_url' | 'favicon_url' | 'og_image_url'>
>

export async function fetchSiteSettingsAdmin(): Promise<SiteSettingsAdmin> {
  const { data } = await api.get<SiteSettingsAdmin>('/admin/site-settings/')
  return data
}

export async function updateSiteSettingsAdmin(
  payload: SiteSettingsAdminPatch,
): Promise<SiteSettingsAdmin> {
  const { data } = await api.patch<SiteSettingsAdmin>(
    '/admin/site-settings/',
    payload,
  )
  return data
}
