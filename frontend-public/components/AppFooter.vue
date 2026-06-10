<script setup lang="ts">
import {
  PhFacebookLogo,
  PhYoutubeLogo,
  PhChatCircleText,
  PhMapPin,
  PhPhone,
  PhEnvelope,
  PhClock,
} from '@phosphor-icons/vue'
import type { SiteSettings } from '~/composables/useSiteSettings'

defineProps<{ site: SiteSettings | null }>()

const year = new Date().getFullYear()
</script>

<template>
  <footer class="bg-paper border-t border-line-base py-14 md:py-20">
    <div class="container-base">
      <div class="grid grid-cols-2 md:grid-cols-12 gap-10 mb-12">
        <div class="col-span-2 md:col-span-4">
          <NuxtLink to="/" class="flex items-center gap-2.5 mb-5">
            <div class="size-8 bg-ink text-white rounded-md flex items-center justify-center font-bold text-sm">
              {{ site?.brand_short_name || 'TT' }}
            </div>
            <span class="font-bold text-base tracking-tight">{{ site?.brand_name }}</span>
          </NuxtLink>
          <p v-if="site?.description" class="text-ink-60 leading-relaxed max-w-xs">{{ site.description }}</p>
          <p v-else-if="site?.license_info" class="text-ink-60 leading-relaxed max-w-xs">{{ site.license_info }}</p>

          <div class="flex gap-3 mt-6">
            <a v-if="site?.facebook_url"
               :href="site.facebook_url" target="_blank" rel="noopener" aria-label="Facebook"
               class="size-9 border border-line-base rounded-lg flex items-center justify-center hover:bg-ink hover:text-white hover:border-ink transition">
              <PhFacebookLogo class="size-5" />
            </a>
            <a v-if="site?.zalo_url"
               :href="site.zalo_url" target="_blank" rel="noopener" aria-label="Zalo"
               class="size-9 border border-line-base rounded-lg flex items-center justify-center hover:bg-ink hover:text-white hover:border-ink transition">
              <PhChatCircleText class="size-5" />
            </a>
            <a v-if="site?.youtube_url"
               :href="site.youtube_url" target="_blank" rel="noopener" aria-label="YouTube"
               class="size-9 border border-line-base rounded-lg flex items-center justify-center hover:bg-ink hover:text-white hover:border-ink transition">
              <PhYoutubeLogo class="size-5" />
            </a>
          </div>
        </div>

        <div class="md:col-span-2">
          <h4 class="font-semibold mb-4 text-sm">Khóa học</h4>
          <ul class="space-y-2.5 text-sm text-ink-60">
            <li><NuxtLink to="/khoa-hoc?nhom=motorcycle" class="hover:text-ink transition">Mô tô</NuxtLink></li>
            <li><NuxtLink to="/khoa-hoc?nhom=car" class="hover:text-ink transition">Ô tô con</NuxtLink></li>
            <li><NuxtLink to="/khoa-hoc?nhom=truck" class="hover:text-ink transition">Xe tải</NuxtLink></li>
            <li><NuxtLink to="/khoa-hoc?nhom=bus" class="hover:text-ink transition">Xe khách</NuxtLink></li>
          </ul>
        </div>

        <div class="md:col-span-2">
          <h4 class="font-semibold mb-4 text-sm">Liên kết</h4>
          <ul class="space-y-2.5 text-sm text-ink-60">
            <li><NuxtLink to="/khoa-hoc" class="hover:text-ink transition">Tất cả khóa học</NuxtLink></li>
            <li><NuxtLink to="/#lien-he" class="hover:text-ink transition">Liên hệ</NuxtLink></li>
            <li><NuxtLink to="/#quy-trinh" class="hover:text-ink transition">Quy trình</NuxtLink></li>
          </ul>
        </div>

        <div class="md:col-span-4">
          <h4 class="font-semibold mb-4 text-sm">Liên hệ</h4>
          <ul class="space-y-3 text-sm text-ink-60">
            <li v-if="site?.address_full" class="flex gap-2.5">
              <PhMapPin class="text-brand-700 shrink-0 mt-0.5 size-4" />
              <span>{{ site.address_full }}</span>
            </li>
            <li v-if="site?.hotline" class="flex gap-2.5">
              <PhPhone class="text-brand-700 shrink-0 mt-0.5 size-4" />
              <a :href="`tel:${site.hotline}`" class="hover:text-ink transition">{{ site.hotline_display || site.hotline }}</a>
            </li>
            <li v-if="site?.email" class="flex gap-2.5">
              <PhEnvelope class="text-brand-700 shrink-0 mt-0.5 size-4" />
              <a :href="`mailto:${site.email}`" class="hover:text-ink transition">{{ site.email }}</a>
            </li>
            <li v-if="site?.working_hours_text" class="flex gap-2.5">
              <PhClock class="text-brand-700 shrink-0 mt-0.5 size-4" />
              <span>{{ site.working_hours_text }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="pt-8 border-t border-line-soft flex flex-col md:flex-row gap-4 md:justify-between items-start md:items-center text-sm text-ink-40">
        <div>© {{ year }} {{ site?.brand_name }}. Mọi quyền được bảo lưu.</div>
        <div v-if="site?.license_info" class="text-ink-40">{{ site.license_info }}</div>
      </div>
    </div>
  </footer>
</template>
