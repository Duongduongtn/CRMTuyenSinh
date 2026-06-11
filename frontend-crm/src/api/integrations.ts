/**
 * API cho IntegrationCredential (Casso + FB Lead Ads).
 *
 * BE endpoint:
 *   GET  /api/admin/integrations/             : superuser, list theo schema
 *   PUT  /api/admin/integrations/{provider}/  : bulk update 1 provider
 *
 * Scope chốt 2026-06-11: ZNS Zalo + SMTP đã bỏ khỏi UI.
 */
import { api } from './client'

export type IntegrationSource = 'db' | 'env' | 'empty'

export interface IntegrationItem {
  key: string
  label: string
  sensitive: boolean
  help_text: string
  masked: string
  has_value: boolean
  source: IntegrationSource
  updated_at: string | null
  updated_by_username: string
}

export type IntegrationsByProvider = Record<string, IntegrationItem[]>

export async function fetchIntegrations(): Promise<IntegrationsByProvider> {
  const { data } = await api.get<IntegrationsByProvider>('/admin/integrations/')
  return data
}

export interface IntegrationUpdateResult {
  provider: string
  keys_changed: string[]
  keys_cleared: string[]
  items: IntegrationItem[]
}

export async function updateIntegration(
  provider: string,
  payload: Record<string, string>,
): Promise<IntegrationUpdateResult> {
  const { data } = await api.put<IntegrationUpdateResult>(
    `/admin/integrations/${provider}/`,
    payload,
  )
  return data
}
