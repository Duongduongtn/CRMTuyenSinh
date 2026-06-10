// Composable upload + list document.

export interface DocumentType {
  id: number
  code: string
  name: string
  scope: 'person' | 'enrollment'
  is_required: boolean
  description: string
}

export interface DocumentItem {
  id: number
  document_type: DocumentType
  file_url: string
  mime_type: string
  file_size: number
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'purged'
  status_display: string
  review_note: string
  reviewed_at: string | null
  created_at: string
  expires_at: string | null
}

export const useDocumentTypes = () => {
  const { request } = useApi()
  return {
    list: (scope?: 'person' | 'enrollment') =>
      request<{ count: number; results: DocumentType[] }>(
        `/student/documents/types${scope ? `?scope=${scope}` : ''}`,
      ),
  }
}

export const usePersonDocuments = (personId: number) => {
  const { request } = useApi()
  const items = ref<DocumentItem[]>([])
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)

  const load = async () => {
    loading.value = true
    error.value = null
    try {
      items.value = await request<DocumentItem[]>(`/student/persons/${personId}/documents`)
    } catch (err: any) {
      error.value = err?.response?.status === 404
        ? 'Không có quyền xem hồ sơ này.'
        : 'Không tải được hồ sơ.'
    } finally {
      loading.value = false
    }
  }

  const upload = async (documentTypeId: number, file: File): Promise<DocumentItem | null> => {
    uploading.value = true
    error.value = null
    try {
      const fd = new FormData()
      fd.append('document_type_id', String(documentTypeId))
      fd.append('file', file)
      const created = await request<DocumentItem>(
        `/student/persons/${personId}/documents`,
        { method: 'POST', body: fd },
      )
      // Optimistic refresh
      await load()
      return created
    } catch (err: any) {
      const data = err?.response?._data
      error.value = data?.detail || data?.file?.[0] || 'Upload thất bại. Vui lòng kiểm tra định dạng và kích thước file.'
      return null
    } finally {
      uploading.value = false
    }
  }

  return { items, loading, uploading, error, load, upload }
}

export const formatBytes = (n: number): string => {
  if (n < 1024) return `${n}B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)}KB`
  return `${(n / 1024 / 1024).toFixed(1)}MB`
}
