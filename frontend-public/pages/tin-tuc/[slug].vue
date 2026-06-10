<script setup lang="ts">
import { PhCalendarBlank, PhClock, PhArrowLeft, PhShare, PhUser } from '@phosphor-icons/vue'
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const slug = computed(() => String(route.params.slug))

const { data: post, error } = await useBlogPost(slug.value)
const { data: site } = await useSiteSettings()

if (!post.value && error.value) {
  throw createError({ statusCode: 404, statusMessage: 'Bài viết không tồn tại.' })
}

marked.setOptions({ gfm: true, breaks: false })
// Sanitize HTML render từ Markdown — chống XSS qua tag thô (script, onerror...)
// dù BTV soạn bài là internal user, vẫn defense in depth.
const contentHtml = computed(() => {
  if (!post.value) return ''
  const raw = marked.parse(post.value.content_md || '') as string
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  })
})

const canonical = computed(() => {
  if (post.value?.canonical_url) return post.value.canonical_url
  const base = useRuntimeConfig().public.siteUrl
  return `${base}/tin-tuc/${slug.value}`
})

useSeoMeta({
  title: () => post.value?.meta_title || post.value?.title || 'Bài viết',
  description: () => post.value?.meta_description || post.value?.excerpt || '',
  ogTitle: () => post.value?.title,
  ogDescription: () => post.value?.excerpt,
  ogImage: () => post.value?.og_image_url || post.value?.cover_image_url,
  ogType: 'article',
  articlePublishedTime: () => post.value?.published_at,
  articleModifiedTime: () => post.value?.updated_at,
})

useHead({
  link: [{ rel: 'canonical', href: canonical }],
})

// Article schema
useSchemaOrg(post.value)

function useSchemaOrg(p: typeof post.value) {
  if (!p) return
  const base = useRuntimeConfig().public.siteUrl
  const article = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    inLanguage: 'vi-VN',
    headline: p.title,
    description: p.excerpt,
    image: p.og_image_url || p.cover_image_url || undefined,
    datePublished: p.published_at,
    dateModified: p.updated_at,
    keywords: p.category.name,
    author: { '@type': 'Organization', name: site.value?.brand_name || 'Trung tâm Đào tạo Lái xe' },
    publisher: {
      '@type': 'Organization',
      name: site.value?.brand_name || 'Trung tâm Đào tạo Lái xe',
      logo: site.value?.logo_url
        ? { '@type': 'ImageObject', url: site.value.logo_url }
        : undefined,
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': canonical.value },
  }
  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: base },
      { '@type': 'ListItem', position: 2, name: 'Tin tức', item: `${base}/tin-tuc` },
      { '@type': 'ListItem', position: 3, name: p.title, item: canonical.value },
    ],
  }
  useHead({
    script: [
      { type: 'application/ld+json', innerHTML: JSON.stringify(article) },
      { type: 'application/ld+json', innerHTML: JSON.stringify(breadcrumb) },
    ],
  })
}

const share = () => {
  if (import.meta.client && navigator.share) {
    navigator.share({
      title: post.value?.title,
      text: post.value?.excerpt,
      url: window.location.href,
    }).catch(() => {})
  }
}
</script>

<template>
  <article v-if="post" class="pb-20">
    <!-- Hero -->
    <header class="container-base pt-8 md:pt-14">
      <NuxtLink
        to="/tin-tuc"
        class="inline-flex items-center gap-1 text-sm text-ink-60 hover:text-ink mb-6 min-h-11"
      >
        <PhArrowLeft class="size-4" /> Quay lại danh sách
      </NuxtLink>

      <p class="eyebrow mb-3">{{ post.category.name }}</p>
      <h1 class="text-3xl md:text-5xl font-bold tracking-tighter mb-5 max-w-3xl">{{ post.title }}</h1>
      <p class="text-lg text-ink-60 leading-relaxed max-w-2xl mb-6">{{ post.excerpt }}</p>

      <div class="flex flex-wrap items-center gap-5 text-sm text-ink-40 mb-10">
        <span class="inline-flex items-center gap-1">
          <PhUser class="size-4" /> {{ site?.brand_name }}
        </span>
        <span class="inline-flex items-center gap-1">
          <PhCalendarBlank class="size-4" /> {{ formatDateVN(post.published_at) }}
        </span>
        <span class="inline-flex items-center gap-1 num-display">
          <PhClock class="size-4" /> {{ post.read_time_minutes }} phút đọc
        </span>
        <button
          type="button"
          class="inline-flex items-center gap-1 hover:text-brand-700 transition min-h-11"
          @click="share"
        >
          <PhShare class="size-4" /> Chia sẻ
        </button>
      </div>
    </header>

    <div v-if="post.cover_image_url" class="container-base mb-10">
      <img
        :src="post.cover_image_url"
        :alt="post.cover_alt || post.title"
        class="w-full aspect-[16/9] object-cover rounded-xl"
        loading="eager"
      >
    </div>

    <!-- Content -->
    <div class="container-base">
      <div class="max-w-narrow mx-auto prose-blog" v-html="contentHtml" />
    </div>
  </article>
</template>

<style scoped>
.prose-blog {
  font-size: 1.05rem;
  line-height: 1.75;
  color: #0F1F1A;
}
.prose-blog :deep(h2) {
  font-size: 1.5rem;
  font-weight: 700;
  margin-top: 2.5rem;
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
}
.prose-blog :deep(h3) {
  font-size: 1.25rem;
  font-weight: 600;
  margin-top: 2rem;
  margin-bottom: 0.75rem;
}
.prose-blog :deep(p) {
  margin-bottom: 1.25rem;
}
.prose-blog :deep(ul),
.prose-blog :deep(ol) {
  margin: 1rem 0 1.25rem 1.25rem;
}
.prose-blog :deep(li) {
  margin-bottom: 0.5rem;
}
.prose-blog :deep(ul) { list-style: disc; }
.prose-blog :deep(ol) { list-style: decimal; }
.prose-blog :deep(a) {
  color: #15803D;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.prose-blog :deep(blockquote) {
  border-left: 3px solid #15803D;
  padding-left: 1rem;
  color: #56635E;
  font-style: italic;
  margin: 1.5rem 0;
}
.prose-blog :deep(code) {
  background: #F7FAF9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, monospace;
}
.prose-blog :deep(img) {
  border-radius: 0.5rem;
  margin: 1.5rem 0;
}
</style>
