/**
 * TypeScript types khớp serializer BE Django.
 *
 * Convention: snake_case từ JSON → giữ nguyên để khớp 1-1, KHÔNG camelCase.
 */

export type LeadStatus = 'new' | 'following' | 'success' | 'failed'
export type LeadPriority = 'hot' | 'warm' | 'cold' | ''
export type LeadSource =
  | 'website'
  | 'landing'
  | 'hotline'
  | 'zalo'
  | 'fb_ads'
  | 'phone'
  | 'referral'
  | 'import'
  | 'other'

export interface LeadListItem {
  id: number
  name: string
  phone: string
  vehicle_class: string
  status: LeadStatus
  priority: LeadPriority
  assigned_to: number | null
  assigned_to_name: string
  contact_count: number
  last_contact_at: string | null
  next_contact_date: string | null
  source: LeadSource
  created_at: string
}

export interface LeadContact {
  id: number
  lead: number
  user: number
  user_name: string
  contact_type: string
  status_before: LeadStatus
  status_after: LeadStatus
  priority_after: LeadPriority
  reason: number | null
  reason_name: string
  reason_text: string
  note: string
  next_contact_date: string | null
  created_at: string
}

export interface LeadDetail extends LeadListItem {
  email: string
  district: string
  address: string
  notes: string
  reason: number | null
  reason_name: string
  reason_text: string
  source_page: string
  source_title: string
  utm_source: string
  utm_medium: string
  utm_campaign: string
  utm_content: string
  utm_term: string
  device_type: string
  device_os: string
  device_browser: string
  screen_size: string
  ip_address: string | null
  user_agent: string
  converted_to_order: boolean
  order_code: string
  converted_at: string | null
  updated_at: string
  contacts: LeadContact[]
}

export interface LeadReason {
  id: number
  name: string
  status_scope: 'following' | 'failed'
  sort_order: number
}

export type EnrollmentStatus =
  | 'pending_deposit'
  | 'deposit_paid'
  | 'partial_paid'
  | 'fully_paid'
  | 'completed'
  | 'cancelled'

export interface EnrollmentListItem {
  id: number
  code: string
  status: EnrollmentStatus
  person_name: string
  person_phone: string
  course_title: string
  vehicle_class: string
  total_amount: string
  deposit_amount: string
  paid_amount: string
  created_at: string
}

export interface PaymentListItem {
  id: number
  enrollment: number
  enrollment_code: string
  amount: string
  payment_method: string
  status: string
  confirmed_at: string | null
  created_at: string
  note: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
