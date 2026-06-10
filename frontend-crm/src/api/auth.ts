import { api, ensureCsrf } from './client'

export interface User {
  id: number
  username: string
  full_name: string
  display_name: string
  email: string
  phone: string
  job_title: string
  avatar_url: string | null
  is_superuser: boolean
  is_staff: boolean
  groups: string[]
  role_labels: string[]
  permissions: string[]
}

export async function login(username: string, password: string): Promise<User> {
  await ensureCsrf()
  const { data } = await api.post<User>('/auth/login', { username, password })
  return data
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}
