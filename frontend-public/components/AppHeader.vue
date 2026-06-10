<script setup lang="ts">
import { PhPhone, PhList, PhX } from '@phosphor-icons/vue'
import type { SiteSettings } from '~/composables/useSiteSettings'

defineProps<{ site: SiteSettings | null }>()

const isMobileOpen = ref(false)
const route = useRoute()
watch(() => route.path, () => { isMobileOpen.value = false })

const nav = [
  { to: '/khoa-hoc', label: 'Khóa học' },
  { to: '/tin-tuc', label: 'Tin tức' },
  { to: '/#quy-trinh', label: 'Quy trình' },
  { to: '/lien-he', label: 'Liên hệ' },
]
</script>

<template>
  <header class="sticky top-0 z-40 bg-paper/95 backdrop-blur-sm border-b border-line-soft">
    <nav class="container-base flex items-center justify-between h-16 md:h-18">
      <NuxtLink to="/" class="flex items-center gap-2.5">
        <div class="size-8 bg-ink text-white rounded-md flex items-center justify-center font-bold text-sm">
          {{ site?.brand_short_name || 'TT' }}
        </div>
        <span class="font-bold text-base tracking-tight">{{ site?.brand_name || 'Trung tâm Đào tạo Lái xe' }}</span>
      </NuxtLink>

      <ul class="hidden lg:flex items-center gap-8 text-[15px]">
        <li v-for="item in nav" :key="item.to">
          <NuxtLink :to="item.to" class="text-ink-60 hover:text-ink transition">
            {{ item.label }}
          </NuxtLink>
        </li>
      </ul>

      <div class="flex items-center gap-2">
        <a
          v-if="site?.hotline"
          :href="`tel:${site.hotline}`"
          class="hidden md:inline-flex items-center gap-1.5 text-sm font-medium px-3 min-h-11 hover:text-brand-700 transition rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
        >
          <PhPhone class="size-4" />
          {{ site?.hotline_display || site?.hotline }}
        </a>
        <NuxtLink
          to="/lien-he"
          class="inline-flex items-center gap-1.5 bg-brand-700 hover:bg-brand-800 text-white text-sm font-medium px-4 py-2.5 rounded-md transition-colors"
        >
          Tư vấn miễn phí
        </NuxtLink>
        <button
          class="lg:hidden p-2 min-w-11 min-h-11 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2"
          :aria-label="isMobileOpen ? 'Đóng menu' : 'Mở menu'"
          :aria-expanded="isMobileOpen"
          @click="isMobileOpen = !isMobileOpen"
        >
          <PhX v-if="isMobileOpen" class="size-6" />
          <PhList v-else class="size-6" />
        </button>
      </div>
    </nav>

    <!-- Mobile menu -->
    <div v-if="isMobileOpen" class="lg:hidden border-t border-line-soft bg-paper">
      <ul class="container-base py-4 space-y-1">
        <li v-for="item in nav" :key="item.to">
          <NuxtLink
            :to="item.to"
            class="block py-3 px-2 text-base font-medium hover:text-brand-700"
          >
            {{ item.label }}
          </NuxtLink>
        </li>
      </ul>
    </div>
  </header>
</template>
