import { api } from './client'
import type { Paginated, PaymentListItem } from './types'

export interface PaymentListParams {
  page?: number
  search?: string
  status?: string
  ordering?: string
}

export async function fetchPayments(params: PaymentListParams = {}): Promise<Paginated<PaymentListItem>> {
  const { data } = await api.get<Paginated<PaymentListItem>>('/admin/payments/', { params })
  return data
}
