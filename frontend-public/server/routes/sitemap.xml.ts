// Server route /sitemap.xml — render runtime + được prerender vào file static.
// Lấy slug khóa từ BE /api/public/courses để sitemap không lệch với DB.

import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const siteUrl = (config.public.siteUrl as string).replace(/\/$/, '')
  const apiBase = (config.public.apiBase as string).replace(/\/$/, '')

  type Course = { slug: string; updated_at?: string }
  let courses: Course[] = []
  try {
    const res = await $fetch<{ results: Course[] }>(`${apiBase}/public/courses/`)
    courses = res.results || []
  } catch {
    courses = []
  }

  const now = new Date().toISOString()
  const urls: string[] = [
    `${siteUrl}/`,
    `${siteUrl}/khoa-hoc`,
    ...courses.map((c) => `${siteUrl}/khoa-hoc/${c.slug}`),
  ]

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) => `  <url>
    <loc>${u}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>weekly</changefreq>
  </url>`,
  )
  .join('\n')}
</urlset>
`
  event.node.res.setHeader('Content-Type', 'application/xml; charset=utf-8')
  return body
})
