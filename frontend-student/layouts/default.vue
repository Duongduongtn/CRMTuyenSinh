<script setup lang="ts">
import { PhHouse, PhFolders, PhUserCircle, PhSignOut, PhGraduationCap } from '@phosphor-icons/vue'

const route = useRoute()
const { isAuthenticated, account, logout } = useAuth()

const navItems = [
  { to: '/dashboard', icon: PhHouse, label: 'Tổng quan' },
  { to: '/ho-so', icon: PhFolders, label: 'Hồ sơ' },
  { to: '/tai-khoan', icon: PhUserCircle, label: 'Tài khoản' },
]

const isActive = (to: string) => route.path === to || route.path.startsWith(to + '/')
</script>

<template>
  <div class="min-h-screen flex flex-col bg-paper-alt">
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:bg-ink focus:text-white focus:rounded-md"
    >Bỏ qua tới nội dung</a>
    <header v-if="isAuthenticated" class="sticky top-0 z-30 bg-paper border-b border-line-soft" style="padding-top: var(--safe-top);">
      <div class="container-base flex items-center justify-between h-14">
        <NuxtLink to="/dashboard" class="flex items-center gap-2">
          <div class="size-8 bg-brand-700 text-white rounded-md flex items-center justify-center">
            <PhGraduationCap class="size-5" weight="bold" />
          </div>
          <span class="font-semibold text-[15px] tracking-tight">Học viên</span>
        </NuxtLink>
        <div class="flex items-center gap-1">
          <span v-if="account" class="hidden sm:inline text-xs text-ink-60">{{ account.display_name || account.phone }}</span>
          <button
            class="p-2 min-w-11 min-h-11 rounded-md hover:bg-paper-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
            aria-label="Đăng xuất"
            @click="logout"
          >
            <PhSignOut class="size-5 text-ink-60" />
          </button>
        </div>
      </div>
    </header>

    <main id="main" class="flex-1 pb-24" :class="{ 'pt-2': isAuthenticated }">
      <slot />
    </main>

    <!-- Bottom tab bar (mobile-first PWA pattern) -->
    <nav
      v-if="isAuthenticated"
      class="fixed bottom-0 inset-x-0 z-30 bg-paper border-t border-line-soft"
      style="padding-bottom: var(--safe-bottom);"
    >
      <ul class="container-base flex items-stretch justify-around h-16">
        <li v-for="item in navItems" :key="item.to" class="flex-1">
          <NuxtLink
            :to="item.to"
            class="h-full flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors duration-300 ease-out-expo"
            :class="isActive(item.to) ? 'text-brand-700 bg-brand-50/70' : 'text-ink-40 hover:text-ink-60'"
          >
            <component :is="item.icon" class="size-6" :weight="isActive(item.to) ? 'fill' : 'regular'" />
            <span>{{ item.label }}</span>
          </NuxtLink>
        </li>
      </ul>
    </nav>
  </div>
</template>
