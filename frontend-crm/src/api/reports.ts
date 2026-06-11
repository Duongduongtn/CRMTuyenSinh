/**
 * API báo cáo Sprint 3 Tuần 6: doanh thu + conversion + export Excel.
 * Endpoint BE: /api/admin/reports/{revenue,conversion,revenue/export.xlsx}
 */
import { api } from './client'

export interface RevenueRow {
  date: string // ISO yyyy-mm-dd
  confirmed_amount: string // decimal as string từ DRF
  confirmed_count: number
}

export interface RevenueSummary {
  total_amount: string
  total_count: number
}

export interface RevenueResponse {
  from: string
  to: string
  rows: RevenueRow[]
  summary: RevenueSummary
}

export interface ConversionResponse {
  from: string
  to: string
  leads: number
  enrollments: number
  paid: number
  rate_lead_to_enrollment_pct: number
  rate_enrollment_to_paid_pct: number
  rate_overall_pct: number
}

export interface ReportRange {
  from?: string // YYYY-MM-DD
  to?: string
}

export async function fetchRevenue(range: ReportRange = {}): Promise<RevenueResponse> {
  const { data } = await api.get<RevenueResponse>('/admin/reports/revenue', { params: range })
  return data
}

export async function fetchConversion(range: ReportRange = {}): Promise<ConversionResponse> {
  const { data } = await api.get<ConversionResponse>('/admin/reports/conversion', { params: range })
  return data
}

/** Force-download Excel. Throw nếu BE trả 4xx/5xx (toast bắt ngoài). */
export async function exportRevenueXlsx(range: ReportRange = {}): Promise<void> {
  const resp = await api.get('/admin/reports/revenue/export.xlsx', {
    params: range,
    responseType: 'blob',
  })
  const url = URL.createObjectURL(resp.data as Blob)
  const a = document.createElement('a')
  a.href = url
  const suffix = range.from && range.to ? `_${range.from}_${range.to}` : ''
  a.download = `doanh-thu${suffix}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
