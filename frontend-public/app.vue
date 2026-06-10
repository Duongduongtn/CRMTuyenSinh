<script setup lang="ts">
import { useSiteSettings } from '~/composables/useSiteSettings'

const { data: site } = await useSiteSettings()
const route = useRoute()

// Default SEO mặc định lấy từ site-settings, page có thể override qua useSeoMeta riêng
const ogImageDefault = computed(() => site.value?.og_image_url || '')
const baseTitle = computed(() => site.value?.brand_name || 'Trung tâm Đào tạo Lái xe')
const baseDesc = computed(
  () =>
    site.value?.meta_description_default ||
    site.value?.description ||
    'Trung tâm đào tạo lái xe chính quy theo Luật 2025.',
)

useHead({
  titleTemplate: (chunk) => (chunk ? `${chunk} · ${baseTitle.value}` : baseTitle.value),
})
useSeoMeta({
  description: baseDesc,
  ogTitle: baseTitle,
  ogDescription: baseDesc,
  ogImage: ogImageDefault,
  ogType: 'website',
  ogLocale: 'vi_VN',
  twitterCard: 'summary_large_image',
})
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-ink focus:text-white focus:px-4 focus:py-2 focus:rounded"
    >Bỏ qua tới nội dung</a>
    <AppHeader :site="site" />
    <main id="main" class="flex-1">
      <NuxtPage :transition="{ name: 'fade', mode: 'out-in' }" />
    </main>
    <AppFooter :site="site" />
  </div>
</template>
