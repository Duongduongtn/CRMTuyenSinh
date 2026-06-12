/**
 * API admin cho SiteSettings (Singleton thông tin trung tâm).
 *
 * BE endpoint:
 *   GET   /api/admin/site-settings/   : superuser, trả full field text/number + URL ảnh.
 *   PATCH /api/admin/site-settings/   : superuser, partial update field text/number.
 *
 * Ảnh (logo/favicon/og_image) tạm thời chỉnh trong Django admin tới khi build
 * upload UI: endpoint này chỉ trả URL read-only.
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

export type BrandImageField = 'logo' | 'favicon' | 'og_image'

/**
 * Spec client-side để validate trước khi upload. PHẢI đồng bộ với
 * backend/apps/core/image_uploads.py IMAGE_FIELD_SPECS.
 * Sprint 4+: cân nhắc expose GET /api/admin/site-settings/image-spec/ để FE
 * pull thay vì hard-code 2 nơi (drift risk khi Sprint 5+ đổi 1 phía).
 */
export const BRAND_IMAGE_SPEC: Record<
  BrandImageField,
  {
    label: string
    accept: string
    maxBytes: number
    minWidth: number
    minHeight: number
    maxWidth: number
    maxHeight: number
    hint: string
  }
> = {
  logo: {
    label: 'Logo trung tâm',
    accept: 'image/png,image/jpeg,image/webp',
    maxBytes: 2 * 1024 * 1024,
    minWidth: 256,
    minHeight: 256,
    maxWidth: 4096,
    maxHeight: 4096,
    hint: 'PNG / JPEG / WebP. Tối đa 2 MB. Tối thiểu 256x256.',
  },
  favicon: {
    label: 'Favicon',
    accept: 'image/png,image/x-icon,image/vnd.microsoft.icon',
    maxBytes: 512 * 1024,
    minWidth: 16,
    minHeight: 16,
    maxWidth: 512,
    maxHeight: 512,
    hint: 'PNG hoặc ICO. Tối đa 512 KB. 16x16 đến 512x512.',
  },
  og_image: {
    label: 'Ảnh chia sẻ mạng xã hội',
    accept: 'image/png,image/jpeg,image/webp',
    maxBytes: 5 * 1024 * 1024,
    minWidth: 600,
    minHeight: 315,
    maxWidth: 4096,
    maxHeight: 4096,
    hint: 'PNG / JPEG / WebP. Tối đa 5 MB. Khuyến nghị 1200x630.',
  },
}

export async function uploadBrandImage(
  field: BrandImageField,
  file: File,
): Promise<SiteSettingsAdmin> {
  const form = new FormData()
  form.append('field', field)
  form.append('image', file)
  const { data } = await api.post<SiteSettingsAdmin>(
    '/admin/site-settings/upload-image/',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function deleteBrandImage(
  field: BrandImageField,
): Promise<SiteSettingsAdmin> {
  const { data } = await api.delete<SiteSettingsAdmin>(
    '/admin/site-settings/upload-image/',
    { data: { field } },
  )
  return data
}
