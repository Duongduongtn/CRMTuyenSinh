import { api } from './client'
import type { EnrollmentListItem, Paginated } from './types'

export interface OrderListParams {
  page?: number
  search?: string
  status?: string
  ordering?: string
}

export async function fetchEnrollments(params: OrderListParams = {}): Promise<Paginated<EnrollmentListItem>> {
  const { data } = await api.get<Paginated<EnrollmentListItem>>('/admin/enrollments/', { params })
  return data
}

export async function fetchEnrollment(id: number): Promise<EnrollmentListItem & Record<string, unknown>> {
  const { data } = await api.get(`/admin/enrollments/${id}/`)
  return data
}

/** Trả PDF blob để FE force-download. */
export async function downloadEnrollmentPDF(id: number, code: string): Promise<void> {
  const resp = await api.get(`/admin/enrollments/${id}/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(resp.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `don-dang-ky-${code}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
