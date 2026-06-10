// Enrollment public — trang /dh/[token].
// Polling 3s để bắt Casso webhook confirm payment.

export interface EnrollmentPublic {
  code: string
  course_title: string
  vehicle_class: string
  student_name: string
  tuition_fee: string
  deposit_amount: string
  paid_amount: string
  status: 'pending' | 'deposited' | 'partial' | 'completed' | 'cancelled' | 'refunded'
  status_display: string
  is_deposit_paid: boolean
  created_at: string
}

export interface DepositQR {
  qr_url: string
  bank_code: string
  account_number: string
  account_name: string
  amount: number
  add_info: string
}

export const useEnrollmentByToken = (token: string) => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<EnrollmentPublic>(`/public/enrollments/by-token/${token}`, {
    baseURL: apiBase,
    key: `enrollment-${token}`,
    server: true,
    lazy: false,
  })
}

export const useDepositQR = (token: string) => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<DepositQR>(`/public/enrollments/by-token/${token}/qr`, {
    baseURL: apiBase,
    key: `deposit-qr-${token}`,
    server: true,
    lazy: false,
  })
}
