import { api } from './client'
import type { LeadContact, LeadDetail, LeadListItem, LeadReason, Paginated } from './types'

export interface LeadListParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
  priority?: string
  source?: string
  vehicle_class?: string
  assigned_to?: number | string
  ordering?: string
}

export async function fetchLeads(params: LeadListParams = {}): Promise<Paginated<LeadListItem>> {
  const { data } = await api.get<Paginated<LeadListItem>>('/admin/leads/', { params })
  return data
}

export async function fetchLead(id: number): Promise<LeadDetail> {
  const { data } = await api.get<LeadDetail>(`/admin/leads/${id}/`)
  return data
}

export interface ContactPayload {
  contact_type: 'call' | 'zalo' | 'sms' | 'email' | 'other'
  status_after: 'following' | 'success' | 'failed'
  priority_after?: 'hot' | 'warm' | 'cold' | ''
  reason?: number | null
  reason_text?: string
  note?: string
  next_contact_date?: string | null
}

export async function recordContact(leadId: number, payload: ContactPayload): Promise<LeadContact> {
  const { data } = await api.post<LeadContact>(`/admin/leads/${leadId}/contact/`, payload)
  return data
}

export async function fetchLeadReasons(scope?: 'following' | 'failed'): Promise<LeadReason[]> {
  const params = scope ? { status_scope: scope } : undefined
  const { data } = await api.get<Paginated<LeadReason> | LeadReason[]>('/admin/lead-reasons/', { params })
  return Array.isArray(data) ? data : data.results
}
