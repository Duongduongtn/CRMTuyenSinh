/**
 * API học viên (CRM phía staff).
 *
 * Sprint 3 Tuần 7 gói B (2026-06-12): văn thư bấm "Tạo link xem nhanh" trong
 * trang chi tiết đơn → BE trả URL quick-view 24h, văn thư copy link gửi tay
 * cho học viên qua Zalo/SMS/gọi điện (bỏ ZNS auto).
 */
import { api } from './client'

export interface QuickTokenResponse {
  url: string
  expires_in_seconds: number
  enrollment_code: string
}

export async function generateStudentQuickToken(enrollmentId: number): Promise<QuickTokenResponse> {
  const { data } = await api.post<QuickTokenResponse>('/student/staff/quick-token', {
    enrollment_id: enrollmentId,
  })
  return data
}
