// Composable cho dashboard học viên.

import type { Ref } from 'vue'

export interface PersonShort {
  id: number
  full_name: string
  id_number_last4: string
  date_of_birth: string | null
  gender: string
}

export interface EnrollmentItem {
  id: number
  code: string
  course_title: string
  course_slug: string
  vehicle_class: string
  vehicle_class_display: string
  status: string
  status_display: string
  tuition_fee: string
  deposit_amount: string
  paid_amount: string
  remaining_amount: string
  deposit_link_token: string
  created_at: string
  deposit_paid_at: string | null
  completed_at: string | null
  person: PersonShort | null
  docs_missing: number
}

interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const useEnrollments = () => {
  const { request } = useApi()
  const enrollments = ref<EnrollmentItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const load = async () => {
    loading.value = true
    error.value = null
    try {
      const resp = await request<Paginated<EnrollmentItem>>('/student/enrollments')
      enrollments.value = resp.results
    } catch (err: any) {
      error.value = err?.message || 'Không tải được danh sách đơn.'
    } finally {
      loading.value = false
    }
  }

  return { enrollments, loading, error, load }
}

export const useEnrollment = (id: Ref<number | string>) => {
  const { request } = useApi()
  const data = ref<EnrollmentItem | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const load = async () => {
    loading.value = true
    error.value = null
    try {
      data.value = await request<EnrollmentItem>(`/student/enrollments/${id.value}`)
    } catch (err: any) {
      error.value = err?.response?.status === 404
        ? 'Không tìm thấy đơn ghi danh.'
        : 'Không tải được dữ liệu.'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, load }
}

export const useMe = () => {
  const { request } = useApi()
  return request<{
    id: number
    phone: string
    display_name: string
    last_login_at: string | null
    persons: PersonShort[]
  }>('/student/me')
}

// Vietnam format helpers
export const formatVND = (value: string | number): string => {
  const n = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(n)) return '0đ'
  return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + 'đ'
}

export const formatDate = (iso: string | null): string => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export const formatDateTime = (iso: string | null): string => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
