// Courses — list + detail từ Django /api/public/courses/.

export type VehicleGroup = 'motorcycle' | 'car' | 'truck' | 'bus' | 'upgrade'

export interface CourseListItem {
  id: number
  slug: string
  title: string
  vehicle_class: string
  vehicle_class_display: string
  vehicle_group: VehicleGroup
  vehicle_group_display: string
  short_description: string
  tuition_fee: string  // Decimal serialize as string in DRF
  deposit_amount: string
  duration_display: string
  duration_days: number
  cover_image_url: string
  is_featured: boolean
  sort_order: number
}

export interface CourseDetail extends CourseListItem {
  description_md: string
  meta_title: string
  meta_description: string
  og_image_url: string
  total_slots: number
  available_slots: number
  updated_at: string
}

interface PaginatedCourses {
  count: number
  next: string | null
  previous: string | null
  results: CourseListItem[]
}

export const useCourses = () => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<PaginatedCourses>('/public/courses/', {
    baseURL: apiBase,
    key: 'courses-list',
    server: true,
    lazy: false,
    default: () => ({ count: 0, next: null, previous: null, results: [] }),
  })
}

export const useCourse = (slug: string) => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<CourseDetail>(`/public/courses/${slug}/`, {
    baseURL: apiBase,
    key: `course-${slug}`,
    server: true,
    lazy: false,
  })
}

// Vietnam currency format: 17.500.000đ
export const formatVND = (value: string | number): string => {
  const n = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(n)) return '0đ'
  return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + 'đ'
}
