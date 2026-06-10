// Blog public API.

export interface BlogCategory {
  id: number
  slug: string
  name: string
  description: string
  sort_order: number
}

export interface BlogPostListItem {
  id: number
  slug: string
  title: string
  excerpt: string
  category: BlogCategory
  cover_image_url: string
  cover_alt: string
  published_at: string
  read_time_minutes: number
  is_featured: boolean
  view_count: number
}

export interface BlogPostDetail extends BlogPostListItem {
  content_md: string
  meta_title: string
  meta_description: string
  og_image_url: string
  canonical_url: string
  updated_at: string
}

interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const useBlogPosts = (params?: { category?: string; featured?: boolean }) => {
  const { public: { apiBase } } = useRuntimeConfig()
  const qs = new URLSearchParams()
  if (params?.category) qs.set('category__slug', params.category)
  if (params?.featured !== undefined) qs.set('is_featured', String(params.featured))
  const query = qs.toString() ? `?${qs.toString()}` : ''

  return useFetch<Paginated<BlogPostListItem>>(`/public/blog/posts/${query}`, {
    baseURL: apiBase,
    key: `blog-posts-${qs.toString()}`,
    server: true,
    lazy: false,
    default: () => ({ count: 0, next: null, previous: null, results: [] }),
  })
}

export const useBlogPost = (slug: string) => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<BlogPostDetail>(`/public/blog/posts/${slug}/`, {
    baseURL: apiBase,
    key: `blog-post-${slug}`,
    server: true,
    lazy: false,
  })
}

export const useBlogCategories = () => {
  const { public: { apiBase } } = useRuntimeConfig()
  return useFetch<Paginated<BlogCategory>>('/public/blog/categories/', {
    baseURL: apiBase,
    key: 'blog-categories',
    server: true,
    default: () => ({ count: 0, next: null, previous: null, results: [] }),
  })
}

export const formatDateVN = (iso: string | null): string => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}
