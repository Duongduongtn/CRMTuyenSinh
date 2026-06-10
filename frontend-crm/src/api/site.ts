import { api } from './client'

/** Khớp serializer apps/core/serializers.py — SiteSettingsPublicSerializer. */
export interface SiteSettings {
  brand_name: string
  brand_short_name: string
  slogan: string
  description: string
  logo_url: string
  favicon_url: string
  og_image_url: string
  hotline: string
  hotline_display: string
  email: string
  address_line: string
  ward: string
  district: string
  city: string
  address_full: string
  map_embed_url: string
  facebook_url: string
  zalo_oa_id: string
  zalo_url: string
  youtube_url: string
  tiktok_url: string
  license_info: string
  meta_title_default: string
  meta_description_default: string
}

export async function fetchSiteSettings(): Promise<SiteSettings> {
  const { data } = await api.get<SiteSettings>('/site-settings')
  return data
}
