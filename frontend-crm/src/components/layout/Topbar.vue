<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  Bell,
  CaretDown,
  SignOut,
  UserCircle,
  List,
} from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'

const auth = useAuthStore()
const site = useSiteStore()
const route = useRoute()
const router = useRouter()

const menuOpen = ref(false)

async function handleLogout() {
  await auth.logout()
  toast.success('Đã đăng xuất.')
  router.replace({ name: 'login' })
}

const initials = () => {
  const name = auth.user?.display_name || auth.user?.username || 'U'
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join('')
    .toUpperCase()
}
</script>

<template>
  <header class="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-line-soft bg-paper/80 backdrop-blur px-5 lg:px-8">
    <button
      class="lg:hidden flex h-9 w-9 items-center justify-center rounded-md text-ink-60 hover:bg-paper-alt"
      aria-label="Mở menu"
    >
      <List :size="20" />
    </button>

    <div class="min-w-0 flex-1">
      <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold truncate">
        {{ site.settings?.brand_short_name || site.settings?.brand_name || 'CRM nội bộ' }}
      </p>
      <p class="text-base font-semibold text-ink tracking-tight truncate" role="heading" aria-level="1">
        {{ (route.meta.title as string) || 'Tổng quan' }}
      </p>
    </div>

    <button
      class="flex h-9 w-9 items-center justify-center rounded-md text-ink-60 hover:bg-paper-alt hover:text-ink transition-colors"
      aria-label="Thông báo"
    >
      <Bell :size="18" />
    </button>

    <div class="relative">
      <button
        class="flex items-center gap-2.5 rounded-full pl-1 pr-2.5 py-1 hover:bg-paper-alt transition-colors"
        :aria-expanded="menuOpen"
        @click="menuOpen = !menuOpen"
      >
        <span class="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-paper text-[12px] font-semibold tracking-tight">
          {{ initials() }}
        </span>
        <span class="hidden sm:flex flex-col items-start leading-tight">
          <span class="text-[13px] font-medium text-ink">{{ auth.user?.display_name }}</span>
          <span class="text-[11px] text-ink-40">{{ auth.user?.role_labels.join(' · ') || 'Người dùng' }}</span>
        </span>
        <CaretDown :size="13" class="text-ink-40" />
      </button>

      <div
        v-if="menuOpen"
        class="absolute right-0 mt-2 w-60 rounded-xl border border-line-soft bg-paper shadow-[0_18px_36px_-12px_rgba(15,31,26,0.15)] overflow-hidden animate-slide-up"
      >
        <div class="border-b border-line-soft px-4 py-3">
          <p class="text-[13px] font-semibold text-ink truncate">{{ auth.user?.display_name }}</p>
          <p class="text-[11px] text-ink-60 truncate">{{ auth.user?.email || auth.user?.username }}</p>
        </div>
        <button
          class="flex w-full items-center gap-2.5 px-4 py-2.5 text-[13px] text-ink-60 hover:bg-paper-alt hover:text-ink transition-colors"
          @click="menuOpen = false"
        >
          <UserCircle :size="16" />
          <span>Hồ sơ cá nhân</span>
        </button>
        <button
          class="flex w-full items-center gap-2.5 px-4 py-2.5 text-[13px] text-danger hover:bg-danger-soft transition-colors border-t border-line-soft"
          @click="handleLogout"
        >
          <SignOut :size="16" />
          <span>Đăng xuất</span>
        </button>
      </div>
    </div>
  </header>
</template>
