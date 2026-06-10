// SiteSettings — brand info đọc từ Django /api/site-settings.
// useFetch cache theo key 'site-settings' nên gọi nhiều lần không re-fetch.

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
  map_lat: number | null
  map_lng: number | null
  working_hours_text: string
  facebook_url: string
  zalo_oa_id: string
  zalo_url: string
  youtube_url: string
  tiktok_url: string
  license_info: string
  meta_title_default: string
  meta_description_default: string
  stat_students_count: number
  stat_pass_rate_percent: number
  stat_years_experience: number
  stat_practice_area_m2: number
}

export const useSiteSettings = () => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<SiteSettings>('/site-settings', {
    baseURL: apiBase,
    key: 'site-settings',
    server: true,
    lazy: false,
    default: () => ({
      brand_name: 'Trung tâm Đào tạo Lái xe',
      brand_short_name: 'TT',
      slogan: '',
      description: '',
      logo_url: '',
      favicon_url: '',
      og_image_url: '',
      hotline: '',
      hotline_display: '',
      email: '',
      address_line: '',
      ward: '',
      district: '',
      city: '',
      address_full: '',
      map_embed_url: '',
      map_lat: null,
      map_lng: null,
      working_hours_text: '',
      facebook_url: '',
      zalo_oa_id: '',
      zalo_url: '',
      youtube_url: '',
      tiktok_url: '',
      license_info: '',
      meta_title_default: '',
      meta_description_default: '',
      stat_students_count: 0,
      stat_pass_rate_percent: 0,
      stat_years_experience: 0,
      stat_practice_area_m2: 0,
    } as SiteSettings),
  })
}
