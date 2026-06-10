// /robots.txt — sinh động để Sitemap dùng URL tuyệt đối (Google yêu cầu).
import { defineEventHandler } from 'h3'

export default defineEventHandler((event) => {
  const config = useRuntimeConfig()
  const siteUrl = (config.public.siteUrl as string).replace(/\/$/, '')
  event.node.res.setHeader('Content-Type', 'text/plain; charset=utf-8')
  return `User-agent: *
Allow: /
Disallow: /dh/

Sitemap: ${siteUrl}/sitemap.xml
`
})
